"""Login, logout and the current user."""

from functools import wraps

from flask import Blueprint, flash, g, redirect, render_template, request, session, url_for
from werkzeug.security import check_password_hash

from .db import get_db

bp = Blueprint("auth", __name__)


@bp.before_app_request
def load_user():
    user_id = session.get("user_id")
    row = None
    if user_id is not None:
        row = get_db().execute("SELECT id, username FROM users WHERE id = ?", (user_id,)).fetchone()
    g.user = dict(row) if row else None


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if g.user is None:
            return redirect(url_for("auth.login"))
        return view(*args, **kwargs)
    return wrapped


@bp.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT id, username, password_hash FROM users WHERE username = ?", (username,)
        ).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            return redirect(url_for("shop.home"))
        flash("아이디 또는 비밀번호를 확인해 주세요.", "error")
        return render_template("login.html"), 401
    return render_template("login.html")


@bp.post("/logout")
def logout():
    session.clear()
    flash("로그아웃했어요.", "info")
    return redirect(url_for("shop.home"))
