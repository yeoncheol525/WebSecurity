"""Deploy the safe service to the existing Ubuntu VM using the user's local credentials."""
import json
import shlex
import sys
from pathlib import Path

from vm_remote import ROOT, STATE, connect, run, ubuntu_credentials


def stream(client, command, password=None):
    stdin, stdout, stderr = client.exec_command(command + " 2>&1", timeout=900)
    if password is not None:
        stdin.write(password + "\n")
        stdin.flush()
    stdin.channel.shutdown_write()
    for line in stdout:
        if password:
            line = line.replace(password, "[REDACTED]")
        print(line, end="", flush=True)
    status = stdout.channel.recv_exit_status()
    if status:
        raise RuntimeError(f"Remote step failed with exit status {status}")


def main():
    credentials = ubuntu_credentials()
    with connect("192.168.186.128", credentials["username"], credentials["password"]) as client:
        status, home, errors = run(client, "printf '%s' \"$HOME\"")
        if status or not home.startswith("/home/"):
            raise RuntimeError("Cannot determine the Ubuntu user's home directory")
        remote_root = home + "/minishop"
        status, existing, errors = run(client, "test -e " + shlex.quote(remote_root))
        if status == 0:
            raise RuntimeError("Ubuntu ~/minishop already exists; inspect before overwriting")
        remote_zip = home + "/minishop-source.zip"
        remote_network = home + "/minishop-network-bootstrap.sh"
        with client.open_sftp() as sftp:
            sftp.put(str(ROOT / "results/minishop-source.zip"), remote_zip)
            sftp.put(str(ROOT / "scripts/bootstrap_ubuntu_lab_network.sh"), remote_network)
            sftp.chmod(remote_network, 0o700)
        stream(client, "sudo -S -p '' sh " + shlex.quote(remote_network), credentials["password"])
        stream(client, "python3 -m zipfile -e " + shlex.quote(remote_zip) + " " + shlex.quote(home))
        stream(client, "cd " + shlex.quote(remote_root) + " && python3 scripts/create_env.py")
        # Credentials are generated inside Ubuntu, never copied from the Windows .env.
        edit = ("from pathlib import Path;p=Path(" + repr(remote_root + "/.env") + ");"
                "s=p.read_text();s=s.replace('BIND_ADDRESS=127.0.0.1','BIND_ADDRESS=192.168.67.20');p.write_text(s)")
        stream(client, "python3 -c " + shlex.quote(edit))
        stream(client, "cd " + shlex.quote(remote_root) +
               " && python3 scripts/setup.py --allow-host-only-bind")
        # Deployment ends after service startup. Verification is a separate manual action.
        STATE.mkdir(parents=True, exist_ok=True)
        (STATE / "ubuntu-deployment.json").write_text(json.dumps({
            "management_ip": "192.168.186.128", "host_only_ip": "192.168.67.20",
            "username": credentials["username"], "project_directory": remote_root,
            "service_url": "http://192.168.67.20:18080", "source": "Downloads/minishop/project",
        }, indent=2), encoding="utf-8")
        print("Ubuntu services started.", flush=True)


if __name__ == "__main__":
    main()
