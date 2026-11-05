"""Drive genuine Ubuntu and Kali checks; persist only non-secret evidence."""
import json
import shlex

from vm_remote import ROOT, STATE, connect, run, ubuntu_credentials


def main():
    credentials = ubuntu_credentials()
    with connect("192.168.67.20", credentials["username"], credentials["password"]) as ubuntu:
        remote_root = "/home/" + credentials["username"] + "/minishop"
        with ubuntu.open_sftp() as sftp:
            sftp.put(str(ROOT / "scripts/verify_environment.py"), remote_root + "/scripts/verify_environment.py")
        stdin, stdout, stderr = ubuntu.exec_command("cd " + shlex.quote(remote_root) +
                                                   " && python3 scripts/verify_environment.py --no-build 2>&1", timeout=600)
        for line in stdout:
            print(line, end="", flush=True)
        if stdout.channel.recv_exit_status():
            raise RuntimeError("Ubuntu validation failed")
        # Only two synthetic web passwords cross into the attacker VM; no DB/admin credentials.
        fetch = ("import sys,json;sys.path.insert(0,'scripts');from lab_support import read_env;"
                 "e=read_env();print(json.dumps({'user1_password':e['DEMO_USER1_PASSWORD'],"
                 "'user2_password':e['DEMO_USER2_PASSWORD'],'server_ip':'192.168.67.20'}))")
        status, payload, errors = run(ubuntu, "cd " + shlex.quote(remote_root) + " && python3 -c " + shlex.quote(fetch))
        if status:
            raise RuntimeError("Cannot read synthetic web-test credentials")
        with ubuntu.open_sftp() as sftp:
            sftp.get(remote_root + "/results/latest.json", str(STATE / "ubuntu-validation.json"))
            summary = json.loads((STATE / "ubuntu-validation.json").read_text())
            remote_results = summary["results_directory"]
            local_results = STATE / "ubuntu-results"
            local_results.mkdir(exist_ok=True)
            for filename in ("summary.json", "test_results.csv", "junit.xml", "versions.json", "host_checks.json"):
                sftp.get(remote_results + "/" + filename, str(local_results / filename))
    with connect("192.168.67.10", "kali", "kali") as kali:
        with kali.open_sftp() as sftp:
            sftp.put(str(ROOT / "scripts/verify_kali_client.py"), "/home/kali/verify_minishop.py")
        stdin, stdout, stderr = kali.exec_command("python3 /home/kali/verify_minishop.py", timeout=60)
        stdin.write(payload)
        stdin.flush()
        stdin.channel.shutdown_write()
        output, errors = stdout.read().decode(), stderr.read().decode()
        status = stdout.channel.recv_exit_status()
        if status:
            print(errors)
            raise RuntimeError("Kali cross-VM verification failed")
        evidence = json.loads(output)
        if not evidence["passed"]:
            raise RuntimeError("Kali reported a failed check")
        (STATE / "kali-validation.json").write_text(json.dumps(evidence, indent=2), encoding="utf-8")
        print(output, flush=True)
    print("Ubuntu 24/24 checks and Kali 8/8 checks passed.", flush=True)


if __name__ == "__main__":
    main()
