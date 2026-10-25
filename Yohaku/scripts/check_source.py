"""Check the merged source folder before building; no optional dependencies."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys


class SourceCheckError(ValueError):
    pass


def _unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise SourceCheckError('マニフェストに重複したファイル名があります。')
        result[key] = value
    return result


def verify_source(project):
    """Verify only the declared source; user data and build outputs are ignored."""
    project = Path(project).resolve()
    manifest = project / 'MANIFEST_SHA256.json'
    try:
        if manifest.is_symlink() or manifest.stat().st_size > 1024 * 1024:
            raise SourceCheckError('マニフェストの形式が不正です。')
        document = json.loads(manifest.read_text(encoding='utf-8'), object_pairs_hook=_unique_object)
    except FileNotFoundError:
        raise SourceCheckError('MANIFEST_SHA256.json がありません。2つのZIPを同じ場所へ展開してください。') from None
    except (OSError, UnicodeError, json.JSONDecodeError, RecursionError):
        raise SourceCheckError('マニフェストを読み込めません。同じ版の2つのZIPから展開し直してください。') from None
    if not isinstance(document, dict) or not 1 <= len(document) <= 10000:
        raise SourceCheckError('マニフェストの形式が不正です。')
    missing, changed = [], []
    for name, expected in document.items():
        relative = PurePosixPath(name)
        if (relative.is_absolute() or relative.as_posix() != name or not relative.parts
                or any(part in ('.', '..') for part in relative.parts)
                or any(char in name for char in ('\\', ':', '\0'))
                or not isinstance(expected, str) or re.fullmatch(r'[0-9a-f]{64}', expected) is None):
            raise SourceCheckError('マニフェストに不正なパスまたはハッシュがあります。')
        path = project
        for part in relative.parts:
            path = path / part
            if path.is_symlink():
                raise SourceCheckError('ソースにリンクが含まれています。ZIPから展開し直してください。')
        if not path.is_file():
            missing.append(name)
            continue
        try:
            digest = hashlib.sha256()
            with path.open('rb') as source:
                for block in iter(lambda: source.read(1024 * 1024), b''):
                    digest.update(block)
        except OSError:
            raise SourceCheckError(f'読み取れないファイルがあります: {name}') from None
        if digest.hexdigest() != expected:
            changed.append(name)
    if missing or changed:
        details = '\n'.join([*(f'不足: {name}' for name in missing[:8]),
                             *(f'内容の不一致: {name}' for name in changed[:8])])
        raise SourceCheckError(f'ソースの確認に失敗しました（不足{len(missing)}件、不一致{len(changed)}件）。\n'
                               f'{details}\n同じ版のZIP 1/2と2/2を、空の同じ場所へ展開して統合してください。')
    return len(document)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--project', type=Path, default=Path(__file__).resolve().parents[1])
    args = parser.parse_args()
    try:
        count = verify_source(args.project)
    except SourceCheckError as error:
        print(str(error), file=sys.stderr)
        return 2
    print(f'ソース{count}ファイルの不足・不一致はありません。')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
