
import os
from functools import wraps
from pathlib import Path
from datetime import datetime
from decimal import Decimal, InvalidOperation

from flask import Blueprint, jsonify, request, session

from backend.database import get_connection


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
    senha_correta = os.getenv("SALTY_ADMIN_PASSWORD", "")

    # Diagnóstico temporário: não exibe nenhuma senha.
    print("\n--- DIAGNOSTICO DO LOGIN ADMIN ---", flush=True)
    print("ARQUIVO DA ROTA:", __file__, flush=True)
    print("PASTA ATUAL:", Path.cwd(), flush=True)
    print("SENHA CONFIGURADA:", bool(senha_correta), flush=True)
    print("TAMANHO CONFIGURADO:", len(senha_correta), flush=True)
    print("TIPO DA SENHA RECEBIDA:", type(senha).__name__, flush=True)

    if isinstance(senha, str):
        print("TAMANHO RECEBIDO:", len(senha), flush=True)
        print("SENHAS IGUAIS:", senha == senha_correta, flush=True)
    else:
        print("TAMANHO RECEBIDO: inválido", flush=True)
        print("SENHAS IGUAIS: False", flush=True)

    print("--- FIM DO DIAGNOSTICO ---\n", flush=True)

    if not senha_correta:
        return jsonify({
            "error": "Senha administrativa não configurada."
        }), 500

    if not isinstance(senha, str) or senha != senha_correta:
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
@exigir_login_admin
def verificar_sessao_admin():
    return jsonify({
        "autenticado": True
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

        pedidos = cursor.fetchall()

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

        itens = cursor.fetchall()

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

            item["opcoes"] = cursor.fetchall()

        cursor.execute("""
            SELECT
                forma,
                valor,
                troco_para,
                status
            FROM pagamentos
            WHERE pedido_id = %s
            ORDER BY id DESC
        """, (pedido_id,))

        pagamentos = cursor.fetchall()

        pedido["itens"] = itens
        pedido["pagamentos"] = pagamentos

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

    # Preço promocional: opcional.
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
        return None, "O campo de disponibilidade deve ser verdadeiro ou falso."

    if not isinstance(destaque, bool):
        return None, "O campo de destaque deve ser verdadeiro ou falso."

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
            produto["category_id"] = int(produto["category_id"])
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
# A cópia começa sem preço promocional.
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

        return datetime.fromisoformat(
            texto.replace("Z", "+00:00")
        ).replace(tzinfo=None)

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
