"""Bounded file-drop rules and data-preserving move / ZIP extraction operations."""
from copy import deepcopy
from datetime import datetime
import errno
import json
import os
from pathlib import Path, PurePosixPath, PureWindowsPath
import re
import shutil
import stat
import tempfile

from .context_options import ContextOptionsStore

ACTIONS = {'move': '移動する', 'print_pdf': 'PDFを印刷する', 'move_extract': '移動して解凍する', 'extract': '解凍する'}
ARCHIVE_EXTENSIONS = {'.zip','.7z'}
MAX_ENTRIES = 10000
MAX_EXPANDED_BYTES = 1024 ** 3


class FileDropError(ValueError):
    pass


def defaults():
    def rule(key, title, extensions, actions):
        return dict(id=key, label=title, extensions=extensions, destination='', password_template='',
                    actions=[{'action': action, 'label': ACTIONS[action]} for action in actions])
    return {'schema_version': 1, 'enabled': True, 'rules': [
        rule('pdf', 'PDF', ['.pdf'], ['move', 'print_pdf']),
        rule('zip', 'ZIP / 7z', ['.zip','.7z'], ['move_extract']),
        rule('other', 'その他のファイル', ['*'], ['move']),
        rule('folder', 'フォルダー', ['<folder>'], ['move'])]}


def password_value(template, now):
    values = {'month': f'{now.month:02d}', 'month1': str(now.month), 'year': str(now.year)}
    return re.sub(r'\{(month1|month|year)\}', lambda m: values[m[1]], template)


def validate(document):
    if (not isinstance(document, dict) or set(document) != {'schema_version', 'enabled', 'rules'}
            or type(document['schema_version']) is not int or document['schema_version'] != 1
            or type(document['enabled']) is not bool or not isinstance(document['rules'], list)
            or not 1 <= len(document['rules']) <= 30):
        raise FileDropError('ファイル操作の設定形式が不正です。ルールは1〜30件です。')
    ids, extensions = set(), set()
    for rule in document['rules']:
        if not isinstance(rule, dict) or set(rule) != {'id', 'label', 'extensions', 'destination', 'password_template', 'actions'}:
            raise FileDropError('ルールには定義済みの設定項目だけを指定してください。')
        key = rule['id']
        if not isinstance(key, str) or not re.fullmatch(r'[a-z][a-z0-9_]{0,31}', key) or key in ids:
            raise FileDropError('ルールIDが不正または重複しています。')
        ids.add(key)
        if not isinstance(rule['label'], str) or not 1 <= len(rule['label'].strip()) <= 60:
            raise FileDropError('ルール名は1〜60文字です。')
        items = rule['extensions']
        if not isinstance(items, list) or not 1 <= len(items) <= 30:
            raise FileDropError('拡張子はルールごとに1〜30個です。')
        for extension in items:
            if (not isinstance(extension, str) or extension not in ('*', '<folder>') and not re.fullmatch(r'\.[a-z0-9]{1,15}', extension)
                    or extension in extensions or extension in ('*', '<folder>') and len(items) != 1):
                raise FileDropError('拡張子は.pdfなど、フォルダーは<folder>、その他は*で指定し、重複させないでください。')
            extensions.add(extension)
        folder, template = rule['destination'], rule['password_template']
        if (not isinstance(folder, str) or len(folder) > 2048 or '\0' in folder
                or folder and not (Path(folder).is_absolute() or PureWindowsPath(folder).is_absolute())):
            raise FileDropError('移動先は空欄か、フォルダーの絶対パスを指定してください。')
        if (not isinstance(template, str) or len(template) > 256 or any(c in template for c in ('\0', '\n', '\r'))
                or any(c in re.sub(r'\{(?:month1|month|year)\}', '', template) for c in '{}')):
            raise FileDropError('パスワードの変数は{month}・{month1}・{year}を使用してください。')
        rows = rule['actions']
        if not isinstance(rows, list) or not 1 <= len(rows) <= 3:
            raise FileDropError('処理は1〜3個です。')
        seen = set()
        for row in rows:
            if (not isinstance(row, dict) or set(row) != {'action', 'label'}
                    or not isinstance(row['action'], str) or row['action'] not in ACTIONS or row['action'] in seen
                    or not isinstance(row['label'], str) or not 1 <= len(row['label'].strip()) <= 60):
                raise FileDropError('処理と表示名が不正です。実行コマンドは指定できません。')
            seen.add(row['action'])
            if row['action'] == 'print_pdf' and items != ['.pdf']:
                raise FileDropError('印刷は.pdf専用のルールに設定してください。')
            if row['action'] in ('move_extract','extract') and not set(items) <= ARCHIVE_EXTENSIONS:
                raise FileDropError('解凍は対応する圧縮形式だけのルールに設定してください。')
    return deepcopy(document)


