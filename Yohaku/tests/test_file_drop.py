"""Synthetic-file tests for limited rules, no-overwrite moves and encrypted ZIPs."""
from copy import deepcopy
from datetime import datetime
import errno
import json
from pathlib import Path
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

import pyzipper
from companion.file_drop import (FileDropError, FileDropStore, defaults, execute, password_value, validate)
from scripts.package_source import source_files


class FileDropTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        self.root = Path(self.temporary.name); self.inbox = self.root/'in'; self.inbox.mkdir()
        self.output = self.root/'out'; self.output.mkdir()

    def rule(self, index):
        rule = defaults()['rules'][index]; rule['destination'] = str(self.output)
        return rule

    def zip(self, name='資料.zip', rows=None, password=None):
        path = self.inbox/name
        if password is None:
            with zipfile.ZipFile(path, 'w', zipfile.ZIP_STORED) as archive:
                for key, value in (rows or {'フォルダー/資料.txt': b'content'}).items():
                    archive.writestr(key, value)
        else:
            with pyzipper.AESZipFile(path, 'w', compression=pyzipper.ZIP_DEFLATED, encryption=pyzipper.WZ_AES) as archive:
                archive.setpassword(password)
                archive.writestr('フォルダー/資料.txt', b'content')
        return path

    def test_matching_is_case_insensitive_with_explicit_extensions_before_fallback(self):
        store = FileDropStore(self.root/'file_drop_settings.json')
        store.data['rules'].insert(0, store.data['rules'].pop())
        for name, expected in [('資料.PDF', 'pdf'), ('資料.ZIP', 'zip'), ('資料.xlsx', 'other'), ('README', 'other')]:
            self.assertEqual(store.matching_rule(name)['id'], expected)
        store.data['enabled'] = False; self.assertIsNone(store.matching_rule('a.pdf'))

    def test_month_templates_at_boundaries_and_literal_passwords(self):
        self.assertEqual(password_value('fixed{month}', datetime(2026, 1, 31)), 'fixed01')
        self.assertEqual(password_value('fixed{month}', datetime(2026, 12, 1)), 'fixed12')
        self.assertEqual(password_value('{year}-{month1}', datetime(2026, 2, 1)), '2026-2')
        self.assertEqual(password_value('unchanged', datetime(2026, 2, 1)), 'unchanged')

    def test_commands_bad_templates_duplicate_extensions_and_unsupported_actions_are_rejected(self):
        for mutation in ('command', 'unknown_action', 'template', 'duplicate', 'wildcard_print', 'extension', 'too_many'):
            document = defaults()
            if mutation == 'command': document['rules'][0]['command'] = 'echo unwanted'
            if mutation == 'unknown_action': document['rules'][0]['actions'][0]['action'] = 'shell'
            if mutation == 'template': document['rules'][1]['password_template'] = '{month.__class__}'
            if mutation == 'duplicate': document['rules'][1]['extensions'] = ['.pdf']
            if mutation == 'wildcard_print': document['rules'][0]['extensions'] = ['.txt']
            if mutation == 'extension': document['rules'][1]['extensions'] = ['.exe']
            if mutation == 'too_many': document['rules'] *= 11
            with self.subTest(mutation=mutation), self.assertRaises(FileDropError): validate(document)

    def test_store_preserves_original_and_backup_and_does_not_expose_invalid_password(self):
        path = self.root/'file_drop_settings.json'; store = FileDropStore(path)
        document = defaults(); document['rules'][1]['password_template'] = 'sample{month}'
        store.save(document); raw = path.read_bytes()
        candidate = deepcopy(document); candidate['rules'][1]['destination'] = str(self.output)
        store.save(candidate); self.assertEqual(path.with_suffix('.json.bak').read_bytes(), raw)
        self.assertEqual(FileDropStore(path).data, candidate)
        path.write_text('{"password_template":"SENSITIVE', encoding='utf-8')
        broken = FileDropStore(path)
        self.assertTrue(broken.error); self.assertNotIn('SENSITIVE', broken.error)
        self.assertIsNone(broken.matching_rule('a.zip'))
        self.assertIn('SENSITIVE', path.read_text())

    def test_settings_and_secret_backups_are_excluded_from_source_packaging(self):
        for suffix in ('.json', '.json.bak', '.json.tmp'):
            (self.root/('file_drop_settings'+suffix)).write_text('private', encoding='utf-8')
        (self.root/'FILE_DROP_SETTINGS.JSON').write_text('private', encoding='utf-8')
        (self.root/'main.py').write_text('code', encoding='utf-8')
        self.assertEqual([p.name for p in source_files(self.root)], ['main.py'])

    def test_move_requires_explicit_registered_action_and_keeps_bytes(self):
        source = self.inbox/'資料.txt'; source.write_bytes(b'original')
        rule = self.rule(2)
        with self.assertRaises(FileDropError): execute('shell', source, rule)
        self.assertTrue(source.exists()); self.assertFalse((self.output/source.name).exists())
        result = execute('move', source, rule)
        self.assertFalse(source.exists()); self.assertEqual(Path(result['path']).read_bytes(), b'original')

    def test_move_does_not_overwrite_existing_file_or_follow_source_links(self):
        source = self.inbox/'a.txt'; source.write_bytes(b'original')
        target = self.output/source.name; target.write_bytes(b'existing')
        with self.assertRaises(FileDropError): execute('move', source, self.rule(2))
        self.assertEqual(source.read_bytes(), b'original'); self.assertEqual(target.read_bytes(), b'existing')
        link = self.inbox/'link.txt'
        try: link.symlink_to(source)
        except OSError: return
        with self.assertRaises(FileDropError): execute('move', link, self.rule(2))
        self.assertTrue(source.exists())

    def test_cross_volume_move_and_copy_failure_preserve_source(self):
        for fail in (False, True):
            source = self.inbox/f'cross{fail}.txt'; source.write_bytes(b'original')
            with patch('companion.file_drop.os.link', side_effect=OSError(errno.EXDEV, 'cross device')), \
                    patch('companion.file_drop.Path.rename', side_effect=OSError(errno.EXDEV, 'cross device')):
                if fail:
                    with patch('companion.file_drop.shutil.copyfileobj', side_effect=OSError('disk full')):
                        with self.assertRaises(FileDropError): execute('move', source, self.rule(2))
                    self.assertEqual(source.read_bytes(), b'original'); self.assertFalse((self.output/source.name).exists())
                else:
                    result = execute('move', source, self.rule(2))
                    self.assertFalse(source.exists()); self.assertEqual(Path(result['path']).read_bytes(), b'original')

    def test_unencrypted_zip_moves_and_extracts_into_a_new_subfolder(self):
        source = self.zip()
        result = execute('move_extract', source, self.rule(1), datetime(2026, 10, 1))
        self.assertFalse(source.exists()); self.assertTrue(Path(result['path']).is_file())
        self.assertEqual((Path(result['extracted'])/'フォルダー/資料.txt').read_bytes(), b'content')
        self.assertFalse(any(p.name.startswith('.yohaku-extract-') for p in self.output.iterdir()))

    def test_aes_zip_uses_execution_month_and_wrong_password_does_not_move_source(self):
        source = self.zip(password=b'sample01'); original = source.read_bytes()
        rule = self.rule(1); rule['password_template'] = 'sample{month}'
        with self.assertRaises(FileDropError) as caught: execute('move_extract', source, rule, datetime(2026, 2, 1))
        self.assertNotIn('sample02', str(caught.exception)); self.assertEqual(source.read_bytes(), original)
        self.assertEqual(list(self.output.iterdir()), [])
        result = execute('move_extract', source, rule, datetime(2026, 1, 1))
        self.assertEqual((Path(result['extracted'])/'フォルダー/資料.txt').read_bytes(), b'content')

    def test_path_traversal_absolute_paths_reserved_names_and_symlinks_are_rejected(self):
        for index, name in enumerate(('../escape', '/abs', 'C:/drive', 'folder\\escape', 'file:stream', 'NUL.txt', 'NUL .txt', 'COM¹.txt', 'a/../b', 'bad.')):
            source = self.zip(name=f'bad{index}.zip', rows={name: b'content'})
            with self.subTest(member=name), self.assertRaises(FileDropError): execute('move_extract', source, self.rule(1))
            self.assertTrue(source.exists()); self.assertEqual(list(self.output.iterdir()), [])
        source = self.inbox/'link.zip'
        with zipfile.ZipFile(source, 'w') as archive:
            info = zipfile.ZipInfo('link'); info.create_system = 3; info.external_attr = (stat.S_IFLNK | 0o777) << 16
            archive.writestr(info, '../outside')
        with self.assertRaises(FileDropError): execute('move_extract', source, self.rule(1))
        self.assertTrue(source.exists())

    def test_duplicate_member_names_and_expansion_limits_are_rejected_before_move(self):
        source = self.zip(rows={'A.txt': b'1', 'a.txt': b'2'})
        with self.assertRaises(FileDropError): execute('move_extract', source, self.rule(1))
        source.unlink(); source = self.zip()
        with patch('companion.file_drop.MAX_EXPANDED_BYTES', 3):
            with self.assertRaises(FileDropError): execute('move_extract', source, self.rule(1))
        self.assertTrue(source.exists()); self.assertEqual(list(self.output.iterdir()), [])

    def test_existing_extraction_folder_and_corrupt_crc_keep_original(self):
        source = self.zip(); final = self.output/source.stem; final.mkdir(); (final/'keep').write_text('keep')
        with self.assertRaises(FileDropError): execute('move_extract', source, self.rule(1))
        self.assertTrue(source.exists()); self.assertEqual((final/'keep').read_text(), 'keep')
        (final/'keep').unlink(); final.rmdir()
        source.write_bytes(source.read_bytes().replace(b'content', b'corrupt'))
        with self.assertRaises(FileDropError): execute('move_extract', source, self.rule(1))
        self.assertTrue(source.exists()); self.assertEqual(list(self.output.iterdir()), [])

    def test_unconfigured_destination_and_changed_extension_do_not_touch_source(self):
        source = self.zip(); rule = defaults()['rules'][1]
        with self.assertRaises(FileDropError): execute('move_extract', source, rule)
        with self.assertRaises(FileDropError): execute('move', source, self.rule(0))
        self.assertTrue(source.exists()); self.assertEqual(list(self.output.iterdir()), [])
