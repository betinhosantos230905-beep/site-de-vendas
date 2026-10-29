
import hmac
import os

import cloudinary.utils
from functools import wraps
from datetime import datetime, date, time, timedelta, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request, session

from backend.database import get_connection
from backend.routes.funcionamento import (
    MODOS_LOJA,
    obter_situacao,
    salvar_dias,
    salvar_modo,
    validar_dias,
)


admin_bp = Blueprint("admin", __name__)

STATUS_VALIDOS = {
    "recebido",
    "confirmado",
    "em_preparo",
    "pronto_retirada",
    "saiu_entrega",
    "entregue",
    "cancelado",
}


def agora_brasil():
    try:
        return datetime.now(ZoneInfo("America/Sao_Paulo"))
    except ZoneInfoNotFoundError:
        # Windows sem o pacote tzdata: usa UTC-3 (Brasil sem horário de verão)
        return datetime.now(timezone(timedelta(hours=-3)))


def serializar_registro(registro):
    """Converte datas e Decimal para tipos que o JSON entende."""
    for chave, valor in registro.items():
        if isinstance(valor, datetime):
            registro[chave] = valor.isoformat(sep=" ", timespec="seconds")
        elif isinstance(valor, date):
            registro[chave] = valor.isoformat()
        elif isinstance(valor, Decimal):
            registro[chave] = float(valor)

    return registro


# ==========================================
# AUTENTICAÇÃO DO ADMINISTRADOR
# ==========================================

def exigir_login_admin(funcao):
    @wraps(funcao)
    def verificar_login(*args, **kwargs):
        if not session.get("admin_logado"):
            return jsonify({
                "error": "Acesso restrito ao administrador."
            }), 401

        return funcao(*args, **kwargs)

    return verificar_login


@admin_bp.post("/login")
def login_admin():
    dados = request.get_json(silent=True) or {}

    senha = dados.get("senha", "")
    senha_correta = os.getenv("SALTY_ADMIN_PASSWORD", "").strip()

    if not senha_correta:
        return jsonify({
            "error": "Senha administrativa não configurada."
        }), 500

    if not isinstance(senha, str) or not hmac.compare_digest(
        senha.encode("utf-8"),
        senha_correta.encode("utf-8")
    ):
        return jsonify({
            "error": "Senha incorreta."
        }), 401

    session.clear()
    session["admin_logado"] = True

    return jsonify({
        "message": "Login realizado com sucesso."
    }), 200


@admin_bp.post("/logout")
def logout_admin():
    session.clear()

    return jsonify({
        "message": "Sessão encerrada."
    }), 200


@admin_bp.get("/sessao")
def verificar_sessao_admin():
    return jsonify({
        "autenticado": bool(session.get("admin_logado"))
    }), 200


# ==========================================
# ASSINATURA SEGURA PARA UPLOAD DE IMAGENS
# ==========================================

@admin_bp.post("/produtos/upload-assinatura")
@exigir_login_admin
def assinar_upload_imagem_produto():
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME", "").strip()
    api_key = os.getenv("CLOUDINARY_API_KEY", "").strip()
    api_secret = os.getenv("CLOUDINARY_API_SECRET", "").strip()

    if not cloud_name or not api_key or not api_secret:
        return jsonify({
            "error": "Configuracao do armazenamento de imagens incompleta."
        }), 500

    timestamp = int(datetime.now(timezone.utc).timestamp())
    parametros = {
        "timestamp": timestamp,
        "folder": "salty/produtos",
    }

    try:
        assinatura = cloudinary.utils.api_sign_request(
            parametros,
            api_secret,
        )
    except Exception:
        return jsonify({
            "error": "Nao foi possivel preparar o envio da imagem."
        }), 500

    return jsonify({
        **parametros,
        "signature": assinatura,
        "api_key": api_key,
        "cloud_name": cloud_name,
    }), 200


# ==========================================
# GERENCIAMENTO DE PEDIDOS
# ==========================================

