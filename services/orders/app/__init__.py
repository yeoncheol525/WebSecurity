import hashlib
import os
import re
import secrets
from datetime import datetime, timedelta, timezone
from functools import wraps
from pathlib import Path
from urllib.parse import urlsplit

from flask import abort, g, jsonify, redirect, render_template, request
from werkzeug.security import check_password_hash, generate_password_hash

from common.runtime import create_base_app, get_db, query


COOKIE_NAME = "minishop_session"
CSRF_COOKIE_NAME = "minishop_csrf"
SESSION_SECONDS = 1800
ORDER_FIELDS = "o.id, o.customer_id, o.product_id, o.quantity, o.total_amount, o.order_date, COALESCE(p.label, '상품 #' || o.product_id::text) AS product_name"
SESSION_TOKEN = re.compile(r"[A-Za-z0-9_-]{43}")


def digest(value):
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def cookie_token():
    value = request.cookies.get(COOKIE_NAME, "")
    return value if SESSION_TOKEN.fullmatch(value) else None


def login_required(function):
    @wraps(function)
    def wrapped(*args, **kwargs):
        token = cookie_token()
        row = None
        if token:
            row = query(
                "session.authenticate",
                "SELECT s.user_id, s.csrf_hash FROM auth.sessions AS s "
                "WHERE s.token_hash = %s AND s.expires_at > now()",
                (digest(token),), fetch="one",
            )
        if row is None:
            g.authorization_result = "unauthenticated"
            if request.accept_mimetypes.best_match(["application/json", "text/html"]) == "text/html":
                return redirect("/login")
            abort(401)
        g.authenticated_user = row["user_id"]
        g.csrf_hash = row["csrf_hash"]
        g.authorization_result = "authenticated"
        return function(*args, **kwargs)
    return wrapped


def require_same_origin():
    # Non-browser clients may omit Origin. JSON-only login prevents simple cross-site form POSTs.
    origin = request.headers.get("Origin")
    if origin:
        parsed = urlsplit(origin)
        expected = urlsplit(request.host_url)
        if (parsed.scheme, parsed.netloc) != (expected.scheme, expected.netloc):
            g.authorization_result = "origin_denied"
            abort(403)


def serialize_order(row):
    return {**row, "total_amount": format(row["total_amount"], ".2f"),
            "order_date": row["order_date"].isoformat()}


