from pathlib import Path
import tempfile
import json
import unittest
from unittest.mock import patch
from images import plan_images, execute_images, plan_non_images, execute_image_cleanup


class ImageTests(unittest.TestCase):
    def test_cleanup_preserves_images_and_outside_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            book = self.make_book(root)
            (book / 'page.jpg').write_text('image')
            (book / 'notes.txt').write_text('notes')
            (book / 'nested').mkdir()
            (book / 'nested/data.zip').write_text('zip')
            (book / 'nested/keep.PNG').write_text('nested image')
            (book.parent / 'keep.txt').write_text('title metadata')
            images, others = plan_images(root), plan_non_images(root)
            self.assertEqual(len(others), 2)
            count, backup = execute_image_cleanup(root, images, others)
            self.assertEqual(count, 1)
            self.assertTrue((book / '001.jpg').exists())
            self.assertTrue((book / 'nested/keep.PNG').exists())
            self.assertTrue((book.parent / 'keep.txt').exists())
            self.assertFalse((book / 'notes.txt').exists())
            records = json.loads((backup / 'restore.json').read_text(encoding='utf-8'))
            target = next(Path(record['backup']) for record in records if Path(record['original']) == book / 'notes.txt')
            self.assertEqual(target.read_text(), 'notes')
            self.assertEqual(plan_non_images(root), [])

    def test_cleanup_failure_restores_non_images(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            book = self.make_book(root)
            (book / 'page.jpg').write_text('image')
            (book / 'notes.txt').write_text('notes')
            images, others = plan_images(root), plan_non_images(root)
            with patch('images.execute_images', side_effect=OSError('simulated failure')), self.assertRaises(RuntimeError):
                execute_image_cleanup(root, images, others)
            self.assertEqual((book / 'notes.txt').read_text(), 'notes')
            self.assertEqual((book / 'page.jpg').read_text(), 'image')

    def test_new_non_image_invalidates_preview(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            book = self.make_book(root)
            (book / 'page.jpg').write_text('image')
            images, others = plan_images(root), plan_non_images(root)
            (book / 'new.txt').write_text('new')
            with self.assertRaises(ValueError):
                execute_image_cleanup(root, images, others)
            self.assertTrue((book / 'new.txt').exists())

    def make_book(self, root, name='book'):
        book = root / 'title' / name
        book.mkdir(parents=True)
        return book

    def test_natural_order_and_each_book_starts_at_one(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            for name in ['book1', 'book2']:
                book = self.make_book(root, name)
                for image in ['page10.JPG', 'page2.JPG', 'page1.JPG']:
                    (book / image).write_text(image)
                (book / 'notes.txt').write_text('keep')
            items = plan_images(root)
            self.assertEqual(len(items), 6)
            self.assertEqual([i.source.name for i in items[:3]], ['page1.JPG', 'page2.JPG', 'page10.JPG'])
            self.assertEqual(execute_images(items), 6)
            for name in ['book1', 'book2']:
                book = root / 'title' / name
                self.assertEqual((book / '002.JPG').read_text(), 'page2.JPG')
                self.assertEqual((book / 'notes.txt').read_text(), 'keep')
            self.assertEqual(execute_images(plan_images(root)), 0)

    def test_existing_numbered_source_does_not_get_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            book = self.make_book(root)
            (book / '000.jpg').write_text('first')
            (book / '001.jpg').write_text('second')
            execute_images(plan_images(root))
            self.assertEqual((book / '001.jpg').read_text(), 'first')
            self.assertEqual((book / '002.jpg').read_text(), 'second')

    def test_collision_with_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            book = self.make_book(root)
            (book / 'page.jpg').write_text('data')
            (book / '001.jpg').mkdir()
            with self.assertRaises(ValueError):
                plan_images(root)

    def test_changed_image_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            book = self.make_book(root)
            (book / 'page.jpg').write_text('data')
            items = plan_images(root)
            (book / 'page.jpg').write_text('modified data')
            with self.assertRaises(ValueError):
                execute_images(items)

    def test_failure_restores_all_names_and_contents(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            book = self.make_book(root)
            for name in ['000.jpg', '001.jpg']:
                (book / name).write_text(name)
            items = plan_images(root)
            original = Path.rename
            def failing(path, destination):
                if Path(destination).name == '002.jpg':
                    raise OSError('simulated failure')
                return original(path, destination)
            with patch.object(Path, 'rename', failing), self.assertRaises(RuntimeError):
                execute_images(items)
            self.assertEqual(sorted(p.name for p in book.iterdir()), ['000.jpg', '001.jpg'])
            for name in ['000.jpg', '001.jpg']:
                self.assertEqual((book / name).read_text(), name)

    def test_depth_and_extension_are_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            book = self.make_book(root)
            (root / 'outside.jpg').write_text('ignore')
            (book.parent / 'cover.jpg').write_text('ignore')
            (book / 'page1.png').write_text('png')
            (book / 'page2.webp').write_text('webp')
            (book / 'nested').mkdir()
            (book / 'nested/deep.jpg').write_text('ignore')
            items = plan_images(root)
            self.assertEqual(len(items), 2)
            execute_images(items)
            self.assertTrue((book / '001.png').exists())
            self.assertTrue((book / '002.webp').exists())
            self.assertTrue((book / 'nested/deep.jpg').exists())


if __name__ == '__main__':
    unittest.main()
