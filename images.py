"""Natural-order numbering of images at root/title/book/image depth."""
from safety import is_link, confined, destination_exists, move_no_replace, recovery_folder, write_recovery
from work import checkpoint
from dataclasses import dataclass
from pathlib import Path
import re
import uuid
import os

EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.tif', '.tiff', '.avif', '.heic', '.heif', '.jxl'}


def natural_key(path):
    parts = re.split(r'(\d+)', path.name.casefold())
    return tuple((1, int(p)) if p.isdecimal() else (0, p) for p in parts), path.name


def signature(path):
    stat = path.stat()
    return stat.st_size, stat.st_mtime_ns, stat.st_ino


@dataclass(frozen=True)
class ImageRename:
    source: Path
    destination: Path
    before: tuple


def plan_images(root):
    root = Path(root).resolve()
    if not root.is_dir():
        raise ValueError('対象フォルダが存在しません')
    result = []
    for title in sorted(root.iterdir(), key=natural_key):
        checkpoint(f'画像を確認: {title.name}')
        if not title.is_dir() or is_link(title) or title.name.casefold() == '.folder-tool-trash':
            continue
        for book in sorted(title.iterdir(), key=natural_key):
            checkpoint(f'画像を確認: {book.name}')
            if not book.is_dir() or is_link(book) or book.name.casefold() == '.folder-tool-trash':
                continue
            files = sorted((p for p in book.iterdir() if p.is_file() and not is_link(p) and p.suffix.casefold() in EXTENSIONS), key=natural_key)
            for number, source in enumerate(files, 1):
                result.append(ImageRename(source, book / f'{number:03d}{source.suffix}', signature(source)))
    validate_plan(result)
    return result


def validate_plan(items):
    sources = {item.source for item in items}
    if len(sources) != len(items):
        raise ValueError('元の画像が重複しています')
    destinations = set()
    inventories = {}
    for parent in {item.destination.parent for item in items}:
        inventory = {}
        for path in parent.iterdir():
            inventory.setdefault(path.name.casefold(), []).append(path)
        inventories[parent] = inventory
    for item in items:
        checkpoint(f'連番を確認: {item.source.name}')
        confined(item.source.parent, item.source)
        confined(item.source.parent, item.destination)
        if item.destination.parent != item.source.parent:
            raise ValueError('画像は同じフォルダ内でのみ変更できます')
        if is_link(item.source) or not item.source.is_file() or signature(item.source) != item.before:
            raise ValueError(f'プレビュー後に画像が変更されています: {item.source}')
        key = str(item.destination).casefold()
        if key in destinations:
            raise ValueError(f'連番の変更先が重複しています: {item.destination}')
        destinations.add(key)
        for existing in inventories[item.destination.parent].get(item.destination.name.casefold(), []):
            if existing.name.casefold() == item.destination.name.casefold() and existing not in sources:
                raise ValueError(f'画像以外のデータと名前が衝突します: {existing}')


def execute_images(items):
    validate_plan(items)
    changed = [item for item in items if item.source != item.destination]
    locations = {item.source: item.source for item in changed}
    try:
        # Stage every source before assigning final names, including swaps/cycles.
        for item in changed:
            temporary = item.source.parent / f'.image-numbering-{uuid.uuid4().hex}.tmp'
            if temporary.exists():
                raise ValueError(f'一時ファイルが既に存在します: {temporary}')
            move_no_replace(item.source, temporary)
            locations[item.source] = temporary
        for item in changed:
            if item.destination.exists():
                raise ValueError(f'変更先が既に存在します: {item.destination}')
            move_no_replace(locations[item.source], item.destination)
            locations[item.source] = item.destination
    except Exception as error:
        failures = []
        # Stage current files again so restoration also handles name cycles.
        for source, current in list(locations.items()):
            if source == current:
                continue
            try:
                temporary = source.parent / f'.image-restore-{uuid.uuid4().hex}.tmp'
                move_no_replace(current, temporary, rollback=True)
                locations[source] = temporary
            except OSError as restore_error:
                failures.append(f'{current}: {restore_error}')
        for source, current in locations.items():
            if source == current:
                continue
            try:
                if source.exists():
                    raise ValueError('復元先が存在します')
                move_no_replace(current, source, rollback=True)
            except (OSError, ValueError) as restore_error:
                failures.append(f'{current} → {source}: {restore_error}')
        raise RuntimeError(f'連番変更失敗: {error}\n' + ('復元失敗: ' + '; '.join(failures) if failures else '元の画像名に戻しました。')) from error
    return len(changed)


@dataclass(frozen=True)
class NonImage:
    source: Path
    before: tuple


def plan_non_images(root):
    root = Path(root).resolve()
    result = []
    def fail(error):
        raise error
    for title in sorted(root.iterdir(), key=natural_key):
        if not title.is_dir() or is_link(title) or title.name.casefold() == '.folder-tool-trash':
            continue
        for book in sorted(title.iterdir(), key=natural_key):
            if not book.is_dir() or is_link(book) or book.name.casefold() == '.folder-tool-trash':
                continue
            for directory, dirs, files in os.walk(book, followlinks=False, onerror=fail):
                checkpoint(f'画像以外を確認: {Path(directory).name}')
                dirs[:] = sorted(d for d in dirs if d.casefold() != '.folder-tool-trash' and not is_link(Path(directory) / d))
                for name in sorted(files):
                    file = Path(directory) / name
                    if file.is_file() and not is_link(file) and file.suffix.casefold() not in EXTENSIONS:
                        result.append(NonImage(file, signature(file)))
    return result


def execute_image_cleanup(root, images, non_images):
    root = Path(root).resolve()
    if plan_images(root) != images or plan_non_images(root) != non_images:
        raise ValueError('ファイル一覧が変わりました。プレビューを作り直してください。')
    backup = None
    moved = []
    try:
        if non_images:
            backup = recovery_folder(root, 'images')
            # Persist recovery paths before moving any data.
            records = [(item.source, backup / item.source.relative_to(root)) for item in non_images]
            write_recovery(backup, records)
        for item in non_images:
            confined(root, item.source)
            if is_link(item.source) or signature(item.source) != item.before:
                raise ValueError(f'削除対象が変更されています: {item.source}')
            target = backup / item.source.relative_to(root)
            target.parent.mkdir(parents=True, exist_ok=True)
            if target.exists():
                raise ValueError(f'退避先が既に存在します: {target}')
            move_no_replace(item.source, target)
            moved.append((item.source, target))
        count = execute_images(images)
    except Exception as error:
        failures = []
        for source, target in reversed(moved):
            try:
                if source.exists():
                    raise ValueError('復元先が存在します')
                move_no_replace(target, source, rollback=True)
            except (OSError, ValueError) as restore_error:
                failures.append(f'{target} → {source}: {restore_error}')
        raise RuntimeError(f'{error}\n' + ('画像以外の復元失敗: ' + '; '.join(failures) if failures else '退避した画像以外のファイルを元に戻しました。')) from error
    return count, backup if non_images else None
