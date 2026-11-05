import re

import requests


def test_T01_catalog_through_nginx(base_url):
    response = requests.get(base_url + "/health/catalog", timeout=5)
    assert response.status_code == 200
    assert response.json()["database_role"] == "catalog_reader"
    assert response.json()["query_mode"] == "bound"
    products = requests.get(base_url + "/products", timeout=5)
    assert products.status_code == 200
    assert len(products.json()["products"]) == 12


def test_T02_order_service_through_nginx(base_url):
    response = requests.get(base_url + "/health/orders", timeout=5)
    assert response.status_code == 200
    assert response.json()["database_role"] == "order_service"
    assert response.json()["ownership_enforced"] is True


def test_normal_search_with_apostrophe_and_hidden_product(base_url):
    response = requests.get(base_url + "/products", params={"q": "O'Reilly"}, timeout=5)
    assert response.status_code == 200
    assert [p["id"] for p in response.json()["products"]] == [1]
    for literal in ("%", "_", "!"):
        assert requests.get(base_url + "/products", params={"q": literal}, timeout=5).json()["products"] == []
    assert requests.get(base_url + "/products/1", timeout=5).status_code == 200
    assert requests.get(base_url + "/products/13", timeout=5).status_code == 404


def test_request_ids_are_generated_at_nginx(base_url):
    headers = {"X-Request-ID": "0" * 32}
    responses = [requests.get(base_url + "/products/1", headers=headers, timeout=5) for _ in range(2)]
    ids = [r.headers["X-Request-ID"] for r in responses]
    assert len(set(ids)) == 2
    assert all(re.fullmatch("[0-9a-f]{32}", value) and value != "0"*32 for value in ids)
