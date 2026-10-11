import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from settings import Settings, settings_path


class SettingsTests(unittest.TestCase):
    def test_settings_beside_application_not_current_directory(self):
        import settings
        self.assertEqual(settings_path(), Path(settings.__file__).resolve().parent / 'settings.json')

    def test_packaged_settings_beside_executable(self):
        with tempfile.TemporaryDirectory() as directory:
            executable = Path(directory) / 'portable/app.exe'
            with patch('settings.sys.frozen', True, create=True), patch('settings.sys.executable', str(executable)):
                self.assertEqual(settings_path(), executable.parent / 'settings.json')

    def test_independent_paths_survive_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            file = root / 'config/settings.json'
            settings = Settings(file)
            settings.save_path('folder_path', root / 'フォルダ操作')
            settings.save_path('book_path', root / '本の整理')
            settings.save_path('folder_path', root / '別のフォルダ')
            restarted = Settings(file)
            self.assertEqual(restarted.remembered('folder_path'), root / '別のフォルダ')
            self.assertEqual(restarted.remembered('book_path'), root / '本の整理')

    def test_missing_path_retained_and_dialog_uses_existing_parent(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = Settings(root / 'settings.json')
            missing = root / 'missing/nested'
            settings.save_path('folder_path', missing)
            restarted = Settings(settings.path)
            self.assertEqual(restarted.remembered('folder_path'), missing)
            self.assertEqual(restarted.initial_directory('folder_path'), str(root))

    def test_corrupt_and_wrong_type_settings_do_not_crash(self):
        with tempfile.TemporaryDirectory() as directory:
            file = Path(directory) / 'settings.json'
            for contents in ['bad json', '[]']:
                file.write_text(contents)
                settings = Settings(file)
                self.assertIsNotNone(settings.warning)
                self.assertIsNone(settings.remembered('folder_path'))
            file.write_text(json.dumps({'folder_path': 5, 'book_path': None}))
            self.assertIsNone(Settings(file).remembered('folder_path'))

    def test_failed_save_keeps_previous_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            settings = Settings(root / 'settings.json')
            settings.save_path('folder_path', root / 'old')
            with patch.object(Path, 'replace', side_effect=OSError('disk full')), self.assertRaises(OSError):
                settings.save_path('folder_path', root / 'new')
            self.assertEqual(Settings(settings.path).remembered('folder_path'), root / 'old')
            self.assertEqual(list(root.iterdir()), [settings.path])


if __name__ == '__main__':
    unittest.main()
