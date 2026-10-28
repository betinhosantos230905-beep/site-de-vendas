
import json
import logging
import secrets
import uuid
from datetime import datetime
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from flask import Blueprint, jsonify, request
from backend.database import get_connection
from backend.routes.funcionamento import obter_situacao

orders_bp = Blueprint("orders", __name__)

CENTAVO = Decimal("0.01")
ZERO = Decimal("0.00")


def dinheiro(valor):
    try:
        valor = Decimal(str(valor))

        if not valor.is_finite():
            raise ValueError()

        return valor.quantize(
            CENTAVO,
            rounding=ROUND_HALF_UP
        )

    except (InvalidOperation, TypeError, ValueError):
        raise ValueError("Valor monetário inválido.")


def obter_configuracoes(cursor):
    cursor.execute(
        "SELECT chave, valor FROM configuracoes_loja"
    )

    return {
        linha["chave"]: linha["valor"]
        for linha in cursor.fetchall()
    }


def criar_numero_pedido(cursor):
    for _ in range(5):
        numero = (
            datetime.now().strftime("S%y%m%d")
            + secrets.token_hex(3).upper()
        )

        cursor.execute(
            "SELECT id FROM pedidos WHERE numero = %s",
            (numero,)
        )

        if not cursor.fetchone():
            return numero

    raise RuntimeError(
        "Não foi possível gerar o número do pedido."
    )


def normalizar_telefone(valor):
    return "".join(
        caractere
        for caractere in str(valor or "")
        if caractere.isdigit()
    )


def calcular_desconto_cupom(cupom, subtotal):
    valor = dinheiro(cupom["valor"])

    if valor <= ZERO:
        raise ValueError("O valor desse cupom é inválido.")

    if cupom["tipo"] == "percentual":
        if valor > Decimal("100"):
            raise ValueError(
                "O percentual desse cupom é inválido."
            )

        desconto = dinheiro(
            subtotal * valor / Decimal("100")
        )

    elif cupom["tipo"] == "valor_fixo":
        desconto = valor

    else:
        raise ValueError(
            "O tipo desse cupom não é válido."
        )

    return min(max(desconto, ZERO), subtotal)


def validar_cupom(cursor, codigo, telefone, subtotal):
    if not codigo:
        return None, ZERO

    codigo = str(codigo).strip().upper()

    if len(codigo) > 30:
        raise ValueError("O código do cupom é inválido.")

    cursor.execute(
        """
        SELECT
            id,
            codigo,
            tipo,
            valor,
            pedido_minimo,
            inicio_em,
            fim_em,
            limite_total,
            limite_por_cliente,
            ativo
        FROM cupons
        WHERE UPPER(codigo) = %s
        FOR UPDATE
        """,
        (codigo,)
    )

    cupom = cursor.fetchone()

    if not cupom or not cupom["ativo"]:
        raise ValueError("Cupom inválido ou inativo.")

    cursor.execute("SELECT NOW() AS agora")
    agora = cursor.fetchone()["agora"]

    if (
        cupom["inicio_em"] is not None
        and agora < cupom["inicio_em"]
    ):
        raise ValueError(
            "Esse cupom ainda não está válido."
        )

    if (
        cupom["fim_em"] is not None
        and agora > cupom["fim_em"]
    ):
        raise ValueError("Esse cupom expirou.")

    pedido_minimo_cupom = dinheiro(
        cupom["pedido_minimo"] or ZERO
    )

    if subtotal < pedido_minimo_cupom:
        raise ValueError(
            "Este cupom exige um pedido mínimo de "
            f"R$ {pedido_minimo_cupom:.2f}."
        )

    cursor.execute(
        """
        SELECT COUNT(*) AS total
        FROM cupom_usos
        WHERE cupom_id = %s
        """,
        (cupom["id"],)
    )

    usos_totais = int(cursor.fetchone()["total"])

    if (
        cupom["limite_total"] is not None
        and usos_totais >= int(cupom["limite_total"])
    ):
        raise ValueError(
            "Esse cupom atingiu o limite total de utilizações."
        )

    limite_cliente = cupom["limite_por_cliente"]

    if limite_cliente is not None:
        telefone_cliente = normalizar_telefone(telefone)

        cursor.execute(
            """
            SELECT p.telefone_cliente
            FROM cupom_usos cu
            JOIN pedidos p
                ON p.id = cu.pedido_id
            WHERE cu.cupom_id = %s
            """,
            (cupom["id"],)
        )

        usos_cliente = sum(
            1
            for linha in cursor.fetchall()
            if normalizar_telefone(
                linha["telefone_cliente"]
            ) == telefone_cliente
        )

        if usos_cliente >= int(limite_cliente):
            raise ValueError(
                "Você já utilizou esse cupom o máximo "
                "de vezes permitido."
            )

    desconto = calcular_desconto_cupom(
        cupom,
        subtotal
    )

    if desconto <= ZERO:
        raise ValueError(
            "Esse cupom não concede desconto para este pedido."
        )

    return cupom, desconto


