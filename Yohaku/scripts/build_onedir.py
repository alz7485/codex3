"""Build a self-contained Windows onedir folder and ZIP, without user data."""
from __future__ import annotations

import argparse
import hashlib
from importlib import metadata
from pathlib import Path
import shutil
import subprocess
import struct
import sys
import venv
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from companion.metadata import VERSION


def required_files(project=PROJECT):
    paths = [project / "Yohaku.spec", project / "packaging/windows_version_info.txt",
             project / "companion/assets/app/yohaku.ico", project / "companion/assets/app/yohaku.png",
             project / "companion/assets/characters/motion_layout.json",
             project / "companion/assets/characters/front_reactions.png",
             project / "companion/assets/dialogue/default_dialogue.json"]
    paths += [project / f"companion/assets/characters/{key}{suffix}.png"
              for key in "abef" for suffix in ("", "_motion")]
    return paths


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="Check build inputs only; works on Linux too.")
    parser.add_argument("--setup-only", action="store_true", help="Prepare the local .venv without building.")
    parser.add_argument("--skip-install", action="store_true", help="Use the current Python and installed build dependencies (CI).")
    args = parser.parse_args()
    missing = [str(path.relative_to(PROJECT)) for path in required_files() if not path.is_file()]
    if missing:
        parser.error("Missing build inputs: " + ", ".join(missing))
    if args.check:
        print(f"Yohaku {VERSION}: icon, version resource and all 4 characters / animations are present.")
        return
    if sys.platform != "win32":
        parser.error("Windows is required for building a Windows executable.")
    if sys.version_info[:2] not in ((3, 11), (3, 12)):
        parser.error("Use Python 3.11 or 3.12.")
    if struct.calcsize("P") != 8:
        parser.error("Use 64-bit Python for the Windows x64 distribution.")
    python = Path(sys.executable)
    if not args.skip_install:
        python = PROJECT / ".venv/Scripts/python.exe"
        if not python.exists():
            venv.EnvBuilder(with_pip=True).create(PROJECT / ".venv")
        subprocess.run([str(python), "-m", "pip", "install", "-r", str(PROJECT / "requirements-build.txt")], check=True)
    if args.setup_only:
        print("Build environment is ready.")
        return
    subprocess.run([str(python), "-m", "PyInstaller", "--noconfirm", "--clean",
                    "--distpath", str(PROJECT / "dist"), "--workpath", str(PROJECT / "build/pyinstaller"),
                    str(PROJECT / "Yohaku.spec")], cwd=PROJECT, check=True)
    folder = PROJECT / "dist/Yohaku"
    if not (folder / "Yohaku.exe").is_file():
        raise RuntimeError("Yohaku.exe was not produced.")
    for path in required_files():
        if "assets" in path.parts:
            target = folder / "_internal" / path.relative_to(PROJECT)
            if not target.is_file():
                raise RuntimeError(f"Bundled asset is missing: {target}")
    for name in ("README.md", "THIRD_PARTY_NOTICES.md"):
        shutil.copy2(PROJECT / name, folder / name)
    (folder / "docs").mkdir(exist_ok=True)
    shutil.copy2(PROJECT / "docs/WINDOWS_CHECKLIST.md", folder / "docs/WINDOWS_CHECKLIST.md")
    # Preserve the licenses installed by the dependency wheels.
    if args.skip_install:
        collect_licenses(folder)
    else:
        subprocess.run([str(python), str(PROJECT / "scripts/collect_licenses.py"), str(folder)], check=True)
    output = PROJECT / "release" / f"Yohaku-v{VERSION}-windows-x64-onedir.zip"
    output.parent.mkdir(exist_ok=True)
    with zipfile.ZipFile(output, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(folder.rglob("*")):
            if path.is_file():
                archive.write(path, Path("Yohaku") / path.relative_to(folder))
    output.with_suffix(".zip.sha256").write_text(hashlib.sha256(output.read_bytes()).hexdigest() + "  " + output.name + "\n", encoding="ascii")
    print(f"Ready: {output}")


def collect_licenses(folder):
    from collect_licenses import collect
    collect(folder)


if __name__ == "__main__":
    main()
