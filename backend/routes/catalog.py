
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
# REGIÕES DE ENTREGA DISPONÍVEIS
# ==========================================

@catalog_bp.get("/regioes-entrega")
def get_public_delivery_regions():
    conexao = None
    cursor = None

    try:
        conexao = get_connection()
        cursor = conexao.cursor(dictionary=True)

        cursor.execute("""
            SELECT
                cidade,
                bairro,
                taxa,
                prazo_estimado_min
            FROM regioes_entrega
            WHERE ativo = 1
            ORDER BY cidade ASC, bairro ASC
        """)

        regioes = cursor.fetchall()

        dados = [
            {
                "cidade": regiao["cidade"],
                "bairro": regiao["bairro"],
                "taxa": str(regiao["taxa"]),
                "prazo_estimado_min": regiao["prazo_estimado_min"],
            }
            for regiao in regioes
        ]

        return _ok(dados)

    except Exception as erro:
        print(
            "ERRO AO BUSCAR AS REGIÕES DE ENTREGA:",
            repr(erro),
            flush=True
        )

        return jsonify({
            "error": "Não foi possível carregar as regiões de entrega."
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

        # Desativa cupons vencidos ou que atingiram o limite de usos.
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

        # Busca somente cupons disponíveis para os clientes.
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
                c.ativo
            FROM cupons AS c
            WHERE c.ativo = 1
              AND (
                  c.inicio_em IS NULL
                  OR c.inicio_em <= NOW()
              )
              AND (
                  c.fim_em IS NULL
                  OR c.fim_em >= NOW()
                  OR (
                      TIME(c.fim_em) = '00:00:00'
                      AND DATE(c.fim_em) = CURDATE()
                  )
              )
              AND (
                  c.limite_total IS NULL
                  OR (
                      SELECT COUNT(*)
                      FROM cupom_usos AS u
                      WHERE u.cupom_id = c.id
                  ) < c.limite_total
              )
            ORDER BY c.id DESC
        """)

        registros = cursor.fetchall()

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

        return jsonify({
            "cupons": cupons
        }), 200

    except Exception as erro:
        if conexao is not None:
            conexao.rollback()

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
