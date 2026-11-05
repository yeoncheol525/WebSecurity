import os

import psycopg
import pytest
import requests


def test_T03_catalog_products_select(db):
    with db("catalog_reader") as conn:
        assert conn.execute("SELECT current_user").fetchone()[0] == "catalog_reader"
        assert conn.execute("SELECT count(*) FROM catalog.products").fetchone()[0] == 12
        assert conn.execute("SELECT count(*) FROM catalog.public_products").fetchone()[0] == 12
        assert conn.execute("SELECT count(*) FROM catalog.products WHERE NOT is_public").fetchone()[0] == 0


def test_T04_catalog_customers_permission_denied(db):
    with db("catalog_reader") as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege) as caught:
            conn.execute("SELECT id FROM private.customers LIMIT 1")
        assert caught.value.sqlstate == "42501"


@pytest.mark.parametrize("table", ["private.orders", "auth.users", "private.payment_meta"])
def test_T05_catalog_other_private_tables_denied(db, table):
    # Identifiers below are fixed test constants, never request data.
    with db("catalog_reader") as conn:
        with pytest.raises(psycopg.errors.InsufficientPrivilege) as caught:
            conn.execute("SELECT id FROM " + table + " LIMIT 1")
        assert caught.value.sqlstate == "42501"


def test_T06_order_role_normal_select(db):
    with db("order_service") as conn:
        result = conn.execute(
            "SELECT o.id FROM private.orders o JOIN private.customers c ON c.id=o.customer_id "
            "WHERE c.user_id=%s ORDER BY o.id", (1,),
        ).fetchall()
        assert [row[0] for row in result] == [1001, 1002, 1003]
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT email FROM private.customers LIMIT 1")
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            conn.execute("SELECT id FROM private.payment_meta LIMIT 1")


@pytest.mark.parametrize("role", ["catalog_reader", "order_service", "catalog_reader_wide"])
def test_no_privileged_roles_memberships_or_public_ddl(db, role):
    with db(os.environ["DB_ADMIN_USER"]) as conn:
        flags = conn.execute("SELECT rolsuper, rolcreatedb, rolcreaterole, rolreplication, rolbypassrls, rolinherit "
                             "FROM pg_roles WHERE rolname=%s", (role,)).fetchone()
        assert flags == (False,) * 6
        assert conn.execute("SELECT count(*) FROM pg_auth_members m JOIN pg_roles r ON r.oid=m.member "
                            "WHERE r.rolname=%s", (role,)).fetchone()[0] == 0
        for privilege in ("CREATE", "TEMPORARY"):
            assert conn.execute("SELECT has_database_privilege(%s, current_database(), %s)",
                                (role, privilege)).fetchone()[0] is False
        for schema in ("public", "catalog", "private", "auth"):
            assert conn.execute("SELECT has_schema_privilege(%s,%s,'CREATE')", (role, schema)).fetchone()[0] is False
        for schema in ("private", "auth"):
            assert conn.execute("SELECT has_schema_privilege('catalog_reader',%s,'USAGE')", (schema,)).fetchone()[0] is False


def test_catalog_write_and_ddl_denied(db):
    with db("catalog_reader") as conn:
        for statement in (
            "INSERT INTO catalog.products (name,description,price) VALUES ('Test','Test',1)",
            "UPDATE catalog.products SET price=0 WHERE id=1",
            "DELETE FROM catalog.products WHERE id=1",
            "CREATE TABLE catalog.forbidden (id integer)",
            "CREATE TABLE public.forbidden (id integer)",
            "CREATE TEMP TABLE forbidden (id integer)",
        ):
            with pytest.raises(psycopg.errors.InsufficientPrivilege):
                conn.execute(statement)


def test_T12_wide_role_bounded_test_then_restore(db, base_url):
    with db(os.environ["DB_ADMIN_USER"]) as admin:
        admin.execute("SELECT pg_advisory_lock(20261105)")
        try:
            assert admin.execute("SELECT rolcanlogin FROM pg_roles WHERE rolname='catalog_reader_wide'").fetchone()[0] is False
            # Role credentials exist only in the ephemeral verifier and database, not the Catalog container.
            activation = admin.execute("SELECT format('ALTER ROLE catalog_reader_wide LOGIN VALID UNTIL %L', "
                                       "clock_timestamp() + interval '5 minutes')").fetchone()[0]
            admin.execute(activation)
            try:
                with db("catalog_reader_wide") as wide:
                    assert wide.execute("SELECT current_user").fetchone()[0] == "catalog_reader_wide"
                    assert wide.execute("SELECT count(*) FROM private.customers").fetchone()[0] == 100
                    assert wide.execute("SELECT count(*) FROM private.orders").fetchone()[0] == 300
                    assert wide.execute("SELECT count(*) FROM private.payment_meta").fetchone()[0] == 300
                    with pytest.raises(psycopg.errors.InsufficientPrivilege):
                        wide.execute("SELECT id FROM auth.users LIMIT 1")
            finally:
                admin.execute("ALTER ROLE catalog_reader_wide NOLOGIN VALID UNTIL '1970-01-01'")
                admin.execute("SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                              "WHERE usename='catalog_reader_wide' AND pid<>pg_backend_pid()")
            assert admin.execute("SELECT rolcanlogin FROM pg_roles WHERE rolname='catalog_reader_wide'").fetchone()[0] is False
        finally:
            admin.execute("SELECT pg_advisory_unlock(20261105)")
    with db("catalog_reader") as limited:
        with pytest.raises(psycopg.errors.InsufficientPrivilege):
            limited.execute("SELECT id FROM private.customers LIMIT 1")
    assert requests.get(base_url + "/health/catalog", timeout=5).json()["database_role"] == "catalog_reader"
