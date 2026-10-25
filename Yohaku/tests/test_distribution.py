import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts.build_onedir import required_files
from scripts.package_source import create_archive, create_split_archives


class DistributionTests(unittest.TestCase):
    def test_two_standalone_zips_restore_all_files_and_exclude_runtime_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'source'
            root.mkdir()
            entries = {'main.py': b'print(1)', 'README.md': b'readme', 'ONEDIR_COMMAND.txt': b'build',
                       'SPLIT_README.txt': b'extract both', 'companion/assets/a.png': bytes(range(256)) * 700,
                       'companion/assets/b.png': bytes(range(255, -1, -1)) * 600,
                       'settings.json': b'PRIVATE', 'files.sqlite3': b'PRIVATE'}
            for name, data in entries.items():
                path = root / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            parts = create_split_archives(root, Path(tmp) / 'output')
            self.assertEqual(len(parts), 2)
            combined = {}
            names = []
            for part in parts:
                self.assertEqual(part.with_suffix('.zip.sha256').read_text().split()[0], hashlib.sha256(part.read_bytes()).hexdigest())
                with zipfile.ZipFile(part) as z:
                    self.assertIsNone(z.testzip())
                    self.assertIn('Yohaku/ONEDIR_COMMAND.txt', z.namelist())
                    self.assertNotIn('Yohaku/settings.json', z.namelist())
                    names.append(set(z.namelist()))
                    combined.update({name: z.read(name) for name in z.namelist()})
            self.assertNotEqual(names[0], names[1])
            manifest = json.loads(combined['Yohaku/MANIFEST_SHA256.json'])
            self.assertEqual(set(manifest), set(entries) - {'settings.json', 'files.sqlite3'})
            for name, digest in manifest.items():
                self.assertEqual(hashlib.sha256(combined['Yohaku/' + name]).hexdigest(), digest)
    def test_onedir_inputs_include_all_characters_and_windows_resources(self):
        paths = required_files()
        self.assertTrue(all(path.is_file() for path in paths))
        self.assertEqual(len([p for p in paths if p.name.endswith("_motion.png")]), 4)
        self.assertEqual(len([p for p in paths if p.name.endswith("_atlas.png")]), 3)
        self.assertIn('atlas_layout.json', [p.name for p in paths])
        self.assertIn("yohaku.ico", [p.name for p in paths])
        self.assertIn("Yohaku.spec", [p.name for p in paths])

    def test_source_zip_keeps_build_code_and_excludes_runtime_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / "source"
            root.mkdir()
            entries = {
                "main.py": "print('ok')", "Yohaku.spec": "# build", "scripts/build_onedir.py": "# build helper",
                ".github/workflows/yohaku-windows.yml": "name: build", "companion/assets/app/yohaku.ico": "asset",
                ".venv/secret.txt": "exclude", "settings.json": "exclude", "history.json": "exclude",
                "files.sqlite3": "exclude", "files.sqlite3-wal": "exclude", ".env.local": "exclude",
                "usage.json": "exclude", "usage.tmp": "exclude", "dialogue.json": "exclude", "dialogue.json.bak": "exclude", "dialogue.json.tmp": "exclude", "Yohaku-conversation.json": "exclude",
                "reminders.json": "exclude", "reminders.json.bak": "exclude", "reminders.json.tmp": "exclude",
                ".aws/config": "exclude", "release/old.zip": "exclude", "debug.log": "exclude",
            }
            for relative, content in entries.items():
                path = root / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_text(content)
            output = Path(tmp) / "source.zip"
            digest = create_archive(root, output)
            self.assertEqual(digest, hashlib.sha256(output.read_bytes()).hexdigest())
            with zipfile.ZipFile(output) as archive:
                self.assertIsNone(archive.testzip())
                manifest = json.loads(archive.read("Yohaku/MANIFEST_SHA256.json"))
                self.assertEqual(set(manifest), {"main.py", "Yohaku.spec", "scripts/build_onedir.py", ".github/workflows/yohaku-windows.yml", "companion/assets/app/yohaku.ico"})
                for relative, expected in manifest.items():
                    self.assertEqual(hashlib.sha256(archive.read("Yohaku/" + relative)).hexdigest(), expected)


if __name__ == "__main__":
    unittest.main()
