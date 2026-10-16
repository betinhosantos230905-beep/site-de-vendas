"""DADOS DE DEMONSTRAÇÃO - fictícios. Serão substituídos pelo banco MySQL na Fase 5."""

CATEGORIES = [
    {"id": 1, "name": "Hambúrgueres", "emoji": "🍔", "tone": "#F6D9C2", "order": 1, "active": True},
    {"id": 2, "name": "Cachorro-quente", "emoji": "🌭", "tone": "#F9E0B8", "order": 2, "active": True},
    {"id": 3, "name": "Salgados", "emoji": "🥟", "tone": "#F5E3A9", "order": 3, "active": True},
    {"id": 4, "name": "Porções", "emoji": "🍟", "tone": "#FBE7A1", "order": 4, "active": True},
    {"id": 5, "name": "Pizzas", "emoji": "🍕", "tone": "#F8C9BD", "order": 5, "active": True},
    {"id": 6, "name": "Bebidas", "emoji": "🥤", "tone": "#CFE6EE", "order": 6, "active": True},
    {"id": 7, "name": "Sobremesas", "emoji": "🍰", "tone": "#F2D3DE", "order": 7, "active": True},
    {"id": 8, "name": "Combos", "emoji": "🎁", "tone": "#E2D7F0", "order": 8, "active": True},
]


def _group(gid, name, min_, max_, options):
    return {
        "id": gid, "name": name, "min": min_, "max": max_,
        "options": [{"id": f"{gid}-{i}", "name": n, "price": p} for i, (n, p) in enumerate(options, 1)],
    }


EXTRAS_BURGER = _group("g-add-burger", "Adicionais", 0, 3,
                       [("Queijo extra", 3.00), ("Bacon", 5.00), ("Ovo", 2.50), ("Cebola caramelizada", 3.50)])
POINT = _group("g-ponto", "Ponto da carne", 1, 1, [("Ao ponto", 0), ("Bem passado", 0)])
SAUCES = _group("g-sauce", "Molhos", 0, 2, [("Maionese da casa", 0), ("Barbecue", 0), ("Picante", 0)])
PIZZA_SIZE = _group("g-pizza-size", "Tamanho", 1, 1, [("Média (6 fatias)", 0), ("Grande (8 fatias)", 12.00)])
SOFT_SIZE = _group("g-soft-size", "Tamanho", 1, 1, [("350 ml", 0), ("600 ml", 3.00)])

PRODUCTS = [
    {"id": 101, "category_id": 1, "name": "Salty Clássico", "price": 24.90, "available": True, "featured": True,
     "prep_minutes": 20, "description": "Pão brioche, blend bovino 160 g, queijo prato, alface e tomate.",
     "option_groups": [POINT, EXTRAS_BURGER]},
    {"id": 102, "category_id": 1, "name": "Salty Bacon", "price": 29.90, "available": True, "featured": True,
     "prep_minutes": 20, "description": "Blend bovino 160 g, bacon crocante, cheddar e maionese da casa.",
     "option_groups": [POINT, EXTRAS_BURGER]},
    {"id": 103, "category_id": 1, "name": "Burger Duplo", "price": 34.90, "available": False, "featured": False,
     "prep_minutes": 25, "description": "Dois blends de 120 g, queijo duplo e picles.", "option_groups": [POINT]},
    {"id": 201, "category_id": 2, "name": "Dog Tradicional", "price": 16.90, "available": True, "featured": False,
     "prep_minutes": 12, "description": "Salsicha, molho de tomate, milho, batata palha e purê.",
     "option_groups": [SAUCES]},
    {"id": 202, "category_id": 2, "name": "Dog Salty", "price": 21.90, "available": True, "featured": True,
     "prep_minutes": 15, "description": "Duas salsichas, cheddar, bacon e batata palha.", "option_groups": [SAUCES]},
    {"id": 301, "category_id": 3, "name": "Coxinha de frango", "price": 7.50, "available": True, "featured": False,
     "prep_minutes": 8, "description": "Massa leve, recheio de frango desfiado e catupiry.", "option_groups": []},
    {"id": 302, "category_id": 3, "name": "Pastel de carne", "price": 8.00, "available": True, "featured": False,
     "prep_minutes": 8, "description": "Pastel frito na hora com carne moída temperada.", "option_groups": []},
    {"id": 401, "category_id": 4, "name": "Batata frita", "price": 19.90, "available": True, "featured": False,
     "prep_minutes": 12, "description": "Porção de 300 g, crocante e sequinha.",
     "option_groups": [_group("g-batata-add", "Cobertura", 0, 2, [("Cheddar", 5.00), ("Bacon", 6.00)])]},
    {"id": 501, "category_id": 5, "name": "Pizza Calabresa", "price": 39.90, "available": True, "featured": False,
     "prep_minutes": 30, "description": "Calabresa fatiada, cebola e mussarela.", "option_groups": [PIZZA_SIZE]},
    {"id": 502, "category_id": 5, "name": "Pizza Mussarela", "price": 36.90, "available": True, "featured": False,
     "prep_minutes": 30, "description": "Mussarela, tomate e orégano.", "option_groups": [PIZZA_SIZE]},
    {"id": 601, "category_id": 6, "name": "Refrigerante", "price": 6.00, "available": True, "featured": False,
     "prep_minutes": None, "description": "Cola, guaraná ou limão, bem gelado.",
     "option_groups": [SOFT_SIZE, _group("g-soft-flavor", "Sabor", 1, 1, [("Cola", 0), ("Guaraná", 0), ("Limão", 0)])]},
    {"id": 602, "category_id": 6, "name": "Suco natural", "price": 9.00, "available": True, "featured": False,
     "prep_minutes": 5, "description": "Laranja ou maracujá, feito na hora.",
     "option_groups": [_group("g-suco", "Sabor", 1, 1, [("Laranja", 0), ("Maracujá", 0)])]},
    {"id": 701, "category_id": 7, "name": "Brownie com sorvete", "price": 17.90, "available": True, "featured": False,
     "prep_minutes": 8, "description": "Brownie quente de chocolate com bola de creme.", "option_groups": []},
    {"id": 801, "category_id": 8, "name": "Combo Salty", "price": 39.90, "available": True, "featured": True,
     "prep_minutes": 25, "description": "Salty Clássico + batata pequena + refrigerante 350 ml.",
     "option_groups": [POINT]},
]
