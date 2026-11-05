"""Host-side helpers. Never print Compose's resolved environment or container secrets."""
import json
import os
import subprocess
from functools import lru_cache
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def read_env():
    result = {}
    for line in (ROOT / ".env").read_text(encoding="utf-8").splitlines():
        if line.strip() and not line.lstrip().startswith("#"):
            key, value = line.split("=", 1)
            result[key.strip()] = value.strip().strip("'\"")
    return result


@lru_cache(maxsize=1)
def docker_prefix():
    if os.environ.get("MINISHOP_DOCKER_SUDO") == "1" and os.name == "posix":
        return ["sudo", "-n", "docker"]
    probe = subprocess.run(["docker", "info", "--format", "{{.ServerVersion}}"], capture_output=True, timeout=30)
    if probe.returncode == 0:
        return ["docker"]
    if os.name == "posix":
        elevated = subprocess.run(["sudo", "-n", "docker", "info", "--format", "{{.ServerVersion}}"],
                                   capture_output=True, timeout=30)
        if elevated.returncode == 0:
            return ["sudo", "-n", "docker"]
    raise RuntimeError("The local Docker Engine is unavailable; run bash scripts/setup-ubuntu.sh")


def compose(*args, capture=False, check=True, timeout=300, input_text=None):
    # Isolate this project's generated .env from unrelated shell variables.
    environment = os.environ.copy()
    environment.update(read_env())
    for name in ("COMPOSE_FILE", "COMPOSE_PROFILES", "COMPOSE_ENV_FILES"):
        environment.pop(name, None)
    compose_files = [] if "-f" in args or "--file" in args else ["-f", str(ROOT / "docker-compose.yml")]
    return subprocess.run(
        [*docker_prefix(), "compose", "--project-directory", str(ROOT), "--env-file", str(ROOT / ".env"), *compose_files, *args],
        cwd=ROOT, env=environment, check=check, text=True, encoding="utf-8", errors="replace",
        capture_output=capture, timeout=timeout, input=input_text,
    )


def admin_sql(statement):
    return compose("exec", "-T", "postgres", "sh", "-c",
                   'exec psql -U "$POSTGRES_USER" -d "$POSTGRES_DB" -v ON_ERROR_STOP=1 -At',
                   capture=True, input_text=statement + "\n").stdout.strip()


def inspect_service(service, template):
    container_id = compose("ps", "-q", service, capture=True).stdout.strip()
    if not container_id:
        raise RuntimeError(f"No running container for {service}")
    result = subprocess.run([*docker_prefix(), "inspect", "--format", template, container_id],
                            check=True, capture_output=True, text=True, encoding="utf-8", timeout=30)
    return json.loads(result.stdout)
