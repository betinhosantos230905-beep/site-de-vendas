from app import create_app


def client():
    return create_app().test_client()


def test_home_serves_menu():
    r = client().get("/")
    assert r.status_code == 200 and b"SALTY" in r.data


def test_categories_ordered():
    data = client().get("/api/categories").get_json()["data"]
    assert [c["order"] for c in data] == sorted(c["order"] for c in data)


def test_filter_by_category():
    data = client().get("/api/products?category=1").get_json()["data"]
    assert data and all(p["category_id"] == 1 for p in data)


def test_unknown_product_404():
    assert client().get("/api/products/99999").status_code == 404
