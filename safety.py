"""Shared protection for links, recovery storage, and non-overwriting moves."""
import json
import os
from pathlib import Path
import stat
import uuid
from work import checkpoint, current

TRASH = '.folder-tool-trash'


def is_link(path):
    path = Path(path)
    try:
        info = path.lstat()
    except FileNotFoundError:
        return False
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, 'st_file_attributes', 0) & 0x400)


def confined(root, path):
    root, path = Path(root).resolve(), Path(path).absolute()
    if root not in path.parents:
        raise ValueError(f'対象範囲外です: {path}')
    for parent in (path, *path.parents):
        if parent == root:
            break
        if is_link(parent):
            raise ValueError(f'リンク・ジャンクションは操作できません: {parent}')
    if path.resolve() != path:
        raise ValueError(f'対象範囲を確認できません: {path}')
    return path


def destination_exists(path):
    path = Path(path)
    if os.path.lexists(path):
        return True
    return path.parent.is_dir() and any(p.name.casefold() == path.name.casefold() for p in path.parent.iterdir())


def move_no_replace(source, destination, rollback=False):
    source, destination = Path(source), Path(destination)
    checkpoint(f'移動: {source.name}', rollback)
    for path in (source, destination):
        for parent in path.parents:
            if is_link(parent):
                raise ValueError(f'親フォルダがリンクです: {parent}')
    if destination_exists(destination):
        raise ValueError(f'移動先が既に存在します: {destination}')
    token = current.get()
    if token is not None and token.journal is not None:
        token.journal.move(source, destination, lambda: source.rename(destination))
    else:
        source.rename(destination)


def record_created(path):
    token = current.get()
    if token is not None and token.journal is not None:
        token.journal.created(path)


def recovery_folder(root, kind):
    root = Path(root).resolve()
    trash = root / TRASH
    confined(root, trash)
    if trash.exists() and not trash.is_dir():
        raise ValueError(f'復元用フォルダを作成できません: {trash}')
    if not trash.exists() and destination_exists(trash):
        raise ValueError(f'復元用フォルダと同名のデータがあります: {trash}')
    trash.mkdir(exist_ok=True)
    backup = trash / f'{kind}-{uuid.uuid4().hex}'
    backup.mkdir()
    return backup


def write_recovery(backup, records):
    # Failure must occur before any source is changed.
    with (Path(backup) / 'restore.json').open('x', encoding='utf-8') as file:
        json.dump([{'original': str(source), 'backup': str(target)} for source, target in records], file, ensure_ascii=False, indent=2)
        file.flush()
        os.fsync(file.fileno())
