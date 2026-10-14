"""Real Windows filename limits, sharing locks, rollback and diagnostics."""
import ctypes
import json
import os
from pathlib import Path
import shutil
import tempfile
import threading
import unittest
from unittest.mock import patch

from core import execute_with_deletions, validate_name
from history import History
from images import execute_image_cleanup, plan_images, plan_non_images
from safety import move_no_replace


@unittest.skipUnless(os.name == 'nt', 'Windows filesystem required')
class WindowsMoveTests(unittest.TestCase):
    def locked(self, path):
        library = ctypes.WinDLL('kernel32', use_last_error=True)
        library.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
        library.CreateFileW.restype = ctypes.c_void_p
        library.CloseHandle.argtypes = [ctypes.c_void_p]
        library.CloseHandle.restype = ctypes.c_int
        # Permit reads/writes but deliberately refuse FILE_SHARE_DELETE.
        handle = library.CreateFileW(str(path), 0x80000000, 3, None, 3, 0, None)
        if handle == ctypes.c_void_p(-1).value:
            raise ctypes.WinError(ctypes.get_last_error())
        return lambda: library.CloseHandle(handle)

    def test_long_original_folder_quarantine_and_undo(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path('\\\\?\\' + str(Path(directory).resolve())) / 'data'
            root.mkdir()
            try:
                name = 'a' * 249 + '_v02'  # 253 UTF-16 units, valid on NTFS.
                original = root / name; original.mkdir()
                (original / 'page.jpg').write_text('keep')
                history = History(root.parent / 'history')
                _, _, backup = history.run('duplicate', lambda: execute_with_deletions(root, [], False, False, {original}))
                records = json.loads((backup / 'restore.json').read_text(encoding='utf-8'))
                target = Path(records[0]['backup'])
                self.assertEqual(target.name, '0000')
                self.assertEqual((target / 'page.jpg').read_text(), 'keep')
                history.undo(history.entries()[0][0])
                self.assertEqual((original / 'page.jpg').read_text(), 'keep')
            finally:
                shutil.rmtree(root.parent)

    def test_utf16_name_limit_is_rejected_before_deletion(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            (root / 'a').mkdir(); (root / 'b').mkdir()
            with self.assertRaises(ValueError):
                validate_name('\U0001f600' * 128)
            with self.assertRaises(RuntimeError):
                execute_with_deletions(root, [('a', 'x' * 256)], False, False, {root / 'b'})
            self.assertTrue((root / 'a').is_dir())
            self.assertTrue((root / 'b').is_dir())
            self.assertFalse((root / '.folder-tool-trash').exists())

    def test_nonimage_quarantine_shortens_long_book_paths_and_undo(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path('\\\\?\\' + str(Path(directory).resolve())) / 'data'
            book = root / 'Title' / ('book_' + 'a' * 180)
            book.mkdir(parents=True)
            try:
                note = book / ('n' * 100 + '.txt'); note.write_text('keep')
                (book / 'page.jpg').write_text('image')
                history = History(root.parent / 'history')
                _, backup = history.run('cleanup', lambda: execute_image_cleanup(root, plan_images(root), plan_non_images(root)))
                records = json.loads((backup / 'restore.json').read_text(encoding='utf-8'))
                target = Path(records[0]['backup'])
                self.assertEqual(target.parent, backup / 'data')
                self.assertEqual(target.name, '000000')
                self.assertEqual(target.read_text(), 'keep')
                history.undo(history.entries()[0][0])
                self.assertEqual(note.read_text(), 'keep')
                self.assertEqual((book / 'page.jpg').read_text(), 'image')
            finally:
                shutil.rmtree(root.parent)

    def test_transient_sharing_lock_is_retried(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / 'Thumbs.db'; source.write_text('keep')
            close = self.locked(source)
            released = threading.Event()
            def release():
                close(); released.set()
            timer = threading.Timer(0.15, release); timer.start()
            try:
                move_no_replace(source, root / 'moved.db')
            finally:
                timer.join()
                if not released.is_set():
                    close()
            self.assertEqual((root / 'moved.db').read_text(), 'keep')

    def test_persistent_sharing_lock_restores_prior_deletions(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            book = root / 'Title/book_v02'; book.mkdir(parents=True)
            for name in ['page.jpg', 'a-note.txt', 'z-locked.txt']:
                (book / name).write_text(name)
            images, others = plan_images(root), plan_non_images(root)
            close = self.locked(book / 'z-locked.txt')
            history = History(root / 'history')
            try:
                with self.assertRaises(RuntimeError) as caught:
                    history.run('cleanup', lambda: execute_image_cleanup(root, images, others))
                self.assertIn('使用中', str(caught.exception))
                self.assertIn('z-locked.txt', str(caught.exception))
                for name in ['page.jpg', 'a-note.txt', 'z-locked.txt']:
                    self.assertEqual((book / name).read_text(), name)
                self.assertEqual(history.entries()[0][1]['status'], 'rolled_back')
            finally:
                close()
            history.run('cleanup', lambda: execute_image_cleanup(root, plan_images(root), plan_non_images(root)))
            self.assertTrue((book / '001.jpg').is_file())
            self.assertFalse((book / 'z-locked.txt').exists())
            history.undo(history.entries()[0][0])
            self.assertEqual((book / 'z-locked.txt').read_text(), 'z-locked.txt')

    def test_permission_denial_does_not_retry_or_remove_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            source = root / 'note.txt'; source.write_text('keep')
            error = PermissionError(13, 'denied', str(source), 5)
            with patch.object(Path, 'rename', side_effect=error) as rename, self.assertRaises(PermissionError) as caught:
                move_no_replace(source, root / 'other.txt')
            self.assertEqual(rename.call_count, 1)
            self.assertIn('アクセスが拒否', str(caught.exception))
            self.assertEqual(source.read_text(), 'keep')
