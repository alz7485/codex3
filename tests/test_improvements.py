from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from history import History
from work import WorkToken, working, Cancelled
from core import execute_with_deletions, deletion_mask, name_from_mask
from images import plan_images, plan_non_images, execute_image_cleanup
from file_cleanup import search_files, delete_files
from comparison import summarize


class ImprovementTests(unittest.TestCase):
    def test_malformed_history_is_visible_but_cannot_change_files(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            history = History(root / 'history'); history.directory.mkdir()
            (root / 'data').write_text('keep')
            malformed = [
                {'status': 'completed', 'moves': None, 'time': None},
                {'status': 'completed', 'label': 'bad', 'time': '', 'moves': [], 'created': [], 'final': None},
                {'status': 'completed', 'label': 'bad', 'time': '', 'moves': [], 'created': [], 'final': [{'path': str(root / 'data'), 'original': str(root / 'old'), 'state': [['.', 1]]}]},
            ]
            for i, value in enumerate(malformed):
                path = history.directory / f'{i}.json'
                path.write_text(json.dumps(value), encoding='utf-8')
                with self.assertRaises(ValueError):
                    history.undo(path)
            self.assertEqual(len(history.entries()), 3)
            self.assertTrue(all(data['status'] == 'unreadable' for _, data in history.entries()))
            self.assertEqual((root / 'data').read_text(), 'keep')

    def test_legacy_history_missing_final_state_cannot_replay(self):
        import json
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / 'data'; root.mkdir()
            (root / 'abc').mkdir()
            history = History(Path(directory).resolve() / 'history')
            history.run('case', lambda: execute_with_deletions(root, [('abc', 'ABC')], False, False, set()))
            path, data = history.entries()[0]
            data['final'] = []
            path.write_text(json.dumps(data), encoding='utf-8')
            with self.assertRaises(ValueError):
                history.undo(path)
            self.assertEqual([p.name for p in root.iterdir()], ['ABC'])

    def test_related_operations_can_be_undone_newest_first(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / 'data'
            original = root / 'Title/book_v02'; original.mkdir(parents=True)
            (original / 'page2.jpg').write_text('keep')
            history = History(Path(directory).resolve() / 'history')
            history.run('巻数', lambda: execute_with_deletions(root / 'Title', [('book_v02', 'Title 第02巻')], False, False, set()))
            first = history.entries()[0][0]
            history.run('画像', lambda: execute_image_cleanup(root, plan_images(root), plan_non_images(root)))
            second = history.entries()[0][0]
            history.undo(second)
            history.undo(first)
            self.assertEqual((original / 'page2.jpg').read_text(), 'keep')

    def test_case_only_history_checks_contents_before_undo(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / 'data'; root.mkdir()
            (root / 'abc').mkdir(); (root / 'abc/page').write_text('before')
            history = History(Path(directory).resolve() / 'history')
            history.run('case', lambda: execute_with_deletions(root, [('abc', 'ABC')], False, False, set()))
            path, data = history.entries()[0]
            self.assertEqual(len(data['final']), 1)
            (root / 'ABC/page').write_text('edited')
            with self.assertRaises(ValueError):
                history.undo(path)
            self.assertEqual((root / 'ABC/page').read_text(), 'edited')

    def test_undo_still_rejects_added_empty_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / 'data'; root.mkdir()
            (root / 'a').mkdir()
            history = History(Path(directory).resolve() / 'history')
            history.run('rename', lambda: execute_with_deletions(root, [('a', 'b')], False, False, set()))
            (root / 'b/new').mkdir()
            with self.assertRaises(ValueError):
                history.undo(history.entries()[0][0])
            self.assertTrue((root / 'b/new').is_dir())

    def test_book_scan_can_cancel_between_books(self):
        from books import discover_books, volume_name
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for name in ['a_v01', 'b_v02']:
                (root / 'Title' / name).mkdir(parents=True)
            token = WorkToken()
            def first_then_cancel(*args):
                result = volume_name(*args)
                token.cancelled.set()
                return result
            with working(token), patch('books.volume_name', side_effect=first_then_cancel), self.assertRaises(Cancelled):
                discover_books(root)

    def test_folder_operation_can_be_undone_after_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / 'data'; root.mkdir()
            original = root / '作品(A)'; original.mkdir()
            (original / 'page.jpg').write_text('keep')
            history = History(Path(directory).resolve() / 'history')
            history.run('整理', lambda: execute_with_deletions(root, [('作品(A)', '作品')], True, True, set()))
            self.assertTrue((root / 'A/作品/page.jpg').exists())
            restarted = History(history.directory)
            restarted.undo(restarted.entries()[0][0])
            self.assertTrue((original / 'page.jpg').exists())
            self.assertFalse((root / 'A').exists())
            self.assertEqual(restarted.entries()[0][1]['status'], 'undone')

    def test_file_deletion_undo(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / 'data'; root.mkdir()
            (root / 'a.txt').write_text('keep')
            history = History(Path(directory).resolve() / 'history')
            history.run('削除', lambda: delete_files(root, search_files(root, '.txt')))
            self.assertFalse((root / 'a.txt').exists())
            history.undo(history.entries()[0][0])
            self.assertEqual((root / 'a.txt').read_text(), 'keep')

    def test_image_rename_and_cleanup_undo(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / 'data'
            book = root / 'title/book'; book.mkdir(parents=True)
            for name in ['000.jpg', '001.jpg', 'note.txt']:
                (book / name).write_text(name)
            history = History(Path(directory).resolve() / 'history')
            history.run('画像整理', lambda: execute_image_cleanup(root, plan_images(root), plan_non_images(root)))
            history.undo(history.entries()[0][0])
            self.assertEqual(sorted(p.name for p in book.iterdir()), ['000.jpg', '001.jpg', 'note.txt'])
            for name in ['000.jpg', '001.jpg', 'note.txt']:
                self.assertEqual((book / name).read_text(), name)

    def test_undo_refuses_modified_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / 'data'; root.mkdir()
            (root / 'a').mkdir(); (root / 'a/file').write_text('old')
            history = History(Path(directory).resolve() / 'history')
            history.run('rename', lambda: execute_with_deletions(root, [('a', 'b')], False, False, set()))
            (root / 'b/file').write_text('modified')
            with self.assertRaises(ValueError):
                history.undo(history.entries()[0][0])
            self.assertEqual((root / 'b/file').read_text(), 'modified')

    def test_cancel_restores_completed_folder_moves(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / 'data'; root.mkdir()
            for name in ['a', 'b']:
                (root / name).mkdir()
            token = WorkToken()
            history = History(Path(directory).resolve() / 'history')
            original = Path.rename
            def cancel_after_first(path, target):
                result = original(path, target)
                if path == root / 'a':
                    token.cancelled.set()
                return result
            with working(token), patch.object(Path, 'rename', cancel_after_first), self.assertRaises(Cancelled):
                history.run('rename', lambda: execute_with_deletions(root, [('a', 'new-a'), ('b', 'new-b')], False, False, set()))
            self.assertTrue((root / 'a').exists())
            self.assertTrue((root / 'b').exists())
            self.assertFalse((root / 'new-a').exists())
            self.assertEqual(history.entries()[0][1]['status'], 'rolled_back')

    def test_undo_collision_preserves_both_sides(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / 'data'; root.mkdir()
            (root / 'a').mkdir()
            history = History(Path(directory).resolve() / 'history')
            history.run('rename', lambda: execute_with_deletions(root, [('a', 'b')], False, False, set()))
            (root / 'a').mkdir()
            (root / 'a/new').write_text('keep')
            with self.assertRaises(RuntimeError):
                history.undo(history.entries()[0][0])
            self.assertTrue((root / 'b').is_dir())
            self.assertEqual((root / 'a/new').read_text(), 'keep')

    def test_leading_and_trailing_square_rules(self):
        name = '[先頭]作品[中間](作者)[末尾]'
        self.assertEqual(name_from_mask(name, deletion_mask(name, False, True, square_scope='leading')), '作品[中間](作者)[末尾]')
        self.assertEqual(name_from_mask(name, deletion_mask(name, False, True, square_scope='trailing')), '[先頭]作品[中間](作者)')

    def test_comparison_counts_images_and_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / 'sub').mkdir()
            (root / 'a.JPG').write_bytes(b'123')
            (root / 'sub/b.png').write_bytes(b'12')
            (root / 'note.txt').write_bytes(b'1')
            result = summarize(root)
            self.assertEqual((result['bytes'], result['files'], result['images']), (6, 3, 2))

    def test_cancel_search_before_any_mutation(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / 'a.txt').write_text('keep')
            token = WorkToken(); token.cancelled.set()
            with working(token), self.assertRaises(Cancelled):
                search_files(root, '.txt')
            self.assertTrue((root / 'a.txt').exists())


if __name__ == '__main__':
    unittest.main()
