from dataclasses import asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from companion.core import CHARACTERS, Engine, Event, Settings, is_quiet, load_json, save_json


class NotificationTests(unittest.TestCase):
    def test_pending_meeting_keeps_one_notification_after_acceptance_and_old_history_is_respected(self):
        self.settings.chatter = False
        pending = Event('shared-key', self.event.start, self.event.end, response='未承諾')
        notice = self.engine.next_notice(self.now, [pending], connected=True)
        self.assertIn('未承諾', notice.heading)
        accepted = Event('shared-key', self.event.start, self.event.end)
        self.assertIsNone(self.engine.next_notice(self.now, [accepted], connected=True))
        self.engine.notified = {'old-entry-key': (self.event.end + timedelta(days=1)).timestamp()}
        upgraded = Event('new-global-key', self.event.start, self.event.end, legacy_key='old-entry-key')
        self.assertIsNone(self.engine.next_notice(self.now, [upgraded], connected=True))

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / "history.json"
        self.settings = Settings()
        self.now = datetime(2026, 10, 22, 10, 0, tzinfo=timezone.utc)
        self.engine = Engine(self.settings, self.path, choose=lambda values: values[0])
        self.engine.last_display = self.now - timedelta(hours=3)
        self.event = Event("opaque-occurrence-key", self.now + timedelta(minutes=10), self.now + timedelta(minutes=40), "CONFIDENTIAL_PROJECT")

    def test_quiet_overnight_and_boundaries(self):
        for hour, expected in ((0, True), (8, True), (9, False), (17, False), (18, True), (23, True)):
            self.assertEqual(is_quiet(self.now.replace(hour=hour), self.settings), expected)
        self.settings.quiet_start, self.settings.quiet_end = "12:00", "13:00"
        self.assertTrue(is_quiet(self.now.replace(hour=12), self.settings))
        self.assertFalse(is_quiet(self.now.replace(hour=13), self.settings))
        self.settings.quiet_end = "12:00"
        self.assertFalse(is_quiet(self.now.replace(hour=12), self.settings))

    def test_meeting_priority_and_duplicate_across_restart(self):
        notice = self.engine.next_notice(self.now, [self.event], connected=True)
        self.assertTrue(notice.important)
        self.assertIn("あと10分", notice.heading)
        second = Engine(self.settings, self.path)
        second.last_display = self.now
        self.assertIsNone(second.next_notice(self.now, [self.event], connected=True))

    def test_calendar_save_failure_retries_without_consuming_notice_or_cooldown(self):
        previous = self.engine.last_display
        with patch.object(Path, 'replace', side_effect=PermissionError('temporary lock')):
            with self.assertRaises(OSError):
                self.engine.next_notice(self.now, [self.event], connected=True)
        self.assertNotIn(self.event.key, self.engine.notified)
        self.assertEqual(self.engine.last_display, previous)
        self.engine.persist(self.now)  # Unrelated later saves must not mark it seen.
        reloaded = Engine(self.settings, self.path)
        self.assertTrue(reloaded.next_notice(self.now + timedelta(seconds=15), [self.event], connected=True).important)
        self.assertIsNone(reloaded.next_notice(self.now + timedelta(seconds=30), [self.event], connected=True))
        self.assertIsNone(Engine(self.settings, self.path).next_notice(self.now + timedelta(seconds=45), [self.event], connected=True))

    def test_subject_not_displayed_or_persisted_by_default(self):
        notice = self.engine.next_notice(self.now, [self.event], connected=True)
        self.assertNotIn(self.event.title, notice.text)
        self.assertNotIn(self.event.title, self.path.read_text())
        self.assertNotIn(self.event.start.isoformat(), self.path.read_text())

    def test_opt_in_title_is_only_in_notification(self):
        self.settings.show_titles = True
        notice = self.engine.next_notice(self.now, [self.event], connected=True)
        self.assertIn(self.event.title, notice.text)
        self.assertNotIn(self.event.title, self.path.read_text())

    def test_hidden_pause_and_quiet_do_not_consume_notifications(self):
        self.assertIsNone(self.engine.next_notice(self.now, [self.event], hidden=True, connected=True))
        self.engine.paused_until = self.now + timedelta(hours=1)
        self.assertIsNone(self.engine.next_notice(self.now, [self.event], connected=True))
        self.engine.paused_until = None
        late = self.now.replace(hour=18)
        self.assertIsNone(self.engine.next_notice(late, [self.event], connected=True))
        self.assertFalse(self.engine.notified)

    def test_disconnected_cannot_notify_cached_meeting(self):
        self.settings.chatter = False
        self.assertIsNone(self.engine.next_notice(self.now, [self.event], connected=False))

    def test_started_meeting_is_not_notified_and_suppresses_chatter(self):
        event = Event("ongoing", self.now - timedelta(minutes=1), self.now + timedelta(minutes=30))
        self.assertIsNone(self.engine.next_notice(self.now, [event], connected=True))

    def test_chatter_interval_and_no_immediate_repeat(self):
        notice = self.engine.next_notice(self.now, [])
        self.assertFalse(notice.important)
        self.assertIsNone(self.engine.next_notice(self.now + timedelta(minutes=9, seconds=59), []))
        next_notice = self.engine.next_notice(self.now + timedelta(minutes=10), [])
        self.assertNotEqual(notice.text, next_notice.text)

    def test_manual_menu_delays_chatter_but_not_meeting(self):
        self.assertIsNone(self.engine.next_notice(self.now, [], allow_chatter=False))
        self.assertTrue(self.engine.next_notice(self.now, [self.event], connected=True, allow_chatter=False).important)

    def test_cancelled_or_removed_event_does_not_generate_notice(self):
        self.settings.chatter = False
        self.assertIsNone(self.engine.next_notice(self.now, [], connected=True))

    def test_recurrences_have_separate_occurrence_keys(self):
        self.engine.next_notice(self.now, [self.event], connected=True)
        tomorrow = self.now + timedelta(days=1)
        other = Event("next-occurrence", self.event.start + timedelta(days=1), self.event.end + timedelta(days=1))
        self.assertTrue(self.engine.next_notice(tomorrow, [other], connected=True).important)

    def test_corrupt_settings_and_history_can_be_loaded(self):
        path = Path(self.temp.name) / "settings.json"
        path.write_text("broken")
        self.assertEqual(Settings.load(path), Settings())
        save_json(path, {"interval": -2, "quiet_start": "invalid", "personality": "unknown", "show_titles": "yes"})
        self.assertEqual(Settings.load(path), Settings())
        self.path.write_text("[]")
        self.assertEqual(load_json(self.path), {})

    def test_character_persistence_and_backwards_compatibility(self):
        path = Path(self.temp.name) / "settings.json"
        save_json(path, {"personality": "冷静な案内役", "interval": 120})
        old = Settings.load(path)
        self.assertEqual(old.character, "A")
        self.assertEqual(old.interval, 10)
        for character in CHARACTERS:
            with self.subTest(character=character):
                old.character = character
                save_json(path, asdict(old))
                restored = Settings.load(path)
                self.assertEqual(restored.character, character)
                self.assertEqual(restored.personality, "冷静な案内役")
        for invalid in ("C", "unknown", "", 5, None):
            save_json(path, {"character": invalid})
            self.assertEqual(Settings.load(path).character, "A")


if __name__ == "__main__":
    unittest.main()
