"""Create the complete YOHAKU source ZIP and checksum, excluding local user data."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from companion.metadata import VERSION

EXCLUDED_DIRS = {".git", ".venv", "__pycache__", "build", "dist", "release", ".pytest_cache", ".aws", ".ssh", ".codex", ".agents"}
PRIVATE_NAMES = {"settings.json", "history.json", "instance.lock", ".env", "smoke-report.json"}


def source_files(project):
    result = []
    for path in sorted(project.rglob("*")):
        relative = path.relative_to(project)
        if any(part in EXCLUDED_DIRS for part in relative.parts):
            continue
        if not path.is_file() or path.is_symlink() or path.name in PRIVATE_NAMES or path.name.startswith(".env."):
            continue
        if path.name == "MANIFEST_SHA256.json" or path.suffix in {".pyc", ".sqlite3", ".sqlite", ".db", ".log", ".zip", ".pem", ".key"}:
            continue
        if path.name.endswith((".sqlite3-journal", ".sqlite3-wal", ".sqlite3-shm")):
            continue
        result.append(path)
    return result


def create_archive(project, output):
    project, output = Path(project), Path(output)
    files = source_files(project)
    manifest = {p.relative_to(project).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    manifest_text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
    (project / "MANIFEST_SHA256.json").write_text(manifest_text, encoding="utf-8")
    output.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, Path("Yohaku") / path.relative_to(project))
        archive.writestr("Yohaku/MANIFEST_SHA256.json", manifest_text)
    with zipfile.ZipFile(output) as archive:
        if archive.testzip() is not None:
            raise RuntimeError("ZIP CRC verification failed.")
        for name, digest in manifest.items():
            if hashlib.sha256(archive.read("Yohaku/" + name)).hexdigest() != digest:
                raise RuntimeError(f"ZIP digest verification failed: {name}")
    digest = hashlib.sha256(output.read_bytes()).hexdigest()
    output.with_suffix(".zip.sha256").write_text(digest + "  " + output.name + "\n", encoding="ascii")
    return digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=PROJECT / "release" / f"Yohaku-v{VERSION}-source.zip")
    args = parser.parse_args()
    digest = create_archive(PROJECT, args.output)
    print(f"Ready: {args.output}\nSHA-256: {digest}")


if __name__ == "__main__":
    main()
