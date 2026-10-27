"""Portable folder selection and non-destructive migration on synthetic data."""
from dataclasses import asdict
from contextlib import closing
import json
import os
from pathlib import Path
import sqlite3
import stat
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch,Mock

from companion import storage
from companion.core import Settings
from scripts.package_source import source_files


class StorageTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.app=self.root/'配布 先';self.app.mkdir()
        self.data=self.app/'Data';self.legacy=self.root/'旧 保存先'/'Yohaku';self.legacy.mkdir(parents=True)

    def test_exe_and_source_paths_ignore_internal_folder_python_and_working_directory(self):
        with patch.object(sys,'frozen',True,create=True),patch.object(sys,'executable',str(self.app/'Yohaku.exe')),patch.object(sys,'_MEIPASS',str(self.app/'_internal'),create=True):
            self.assertEqual(storage.data_directory(),self.data)
        with patch.object(sys,'frozen',False,create=True),patch.object(storage,'__file__',str(self.app/'companion'/'storage.py')):
            self.assertEqual(storage.data_directory(),self.data)

    def test_fresh_install_creates_only_the_data_folder_and_no_legacy_folder(self):
        missing=self.root/'missing'/'Yohaku'
        self.assertFalse(storage.prepare_data_directory(self.data,missing))
        self.assertTrue(self.data.is_dir());self.assertEqual(list(self.data.iterdir()),[])
        self.assertFalse(missing.exists());self.assertFalse(list(self.app.glob('.Yohaku-Data-*')))

    def test_known_json_and_backups_are_copied_but_sources_and_unknown_files_remain(self):
        expected={}
        for name in storage.JSON_NAMES:
            for suffix in ('.json','.json.bak'):
                path=self.legacy/(name+suffix);data=json.dumps({'name':name,'suffix':suffix}).encode()
                path.write_bytes(data);expected[path.name]=data
        for name in ('settings.tmp','dialogue.json.tmp','unrelated.json','private.txt'):(self.legacy/name).write_bytes(b'leave')
        self.assertTrue(storage.prepare_data_directory(self.data,self.legacy))
        self.assertEqual({p.name:p.read_bytes() for p in self.data.iterdir()},expected)
        self.assertTrue(all((self.legacy/name).read_bytes()==data for name,data in expected.items()))
        self.assertEqual((self.legacy/'unrelated.json').read_bytes(),b'leave')

    def test_database_backup_includes_committed_wal_records_without_deleting_the_source(self):
        source=self.legacy/'files.sqlite3';connection=sqlite3.connect(source)
        try:
            connection.execute('PRAGMA journal_mode=WAL');connection.execute('PRAGMA wal_autocheckpoint=0')
            connection.execute('CREATE TABLE samples(name TEXT)');connection.commit()
            connection.execute("INSERT INTO samples VALUES ('committed in WAL')");connection.commit()
            self.assertTrue(source.with_name(source.name+'-wal').exists())
            self.assertTrue(storage.prepare_data_directory(self.data,self.legacy))
            with closing(sqlite3.connect(self.data/'files.sqlite3')) as migrated:
                self.assertEqual(migrated.execute('SELECT name FROM samples').fetchall(),[('committed in WAL',)])
            self.assertTrue(source.exists());self.assertEqual(connection.execute('SELECT count(*) FROM samples').fetchone(),(1,))
        finally:connection.close()

    def test_existing_data_including_empty_folder_is_never_merged_or_overwritten(self):
        (self.legacy/'settings.json').write_bytes(b'legacy')
        self.data.mkdir();self.assertFalse(storage.prepare_data_directory(self.data,self.legacy))
        self.assertEqual(list(self.data.iterdir()),[])
        (self.data/'settings.json').write_bytes(b'portable')
        self.assertFalse(storage.prepare_data_directory(self.data,self.legacy))
        self.assertEqual((self.data/'settings.json').read_bytes(),b'portable')
        self.assertEqual((self.legacy/'settings.json').read_bytes(),b'legacy')

    def test_copy_failure_cannot_commit_partial_data_and_next_start_can_retry(self):
        for name in ('settings.json','dialogue.json'):(self.legacy/name).write_bytes(b'original')
        original=storage.shutil.copyfile;calls=[]
        def copy(source,destination):
            calls.append(source)
            if len(calls)==2:raise OSError('synthetic disk failure')
            return original(source,destination)
        with patch('companion.storage.shutil.copyfile',side_effect=copy),self.assertRaises(storage.StorageError):
            storage.prepare_data_directory(self.data,self.legacy)
        self.assertFalse(self.data.exists());self.assertFalse(list(self.app.glob('.Yohaku-Data-*')))
        self.assertTrue(all(p.read_bytes()==b'original' for p in self.legacy.iterdir()))
        self.assertTrue(storage.prepare_data_directory(self.data,self.legacy))
        self.assertEqual((self.data/'dialogue.json').read_bytes(),b'original')

    def test_invalid_history_leaves_originals_and_does_not_publish_partial_json(self):
        (self.legacy/'settings.json').write_bytes(b'original')
        (self.legacy/'files.sqlite3').write_bytes(b'not a database')
        with self.assertRaises(storage.StorageError):storage.prepare_data_directory(self.data,self.legacy)
        self.assertFalse(self.data.exists());self.assertFalse(list(self.app.glob('.Yohaku-Data-*')))
        self.assertEqual((self.legacy/'settings.json').read_bytes(),b'original')
        self.assertEqual((self.legacy/'files.sqlite3').read_bytes(),b'not a database')

    def test_unwritable_data_reports_failure_without_falling_back(self):
        self.data.mkdir();(self.data/'settings.json').write_bytes(b'keep')
        with patch('companion.storage.tempfile.TemporaryFile',side_effect=PermissionError()),self.assertRaises(storage.StorageError):
            storage.prepare_data_directory(self.data,self.legacy)
        self.assertEqual((self.data/'settings.json').read_bytes(),b'keep');self.assertFalse(list(self.legacy.iterdir()))

    def test_reparse_files_are_not_imported(self):
        path=Mock();path.lstat.return_value=SimpleNamespace(st_mode=stat.S_IFREG,st_file_attributes=0x400)
        with self.assertRaises(storage.StorageError):storage.regular_file(path)

    def test_user_data_unknown_filenames_and_interrupted_staging_are_excluded_from_distribution(self):
        for n,name in enumerate(('Data','data','DATA')):
            project=self.root/str(n);project.mkdir();(project/'main.py').write_text('source')
            private=project/name;private.mkdir();(private/'custom-secret.json').write_text('private')
            (private/'unknown.txt').write_text('private')
            staged=project/'.Yohaku-Data-leftover';staged.mkdir();(staged/'unknown.txt').write_text('private')
            (project/'.Yohaku.init.lock').write_text('private')
            assets=project/'companion/assets/data';assets.mkdir(parents=True);(assets/'default.json').write_text('bundled')
            self.assertEqual({p.relative_to(project).as_posix() for p in source_files(project)},{'main.py','companion/assets/data/default.json'})


class StorageStartupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from companion.ui import create_application
        cls.app=create_application()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name);self.project=self.root/'app';self.project.mkdir()
        self.data=self.project/'Data';self.legacy=self.root/'old'/'Yohaku';self.legacy.mkdir(parents=True)
        (self.legacy/'settings.json').write_text('{}')

    def test_first_start_migrates_and_the_data_lock_blocks_a_second_instance(self):
        from companion.ui import lock_data_directory
        with patch('companion.storage.legacy_directory',return_value=self.legacy):
            lock=lock_data_directory(self.data)
            try:
                self.assertTrue(lock.isLocked());self.assertEqual((self.data/'settings.json').read_text(),'{}')
                with self.assertRaises(storage.StorageError):lock_data_directory(self.data)
                self.assertEqual((self.legacy/'settings.json').read_text(),'{}')
            finally:lock.unlock()

    def test_running_legacy_version_blocks_the_copy_without_creating_data(self):
        from PySide6.QtCore import QLockFile
        from companion.ui import lock_data_directory
        old_lock=QLockFile(str(self.legacy/'instance.lock'));self.assertTrue(old_lock.tryLock(0))
        try:
            with patch('companion.storage.legacy_directory',return_value=self.legacy),self.assertRaises(storage.StorageError):
                lock_data_directory(self.data)
            self.assertFalse(self.data.exists());self.assertEqual((self.legacy/'settings.json').read_text(),'{}')
        finally:old_lock.unlock()

    def test_default_controller_creates_settings_and_uses_Data_for_all_stores(self):
        from companion.ui import Controller
        from PySide6.QtWidgets import QSystemTrayIcon
        with patch('companion.storage.application_directory',return_value=self.project),patch('companion.ui.Settings.load',return_value=Settings(context_enabled=False,mail_enabled=False)),patch.object(QSystemTrayIcon,'isSystemTrayAvailable',return_value=True):
            controller=Controller(self.app)
        try:
            self.assertEqual(controller.path,self.data)
            self.assertTrue((self.data/'settings.json').is_file())
            self.assertFalse(json.loads((self.data/'settings.json').read_text())['outlook_enabled'])
            stores=(controller.dialogue,controller.engine.context_options,controller.engine.topic_preferences,
                    controller.engine.reminders,controller.engine.one_shots,controller.activity_history,
                    controller.file_drop_service.store,controller.file_drop_service.destinations,controller.shelf_service.store)
            self.assertTrue(all(store.path.parent==self.data for store in stores))
        finally:
            controller.shutdown();controller.tray.hide()
            for widget in (controller.resident,controller.bubble,controller.panel,controller.history_window):widget.hide()
            controller.deleteLater();self.app.processEvents()
