"""Package source as one ZIP up to 24 MB, otherwise two; exclude user data."""
from __future__ import annotations

import argparse
from copy import copy
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import zipfile

PROJECT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT))
from companion.metadata import VERSION

EXCLUDED_DIRS = {".git", ".venv", "__pycache__", "build", "dist", "release", ".pytest_cache", ".aws", ".ssh", ".codex", ".agents"}
PRIVATE_NAMES = {"settings.json", "history.json", "instance.lock", ".env", "smoke-report.json", "dialogue.json", "dialogue.json.bak", "dialogue.json.tmp", "Yohaku-conversation.json", "usage.json", "usage.tmp", "settings.tmp", "history.tmp", "reminders.json", "reminders.json.bak", "reminders.json.tmp"}
PRIVATE_NAMES.update({name+suffix for name in ("context_options", "topic_preferences", "one_shot_notifications") for suffix in (".json", ".json.bak", ".json.tmp")})
PRIVATE_NAMES.update({name+suffix for name in ('file_drop_settings','file_destinations','shelf') for suffix in ('.json','.json.bak','.json.tmp')})
PRIVATE_NAMES.add('.yohaku.init.lock')


def source_files(project):
    result = []
    for path in sorted(project.rglob("*")):
        relative = path.relative_to(project)
        if relative.parts[0].casefold()=='data':continue
        if any(part.casefold() in EXCLUDED_DIRS or part.casefold().startswith('.yohaku-data-') for part in relative.parts):
            continue
        if not path.is_file() or path.is_symlink() or path.name.casefold() in {name.casefold() for name in PRIVATE_NAMES} or path.name.casefold().startswith(".env."):
            continue
        # Documentation previews are published on GitHub. Runtime artwork in
        # companion/assets remains included; source ZIPs need no large demo GIFs.
        if relative.parts[0] == 'docs' and path.suffix.lower() in {'.png', '.gif', '.jpg', '.jpeg', '.webp', '.mp4'}:
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


def create_split_archives(project, output_directory):
    """Balance compressed sizes without cutting any file or ZIP byte stream."""
    output_directory = Path(output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    common = {'Yohaku/MANIFEST_SHA256.json', 'Yohaku/README.md',
              'Yohaku/ONEDIR_COMMAND.txt', 'Yohaku/SPLIT_README.txt'}
    with tempfile.TemporaryDirectory(prefix='yohaku-source-') as temporary:
        full = Path(temporary) / 'source.zip'
        create_archive(project, full)
        with zipfile.ZipFile(full) as source:
            groups, sizes = [[], []], [0, 0]
            for entry in sorted(source.infolist(), key=lambda entry: (-entry.compress_size, entry.filename)):
                if entry.filename in common:
                    for group in groups:
                        group.append(entry)
                else:
                    index = 0 if sizes[0] <= sizes[1] else 1
                    groups[index].append(entry)
                    sizes[index] += entry.compress_size
            paths = []
            for index, entries in enumerate(groups, 1):
                path = output_directory / f'Yohaku-v{VERSION}-source-part{index}-of-2.zip'
                with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as destination:
                    for entry in sorted(entries, key=lambda entry: entry.filename):
                        destination.writestr(copy(entry), source.read(entry.filename))
                with zipfile.ZipFile(path) as check:
                    assert check.testzip() is None
                    manifest = json.loads(check.read('Yohaku/MANIFEST_SHA256.json'))
                    for name in check.namelist():
                        relative = name.removeprefix('Yohaku/')
                        if relative in manifest:
                            assert hashlib.sha256(check.read(name)).hexdigest() == manifest[relative]
                digest = hashlib.sha256(path.read_bytes()).hexdigest()
                path.with_suffix('.zip.sha256').write_text(digest + '  ' + path.name + '\n', encoding='ascii')
                paths.append(path)
            # Each required source file must be present in at least one part.
            with zipfile.ZipFile(paths[0]) as a, zipfile.ZipFile(paths[1]) as b:
                assert set(a.namelist()) | set(b.namelist()) == set(source.namelist())
            return paths


def create_default_archives(project, output_directory, limit=24_000_000):
    output_directory = Path(output_directory)
    path = output_directory / f'Yohaku-v{VERSION}-source.zip'
    create_archive(project, path)
    if path.stat().st_size <= limit:
        return [path]
    path.unlink(); path.with_suffix('.zip.sha256').unlink()
    return create_split_archives(project, output_directory)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=PROJECT / 'release')
    parser.add_argument('--output', type=Path, help='Explicit single ZIP output; otherwise choose by compressed size.')
    args = parser.parse_args()
    if args.output:
        digest = create_archive(PROJECT, args.output)
        print(f'Ready: {args.output}\nSHA-256: {digest}')
    else:
        for path in create_default_archives(PROJECT, args.output_dir):
            print(f'Ready: {path} ({path.stat().st_size:,} bytes)')


if __name__ == "__main__":
    main()
