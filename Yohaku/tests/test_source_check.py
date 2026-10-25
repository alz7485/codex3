"""Detect incomplete, mixed and unsafe source folders before building."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

from scripts.check_source import SourceCheckError, verify_source
from scripts.package_source import create_split_archives


class SourceCheckTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)/'source'
        self.root.mkdir()
        self.manifest = self.root/'MANIFEST_SHA256.json'

    def source(self, files):
        manifest = {}
        for name, data in files.items():
            path = self.root/name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            manifest[name] = hashlib.sha256(data).hexdigest()
        self.manifest.write_text(json.dumps(manifest), encoding='utf-8')
        return manifest

    def test_valid_binary_crlf_and_unicode_files_pass_and_local_settings_are_ignored(self):
        self.source({'main.py': b'pass\n', 'ONEDIR_COMMAND.txt': b'build\r\n',
                     'assets/日本語.bin': bytes(range(256))})
        (self.root/'settings.json').write_text('private local settings')
        self.assertEqual(verify_source(self.root), 3)

    def test_missing_or_changed_file_blocks_build_with_recovery_instructions(self):
        for mutation in ('missing', 'mixed-version'):
            with self.subTest(mutation=mutation):
                self.source({'main.py': b'current version'})
                if mutation == 'missing':
                    (self.root/'main.py').unlink()
                else:
                    (self.root/'main.py').write_bytes(b'older version')
                with self.assertRaises(SourceCheckError) as caught:
                    verify_source(self.root)
                self.assertIn('main.py', str(caught.exception))
                self.assertIn('ZIP 1/2と2/2', str(caught.exception))

    def test_partial_zip_fails_and_two_parts_together_pass(self):
        files = {'main.py': b'pass\n', 'README.md': b'merge both parts',
                 'ONEDIR_COMMAND.txt': b'build\r\n', 'SPLIT_README.txt': b'merge',
                 'assets/a.bin': bytes(range(256))*400, 'assets/b.bin': bytes(range(255, -1, -1))*400}
        self.source(files)
        parts = create_split_archives(self.root, Path(self.temp.name)/'zips')
        merged = Path(self.temp.name)/'merged'
        with zipfile.ZipFile(parts[0]) as archive:
            archive.extractall(merged)
        with self.assertRaises(SourceCheckError):
            verify_source(merged/'Yohaku')
        with zipfile.ZipFile(parts[1]) as archive:
            archive.extractall(merged)
        self.assertEqual(verify_source(merged/'Yohaku'), len(files))

    def test_invalid_manifests_and_outside_paths_are_rejected_without_reading_outside(self):
        zero = '0'*64
        documents = ['{broken', '[]', '{}', '{"main.py":"'+zero+'","main.py":"'+zero+'"}']
        for name in ('../outside', '/absolute', 'C:/outside', 'a\\b', 'a/./b', 'a//b', '.'):
            documents.append(json.dumps({name: zero}))
        documents.append(json.dumps({'main.py': 'invalid digest'}))
        for text in documents:
            with self.subTest(text=text[:70]):
                self.manifest.write_text(text)
                with self.assertRaises(SourceCheckError):
                    verify_source(self.root)

    def test_symlink_in_file_or_directory_is_rejected(self):
        outside = Path(self.temp.name)/'outside'
        outside.mkdir(); (outside/'data').write_bytes(b'outside')
        self.manifest.write_text(json.dumps({'linked/data': hashlib.sha256(b'outside').hexdigest()}))
        try:
            (self.root/'linked').symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest('Creating a directory symlink is unavailable in this environment.')
        with self.assertRaises(SourceCheckError):
            verify_source(self.root)

    def test_cli_failure_returns_nonzero_without_rewriting_source(self):
        script = Path(__file__).resolve().parents[1]/'scripts/check_source.py'
        self.source({'main.py': b'pass'})
        original = self.manifest.read_bytes()
        (self.root/'main.py').unlink()
        result = subprocess.run([sys.executable, str(script), '--project', str(self.root)],
                                capture_output=True, timeout=15)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(self.manifest.read_bytes(), original)


if __name__ == '__main__':
    unittest.main()
