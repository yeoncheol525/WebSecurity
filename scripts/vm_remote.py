"""SSH helpers for this Windows-hosted VMware lab; passwords never enter logs or CLI arguments."""
import json
import os
import subprocess
from pathlib import Path

import paramiko


ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "results" / "vm"


def ubuntu_credentials():
    path = str(STATE / "ubuntu-credential.clixml").replace("'", "''")
    command = ("$c=Import-Clixml -LiteralPath '" + path + "'; "
               "$p=$c.GetNetworkCredential(); @{username=$p.UserName;password=$p.Password}|ConvertTo-Json -Compress")
    completed = subprocess.run(["powershell.exe", "-NoProfile", "-Command", command],
                               check=True, capture_output=True, text=True, encoding="utf-8")
    return json.loads(completed.stdout)


def connect(host, username, password):
    STATE.mkdir(parents=True, exist_ok=True)
    client = paramiko.SSHClient()
    known_hosts = STATE / "known_hosts"
    if known_hosts.exists():
        client.load_host_keys(str(known_hosts))
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(host, username=username, password=password, timeout=12,
                   auth_timeout=12, banner_timeout=12, allow_agent=False, look_for_keys=False)
    client.save_host_keys(str(known_hosts))
    return client


def run(client, command, *, password=None, timeout=60):
    stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
    if password is not None:
        stdin.write(password + "\n")
        stdin.flush()
    stdin.channel.shutdown_write()
    output, errors = stdout.read().decode("utf-8", "replace"), stderr.read().decode("utf-8", "replace")
    status = stdout.channel.recv_exit_status()
    if password:
        output, errors = output.replace(password, "[REDACTED]"), errors.replace(password, "[REDACTED]")
    return status, output, errors


if __name__ == "__main__":
    credentials = ubuntu_credentials()
    with connect("192.168.186.128", credentials["username"], credentials["password"]) as client:
        status, output, errors = run(client, "whoami; hostname; cat /etc/os-release; "
                                    "ip -br address; ip route; df -h /; "
                                    "command -v docker || true; command -v git || true; "
                                    "python3 --version; sudo -n true", timeout=30)
        print(output)
        print(errors)
        print("Inspection exit status:", status)
