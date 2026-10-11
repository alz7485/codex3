"""Durable operation history and conflict-checked reverse replay."""
import json
import os
from pathlib import Path
from datetime import datetime, timezone
import tempfile
import uuid
import stat
from safety import is_link, move_no_replace, destination_exists
from work import current, checkpoint, Cancelled


def atomic_json(path, value):
    temporary = None
    try:
        with tempfile.NamedTemporaryFile('w', dir=path.parent, encoding='utf-8', delete=False) as file:
            temporary = Path(file.name)
            json.dump(value, file, ensure_ascii=False, indent=2)
            file.flush(); os.fsync(file.fileno())
        temporary.replace(path)
    finally:
        if temporary is not None:
            temporary.unlink(missing_ok=True)


def fingerprint(path):
    """Detect replacement or edits before undo, including directory contents."""
    path = Path(path)
    result = []
    def entry(file):
        checkpoint(f'復元用の状態確認: {file.name}')
        info = file.lstat()
        return [str(file.relative_to(path)) if file != path else '.', info.st_mode, info.st_size, info.st_mtime_ns, info.st_ino]
    if is_link(path) or not path.exists():
        raise ValueError(f'履歴の対象が存在しないかリンクです: {path}')
    result.append(entry(path))
    if path.is_dir():
        def fail(error):
            raise error
        for directory, dirs, files in os.walk(path, followlinks=False, onerror=fail):
            dirs.sort(); files.sort()
            for name in dirs + files:
                result.append(entry(Path(directory) / name))
            dirs[:] = [name for name in dirs if not is_link(Path(directory) / name)]
    return result


def states_match(actual, expected):
    # Directory size/mtime also change during a later operation and its undo.
    # Names, type, identity and every descendant are still compared; file size
    # and mtime remain mandatory. Normalize both sides for older histories too.
    def normalize(state):
        result = []
        for item in state:
            record = list(item)
            if stat.S_ISDIR(record[1]):
                record[2:4] = [0, 0]
            result.append(record)
        return result
    return normalize(actual) == normalize(expected)


def validate_record(data):
    """Reject malformed JSON before display or any reverse replay."""
    if not isinstance(data, dict):
        raise ValueError('履歴データの形式が不正です')
    for key in ('label', 'time', 'status'):
        if not isinstance(data.get(key), str):
            raise ValueError('履歴データの形式が不正です')
    for key in ('moves', 'created', 'final'):
        if not isinstance(data.get(key), list):
            raise ValueError('履歴データの形式が不正です')
    def valid_path(value):
        return isinstance(value, str) and bool(value)
    if any(not isinstance(move, list) or len(move) != 2 or not all(valid_path(p) for p in move) for move in data['moves']):
        raise ValueError('履歴の移動記録が不正です')
    if not all(valid_path(p) for p in data['created']):
        raise ValueError('履歴の作成記録が不正です')
    for item in data['final']:
        if not isinstance(item, dict) or not valid_path(item.get('path')) or not valid_path(item.get('original')) or not isinstance(item.get('state'), list) or not item['state']:
            raise ValueError('履歴の状態記録が不正です')
        for record in item['state']:
            if not isinstance(record, list) or len(record) != 5 or not isinstance(record[0], str) or not all(isinstance(value, int) for value in record[1:]):
                raise ValueError('履歴の状態記録が不正です')
    return data


class Journal:
    def __init__(self, path, label):
        self.path = path
        self.data = {'id': path.stem, 'label': label, 'time': datetime.now(timezone.utc).isoformat(), 'status': 'running', 'moves': [], 'created': [], 'final': []}
        self.owners = {}
        self.move_origins = []
        self.save()

    def save(self):
        atomic_json(self.path, self.data)

    def move(self, source, destination, rename):
        source, destination = Path(source), Path(destination)
        # Persist intent before altering the filesystem.
        self.data['pending'] = [str(source), str(destination)]
        self.save()
        origin = next((owner for owner, location in self.owners.items() if location == source), source)
        rename()
        self.data['moves'].append([str(source), str(destination)])
        self.move_origins.append(origin)
        self.data.pop('pending', None)
        found = False
        for origin, location in list(self.owners.items()):
            if location == source:
                self.owners[origin] = destination
                found = True
            elif source in location.parents:
                self.owners[origin] = destination / location.relative_to(source)
        if not found:
            self.owners[source] = destination
        self.save()

    def created(self, path):
        self.data['created'].append(str(path))
        self.save()

    def finish(self, status):
        self.data['final'] = [{'original': str(origin), 'path': str(location), 'state': fingerprint(location)} for origin, location in self.owners.items() if str(origin) != str(location)]
        self.data['status'] = status
        self.data.pop('pending', None)
        self.save()


