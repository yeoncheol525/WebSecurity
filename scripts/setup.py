import argparse
import ipaddress
import subprocess
import sys

from create_env import main as create_env
from lab_support import EXPERIMENTS, admin_sql, compose, docker_prefix, read_env, select_experiment, selected_experiment
from network_config import validate_bind


def main():
    parser = argparse.ArgumentParser(description="Install and start MiniShop services for the selected condition")
    parser.add_argument("--allow-host-only-bind", action="store_true",
                        help="Confirm the configured private address belongs to the isolated lab adapter")
    parser.add_argument("--bind", help="Bind to an assigned private address; existing credentials are preserved")
    parser.add_argument("--local", action="store_true", help="Bind to loopback only")
    parser.add_argument("--experiment", choices=EXPERIMENTS,
                        help="Select one condition; defaults to the saved selection, or E4 on first use")
    args = parser.parse_args()
    if args.local and args.bind:
        parser.error("Choose --local or --bind")
    create_env("127.0.0.1" if args.local else args.bind)
    if args.experiment:
        select_experiment(args.experiment)
    values = read_env()
    experiment = selected_experiment(values)
    address = ipaddress.ip_address(values.get("BIND_ADDRESS", "127.0.0.1"))
    if address.is_unspecified or address.is_multicast or not address.is_private:
        parser.error("Bind to loopback or a specific isolated private adapter, never all interfaces")
    validate_bind(str(address))
    subprocess.run([*docker_prefix(), "info", "--format", "{{.ServerVersion}}"], check=True, timeout=30)
    compose("config", "--quiet")
    # These are the selected environment's connection settings, not permission tests.
    # Wide credentials already exist in both new and existing PostgreSQL volumes.
    compose("up", "-d", "--wait", "--wait-timeout", "180", "postgres", timeout=300)
    if experiment in ("E1", "E2"):
        admin_sql("ALTER ROLE catalog_reader_wide LOGIN VALID UNTIL 'infinity';")
    else:
        admin_sql("ALTER ROLE catalog_reader_wide NOLOGIN VALID UNTIL '1970-01-01';\n"
                  "SELECT pg_terminate_backend(pid) FROM pg_stat_activity "
                  "WHERE usename='catalog_reader_wide' AND pid<>pg_backend_pid();")
    compose("up", "-d", "--build", "--wait", "--wait-timeout", "180", timeout=600)
    # Compose does not detect changes inside the bind-mounted nginx.conf.
    # Recreate only the proxy so configuration updates take effect.
    compose("up", "-d", "--no-deps", "--force-recreate", "--wait", "--wait-timeout", "60", "nginx")
    print(f"{experiment} lab URL: http://{address}:{values.get('HTTP_PORT', '18080')}", flush=True)
    if address.is_loopback:
        print("No dedicated private interface was selected. Add a Host-only interface, then rerun with --bind IP for Kali access.")
    print("Services ready.")
    print(f"Experiment documentation: experiments/{experiment}/README.md")
    print("Web credentials: python3 scripts/demo_credentials.py")


if __name__ == "__main__":
    try:
        main()
    except (subprocess.SubprocessError, OSError, ValueError, RuntimeError) as error:
        if isinstance(error, (ValueError, RuntimeError)):
            print(str(error), file=sys.stderr)
        print(f"Setup failed ({type(error).__name__}); no existing volume was deleted.", file=sys.stderr)
        raise SystemExit(1)
