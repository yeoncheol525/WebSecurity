"""Optional real Firefox UI check inside Kali (stdlib + installed geckodriver/Firefox)."""
import base64
import json
import socket
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path


def main():
    config = json.load(sys.stdin)
    base = config["base_url"].rstrip("/")
    with socket.socket() as reservation:
        reservation.bind(("127.0.0.1", 0))
        port = reservation.getsockname()[1]
    with tempfile.TemporaryDirectory(prefix="minishop-browser-") as temporary:
        with open(Path(temporary) / "geckodriver.log", "w") as log:
            process = subprocess.Popen(["geckodriver", "--host", "127.0.0.1", "--port", str(port)], stdout=log, stderr=log)
        endpoint = f"http://127.0.0.1:{port}"
        session = None
        checks = []

        def command(method, path, value=None):
            request = urllib.request.Request(endpoint + path, method=method,
                                             data=json.dumps(value).encode() if value is not None else None,
                                             headers={"Content-Type": "application/json"})
            with urllib.request.urlopen(request, timeout=45) as response:
                return json.load(response)["value"]

        def execute(script):
            return command("POST", f"/session/{session}/execute/sync", {"script": script, "args": []})

        def wait(script, description):
            limit = time.monotonic() + 20
            while time.monotonic() < limit:
                if execute(script):
                    return
                time.sleep(0.2)
            raise AssertionError("Browser timeout: " + description)

        def visit(path):
            command("POST", f"/session/{session}/url", {"url": base + path})

        def element(selector):
            value = command("POST", f"/session/{session}/element", {"using": "css selector", "value": selector})
            return value["element-6066-11e4-a52e-4f735466cecf"]

        def type_text(selector, text):
            command("POST", f"/session/{session}/element/{element(selector)}/value", {"text": text})

        def click(selector):
            command("POST", f"/session/{session}/element/{element(selector)}/click", {})

        try:
            deadline = time.monotonic() + 15
            while True:
                try:
                    command("GET", "/status")
                    break
                except OSError:
                    if time.monotonic() > deadline:
                        raise
                    time.sleep(0.2)
            created = command("POST", "/session", {"capabilities": {"alwaysMatch": {"browserName": "firefox",
                                "moz:firefoxOptions": {"args": ["-headless"]}}}})
            session = created["sessionId"]
            command("POST", f"/session/{session}/window/rect", {"width": 1366, "height": 900})
            visit("/")
            wait("return !!document.querySelector('.shopping-bag') && !!document.querySelector('#login-link')", "home")
            checks.append("B01 original home layout")
            visit("/shop")
            wait("return document.querySelectorAll('.product-card').length === 12", "product list")
            checks.append("B02 products rendered from Catalog API")
            visit("/shop?q=O%27Reilly")
            wait("return document.querySelectorAll('.product-card').length === 1", "apostrophe search")
            checks.append("B03 normal search with apostrophe")
            visit("/login")
            type_text("#username", "user1")
            type_text("#password", "incorrect")
            click("#login-form button")
            wait("return !document.querySelector('#page-message').hidden", "invalid login")
            checks.append("B04 invalid login feedback")
            command("POST", f"/session/{session}/element/{element('#password')}/clear", {})
            type_text("#password", config["user1_password"])
            click("#login-form button")
            wait("return location.pathname === '/account/orders' && document.querySelectorAll('#order-list tr').length === 3", "login and orders")
            assert execute("return [...document.querySelectorAll('.order-number')].map(x=>x.textContent).join(',')") == "#1001,#1002,#1003"
            checks.append("B05 login and own orders")
            screenshot = command("GET", f"/session/{session}/screenshot")
            Path(config.get("screenshot", "/home/kali/minishop-ui.png")).write_bytes(base64.b64decode(screenshot))
            visit("/account/orders/1001")
            wait("return !document.querySelector('#order-detail').hidden", "own order detail")
            checks.append("B06 own order detail")
            visit("/account/orders/2002")
            wait("return !document.querySelector('#page-message').hidden", "other order denied")
            assert execute("return document.querySelector('#order-detail').hidden") is True
            checks.append("B07 other user's order body stays hidden")
            click("#logout-button")
            wait("return location.pathname === '/' && !document.querySelector('#login-link').hidden", "logout")
            checks.append("B08 server-side logout")
            print(json.dumps({"passed": True, "target": base, "browser": created["capabilities"]["browserVersion"], "checks": checks}, indent=2))
        finally:
            if session:
                try:
                    command("DELETE", f"/session/{session}")
                except OSError:
                    pass
            process.terminate()
            process.wait(timeout=10)


if __name__ == "__main__":
    main()
