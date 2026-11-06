import json
import subprocess
import sys
import urllib.request

from lab_support import ROOT, read_env


def main():
    # Reuse the same selection path as setup; the saved condition must also become E4.
    subprocess.run([sys.executable, str(ROOT / "scripts/setup.py"), "--experiment", "E4"], check=True)
    values = read_env()
    url = f"http://{values['BIND_ADDRESS']}:{values['HTTP_PORT']}/health/catalog"
    with urllib.request.urlopen(url, timeout=5) as response:
        data = json.load(response)
    if data["database_role"] != "catalog_reader" or data["query_mode"] != "bound":
        raise RuntimeError("Safe mode verification failed")
    print("Safe mode restored: catalog_reader / bound SQL; wide role NOLOGIN, existing wide connections revoked.")


if __name__ == "__main__":
    main()
