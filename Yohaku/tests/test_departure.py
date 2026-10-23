from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import types
import unittest
from unittest.mock import Mock, patch

from companion.core import Engine, Settings, save_json
from companion.departure import attendance_url, departure_body, system_uptime_seconds


class DepartureTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'history.json'
        self.now = datetime(2026, 10, 23, 17, 20, tzinfo=timezone.utc)
        self.settings = Settings(departure_enabled=True, departure_time='17:20', quiet_start='00:00', quiet_end='00:00')
        self.engine = Engine(self.settings, self.path)

    def test_scheduled_notice_has_windows_boot_time_and_is_once_per_day_across_restart(self):
        provider = Mock(return_value=9 * 3600 + 5 * 60)
        self.assertIsNone(self.engine.departure_notice(self.now - timedelta(seconds=1), uptime_provider=provider))
        notice = self.engine.departure_notice(self.now, uptime_provider=provider)
        self.assertEqual(notice.kind, 'departure')
        self.assertIn('10/23 08:15', notice.text)
        self.assertIn('9時間5分', notice.text)
        self.assertIsNone(self.engine.departure_notice(self.now + timedelta(minutes=1), uptime_provider=provider))
        provider.assert_called_once()
        self.engine.persist(self.now)
        restarted = Engine(self.settings, self.path)
        self.assertIsNone(restarted.departure_notice(self.now))
        self.assertIsNotNone(restarted.departure_notice(self.now + timedelta(days=3)))

    def test_hidden_quiet_pause_weekend_and_expired_window_do_not_mark_as_notified(self):
        self.assertIsNone(self.engine.departure_notice(self.now, hidden=True))
        self.settings.quiet_start, self.settings.quiet_end = '17:00', '18:00'
        self.assertIsNone(self.engine.departure_notice(self.now))
        self.settings.quiet_start = self.settings.quiet_end = '00:00'
        self.engine.paused_until = self.now + timedelta(hours=1)
        self.assertIsNone(self.engine.departure_notice(self.now))
        self.engine.paused_until = None
        self.assertIsNone(self.engine.departure_notice(self.now + timedelta(days=1)))
        self.assertIsNone(self.engine.departure_notice(self.now + timedelta(minutes=10)))
        self.assertEqual(self.engine.departure_date, '')
        self.settings.departure_enabled = False
        self.assertIsNone(self.engine.departure_notice(self.now))
        self.settings.departure_enabled = True
        self.settings.departure_weekdays = False
        self.assertIsNotNone(self.engine.departure_notice(self.now + timedelta(days=1)))

    def test_attendance_url_is_user_supplied_http_or_https_and_is_not_opened_by_schedule(self):
        self.assertEqual(attendance_url(''), '')
        self.assertEqual(attendance_url(' http://intranet/time '), 'http://intranet/time')
        for value in ('javascript:alert(1)', 'file:///C:/test.exe', 'https://', 'https://host/with space'):
            with self.assertRaises(ValueError): attendance_url(value)
        self.settings.attendance_url = 'https://attendance.example.test/input'
        with patch('webbrowser.open') as browser:
            self.assertIsNotNone(self.engine.departure_notice(self.now))
            browser.assert_not_called()

    def test_unknown_uptime_is_reported_and_real_windows_counter_is_used(self):
        self.assertIn('取得できません', departure_body('退勤です。', self.now, None))
        clock = Mock(return_value=30_000)
        fake = types.SimpleNamespace(kernel32=types.SimpleNamespace(GetTickCount64=clock))
        with patch('companion.departure.sys.platform', 'win32'), patch('companion.departure.ctypes.windll', fake, create=True):
            self.assertEqual(system_uptime_seconds(), 30)
        self.assertNotIn('勤怠', departure_body('独自のメッセージ', self.now, 1))

    def test_settings_migrate_and_validate_and_do_not_store_attendance_url_in_notice_history(self):
        path = Path(self.temp.name) / 'settings.json'
        save_json(path, {'departure_time':'bad', 'attendance_url':'file:///C:/a.exe'})
        restored = Settings.load(path)
        self.assertFalse(restored.departure_enabled)
        self.assertEqual(restored.departure_time, '17:00')
        self.assertEqual(restored.attendance_url, '')
        self.settings.attendance_url = 'https://attendance.example.test/input'
        self.engine.departure_notice(self.now)
        self.engine.persist(self.now)
        self.assertNotIn('attendance.example.test', self.path.read_text())


if __name__ == '__main__': unittest.main()
