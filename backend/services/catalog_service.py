"""Regras do cardápio (sem SQL e sem HTTP)."""
from backend.repositories import catalog_repository as repo


def categories():
    return repo.list_categories()


def products(category_id=None):
    return repo.list_products(category_id)


def product(product_id):
    return repo.get_product(product_id)
