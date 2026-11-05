import json
import urllib.request

from lab_support import admin_sql, compose, read_env


def main():
    admin_sql("ALTER ROLE catalog_reader_wide NOLOGIN VALID UNTIL '1970-01-01';\n"
              "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
              "WHERE usename='catalog_reader_wide' AND pid<>pg_backend_pid();")
    # Explicit base file removes any previously applied experiment override.
    compose("-f", "docker-compose.yml", "up", "-d", "--no-deps", "--wait",
            "--wait-timeout", "120", "catalog-service", "nginx")
    values = read_env()
    url = f"http://{values['BIND_ADDRESS']}:{values['HTTP_PORT']}/health/catalog"
    with urllib.request.urlopen(url, timeout=5) as response:
        data = json.load(response)
    if data["database_role"] != "catalog_reader" or data["query_mode"] != "bound":
        raise RuntimeError("Safe mode verification failed")
    print("Safe mode restored: catalog_reader / bound SQL; wide role NOLOGIN, existing wide connections revoked.")


if __name__ == "__main__":
    main()
