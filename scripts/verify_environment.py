"""Real Docker/PostgreSQL/HTTP checks. Does not emulate DB permissions or delete data."""
import argparse
import csv
import http.cookiejar
import json
import platform
import re
import socket
import subprocess
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as ET
from datetime import datetime, timedelta, timezone

from lab_support import ROOT, admin_sql, compose, inspect_service, read_env, selected_experiment


def http_json(opener, base_url, path, body=None, headers=None):
    request_headers = dict(headers or {})
    if body is not None:
        request_headers["Content-Type"] = "application/json"
    request = urllib.request.Request(base_url + path,
                                     data=json.dumps(body).encode() if body is not None else None,
                                     headers=request_headers)
    with opener.open(request, timeout=15) as response:
        return json.load(response)


def main():
    parser = argparse.ArgumentParser(description="Verify T01-T12; restarts only this lab's four containers")
    parser.add_argument("--no-build", action="store_true", help="Use the already built service/test images")
    args = parser.parse_args()
    values = read_env()
    if selected_experiment(values) != "E4":
        parser.error("Developer regression checks require E4; select it explicitly with setup.py --experiment E4. No condition was changed.")
    run_id = datetime.now(timezone(timedelta(hours=9))).strftime("%Y%m%dT%H%M%S_KST")
    result_dir = ROOT / "results" / run_id
    result_dir.mkdir(parents=True)
    base_url = f"http://{values['BIND_ADDRESS']}:{values['HTTP_PORT']}"
    compose("config", "--quiet")
    up = ["up", "-d", "--wait", "--wait-timeout", "180"]
    if not args.no_build:
        up.append("--build")
    compose(*up, timeout=600)
    if not args.no_build:
        compose("--profile", "verification", "build", "tester", timeout=600)

    rows = []
    try:
        tested = compose("--profile", "verification", "run", "--rm", "--no-deps", "tester",
                         "python", "-m", "pytest", "tests", "-v", "-rA", "-p", "no:cacheprovider",
                         f"--junitxml=/results/{run_id}/junit.xml", capture=True, check=False)
        (result_dir / "pytest.txt").write_text(tested.stdout + tested.stderr, encoding="utf-8")
        cases = ET.parse(result_dir / "junit.xml").getroot().findall(".//testcase")
        for case in cases:
            match = re.search(r"T\d{2}", case.attrib["name"])
            failure = case.find("failure")
            error = case.find("error")
            skipped = case.find("skipped")
            status = "FAIL" if failure is not None or error is not None else "SKIP" if skipped is not None else "PASS"
            rows.append({"test_id": match.group() if match else "EXTRA", "case": case.attrib["name"],
                         "status": status, "evidence": "junit.xml", "detail": "Real HTTP/PostgreSQL assertions"})
        print(f"Container tests: {sum(r['status']=='PASS' for r in rows)}/{len(rows)} cases passed")

        # T10: verify both data and an already issued server-side session survive restart.
        cookies = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookies))
        try:
            login = http_json(opener, base_url, "/login", {"username": "user1", "password": values["DEMO_USER1_PASSWORD"]})
            before = http_json(opener, base_url, "/orders/1001")["order"]
            seed_before = admin_sql("SELECT (SELECT count(*) FROM private.customers), "
                                    "(SELECT count(*) FROM private.orders), (SELECT count(*) FROM private.payment_meta);")
            compose("restart", "postgres", "catalog-service", "order-service", "nginx")
            compose("up", "-d", "--wait", "--wait-timeout", "180")
            after = http_json(opener, base_url, "/orders/1001")["order"]
            seed_after = admin_sql("SELECT (SELECT count(*) FROM private.customers), "
                                   "(SELECT count(*) FROM private.orders), (SELECT count(*) FROM private.payment_meta);")
            if before != after or seed_before != seed_after or seed_after != "100|300|300":
                raise AssertionError("Data or session changed across restart")
            http_json(opener, base_url, "/logout", {}, {"X-CSRF-Token": login["csrf_token"]})
            rows.append({"test_id": "T10", "case": "container_restart", "status": "PASS", "evidence": "host_checks.json",
                         "detail": "All four restarted; existing session and order survived; seed counts 100/300/300 preserved"})
        except Exception as error:
            rows.append({"test_id": "T10", "case": "container_restart", "status": "FAIL", "evidence": "host_checks.json",
                         "detail": type(error).__name__})

        # T11: check Docker publication AND a real connection from the host, outside the private network.
        try:
            publication = {}
            for service in ("postgres", "catalog-service", "order-service"):
                publication[service] = inspect_service(service, "{{json .NetworkSettings.Ports}}")
                if any(binding for binding in publication[service].values()):
                    raise AssertionError("Backend port published")
            host = values["BIND_ADDRESS"]
            try:
                with socket.create_connection((host, 5432), timeout=2):
                    reachable = True
            except OSError:
                reachable = False
            if reachable:
                raise AssertionError("Host port 5432 is reachable; investigate before claiming isolation")
            rows.append({"test_id": "T11", "case": "postgres_not_published", "status": "PASS", "evidence": "host_checks.json",
                         "detail": f"No backend HostPort; TCP {host}:5432 unreachable from Docker host. Kali VM check remains separate."})
        except Exception as error:
            rows.append({"test_id": "T11", "case": "postgres_not_published", "status": "FAIL", "evidence": "host_checks.json",
                         "detail": type(error).__name__})

        # Capture logs without request bodies, passwords, tokens, parameter values, or synthetic PII.
        log_output = compose("logs", "--no-color", "--no-log-prefix", "catalog-service", "order-service", capture=True)
        audit = []
        for line in log_output.stdout.splitlines():
            try:
                item = json.loads(line)
            except (ValueError, TypeError):
                continue
            if isinstance(item, dict) and item.get("event") in ("http_request", "db_query", "database_error", "application_error"):
                audit.append(item)
        http_events = [item for item in audit if item.get("event") == "http_request"]
        required = {"timestamp", "request_id", "service", "endpoint", "authenticated_user", "database_role",
                    "http_status", "authorization_result", "execution_time_ms"}
        audit_text = "\n".join(json.dumps(item) for item in audit)
        forbidden = [value for key, value in values.items() if "PASSWORD" in key and value]
        forbidden.extend(cookie.value for cookie in cookies)
        log_ok = bool(http_events) and all(required <= event.keys() for event in http_events)
        log_ok = log_ok and not any(secret in log_output.stdout for secret in forbidden)
        log_ok = log_ok and "@example.invalid" not in audit_text
        rows.append({"test_id": "EXTRA", "case": "audit_fields_and_redaction", "status": "PASS" if log_ok else "FAIL",
                     "evidence": "audit_events.jsonl", "detail": f"{len(http_events)} request events; required fields and secret/PII scan"})
        (result_dir / "audit_events.jsonl").write_text(audit_text + "\n", encoding="utf-8")
        versions_code = "import importlib.metadata as m,json,platform;print(json.dumps({'python':platform.python_version(),**{n:m.version(n) for n in ['Flask','Werkzeug','psycopg','psycopg-binary','gunicorn']}}))"
        versions = json.loads(compose("exec", "-T", "catalog-service", "python", "-c", versions_code, capture=True).stdout)
        versions["postgresql"] = admin_sql("SHOW server_version;")
        nginx_version = compose("exec", "-T", "nginx", "nginx", "-v", capture=True)
        versions["nginx"] = (nginx_version.stdout + nginx_version.stderr).strip()
        versions["docker_compose"] = subprocess.run(["docker", "compose", "version", "--short"], capture_output=True,
                                                     check=True, text=True, timeout=30).stdout.strip()
        versions["image_ids"] = {service: inspect_service(service, "{{json .Image}}")
                                  for service in ("postgres", "nginx", "catalog-service", "order-service")}
        (result_dir / "versions.json").write_text(json.dumps(versions, indent=2), encoding="utf-8")
        print("Runtime versions: " + json.dumps(versions, ensure_ascii=True))
    finally:
        # Also runs if the test container is killed or a test fails before its own cleanup.
        admin_sql("ALTER ROLE catalog_reader_wide NOLOGIN VALID UNTIL '1970-01-01';\n"
                  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                  "WHERE usename='catalog_reader_wide' AND pid<>pg_backend_pid();")

    with (result_dir / "test_results.csv").open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=["test_id", "case", "status", "evidence", "detail"])
        writer.writeheader()
        writer.writerows(rows)
    host_rows = [row for row in rows if row["test_id"] in ("T10", "T11")]
    (result_dir / "host_checks.json").write_text(json.dumps(host_rows, indent=2), encoding="utf-8")
    logical = {}
    for number in range(1, 13):
        test_id = f"T{number:02}"
        statuses = [row["status"] for row in rows if row["test_id"] == test_id]
        logical[test_id] = "PASS" if statuses and all(value == "PASS" for value in statuses) else "FAIL"
        print(f"{test_id}: {logical[test_id]}")
    passed = all(value == "PASS" for value in logical.values()) and all(row["status"] == "PASS" for row in rows)
    execution_host = {"os": platform.system(), "kernel": platform.release(), "python": platform.python_version()}
    if hasattr(platform, "freedesktop_os_release") and platform.system() == "Linux":
        execution_host["distribution"] = platform.freedesktop_os_release().get("PRETTY_NAME", "Linux")
        detected = subprocess.run(["systemd-detect-virt"], capture_output=True, text=True, check=False, timeout=10)
        execution_host["virtualization"] = detected.stdout.strip() or "unknown"
    summary = {"run_id": run_id, "passed": passed, "logical_tests": logical, "assertion_cases": len(rows),
               "case_passes": sum(row["status"] == "PASS" for row in rows), "base_url": base_url,
               "execution_host": execution_host,
               "vm_validation": "T01-T12 verify this Docker host. Cross-VM client results are recorded separately by verify_kali_client.py.",
               "results_directory": str(result_dir)}
    (result_dir / "summary.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    (ROOT / "results" / "latest.json").write_text(json.dumps(summary, indent=2), encoding="utf-8")
    print(f"{'PASS' if passed else 'FAIL'}: {summary['case_passes']}/{len(rows)} cases. Evidence: {result_dir}")
    return 0 if passed else 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (subprocess.SubprocessError, OSError, ValueError, ET.ParseError) as error:
        print(f"Verification could not finish ({type(error).__name__}); do not claim T01-T12 passed.", file=sys.stderr)
        raise SystemExit(1)
