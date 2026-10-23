import hashlib
import json
from pathlib import Path
import tempfile
import unittest
import zipfile

from scripts.build_onedir import required_files
from scripts.package_source import create_archive


class DistributionTests(unittest.TestCase):
    def test_onedir_inputs_include_all_characters_and_windows_resources(self):
        paths = required_files()
        self.assertTrue(all(path.is_file() for path in paths))
        self.assertEqual(len([p for p in paths if p.name.endswith("_motion.png")]), 4)
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
