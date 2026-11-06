"""Generate per-install lab secrets using only Python's standard library."""
import hashlib
import os
import secrets
from pathlib import Path

from network_config import auto_bind, validate_bind


ROOT = Path(__file__).resolve().parents[1]


def password_hash(password):
    salt = secrets.token_hex(16)
    value = hashlib.pbkdf2_hmac("sha256", password.encode(), salt.encode(), 1_000_000).hex()
    return f"pbkdf2:sha256:1000000${salt}${value}"


def parse_env(path):
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip().strip("'\"")
    return values


def main(bind_address=None):
    path = ROOT / ".env"
    legacy = {}
    if path.exists():
        legacy = parse_env(path)
        if "WEB_PORT" in legacy and "POSTGRES_PASSWORD" not in legacy:
            backup = ROOT / ".env.sqlite-backup"
            if backup.exists():
                raise ValueError("Legacy .env backup already exists; inspect it before retrying")
            path.rename(backup)
            if os.name == "posix":
                backup.chmod(0o600)
            print("Preserved SQLite configuration as .env.sqlite-backup; instance/ data remains unchanged.")
        else:
            required = ("POSTGRES_PASSWORD", "CATALOG_READER_PASSWORD", "CATALOG_READER_WIDE_PASSWORD",
                        "ORDER_SERVICE_PASSWORD", "DEMO_USER1_PASSWORD", "DEMO_USER2_PASSWORD",
                        "DEMO_USER1_PASSWORD_HASH", "DEMO_USER2_PASSWORD_HASH")
            if any(not legacy.get(key) for key in required):
                raise ValueError("Existing .env is incomplete; it was preserved to avoid changing database credentials")
            if bind_address is not None:
                checked = validate_bind(bind_address)
                lines = path.read_text(encoding="utf-8").splitlines()
                updated = ["BIND_ADDRESS=" + checked if line.startswith("BIND_ADDRESS=") else line for line in lines]
                if not any(line.startswith("BIND_ADDRESS=") for line in lines):
                    updated.append("BIND_ADDRESS=" + checked)
                path.write_text("\n".join(updated) + "\n", encoding="utf-8")
            print("Existing .env preserved. Database credentials were not changed.")
            return
    selected_bind = validate_bind(bind_address if bind_address is not None else auto_bind())
    values = {
        "COMPOSE_PROJECT_NAME": "minishop", "BIND_ADDRESS": selected_bind, "HTTP_PORT": "18080",
        "LAB_EXPERIMENT": "E4",
        "POSTGRES_DB": "minishop", "POSTGRES_USER": "minishop_admin",
        "POSTGRES_PASSWORD": secrets.token_urlsafe(32),
        "CATALOG_READER_PASSWORD": secrets.token_urlsafe(32),
        "CATALOG_READER_WIDE_PASSWORD": secrets.token_urlsafe(32),
        "ORDER_SERVICE_PASSWORD": secrets.token_urlsafe(32),
        "DEMO_USER1_PASSWORD": secrets.token_urlsafe(18),
        "DEMO_USER2_PASSWORD": secrets.token_urlsafe(18),
        "SESSION_COOKIE_SECURE": "false",
        "TEST_UID": str(os.getuid()) if hasattr(os, "getuid") else "10001",
        "TEST_GID": str(os.getgid()) if hasattr(os, "getgid") else "10001",
    }
    for number in (1, 2):
        # Single quotes prevent Compose from interpreting dollar signs in Werkzeug hashes.
        values[f"DEMO_USER{number}_PASSWORD_HASH"] = "'" + password_hash(values[f"DEMO_USER{number}_PASSWORD"]) + "'"
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
        stream.write("# Local generated secrets. Do not commit or share this file.\n")
        for key, value in values.items():
            stream.write(f"{key}={value}\n")
    print("Created .env with unique secrets and PBKDF2-SHA256 password hashes (1,000,000 iterations).")
    print("Local demo login credentials: python3 scripts/demo_credentials.py")


if __name__ == "__main__":
    main()
