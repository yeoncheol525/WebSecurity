"""MiniShop development application."""

from pathlib import Path
import secrets
import sqlite3

from flask import Flask, g, jsonify, render_template

from . import db


def create_app(test_config=None):
    project_root = Path(__file__).resolve().parent.parent
    app = Flask(__name__, instance_path=str(project_root / "instance"))
    app.config.from_mapping(
        DATABASE=str(Path(app.instance_path) / "minishop.sqlite3"),
        SECRET_KEY=None,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE="Lax",
    )
    if test_config:
        app.config.update(test_config)

    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    if not app.config["SECRET_KEY"]:
        key_file = Path(app.instance_path) / ".session_key"
        key_file.parent.mkdir(parents=True, exist_ok=True)
        if not key_file.exists():
            key_file.write_text(secrets.token_hex(32), encoding="ascii")
        app.config["SECRET_KEY"] = key_file.read_text(encoding="ascii").strip()

    db.init_app(app)
    with app.app_context():
        db.init_db()

    from .auth import bp as auth_bp
    from .shop import bp as shop_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(shop_bp)

    @app.context_processor
    def template_context():
        return {"current_user": g.get("user")}

    @app.get("/health")
    def health():
        try:
            db.get_db().execute("SELECT 1").fetchone()
        except sqlite3.Error:
            return jsonify(status="error", database="error", app="minishop", mode="development"), 503
        return jsonify(status="ok", database="ok", app="minishop", mode="development")

    @app.errorhandler(404)
    def not_found(_error):
        return render_template("error.html", status_code=404), 404

    return app