class FileDropStore(ContextOptionsStore):
    validate = staticmethod(validate)

    def __init__(self, path):
        self.path = Path(path); self.data = defaults(); self.error = ''
        if self.path.exists():
            try:
                if self.path.stat().st_size > 1024 * 1024:
                    raise FileDropError('設定JSONが大きすぎます。')
                self.data = validate(json.loads(self.path.read_text(encoding='utf-8-sig')))
            except (OSError, ValueError, TypeError, RecursionError):
                self.error = 'ファイル操作の設定を読み込めません。元のJSONは保持しています。'

    def matching_rule(self, path):
        if self.error or not self.data['enabled']:
            return None
        extension = '<folder>' if Path(path).is_dir() else Path(path).suffix.lower()
        for rule in self.data['rules']:
            if extension in rule['extensions']:
                return deepcopy(rule)
        if extension=='.7z':
            rule=next((deepcopy(row) for row in self.data['rules'] if '.zip' in row['extensions']),None)
            if rule is not None:
                rule['extensions']=['.7z'];return rule
        rule = next((deepcopy(rule) for rule in self.data['rules'] if rule['extensions'] == ['*']), None)
        if extension == '<folder>' and rule:
            rule['actions'] = [row for row in rule['actions'] if row['action'] == 'move']
        return rule if rule and rule['actions'] else None


def is_link(path):
    value = Path(path).lstat()
    return stat.S_ISLNK(value.st_mode) or bool(getattr(value, 'st_file_attributes', 0) & 0x400)


def dropped_item(path):
    path = Path(path)
    try:
        if not path.is_absolute() or is_link(path) or not (path.is_file() or path.is_dir()) or path.parent == path:
            raise FileDropError('通常のファイルかフォルダーを1つ選んでください。リンクは対象外です。')
        return path.absolute()
    except OSError:
        raise FileDropError('ファイルまたはフォルダーを確認できません。') from None


def folder_snapshot(source):
    """Bounded inventory; never traverse symbolic links or Windows junctions."""
    result = {}; total = 0; pending = [Path(source)]
    while pending:
        path = pending.pop()
        if is_link(path):
            raise FileDropError('リンクを含むフォルダーは移動できません。元の場所に保持しました。')
        directory = path.is_dir()
        if not directory and not path.is_file():
            raise FileDropError('通常のファイル以外が含まれています。')
        identity = file_identity(path)
        result[str(path.relative_to(source))] = (directory, identity)
        if directory:
            pending.extend(path.iterdir())
        else:
            total += identity[2]
        if len(result) > MAX_ENTRIES or total > MAX_EXPANDED_BYTES:
            raise FileDropError('フォルダーの移動は10,000項目・合計1GiBまでです。')
    return result


def remove_copied_folder(source, snapshot):
    """Delete only the inventoried entries; keep later additions or edits."""
    def same_directory(path):
        key = str(path.relative_to(source)); old = snapshot.get(key)
        return old and old[0] and not is_link(path) and file_identity(path)[:2] == old[1][:2]
    for key, (directory, identity) in snapshot.items():
        if directory:
            continue
        path = source/key
        try:
            ancestors = [path.parent]
            while ancestors[-1] != source:
                ancestors.append(ancestors[-1].parent)
            if all(same_directory(parent) for parent in ancestors) and not is_link(path) and file_identity(path) == identity:
                path.unlink()
        except OSError:
            pass
    for key, (directory, _) in sorted(snapshot.items(), key=lambda row: len(Path(row[0]).parts), reverse=True):
        if directory:
            path = source/key
            try:
                if same_directory(path):
                    path.rmdir()  # New children cause failure and remain untouched.
            except OSError:
                pass
    return source.exists() or source.is_symlink()


