"""Shared protection for links, recovery storage, and non-overwriting moves."""
import json
import os
from pathlib import Path
import stat
import uuid
import threading
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
        token.journal.move(source, destination, lambda: rename_with_retry(source, destination, rollback))
    else:
        rename_with_retry(source, destination, rollback)


def rename_with_retry(source, destination, rollback=False):
    for attempt in range(6):
        checkpoint(f'移動: {source.name}', rollback)
        if destination_exists(destination):
            raise ValueError(f'移動先が既に存在します: {destination}')
        try:
            return source.rename(destination)
        except OSError as error:
            code = getattr(error, 'winerror', None)
            if code in (32, 33) and attempt < 5:
                checkpoint(f'使用中のため再試行: {source.name}', rollback)
                token = current.get()
                delay = min(0.1 * 2**attempt, 0.4)
                if token is not None and not rollback:
                    token.cancelled.wait(delay)
                else:
                    threading.Event().wait(delay)
                continue
            if code in (32, 33):
                help_text = '別のアプリで使用中です。画像ビューアーやエクスプローラーのプレビューを閉じて再実行してください。'
            elif isinstance(error, PermissionError) or code == 5:
                help_text = 'アクセスが拒否されました。使用中のアプリ、対象フォルダの書き込み権限、読み取り専用属性を確認してください。'
            elif code == 206:
                help_text = 'パスまたは名前が長すぎます。対象フォルダを短いパスへ移すか、変更後の名前を短くしてください。'
            else:
                help_text = '移動できませんでした。'
            message = f'{help_text}\n対象: {source}\n移動先: {destination}\n元のエラー: {error}'
            raise OSError(error.errno, message, str(source), code, str(destination)) from error


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
