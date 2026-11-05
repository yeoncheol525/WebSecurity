import argparse
import ipaddress
import subprocess
import sys

from create_env import main as create_env
from lab_support import ROOT, compose, docker_prefix, read_env
from network_config import validate_bind


def main():
    parser = argparse.ArgumentParser(description="Build and start the safe MiniShop lab")
    parser.add_argument("--allow-host-only-bind", action="store_true",
                        help="Confirm the configured private address belongs to the isolated lab adapter")
    parser.add_argument("--bind", help="Bind to an assigned private address; existing credentials are preserved")
    parser.add_argument("--local", action="store_true", help="Bind to loopback only")
    parser.add_argument("--verify", action="store_true", help="Build the verifier and run real HTTP/DB checks")
    args = parser.parse_args()
    if args.local and args.bind:
        parser.error("Choose --local or --bind")
    create_env("127.0.0.1" if args.local else args.bind)
    values = read_env()
    address = ipaddress.ip_address(values.get("BIND_ADDRESS", "127.0.0.1"))
    if address.is_unspecified or address.is_multicast or not address.is_private:
        parser.error("Bind to loopback or a specific isolated private adapter, never all interfaces")
    validate_bind(str(address))
    subprocess.run([*docker_prefix(), "info", "--format", "{{.ServerVersion}}"], check=True, timeout=30)
    compose("config", "--quiet")
    compose("up", "-d", "--build", "--wait", "--wait-timeout", "180", timeout=600)
    # Compose does not detect changes inside the bind-mounted nginx.conf.
    # Recreate only the proxy so updates are active before verification.
    compose("up", "-d", "--no-deps", "--force-recreate", "--wait", "--wait-timeout", "60", "nginx")
    print(f"Safe lab URL: http://{address}:{values.get('HTTP_PORT', '18080')}", flush=True)
    if address.is_loopback:
        print("No dedicated private interface was selected. Add a Host-only interface, then rerun with --bind IP for Kali access.")
    if args.verify:
        compose("--profile", "verification", "build", "tester", timeout=600)
        subprocess.run([sys.executable, str(ROOT / "scripts/verify_environment.py"), "--no-build"], check=True)
    print("Ready. Web-test credentials: python3 scripts/demo_credentials.py")


if __name__ == "__main__":
    try:
        main()
    except (subprocess.SubprocessError, OSError, ValueError, RuntimeError) as error:
        if isinstance(error, (ValueError, RuntimeError)):
            print(str(error), file=sys.stderr)
        print(f"Setup failed ({type(error).__name__}); no existing volume was deleted.", file=sys.stderr)
        raise SystemExit(1)
