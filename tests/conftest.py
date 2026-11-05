import os

import psycopg
import pytest
import requests


@pytest.fixture(scope="session")
def base_url():
    return os.environ["BASE_URL"].rstrip("/")


def db_connection(role):
    passwords = {
        "catalog_reader": "CATALOG_READER_PASSWORD",
        "catalog_reader_wide": "CATALOG_READER_WIDE_PASSWORD",
        "order_service": "ORDER_SERVICE_PASSWORD",
        os.environ["DB_ADMIN_USER"]: "DB_ADMIN_PASSWORD",
    }
    return psycopg.connect(host=os.environ["DB_HOST"], dbname=os.environ["DB_NAME"],
                           user=role, password=os.environ[passwords[role]],
                           autocommit=True, connect_timeout=5)


@pytest.fixture
def db():
    return db_connection


@pytest.fixture
def user1(base_url):
    with requests.Session() as client:
        response = client.post(base_url + "/login", json={
            "username": "user1", "password": os.environ["DEMO_USER1_PASSWORD"],
        }, timeout=10)
        assert response.status_code == 200
        csrf = response.json()["csrf_token"]
        yield client
        client.post(base_url + "/logout", headers={"X-CSRF-Token": csrf}, timeout=10)
