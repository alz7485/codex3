import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch
from core import plan, execute, execute_with_deletions, validate_name
from file_cleanup import search_files, delete_files
from images import plan_images, execute_image_cleanup, plan_non_images, natural_key
from settings import Settings
from safety import is_link, move_no_replace


class AuditTests(unittest.TestCase):
    def test_recovery_symlink_never_moves_data_outside(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'root'
            outside = Path(directory) / 'outside'
            root.mkdir(); outside.mkdir()
            (root / '.folder-tool-trash').symlink_to(outside, target_is_directory=True)
            file = root / 'a.txt'
            file.write_text('keep')
            with self.assertRaises(RuntimeError):
                delete_files(root, search_files(root, '.txt'))
            self.assertEqual(file.read_text(), 'keep')
            self.assertEqual(list(outside.iterdir()), [])

    def test_folder_recovery_info_written_before_move(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ['a', 'b']:
                (root / name).mkdir()
            with patch('core.write_recovery', side_effect=OSError('disk full')), self.assertRaises(RuntimeError):
                execute_with_deletions(root, [('a', 'b')], False, False, {root / 'b'})
            self.assertTrue((root / 'a').is_dir())
            self.assertTrue((root / 'b').is_dir())

    def test_restore_json_file_can_itself_be_quarantined(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'restore.json').write_text('original data')
            backup = delete_files(root, search_files(root, '.json'))
            self.assertEqual((backup / 'data/restore.json').read_text(), 'original data')
            metadata = json.loads((backup / 'restore.json').read_text())
            self.assertEqual(metadata[0]['original'], str(root / 'restore.json'))

    def test_reserved_recovery_and_windows_names_rejected(self):
        for name in ['.folder-tool-trash', '.Folder-Tool-Trash', 'CON .txt', 'COM¹', 'LPT².txt', 'CONIN$']:
            with self.subTest(name=name), self.assertRaises(ValueError):
                validate_name(name)

    def test_case_only_folder_rename_and_rollback(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'abc').mkdir()
            (root / 'def').mkdir()
            ops, groups = plan(root, [('abc', 'ABC'), ('def', 'DEF')])
            original = Path.rename
            def fail(path, target):
                if Path(target).name == 'DEF':
                    raise OSError('simulated failure')
                return original(path, target)
            with patch.object(Path, 'rename', fail), self.assertRaises(RuntimeError):
                execute(ops, groups)
            self.assertEqual(sorted(p.name for p in root.iterdir()), ['abc', 'def'])
            execute(*plan(root, [('abc', 'ABC')]))
            self.assertEqual(sorted(p.name for p in root.iterdir()), ['ABC', 'def'])

    def test_virtual_plan_and_source_traversal(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / 'a').mkdir(); (root / 'b').mkdir()
            self.assertEqual(len(plan(root, [('a', 'b')], deleted={root / 'b'})[0]), 1)
            with self.assertRaises(ValueError):
                plan(root, [('../outside', 'safe')])
            with self.assertRaises(ValueError):
                plan(root, [('a', 'new')], group_names={'a': '.folder-tool-trash'}, move_groups=True)

    def test_destination_dangling_link_and_case_collision(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = root / 'source.txt'
            file.write_text('keep')
            (root / 'dest.txt').symlink_to(root / 'missing')
            with self.assertRaises(ValueError):
                move_no_replace(file, root / 'dest.txt')
            (root / 'UPPER.txt').write_text('other')
            with self.assertRaises(ValueError):
                move_no_replace(file, root / 'upper.txt')
            self.assertEqual(file.read_text(), 'keep')

    def test_windows_junction_attribute_detection(self):
        class Info:
            st_mode = 0o40755
            st_file_attributes = 0x400
        with patch.object(Path, 'lstat', return_value=Info()):
            self.assertTrue(is_link(Path('junction')))

    def test_natural_sort_non_decimal_unicode_does_not_crash(self):
        files = [Path('page².jpg'), Path('page10.jpg'), Path('page2.jpg')]
        ordered = sorted(files, key=natural_key)
        self.assertLess(ordered.index(Path('page2.jpg')), ordered.index(Path('page10.jpg')))

    def test_nested_recovery_data_excluded_from_image_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            book = root / 'title/book'
            backup = book / '.Folder-Tool-Trash/backup'
            backup.mkdir(parents=True)
            (backup / 'old.txt').write_text('keep')
            self.assertEqual(plan_non_images(root), [])

    def test_image_cleanup_symlink_recovery_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / 'root'
            book = root / 'title/book'
            book.mkdir(parents=True)
            outside = Path(directory) / 'outside'
            outside.mkdir()
            (root / '.folder-tool-trash').symlink_to(outside, target_is_directory=True)
            (book / 'a.jpg').write_text('image')
            (book / 'a.txt').write_text('keep')
            with self.assertRaises(RuntimeError):
                execute_image_cleanup(root, plan_images(root), plan_non_images(root))
            self.assertTrue((book / 'a.jpg').exists())
            self.assertTrue((book / 'a.txt').exists())
            self.assertEqual(list(outside.iterdir()), [])

    def test_corrupt_settings_preserved_when_saving(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = root / 'settings.json'
            file.write_text('corrupt original')
            Settings(file).save_value('delete_query', '.txt')
            backups = list(root.glob('settings.invalid-*.json'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(backups[0].read_text(), 'corrupt original')
            self.assertEqual(Settings(file).data['delete_query'], '.txt')


if __name__ == '__main__':
    unittest.main()
