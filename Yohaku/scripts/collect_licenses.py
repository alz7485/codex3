"""Copy license texts from installed Python distribution metadata."""
from importlib import metadata
from pathlib import Path
import shutil
import sys


def collect(folder):
    destination = Path(folder) / "third-party-licenses"
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("PySide6", "PySide6_Essentials", "PySide6_Addons", "shiboken6", "pywin32", "pyinstaller", "pyinstaller-hooks-contrib", "packaging", "altgraph"):
        try:
            dist = metadata.distribution(name)
        except metadata.PackageNotFoundError:
            continue
        for entry in dist.files or []:
            if "license" in str(entry).lower() or "copying" in entry.name.lower():
                source = Path(dist.locate_file(entry))
                if source.is_file() and source.suffix.lower() in ("", ".txt", ".md", ".rst"):
                    target = destination / name / entry.name
                    target.parent.mkdir(parents=True, exist_ok=True)
                    shutil.copy2(source, target)
    for filename in ("LICENSE.txt", "LICENSE"):
        source = Path(sys.base_prefix) / filename
        if source.is_file():
            shutil.copy2(source, destination / "PYTHON-LICENSE.txt")
            break


if __name__ == "__main__":
    collect(sys.argv[1])
