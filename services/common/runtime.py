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
    mode = os.getenv("SQL_QUERY_MODE", "bound")
    if mode not in ("bound", "interpolated"):
        raise RuntimeError("Unknown SQL query mode")
    lab = os.getenv("LAB_EXPERIMENTS_ENABLED") == "true"
    if mode == "interpolated" and not (service == "catalog" and lab):
        raise RuntimeError("Interpolated search requires an explicit Catalog experiment")
    app.config["SQL_QUERY_MODE"] = mode
    # Orders-only lab toggles for auxiliary experiments A (login SQLi) and C2 (IDOR).
    # Both default to the secure value and only unlock under an explicit Orders experiment.
    login_mode = os.getenv("LOGIN_SQL_MODE", "bound")
    if login_mode not in ("bound", "interpolated"):
        raise RuntimeError("Unknown login SQL mode")
    if login_mode == "interpolated" and not (service == "orders" and lab):
        raise RuntimeError("Vulnerable login requires an explicit Orders experiment")
    ownership = os.getenv("OWNERSHIP_CHECK", "on")
    if ownership not in ("on", "off"):
        raise RuntimeError("OWNERSHIP_CHECK must be on or off")
    if ownership == "off" and not (service == "orders" and lab):
        raise RuntimeError("Disabling the ownership check requires an explicit Orders experiment")
    app.config["LOGIN_SQL_MODE"] = login_mode
    app.config["OWNERSHIP_CHECK"] = ownership

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
                       query_mode=mode,
                       ownership_enforced=(service == "orders" and app.config["OWNERSHIP_CHECK"] == "on"),
                       login_sql_mode=app.config.get("LOGIN_SQL_MODE", "bound"))

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
    return _execute_query(template_id, sql_template, params, fetch=fetch)


def interpolated_search(sql_template, search_value):
    """Deliberately vulnerable E1/E3 search. Never use for authentication or orders."""
    from flask import current_app

    if (g.service != "catalog" or current_app.config["SQL_QUERY_MODE"] != "interpolated"
            or os.getenv("LAB_EXPERIMENTS_ENABLED") != "true"):
        raise RuntimeError("Interpolated search is disabled outside E1/E3")
    if sql_template.count("%s") != 1:
        raise ValueError("The experiment search template must have exactly one value")
    statement = sql_template.replace("%s", "'" + search_value + "'")
    return _execute_query("catalog.search", sql_template, (search_value,), fetch="all", statement=statement)


def interpolated_query(template_id, sql_template, statement, *, fetch=None):
    """Lab-only raw-statement execution for Orders experiments (A). Gated like interpolated_search."""
    if os.getenv("LAB_EXPERIMENTS_ENABLED") != "true":
        raise RuntimeError("Interpolated query is disabled outside an explicit experiment")
    return _execute_query(template_id, sql_template, (), fetch=fetch, statement=statement)


def _execute_query(template_id, sql_template, params, *, fetch, statement=None):
    started = time.perf_counter()
    fields = {
        "template_id": template_id, "sql_template": " ".join(sql_template.split()),
        "binding": "interpolated" if statement is not None else "parameters", "parameter_count": len(params),
        "parameters": [{"type": type(value).__name__, "value": "[REDACTED]"} for value in params],
    }
    try:
        # Keep the interpolated statement out of logs, including on database errors.
        cur = get_db().execute(statement) if statement is not None else get_db().execute(sql_template, params)
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