def move_folder(source, rule):
    source = dropped_item(source)
    configured = Path(rule['destination']) if rule['destination'] else None
    if configured and (configured.resolve() == source.resolve() or source.resolve() in configured.resolve().parents):
        raise FileDropError('フォルダー自身や、その中には移動できません。')
    before = folder_snapshot(source)
    folder = destination(rule); target = folder/source.name
    if target.resolve() == source.resolve():
        return {'path': str(source)}
    if target.exists() or target.is_symlink():
        raise FileDropError('移動先に同名の項目があります。上書きせず中止しました。')
    try:
        # Copy to a private staging directory on the destination volume first.
        # Keep the entire original until a complete copy has been published.
        with tempfile.TemporaryDirectory(prefix='.yohaku-move-', dir=folder) as temporary:
            stage = Path(temporary)/'content'
            shutil.copytree(source, stage, symlinks=True)
            if folder_snapshot(source) != before:
                raise FileDropError('処理中にフォルダーが変更されました。元の場所に保持しました。')
            copied = folder_snapshot(stage)
            if set(copied) != set(before) or any(copied[key][0] != row[0] or not row[0] and copied[key][1][2:4] != row[1][2:4] for key, row in before.items()):
                raise FileDropError('コピー結果を確認できません。元の場所に保持しました。')
            if target.exists() or target.is_symlink():
                raise FileDropError('移動先に同名の項目があります。上書きせず中止しました。')
            stage.rename(target)
        retained = remove_copied_folder(source, before)
        return {'path': str(target), 'source_retained': retained}
    except FileDropError:
        raise
    except OSError:
        raise FileDropError('フォルダーを移動できません。元の場所に保持しました。') from None


def regular_file(path):
    path = Path(path)
    try:
        if not path.is_absolute() or is_link(path) or not path.is_file():
            raise FileDropError('通常のファイルを1つ選んでください。フォルダーやリンクは対象外です。')
        return path.absolute()
    except OSError:
        raise FileDropError('ファイルを確認できません。') from None


def destination(rule):
    if not rule['destination']:
        raise FileDropError('先に設定画面で移動先を指定してください。')
    path = Path(rule['destination'])
    if not path.is_absolute():
        raise FileDropError('このPCのフォルダーの絶対パスを指定してください。')
    try:
        path.mkdir(parents=True, exist_ok=True)
        if not path.is_dir():
            raise OSError()
    except OSError:
        raise FileDropError('移動先フォルダーを利用できません。') from None
    return path


def file_identity(path):
    value = path.stat()
    return value.st_dev, value.st_ino, value.st_size, value.st_mtime_ns


def move_file(source, target):
    """Do not overwrite; a failed cross-volume copy must keep the source."""
    source = regular_file(source); target = Path(target)
    if target.is_symlink():
        raise FileDropError('移動先がリンクです。上書きせず中止しました。')
    if source.resolve() == target.resolve():
        return target
    if target.exists() or target.is_symlink():
        raise FileDropError('移動先に同名のファイルがあります。上書きせず中止しました。')
    try:
        if os.name == 'nt':
            source.rename(target)  # Windows rename never replaces an existing file.
        else:
            os.link(source, target, follow_symlinks=False)
            try:
                source.unlink()
            except OSError:
                target.unlink(); raise
        return target
    except OSError as error:
        if error.errno != errno.EXDEV:
            raise FileDropError('ファイルを移動できません。使用中・権限・同名ファイルを確認してください。') from None
    created = False
    try:
        before = file_identity(source)
        with source.open('rb') as reader, target.open('xb') as writer:
            created = True
            shutil.copyfileobj(reader, writer, 1024 * 1024)
        if source.is_symlink() or file_identity(source) != before:
            raise OSError('Source changed')
        shutil.copystat(source, target, follow_symlinks=False)
        source.unlink()
        return target
    except OSError:
        if created:
            target.unlink(missing_ok=True)
        raise FileDropError('移動を完了できません。元ファイルは保持しました。') from None


def archive_members(archive):
    members = archive.infolist()
    if len(members) > MAX_ENTRIES or sum(row.file_size for row in members) > MAX_EXPANDED_BYTES:
        raise FileDropError('解凍は10,000項目・合計1GiBまでです。')
    seen = set(); result = []
    for row in members:
        name = row.filename
        path = PurePosixPath(name.rstrip('/'))
        if (not name or getattr(row, 'orig_filename', name) != name or path.is_absolute() or not path.parts or any(p in ('.', '..') for p in name.rstrip('/').split('/'))
                or any(c in name for c in ('\\', ':', '\0')) or stat.S_ISLNK(row.external_attr >> 16)
                or any(p.endswith((' ', '.')) or re.fullmatch(r'(?:con|prn|aux|nul|com[1-9¹²³]|lpt[1-9¹²³])', p.split('.')[0].rstrip(' .'), re.I) for p in path.parts)
                or any(c in name for c in '<>"|?*') or any(ord(c) < 32 for c in name)):
            raise FileDropError('解凍先の外へのパスや、対応できない名前・リンクが含まれています。')
        key = str(path).casefold()
        if key in seen:
            raise FileDropError('圧縮ファイル内に重複する名前があります。')
        seen.add(key); result.append((row, path))
    return result