# Valida o cupom antes de o cliente finalizar o pedido.
@orders_bp.post("/coupons/validate")
def validate_coupon():
    dados = request.get_json(silent=True)

    if not isinstance(dados, dict):
        return jsonify({
            "error": "Envie os dados do cupom em formato JSON."
        }), 400

    codigo = str(
        dados.get(
            "cupom_codigo",
            dados.get("cupom", "")
        ) or ""
    ).strip().upper()

    telefone = str(
        dados.get("telefone", "")
    ).strip()

    if not codigo:
        return jsonify({
            "error": "Digite o código do cupom."
        }), 400

    if len(codigo) > 30:
        return jsonify({
            "error": "O código do cupom é inválido."
        }), 400

    try:
        subtotal = dinheiro(dados.get("subtotal", 0))

    except (ValueError, TypeError, InvalidOperation):
        return jsonify({
            "error": "Subtotal inválido."
        }), 400

    if subtotal <= ZERO:
        return jsonify({
            "error": "O carrinho não possui um subtotal válido."
        }), 400

    conn = None
    cursor = None

    try:
        conn = get_connection()
        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)

        cupom, desconto = validar_cupom(
            cursor,
            codigo,
            telefone,
            subtotal
        )

        total_com_desconto = dinheiro(
            subtotal - desconto
        )

        resposta = {
            "valid": True,
            "cupom": cupom["codigo"],
            "desconto": str(desconto),
            "subtotal": str(subtotal),
            "total_com_desconto": str(total_com_desconto),
        }

        return jsonify(resposta), 200

    except ValueError as erro:
        return jsonify({
            "error": str(erro)
        }), 400

    except Exception:
        logging.exception(
            "Erro ao validar cupom da SALTY."
        )

        return jsonify({
            "error": "Não foi possível validar o cupom."
        }), 500

    finally:
        if conn is not None:
            try:
                conn.rollback()
            except Exception:
                pass

        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass

        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


