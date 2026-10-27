"""Product browsing and the signed-in user's orders."""

from flask import Blueprint, abort, g, render_template, request

from .auth import login_required
from .db import get_db

bp = Blueprint("shop", __name__)


@bp.get("/")
def home():
    return render_template("home.html")


@bp.get("/products")
def products():
    keyword = request.args.get("keyword", "").strip()
    rows = get_db().execute(
        "SELECT id, name, price FROM products WHERE is_public = 1 AND name LIKE ? ORDER BY id",
        (f"%{keyword}%",),
    ).fetchall()
    return render_template("products.html", products=[dict(row) for row in rows], keyword=keyword)


@bp.get("/orders")
@login_required
def orders():
    order_id = request.args.get("order_id", "").strip()
    sql = """SELECT o.id, o.user_id, o.product_id, o.quantity, p.name AS product_name
             FROM orders AS o JOIN products AS p ON p.id = o.product_id
             WHERE o.user_id = ?"""
    parameters = [g.user["id"]]
    if order_id:
        sql += " AND o.id = ?"
        parameters.append(order_id)
    rows = get_db().execute(sql + " ORDER BY o.id", parameters).fetchall()
    return render_template("orders.html", orders=[dict(row) for row in rows], order_id=order_id)


@bp.get("/orders/<int:order_id>")
@login_required
def order_detail(order_id):
    row = get_db().execute(
        """SELECT o.id, o.user_id, o.product_id, o.quantity, p.name AS product_name
           FROM orders AS o JOIN products AS p ON p.id = o.product_id
           WHERE o.id = ? AND o.user_id = ?""",
        (order_id, g.user["id"]),
    ).fetchone()
    if row is None:
        abort(404)
    return render_template("order_detail.html", order=dict(row))
