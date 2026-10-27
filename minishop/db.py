"""SQLite connection, schema and initial sample data."""

import sqlite3
from pathlib import Path

from flask import current_app, g
from werkzeug.security import generate_password_hash


def get_db():
    if "db" not in g:
        g.db = sqlite3.connect(current_app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db


def close_db(_error=None):
    connection = g.pop("db", None)
    if connection is not None:
        connection.close()


def init_db(*, reset=False):
    """Create and seed a new database; preserve existing data unless reset is explicit."""
    connection = get_db()
    exists = connection.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?", ("users",)
    ).fetchone()
    if exists and not reset:
        return False

    if reset:
        connection.executescript(
            "DROP TABLE IF EXISTS orders; DROP TABLE IF EXISTS products; DROP TABLE IF EXISTS users;"
        )
    schema = Path(__file__).with_name("schema.sql").read_text(encoding="utf-8")
    connection.executescript(schema)
    with connection:
        connection.executemany(
            "INSERT INTO users (id, username, password_hash) VALUES (?, ?, ?)",
            [
                (1, "user1", generate_password_hash("User1-Lab!2026")),
                (2, "user2", generate_password_hash("User2-Lab!2026")),
            ],
        )
        connection.executemany(
            "INSERT INTO products (id, name, price, is_public) VALUES (?, ?, ?, ?)",
            [(101, "Laptop", 1200000, 1), (102, "Keyboard", 89000, 1), (901, "Hidden Prototype", 999000, 0)],
        )
        connection.executemany(
            "INSERT INTO orders (id, user_id, product_id, quantity) VALUES (?, ?, ?, ?)",
            [(1001, 1, 102, 1), (2002, 2, 101, 1)],
        )
    return True


def init_app(app):
    app.teardown_appcontext(close_db)
