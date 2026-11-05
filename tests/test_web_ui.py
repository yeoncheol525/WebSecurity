import os

import requests


def test_html_pages_and_assets(base_url):
    for path, marker in (("/", "MiniShop"), ("/shop", "product-grid"), ("/login", "login-form"),
                         ("/account/orders", "order-list"), ("/account/orders/1001", "order-detail")):
        response = requests.get(base_url + path, timeout=5)
        assert response.status_code == 200
        assert "text/html" in response.headers["Content-Type"]
        assert marker in response.text
        assert "User1-Lab!2026" not in response.text
        assert "script-src 'self'" in response.headers["Content-Security-Policy"]
    for asset in ("style.css", "app.js"):
        assert requests.get(base_url + "/static/" + asset, timeout=5).status_code == 200


def test_browser_bookmarks_redirect_while_api_stays_json(base_url):
    browser = requests.get(base_url + "/products", headers={"Accept": "text/html"}, allow_redirects=False, timeout=5)
    assert browser.status_code == 302 and browser.headers["Location"].startswith("/shop")
    api = requests.get(base_url + "/products", headers={"Accept": "application/json"}, timeout=5)
    assert len(api.json()["products"]) == 12
    orders = requests.get(base_url + "/orders", headers={"Accept": "text/html"}, allow_redirects=False, timeout=5)
    assert orders.status_code == 302 and orders.headers["Location"] == "/login"


def test_browser_session_and_csrf_cookie(base_url):
    with requests.Session() as client:
        login = client.post(base_url + "/login", json={"username": "user1", "password": os.environ["DEMO_USER1_PASSWORD"]}, timeout=10)
        assert login.status_code == 200
        assert client.cookies.get("minishop_csrf") == login.json()["csrf_token"]
        session = client.get(base_url + "/session", timeout=5)
        assert session.status_code == 200 and session.json()["user"]["username"] == "user1"
        own = client.get(base_url + "/orders/1001", timeout=5)
        assert own.status_code == 200 and own.json()["order"]["product_name"]
        assert client.post(base_url + "/logout", headers={"X-CSRF-Token": client.cookies.get("minishop_csrf")}, timeout=5).status_code == 200
        assert client.get(base_url + "/session", timeout=5).status_code == 401
