"""Portable user data beside the EXE, with an all-or-nothing legacy copy."""
import os
from contextlib import closing
from pathlib import Path
import shutil
import sqlite3
import stat
import sys
import tempfile
import time

JSON_NAMES=('settings','dialogue','history','usage','context_options','topic_preferences',
            'reminders','one_shot_notifications','file_drop_settings','file_destinations','shelf')


class StorageError(OSError):pass


def application_directory():
    if getattr(sys,'frozen',False):return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parents[1]


def data_directory():return application_directory()/'Data'


def legacy_directory():
    return Path(os.environ.get('LOCALAPPDATA',Path.home()/'.local'/'share'))/'Yohaku'


def regular_file(path):
    info=path.lstat()
    if not stat.S_ISREG(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
        raise StorageError('旧保存先に通常ファイル以外があり、データをコピーできません。')


def copy_history(source,destination):
    regular_file(source);started=time.monotonic()
    def progress(status,remaining,total):
        if time.monotonic()-started>10:raise StorageError('ファイル履歴のコピーを完了できません。旧版を終了して再起動してください。')
    # SQLite backup includes committed WAL records; copying only the main file
    # could silently omit recent history. The legacy database is opened read-only.
    with closing(sqlite3.connect(source.resolve().as_uri()+'?mode=ro',uri=True,timeout=2)) as original:
        with closing(sqlite3.connect(destination)) as copied:
            original.backup(copied,pages=128,progress=progress,sleep=.05)
            if copied.execute('PRAGMA quick_check').fetchone()!=('ok',):
                raise StorageError('旧ファイル履歴をコピーできません。元のデータは保持しています。')
            copied.commit()


def prepare_data_directory(target,legacy=None):
    target=Path(target);legacy=Path(legacy) if legacy is not None else legacy_directory()
    try:
        if target.exists():
            info=target.lstat()
            if not stat.S_ISDIR(info.st_mode) or getattr(info,'st_file_attributes',0)&0x400:
                raise StorageError('Dataが通常のフォルダではありません。アプリの配置先をご確認ください。')
            # Existing Data always wins, including an intentionally empty folder.
            with tempfile.TemporaryFile(dir=target):pass
            return False
        target.parent.mkdir(parents=True,exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.Yohaku-Data-',dir=target.parent) as temporary:
            staged=Path(temporary);copied=False
            if legacy.is_dir():
                for name in JSON_NAMES:
                    for suffix in ('.json','.json.bak'):
                        source=legacy/(name+suffix)
                        if source.exists() or source.is_symlink():
                            regular_file(source);shutil.copyfile(source,staged/source.name);copied=True
                database=legacy/'files.sqlite3'
                if database.exists() or database.is_symlink():
                    copy_history(database,staged/database.name);copied=True
            if target.exists():raise StorageError('準備中にDataが作成されました。上書きせず停止しました。再起動してください。')
            # Windows rename refuses an existing destination. Commit the whole
            # directory only after every copy succeeds, while startup is locked.
            staged.rename(target)
        return copied
    except StorageError:raise
    except sqlite3.Error as error:
        raise StorageError('旧保存先のファイル履歴を読み込めず、移行を中止しました。元のデータは保持しています。旧保存先をバックアップしてご確認ください。') from error
    except OSError as error:
        raise StorageError('Dataを準備できません。アプリを書き込み可能なフォルダに置き、空き容量と旧版の終了をご確認ください。元のデータは保持しています。') from error
