"""Package only source files; generated secrets, results and runtime state stay local."""
import hashlib
import json
import zipfile
from pathlib import Path

from lab_support import ROOT


def main():
    excluded_dirs = {".git", ".venv", "results", "__pycache__", ".pytest_cache", "instance", "vm", "vms", "downloads"}
    files = [path for path in ROOT.rglob("*") if path.is_file()
             and not (set(path.relative_to(ROOT).parts) & excluded_dirs)
             and not (path.name.startswith(".env") and path.name != ".env.example")
             and path.name != "SOURCE_MANIFEST.json"
             and path.suffix not in (".pyc", ".pyo", ".zip", ".clixml")]
    destination = ROOT / "results" / "minishop-source.zip"
    destination.parent.mkdir(exist_ok=True)
    manifest = {}
    with zipfile.ZipFile(destination, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(files):
            relative = Path("minishop") / path.relative_to(ROOT)
            archive.write(path, relative.as_posix())
            manifest[relative.as_posix()] = hashlib.sha256(path.read_bytes()).hexdigest()
        archive.writestr("minishop/SOURCE_MANIFEST.json", json.dumps(manifest, indent=2))
    with zipfile.ZipFile(destination) as archive:
        if any((Path(name).name.startswith(".env") and Path(name).name != ".env.example")
               or "results" in Path(name).parts for name in archive.namelist()):
            raise RuntimeError("Unexpected generated content in source archive")
    print(f"Packaged {len(files)} source files; no .env or results: {destination}")


if __name__ == "__main__":
    main()
