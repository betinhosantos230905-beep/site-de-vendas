


from backend.database import get_connection
from backend.demo.data import CATEGORIES, PRODUCTS


def popular_banco():
    conexao = get_connection()
    cursor = conexao.cursor()

    try:
        conexao.start_transaction()

        tabelas = [
            "categorias",
            "produtos",
            "grupos_opcoes",
            "opcoes",
            "produto_grupos_opcoes",
        ]

        for tabela in tabelas:
            cursor.execute(f"SELECT COUNT(*) FROM {tabela}")
            total = cursor.fetchone()[0]

            if total > 0:
                raise Exception(
                    f"A tabela {tabela} já possui registros. "
                    "Importação cancelada para evitar duplicações."
                )

        # Cadastra as categorias.
        for categoria in CATEGORIES:
            cursor.execute(
                """
                INSERT INTO categorias
                    (id, nome, descricao, ordem, ativo)
                VALUES (%s, %s, %s, %s, %s)
                """,
                (
                    categoria["id"],
                    categoria["name"],
                    None,
                    categoria["order"],
                    categoria["active"],
                ),
            )

        # Cadastra os produtos.
        for produto in PRODUCTS:
            cursor.execute(
                """
                INSERT INTO produtos (
                    id, categoria_id, nome, descricao, preco,
                    disponivel, destaque, tempo_preparo_min, ativo
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, 1)
                """,
                (
                    produto["id"],
                    produto["category_id"],
                    produto["name"],
                    produto["description"],
                    produto["price"],
                    produto["available"],
                    produto["featured"],
                    produto["prep_minutes"],
                ),
            )

        # Cadastra grupos de opções e associa cada grupo aos produtos.
        grupos_cadastrados = {}

        for produto in PRODUCTS:
            for ordem, grupo in enumerate(
                produto["option_groups"], start=1
            ):
                grupo_demo_id = grupo["id"]

                if grupo_demo_id not in grupos_cadastrados:
                    cursor.execute(
                        """
                        INSERT INTO grupos_opcoes
                            (nome, minimo, maximo, ativo)
                        VALUES (%s, %s, %s, 1)
                        """,
                        (
                            grupo["name"],
                            grupo["min"],
                            grupo["max"],
                        ),
                    )

                    grupo_banco_id = cursor.lastrowid
                    grupos_cadastrados[grupo_demo_id] = grupo_banco_id

                    # Cadastra as opções pertencentes ao grupo.
                    for ordem_opcao, opcao in enumerate(
                        grupo["options"], start=1
                    ):
                        cursor.execute(
                            """
                            INSERT INTO opcoes (
                                grupo_id, nome, preco_adicional,
                                disponivel, ordem
                            )
                            VALUES (%s, %s, %s, 1, %s)
                            """,
                            (
                                grupo_banco_id,
                                opcao["name"],
                                opcao["price"],
                                ordem_opcao,
                            ),
                        )

                # Liga o grupo ao produto.
                cursor.execute(
                    """
                    INSERT INTO produto_grupos_opcoes
                        (produto_id, grupo_id, ordem)
                    VALUES (%s, %s, %s)
                    """,
                    (
                        produto["id"],
                        grupos_cadastrados[grupo_demo_id],
                        ordem,
                    ),
                )

        conexao.commit()

        print("Categorias cadastradas:", len(CATEGORIES))
        print("Produtos cadastrados:", len(PRODUCTS))
        print("Grupos de opções cadastrados:", len(grupos_cadastrados))
        print("Importação concluída com sucesso!")

    except Exception:
        conexao.rollback()
        raise

    finally:
        cursor.close()
        conexao.close()


if __name__ == "__main__":
    popular_banco()
