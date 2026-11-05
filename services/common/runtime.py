import json
import logging
import os
import re
import time
import uuid
from datetime import datetime, timezone

import psycopg
from flask import Flask, g, jsonify, request
from psycopg.rows import dict_row
from werkzeug.exceptions import HTTPException


LOGGER = logging.getLogger("minishop.audit")
if not LOGGER.handlers:
    handler = logging.StreamHandler()
    handler.setFormatter(logging.Formatter("%(message)s"))
    LOGGER.addHandler(handler)
LOGGER.setLevel(logging.INFO)
LOGGER.propagate = False


def emit(event, **fields):
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "request_id": getattr(g, "request_id", None),
        "service": getattr(g, "service", None),
        "event": event,
    }
    record.update(fields)
    LOGGER.info(json.dumps(record, ensure_ascii=True, separators=(",", ":")))


def create_base_app(service, *, template_folder=None, static_folder=None):
    app = Flask(service, template_folder=template_folder, static_folder=static_folder, static_url_path="/static")
    app.config.update(MAX_CONTENT_LENGTH=16 * 1024, DEBUG=False, TESTING=False)
    expected_role = "catalog_reader" if service == "catalog" else "order_service"
    role = os.environ["DB_USER"]
    if role != expected_role:
        if not (service == "catalog" and role == "catalog_reader_wide"
                and os.getenv("LAB_EXPERIMENTS_ENABLED") == "true"):
            raise RuntimeError("Unexpected database role; lab role requires explicit opt-in")
    if os.getenv("SQL_QUERY_MODE", "bound") != "bound":
        raise RuntimeError("Only parameter-bound queries are implemented in this stage")

    @app.before_request
    def begin_request():
        supplied = request.headers.get("X-Request-ID", "")
        g.request_id = supplied if re.fullmatch(r"[0-9a-f]{32}", supplied) else uuid.uuid4().hex
        g.service = service
        g.started = time.perf_counter()
        g.authenticated_user = None
        g.database_role = role
        g.authorization_result = "public"

    @app.after_request
    def finish_request(response):
        response.headers["X-Request-ID"] = g.request_id
        response.headers["Cache-Control"] = "no-store"
        emit(
            "http_request", endpoint=request.url_rule.rule if request.url_rule else "unmatched",
            method=request.method, authenticated_user=g.authenticated_user,
            database_role=g.database_role, http_status=response.status_code,
            authorization_result=g.authorization_result,
            execution_time_ms=round((time.perf_counter() - g.started) * 1000, 3),
        )
        return response

    @app.teardown_appcontext
    def close_connection(_error):
        conn = g.pop("db", None)
        if conn is not None:
            conn.close()

    @app.errorhandler(HTTPException)
    def http_error(error):
        return jsonify(error=error.name.lower().replace(" ", "_")), error.code

    @app.errorhandler(psycopg.Error)
    def database_error(error):
        # Never render DB exception strings, SQL text with values, or DSNs.
        emit("database_error", sqlstate=error.sqlstate, database_role=g.database_role)
        return jsonify(error="database_unavailable"), 503

    @app.errorhandler(Exception)
    def internal_error(error):
        emit("application_error", error_type=type(error).__name__)
        return jsonify(error="internal_error"), 500

    @app.get("/health")
    def health():
        row = query("health.identity", "SELECT current_user AS database_role", fetch="one")
        g.database_role = row["database_role"]
        # A successful TCP connection alone is not application readiness.
        if service == "catalog":
            query("health.catalog", "SELECT item_key FROM catalog.public_products LIMIT 1", fetch="one")
        else:
            query("health.orders", "SELECT id FROM private.orders LIMIT 1", fetch="one")
            query("health.sessions", "SELECT token_hash FROM auth.sessions LIMIT 0")
        return jsonify(status="ok", service=service, database_role=g.database_role,
                       query_mode="bound", ownership_enforced=(service == "orders"))

    return app


def get_db():
    if "db" not in g:
        g.db = psycopg.connect(
            host=os.getenv("DB_HOST", "postgres"), port=int(os.getenv("DB_PORT", "5432")),
            dbname=os.environ["DB_NAME"], user=os.environ["DB_USER"],
            password=os.environ["DB_PASSWORD"], connect_timeout=3, autocommit=True,
            row_factory=dict_row, application_name="minishop-" + g.service,
            options="-c search_path=pg_catalog -c statement_timeout=3000 -c lock_timeout=1000 -c idle_in_transaction_session_timeout=5000",
        )
        g.database_role = g.db.execute("SELECT current_user").fetchone()["current_user"]
    return g.db


def query(template_id, sql_template, params=(), *, fetch=None):
    """Only code-owned SQL templates. Values are bound, and all values are redacted in logs."""
    started = time.perf_counter()
    fields = {
        "template_id": template_id, "sql_template": " ".join(sql_template.split()),
        "binding": "parameters", "parameter_count": len(params),
        "parameters": [{"type": type(value).__name__, "value": "[REDACTED]"} for value in params],
    }
    try:
        cur = get_db().execute(sql_template, params)
        if fetch == "one":
            result = cur.fetchone()
        elif fetch == "all":
            result = cur.fetchall()
        else:
            result = None
        fields.update(database_role=g.database_role, row_count=cur.rowcount, outcome="ok")
        return result
    except psycopg.Error as error:
        fields.update(database_role=g.database_role, outcome="error", sqlstate=error.sqlstate)
        raise
    finally:
        fields["execution_time_ms"] = round((time.perf_counter() - started) * 1000, 3)
        emit("db_query", **fields)
