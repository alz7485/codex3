"""Folder planning and filesystem operations (standard library only)."""
from safety import is_link, confined, destination_exists, move_no_replace, recovery_folder, write_recovery
from safety import record_created
from work import checkpoint
from dataclasses import dataclass
from pathlib import Path
import re
import os
import uuid

PARTS = re.compile(r'\[[^\[\]]*\]|［[^［］]*］|\([^()]*\)|（[^（）]*）')


def normalize_punctuation(name):
    """Mixed !/? sequences take precedence over repeated exclamations."""
    def replace(match):
        run = match.group()
        has_bang = any(char in '!！' for char in run)
        has_question = any(char in '?？' for char in run)
        if has_bang and has_question:
            return run.translate(str.maketrans({'!': '！', '?': '？'}))
        if has_bang:
            return '!' * len(run) if len(run) >= 2 else '！'
        return run
    return re.sub(r'[!！?？]+', replace, name)


def folder_size(path):
    """Logical file bytes; never follow directory or file symlinks."""
    total = 0
    def fail(error):
        raise error
    for directory, dirs, files in os.walk(path, followlinks=False, onerror=fail):
        checkpoint(f'容量を集計: {Path(directory).name}')
        dirs[:] = [name for name in dirs if not is_link(Path(directory) / name)]
        for name in files:
            checkpoint(f'容量を集計: {name}')
            file = Path(directory) / name
            if not is_link(file):
                total += file.stat().st_size
    return total


def collisions(root, rows, move_groups=False, deleted=(), group_names=None):
    root = Path(root)
    deleted = set(deleted)
    targets = {}
    pairs = []
    for original, new in rows:
        validate_name(original)
        validate_name(new)
        source = root / original
        if source in deleted:
            continue
        confined(root, source)
        if not source.is_dir():
            raise ValueError(f'元のフォルダが見つかりません: {source}')
        group = (group_names or {}).get(original, group_name(original)) if move_groups else ''
        if group:
            validate_name(group)
        destination = root / group / new if group else root / new
        confined(root, destination)
        key = str(destination).casefold()
        if key in targets:
            pairs.append((targets[key], source, destination))
        else:
            targets[key] = source
        if destination.parent.is_dir():
            for existing in destination.parent.iterdir():
                if existing.name.casefold() == new.casefold() and existing != source and existing not in deleted:
                    if existing.is_symlink() or not existing.is_dir():
                        raise ValueError(f'変更先は通常のフォルダではありません: {existing}')
                    pairs.append((existing, source, destination))
    return pairs


def execute_with_deletions(root, rows, create_groups, move_groups, deleted, group_names=None):
    """Quarantine selected folders before execution; restore on failure."""
    root = Path(root).resolve()
    moved = []
    deleted = {Path(source).absolute() for source in deleted}
    # Validate the complete virtual result before quarantining any folder.
    backup = None
    try:
        ops, groups = plan(root, rows, create_groups, move_groups, group_names, deleted=deleted)
        records = []
        if deleted:
            backup = recovery_folder(root, 'folders')
            records = [(source, backup / f'{index:04d}_{source.name}') for index, source in enumerate(sorted(deleted))]
            write_recovery(backup, records)
        for source, target in records:
            confined(root, source)
            move_no_replace(source, target)
            moved.append((source, target))
        retained = [(old, new) for old, new in rows if root / old not in deleted]
        ops, groups = plan(root, retained, create_groups, move_groups, group_names)
        execute(ops, groups)
    except Exception as error:
        failures = []
        for source, target in reversed(moved):
            try:
                if source.exists():
                    raise ValueError(f'復元先が存在します: {source}')
                move_no_replace(target, source, rollback=True)
            except Exception as restore_error:
                failures.append(str(restore_error))
        raise RuntimeError(f'{error}\n' + ('削除対象の復元失敗: ' + '; '.join(failures) if failures else '削除対象を元に戻しました。')) from error
    return ops, groups, backup if moved else None


def segments(name):
    return list(PARTS.finditer(name))


def suggested_name(name, remove_round, remove_square, protected=()):
    pieces, offset = [], 0
    for index, match in enumerate(segments(name)):
        pieces.append(name[offset:match.start()])
        round_part = match.group()[0] in '(（'
        remove = remove_round if round_part else remove_square
        if not remove or index in protected:
            pieces.append(match.group())
        offset = match.end()
    pieces.append(name[offset:])
    return ''.join(pieces).strip()


def group_name(name):
    for match in re.finditer(r'\([^()]*\)|（[^（）]*）', name):
        return match.group()[1:-1].strip()
    return ''


def validate_name(name):
    if not name or name.casefold() == '.folder-tool-trash' or name in ('.', '..') or name.endswith((' ', '.')):
        raise ValueError(f'無効なフォルダ名: {name!r}')
    if any(c in '<>:"/\\|?*' or ord(c) < 32 for c in name):
        raise ValueError(f'Windowsで使用できない文字: {name!r}')
    stem = name.split('.')[0].rstrip(' ').upper()
    if stem in {'CON', 'PRN', 'AUX', 'NUL', 'CONIN$', 'CONOUT$', *(f'COM{i}' for i in '123456789¹²³'), *(f'LPT{i}' for i in '123456789¹²³')}:
        raise ValueError(f'Windowsの予約名: {name!r}')


