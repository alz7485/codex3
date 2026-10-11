from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from file_cleanup import matches, search_files, delete_files, Candidate, signature
from settings import Settings


class FileCleanupTests(unittest.TestCase):
    def test_or_search_and_extension_matching(self):
        self.assertTrue(matches('広告.jpg', '広告 .txt'))
        self.assertTrue(matches('notes.TXT', '広告 .txt'))
        self.assertTrue(matches('notes.TXT', '*.txt'))
        self.assertFalse(matches('notes.txt.bak', '.txt'))
        self.assertFalse(matches('other.jpg', '広告 .txt'))
        self.assertTrue(matches('SAMPLE.jpg', 'sample'))
        self.assertFalse(matches('anything.txt', '   '))

    def test_recursive_search_and_individual_exclusion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / 'nested/deep').mkdir(parents=True)
            for relative in ['a.txt', 'nested/b.txt', 'nested/deep/広告.jpg', 'keep.png']:
                (root / relative).write_text(relative)
            candidates = search_files(root, '広告 .txt')
            self.assertEqual(len(candidates), 3)
            excluded = root / 'nested/b.txt'
            chosen = [c for c in candidates if c.source != excluded]
            backup = delete_files(root, chosen)
            self.assertTrue(excluded.exists())
            self.assertTrue((root / 'keep.png').exists())
            self.assertFalse((root / 'a.txt').exists())
            self.assertEqual((backup / 'data/nested/deep/広告.jpg').read_text(), 'nested/deep/広告.jpg')
            self.assertTrue((backup / 'restore.json').exists())
            self.assertEqual([c.source for c in search_files(root, '広告 .txt')], [excluded])

    def test_empty_query_and_modified_candidate_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            with self.assertRaises(ValueError):
                search_files(root, '  ')
            file = root / 'a.txt'
            file.write_text('old')
            candidates = search_files(root, '.txt')
            file.write_text('modified')
            with self.assertRaises(ValueError):
                delete_files(root, candidates)
            self.assertEqual(file.read_text(), 'modified')

    def test_outside_scope_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve() / 'root'
            root.mkdir()
            outside = Path(directory).resolve() / 'outside.txt'
            outside.write_text('keep')
            with self.assertRaises(ValueError):
                delete_files(root, [Candidate(outside, signature(outside))])
            self.assertTrue(outside.exists())

    def test_failure_rolls_back(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for name in ['a.txt', 'b.txt']:
                (root / name).write_text(name)
            candidates = search_files(root, '.txt')
            original = Path.rename
            def fail(path, target):
                if path == root / 'b.txt':
                    raise OSError('simulated failure')
                return original(path, target)
            with patch.object(Path, 'rename', fail), self.assertRaises(RuntimeError):
                delete_files(root, candidates)
            self.assertEqual((root / 'a.txt').read_text(), 'a.txt')
            self.assertEqual((root / 'b.txt').read_text(), 'b.txt')

    def test_query_remembered_separately_from_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            settings = Settings(root / 'settings.json')
            settings.save_path('folder_path', root)
            settings.save_value('delete_query', '広告 .txt *.url')
            restarted = Settings(settings.path)
            self.assertEqual(restarted.data['delete_query'], '広告 .txt *.url')
            self.assertEqual(restarted.remembered('folder_path'), root)


if __name__ == '__main__':
    unittest.main()