# Lista os cupons ativos para exibição no site.
# Não retorna limites de utilização nem outros dados internos.
@orders_bp.get("/coupons")
def list_coupons():
    conn = None
    cursor = None

    try:
        conn = get_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                c.codigo,
                c.tipo,
                CAST(c.valor AS CHAR) AS valor,
                CAST(c.pedido_minimo AS CHAR) AS pedido_minimo,
                DATE_FORMAT(
                    c.fim_em,
                    '%Y-%m-%d %H:%i:%s'
                ) AS fim_em
            FROM cupons c
            WHERE c.ativo = 1
              AND (
                  c.inicio_em IS NULL
                  OR c.inicio_em <= NOW()
              )
              AND (
                  c.fim_em IS NULL
                  OR c.fim_em >= NOW()
              )
              AND (
                  c.limite_total IS NULL
                  OR (
                      SELECT COUNT(*)
                      FROM cupom_usos cu
                      WHERE cu.cupom_id = c.id
                  ) < c.limite_total
              )
            ORDER BY
                c.fim_em IS NULL,
                c.fim_em ASC
            """
        )

        return jsonify({
            "cupons": cursor.fetchall()
        }), 200

    except Exception:
        logging.exception(
            "Erro ao listar cupons disponíveis da SALTY."
        )

        return jsonify({
            "error": "Não foi possível carregar os cupons."
        }), 500

    finally:
        if cursor is not None:
            try:
                cursor.close()
            except Exception:
                pass

        if conn is not None:
            try:
                conn.close()
            except Exception:
                pass


@orders_bp.post("/orders")
def create_order():
    dados = request.get_json(silent=True)

    if not isinstance(dados, dict):
        return jsonify({
            "error": "Envie os dados do pedido em formato JSON."
        }), 400

    nome = str(dados.get("nome", "")).strip()
    telefone = str(dados.get("telefone", "")).strip()
    email = str(dados.get("email", "")).strip().lower()
    modalidade = dados.get("modalidade")
    itens = dados.get("itens")
    pagamento = dados.get("pagamento")
    chave = str(
        dados.get("chave_idempotencia", "")
    ).strip()
    observacoes = str(
        dados.get("observacoes", "")
    ).strip()
    cupom_codigo = str(
        dados.get("cupom_codigo", dados.get("cupom", "")) or ""
    ).strip()

    if not nome or len(nome) > 120:
        return jsonify({
            "error": "Informe um nome válido."
        }), 400

    if not telefone or len(telefone) > 20:
        return jsonify({
            "error": "Informe um telefone válido."
        }), 400

    if modalidade not in ("entrega", "retirada"):
        return jsonify({
            "error": "Escolha entrega ou retirada."
        }), 400
    if pagamento == "pix":
        if (
            not email
            or len(email) > 254
            or email.count("@") != 1
            or email.startswith("@")
            or email.endswith("@")
            or any(caractere.isspace() for caractere in email)
        ):
            return jsonify({
                "error": "Informe um e-mail válido para pagar com Pix."
            }), 400

    if pagamento not in (
        "pix",
        "dinheiro",
        "cartao_entrega"
    ):
        return jsonify({
            "error": "Escolha uma forma de pagamento válida."
        }), 400

    if (
        not isinstance(itens, list)
        or not itens
        or len(itens) > 100
    ):
        return jsonify({
            "error": "Confira os itens do carrinho."
        }), 400

    if len(observacoes) > 300:
        return jsonify({
            "error": "As observações são muito longas."
        }), 400

    if len(cupom_codigo) > 30:
        return jsonify({
            "error": "O código do cupom é inválido."
        }), 400

    try:
        chave = str(uuid.UUID(chave))

    except (ValueError, TypeError, AttributeError):
        return jsonify({
            "error": (
                "Identificador do pedido inválido. "
                "Tente novamente."
            )
        }), 400

    endereco = dados.get("endereco") or {}

    if not isinstance(endereco, dict):
        return jsonify({
            "error": "Confira o endereço informado."
        }), 400

    troco_para = None

    if (
        pagamento == "dinheiro"
        and dados.get("troco_para") not in (None, "")
    ):
        try:
            troco_para = dinheiro(
                dados["troco_para"]
            )

            if troco_para <= ZERO:
                raise ValueError()

        except (ValueError, InvalidOperation):
            return jsonify({
                "error": "Informe um valor de troco válido."
            }), 400

    conn = None
    cursor = None

    try:
        conn = get_connection()
        conn.start_transaction()
        cursor = conn.cursor(dictionary=True)

        # Evita duplicar um pedido em tentativas repetidas.
        cursor.execute(
            """
            SELECT id, numero, total, desconto
            FROM pedidos
            WHERE chave_idempotencia = %s
            """,
            (chave,)
        )

        existente = cursor.fetchone()

        if existente:
            conn.commit()

            return jsonify({
                "message": "Pedido já registrado.",
                "pedido": {
                    "id": existente["id"],
                    "numero": existente["numero"],
                    "total": str(existente["total"]),
                    "desconto": str(
                        existente.get("desconto") or ZERO
                    ),
                }
            }), 200

        config = obter_configuracoes(cursor)

        situacao_loja = obter_situacao(cursor)
        aberta = situacao_loja["aberta"]

        aceita_fechada = (
            str(
                config.get(
                    "aceita_pedido_fechada",
                    "false"
                )
            ).lower()
            == "true"
        )

        if not aberta and not aceita_fechada:
            conn.rollback()

            return jsonify({
                "error": (
                    "A SALTY está fechada e "
                    "não está aceitando pedidos."
                )
            }), 409

        try:
            formas = json.loads(
                config.get("formas_pagamento", "[]")
            )

        except (ValueError, TypeError):
            formas = []

        if pagamento not in formas:
            raise ValueError(
                "Essa forma de pagamento não está disponível."
            )

        pedido_minimo = dinheiro(
            config.get("pedido_minimo", "0")
        )

        subtotal = ZERO
        itens_validados = []

        for item in itens:
            if not isinstance(item, dict):
                raise ValueError(
                    "Um dos itens do pedido é inválido."
                )

            try:
                produto_id = int(item.get("produto_id"))
                quantidade = int(item.get("quantidade"))

            except (TypeError, ValueError):
                raise ValueError(
                    "Confira os produtos e as quantidades."
                )

            if (
                produto_id <= 0
                or not 1 <= quantidade <= 99
            ):
                raise ValueError(
                    "Confira os produtos e as quantidades."
                )

            opcoes = item.get("opcoes", [])

            if (
                not isinstance(opcoes, list)
                or len(opcoes) > 50
                or len(set(map(str, opcoes))) != len(opcoes)
            ):
                raise ValueError(
                    "As opções selecionadas são inválidas."
                )

            try:
                opcoes = [
                    int(opcao)
                    for opcao in opcoes
                ]

            except (TypeError, ValueError):
                raise ValueError(
                    "Uma opção selecionada é inválida."
                )

            cursor.execute(
                """
                SELECT
                    id,
                    nome,
                    preco,
                    preco_promocional
                FROM produtos
                WHERE id = %s
                  AND ativo = 1
                  AND disponivel = 1
                FOR UPDATE
                """,
                (produto_id,)
            )

            produto = cursor.fetchone()

            if not produto:
                raise ValueError(
                    "Um produto não está mais disponível. "
                    "Atualize o cardápio."
                )

            cursor.execute(
                """
                SELECT
                    g.id AS grupo_id,
                    g.nome AS grupo_nome,
                    g.minimo,
                    g.maximo,
                    o.id AS opcao_id,
                    o.nome AS opcao_nome,
                    o.preco_adicional
                FROM produto_grupos_opcoes pgo
                JOIN grupos_opcoes g
                    ON g.id = pgo.grupo_id
                LEFT JOIN opcoes o
                    ON o.grupo_id = g.id
                    AND o.disponivel = 1
                WHERE pgo.produto_id = %s
                  AND g.ativo = 1
                ORDER BY pgo.ordem, o.ordem, o.id
                """,
                (produto_id,)
            )

            linhas = cursor.fetchall()

            grupos = {}
            opcoes_validas = {}

            for linha in linhas:
                grupo_id = linha["grupo_id"]

                if grupo_id not in grupos:
                    grupos[grupo_id] = {
                        "nome": linha["grupo_nome"],
                        "minimo": linha["minimo"],
                        "maximo": linha["maximo"],
                    }

                if linha["opcao_id"] is not None:
                    opcoes_validas[
                        linha["opcao_id"]
                    ] = {
                        "grupo_id": grupo_id,
                        "grupo": linha["grupo_nome"],
                        "nome": linha["opcao_nome"],
                        "preco": dinheiro(
                            linha["preco_adicional"]
                        ),
                    }

            escolhidas = {
                grupo_id: []
                for grupo_id in grupos
            }

            adicionais = []
            adicional_total = ZERO

            for opcao_id in opcoes:
                opcao = opcoes_validas.get(opcao_id)

                if not opcao:
                    raise ValueError(
                        "Uma opção não pertence a esse produto "
                        "ou não está disponível."
                    )

                escolhidas[
                    opcao["grupo_id"]
                ].append(opcao_id)

                adicionais.append({
                    "id": opcao_id,
                    "grupo": opcao["grupo"],
                    "nome": opcao["nome"],
                    "preco": opcao["preco"],
                })

                adicional_total += opcao["preco"]

            for grupo_id, grupo in grupos.items():
                total_opcoes = len(
                    escolhidas[grupo_id]
                )

                if not (
                    grupo["minimo"]
                    <= total_opcoes
                    <= grupo["maximo"]
                ):
                    raise ValueError(
                        f"Confira as opções do grupo "
                        f"{grupo['nome']}."
                    )

            preco_normal = dinheiro(produto["preco"])
            promocional = produto.get(
                "preco_promocional"
            )

            if promocional is not None:
                promocional = dinheiro(promocional)
            else:
                promocional = ZERO

            if ZERO < promocional < preco_normal:
                preco_base = promocional
            else:
                preco_base = preco_normal

            preco_unitario = (
                preco_base + adicional_total
            )

            subtotal_item = dinheiro(
                preco_unitario * quantidade
            )

            subtotal += subtotal_item

            nota = str(
                item.get("observacao", "")
            ).strip()

            if len(nota) > 140:
                raise ValueError(
                    "A observação de um produto é muito longa."
                )

            itens_validados.append({
                "produto_id": produto_id,
                "nome": produto["nome"],
                "preco_unitario": preco_unitario,
                "quantidade": quantidade,
                "observacao": nota,
                "subtotal": subtotal_item,
                "opcoes": adicionais,
            })

        subtotal = dinheiro(subtotal)

        if subtotal < pedido_minimo:
            raise ValueError(
                f"O pedido mínimo é de R$ {pedido_minimo:.2f}."
            )

        taxa_entrega = ZERO

        endereco_salvo = {
            "entrega_cep": None,
            "entrega_rua": None,
            "entrega_numero": None,
            "entrega_complemento": None,
            "entrega_bairro": None,
            "entrega_cidade": None,
            "entrega_uf": None,
            "entrega_referencia": None,
        }

        if modalidade == "entrega":
            campos = {
                "cep": 8,
                "rua": 150,
                "numero": 15,
                "complemento": 80,
                "bairro": 80,
                "cidade": 80,
                "uf": 2,
                "referencia": 150,
            }

            endereco_limpo = {
                campo: str(
                    endereco.get(campo, "")
                ).strip()
                for campo in campos
            }

            cep = "".join(
                caractere
                for caractere in endereco_limpo["cep"]
                if caractere.isdigit()
            )

            endereco_limpo["cep"] = cep

            obrigatorios = (
                "rua",
                "numero",
                "bairro",
                "cidade",
                "uf",
            )

            if (
                len(cep) != 8
                or any(
                    not endereco_limpo[campo]
                    for campo in obrigatorios
                )
                or len(endereco_limpo["uf"]) != 2
            ):
                raise ValueError(
                    "Preencha CEP, rua, número, bairro, cidade e UF."
                )

            for campo, limite in campos.items():
                if len(endereco_limpo[campo]) > limite:
                    raise ValueError(
                        f"O campo {campo} excede "
                        "o tamanho permitido."
                    )

            cidade = endereco_limpo["cidade"].strip()
            uf = endereco_limpo["uf"].strip().upper()

            if (
                cidade.casefold() != "vassouras"
                or uf != "RJ"
            ):
                raise ValueError(
                    "No momento, a SALTY entrega "
                    "somente em Vassouras, RJ."
                )

            taxa_entrega = dinheiro(
                config.get(
                    "taxa_entrega_padrao",
                    "7.00"
                )
            )

            if taxa_entrega < ZERO:
                raise ValueError(
                    "A taxa de entrega configurada é inválida."
                )

            endereco_salvo = {
                "entrega_cep": cep,
                "entrega_rua": endereco_limpo["rua"],
                "entrega_numero": endereco_limpo["numero"],
                "entrega_complemento": (
                    endereco_limpo["complemento"] or None
                ),
                "entrega_bairro": endereco_limpo["bairro"],
                "entrega_cidade": cidade,
                "entrega_uf": uf,
                "entrega_referencia": (
                    endereco_limpo["referencia"] or None
                ),
            }

        # O cupom também é validado novamente na finalização.
        cupom, desconto = validar_cupom(
            cursor,
            cupom_codigo,
            telefone,
            subtotal
        )

        total = dinheiro(
            subtotal + taxa_entrega - desconto
        )

        if total < ZERO:
            total = ZERO

        if (
            troco_para is not None
            and troco_para < total
        ):
            raise ValueError(
                "O valor informado para o troco "
                "precisa cobrir o total."
            )

        numero = criar_numero_pedido(cursor)

        cursor.execute(
            """
            INSERT INTO pedidos (
                numero,
                chave_idempotencia,
                cupom_id,
                nome_cliente,
                telefone_cliente,
                email_cliente,
                modalidade,
                entrega_cep,
                entrega_rua,
                entrega_numero,
                entrega_complemento,
                entrega_bairro,
                entrega_cidade,
                entrega_uf,
                entrega_referencia,
                status,
                subtotal,
                taxa_entrega,
                desconto,
                total,
                observacoes
            )
            VALUES (
                %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s,
                'recebido', %s, %s, %s, %s, %s
            )
            """,
            (
                numero,
                chave,
                cupom["id"] if cupom else None,
                nome,
                telefone,
                email or None,
                modalidade,
                endereco_salvo["entrega_cep"],
                endereco_salvo["entrega_rua"],
                endereco_salvo["entrega_numero"],
                endereco_salvo["entrega_complemento"],
                endereco_salvo["entrega_bairro"],
                endereco_salvo["entrega_cidade"],
                endereco_salvo["entrega_uf"],
                endereco_salvo["entrega_referencia"],
                subtotal,
                taxa_entrega,
                desconto,
                total,
                observacoes or None,
            )
        )

        pedido_id = cursor.lastrowid

        for item in itens_validados:
            cursor.execute(
                """
                INSERT INTO itens_pedido (
                    pedido_id,
                    produto_id,
                    nome_produto,
                    preco_unitario,
                    quantidade,
                    observacao,
                    subtotal
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s)
                """,
                (
                    pedido_id,
                    item["produto_id"],
                    item["nome"],
                    item["preco_unitario"],
                    item["quantidade"],
                    item["observacao"] or None,
                    item["subtotal"],
                )
            )

            item_id = cursor.lastrowid

            for opcao in item["opcoes"]:
                cursor.execute(
                    """
                    INSERT INTO itens_pedido_opcoes (
                        item_pedido_id,
                        opcao_id,
                        nome_grupo,
                        nome_opcao,
                        preco_adicional
                    )
                    VALUES (%s, %s, %s, %s, %s)
                    """,
                    (
                        item_id,
                        opcao["id"],
                        opcao["grupo"],
                        opcao["nome"],
                        opcao["preco"],
                    )
                )

        if cupom:
            cursor.execute(
                """
                INSERT INTO cupom_usos (
                    cupom_id,
                    pedido_id,
                    usuario_id,
                    valor_desconto
                )
                VALUES (%s, %s, NULL, %s)
                """,
                (
                    cupom["id"],
                    pedido_id,
                    desconto,
                )
            )

        cursor.execute(
            """
            INSERT INTO pagamentos (
                pedido_id,
                forma,
                valor,
                troco_para,
                status
            )
            VALUES (%s, %s, %s, %s, 'pendente')
            """,
            (
                pedido_id,
                pagamento,
                total,
                troco_para,
            )
        )

        cursor.execute(
            """
            INSERT INTO historico_status_pedido (
                pedido_id,
                status_anterior,
                status_novo,
                motivo
            )
            VALUES (%s, NULL, 'recebido', %s)
            """,
            (
                pedido_id,
                "Pedido criado pelo site.",
            )
        )

        conn.commit()

        return jsonify({
            "message": "Pedido registrado com sucesso!",
            "pedido": {
                "id": pedido_id,
                "numero": numero,
                "subtotal": str(subtotal),
                "taxa_entrega": str(taxa_entrega),
                "desconto": str(desconto),
                "total": str(total),
                "cupom": cupom["codigo"] if cupom else None,
                "status": "recebido",
            }
        }), 201

    except ValueError as erro:
        if conn and conn.is_connected():
            conn.rollback()

        return jsonify({
            "error": str(erro)
        }), 400

    except Exception:
        if conn and conn.is_connected():
            conn.rollback()

        logging.exception(
            "Erro ao registrar pedido na SALTY."
        )

        return jsonify({
            "error": (
                "Não foi possível registrar o pedido. "
                "Tente novamente."
            )
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conn and conn.is_connected():
            conn.close()