@admin_bp.get("/pedidos")
@exigir_login_admin
def listar_pedidos():
    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id,
                numero,
                nome_cliente,
                telefone_cliente,
                modalidade,
                status,
                subtotal,
                taxa_entrega,
                desconto,
                total,
                criado_em
            FROM pedidos
            ORDER BY criado_em DESC
            LIMIT 100
        """)

        pedidos = [serializar_registro(p) for p in cursor.fetchall()]

        return jsonify({
            "pedidos": pedidos
        }), 200

    except Exception:
        return jsonify({
            "error": "Não foi possível consultar os pedidos."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()


@admin_bp.get("/pedidos/<int:pedido_id>")
@exigir_login_admin
def detalhar_pedido(pedido_id):
    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT *
            FROM pedidos
            WHERE id = %s
        """, (pedido_id,))

        pedido = cursor.fetchone()

        if not pedido:
            return jsonify({
                "error": "Pedido não encontrado."
            }), 404

        cursor.execute("""
            SELECT
                id,
                produto_id,
                nome_produto,
                preco_unitario,
                quantidade,
                observacao,
                subtotal
            FROM itens_pedido
            WHERE pedido_id = %s
            ORDER BY id
        """, (pedido_id,))

        itens = [serializar_registro(i) for i in cursor.fetchall()]

        for item in itens:
            cursor.execute("""
                SELECT
                    nome_grupo,
                    nome_opcao,
                    preco_adicional
                FROM itens_pedido_opcoes
                WHERE item_pedido_id = %s
                ORDER BY id
            """, (item["id"],))

            item["opcoes"] = [
                serializar_registro(o) for o in cursor.fetchall()
            ]

        cursor.execute("""
            SELECT
                forma,
                valor,
                troco_para,
                status,
                pago_em
            FROM pagamentos
            WHERE pedido_id = %s
            ORDER BY id DESC
        """, (pedido_id,))

        pagamentos = [serializar_registro(p) for p in cursor.fetchall()]

        pedido["itens"] = itens
        pedido["pagamentos"] = pagamentos
        serializar_registro(pedido)

        return jsonify({
            "pedido": pedido
        }), 200

    except Exception:
        return jsonify({
            "error": "Não foi possível consultar os detalhes do pedido."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()


@admin_bp.patch("/pedidos/<int:pedido_id>/status")
@exigir_login_admin
def atualizar_status_pedido(pedido_id):
    dados = request.get_json(silent=True) or {}
    novo_status = dados.get("status")

    if (
        not isinstance(novo_status, str)
        or novo_status not in STATUS_VALIDOS
    ):
        return jsonify({
            "error": "Status inválido."
        }), 400

    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor(dictionary=True)

        conexao.start_transaction()

        cursor.execute("""
            SELECT status
            FROM pedidos
            WHERE id = %s
            FOR UPDATE
        """, (pedido_id,))

        pedido = cursor.fetchone()

        if not pedido:
            conexao.rollback()

            return jsonify({
                "error": "Pedido não encontrado."
            }), 404

        status_anterior = pedido["status"]

        if status_anterior == novo_status:
            conexao.commit()

            return jsonify({
                "message": "O pedido já está nesse status.",
                "status": novo_status,
            }), 200

        cursor.execute("""
            UPDATE pedidos
            SET status = %s
            WHERE id = %s
        """, (novo_status, pedido_id))

        cursor.execute("""
            INSERT INTO historico_status_pedido (
                pedido_id,
                status_anterior,
                status_novo
            )
            VALUES (%s, %s, %s)
        """, (pedido_id, status_anterior, novo_status))

        # Ao entregar o pedido, confirmar o pagamento.
        if novo_status == "entregue":
            data_pagamento = agora_brasil()

            cursor.execute("""
                UPDATE pagamentos
                SET
                    pago_em = COALESCE(pago_em, %s),
                    status = 'pago'
                WHERE pedido_id = %s
                  AND status = 'pendente'
            """, (data_pagamento, pedido_id))

        conexao.commit()

        return jsonify({
            "message": "Status atualizado com sucesso.",
            "status_anterior": status_anterior,
            "status": novo_status,
        }), 200

    except Exception:
        if conexao:
            conexao.rollback()

        return jsonify({
            "error": "Não foi possível atualizar o status do pedido."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()


# ==========================================

# ==========================================
# FATURAMENTO
# Considera somente pagamentos confirmados
# ==========================================

@admin_bp.get("/faturamento")
@exigir_login_admin
def consultar_faturamento_admin():
    periodo = (
        request.args.get("periodo", "todo_periodo").strip()
    )

    descricoes_periodo = {
        "todo_periodo": "Todo o período",
        "hoje": "Hoje",
        "ontem": "Ontem",
        "ultimos_7_dias": "Últimos 7 dias",
        "ultimos_30_dias": "Últimos 30 dias",
        "mes_atual": "Mês atual",
        "mes_anterior": "Mês anterior",
        "ano_atual": "Ano atual",
        "personalizado": "Período personalizado",
    }

    if periodo not in descricoes_periodo:
        return jsonify({
            "error": "O período informado é inválido."
        }), 400

    inicio = None
    fim = None

    hoje = agora_brasil().date()

    if periodo == "hoje":
        inicio = datetime.combine(hoje, time.min)
        fim = inicio + timedelta(days=1)

    elif periodo == "ontem":
        ontem = hoje - timedelta(days=1)
        inicio = datetime.combine(ontem, time.min)
        fim = inicio + timedelta(days=1)

    elif periodo == "ultimos_7_dias":
        inicio = datetime.combine(
            hoje - timedelta(days=6),
            time.min
        )
        fim = datetime.combine(
            hoje + timedelta(days=1),
            time.min
        )

    elif periodo == "ultimos_30_dias":
        inicio = datetime.combine(
            hoje - timedelta(days=29),
            time.min
        )
        fim = datetime.combine(
            hoje + timedelta(days=1),
            time.min
        )

    elif periodo == "mes_atual":
        inicio = datetime(hoje.year, hoje.month, 1)

        if hoje.month == 12:
            proximo_mes = date(hoje.year + 1, 1, 1)
        else:
            proximo_mes = date(
                hoje.year,
                hoje.month + 1,
                1
            )

        fim = datetime.combine(proximo_mes, time.min)

    elif periodo == "mes_anterior":
        primeiro_deste_mes = date(
            hoje.year,
            hoje.month,
            1
        )

        ultimo_mes = primeiro_deste_mes - timedelta(days=1)

        inicio = datetime(
            ultimo_mes.year,
            ultimo_mes.month,
            1
        )

        fim = datetime.combine(
            primeiro_deste_mes,
            time.min
        )

    elif periodo == "ano_atual":
        inicio = datetime(hoje.year, 1, 1)
        fim = datetime(hoje.year + 1, 1, 1)

    elif periodo == "personalizado":
        try:
            data_inicial = date.fromisoformat(
                request.args.get(
                    "data_inicial", ""
                ).strip()
            )

            data_final = date.fromisoformat(
                request.args.get(
                    "data_final", ""
                ).strip()
            )

            if data_final < data_inicial:
                raise ValueError

            inicio = datetime.combine(
                data_inicial,
                time.min
            )

            fim = datetime.combine(
                data_final + timedelta(days=1),
                time.min
            )

        except (ValueError, TypeError, OverflowError):
            return jsonify({
                "error": (
                    "Informe datas válidas. "
                    "A data final não pode ser anterior "
                    "à data inicial."
                )
            }), 400

    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor(dictionary=True)

        sql = """
            SELECT
                pg.id AS id,
                pg.id AS pagamento_id,
                pg.pedido_id,
                pe.numero AS numero_pedido,
                pe.nome_cliente,
                pg.forma,
                pg.valor,
                pg.status,
                pg.pago_em
            FROM pagamentos AS pg
            INNER JOIN pedidos AS pe
                ON pe.id = pg.pedido_id
            WHERE pg.status = 'pago'
              AND pg.pago_em IS NOT NULL
        """

        parametros = []

        if inicio is not None and fim is not None:
            sql += """
                AND pg.pago_em >= %s
                AND pg.pago_em < %s
            """

            parametros.extend([inicio, fim])

        sql += """
            ORDER BY pg.pago_em DESC, pg.id DESC
        """

        cursor.execute(sql, tuple(parametros))
        registros = cursor.fetchall()

        pagamentos = []
        total = Decimal("0.00")

        for registro in registros:
            valor = Decimal(str(registro["valor"]))
            total += valor

            pago_em = registro["pago_em"]

            pagamentos.append({
                "id": int(registro["id"]),
                "pagamento_id": int(
                    registro["pagamento_id"]
                ),
                "pedido_id": int(registro["pedido_id"]),
                "numero_pedido": registro["numero_pedido"],
                "nome_cliente": registro["nome_cliente"],
                "forma": registro["forma"],
                "valor": float(valor),
                "status": registro["status"],
                "pago_em": (
                    pago_em.isoformat(
                        sep=" ",
                        timespec="seconds"
                    )
                    if pago_em
                    else None
                ),
            })

        quantidade = len(pagamentos)

        ticket_medio = (
            total / quantidade
            if quantidade > 0
            else Decimal("0.00")
        )

        return jsonify({
            "periodo": periodo,
            "periodo_descricao": descricoes_periodo[periodo],
            "data_inicial": (
                inicio.date().isoformat()
                if inicio is not None
                else None
            ),
            "data_final": (
                (fim - timedelta(days=1)).date().isoformat()
                if fim is not None
                else None
            ),
            "total": float(total),
            "quantidade": quantidade,
            "ticket_medio": float(
                ticket_medio.quantize(Decimal("0.01"))
            ),
            "pagamentos": pagamentos,
        }), 200

    except Exception:
        return jsonify({
            "error": "Não foi possível consultar o faturamento."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()

# ==========================================
# GERENCIAMENTO DE CATEGORIAS
# ==========================================

def categoria_existe(cursor, categoria_id):
    cursor.execute("""
        SELECT id
        FROM categorias
        WHERE id = %s AND ativo = 1
    """, (categoria_id,))

    return cursor.fetchone() is not None


@admin_bp.get("/categorias")
@exigir_login_admin
def listar_categorias_admin():
    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id,
                nome AS name,
                descricao AS description,
                imagem_url AS image_url,
                ordem AS `order`,
                ativo AS active
            FROM categorias
            ORDER BY ordem, nome
        """)

        categorias = cursor.fetchall()

        for categoria in categorias:
            categoria["id"] = int(categoria["id"])
            categoria["order"] = int(categoria["order"])
            categoria["active"] = bool(categoria["active"])

        return jsonify({
            "data": categorias
        }), 200

    except Exception:
        return jsonify({
            "error": "Não foi possível carregar as categorias."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()


# ==========================================
# CADASTRAR CATEGORIA
# ==========================================

@admin_bp.post("/categorias")
@exigir_login_admin
def cadastrar_categoria_admin():
    dados = request.get_json(silent=True) or {}

    nome = str(dados.get("name") or "").strip()
    descricao = str(dados.get("description") or "").strip()
    imagem_url = str(dados.get("image_url") or "").strip()

    try:
        ordem_recebida = dados.get("order", 0)

        if isinstance(ordem_recebida, bool):
            raise ValueError

        ordem = int(ordem_recebida)

    except (TypeError, ValueError, OverflowError):
        return jsonify({
            "error": "Informe uma ordem válida."
        }), 400

    ativo = dados.get("active", True)

    if not isinstance(ativo, bool):
        return jsonify({
            "error": "O campo active deve ser verdadeiro ou falso."
        }), 400

    if not nome or len(nome) > 60:
        return jsonify({
            "error": "O nome deve ter entre 1 e 60 caracteres."
        }), 400

    if len(descricao) > 200:
        return jsonify({
            "error": "A descrição pode ter até 200 caracteres."
        }), 400

    if len(imagem_url) > 255:
        return jsonify({
            "error": "O endereço da imagem pode ter até 255 caracteres."
        }), 400

    if ordem < 0 or ordem > 65535:
        return jsonify({
            "error": "A ordem deve estar entre 0 e 65535."
        }), 400

    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor()

        cursor.execute("""
            INSERT INTO categorias (
                nome,
                descricao,
                imagem_url,
                ordem,
                ativo
            )
            VALUES (%s, %s, %s, %s, %s)
        """, (
            nome,
            descricao or None,
            imagem_url or None,
            ordem,
            ativo
        ))

        categoria_id = cursor.lastrowid
        conexao.commit()

        return jsonify({
            "message": "Categoria cadastrada com sucesso.",
            "id": categoria_id
        }), 201

    except Exception as erro:
        if conexao:
            conexao.rollback()

        if getattr(erro, "errno", None) == 1062:
            return jsonify({
                "error": "Já existe uma categoria com esse nome."
            }), 409

        return jsonify({
            "error": "Não foi possível cadastrar a categoria."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()


# ==========================================
# VALIDAÇÃO DOS PRODUTOS
# ==========================================

def validar_dados_produto(dados):
    if not isinstance(dados, dict):
        return None, "Dados do produto inválidos."

    nome = str(dados.get("name", "")).strip()
    descricao = str(dados.get("description") or "").strip()
    imagem_url = str(dados.get("image_url") or "").strip()

    try:
        categoria_id = int(dados.get("category_id"))
        preco = Decimal(str(dados.get("price")))
    except (TypeError, ValueError, InvalidOperation):
        return None, "Informe uma categoria e um preço válidos."

    if not nome or len(nome) > 100:
        return None, "O nome deve ter entre 1 e 100 caracteres."

    if len(descricao) > 300:
        return None, "A descrição pode ter até 300 caracteres."

    if len(imagem_url) > 255:
        return None, "O endereço da imagem é muito longo."

    if categoria_id <= 0:
        return None, "Selecione uma categoria válida."

    if (
        not preco.is_finite()
        or preco < 0
        or preco > Decimal("99999999.99")
    ):
        return None, "Informe um preço válido."

    preco_promocional_texto = dados.get("promo_price")

    if preco_promocional_texto in (None, ""):
        preco_promocional = None
    else:
        try:
            preco_promocional = Decimal(
                str(preco_promocional_texto)
            )
        except (TypeError, ValueError, InvalidOperation):
            return None, "Informe um preço promocional válido."

        if (
            not preco_promocional.is_finite()
            or preco_promocional <= 0
            or preco_promocional > Decimal("99999999.99")
        ):
            return None, (
                "O preço promocional deve ser maior que zero "
                "e não pode ultrapassar o limite permitido."
            )

        if preco_promocional >= preco:
            return None, (
                "O preço promocional deve ser menor que o preço normal."
            )

    tempo = dados.get("prep_minutes")

    if tempo in ("", None):
        tempo = None
    else:
        try:
            tempo = int(tempo)
        except (TypeError, ValueError):
            return None, "O tempo de preparo deve ser um número inteiro."

        if tempo < 0 or tempo > 65535:
            return None, "O tempo de preparo informado é inválido."

    disponivel = dados.get("available", True)
    destaque = dados.get("featured", False)

    if not isinstance(disponivel, bool):
        return None, "A disponibilidade deve ser verdadeira ou falsa."

    if not isinstance(destaque, bool):
        return None, "O destaque deve ser verdadeiro ou falso."

    produto = {
        "category_id": categoria_id,
        "name": nome,
        "description": descricao or None,
        "price": preco,
        "promo_price": preco_promocional,
        "image_url": imagem_url or None,
        "available": disponivel,
        "featured": destaque,
        "prep_minutes": tempo,
    }

    return produto, None


# ==========================================
# LISTAR PRODUTOS
# ==========================================

@admin_bp.get("/produtos")
@exigir_login_admin
def listar_produtos_admin():
    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                p.id,
                p.categoria_id AS category_id,
                c.nome AS category_name,
                p.nome AS name,
                p.descricao AS description,
                p.preco AS price,
                p.preco_promocional AS promo_price,
                p.imagem_url AS image_url,
                p.disponivel AS available,
                p.destaque AS featured,
                p.tempo_preparo_min AS prep_minutes,
                p.ativo AS active
            FROM produtos AS p
            LEFT JOIN categorias AS c
                ON c.id = p.categoria_id
            ORDER BY p.ativo DESC, p.nome
        """)

        produtos = cursor.fetchall()

        for produto in produtos:
            produto["id"] = int(produto["id"])

            if produto["category_id"] is not None:
                produto["category_id"] = int(
                    produto["category_id"]
                )

            produto["price"] = float(produto["price"])

            if produto["promo_price"] is not None:
                produto["promo_price"] = float(
                    produto["promo_price"]
                )

            produto["available"] = bool(produto["available"])
            produto["featured"] = bool(produto["featured"])
            produto["active"] = bool(produto["active"])

            if produto["prep_minutes"] is not None:
                produto["prep_minutes"] = int(
                    produto["prep_minutes"]
                )

        return jsonify({
            "data": produtos
        }), 200

    except Exception:
        return jsonify({
            "error": "Não foi possível carregar os produtos."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()


# ==========================================
# CADASTRAR PRODUTO
# ==========================================

@admin_bp.post("/produtos")
@exigir_login_admin
def cadastrar_produto_admin():
    dados = request.get_json(silent=True) or {}
    produto, erro = validar_dados_produto(dados)

    if erro:
        return jsonify({
            "error": erro
        }), 400

    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor()

        if not categoria_existe(cursor, produto["category_id"]):
            return jsonify({
                "error": (
                    "A categoria selecionada não existe ou está inativa."
                )
            }), 400

        cursor.execute("""
            INSERT INTO produtos (
                categoria_id,
                nome,
                descricao,
                preco,
                preco_promocional,
                imagem_url,
                disponivel,
                destaque,
                tempo_preparo_min,
                ativo
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 1)
        """, (
            produto["category_id"],
            produto["name"],
            produto["description"],
            produto["price"],
            produto["promo_price"],
            produto["image_url"],
            produto["available"],
            produto["featured"],
            produto["prep_minutes"],
        ))

        produto_id = cursor.lastrowid
        conexao.commit()

        return jsonify({
            "message": "Produto cadastrado com sucesso.",
            "id": produto_id
        }), 201

    except Exception:
        if conexao:
            conexao.rollback()

        return jsonify({
            "error": "Não foi possível cadastrar o produto."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()


# ==========================================
# EDITAR PRODUTO
# ==========================================

@admin_bp.patch("/produtos/<int:produto_id>")
@exigir_login_admin
def editar_produto_admin(produto_id):
    dados = request.get_json(silent=True) or {}
    produto, erro = validar_dados_produto(dados)

    if erro:
        return jsonify({
            "error": erro
        }), 400

    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor()

        if not categoria_existe(cursor, produto["category_id"]):
            return jsonify({
                "error": (
                    "A categoria selecionada não existe ou está inativa."
                )
            }), 400

        cursor.execute("""
            UPDATE produtos
            SET
                categoria_id = %s,
                nome = %s,
                descricao = %s,
                preco = %s,
                preco_promocional = %s,
                imagem_url = %s,
                disponivel = %s,
                destaque = %s,
                tempo_preparo_min = %s
            WHERE id = %s AND ativo = 1
        """, (
            produto["category_id"],
            produto["name"],
            produto["description"],
            produto["price"],
            produto["promo_price"],
            produto["image_url"],
            produto["available"],
            produto["featured"],
            produto["prep_minutes"],
            produto_id,
        ))

        if cursor.rowcount == 0:
            cursor.execute("""
                SELECT id
                FROM produtos
                WHERE id = %s AND ativo = 1
            """, (produto_id,))

            if not cursor.fetchone():
                return jsonify({
                    "error": "Produto não encontrado ou inativo."
                }), 404

        conexao.commit()

        return jsonify({
            "message": "Produto atualizado com sucesso."
        }), 200

    except Exception:
        if conexao:
            conexao.rollback()

        return jsonify({
            "error": "Não foi possível atualizar o produto."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()


# ==========================================
# DUPLICAR PRODUTO
# ==========================================

@admin_bp.post("/produtos/<int:produto_id>/duplicar")
@exigir_login_admin
def duplicar_produto_admin(produto_id):
    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor()

        cursor.execute("""
            INSERT INTO produtos (
                categoria_id,
                nome,
                descricao,
                preco,
                preco_promocional,
                imagem_url,
                disponivel,
                destaque,
                tempo_preparo_min,
                ativo
            )
            SELECT
                categoria_id,
                CONCAT(LEFT(nome, 90), ' (cópia)'),
                descricao,
                preco,
                NULL,
                imagem_url,
                disponivel,
                0,
                tempo_preparo_min,
                1
            FROM produtos
            WHERE id = %s AND ativo = 1
        """, (produto_id,))

        if cursor.rowcount == 0:
            return jsonify({
                "error": "Produto não encontrado ou inativo."
            }), 404

        novo_id = cursor.lastrowid
        conexao.commit()

        return jsonify({
            "message": "Produto duplicado com sucesso.",
            "id": novo_id
        }), 201

    except Exception:
        if conexao:
            conexao.rollback()

        return jsonify({
            "error": "Não foi possível duplicar o produto."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()


# ==========================================
# ATIVAR OU DESATIVAR PRODUTO
# ==========================================

@admin_bp.patch("/produtos/<int:produto_id>/ativo")
@exigir_login_admin
def alterar_ativo_produto_admin(produto_id):
    dados = request.get_json(silent=True) or {}
    ativo = dados.get("active")

    if not isinstance(ativo, bool):
        return jsonify({
            "error": "Informe active como verdadeiro ou falso."
        }), 400

    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor()

        cursor.execute("""
            UPDATE produtos
            SET ativo = %s
            WHERE id = %s
        """, (ativo, produto_id))

        if cursor.rowcount == 0:
            cursor.execute("""
                SELECT id
                FROM produtos
                WHERE id = %s
            """, (produto_id,))

            if not cursor.fetchone():
                return jsonify({
                    "error": "Produto não encontrado."
                }), 404

        conexao.commit()

        mensagem = (
            "Produto ativado com sucesso."
            if ativo
            else "Produto desativado com sucesso."
        )

        return jsonify({
            "message": mensagem
        }), 200

    except Exception:
        if conexao:
            conexao.rollback()

        return jsonify({
            "error": "Não foi possível alterar o produto."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()


# ==========================================
# VALIDAÇÃO DOS CUPONS
# ==========================================

def validar_dados_cupom(dados):
    if not isinstance(dados, dict):
        return None, "Dados do cupom inválidos."

    codigo = str(dados.get("codigo") or "").strip().upper()
    tipo = dados.get("tipo")

    if not codigo or len(codigo) > 30:
        return None, "O código deve ter entre 1 e 30 caracteres."

    if tipo not in ("percentual", "valor_fixo"):
        return None, "Selecione um tipo de desconto válido."

    try:
        valor = Decimal(str(dados.get("valor")))
        pedido_minimo = Decimal(
            str(dados.get("pedido_minimo", 0))
        )
    except (InvalidOperation, TypeError, ValueError):
        return None, (
            "Informe valores válidos para o desconto e pedido mínimo."
        )

    if not valor.is_finite() or valor <= 0:
        return None, "O desconto deve ser maior que zero."

    if tipo == "percentual" and valor > 100:
        return None, "O desconto percentual não pode passar de 100%."

    if (
        tipo == "valor_fixo"
        and valor > Decimal("99999999.99")
    ):
        return None, "O valor do desconto é muito alto."

    if (
        not pedido_minimo.is_finite()
        or pedido_minimo < 0
        or pedido_minimo > Decimal("99999999.99")
    ):
        return None, "O pedido mínimo informado é inválido."

    def converter_data(campo):
        texto = dados.get(campo)

        if texto in (None, ""):
            return None

        if not isinstance(texto, str):
            raise ValueError

        data_convertida = datetime.fromisoformat(
            texto.replace("Z", "+00:00")).replace(tzinfo=None)

        # Quando o campo contém apenas a data, considerar
        # o último segundo desse dia como validade final.
        if campo == "fim_em" and len(texto) == 10:
            data_convertida = data_convertida.replace(
                hour=23,
                minute=59,
                second=59,
                microsecond=0
    )

        return data_convertida

    try:
        inicio_em = converter_data("inicio_em")
        fim_em = converter_data("fim_em")
    except (ValueError, TypeError):
        return None, "Informe datas de validade válidas."

    if inicio_em and fim_em and fim_em < inicio_em:
        return None, "A data final deve ser posterior à data inicial."

    def converter_limite(campo):
        valor_limite = dados.get(campo)

        if valor_limite in (None, ""):
            return None

        if isinstance(valor_limite, bool):
            raise ValueError

        numero = int(valor_limite)

        if numero < 1 or numero > 4294967295:
            raise ValueError

        return numero

    try:
        limite_total = converter_limite("limite_total")
        limite_por_cliente = converter_limite(
            "limite_por_cliente"
        )
    except (TypeError, ValueError, OverflowError):
        return None, (
            "Os limites de utilização devem ser números inteiros positivos."
        )

    ativo = dados.get("ativo", True)

    if not isinstance(ativo, bool):
        return None, "O campo ativo deve ser verdadeiro ou falso."

    return {
        "codigo": codigo,
        "tipo": tipo,
        "valor": valor,
        "pedido_minimo": pedido_minimo,
        "inicio_em": inicio_em,
        "fim_em": fim_em,
        "limite_total": limite_total,
        "limite_por_cliente": limite_por_cliente,
        "ativo": ativo,
    }, None


# ==========================================
# LISTAR CUPONS
# ==========================================

@admin_bp.get("/cupons")
@exigir_login_admin
def listar_cupons_admin():
    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor(dictionary=True)

        # Desativa cupons vencidos ou que atingiram o limite de usos.
        # Os registros permanecem no banco para preservar o histórico.
        cursor.execute("""
            UPDATE cupons AS c
            SET ativo = 0
            WHERE c.ativo = 1
              AND (
                  (
                      c.fim_em IS NOT NULL
                      AND (
                          (
                              TIME(c.fim_em) = '00:00:00'
                              AND DATE(c.fim_em) < CURDATE()
                          )
                          OR (
                              TIME(c.fim_em) <> '00:00:00'
                              AND c.fim_em < NOW()
                          )
                      )
                  )
                  OR (
                      c.limite_total IS NOT NULL
                      AND (
                          SELECT COUNT(*)
                          FROM cupom_usos AS u
                          WHERE u.cupom_id = c.id
                      ) >= c.limite_total
                  )
              )
        """)

        conexao.commit()

        cursor.execute("""
            SELECT
                c.id,
                c.codigo,
                c.tipo,
                c.valor,
                c.pedido_minimo,
                c.inicio_em,
                c.fim_em,
                c.limite_total,
                c.limite_por_cliente,
                c.ativo,
                COUNT(u.id) AS utilizacoes
            FROM cupons AS c
            LEFT JOIN cupom_usos AS u
                ON u.cupom_id = c.id
            GROUP BY
                c.id,
                c.codigo,
                c.tipo,
                c.valor,
                c.pedido_minimo,
                c.inicio_em,
                c.fim_em,
                c.limite_total,
                c.limite_por_cliente,
                c.ativo
            ORDER BY c.id DESC
        """)

        cupons = cursor.fetchall()

        for cupom in cupons:
            cupom["id"] = int(cupom["id"])
            cupom["valor"] = float(cupom["valor"])
            cupom["pedido_minimo"] = float(
                cupom["pedido_minimo"]
            )
            cupom["ativo"] = bool(cupom["ativo"])
            cupom["utilizacoes"] = int(cupom["utilizacoes"])

            for campo in ("limite_total", "limite_por_cliente"):
                if cupom[campo] is not None:
                    cupom[campo] = int(cupom[campo])

            for campo in ("inicio_em", "fim_em"):
                if cupom[campo]:
                    cupom[campo] = cupom[campo].isoformat()

        return jsonify({
            "data": cupons
        }), 200

    except Exception:
        return jsonify({
            "error": "Não foi possível carregar os cupons."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()


# ==========================================
# CADASTRAR CUPOM
# ==========================================

@admin_bp.post("/cupons")
@exigir_login_admin
def cadastrar_cupom_admin():
    dados = request.get_json(silent=True) or {}
    cupom, erro = validar_dados_cupom(dados)

    if erro:
        return jsonify({
            "error": erro
        }), 400

    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor()

        cursor.execute("""
            INSERT INTO cupons (
                codigo,
                tipo,
                valor,
                pedido_minimo,
                inicio_em,
                fim_em,
                limite_total,
                limite_por_cliente,
                ativo
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """, (
            cupom["codigo"],
            cupom["tipo"],
            cupom["valor"],
            cupom["pedido_minimo"],
            cupom["inicio_em"],
            cupom["fim_em"],
            cupom["limite_total"],
            cupom["limite_por_cliente"],
            cupom["ativo"],
        ))

        cupom_id = cursor.lastrowid
        conexao.commit()

        return jsonify({
            "message": "Cupom cadastrado com sucesso.",
            "id": cupom_id,
        }), 201

    except Exception as erro:
        if conexao:
            conexao.rollback()

        if getattr(erro, "errno", None) == 1062:
            return jsonify({
                "error": "Já existe um cupom com esse código."
            }), 409

        return jsonify({
            "error": "Não foi possível cadastrar o cupom."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()


# ==========================================
# EDITAR CUPOM
# ==========================================

@admin_bp.patch("/cupons/<int:cupom_id>")
@exigir_login_admin
def editar_cupom_admin(cupom_id):
    dados = request.get_json(silent=True) or {}
    cupom, erro = validar_dados_cupom(dados)

    if erro:
        return jsonify({
            "error": erro
        }), 400

    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor()

        cursor.execute("""
            UPDATE cupons
            SET
                codigo = %s,
                tipo = %s,
                valor = %s,
                pedido_minimo = %s,
                inicio_em = %s,
                fim_em = %s,
                limite_total = %s,
                limite_por_cliente = %s,
                ativo = %s
            WHERE id = %s
        """, (
            cupom["codigo"],
            cupom["tipo"],
            cupom["valor"],
            cupom["pedido_minimo"],
            cupom["inicio_em"],
            cupom["fim_em"],
            cupom["limite_total"],
            cupom["limite_por_cliente"],
            cupom["ativo"],
            cupom_id,
        ))

        if cursor.rowcount == 0:
            cursor.execute(
                "SELECT id FROM cupons WHERE id = %s",
                (cupom_id,)
            )

            if not cursor.fetchone():
                return jsonify({
                    "error": "Cupom não encontrado."
                }), 404

        conexao.commit()

        return jsonify({
            "message": "Cupom atualizado com sucesso."
        }), 200

    except Exception as erro:
        if conexao:
            conexao.rollback()

        if getattr(erro, "errno", None) == 1062:
            return jsonify({
                "error": "Já existe um cupom com esse código."
            }), 409

        return jsonify({
            "error": "Não foi possível atualizar o cupom."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()


# ==========================================
# ATIVAR OU DESATIVAR CUPOM
# ==========================================

@admin_bp.patch("/cupons/<int:cupom_id>/ativo")
@exigir_login_admin
def alterar_ativo_cupom_admin(cupom_id):
    dados = request.get_json(silent=True) or {}
    ativo = dados.get("ativo")

    if not isinstance(ativo, bool):
        return jsonify({
            "error": "Informe ativo como verdadeiro ou falso."
        }), 400

    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor()

        cursor.execute("""
            UPDATE cupons
            SET ativo = %s
            WHERE id = %s
        """, (ativo, cupom_id))

        if cursor.rowcount == 0:
            cursor.execute(
                "SELECT id FROM cupons WHERE id = %s",
                (cupom_id,)
            )

            if not cursor.fetchone():
                return jsonify({
                    "error": "Cupom não encontrado."
                }), 404

        conexao.commit()

        mensagem = (
            "Cupom ativado com sucesso."
            if ativo
            else "Cupom desativado com sucesso."
        )

        return jsonify({
            "message": mensagem
        }), 200

    except Exception:
        if conexao:
            conexao.rollback()

        return jsonify({
            "error": "Não foi possível alterar o cupom."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()


# ==========================================
# REGIÕES DE ENTREGA
# ==========================================

def validar_dados_regiao(dados):
    """Valida os dados recebidos para uma região de entrega."""
    if not isinstance(dados, dict):
        return None, "Envie os dados da região em formato válido."

    bairro = dados.get("bairro")
    cidade = dados.get("cidade")

    if not isinstance(bairro, str) or not bairro.strip():
        return None, "Informe o bairro."

    if not isinstance(cidade, str) or not cidade.strip():
        return None, "Informe a cidade."

    bairro = bairro.strip()
    cidade = cidade.strip()

    if len(bairro) > 80:
        return None, "O bairro deve ter no máximo 80 caracteres."

    if len(cidade) > 80:
        return None, "A cidade deve ter no máximo 80 caracteres."

    try:
        taxa = Decimal(str(dados.get("taxa")))

        if (
            not taxa.is_finite()
            or taxa < Decimal("0")
            or taxa > Decimal("99999999.99")
        ):
            raise ValueError()

        taxa = taxa.quantize(Decimal("0.01"))

    except (InvalidOperation, TypeError, ValueError):
        return None, "Informe uma taxa de entrega válida."

    prazo = dados.get("prazo_estimado_min")

    if prazo in ("", None):
        prazo = None
    else:
        if (
            isinstance(prazo, bool)
            or not isinstance(prazo, int)
            or prazo < 0
            or prazo > 65535
        ):
            return None, "Informe um prazo válido em minutos."

    ativo = dados.get("ativo", True)

    if not isinstance(ativo, bool):
        return None, "O campo ativo deve ser verdadeiro ou falso."

    return {
        "bairro": bairro,
        "cidade": cidade,
        "taxa": taxa,
        "prazo_estimado_min": prazo,
        "ativo": ativo,
    }, None


@admin_bp.get("/regioes-entrega")
@exigir_login_admin
def listar_regioes_entrega_admin():
    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                id,
                bairro,
                cidade,
                taxa,
                prazo_estimado_min,
                ativo
            FROM regioes_entrega
            ORDER BY cidade, bairro
        """)

        regioes = cursor.fetchall()

        for regiao in regioes:
            regiao["id"] = int(regiao["id"])
            regiao["taxa"] = str(regiao["taxa"])
            regiao["prazo_estimado_min"] = (
                int(regiao["prazo_estimado_min"])
                if regiao["prazo_estimado_min"] is not None
                else None
            )
            regiao["ativo"] = bool(regiao["ativo"])

        return jsonify({"data": regioes}), 200

    except Exception:
        return jsonify({
            "error": "Não foi possível carregar as regiões de entrega."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()


@admin_bp.post("/regioes-entrega")
@exigir_login_admin
def cadastrar_regiao_entrega_admin():
    dados = request.get_json(silent=True)
    regiao, erro = validar_dados_regiao(dados)

    if erro:
        return jsonify({"error": erro}), 400

    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT id
            FROM regioes_entrega
            WHERE bairro = %s AND cidade = %s
            LIMIT 1
        """, (regiao["bairro"], regiao["cidade"]))

        if cursor.fetchone():
            return jsonify({
                "error": "Esse bairro já está cadastrado nessa cidade."
            }), 409

        cursor.execute("""
            INSERT INTO regioes_entrega (
                bairro,
                cidade,
                taxa,
                prazo_estimado_min,
                ativo
            )
            VALUES (%s, %s, %s, %s, %s)
        """, (
            regiao["bairro"],
            regiao["cidade"],
            str(regiao["taxa"]),
            regiao["prazo_estimado_min"],
            int(regiao["ativo"]),
        ))

        conexao.commit()

        return jsonify({
            "message": "Região de entrega cadastrada com sucesso.",
            "id": cursor.lastrowid,
        }), 201

    except Exception:
        if conexao:
            conexao.rollback()

        return jsonify({
            "error": "Não foi possível cadastrar a região de entrega."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()


@admin_bp.patch("/regioes-entrega/<int:regiao_id>")
@exigir_login_admin
def editar_regiao_entrega_admin(regiao_id):
    dados = request.get_json(silent=True)
    regiao, erro = validar_dados_regiao(dados)

    if erro:
        return jsonify({"error": erro}), 400

    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT id
            FROM regioes_entrega
            WHERE id = %s
        """, (regiao_id,))

        if not cursor.fetchone():
            return jsonify({
                "error": "Região de entrega não encontrada."
            }), 404

        cursor.execute("""
            SELECT id
            FROM regioes_entrega
            WHERE bairro = %s
              AND cidade = %s
              AND id <> %s
            LIMIT 1
        """, (
            regiao["bairro"],
            regiao["cidade"],
            regiao_id,
        ))

        if cursor.fetchone():
            return jsonify({
                "error": "Esse bairro já está cadastrado nessa cidade."
            }), 409

        cursor.execute("""
            UPDATE regioes_entrega
            SET
                bairro = %s,
                cidade = %s,
                taxa = %s,
                prazo_estimado_min = %s,
                ativo = %s
            WHERE id = %s
        """, (
            regiao["bairro"],
            regiao["cidade"],
            str(regiao["taxa"]),
            regiao["prazo_estimado_min"],
            int(regiao["ativo"]),
            regiao_id,
        ))

        conexao.commit()

        return jsonify({
            "message": "Região de entrega atualizada com sucesso."
        }), 200

    except Exception:
        if conexao:
            conexao.rollback()

        return jsonify({
            "error": "Não foi possível atualizar a região de entrega."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()


@admin_bp.patch("/regioes-entrega/<int:regiao_id>/ativo")
@exigir_login_admin
def alterar_ativo_regiao_entrega_admin(regiao_id):
    dados = request.get_json(silent=True) or {}
    ativo = dados.get("ativo")

    if not isinstance(ativo, bool):
        return jsonify({
            "error": "Informe ativo como verdadeiro ou falso."
        }), 400

    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor()

        cursor.execute("""
            UPDATE regioes_entrega
            SET ativo = %s
            WHERE id = %s
        """, (int(ativo), regiao_id))

        if cursor.rowcount == 0:
            cursor.execute("""
                SELECT id
                FROM regioes_entrega
                WHERE id = %s
            """, (regiao_id,))

            if not cursor.fetchone():
                return jsonify({
                    "error": "Região de entrega não encontrada."
                }), 404

        conexao.commit()

        return jsonify({
            "message": (
                "Região ativada com sucesso."
                if ativo
                else "Região desativada com sucesso."
            )
        }), 200

    except Exception:
        if conexao:
            conexao.rollback()

        return jsonify({
            "error": "Não foi possível alterar o status da região."
        }), 500

    finally:
        if cursor:
            cursor.close()
        if conexao:
            conexao.close()

# ==========================================
# CONFIGURAÇÕES DA LOJA
# ==========================================

@admin_bp.get("/configuracoes")
@exigir_login_admin
def listar_configuracoes_admin():
    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT valor
            FROM configuracoes_loja
            WHERE chave = %s
        """, ("taxa_entrega_padrao",))

        resultado = cursor.fetchone()

        taxa = (
            resultado["valor"]
            if resultado
            else "7.00"
        )

        return jsonify({
            "taxa_entrega_padrao": str(taxa)
        }), 200

    except Exception:
        return jsonify({
            "error": "Não foi possível carregar as configurações."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()


@admin_bp.patch("/configuracoes/taxa-entrega")
@exigir_login_admin
def atualizar_taxa_entrega_admin():
    dados = request.get_json(silent=True) or {}

    try:
        taxa = Decimal(
            str(dados.get("taxa_entrega_padrao"))
        )

        if (
            not taxa.is_finite()
            or taxa < Decimal("0")
            or taxa > Decimal("99999999.99")
        ):
            raise ValueError()

        taxa = taxa.quantize(Decimal("0.01"))

    except (InvalidOperation, TypeError, ValueError):
        return jsonify({
            "error": "Informe uma taxa de entrega válida."
        }), 400

    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor()

        cursor.execute("""
            INSERT INTO configuracoes_loja (chave, valor)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE valor = VALUES(valor)
        """, (
            "taxa_entrega_padrao",
            str(taxa)
        ))

        conexao.commit()

        return jsonify({
            "message": "Taxa de entrega atualizada com sucesso.",
            "taxa_entrega_padrao": str(taxa)
        }), 200

    except Exception:
        if conexao:
            conexao.rollback()

        return jsonify({
            "error": "Não foi possível salvar a taxa de entrega."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()
 


# ==========================================
# EXCLUIR PRODUTO
# Só exclui se nunca foi vendido (preserva o histórico dos pedidos)
# ==========================================

@admin_bp.delete("/produtos/<int:produto_id>")
@exigir_login_admin
def excluir_produto_admin(produto_id):
    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute(
            "SELECT id FROM produtos WHERE id = %s",
            (produto_id,)
        )

        if not cursor.fetchone():
            return jsonify({
                "error": "Produto não encontrado."
            }), 404

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM itens_pedido
            WHERE produto_id = %s
        """, (produto_id,))

        if int(cursor.fetchone()["total"]) > 0:
            return jsonify({
                "error": (
                    "Este produto já foi vendido e não pode ser excluído, "
                    "para preservar o histórico dos pedidos. "
                    "Use o botão Desativar para tirá-lo do cardápio."
                ),
                "codigo": "produto_com_pedidos",
            }), 409

        cursor.execute(
            "DELETE FROM produtos WHERE id = %s",
            (produto_id,)
        )

        conexao.commit()

        return jsonify({
            "message": "Produto excluído com sucesso."
        }), 200

    except Exception as erro:
        if conexao:
            conexao.rollback()

        if getattr(erro, "errno", None) == 1451:
            return jsonify({
                "error": (
                    "Este produto está vinculado a outros registros e não "
                    "pode ser excluído. Use o botão Desativar."
                ),
                "codigo": "produto_vinculado",
            }), 409

        return jsonify({
            "error": "Não foi possível excluir o produto."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()


# ==========================================
# DESTACAR PRODUTO
# ==========================================

@admin_bp.patch("/produtos/<int:produto_id>/destaque")
@exigir_login_admin
def alterar_destaque_produto_admin(produto_id):
    dados = request.get_json(silent=True) or {}
    destaque = dados.get("featured")

    if not isinstance(destaque, bool):
        return jsonify({
            "error": "Informe featured como verdadeiro ou falso."
        }), 400

    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor()

        cursor.execute("""
            UPDATE produtos
            SET destaque = %s
            WHERE id = %s
        """, (destaque, produto_id))

        if cursor.rowcount == 0:
            cursor.execute(
                "SELECT id FROM produtos WHERE id = %s",
                (produto_id,)
            )

            if not cursor.fetchone():
                return jsonify({
                    "error": "Produto não encontrado."
                }), 404

        conexao.commit()

        return jsonify({
            "message": (
                "Produto destacado com sucesso."
                if destaque
                else "Destaque removido com sucesso."
            )
        }), 200

    except Exception:
        if conexao:
            conexao.rollback()

        return jsonify({
            "error": "Não foi possível alterar o destaque."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()


# ==========================================
# EXCLUIR CATEGORIA
# Não exclui se houver produtos associados
# ==========================================

@admin_bp.delete("/categorias/<int:categoria_id>")
@exigir_login_admin
def excluir_categoria_admin(categoria_id):
    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute(
            "SELECT id FROM categorias WHERE id = %s",
            (categoria_id,)
        )

        if not cursor.fetchone():
            return jsonify({
                "error": "Categoria não encontrada."
            }), 404

        cursor.execute("""
            SELECT COUNT(*) AS total
            FROM produtos
            WHERE categoria_id = %s
        """, (categoria_id,))

        total = int(cursor.fetchone()["total"])

        if total > 0:
            return jsonify({
                "error": (
                    f"Esta categoria possui {total} produto(s). "
                    "Mova os produtos para outra categoria antes de excluir."
                ),
                "codigo": "categoria_com_produtos",
            }), 409

        cursor.execute(
            "DELETE FROM categorias WHERE id = %s",
            (categoria_id,)
        )

        conexao.commit()

        return jsonify({
            "message": "Categoria excluída com sucesso."
        }), 200

    except Exception as erro:
        if conexao:
            conexao.rollback()

        if getattr(erro, "errno", None) == 1451:
            return jsonify({
                "error": (
                    "Esta categoria está vinculada a outros registros "
                    "e não pode ser excluída."
                ),
                "codigo": "categoria_vinculada",
            }), 409

        return jsonify({
            "error": "Não foi possível excluir a categoria."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()


# ==========================================
# ORDEM DAS CATEGORIAS
# Recebe a lista completa de ids na nova ordem
# ==========================================

@admin_bp.put("/categorias/ordem")
@exigir_login_admin
def reordenar_categorias_admin():
    dados = request.get_json(silent=True) or {}
    ids = dados.get("ids")

    if (
        not isinstance(ids, list)
        or not ids
        or len(ids) > 5000
        or any(
            isinstance(i, bool) or not isinstance(i, int) or i <= 0
            for i in ids
        )
        or len(set(ids)) != len(ids)
    ):
        return jsonify({
            "error": "Informe a lista de categorias na nova ordem."
        }), 400

    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor(dictionary=True)

        conexao.start_transaction()

        cursor.execute("SELECT id FROM categorias FOR UPDATE")
        existentes = {int(linha["id"]) for linha in cursor.fetchall()}

        if set(ids) != existentes:
            conexao.rollback()

            return jsonify({
                "error": (
                    "A lista de categorias mudou. "
                    "Atualize a página e tente novamente."
                )
            }), 409

        for posicao, categoria_id in enumerate(ids, start=1):
            cursor.execute(
                "UPDATE categorias SET ordem = %s WHERE id = %s",
                (posicao, categoria_id)
            )

        conexao.commit()

        return jsonify({
            "message": "Ordem das categorias salva com sucesso."
        }), 200

    except Exception:
        if conexao:
            conexao.rollback()

        return jsonify({
            "error": "Não foi possível salvar a ordem das categorias."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()


# ==========================================
# FUNCIONAMENTO DA LOJA (horários + abrir/fechar manual)
# ==========================================

@admin_bp.get("/configuracoes/funcionamento")
@exigir_login_admin
def obter_funcionamento_admin():
    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor(dictionary=True)

        return jsonify(obter_situacao(cursor)), 200

    except Exception:
        return jsonify({
            "error": "Não foi possível carregar o funcionamento da loja."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()


@admin_bp.put("/configuracoes/funcionamento")
@exigir_login_admin
def salvar_funcionamento_admin():
    dados = request.get_json(silent=True) or {}
    dias, erro = validar_dias(dados.get("dias"))

    if erro:
        return jsonify({
            "error": erro
        }), 400

    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor(dictionary=True)

        salvar_dias(cursor, dias)
        conexao.commit()

        return jsonify(obter_situacao(cursor)), 200

    except Exception:
        if conexao:
            conexao.rollback()

        return jsonify({
            "error": "Não foi possível salvar os horários."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()


@admin_bp.patch("/configuracoes/loja-modo")
@exigir_login_admin
def alterar_modo_loja_admin():
    dados = request.get_json(silent=True) or {}
    modo = dados.get("modo")

    if modo not in MODOS_LOJA:
        return jsonify({
            "error": "Modo inválido. Use automatico, aberta ou fechada."
        }), 400

    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor(dictionary=True)

        salvar_modo(cursor, modo)
        conexao.commit()

        return jsonify(obter_situacao(cursor)), 200

    except Exception:
        if conexao:
            conexao.rollback()

        return jsonify({
            "error": "Não foi possível alterar o estado da loja."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()
            
    

# ==========================================
# GESTÃO DE CLIENTES
# Lista clientes identificados pelos pedidos
# ==========================================

@admin_bp.get("/clientes")
@exigir_login_admin
def listar_clientes_admin():
    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                telefone_cliente,
                MAX(nome_cliente) AS nome,
                COUNT(*) AS total_pedidos,
                SUM(
                    CASE
                        WHEN status != 'cancelado' THEN 1
                        ELSE 0
                    END
                ) AS pedidos_validos,
                SUM(
                    CASE
                        WHEN status != 'cancelado' THEN total
                        ELSE 0
                    END
                ) AS total_gasto,
                MAX(criado_em) AS ultima_compra
            FROM pedidos
            WHERE telefone_cliente IS NOT NULL
              AND TRIM(telefone_cliente) != ''
            GROUP BY telefone_cliente
            ORDER BY MAX(criado_em) DESC
        """)

        clientes = cursor.fetchall()

        for cliente in clientes:
            cliente["total_pedidos"] = int(
                cliente["total_pedidos"] or 0
            )
            cliente["pedidos_validos"] = int(
                cliente["pedidos_validos"] or 0
            )
            cliente["total_gasto"] = float(
                cliente["total_gasto"] or 0
            )

            if cliente["ultima_compra"]:
                cliente["ultima_compra"] = (
                    cliente["ultima_compra"].isoformat(
                        sep=" ",
                        timespec="seconds"
                    )
                )

        return jsonify({
            "clientes": clientes
        }), 200

    except Exception:
        return jsonify({
            "error": "Não foi possível carregar os clientes."
        }), 500

    finally:
        if cursor:
            cursor.close()

        if conexao:
            conexao.close()
