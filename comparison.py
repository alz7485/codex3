"""Folder comparison details for duplicate decisions."""
import os
from pathlib import Path
from images import EXTENSIONS
from safety import is_link
from work import checkpoint


def summarize(path):
    path = Path(path)
    result = {'bytes': 0, 'files': 0, 'images': 0, 'names': set()}
    def fail(error):
        raise error
    for directory, dirs, files in os.walk(path, followlinks=False, onerror=fail):
        checkpoint(f'フォルダを比較: {Path(directory).name}')
        dirs[:] = [name for name in dirs if name.casefold() != '.folder-tool-trash' and not is_link(Path(directory) / name)]
        for name in files:
            checkpoint(f'フォルダを比較: {name}')
            file = Path(directory) / name
            if is_link(file) or not file.is_file():
                continue
            result['bytes'] += file.stat().st_size
            result['files'] += 1
            result['images'] += file.suffix.casefold() in EXTENSIONS
            result['names'].add(str(file.relative_to(path)))
    return result
