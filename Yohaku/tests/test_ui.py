"""Headless UI checks. Run with QT_QPA_PLATFORM=offscreen."""
from datetime import datetime, timedelta
import os
import hashlib
from pathlib import Path
import tempfile
import time
import unittest
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
from companion.core import CHARACTERS, PHRASES, Event, Settings
from companion.activity import FileObservation
from companion.dialogue import voice_for
from companion.ui import Controller, Panel, character_frames, character_pixmap, create_application


class UserInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory()
        cls.old_local = os.environ.get("LOCALAPPDATA")
        os.environ["LOCALAPPDATA"] = cls.temp.name
        cls.app = create_application()
        cls.controller = Controller(cls.app)

    @classmethod
    def tearDownClass(cls):
        c = cls.controller
        c.tick_timer.stop()
        c.poll_timer.stop()
        c.animation_timer.stop()
        c.activity_timer.stop()
        c.tray.hide()
        c.panel.hide()
        c.resident.hide()
        c.bubble.hide()
        c.interaction.hide()
        c.history_window.hide()
        cls.temp.cleanup()
        if cls.old_local is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = cls.old_local

    def setUp(self):
        self.controller.history_window.hide()

    def test_pause_and_restore(self):
        c = self.controller
        c.pause()
        self.assertIsNotNone(c.engine.paused_until)
        self.assertIn("解除", c.panel.pause_button.text())
        c.pause()
        self.assertIsNone(c.engine.paused_until)

    def test_sharing_hides_character_and_blocks_sample(self):
        c = self.controller
        c.share()
        self.assertTrue(c.hidden)
        self.assertFalse(c.resident.isVisible())
        self.assertFalse(c.panel.isVisible())
        c.sample()
        self.assertFalse(c.bubble.isVisible())
        c.share()
        self.assertTrue(c.resident.isVisible())

    def test_privacy_change_clears_cached_title_and_bubble(self):
        c = self.controller
        now = datetime.now().astimezone()
        c.events = [Event("key", now, now + timedelta(hours=1), "SECRET")]
        c.panel.event_summary.setText("SECRET")
        c.sample()
        c.panel.update_setting("show_titles", False)
        self.assertFalse(c.events)
        self.assertNotIn("SECRET", c.panel.event_summary.text())
        self.assertFalse(c.bubble.isVisible())
        self.assertTrue((Path(self.temp.name) / "Yohaku/settings.json").exists())

    def test_stale_async_result_cannot_restore_title(self):
        c = self.controller
        c.settings.outlook_enabled = False
        now = datetime.now().astimezone()
        c.received(c.generation - 1, [Event("key", now, now, "SECRET")], "")
        self.assertFalse(c.events)
        self.assertNotIn("SECRET", c.panel.event_summary.text())

    def test_both_pages_and_sample_can_be_rendered(self):
        c = self.controller
        c.show_panel()
        for index in (0, 1):
            c.panel.set_page(index)
            self.app.processEvents()
            self.assertFalse(c.panel.grab().isNull())
        c.sample()
        self.assertTrue(c.bubble.isVisible())
        self.assertIn("実際の予定ではありません", c.bubble.heading.text())
        c.bubble.hide()

    def test_character_choices_apply_and_save_without_interrupting_notification(self):
        c = self.controller
        now = datetime.now().astimezone()
        event = Event("unchanged-event", now + timedelta(minutes=5), now + timedelta(hours=1))
        c.events = [event]
        c.connected = True
        c.connected_at = now
        c.engine.paused_until = now + timedelta(hours=1)
        original_personality = c.settings.personality
        generation = c.generation
        c.sample()
        try:
            rendered = set()
            for key in CHARACTERS:
                with self.subTest(character=key):
                    c.panel.character_buttons[key].click()
                    self.app.processEvents()
                    self.assertEqual(c.resident.character, key)
                    self.assertEqual(c.panel.hero_mascot.character, key)
                    self.assertEqual(c.panel.rail_mascot.character, key)
                    self.assertEqual(c.settings.personality, original_personality)
                    self.assertEqual(c.generation, generation)
                    self.assertTrue(c.connected)
                    self.assertEqual(c.events, [event])
                    self.assertIsNotNone(c.engine.paused_until)
                    self.assertTrue(c.bubble.isVisible())
                    self.assertEqual(sum(b.isChecked() for b in c.panel.character_buttons.values()), 1)
                    restored = Settings.load(Path(self.temp.name) / "Yohaku/settings.json")
                    self.assertEqual(restored.character, key)
                    fresh_panel = Panel(restored)
                    self.assertEqual(fresh_panel.hero_mascot.character, key)
                    self.assertTrue(fresh_panel.character_buttons[key].isChecked())
                    fresh_panel.deleteLater()
                    rendered.add(c.resident.pixmap.cacheKey())
                    self.assertEqual(c.tray.icon().cacheKey(), c.icon.cacheKey())
            self.assertEqual(len(rendered), 4)
        finally:
            c.panel.character_buttons["A"].click()
            c.events = []
            c.connected = False
            c.connected_at = None
            c.engine.paused_until = None
            c.bubble.hide()

    def test_switching_while_sharing_keeps_resident_hidden(self):
        c = self.controller
        c.share()
        try:
            c.panel.character_buttons["F"].click()
            self.assertFalse(c.resident.isVisible())
            self.assertFalse(c.bubble.isVisible())
            self.assertTrue(c.hidden)
            self.assertEqual(c.resident.character, "F")
        finally:
            c.share()
            c.panel.character_buttons["A"].click()

    def test_all_character_assets_have_transparent_background(self):
        for key in CHARACTERS:
            with self.subTest(character=key):
                image = character_pixmap(key).toImage()
                self.assertTrue(image.hasAlphaChannel())
                self.assertEqual(image.pixelColor(0, 0).alpha(), 0)
                self.assertEqual(image.pixelColor(image.width() - 1, image.height() - 1).alpha(), 0)

    def test_app_has_brand_name_version_and_windows_icon(self):
        c = self.controller
        self.assertEqual(self.app.applicationDisplayName(), "余白 / YOHAKU")
        self.assertEqual(self.app.applicationVersion(), "0.7.0")
        self.assertFalse(c.brand_icon.isNull())
        self.assertEqual(c.panel.windowIcon().cacheKey(), c.brand_icon.cacheKey())
        c.panel.character_buttons["B"].click()
        self.assertEqual(c.panel.windowIcon().cacheKey(), c.brand_icon.cacheKey())
        self.assertEqual(c.tray.icon().cacheKey(), c.icon.cacheKey())
        c.panel.character_buttons["A"].click()

    def test_click_menu_selects_all_four_actions_without_leaking_title(self):
        c = self.controller
        now = datetime.now().astimezone()
        c.events = [Event("private", now + timedelta(minutes=30), now + timedelta(hours=1), "SECRET")]
        c.connected = True
        c.connected_at = now
        c.settings.show_titles = False
        try:
            c.resident.clicked.emit()
            self.assertTrue(c.interaction.isVisible())
            self.assertIs(c.interaction, c.bubble)
            self.assertIn(c.bubble.text.text(), PHRASES[voice_for(c.settings)]["call"])
            window_id = int(c.bubble.winId())
            self.assertEqual(set(c.interaction.buttons), {"calendar", "activity", "settings", "message"})
            self.assertTrue(c.interaction.timer.isActive())
            self.assertEqual(c.interaction.timer.interval(), 60000)
            c.interaction.buttons["calendar"].click()
            self.assertIn("件名は非表示", c.interaction.text.text())
            self.assertNotIn("SECRET", c.interaction.text.text())
            self.assertEqual(int(c.bubble.winId()), window_id)
            self.assertFalse(c.history_window.isVisible())
            c.interaction.buttons["message"].click()
            self.assertEqual(int(c.bubble.winId()), window_id)
            self.assertFalse(c.history_window.isVisible())
            c.interaction.buttons["activity"].click()
            self.assertTrue(c.history_window.isVisible())
            self.assertIn("記録オフ", c.history_window.status.text())
            self.assertNotIn("記録オフ", c.bubble.text.text())
            c.interaction.buttons["message"].click()
            first = c.interaction.text.text()
            c.interaction.buttons["message"].click()
            self.assertNotEqual(first, c.interaction.text.text())
            c.panel.hide()
            c.interaction.buttons["settings"].click()
            self.assertTrue(c.panel.isVisible())
            self.assertEqual(int(c.bubble.winId()), window_id)
            c.panel.update_setting("show_titles", False)
            self.assertFalse(c.events)
        finally:
            c.interaction.hide()
            c.history_window.hide()
            c.events = []
            c.connected = False
            c.connected_at = None

    def test_logging_opt_in_stop_stale_result_and_delete(self):
        c = self.controller
        now = datetime.now().astimezone()
        c.activity_history.clear()
        with patch("companion.ui.opened_file_snapshot") as provider:
            c.poll_activity()
            provider.assert_not_called()
        try:
            with patch.object(c, "poll_activity"):
                c.panel.logging_check.click()
            self.assertTrue(c.settings.file_logging)
            c.activity_timer.stop()
            generation = c.activity_generation
            c.activity_received(generation, [], "")
            document = FileObservation("C:\\work\\予算.xlsx", "予算.xlsx", "Excel")
            c.activity_received(generation, [document], "")
            self.assertEqual(c.activity_history.for_day(now.astimezone().date(), now)[0][0], "予算.xlsx")
            c.open_choices()
            c.select_content("activity")
            self.assertEqual(c.history_window.table.topLevelItem(0).text(1), "予算.xlsx")
            self.assertEqual(c.history_window.table.topLevelItem(0).text(2), "C:\\work\\予算.xlsx")
            self.assertNotIn("予算.xlsx", c.bubble.text.text())
            c.panel.logging_check.click()
            self.assertFalse(c.settings.file_logging)
            self.assertFalse(c.activity_timer.isActive())
            c.activity_received(generation, [FileObservation("C:\\stale.xlsx", "STALE.xlsx", "Excel")], "")
            self.assertEqual(len(c.activity_history.for_day(now.astimezone().date(), now)), 1)
            c.panel.clear_history_requested.emit()
            self.assertFalse(c.activity_history.path.exists())
            self.assertEqual(c.history_window.table.topLevelItemCount(), 0)
        finally:
            if c.settings.file_logging:
                c.panel.logging_check.click()
            c.interaction.hide()
            c.history_window.hide()
            c.activity_history.clear()

    def test_file_history_calendar_switches_date_and_reveals_only_selected_day(self):
        c = self.controller
        now = datetime.now().astimezone()
        day = now.date()
        previous = now - timedelta(days=1)
        try:
            c.activity_history.append([FileObservation("C:\\today.xlsx", "今日.xlsx", "Excel", now),
                                       FileObservation("C:\\yesterday.xlsx", "昨日.xlsx", "Excel", previous)], now)
            c.open_choices()
            c.select_content("activity")
            self.assertTrue(c.history_window.calendar.isVisible())
            self.assertEqual(c.history_window.table.topLevelItem(0).text(1), "今日.xlsx")
            c.history_window.calendar.setSelectedDate(c.history_window.calendar.selectedDate().addDays(-1))
            self.assertEqual(c.history_window.table.topLevelItemCount(), 1)
            self.assertEqual(c.history_window.table.topLevelItem(0).text(1), "昨日.xlsx")
            c.select_content("message")
            self.assertTrue(c.history_window.isVisible())
            self.assertTrue(c.bubble.isVisible())
        finally:
            c.history_window.calendar.setSelectedDate(c.history_window.calendar.maximumDate())
            c.history_window.hide()
            c.interaction.hide()
            c.activity_history.clear()

    def test_screen_sharing_hides_dedicated_history_and_usual_bubble(self):
        c = self.controller
        c.open_choices()
        c.select_content("activity")
        self.assertTrue(c.history_window.isVisible())
        c.share()
        try:
            self.assertFalse(c.bubble.isVisible())
            self.assertFalse(c.history_window.isVisible())
            c.select_content("activity")
            self.assertFalse(c.history_window.isVisible())
        finally:
            c.share()

    def test_auto_notice_and_click_use_same_speech_window_with_four_separate_rows(self):
        c = self.controller
        c.sample()
        window_id = int(c.bubble.winId())
        width = c.bubble.width()
        self.assertFalse(c.bubble.choice_row.isVisible())
        c.resident.clicked.emit()
        self.assertEqual(int(c.bubble.winId()), window_id)
        self.assertEqual(c.bubble.width(), width)
        self.assertTrue(c.bubble.choice_row.isVisible())
        self.assertEqual([b.text() for b in c.bubble.buttons.values()], ["予定を聞く", "ファイル起動履歴を見る", "設定を開く", "一言を聞く"])
        self.assertTrue(all(not b.isCheckable() for b in c.bubble.buttons.values()))
        self.app.processEvents()
        rows = [b.geometry() for b in c.bubble.buttons.values()]
        self.assertTrue(all(a.bottom() < b.top() for a, b in zip(rows, rows[1:])))
        self.assertEqual(len({row.left() for row in rows}), 1)
        self.assertEqual(len({row.width() for row in rows}), 1)
        c.bubble.hide()

    def test_animated_frames_are_distinct_and_render_for_every_character(self):
        c = self.controller
        try:
            for key in CHARACTERS:
                frames = character_frames(key)
                self.assertEqual(len(frames), 24)
                digests = set()
                for frame in frames:
                    image = frame.toImage()
                    digests.add(hashlib.sha256(bytes(image.bits())).hexdigest())
                self.assertEqual(len(digests), 24)
                c.panel.character_buttons[key].click()
                for index in range(24):
                    self.assertTrue(frames[index].hasAlphaChannel())
                    c.resident.frame_index = index
                    self.assertFalse(c.resident.grab().isNull())
        finally:
            c.resident.frame_index = None
            c.panel.character_buttons["A"].click()

    def test_right_click_hides_and_tray_left_click_restores_without_opening_settings(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        from PySide6.QtWidgets import QSystemTrayIcon
        c = self.controller
        c.panel.hide()
        c.open_choices()
        try:
            with patch.object(QSystemTrayIcon, "isSystemTrayAvailable", return_value=True):
                QTest.mouseClick(c.resident, Qt.MouseButton.RightButton)
                self.assertTrue(c.user_hidden)
                self.assertFalse(c.resident.isVisible())
                self.assertFalse(c.bubble.isVisible())
                self.assertFalse(c.panel.isVisible())
                self.assertFalse(c.animation_timer.isActive())
                c.sample()
                c.tick()
                self.assertFalse(c.bubble.isVisible())
                c.tray_activated(QSystemTrayIcon.ActivationReason.Trigger)
                self.assertTrue(c.resident.isVisible())
                self.assertFalse(c.panel.isVisible())
                self.assertFalse(c.bubble.isVisible())
                self.assertFalse(c.user_hidden)
                c.tray_activated(QSystemTrayIcon.ActivationReason.Context)
                self.assertTrue(c.resident.isVisible())
                c.tray_activated(QSystemTrayIcon.ActivationReason.Trigger)
                self.assertFalse(c.resident.isVisible())
                c.tray_activated(QSystemTrayIcon.ActivationReason.Trigger)
                self.assertTrue(c.resident.isVisible())
                c.open_choices()
                QTest.mouseClick(c.bubble.text, Qt.MouseButton.RightButton)
                self.assertFalse(c.bubble.isVisible())
                self.assertFalse(c.resident.isVisible())
                c.tray_activated(QSystemTrayIcon.ActivationReason.Trigger)
        finally:
            c.user_hidden = False
            c.apply_visibility()

    def test_bubble_one_minute_lifetime_and_calendar_tick_does_not_restart_timer(self):
        from PySide6.QtTest import QTest
        c = self.controller
        c.sample()
        self.assertEqual(c.bubble.timer.interval(), 60000)
        c.open_choices()
        self.assertEqual(c.bubble.timer.interval(), 60000)
        c.select_content("calendar")
        self.assertEqual(c.bubble.timer.interval(), 60000)
        with patch.object(c, "select_content") as refresh:
            c.tick()
            refresh.assert_not_called()
        c.select_content("message")
        self.assertEqual(c.bubble.timer.interval(), 60000)
        # Exercise the same timer's hide path without a real one-minute wait.
        c.bubble.timer.start(1)
        QTest.qWait(20)
        self.assertFalse(c.bubble.isVisible())
        self.assertTrue(c.resident.isVisible())

    def test_no_tray_fallback_keeps_a_visible_recovery_path(self):
        from PySide6.QtWidgets import QSystemTrayIcon
        c = self.controller
        with patch.object(QSystemTrayIcon, "isSystemTrayAvailable", return_value=False):
            c.hide_character()
        self.assertTrue(c.resident.isVisible())
        self.assertTrue(c.panel.isVisible())
        self.assertFalse(c.user_hidden)
        c.panel.hide()

    def test_walk_pauses_for_interaction_and_motion_can_be_disabled(self):
        c = self.controller
        start, end = c.settings.quiet_start, c.settings.quiet_end
        c.settings.quiet_start = c.settings.quiet_end = "00:00"
        c.panel.hide()
        c.bubble.hide()
        c.motion.wait = 0
        c.motion_x = 200.0
        try:
            c.open_choices()
            c.last_motion_time = time.monotonic() - 0.05
            c.animate()
            self.assertEqual(c.motion_x, 200)
            c.interaction.hide()
            c.last_motion_time = time.monotonic() - 0.05
            with patch.object(c.resident, "underMouse", return_value=False):
                c.animate()
            self.assertNotEqual(c.motion_x, 200)
            c.panel.animation_check.click()
            self.assertFalse(c.animation_timer.isActive())
            self.assertIsNone(c.resident.frame_index)
            self.assertFalse(c.panel.walking_check.isEnabled())
        finally:
            c.settings.quiet_start, c.settings.quiet_end = start, end
            if not c.settings.animation:
                c.panel.animation_check.click()
            c.motion.wait = 15
            c.motion.distance = 0
            c.interaction.hide()


if __name__ == "__main__":
    unittest.main()