def create_app():
    directory = Path(__file__).resolve().parent
    app = create_base_app("orders", template_folder=str(directory / "templates"), static_folder=str(directory / "static"))
    # Same-cost verification for nonexistent users; generated once per Gunicorn worker.
    dummy_hash = generate_password_hash(secrets.token_urlsafe(24), method="pbkdf2:sha256:1000000")
    secure_cookie = os.getenv("SESSION_COOKIE_SECURE", "false") == "true"

    @app.get("/")
    def home_page():
        return render_template("home.html", page="home")

    @app.get("/shop")
    def shop_page():
        return render_template("products.html", page="products")

    @app.get("/login")
    def login_page():
        return render_template("login.html", page="login")

    @app.get("/account/orders")
    def orders_page():
        return render_template("orders.html", page="orders")

    @app.get("/account/orders/<int:order_id>")
    def order_page(order_id):
        return render_template("order_detail.html", page="order", order_id=order_id)

    @app.get("/session")
    @login_required
    def session_info():
        user = query("session.user", "SELECT id, username, role FROM auth.users WHERE id = %s",
                     (g.authenticated_user,), fetch="one")
        if user is None:
            abort(401)
        return jsonify(user=user)

    @app.post("/login")
    def login():
        require_same_origin()
        if not request.is_json:
            abort(415)
        body = request.get_json()
        if not isinstance(body, dict):
            abort(400)
        username, password = body.get("username"), body.get("password")
        if not isinstance(username, str) or not isinstance(password, str):
            abort(400)
        if not (1 <= len(username) <= 64 and 1 <= len(password) <= 256):
            abort(400)
        user = query("auth.login", "SELECT id, username, password_hash, role FROM auth.users "
                     "WHERE username = %s", (username,), fetch="one")
        candidate = user["password_hash"] if user and not user["password_hash"].startswith("!") else dummy_hash
        valid = check_password_hash(candidate, password)
        if not user or user["password_hash"].startswith("!") or not valid:
            g.authorization_result = "invalid_credentials"
            return jsonify(error="invalid_credentials"), 401
        token, csrf_token = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        old_token = cookie_token()
        with get_db().transaction():
            if old_token:
                query("session.rotate", "DELETE FROM auth.sessions WHERE token_hash = %s", (digest(old_token),))
            query("session.create", "INSERT INTO auth.sessions (token_hash, csrf_hash, user_id, expires_at) "
                  "VALUES (%s, %s, %s, %s)",
                  (digest(token), digest(csrf_token), user["id"],
                   datetime.now(timezone.utc) + timedelta(seconds=SESSION_SECONDS)))
        g.authenticated_user = user["id"]
        g.authorization_result = "allowed"
        response = jsonify(user={"id": user["id"], "username": user["username"]}, csrf_token=csrf_token)
        response.set_cookie(COOKIE_NAME, token, httponly=True, secure=secure_cookie,
                            samesite="Strict", max_age=SESSION_SECONDS, path="/")
        # This token is deliberately readable by same-origin JavaScript. The authentication cookie stays HttpOnly.
        response.set_cookie(CSRF_COOKIE_NAME, csrf_token, httponly=False, secure=secure_cookie,
                            samesite="Strict", max_age=SESSION_SECONDS, path="/")
        return response

    @app.post("/logout")
    @login_required
    def logout():
        require_same_origin()
        csrf = request.headers.get("X-CSRF-Token", "")
        if not SESSION_TOKEN.fullmatch(csrf) or not secrets.compare_digest(digest(csrf), g.csrf_hash):
            g.authorization_result = "csrf_denied"
            abort(403)
        query("session.revoke", "DELETE FROM auth.sessions WHERE token_hash = %s", (digest(cookie_token()),))
        g.authorization_result = "allowed"
        response = jsonify(status="logged_out")
        response.delete_cookie(COOKIE_NAME, path="/", httponly=True, secure=secure_cookie, samesite="Strict")
        response.delete_cookie(CSRF_COOKIE_NAME, path="/", secure=secure_cookie, samesite="Strict")
        return response

    @app.get("/orders")
    @login_required
    def orders():
        if request.accept_mimetypes.best_match(["application/json", "text/html"]) == "text/html":
            return redirect("/account/orders")
        rows = query("orders.list", "SELECT " + ORDER_FIELDS +
                     " FROM private.orders AS o JOIN private.customers AS c ON c.id = o.customer_id "
                     "LEFT JOIN catalog.public_products AS p ON p.item_key = o.product_id "
                     "WHERE c.user_id = %s ORDER BY o.id", (g.authenticated_user,), fetch="all")
        g.authorization_result = "allowed"
        return jsonify(orders=[serialize_order(row) for row in rows])

    @app.get("/orders/<int:order_id>")
    @login_required
    def order(order_id):
        if request.accept_mimetypes.best_match(["application/json", "text/html"]) == "text/html":
            return redirect(f"/account/orders/{order_id}")
        row = query("orders.detail", "SELECT " + ORDER_FIELDS +
                    " FROM private.orders AS o JOIN private.customers AS c ON c.id = o.customer_id "
                    "LEFT JOIN catalog.public_products AS p ON p.item_key = o.product_id "
                    "WHERE o.id = %s AND c.user_id = %s",
                    (order_id, g.authenticated_user), fetch="one")
        if row is None:
            # Identical response for a nonexistent order and another user's order.
            g.authorization_result = "denied_or_not_found"
            abort(404)
        g.authorization_result = "allowed"
        return jsonify(order=serialize_order(row))

    return app