class History:
    def __init__(self, directory):
        self.directory = Path(directory)

    def entries(self):
        if not self.directory.exists():
            return []
        if is_link(self.directory):
            raise ValueError('履歴フォルダがリンクです')
        result = []
        for file in self.directory.glob('*.json'):
            if is_link(file):
                continue
            try:
                value = validate_record(json.loads(file.read_text(encoding='utf-8')))
                result.append((file, value))
            except (ValueError, OSError):
                result.append((file, {'label': file.name, 'time': '', 'status': 'unreadable', 'moves': []}))
        return sorted(result, key=lambda entry: entry[1].get('time', ''), reverse=True)

    def run(self, label, function):
        if is_link(self.directory):
            raise ValueError('履歴フォルダがリンクです')
        self.directory.mkdir(parents=True, exist_ok=True)
        journal = Journal(self.directory / f'{uuid.uuid4().hex}.json', label)
        token = current.get()
        if token is None:
            from work import WorkToken, working
            with working(WorkToken()):
                return self._run(journal, function)
        return self._run(journal, function)

    def _run(self, journal, function):
        token = current.get()
        token.journal = journal
        try:
            result = function()
            checkpoint('履歴の保存中')
            journal.finish('completed')
            return result
        except Exception as error:
            # Core routines already attempt rollback; replaying their successful
            # forward AND rollback moves reverses any remaining changes safely.
            token.journal = None
            unresolved = {origin for origin, location in journal.owners.items() if str(origin) != str(location)}
            remaining_moves = [move for move, origin in zip(journal.data['moves'], journal.move_origins) if origin in unresolved]
            failures = self._reverse(remaining_moves, rollback=True)
            for path in reversed(journal.data['created']):
                try:
                    Path(path).rmdir()
                except FileNotFoundError:
                    pass
                except OSError as failure:
                    failures.append(str(failure))
            journal.data['status'] = 'failed' if failures else 'rolled_back'
            journal.data['error'] = str(error)
            journal.data['recovery_errors'] = failures
            journal.save()
            if failures:
                raise RuntimeError(f'{error}\n復元失敗: ' + '; '.join(failures) + f'\n履歴: {journal.path}') from error
            if token.cancelled.is_set():
                raise Cancelled('キャンセルしました。変更を元に戻しました。') from error
            raise
        finally:
            token.journal = None

    @staticmethod
    def _reverse(moves, rollback=False):
        completed = []
        try:
            for source, destination in reversed(moves):
                checkpoint(f'復元: {Path(source).name}', rollback)
                move_no_replace(destination, source, rollback=rollback)
                completed.append((source, destination))
        except Exception as error:
            failures = [str(error)]
            for source, destination in reversed(completed):
                try:
                    move_no_replace(source, destination, rollback=True)
                except Exception as failure:
                    failures.append(str(failure))
            return failures
        return []

    def undo(self, path):
        path = Path(path)
        if path.parent != self.directory or is_link(path):
            raise ValueError('無効な履歴です')
        data = validate_record(json.loads(path.read_text(encoding='utf-8')))
        if data['status'] != 'completed':
            raise ValueError('完了した操作だけを元に戻せます')
        paths = [p for move in data['moves'] for p in move] + data['created'] + [item['path'] for item in data['final']]
        if not all(Path(p).is_absolute() for p in paths):
            raise ValueError('履歴に相対パスが含まれています')
        moves = data['moves']
        if not data['final']:
            # Older Windows case-only histories omitted their final state.
            # A true no-op needs no replay; an unprotected change must stop.
            locations = {}
            for source, destination in moves:
                source, destination = Path(source), Path(destination)
                origin = next((owner for owner, location in locations.items() if location == source), source)
                locations[origin] = destination
            if any(str(origin) != str(location) for origin, location in locations.items()):
                raise ValueError('復元用の状態記録が不足しているため、安全に復元できません')
            moves = []
        for item in data['final']:
            if not states_match(fingerprint(Path(item['path'])), item['state']):
                raise ValueError(f'操作後に変更されたため復元できません: {item["path"]}')
        failures = self._reverse(moves)
        if failures:
            token = current.get()
            if token is not None and token.cancelled.is_set() and len(failures) == 1:
                raise Cancelled('復元をキャンセルしました。実行前の状態を維持しています。')
            raise RuntimeError('復元できませんでした: ' + '; '.join(failures))
        for created in reversed(data['created']):
            try:
                Path(created).rmdir()
            except FileNotFoundError:
                pass
            except OSError:
                # Keep a directory if another app placed new data in it.
                pass
        data['status'] = 'undone'
        atomic_json(path, data)
