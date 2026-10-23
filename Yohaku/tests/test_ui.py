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
from companion.core import CHARACTERS, PHRASES, Event, Notice, Settings
from companion.activity import FileObservation
from companion.dialogue import voice_for
from companion.ui import Controller, Panel, Resident, blend_frames, character_frames, character_pixmap, create_application
from PySide6.QtCore import QEvent, QPoint, QPointF, QRect, QDate, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPixmap
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QPushButton


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
        c.context_timer.stop()
        c.shutdown()
        c.tray.hide()
        c.panel.hide()
        c.resident.hide()
        c.bubble.hide()
        c.interaction.hide()
        c.history_window.hide()
        if c.editor:
            c.editor.hide()
        cls.temp.cleanup()
        if cls.old_local is None:
            os.environ.pop("LOCALAPPDATA", None)
        else:
            os.environ["LOCALAPPDATA"] = cls.old_local

    def setUp(self):
        self.controller.history_window.hide()

    def test_all_bubbles_show_body_without_a_header(self):
        bubble = self.controller.bubble
        try:
            for kind in ("calendar", "notification", "departure", "menu", "message"):
                bubble.display(Notice("表示見出し", "本文だけのメッセージ。", kind=kind))
                self.app.processEvents()
                self.assertFalse(bubble.heading.isVisible())
                self.assertFalse(any(button.text() == '×' for button in bubble.findChildren(QPushButton)))
                self.assertEqual(bubble.text.text(), "本文だけのメッセージ。")
            bubble.open_choices()
            self.assertFalse(bubble.heading.isVisible())
        finally:
            bubble.hide()

    def test_frame_transition_preserves_alpha_and_interpolates_color(self):
        a, b = QPixmap(8, 8), QPixmap(8, 8)
        a.fill(QColor(200, 0, 0, 255))
        b.fill(QColor(0, 0, 200, 255))
        for progress in (0, 0.25, 0.5, 0.75, 1):
            color = blend_frames(a, b, progress).toImage().pixelColor(4, 4)
            self.assertGreaterEqual(color.alpha(), 254)
            self.assertLessEqual(abs(color.red() - 200 * (1 - progress)), 2)
            self.assertLessEqual(abs(color.blue() - 200 * progress), 2)
        a.fill(Qt.GlobalColor.transparent)
        b.fill(Qt.GlobalColor.transparent)
        self.assertEqual(blend_frames(a, b, 0.5).toImage().pixelColor(0, 0).alpha(), 0)

    def test_compact_message_height_follows_lines_and_removes_close_button(self):
        bubble = self.controller.bubble
        try:
            bubble.open_choices()
            heights = []
            for lines in (1, 2, 3, 1):
                bubble.display(Notice('', '\n'.join(['短いメッセージです。'] * lines)))
                self.app.processEvents()
                self.assertFalse(any(button.text() == '×' for button in bubble.findChildren(QPushButton)))
                self.assertFalse(bubble.heading.isVisible())
                self.assertEqual(bubble.content_scroll.height(), bubble.text.heightForWidth(bubble.width() - 36))
                self.assertEqual(bubble.height(), bubble.content_scroll.height() + 34)
                heights.append(bubble.height())
            self.assertEqual(heights[0], heights[3])
            self.assertGreater(heights[1], heights[0])
            self.assertEqual(heights[2] - heights[1], heights[1] - heights[0])
        finally:
            bubble.hide()

    def test_clicking_message_text_and_background_closes_only_the_bubble(self):
        c = self.controller
        try:
            for widget, point in ((c.bubble.text, QPoint(8, 8)), (c.bubble.content_scroll.viewport(), QPoint(8, 8)),
                                  (c.bubble, QPoint(8, 8))):
                c.bubble.display(Notice('', 'クリックで閉じます。'))
                QTest.mouseClick(widget, Qt.MouseButton.LeftButton, pos=point)
                self.assertFalse(c.bubble.isVisible())
                self.assertFalse(c.bubble.timer.isActive())
                self.assertTrue(c.resident.isVisible())
            c.bubble.open_choices()
            QTest.mouseClick(c.bubble.text, Qt.MouseButton.LeftButton, pos=QPoint(8, 8))
            self.assertTrue(c.bubble.isVisible())
            self.assertFalse(any(button.text() == '×' for button in c.bubble.findChildren(QPushButton)))
        finally:
            c.bubble.hide()

    def test_new_mail_has_senders_without_counts_and_unread_is_only_conversation_context(self):
        c = self.controller
        old = (c.settings.outlook_enabled, c.settings.mail_enabled, c.settings.mail_show_senders,
               c.settings.quiet_start, c.settings.quiet_end, c.engine.paused_until, c.unread_count, c.unread_at)
        try:
            c.settings.outlook_enabled = c.settings.mail_enabled = c.settings.mail_show_senders = True
            c.settings.quiet_start = c.settings.quiet_end = '00:00'
            c.engine.paused_until = None
            c.bubble.hide()

            c.mail_result(c.mail_generation, {'unread_count': 12}, '')
            self.assertFalse(c.bubble.isVisible())
            self.assertEqual(c.engine.context['unread_mail_count'], 12)
            c.mail_result(c.mail_generation, {'messages': [{'kind': 'mail', 'sender': '山田'},
                                                          {'kind': 'mail', 'sender': '佐藤さん'}]}, '')
            self.assertEqual(c.bubble.kind, 'notification')
            self.assertIn('山田さん', c.bubble.text.text())
            self.assertIn('佐藤さん', c.bubble.text.text())
            self.assertIn('山田さんと佐藤さんから', c.bubble.text.text())
            self.assertNotIn('送信者：', c.bubble.text.text())
            self.assertNotRegex(c.bubble.text.text() + c.bubble.heading.text(), r'\d+件')
            c.mail_result(c.mail_generation, {'messages': [{'kind': 'mail', 'sender': '鈴木さん'}]}, '')
            self.assertNotIn('山田さん', c.bubble.text.text())
            self.assertIn('鈴木さん', c.bubble.text.text())
            self.assertRegex(c.bubble.text.text(), r'^鈴木さんから(?:新しい)?メールが(?:来|届き)ました。$')
            c.mail_result(c.mail_generation, {'messages': [{'kind': 'mail', 'sender': '田中'},
                                                          {'kind': 'meeting', 'sender': '高橋'}]}, '')
            self.assertIn('田中さんから', c.bubble.text.text())
            self.assertIn('高橋さんから会議の案内が来ました。', c.bubble.text.text())
            c.bubble.hide()
            c.unread_at = datetime.now().astimezone() - timedelta(seconds=100)
            c.refresh_context_metrics(datetime.now().astimezone())
            self.assertNotIn('unread_mail_count', c.engine.context)
            c.mail_result(c.mail_generation, {'unread_count': None}, '')
            self.assertIsNone(c.unread_count)
        finally:
            (c.settings.outlook_enabled, c.settings.mail_enabled, c.settings.mail_show_senders,
             c.settings.quiet_start, c.settings.quiet_end, c.engine.paused_until, c.unread_count, c.unread_at) = old
            c.bubble.hide()

    def test_pending_calendar_status_and_partial_read_warning_are_visible(self):
        from companion.outlook import CalendarEvents
        c = self.controller
        old = (c.events, c.connected, c.connected_at, c.settings.show_titles)
        now = datetime.now().astimezone()
        try:
            c.settings.show_titles = False
            c.received(c.generation, CalendarEvents([Event('pending-ui', now + timedelta(minutes=30),
                       now + timedelta(hours=1), response='未承諾')], complete=False, warnings=['会議案内を一部取得できません。']), '')
            self.assertIn('未承諾', c.panel.event_summary.text())
            self.assertIn('一部取得', c.panel.status_label.text())
            self.assertIn('一部取得できません', c.panel.calendar_detail.text())
            c.select_content('calendar')
            self.assertIn('[未承諾]', c.bubble.text.text())
            self.assertIn('一部の予定', c.bubble.text.text())
            self.assertIsNone(c.daily_events)
        finally:
            c.events, c.connected, c.connected_at, c.settings.show_titles = old
            c.bubble.hide()

    def test_drag_does_not_click_and_small_pointer_jitter_still_clicks(self):
        resident = Resident()
        resident.move(100, 100)
        resident.show()
        clicks, points, finishes = [], [], []
        resident.clicked.connect(lambda: clicks.append(True))
        resident.dragged.connect(points.append)
        resident.drag_finished.connect(lambda: finishes.append(True))
        try:
            QTest.mouseClick(resident, Qt.MouseButton.LeftButton, pos=QPoint(30, 30))
            self.assertEqual(len(clicks), 1)
            QTest.mousePress(resident, Qt.MouseButton.LeftButton, pos=QPoint(30, 30))
            origin = resident.press_position
            event = QMouseEvent(QEvent.Type.MouseMove, QPointF(31, 31),
                                QPointF(origin + QPoint(1, 1)), Qt.MouseButton.NoButton,
                                Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
            self.app.sendEvent(resident, event)
            QTest.mouseRelease(resident, Qt.MouseButton.LeftButton, pos=QPoint(31, 31))
            self.assertEqual(len(clicks), 2)
            self.assertEqual(points, [])
            QTest.mousePress(resident, Qt.MouseButton.LeftButton, pos=QPoint(30, 30))
            origin = resident.press_position
            for delta in (QPoint(1, 1), QPoint(80, -30)):
                event = QMouseEvent(QEvent.Type.MouseMove, QPointF(30, 30),
                                    QPointF(origin + delta), Qt.MouseButton.NoButton,
                                    Qt.MouseButton.LeftButton, Qt.KeyboardModifier.NoModifier)
                self.app.sendEvent(resident, event)
                if delta == QPoint(1, 1):
                    self.assertEqual(points, [])
            self.assertEqual(points, [QPoint(180, 70)])
            self.assertTrue(resident.dragging)
            QTest.mouseRelease(resident, Qt.MouseButton.LeftButton, pos=QPoint(30, 30))
            self.assertEqual(len(clicks), 2)
            self.assertEqual(finishes, [True])
            self.assertFalse(resident.dragging)
            self.assertIsNone(resident.press_position)
        finally:
            resident.hide()
            resident.deleteLater()

    def test_drag_position_is_clamped_saved_and_used_as_walking_height(self):
        c = self.controller
        old_x, old_y = c.motion_x, c.motion_y
        old_settings = (c.settings.position_set, c.settings.position_x, c.settings.position_y)
        area = self.app.primaryScreen().availableGeometry()
        try:
            c.drag_character(QPoint(area.left() + 120, area.top() + 50))
            c.finish_drag()
            restored = Settings.load(c.path / "settings.json")
            self.assertTrue(restored.position_set)
            self.assertEqual((restored.position_x, restored.position_y), (c.resident.x(), c.resident.y()))
            y = c.resident.y()
            c.motion_x += 20
            c.position()
            self.assertEqual(c.resident.y(), y)
            c.bubble.display(Notice("", "上端でも読めます。"))
            c.drag_character(QPoint(area.left() + 120, area.top() - 1000))
            self.assertTrue(c.bubble.tail_above)
            self.assertGreater(c.bubble.y(), c.resident.y())
            c.drag_character(QPoint(area.right() + 10000, area.bottom() + 10000))
            self.assertTrue(area.contains(c.resident.geometry()))
            c.motion_x, c.motion_y = float(restored.position_x), restored.position_y
            c.position()
            self.assertEqual((c.resident.x(), c.resident.y()), (restored.position_x, restored.position_y))
        finally:
            c.settings.position_set, c.settings.position_x, c.settings.position_y = old_settings
            c.motion_x, c.motion_y = old_x, old_y
            c.bubble.hide()
            c.position()

    def test_drag_uses_secondary_monitor_and_recovers_after_monitor_removal(self):
        from types import SimpleNamespace
        c = self.controller
        old_x, old_y = c.motion_x, c.motion_y
        primary = SimpleNamespace(availableGeometry=lambda: QRect(0, 0, 1920, 1040))
        secondary = SimpleNamespace(availableGeometry=lambda: QRect(-1280, 0, 1280, 984))
        try:
            with patch.object(c.app, "screenAt", return_value=secondary):
                c.drag_character(QPoint(-900, 300))
                self.assertEqual(c.resident.pos(), QPoint(-900, 300))
            with patch.object(c.app, "screenAt", return_value=None), patch.object(c.app, "screens", return_value=[primary]):
                c.position()
                self.assertTrue(primary.availableGeometry().contains(c.resident.geometry()))
        finally:
            c.motion_x, c.motion_y = old_x, old_y
            c.position()

    def test_history_columns_calendar_range_and_double_click_open_file(self):
        from companion.ui import HistoryWindow
        window = HistoryWindow()
        now = datetime.now().astimezone()
        path = str(Path(self.temp.name) / '長いファイル名の予算資料.xlsx')
        try:
            window.set_records([('長いファイル名の予算資料.xlsx', path, 'Excel', now.isoformat())], 'テスト')
            window.show()
            self.app.processEvents()
            self.assertEqual(window.table.columnCount(), 3)
            self.assertGreaterEqual(window.table.columnWidth(1), 300)
            self.assertEqual(window.calendar.minimumDate(), QDate.currentDate().addMonths(-3))
            item = window.table.topLevelItem(0)
            with patch('companion.ui.QDesktopServices.openUrl', return_value=True) as opener:
                point = window.table.visualItemRect(item).center()
                QTest.mouseClick(window.table.viewport(), Qt.MouseButton.LeftButton, pos=point)
                QTest.mouseDClick(window.table.viewport(), Qt.MouseButton.LeftButton, pos=point)
                opener.assert_called_once()
                self.assertEqual(opener.call_args.args[0].toLocalFile(), path)
        finally:
            window.hide()
            window.deleteLater()

    def test_calendar_today_and_selection_use_distinct_clear_colors(self):
        from companion.ui import HistoryCalendar
        calendar = HistoryCalendar()
        today = QDate.currentDate()
        calendar.setSelectedDate(today.addDays(-1))
        from PySide6.QtGui import QPainter
        colors = []
        try:
            for day in (today.addDays(-1), today):
                pixmap = QPixmap(72, 52)
                pixmap.fill(QColor('white'))
                painter = QPainter(pixmap)
                calendar.paintCell(painter, QRect(0, 0, 72, 52), day)
                painter.end()
                colors.append(pixmap.toImage().pixelColor(14, 10).name())
            self.assertEqual(colors, ['#1d4ed8', '#fde68a'])
        finally:
            calendar.deleteLater()

    def test_departure_asks_before_opening_site_and_no_url_opens_settings(self):
        c = self.controller
        old = c.settings.attendance_url
        try:
            c.settings.attendance_url = 'https://attendance.example.test/input'
            with patch('companion.ui.QDesktopServices.openUrl', return_value=True) as opener:
                c.bubble.show_departure(Notice('退勤前', 'PC起動 08:00', kind='departure'), True)
                self.assertTrue(c.bubble.departure_row.isVisible())
                opener.assert_not_called()
                c.bubble.attendance_button.click()
                opener.assert_called_once()
                self.assertEqual(opener.call_args.args[0].toString(), c.settings.attendance_url)
                self.assertFalse(c.bubble.isVisible())
            c.settings.attendance_url = ''
            with patch('companion.ui.QDesktopServices.openUrl') as opener:
                c.bubble.show_departure(Notice('退勤前', '時刻です', kind='departure'), False)
                c.bubble.attendance_button.click()
                opener.assert_not_called()
                self.assertTrue(c.panel.isVisible())
                self.assertEqual(c.panel.pages.currentIndex(), 1)
            c.bubble.display(Notice('', '通常の一言'))
            self.assertFalse(c.bubble.departure_row.isVisible())
        finally:
            c.settings.attendance_url = old
            c.panel.hide()
            c.bubble.hide()

    def test_departure_settings_validate_and_save_from_settings_ui(self):
        from dataclasses import asdict
        from PySide6.QtCore import QTime
        c = self.controller
        old = asdict(c.settings)
        p = c.panel
        try:
            p.attendance_url.setText('javascript:alert(1)')
            p.save_departure_fields()
            self.assertEqual(asdict(c.settings), old)
            self.assertIn('URL', p.departure_status.text())
            p.departure_check.setChecked(True)
            p.departure_time.setTime(QTime(17, 0))
            p.attendance_url.setText('https://attendance.example.test/input')
            p.departure_message.setPlainText('本日の勤怠を確認しましょう。')
            p.save_departure_fields()
            restored = Settings.load(c.path / 'settings.json')
            self.assertTrue(restored.departure_enabled)
            self.assertEqual(restored.departure_time, '17:00')
            self.assertEqual(restored.departure_message, '本日の勤怠を確認しましょう。')
            self.assertEqual(restored.attendance_url, 'https://attendance.example.test/input')
        finally:
            for key, value in old.items(): setattr(c.settings, key, value)
            p.departure_check.setChecked(c.settings.departure_enabled)
            p.departure_time.setTime(QTime.fromString(c.settings.departure_time, 'HH:mm'))
            p.attendance_url.setText(c.settings.attendance_url)
            p.departure_message.setPlainText(c.settings.departure_message)

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
        self.assertEqual(self.app.applicationVersion(), "0.11.2")
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
            c.resident.context_requested.emit(c.resident.pos())
            self.assertTrue(c.interaction.isVisible())
            self.assertIs(c.interaction, c.bubble)
            self.assertIn(c.bubble.text.text(), PHRASES[voice_for(c.settings)]["call"])
            window_id = int(c.bubble.winId())
            self.assertEqual(set(c.interaction.buttons), {"calendar", "activity", "settings", "hide"})
            self.assertTrue(c.interaction.timer.isActive())
            self.assertEqual(c.interaction.timer.interval(), 60000)
            c.interaction.buttons["calendar"].click()
            self.assertIn("件名は非表示", c.interaction.text.text())
            self.assertNotIn("SECRET", c.interaction.text.text())
            self.assertEqual(int(c.bubble.winId()), window_id)
            self.assertFalse(c.history_window.isVisible())
            c.resident.clicked.emit()
            self.assertEqual(int(c.bubble.winId()), window_id)
            self.assertFalse(c.history_window.isVisible())
            c.open_choices()
            c.interaction.buttons["activity"].click()
            self.assertTrue(c.history_window.isVisible())
            self.assertIn("記録オフ", c.history_window.status.text())
            self.assertNotIn("記録オフ", c.bubble.text.text())
            c.resident.clicked.emit()
            first = c.interaction.text.text()
            c.resident.clicked.emit()
            self.assertNotEqual(first, c.interaction.text.text())
            c.panel.hide()
            c.open_choices()
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
        c.resident.context_requested.emit(c.resident.pos())
        self.assertEqual(int(c.bubble.winId()), window_id)
        self.assertEqual(c.bubble.width(), width)
        self.assertTrue(c.bubble.choice_row.isVisible())
        self.assertEqual([b.text() for b in c.bubble.buttons.values()], ["予定を聞く", "ファイル起動履歴を見る", "設定を開く", "非表示にする"])
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
                self.assertTrue(c.bubble.choice_row.isVisible())
                c.bubble.buttons["hide"].click()
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
                self.assertTrue(c.bubble.choice_row.isVisible())
                c.bubble.buttons["hide"].click()
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

    def test_dialogue_editor_save_updates_running_engine_and_bubble_timer(self):
        from copy import deepcopy
        c = self.controller
        original = deepcopy(c.dialogue.data)
        try:
            c.panel.dialogue_requested.emit()
            e = c.editor
            self.assertTrue(e.isVisible())
            e.voice.setCurrentText('控えめな皮肉屋')
            e.phrase_topics.setCurrentRow(0)
            e.line_edit.setPlainText('編集画面から保存した一言です。')
            e.options['interval_minutes'].setValue(17)
            e.options['bubble_seconds'].setValue(85)
            generation, connected = c.generation, c.connected
            self.assertTrue(e.save())
            with patch.object(c.engine, 'choose', side_effect=lambda values: values[0]):
                self.assertEqual(c.engine.phrase('call'), '編集画面から保存した一言です。')
            self.assertEqual(c.settings.interval, 17)
            self.assertEqual(c.panel.interval_spin.value(), 17)
            self.assertEqual(c.generation, generation)
            self.assertEqual(c.connected, connected)
            c.open_choices()
            self.assertEqual(c.bubble.timer.interval(), 85000)
            e.hide()
            c.show_dialogue_editor()
            self.assertEqual(e.line_edit.toPlainText(), '編集画面から保存した一言です。')
            e.hide()
        finally:
            c.dialogue.save(original)
            c.dialogue_saved()
            c.bubble.hide()
            if c.editor:
                c.editor.revert()
                c.editor.hide()

    def test_quit_keeps_application_running_when_editor_cancelled(self):
        from PySide6.QtWidgets import QMessageBox
        c = self.controller
        c.show_dialogue_editor()
        c.editor.line_edit.setPlainText('保存前の内容')
        try:
            with patch.object(QMessageBox, 'question', return_value=QMessageBox.StandardButton.Cancel), patch.object(c.app, 'quit') as quit_app:
                c.request_quit()
                quit_app.assert_not_called()
            self.assertTrue(c.editor.dirty)
        finally:
            c.editor.revert()
            c.editor.hide()

    def test_left_click_is_message_right_click_is_menu_with_hide_action(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        c=self.controller
        c.panel.hide()
        QTest.mouseClick(c.resident,Qt.MouseButton.LeftButton)
        self.assertTrue(c.bubble.isVisible())
        self.assertFalse(c.bubble.choice_row.isVisible())
        self.assertEqual(c.bubble.kind,'message')
        QTest.mouseClick(c.resident,Qt.MouseButton.RightButton)
        self.assertTrue(c.bubble.choice_row.isVisible())
        self.assertNotIn('message',c.bubble.buttons)
        self.assertIn('hide',c.bubble.buttons)
        c.bubble.hide()

    def test_mail_notification_is_immediate_colored_and_privacy_modes_suppress_it(self):
        c=self.controller
        old=(c.settings.outlook_enabled,c.settings.mail_enabled,c.settings.mail_show_senders,c.settings.quiet_start,c.settings.quiet_end,c.engine.paused_until)
        try:
            c.settings.outlook_enabled=True;c.settings.mail_enabled=True;c.settings.mail_show_senders=False
            c.settings.quiet_start=c.settings.quiet_end='00:00';c.engine.paused_until=None
            c.open_choices()
            c.mail_result(c.mail_generation,{'messages':[{'kind':'mail','sender':'SECRET'}]},'')
            self.assertEqual(c.bubble.kind,'notification')
            self.assertFalse(c.bubble.choice_row.isVisible())
            self.assertNotIn('SECRET',c.bubble.text.text())
            notification_color=c.bubble.grab().toImage().pixelColor(8,45)
            c.select_content('calendar')
            self.assertEqual(c.bubble.kind,'calendar')
            self.assertNotEqual(c.bubble.grab().toImage().pixelColor(8,45),notification_color)
            c.bubble.hide()
            c.mail_result(c.mail_generation-1,{'messages':[{'kind':'mail','sender':'STALE'}]},'')
            self.assertFalse(c.bubble.isVisible())
            c.user_hidden=True
            c.mail_result(c.mail_generation,{'messages':[{'kind':'mail','sender':'TEST'}]},'')
            self.assertFalse(c.bubble.isVisible())
            c.user_hidden=False
            c.engine.paused_until=datetime.now().astimezone()+timedelta(hours=1)
            c.mail_result(c.mail_generation,{'messages':[{'kind':'mail','sender':'TEST'}]},'')
            self.assertFalse(c.bubble.isVisible())
        finally:
            c.settings.outlook_enabled,c.settings.mail_enabled,c.settings.mail_show_senders,c.settings.quiet_start,c.settings.quiet_end,c.engine.paused_until=old
            c.user_hidden=False;c.bubble.hide()

    def test_context_disable_and_stale_result_do_not_restore_aggregate_data(self):
        c=self.controller
        old=c.settings.context_enabled
        try:
            generation=c.context_generation
            c.context_received(generation,{'desktop_files':80,'open_office_files':12},'')
            self.assertEqual(c.engine.context.get('desktop_files'),80)
            c.panel.update_setting('context_enabled',False)
            self.assertNotIn('desktop_files',c.engine.context)
            self.assertNotIn('daily_active_minutes',c.engine.context)
            c.context_received(generation,{'desktop_files':80},'')
            self.assertNotIn('desktop_files',c.engine.context)
        finally:
            c.panel.update_setting('context_enabled',old)

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
