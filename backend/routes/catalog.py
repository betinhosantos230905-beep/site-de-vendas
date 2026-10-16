
from flask import Blueprint, jsonify, request

from backend.services import catalog_service as service
from backend.database import get_connection


catalog_bp = Blueprint("catalog", __name__)

DEMO = False


def _ok(data):
    return jsonify({
        "data": data,
        "demo": DEMO
    })


# ==========================================
# CATEGORIAS DO CARDÁPIO
# ==========================================

@catalog_bp.get("/categories")
def get_categories():
    return _ok(service.categories())


# ==========================================
# PRODUTOS DO CARDÁPIO
# ==========================================

@catalog_bp.get("/products")
def get_products():
    return _ok(
        service.products(
            request.args.get("category", type=int)
        )
    )


@catalog_bp.get("/products/<int:product_id>")
def get_product(product_id):
    found = service.product(product_id)

    if found is None:
        return jsonify({
            "error": "Produto não encontrado."
        }), 404

    return _ok(found)


# ==========================================
# CONFIGURAÇÕES PÚBLICAS DA LOJA
# TAXA DE ENTREGA
# ==========================================

@catalog_bp.get("/configuracoes")
def get_public_settings():
    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT valor
            FROM configuracoes_loja
            WHERE chave = %s
            LIMIT 1
        """, ("taxa_entrega_padrao",))

        registro = cursor.fetchone()

        taxa = str(registro["valor"]) if registro else "7.00"

        return _ok({
            "taxa_entrega_padrao": taxa
        })

    except Exception as erro:
        print(
            "ERRO AO BUSCAR A TAXA DE ENTREGA:",
            repr(erro),
            flush=True
        )

        return jsonify({
            "error": "Não foi possível carregar a taxa de entrega."
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if conexao is not None:
            conexao.close()


# ==========================================
# CUPONS DISPONÍVEIS NO CARDÁPIO
# TESTE DIRETO NO MYSQL
# ==========================================

@catalog_bp.get("/coupons")
def get_coupons():
    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor(dictionary=True)

        # Confere o banco utilizado pela conexão.
        cursor.execute("SELECT DATABASE() AS banco_atual")
        banco = cursor.fetchone()

        print(
            "BANCO USADO PELA API DE CUPONS:",
            banco,
            flush=True
        )

        # Busca os cupons ativos.
        cursor.execute("""
            SELECT
                id,
                codigo,
                tipo,
                valor,
                pedido_minimo,
                inicio_em,
                fim_em,
                limite_total,
                ativo
            FROM cupons
            WHERE ativo = 1
            ORDER BY id DESC
        """)

        registros = cursor.fetchall()

        print(
            "TESTE DIRETO DOS CUPONS:",
            registros,
            flush=True
        )

        cupons = []

        for registro in registros:
            inicio = registro.get("inicio_em")
            fim = registro.get("fim_em")
            limite = registro.get("limite_total")

            codigo = registro.get("codigo")
            tipo = registro.get("tipo")
            valor = float(registro.get("valor") or 0)

            pedido_minimo = float(
                registro.get("pedido_minimo") or 0
            )

            cupons.append({
                "id": int(registro["id"]),
                "codigo": codigo,
                "code": codigo,
                "tipo": tipo,
                "valor": valor,
                "pedido_minimo": pedido_minimo,
                "min_order": pedido_minimo,
                "inicio_em": (
                    inicio.isoformat() if inicio else None
                ),
                "fim_em": (
                    fim.isoformat() if fim else None
                ),
                "limite_total": (
                    int(limite) if limite is not None else None
                ),
                "utilizacoes": 0,
                "ativo": bool(registro.get("ativo")),
                "active": bool(registro.get("ativo")),
                "discount_type": tipo,
                "discount_value": valor
            })

        print(
            "TOTAL DE CUPONS ENVIADOS:",
            len(cupons),
            flush=True
        )

        return jsonify({
            "cupons": cupons
        }), 200

    except Exception as erro:
        print(
            "ERRO NA API DE CUPONS:",
            repr(erro),
            flush=True
        )

        return jsonify({
            "error": "Não foi possível carregar os cupons."
        }), 500

    finally:
        if cursor is not None:
            cursor.close()

        if conexao is not None:
            conexao.close()
