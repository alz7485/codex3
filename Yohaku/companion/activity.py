"""Opt-in file-open observations from existing Office instances and Recent Items.

Never reads document contents or starts Office. Not an exhaustive Windows audit.
"""
from __future__ import annotations

from contextlib import contextmanager
from calendar import monthrange
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
import ntpath
from pathlib import Path
import sqlite3
import sys

MAX_HISTORY_RECORDS = 15000
DAY_RECORD_LIMIT = 2000


def retention_start(now):
    day = now.astimezone().date()
    month = day.year * 12 + day.month - 1 - 3
    year, month = divmod(month, 12)
    return day.replace(year=year, month=month + 1, day=min(day.day, monthrange(year, month + 1)[1]))


@dataclass(frozen=True)
class FileObservation:
    path: str
    name: str
    source: str
    opened: datetime | None = None

    @property
    def key(self):
        return self.path.replace("/", "\\").casefold()


class FileSnapshot(list):
    """Observations plus sources whose missing entries cannot imply a close."""
    def __init__(self, values=(), incomplete_sources=()):
        super().__init__(values)
        self.incomplete_sources = set(incomplete_sources)

    @property
    def warnings(self):
        return tuple(f'{source}の文書を一部確認できません。次回の確認で再試行します。'
                     for source in sorted(self.incomplete_sources))


def opened_file_snapshot() -> list[FileObservation]:
    if sys.platform != "win32":
        raise RuntimeError("ファイル履歴はWindowsで利用できます。")
    import pythoncom
    import win32com.client
    from win32com.shell import shell, shellcon
    pythoncom.CoInitialize()
    try:
        result = FileSnapshot()
        for application, collection, title in (("Excel.Application", "Workbooks", "Excel"),
                                               ("Word.Application", "Documents", "Word"),
                                               ("PowerPoint.Application", "Presentations", "PowerPoint")):
            try:
                office = win32com.client.GetActiveObject(application)
                documents = getattr(office, collection)
                count = int(documents.Count)
                if count > 256:
                    result.incomplete_sources.add(title)
                for index in range(1, min(count, 256) + 1):
                    try:
                        document = documents.Item(index)
                        if not str(document.Path):
                            continue  # Unsaved document, no stable file identity.
                        result.append(FileObservation(str(document.FullName), str(document.Name), title))
                    except Exception:
                        result.incomplete_sources.add(title)
                        continue  # Busy Office or closing document: retry next scan.
            except Exception as error:
                # MK_E_UNAVAILABLE means no running instance; other failures
                # leave its document state unknown rather than empty.
                if getattr(error, 'hresult', None) != -2147221021:
                    result.incomplete_sources.add(title)
                continue  # Never start an Office instance.
        try:
            recent = Path(shell.SHGetFolderPath(0, shellcon.CSIDL_RECENT, 0, 0))
            shortcuts = []
            for path in recent.glob("*.lnk"):
                try:
                    shortcuts.append((path.stat().st_mtime, path))
                except OSError:
                    continue
            for modified, path in sorted(shortcuts, key=lambda pair: pair[0], reverse=True)[:1000]:
                try:
                    link = pythoncom.CoCreateInstance(shell.CLSID_ShellLink, None, pythoncom.CLSCTX_INPROC_SERVER, shell.IID_IShellLink)
                    link.QueryInterface(pythoncom.IID_IPersistFile).Load(str(path))
                    target, attributes = link.GetPath(4)  # SLGP_RAWPATH; no Resolve.
                    if not target or (attributes and int(attributes[0]) & 0x10):
                        continue  # Cached directory attribute; do not stat the target.
                    name = ntpath.basename(target)
                    if name:
                        result.append(FileObservation(target, name, "Windowsの最近使ったファイル",
                                                      datetime.fromtimestamp(modified, timezone.utc).astimezone()))
                except Exception:
                    continue
        except Exception:
            if not result:
                raise RuntimeError("ファイル履歴を確認できません。最近使ったファイルとOfficeの状態をご確認ください。") from None
        return result
    finally:
        pythoncom.CoUninitialize()


