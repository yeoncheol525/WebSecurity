"""Run inside Kali against the authorized Ubuntu lab; no SQLi payloads or DB credentials."""
import argparse
import getpass
import http.cookiejar
import ipaddress
import json
import platform
import socket
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone


def main():
    # JSON on stdin contains only temporary web-test credentials; nothing is saved or echoed.
    parser = argparse.ArgumentParser(description="Run Kali-to-Ubuntu checks using only synthetic web credentials")
    parser.add_argument("--server", default="192.168.67.20")
    args = parser.parse_args()
    if sys.stdin.isatty():
        config = {"server_ip": args.server,
                  "user1_password": getpass.getpass("Ubuntu MiniShop user1 password: "),
                  "user2_password": getpass.getpass("Ubuntu MiniShop user2 password: ")}
    else:
        config = json.load(sys.stdin)
    address = config.get("server_ip", "192.168.67.20")
    if not ipaddress.ip_address(address).is_private:
        raise RuntimeError("The test target must be the private Ubuntu lab address")
    base_url = f"http://{address}:18080"
    checks = []

    def record(test_id, description, good, **evidence):
        checks.append({"test_id": test_id, "description": description,
                       "status": "PASS" if good else "FAIL", **evidence})

    def request(opener, path, body=None, headers=None):
        request_headers = dict(headers or {})
        if body is not None:
            request_headers["Content-Type"] = "application/json"
        req = urllib.request.Request(base_url + path, headers=request_headers,
                                     data=json.dumps(body).encode() if body is not None else None)
        try:
            response = opener.open(req, timeout=10)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            data = json.load(response)
            return response.status, data, dict(response.headers)

    anon = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    status, data, headers = request(anon, "/products")
    record("K01", "Kali to Ubuntu public products", status == 200 and len(data.get("products", [])) == 12,
           http_status=status, product_count=len(data.get("products", [])), request_id=headers.get("X-Request-ID"))
    catalog_status, catalog, _ = request(anon, "/health/catalog")
    order_status, orders, _ = request(anon, "/health/orders")
    record("K02", "Two upstream services and safe roles through Nginx",
           catalog_status == order_status == 200 and catalog.get("database_role") == "catalog_reader"
           and orders.get("database_role") == "order_service" and catalog.get("query_mode") == "bound",
           catalog_role=catalog.get("database_role"), order_role=orders.get("database_role"))
    status, data, _ = request(anon, "/orders")
    record("K03", "Anonymous order access denied", status == 401, http_status=status)

    for number, own, other in ((1, 1001, 2002), (2, 2002, 1001)):
        cookies = http.cookiejar.CookieJar()
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), urllib.request.HTTPCookieProcessor(cookies))
        status, login, _ = request(opener, "/login", {"username": f"user{number}", "password": config[f"user{number}_password"]})
        if status != 200:
            record(f"K0{number+3}", f"user{number} login and own order", False, http_status=status)
            continue
        own_status, own_body, _ = request(opener, f"/orders/{own}")
        other_status, other_body, _ = request(opener, f"/orders/{other}")
        record(f"K0{number+3}", f"user{number} own order allowed and other user's order denied",
               own_status == 200 and own_body.get("order", {}).get("id") == own
               and other_status == 404 and other_body == {"error": "not_found"},
               own_order_status=own_status, other_order_status=other_status)
        logout_status, _, _ = request(opener, "/logout", {}, {"X-CSRF-Token": login["csrf_token"]})
        if logout_status != 200:
            record(f"K_LOGOUT_{number}", "Logout", False, http_status=logout_status)

    closed = {}
    for port in (5432, 8000):
        try:
            with socket.create_connection((address, port), timeout=2):
                closed[str(port)] = False
        except OSError:
            closed[str(port)] = True
    record("K06", "PostgreSQL and application ports unreachable directly", all(closed.values()), ports_closed=closed)
    routes = json.loads(subprocess.check_output(["ip", "-j", "route"], text=True))
    route_to_server = json.loads(subprocess.check_output(["ip", "-j", "route", "get", address], text=True))[0]
    no_default = not any(route.get("dst") == "default" for route in routes)
    source_ip = route_to_server.get("prefsrc", route_to_server.get("src"))
    record("K07", "Kali traffic uses Host-only with no default internet route",
           no_default and source_ip == "192.168.67.10" and route_to_server.get("dev") == "eth1",
           source_ip=source_ip, interface=route_to_server.get("dev"), default_route_present=not no_default)
    with socket.create_connection((address, 18080), timeout=3) as connection:
        source = connection.getsockname()[0]
    record("K08", "Actual HTTP TCP source address", source == "192.168.67.10", source_ip=source, destination=base_url)
    result = {"timestamp": datetime.now(timezone.utc).isoformat(), "client_hostname": socket.gethostname(),
              "client_os": platform.freedesktop_os_release().get("PRETTY_NAME", "Linux"),
              "target": base_url, "passed": all(check["status"] == "PASS" for check in checks), "checks": checks}
    print(json.dumps(result, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
