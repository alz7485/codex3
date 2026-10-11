import tempfile
import unittest
from pathlib import Path
from books import volume_name, discover_books
from core import execute_with_deletions
from images import plan_images, plan_non_images


class BookTests(unittest.TestCase):
    def test_generated_equivalent_volume_name_survives_second_run(self):
        for original in ['name_v05s', 'name_002', 'name_101s']:
            with self.subTest(original=original):
                name = volume_name('作品', original)
                self.assertEqual(volume_name('作品', name), name)

    def test_examples_and_rightmost_number(self):
        cases = {
            'ossan_wa_suro_raifu_no_v05s': 'タイトル 第05巻相当',
            'rpeggio_of_Blue_Steel_Kaiyo_Gijutsu_v02': 'タイトル 第02巻',
            'name_v05s_extra': 'タイトル 第05巻相当',
            'series2000_v2_suffix': 'タイトル 第02巻',
            'series_v02_patch12s_more': 'タイトル 第12巻相当',
            'v1': 'タイトル 第01巻',
            'v99': 'タイトル 第99巻',
            'v100': 'タイトル 第100巻',
            'v101s': 'タイトル 第101巻相当',
            'v0002': 'タイトル 第02巻',
            'v1000': 'タイトル 第1000巻',
            'no_digits': None,
            'v00': None,
        }
        for source, expected in cases.items():
            with self.subTest(source=source):
                self.assertEqual(volume_name('タイトル', source), expected)

    def test_rename_preserves_contents_and_works_with_image_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            title = root / '作品'
            book = title / 'name_v05s_more'
            book.mkdir(parents=True)
            (book / 'page1.jpg').write_text('image')
            (book / 'notes.txt').write_text('notes')
            books = discover_books(root)
            self.assertEqual(len(books), 1)
            execute_with_deletions(title, [(book.name, books[0].suggested)], False, False, set())
            renamed = title / '作品 第05巻相当'
            self.assertEqual((renamed / 'page1.jpg').read_text(), 'image')
            self.assertEqual(len(plan_images(root)), 1)
            self.assertEqual(len(plan_non_images(root)), 1)

    def test_backup_folders_excluded_from_all_discovery(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            backup = root / '作品/.folder-tool-trash/backup1'
            backup.mkdir(parents=True)
            (backup / 'old.jpg').write_text('image')
            (backup / 'restore.json').write_text('metadata')
            self.assertEqual(discover_books(root), [])
            self.assertEqual(plan_images(root), [])
            self.assertEqual(plan_non_images(root), [])


if __name__ == '__main__':
    unittest.main()