class FileHistory:
    def __init__(self, path: Path):
        self.path = path

    @contextmanager
    def _connect(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        db = sqlite3.connect(self.path)
        try:
            with db:
                db.execute("PRAGMA secure_delete=ON")
                db.execute("CREATE TABLE IF NOT EXISTS files (id INTEGER PRIMARY KEY, name TEXT NOT NULL, path TEXT NOT NULL, source TEXT NOT NULL, opened TEXT NOT NULL, observed TEXT NOT NULL, UNIQUE(path, opened))")
                db.execute('CREATE INDEX IF NOT EXISTS files_opened_idx ON files(opened)')
                yield db
        finally:
            db.close()

    @staticmethod
    def _prune(db, now):
        cutoff = datetime.combine(retention_start(now), time.min).astimezone().astimezone(timezone.utc).isoformat()
        db.execute("DELETE FROM files WHERE opened < ?", (cutoff,))
        db.execute("DELETE FROM files WHERE id NOT IN (SELECT id FROM files ORDER BY opened DESC, id DESC LIMIT ?)", (MAX_HISTORY_RECORDS,))

    def append(self, observations: list[FileObservation], now: datetime):
        if not observations and not self.path.exists():
            return
        with self._connect() as db:
            for item in observations:
                db.execute("INSERT OR IGNORE INTO files(name, path, source, opened, observed) VALUES (?, ?, ?, ?, ?)",
                           (item.name, item.path, item.source, (item.opened or now).astimezone(timezone.utc).isoformat(), now.astimezone(timezone.utc).isoformat()))
            self._prune(db, now)

    def for_day(self, day: date, now: datetime, limit=DAY_RECORD_LIMIT):
        if not self.path.exists():
            return []
        start = datetime.combine(day, time.min).astimezone().astimezone(timezone.utc).isoformat()
        end = datetime.combine(day + timedelta(days=1), time.min).astimezone().astimezone(timezone.utc).isoformat()
        with self._connect() as db:
            self._prune(db, now)
            return db.execute("SELECT name, path, source, opened FROM files WHERE opened >= ? AND opened < ? ORDER BY opened DESC LIMIT ?", (start, end, limit)).fetchall()

    def repeat_summary(self, now):
        if not self.path.exists():
            return None
        day = now.astimezone().date()
        start = datetime.combine(day, time.min).astimezone().astimezone(timezone.utc).isoformat()
        end = datetime.combine(day + timedelta(days=1), time.min).astimezone().astimezone(timezone.utc).isoformat()
        with self._connect() as db:
            row = db.execute("SELECT name, COUNT(*) AS n FROM files WHERE opened >= ? AND opened < ? GROUP BY path COLLATE NOCASE ORDER BY n DESC, MAX(opened) DESC LIMIT 1", (start, end)).fetchone()
        return {'file_name': row[0], 'file_open_count': row[1]} if row else {'file_name': '', 'file_open_count': 0}

    def target_counts(self, targets, now):
        """Match retained observations only; never scan or open a target folder."""
        counts={target['id']:0 for target in targets}
        if not targets or not self.path.exists(): return counts
        day=now.astimezone().date()
        start=datetime.combine(day,time.min).astimezone().astimezone(timezone.utc).isoformat()
        end=datetime.combine(day+timedelta(days=1),time.min).astimezone().astimezone(timezone.utc).isoformat()
        with self._connect() as db:
            rows=db.execute('SELECT path, COUNT(*) FROM files WHERE opened>=? AND opened<? GROUP BY path',(start,end)).fetchall()
        for target in targets:
            key=ntpath.normpath(target['path']).casefold().rstrip('\\')
            for path,count in rows:
                normalized=ntpath.normpath(path).casefold()
                if normalized==key or (target['kind']=='folder' and normalized.startswith(key+'\\')):
                    counts[target['id']]+=count
        return counts

    def search(self, text, now):
        """Search every retained row; dates and the per-day display cap do not apply."""
        query = text.strip().casefold()
        if not query or not self.path.exists():
            return []
        with self._connect() as db:
            self._prune(db, now)
            db.create_function('casefold', 1, str.casefold, deterministic=True)
            return db.execute(
                'SELECT name, path, source, opened FROM files '
                'WHERE instr(casefold(name), ?) > 0 OR instr(casefold(path), ?) > 0 '
                'ORDER BY opened DESC, id DESC LIMIT ?',
                (query, query, MAX_HISTORY_RECORDS)).fetchall()

    def clear(self):
        self.path.unlink(missing_ok=True)


class FileTracker:
    def __init__(self, history: FileHistory):
        self.history = history
        self.enabled = False
        self.since = None
        self.previous_office = set()
        self.office_sources = {}
        self.unbaselined_sources = set()
        self.recent_seen = {}
        self.last_recorded = {}
        self.baselined = False

    def configure(self, enabled: bool, now: datetime):
        self.enabled = enabled
        self.since = now
        self.previous_office.clear()
        self.office_sources.clear()
        self.unbaselined_sources.clear()
        self.recent_seen.clear()
        self.last_recorded.clear()
        self.baselined = False

    def ingest(self, snapshot: list[FileObservation], now: datetime):
        if not self.enabled:
            return
        office = {item.key: item for item in snapshot if item.opened is None}
        recent = {item.key: item for item in snapshot if item.opened is not None}
        incomplete = set(getattr(snapshot, 'incomplete_sources', ()))
        candidates = {}
        if self.baselined:
            for key, item in recent.items():
                if item.opened >= self.since and self.recent_seen.get(key) != item.opened:
                    candidates[key] = item
            for key, item in office.items():
                if key not in self.previous_office and item.source not in self.unbaselined_sources:
                    timestamp = candidates[key].opened if key in candidates else now
                    candidates[key] = FileObservation(item.path, item.name, item.source, timestamp)
        additions = []
        recorded = dict(self.last_recorded)
        for key, item in candidates.items():
            stamp = item.opened or now
            previous = self.last_recorded.get(key)
            if previous is None or abs((stamp - previous).total_seconds()) > 15:
                additions.append(item)
                recorded[key] = stamp
        self.history.append(additions, now)
        # Commit deduplication and baselines only after the DB transaction.
        retained = {key: source for key, source in self.office_sources.items() if source in incomplete}
        retained.update({key: item.source for key, item in office.items()})
        self.office_sources = retained
        self.previous_office = set(retained)
        self.unbaselined_sources = ((self.unbaselined_sources & incomplete) if self.baselined else incomplete)
        self.recent_seen = {key: item.opened for key, item in recent.items()}
        self.last_recorded = {key: stamp for key, stamp in recorded.items() if (now - stamp).total_seconds() < 86400}
        self.baselined = True
