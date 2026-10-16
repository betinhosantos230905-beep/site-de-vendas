
from backend.database import get_connection


def list_categories():
    conexao = get_connection()
    cursor = conexao.cursor(dictionary=True)

    try:
        cursor.execute("""
            SELECT
                id,
                nome AS name,
                ordem AS `order`,
                ativo AS active
            FROM categorias
            WHERE ativo = 1
            ORDER BY ordem, nome
        """)

        categorias = cursor.fetchall()

        for categoria in categorias:
            categoria["id"] = int(categoria["id"])
            categoria["order"] = int(categoria["order"])
            categoria["active"] = bool(categoria["active"])

        return categorias

    finally:
        cursor.close()
        conexao.close()


def list_products(category_id=None):
    conexao = get_connection()
    cursor = conexao.cursor(dictionary=True)

    try:
        sql = """
            SELECT
                id,
                categoria_id AS category_id,
                nome AS name,
                descricao AS description,
                preco AS price,
                preco_promocional AS promo_price,
                imagem_url AS image_url,
                disponivel AS available,
                destaque AS featured,
                tempo_preparo_min AS prep_minutes
            FROM produtos
            WHERE ativo = 1
        """

        parametros = []

        if category_id is not None:
            sql += " AND categoria_id = %s"
            parametros.append(category_id)

        sql += " ORDER BY destaque DESC, nome"

        cursor.execute(sql, parametros)
        produtos = cursor.fetchall()

        for produto in produtos:
            produto["id"] = int(produto["id"])

            produto["category_id"] = int(
                produto["category_id"]
            )

            produto["price"] = float(
                produto["price"]
            )

            if produto["promo_price"] is not None:
                produto["promo_price"] = float(
                    produto["promo_price"]
                )

            produto["available"] = bool(
                produto["available"]
            )

            produto["featured"] = bool(
                produto["featured"]
            )

            if produto["prep_minutes"] is not None:
                produto["prep_minutes"] = int(
                    produto["prep_minutes"]
                )

        grupos_por_produto = {}

        cursor.execute("""
            SELECT
                pgo.produto_id AS product_id,
                go.id AS group_id,
                go.nome AS group_name,
                go.minimo AS min_options,
                go.maximo AS max_options,
                o.id AS option_id,
                o.nome AS option_name,
                o.preco_adicional AS option_price
            FROM produto_grupos_opcoes AS pgo
            INNER JOIN grupos_opcoes AS go
                ON go.id = pgo.grupo_id
            LEFT JOIN opcoes AS o
                ON o.grupo_id = go.id
                AND o.disponivel = 1
            INNER JOIN produtos AS p
                ON p.id = pgo.produto_id
            WHERE p.ativo = 1
                AND go.ativo = 1
            ORDER BY
                pgo.produto_id,
                pgo.ordem,
                go.id,
                o.ordem,
                o.nome
        """)

        for linha in cursor.fetchall():
            product_id = int(
                linha["product_id"]
            )

            group_id = int(
                linha["group_id"]
            )

            if product_id not in grupos_por_produto:
                grupos_por_produto[product_id] = {}

            if group_id not in grupos_por_produto[product_id]:
                grupos_por_produto[product_id][group_id] = {
                    "id": group_id,
                    "name": linha["group_name"],
                    "min": int(linha["min_options"]),
                    "max": int(linha["max_options"]),
                    "options": [],
                }

            if linha["option_id"] is not None:
                grupos_por_produto[product_id][group_id][
                    "options"
                ].append({
                    "id": int(linha["option_id"]),
                    "name": linha["option_name"],
                    "price": float(linha["option_price"]),
                })

        for produto in produtos:
            grupos = grupos_por_produto.get(
                produto["id"], {}
            )

            produto["option_groups"] = list(
                grupos.values()
            )

        return produtos

    finally:
        cursor.close()
        conexao.close()


def get_product(product_id):
    produtos = list_products()

    return next(
        (
            produto
            for produto in produtos
            if produto["id"] == product_id
        ),
        None
    )