@dataclass
class Operation:
    source: Path
    destination: Path


def plan(root, rows, create_groups=False, move_groups=False, group_names=None, deleted=()):
    root = Path(root).resolve()
    operations, groups = [], set()
    deleted = {Path(source).absolute() for source in deleted}
    for source in deleted:
        confined(root, source)
        if not source.is_dir() or any(p.name.casefold() == '.folder-tool-trash' for p in (source, *source.parents) if p != root):
            raise ValueError(f'削除対象が無効です: {source}')
        if any(other != source and (other in source.parents or source in other.parents) for other in deleted):
            raise ValueError('親子関係にあるフォルダは同時に削除できません')
    seen_sources = set()
    for original, new_name in rows:
        checkpoint(f'名前を確認: {original}')
        validate_name(original)
        validate_name(new_name)
        source = root / original
        confined(root, source)
        if source in seen_sources:
            raise ValueError(f'元のフォルダが重複しています: {original}')
        seen_sources.add(source)
        if source in deleted:
            continue
        if any(parent in deleted for parent in source.parents):
            raise ValueError(f'元のフォルダが削除対象に含まれます: {source}')
        if is_link(source) or not source.is_dir():
            raise ValueError(f'対象フォルダが存在しないか、リンクです: {original}')
        group = (group_names or {}).get(original, group_name(original)) if create_groups or move_groups else ''
        if group:
            validate_name(group)
            groups.add(root / group)
        destination = root / group / new_name if move_groups and group else root / new_name
        confined(root, destination)
        if any(parent in deleted for parent in destination.parents):
            raise ValueError(f'変更先の親フォルダが削除対象です: {destination}')
        if str(destination) != str(source):
            operations.append(Operation(source, destination))
    sources = {op.source for op in operations}
    destinations = set()
    for op in operations:
        key = str(op.destination).casefold()
        if key in destinations:
            raise ValueError(f'変更先が重複しています: {op.destination.name}')
        destinations.add(key)
        # Reject swaps too: safer than partially overwriting during sequential execution.
        if op.destination.parent.is_dir():
            for existing in op.destination.parent.iterdir():
                if existing.name.casefold() == op.destination.name.casefold() and existing != op.source and existing not in deleted:
                    raise ValueError(f'変更先が既に存在します: {op.destination}')
    for group in groups:
        if group in sources or group in deleted or is_link(group) or (group.exists() and not group.is_dir()):
            raise ValueError(f'分類先を使用できません: {group.name}')
        if any(op.destination == group for op in operations):
            raise ValueError(f'変更先と分類先が重複しています: {group.name}')
    return operations, groups


def execute(operations, groups):
    completed, created = [], []
    try:
        for group in sorted(groups):
            if not group.exists():
                group.mkdir()
                created.append(group)
                record_created(group)
        for op in operations:
            if op.source.parent == op.destination.parent and op.source.name.casefold() == op.destination.name.casefold():
                temporary = op.source.parent / f'.folder-rename-{uuid.uuid4().hex}.tmp'
                move_no_replace(op.source, temporary)
                try:
                    move_no_replace(temporary, op.destination)
                except Exception:
                    move_no_replace(temporary, op.source, rollback=True)
                    raise
            else:
                move_no_replace(op.source, op.destination)
            completed.append(op)
    except Exception as error:
        failures = []
        for op in reversed(completed):
            try:
                if op.source.parent == op.destination.parent and op.source.name.casefold() == op.destination.name.casefold():
                    temporary = op.source.parent / f'.folder-restore-{uuid.uuid4().hex}.tmp'
                    move_no_replace(op.destination, temporary, rollback=True)
                    move_no_replace(temporary, op.source, rollback=True)
                    continue
                if op.source.exists():
                    raise ValueError('元の場所に別のフォルダがあります')
                move_no_replace(op.destination, op.source, rollback=True)
            except Exception as rollback_error:
                failures.append(str(rollback_error))
        for group in reversed(created):
            try:
                group.rmdir()
            except OSError as rollback_error:
                failures.append(str(rollback_error))
        raise RuntimeError(f'処理失敗: {error}\n' + ('復元失敗: ' + '; '.join(failures) if failures else '変更を元に戻しました。')) from error
    return completed, created


def deletion_mask(name, remove_round=True, remove_square=True, overrides=None, square_scope='all'):
    mask = [False] * len(name)
    for match in segments(name):
        remove = remove_round if match.group()[0] in '(（' else remove_square
        if match.group()[0] in '[［':
            if square_scope == 'leading':
                remove = remove and not name[:match.start()].strip()
            elif square_scope == 'trailing':
                remove = remove and not name[match.end():].strip()
        mask[match.start():match.end()] = [remove] * (match.end() - match.start())
    for index, remove in (overrides or {}).items():
        if 0 <= index < len(mask):
            mask[index] = remove
    return mask


def name_from_mask(name, mask):
    return ''.join(char for char, remove in zip(name, mask) if not remove).strip()
