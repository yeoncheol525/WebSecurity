"""An explicit, opt-in deletion of this lab's verified PostgreSQL volume only."""
import argparse
import json
import subprocess
import sys

from lab_support import ROOT, compose, docker_prefix, inspect_service, read_env


def main():
    parser = argparse.ArgumentParser(description="Permanently delete and recreate MiniShop's synthetic data")
    parser.add_argument("--confirm-delete-minishop-data", action="store_true")
    args = parser.parse_args()
    if not args.confirm_delete_minishop_data:
        parser.error("No data deleted. Specify --confirm-delete-minishop-data only after saving needed evidence.")
    mounts = inspect_service("postgres", "{{json .Mounts}}")
    candidates = [mount["Name"] for mount in mounts if mount["Type"] == "volume"
                  and mount["Destination"] == "/var/lib/postgresql/data"]
    if len(candidates) != 1:
        raise RuntimeError("Cannot identify exactly one lab data volume; refusing deletion")
    volume = candidates[0]
    info = json.loads(subprocess.run([*docker_prefix(), "volume", "inspect", volume], check=True,
                                     capture_output=True, text=True, timeout=30).stdout)[0]
    labels = info.get("Labels") or {}
    if (labels.get("com.docker.compose.project") != read_env()["COMPOSE_PROJECT_NAME"]
            or labels.get("com.docker.compose.volume") != "postgres-data"):
        raise RuntimeError("Volume labels do not match this lab; refusing deletion")
    print(f"Deleting the explicitly confirmed synthetic lab volume: {volume}")
    compose("down")
    subprocess.run([*docker_prefix(), "volume", "rm", volume], check=True, timeout=60)
    # Reapply the selected condition, including the wide role for E1/E2.
    subprocess.run([sys.executable, str(ROOT / "scripts/setup.py")], check=True)
    print("Recreated the fixed seed. Existing .env credentials were preserved.")


if __name__ == "__main__":
    main()
