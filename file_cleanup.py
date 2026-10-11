"""Recursive OR filename search with individually selectable file deletion."""
from safety import is_link, confined, destination_exists, move_no_replace, recovery_folder, write_recovery
from work import checkpoint
from dataclasses import dataclass
from pathlib import Path
import os


def matches(name, query):
    name = name.casefold()
    for term in query.split(' '):
        term = term.strip().casefold()
        if not term:
            continue
        if term.startswith('*.'):
            term = term[1:]
        if term.startswith('.'):
            if name.endswith(term):
                return True
        elif term in name:
            return True
    return False


def signature(file):
    stat = file.stat()
    return stat.st_size, stat.st_mtime_ns, stat.st_ino


@dataclass(frozen=True)
class Candidate:
    source: Path
    before: tuple


def search_files(root, query):
    if not query.strip():
        raise ValueError('検索文字列または拡張子を入力してください。')
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('対象フォルダが見つかりません。')
    result = []
    def fail(error):
        raise error
    for directory, dirs, files in os.walk(root, followlinks=False, onerror=fail):
        checkpoint(f'検索: {Path(directory).name}')
        dirs[:] = sorted(d for d in dirs if d.casefold() != '.folder-tool-trash' and not is_link(Path(directory) / d))
        for name in sorted(files):
            checkpoint(f'検索: {name}')
            file = Path(directory) / name
            if not is_link(file) and file.is_file() and matches(name, query):
                result.append(Candidate(file, signature(file)))
    return result


def delete_files(root, candidates):
    root = Path(root).resolve()
    if not candidates:
        return None
    seen = set()
    for item in candidates:
        source = item.source
        if source in seen or root not in source.resolve().parents or source.resolve() != source or '.folder-tool-trash' in source.relative_to(root).parts:
            raise ValueError(f'対象範囲外または重複したファイルです: {source}')
        seen.add(source)
        if is_link(source) or not source.is_file() or signature(source) != item.before:
            raise ValueError(f'確認後にファイルが変更されています: {source}')
    backup = None
    moved = []
    try:
        backup = recovery_folder(root, 'files')
        # Keep payload separate from metadata, including a source named restore.json.
        records = [(item.source, backup / 'data' / item.source.relative_to(root)) for item in candidates]
        write_recovery(backup, records)
        for item in candidates:
            source = item.source
            if source.resolve() != source or is_link(source) or signature(source) != item.before:
                raise ValueError(f'確認後にファイルが変更されています: {source}')
            confined(root, source)
            target = backup / 'data' / source.relative_to(root)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                raise ValueError(f'退避先が既に存在します: {target}')
            move_no_replace(source, target)
            moved.append((source, target))
    except Exception as error:
        failures = []
        for source, target in reversed(moved):
            try:
                if source.exists():
                    raise ValueError('復元先が存在します')
                move_no_replace(target, source, rollback=True)
            except (OSError, ValueError) as restore_error:
                failures.append(f'{target} → {source}: {restore_error}')
        raise RuntimeError(f'削除失敗: {error}\n' + ('復元失敗: ' + '; '.join(failures) if failures else '退避したファイルを元に戻しました。')) from error
    return backup
