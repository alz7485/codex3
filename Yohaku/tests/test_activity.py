from datetime import datetime, timedelta, timezone
from pathlib import Path
import sqlite3
import tempfile
import unittest
from types import ModuleType, SimpleNamespace
from unittest.mock import Mock, patch

from companion.activity import FileHistory, FileTracker, FileObservation, FileSnapshot, MAX_HISTORY_RECORDS, retention_start


class FileHistoryTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "files.sqlite3"
        self.history = FileHistory(self.path)
        self.tracker = FileTracker(self.history)
        self.now = datetime(2026, 10, 22, 10, tzinfo=timezone.utc)

    def file(self, name="予算.xlsx", folder="A", opened=None):
        return FileObservation(f"C:\\work\\{folder}\\{name}", name, "Excel", opened)

    def rows(self, now=None):
        now = now or self.now
        return self.history.for_day(now.astimezone().date(), now, 2000)

    def test_disabled_records_nothing_and_does_not_create_database(self):
        self.tracker.ingest([self.file()], self.now)
        self.assertFalse(self.path.exists())
        self.assertEqual(self.rows(), [])

    def test_opt_in_skips_baseline_and_records_file_name_and_full_path_once(self):
        old, new = self.file("既存.xlsx"), self.file()
        self.tracker.configure(True, self.now)
        self.tracker.ingest([old], self.now)
        self.tracker.ingest([old, new, new], self.now + timedelta(seconds=5))
        self.tracker.ingest([new], self.now + timedelta(seconds=10))
        rows = self.rows()
        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0][:3], ("予算.xlsx", "C:\\work\\A\\予算.xlsx", "Excel"))
        from contextlib import closing
        with closing(sqlite3.connect(self.path)) as db:
            columns = [row[1] for row in db.execute("PRAGMA table_info(files)")]
            self.assertEqual(columns, ["id", "name", "path", "source", "opened", "observed"])

    def test_same_filename_in_different_directories_and_reopening(self):
        a, b = self.file(folder="A"), self.file(folder="B")
        self.tracker.configure(True, self.now)
        self.tracker.ingest([], self.now)
        self.tracker.ingest([a, b], self.now + timedelta(seconds=5))
        self.assertEqual(len(self.rows()), 2)
        self.tracker.ingest([b], self.now + timedelta(seconds=10))
        self.tracker.ingest([a, b], self.now + timedelta(seconds=30))
        self.assertEqual(len(self.rows()), 3)

    def test_failed_sqlite_save_retries_office_and_recent_without_loss_or_duplicates(self):
        for recent in (False, True):
            for delay in (5, 20):
                with self.subTest(recent=recent, delay=delay):
                    self.history.clear()
                    self.tracker.configure(True, self.now)
                    self.tracker.ingest([], self.now)
                    stamp = self.now + timedelta(seconds=5)
                    item = self.file(opened=stamp if recent else None)
                    with patch.object(self.history, 'append', side_effect=sqlite3.OperationalError('locked')):
                        with self.assertRaises(sqlite3.OperationalError):
                            self.tracker.ingest([item], stamp)
                    self.assertEqual(self.tracker.previous_office, set())
                    self.assertEqual(self.tracker.last_recorded, {})
                    self.assertEqual(self.tracker.recent_seen, {})
                    self.tracker.ingest([item], stamp + timedelta(seconds=delay))
                    self.tracker.ingest([item], stamp + timedelta(seconds=60))
                    self.assertEqual(len(self.rows()), 1)

    def test_incomplete_source_keeps_known_files_but_complete_close_allows_reopen(self):
        item = self.file()
        self.tracker.configure(True, self.now)
        self.tracker.ingest([item], self.now)
        self.tracker.ingest(FileSnapshot([], ['Excel']), self.now + timedelta(seconds=5))
        self.tracker.ingest([item], self.now + timedelta(seconds=10))
        self.assertEqual(self.rows(), [])
        self.tracker.ingest([], self.now + timedelta(seconds=20))
        self.tracker.ingest([item], self.now + timedelta(seconds=40))
        self.assertEqual(len(self.rows()), 1)

    def test_initial_busy_source_recovers_as_baseline_then_tracks_new_files(self):
        self.tracker.configure(True, self.now)
        self.tracker.ingest(FileSnapshot([], ['Excel']), self.now)
        self.tracker.ingest([self.file()], self.now + timedelta(seconds=5))
        self.assertEqual(self.rows(), [])
        self.tracker.ingest([self.file(), self.file('新規.xlsx')], self.now + timedelta(seconds=10))
        self.assertEqual([row[0] for row in self.rows()], ['新規.xlsx'])

    def test_busy_office_adapter_marks_incomplete_and_does_not_invent_reopen(self):
        from companion.activity import opened_file_snapshot
        com = ModuleType('pythoncom')
        com.CoInitialize, com.CoUninitialize = Mock(), Mock()
        package, client = ModuleType('win32com'), ModuleType('win32com.client')
        package.client = client
        shell = ModuleType('win32com.shell')
        shell.shell = SimpleNamespace(SHGetFolderPath=lambda *_: self.temp.name)
        shell.shellcon = SimpleNamespace(CSIDL_RECENT=8)
        class NoInstance(Exception):
            hresult = -2147221021
        busy = False
        def document(_):
            if busy:
                raise RuntimeError('RPC_E_CALL_REJECTED')
            return SimpleNamespace(Path='C:/work', FullName='C:/work/test.docx', Name='test.docx')
        office = SimpleNamespace(Documents=SimpleNamespace(Count=1, Item=document))
        def active(name):
            if name == 'Word.Application':
                return office
            raise NoInstance()
        client.GetActiveObject = Mock(side_effect=active)
        self.tracker.configure(True, self.now)
        modules = {'pythoncom':com, 'win32com':package, 'win32com.client':client, 'win32com.shell':shell}
        with patch.dict('sys.modules', modules), patch('sys.platform', 'win32'):
            for seconds, busy in ((0, False), (5, True), (10, False)):
                snapshot = opened_file_snapshot()
                self.assertEqual(snapshot.incomplete_sources, {'Word'} if busy else set())
                self.assertEqual(bool(snapshot.warnings), busy)
                self.tracker.ingest(snapshot, self.now + timedelta(seconds=seconds))
        self.assertEqual(self.rows(), [])
        self.assertEqual(com.CoInitialize.call_count, 3)
        self.assertEqual(com.CoUninitialize.call_count, 3)

    def test_off_and_reenable_do_not_import_preexisting_files(self):
        self.tracker.configure(True, self.now)
        self.tracker.ingest([], self.now)
        self.tracker.configure(False, self.now + timedelta(seconds=2))
        self.tracker.ingest([self.file()], self.now + timedelta(seconds=5))
        self.assertFalse(self.path.exists())
        self.tracker.configure(True, self.now + timedelta(seconds=10))
        self.tracker.ingest([self.file()], self.now + timedelta(seconds=10))
        self.tracker.ingest([self.file(), self.file("新規.xlsx")], self.now + timedelta(seconds=15))
        self.assertEqual(len(self.rows()), 1)

    def test_recent_item_updates_merge_with_office_observation(self):
        old = self.file(opened=self.now - timedelta(days=1))
        self.tracker.configure(True, self.now)
        self.tracker.ingest([old], self.now)
        stamp = self.now + timedelta(seconds=3)
        recent = FileObservation(old.path, old.name, "Windowsの最近使ったファイル", stamp)
        self.tracker.ingest([recent, self.file()], self.now + timedelta(seconds=5))
        self.assertEqual(len(self.rows()), 1)
        self.assertEqual(self.rows()[0][2], "Excel")
        self.tracker.ingest([recent, self.file()], self.now + timedelta(seconds=10))
        self.assertEqual(len(self.rows()), 1)

    def test_date_filter_distinguishes_midnight_and_empty_days(self):
        day = self.now.astimezone().date()
        today = datetime.combine(day, datetime.min.time()).astimezone()
        previous = today - timedelta(seconds=1)
        self.history.append([self.file("昨日.xlsx", opened=previous), self.file("今日.xlsx", opened=today)], self.now)
        self.assertEqual(self.history.for_day(day, self.now)[0][0], "今日.xlsx")
        self.assertEqual(self.history.for_day(day - timedelta(days=1), self.now)[0][0], "昨日.xlsx")
        self.assertEqual(self.history.for_day(day - timedelta(days=2), self.now), [])

    def test_retention_limit_clear_and_reload(self):
        files = [self.file(f"{i}.xlsx", opened=self.now + timedelta(seconds=i)) for i in range(MAX_HISTORY_RECORDS + 3)]
        self.history.append(files, self.now)
        loaded = FileHistory(self.path)
        self.assertEqual(len(loaded.for_day(self.now.astimezone().date(), self.now, MAX_HISTORY_RECORDS + 10)), MAX_HISTORY_RECORDS)
        self.assertEqual(loaded.for_day(self.now.astimezone().date(), self.now + timedelta(days=100)), [])
        loaded.clear()
        self.assertFalse(self.path.exists())

    def test_three_calendar_month_retention_includes_boundary_and_handles_month_ends(self):
        now = self.now.replace(month=10, day=31)
        self.assertEqual(retention_start(now).isoformat(), '2026-07-31')
        feb = now.replace(month=5)
        self.assertEqual(retention_start(feb).isoformat(), '2026-02-28')
        self.history.append([self.file('境界.xlsx', opened=now.replace(month=7, day=31)),
                             self.file('期限切れ.xlsx', opened=now.replace(month=7, day=30))], now)
        rows = self.history.for_day(now.replace(month=7, day=31).date(), now)
        self.assertEqual(rows[0][0], '境界.xlsx')
        self.assertEqual(self.history.for_day(now.replace(month=7, day=30).date(), now), [])

    def test_office_adapter_reads_existing_workbook_metadata_without_opening_file(self):
        from companion.activity import opened_file_snapshot
        pythoncom = ModuleType("pythoncom")
        pythoncom.CoInitialize = Mock()
        pythoncom.CoUninitialize = Mock()
        win32com = ModuleType("win32com")
        client = ModuleType("win32com.client")
        saved = SimpleNamespace(Path="C:\\work", FullName="C:\\work\\予算.xlsx", Name="予算.xlsx")
        unsaved = SimpleNamespace(Path="", FullName="Book1", Name="Book1")
        office = SimpleNamespace(Workbooks=SimpleNamespace(Count=2, Item=lambda i: saved if i == 1 else unsaved))
        def get_existing(name):
            if name == "Excel.Application":
                return office
            raise RuntimeError("not running")
        client.GetActiveObject = Mock(side_effect=get_existing)
        win32com.client = client
        shell_package = ModuleType("win32com.shell")
        shell_package.shell = SimpleNamespace(SHGetFolderPath=lambda *args: self.temp.name)
        shell_package.shellcon = SimpleNamespace(CSIDL_RECENT=8)
        with patch.dict("sys.modules", {"pythoncom": pythoncom, "win32com": win32com,
                                       "win32com.client": client, "win32com.shell": shell_package}), patch("sys.platform", "win32"):
            observations = opened_file_snapshot()
        self.assertEqual(len(observations), 1)
        self.assertEqual(observations[0].path, saved.FullName)
        self.assertEqual(observations[0].source, "Excel")
        pythoncom.CoUninitialize.assert_called_once()


if __name__ == "__main__":
    unittest.main()
