"""Portable JSON settings stored beside the application."""
import json
import sys
from pathlib import Path
import tempfile
import os
import shutil
import uuid


def settings_path():
    base = Path(sys.executable).resolve().parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parent
    return base / 'settings.json'


class Settings:
    def __init__(self, path=None):
        self.path = Path(path) if path is not None else settings_path()
        self.data = {}
        self.warning = None
        self.invalid = False
        try:
            self.data = json.loads(self.path.read_text(encoding='utf-8'))
            if not isinstance(self.data, dict):
                raise ValueError('設定ファイルの形式が不正です')
        except FileNotFoundError:
            pass
        except (OSError, ValueError) as error:
            self.data = {}
            self.invalid = True
            self.warning = f'保存済みパスを読み込めませんでした: {error}'

    def remembered(self, key):
        value = self.data.get(key)
        return Path(value) if isinstance(value, str) and value else None

    def initial_directory(self, key):
        path = self.remembered(key)
        if path:
            for candidate in (path, *path.parents):
                try:
                    if candidate.is_dir():
                        return str(candidate)
                except OSError:
                    continue
        return None

    def save_path(self, key, path):
        self.save_value(key, str(Path(path).absolute()))

    def save_value(self, key, value):
        updated = {**self.data, key: value}
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if self.invalid and self.path.exists():
            # Do not silently erase the user's unreadable settings.
            shutil.copy2(self.path, self.path.with_name(f'settings.invalid-{uuid.uuid4().hex}.json'))
            self.invalid = False
        temporary = None
        try:
            with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=self.path.parent, delete=False) as file:
                temporary = Path(file.name)
                json.dump(updated, file, ensure_ascii=False, indent=2)
                file.flush()
                os.fsync(file.fileno())
            temporary.replace(self.path)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        self.data = updated
