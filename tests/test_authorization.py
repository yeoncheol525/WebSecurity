import os

import pytest
import requests


@pytest.mark.parametrize("number,order_id", [(1, 1001), (2, 2002)])
def test_T07_login_and_own_orders(base_url, number, order_id):
    with requests.Session() as client:
        login = client.post(base_url + "/login", json={"username": f"user{number}",
                            "password": os.environ[f"DEMO_USER{number}_PASSWORD"]}, timeout=10)
        assert login.status_code == 200
        cookie = login.headers["Set-Cookie"]
        assert "HttpOnly" in cookie and "SameSite=Strict" in cookie
        detail = client.get(base_url + f"/orders/{order_id}", timeout=5)
        assert detail.status_code == 200
        assert detail.json()["order"]["id"] == order_id
        listing = client.get(base_url + "/orders", timeout=5)
        assert listing.status_code == 200
        assert len(listing.json()["orders"]) == 3
        assert all(row["customer_id"] == number for row in listing.json()["orders"])
        csrf = login.json()["csrf_token"]
        assert client.post(base_url + "/logout", headers={"X-CSRF-Token": csrf}, timeout=5).status_code == 200


def test_T08_other_users_order_denied(base_url, user1):
    other = user1.get(base_url + "/orders/2002", timeout=5)
    absent = user1.get(base_url + "/orders/999999", timeout=5)
    assert other.status_code == absent.status_code == 404
    assert other.json() == absent.json() == {"error": "not_found"}


@pytest.mark.parametrize("path", ["/orders", "/orders/1001"])
def test_T09_anonymous_orders_denied(base_url, path):
    response = requests.get(base_url + path, timeout=5)
    assert response.status_code == 401


def test_bad_credentials_and_csrf(base_url):
    invalid = requests.post(base_url + "/login", json={"username": "user1", "password": "incorrect"}, timeout=10)
    assert invalid.status_code == 401
    assert "Set-Cookie" not in invalid.headers
    assert requests.post(base_url + "/login", data={"username": "user1"}, timeout=5).status_code == 415
    assert requests.post(base_url + "/login", json={}, headers={"Origin": "https://different.invalid"}, timeout=5).status_code == 403
    with requests.Session() as client:
        login = client.post(base_url + "/login", json={"username": "user1", "password": os.environ["DEMO_USER1_PASSWORD"]}, timeout=10)
        assert login.status_code == 200
        copied_token = client.cookies.get("minishop_session")
        assert client.post(base_url + "/logout", timeout=5).status_code == 403
        assert client.post(base_url + "/logout", headers={"X-CSRF-Token": login.json()["csrf_token"]}, timeout=5).status_code == 200
        # Logout invalidates even a separately copied cookie on the server.
        replay = requests.get(base_url + "/orders", cookies={"minishop_session": copied_token}, timeout=5)
        assert replay.status_code == 401