def move_extract(source, rule, now, move_source=True):
    import pyzipper
    source = regular_file(source)
    if source.suffix.lower() not in ARCHIVE_EXTENSIONS:
        raise FileDropError('この圧縮形式には対応していません。')
    folder = destination(rule); target = folder/source.name; final = folder/source.stem
    if final.exists() or final.is_symlink() or final == target:
        raise FileDropError('同名の解凍先があります。上書きせず中止しました。')
    if move_source and source.resolve() != target.resolve() and (target.exists() or target.is_symlink()):
        raise FileDropError('移動先に同名の圧縮ファイルがあります。上書きせず中止しました。')
    before = file_identity(source)
    password = password_value(rule['password_template'], now).encode('utf-8') or None
    try:
        with tempfile.TemporaryDirectory(prefix='.yohaku-extract-', dir=folder) as temporary:
            stage = Path(temporary)/'content'; stage.mkdir()
            if source.suffix.lower()=='.7z':
                from .seven_zip import extract_7z
                extract_7z(source,stage,password.decode('utf-8') if password else '')
            else:
                with pyzipper.AESZipFile(source) as archive:
                    members = archive_members(archive); written = 0
                    for member, relative in members:
                        output = stage.joinpath(*relative.parts)
                        if member.is_dir():
                            output.mkdir(parents=True, exist_ok=True); continue
                        output.parent.mkdir(parents=True, exist_ok=True)
                        with archive.open(member, pwd=password) as reader, output.open('xb') as writer:
                            file_bytes = 0
                            for block in iter(lambda: reader.read(1024 * 1024), b''):
                                written += len(block); file_bytes += len(block)
                                if written > MAX_EXPANDED_BYTES or file_bytes > member.file_size:
                                    raise FileDropError('解凍サイズの上限を超えています。')
                                writer.write(block)
                            if file_bytes != member.file_size:
                                raise FileDropError('圧縮データのサイズが不正です。')
            if source.is_symlink() or file_identity(source) != before:
                raise FileDropError('処理中に圧縮ファイルが変更されました。中止しました。')
            moved = move_file(source, target) if move_source else source
            try:
                if final.exists() or final.is_symlink():
                    raise OSError()
                stage.rename(final)
            except OSError:
                if source.resolve() != moved.resolve():
                    try:
                        move_file(moved, source)
                    except FileDropError:
                        raise FileDropError('解凍結果を配置できません。圧縮ファイルは移動先に保持しています。') from None
                raise FileDropError('解凍結果を配置できません。圧縮ファイルは保持しています。') from None
    except FileDropError:
        raise
    except (OSError, RuntimeError, ValueError, NotImplementedError, pyzipper.BadZipFile):
        raise FileDropError('解凍できません。パスワード・圧縮データ・空き容量・権限を確認してください。元ファイルは移動していません。') from None
    return {'path': str(target if move_source else source), 'extracted': str(final),'source_preserved':not move_source}


def execute(action, path, rule, now=None):
    # Revalidate a snapshot immediately before executing the selected action.
    validate({'schema_version': 1, 'enabled': True, 'rules': [rule]})
    if action not in {row['action'] for row in rule['actions']}:
        raise FileDropError('この処理はルールに登録されていません。')
    source = dropped_item(path)
    if source.is_dir():
        if action != 'move' or not set(rule['extensions']) <= {'<folder>', '*'}:
            raise FileDropError('フォルダーは移動だけを選べます。')
        return move_folder(source, rule)
    if source.suffix.lower() not in rule['extensions'] and '*' not in rule['extensions']:
        raise FileDropError('ファイルの拡張子とルールが一致しません。')
    if action == 'move':
        return {'path': str(move_file(source, destination(rule)/source.name))}
    if action in ('move_extract','extract'):
        return move_extract(source, rule, now or datetime.now().astimezone(),move_source=action=='move_extract')
    raise FileDropError('印刷は画面の印刷ダイアログから実行してください。')
