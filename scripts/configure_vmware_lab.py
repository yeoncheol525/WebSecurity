"""Add a dedicated Host-only NIC to powered-off lab VMs; preserve the existing NIC."""
import json
import re
import shutil
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / "results" / "vm"
VMRUN = Path("C:/Program Files (x86)/VMware/VMware Workstation/vmrun.exe")


def registered_ubuntu():
    inventory = Path.home() / "AppData/Roaming/VMware/inventory.vmls"
    try:
        text = inventory.read_text(encoding="utf-8")
    except UnicodeDecodeError:
        text = inventory.read_text(encoding="mbcs")
    paths = re.findall(r'^vmlist\d+\.config\s*=\s*"([^"]+)"', text, re.M)
    candidates = [Path(path) for path in paths if path and Path(path).exists()
                  and 'guestOS = "ubuntu-64"' in Path(path).read_text(encoding="utf-8")]
    if len(candidates) != 1:
        raise RuntimeError("Cannot uniquely identify the registered Ubuntu VM")
    return candidates[0]


def main():
    STATE.mkdir(parents=True, exist_ok=True)
    kali = list((ROOT.parent / "vms" / "kali").rglob("*.vmx"))
    if len(kali) != 1:
        raise RuntimeError("Cannot uniquely identify extracted Kali VM")
    machines = {"ubuntu": registered_ubuntu(), "kali": kali[0]}
    running = subprocess.check_output([str(VMRUN), "list"]).decode("utf-8", "replace")
    for name, path in machines.items():
        if str(path) in running or path.name in running:
            raise RuntimeError(f"{name} is still running; shut it down cleanly before editing hardware")
        text = path.read_text(encoding="utf-8")
        backup = STATE / f"{name}-before-hostonly.vmx"
        if not backup.exists():
            shutil.copy2(path, backup)
        existing = dict(re.findall(r'^(ethernet1\.[^\s=]+)\s*=\s*"([^"]*)"', text, re.M))
        if existing and existing.get("ethernet1.connectionType") not in (None, "hostonly"):
            raise RuntimeError(f"{name} already has a different second NIC; preserve it")
        additions = {
            "ethernet1.present": "TRUE", "ethernet1.connectionType": "hostonly",
            "ethernet1.addressType": "generated", "ethernet1.virtualDev": "e1000",
            "ethernet1.startConnected": "TRUE",
        }
        for key, value in additions.items():
            pattern = r'^' + re.escape(key) + r'\s*=.*$'
            replacement = f'{key} = "{value}"'
            text = re.sub(pattern, replacement, text, flags=re.M) if re.search(pattern, text, re.M) else text + "\n" + replacement
        path.write_text(text.rstrip() + "\n", encoding="utf-8", newline="\n")
        print(f"{name}: preserved ethernet0, added ethernet1 Host-only; original VMX backed up")
    (STATE / "machines.json").write_text(json.dumps({name: str(path) for name,path in machines.items()}, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
