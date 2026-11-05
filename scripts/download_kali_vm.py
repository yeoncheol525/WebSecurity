"""Resume the official Kali VMware image and verify its published SHA-256."""
import hashlib
import json
import shutil
import time
import urllib.request
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
VM_ROOT = ROOT.parent / "vms" / "kali"
IMAGE_ROOT = ROOT.parent / "downloads" / "kali-image"
IMAGE_URL = "https://gsl-syd.mm.fcix.net/kali-images/kali-2026.3/kali-linux-2026.3-vmware-amd64.7z"
IMAGE_SHA256 = "f7a008dfc78de660f8e98b8cbbf94c36688e5441bf53d6c32643f0573177a096"


def main():
    IMAGE_ROOT.mkdir(parents=True, exist_ok=True)
    VM_ROOT.parent.mkdir(parents=True, exist_ok=True)
    target = IMAGE_ROOT / "kali-linux-2026.3-vmware-amd64.7z"
    partial = target.with_suffix(".7z.partial")
    if not target.exists():
        offset = partial.stat().st_size if partial.exists() else 0
        headers = {"User-Agent": "MiniShop-Lab-Setup/1.0"}
        if offset:
            headers["Range"] = f"bytes={offset}-"
        request = urllib.request.Request(IMAGE_URL, headers=headers)
        with urllib.request.urlopen(request, timeout=60) as response:
            if offset and response.status != 206:
                raise RuntimeError("Server did not honor resume; partial data preserved")
            total = offset + int(response.headers.get("Content-Length", 0))
            print(f"Downloading official Kali VM: {offset}/{total} bytes", flush=True)
            last_report = time.monotonic()
            with partial.open("ab" if offset else "wb") as stream:
                while chunk := response.read(4 * 1024 * 1024):
                    stream.write(chunk)
                    offset += len(chunk)
                    if time.monotonic() - last_report > 20:
                        print(f"Kali image: {offset / 1024**3:.2f}/{total / 1024**3:.2f} GiB", flush=True)
                        last_report = time.monotonic()
        partial.rename(target)
    checksum = hashlib.file_digest(target.open("rb"), "sha256").hexdigest()
    if checksum != IMAGE_SHA256:
        raise RuntimeError("Image checksum mismatch; do not extract or boot")
    print("Kali official SHA-256 verified", flush=True)
    (IMAGE_ROOT / "kali-image-source.json").write_text(json.dumps({
        "url": IMAGE_URL, "official_page": "https://www.kali.org/get-kali/",
        "file": target.name, "sha256": checksum, "verified": True,
    }, indent=2), encoding="utf-8")
    import py7zr
    with py7zr.SevenZipFile(target) as archive:
        members = archive.list()
        size = sum(item.uncompressed for item in members if not item.is_directory)
        print(f"Extracting Kali VM: {size / 1024**3:.2f} GiB logical files", flush=True)
        for item in members:
            path = Path(item.filename)
            if path.is_absolute() or ".." in path.parts:
                raise RuntimeError("Unsafe archive path")
        vmx_members = [item.filename for item in members if item.filename.endswith(".vmx")]
        if vmx_members and not list(VM_ROOT.glob("*.vmx")):
            staging = IMAGE_ROOT / "extracted"
            if staging.exists() or VM_ROOT.exists():
                raise RuntimeError("Existing extraction or VM folder found; inspect it before retrying")
            archive.extractall(path=staging)
            source = staging / Path(vmx_members[0]).parts[0]
            if not source.resolve().is_relative_to(IMAGE_ROOT.resolve()):
                raise RuntimeError("Extraction source escaped the image directory")
            if not VM_ROOT.resolve().is_relative_to((ROOT.parent / "vms").resolve()):
                raise RuntimeError("VM destination escaped the workspace")
            shutil.move(str(source), str(VM_ROOT))
    print("Kali VM: workspace/vms/kali; original image: workspace/downloads/kali-image", flush=True)


if __name__ == "__main__":
    main()
