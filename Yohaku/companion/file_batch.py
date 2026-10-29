"""A bounded drop selection and sequential operations with honest partial results."""
from pathlib import Path
import os

from .file_drop import ARCHIVE_EXTENSIONS,FileDropError,dropped_item,file_identity,folder_snapshot

MAX_DROP_ITEMS=500


def selection(value):
    values=value if isinstance(value,(list,tuple)) else (value,)
    if not 1<=len(values)<=MAX_DROP_ITEMS:raise FileDropError('一度に渡せるのは1〜500項目です。')
    paths=[];seen=set()
    for value in values:
        path=dropped_item(value);key=os.path.normcase(os.path.normpath(str(path)))
        if key not in seen:paths.append(path);seen.add(key)
    return tuple(paths)


def group_kind(paths):
    if all(path.is_file() and path.suffix.lower()=='.pdf' for path in paths):return 'pdf'
    if all(path.is_file() and path.suffix.lower() in ARCHIVE_EXTENSIONS for path in paths):return 'archive'
    return 'other'


def check_identities(paths,identities):
    if len(paths)!=len(identities):raise FileDropError('対象の確認情報が一致しません。')
    for path,expected in zip(paths,identities):
        if file_identity(dropped_item(path))!=expected:
            raise FileDropError(path.name+' が変更されています。もう一度ドロップしてください。')


def preflight(paths,identities,operation,rules):
    check_identities(paths,identities)
    if len(paths)!=len(rules):raise FileDropError('対象の処理設定が一致しません。')
    if operation not in ('move','extract'):return
    seen=set();sources=[path.resolve() for path in paths]
    if operation=='move' and any(a in b.parents for a in sources for b in sources if a!=b):
        raise FileDropError('親フォルダーとその中の項目が重複しています。別々に渡してください。')
    for path,rule in zip(paths,rules):
        folder=Path(rule['destination']).resolve();target=folder/(path.stem if operation=='extract' else path.name)
        key=str(target).casefold()
        if key in seen:raise FileDropError('同名の処理先になる項目があります。上書きせず中止しました。')
        seen.add(key)
        if path.is_dir() and (folder==path.resolve() or path.resolve() in folder.parents):
            raise FileDropError('フォルダー自身や、その中には移動できません。')
        if target.exists() or target.is_symlink():
            if operation=='extract' or target.resolve()!=path.resolve():
                raise FileDropError('処理先に同名の項目があります。上書きせず中止しました。')
        if operation=='move' and path.is_dir():folder_snapshot(path)


def execute_batch(paths,identities,operation,rules,now,execute_item):
    completed=[];error=''
    try:
        preflight(paths,identities,operation,rules)
        for index,(path,rule) in enumerate(zip(paths,rules)):
            check_identities((path,),(identities[index],))
            result=execute_item(operation,path,rule,now)
            if operation=='print_pdf' and not result.get('printed'):
                raise FileDropError('印刷を中止しました。')
            completed.append(dict(name=path.name,result=result))
    except FileDropError as problem:error=str(problem)
    except Exception:error='処理を完了できません。ファイル・処理先・プリンターを確認してください。'
    return dict(batch=True,operation=operation,total=len(paths),completed=completed,
                remaining=[path.name for path in paths[len(completed):]],error=error)
