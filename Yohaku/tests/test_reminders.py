from copy import deepcopy
from dataclasses import asdict
from datetime import date, datetime, timedelta, timezone
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from companion.core import Engine, Event, Notice, Settings, save_json
from companion.reminders import (ReminderError, ReminderStore, due_time, matches_date,
    monthly_date, new_rule, next_occurrence, validate)


def document(*rules):
    return {'schema_version': 1, 'notifications': list(rules)}


class ReminderLogicTests(unittest.TestCase):
    def setUp(self):
        self.rule = new_rule()

    def test_month_end_covers_weekends_february_leap_year_and_year_end(self):
        condition = {'kind': 'month_end_weekday'}
        for year, month, expected in [(2026, 10, 30), (2026, 5, 29), (2026, 8, 31),
                                      (2024, 2, 29), (2020, 2, 28), (2027, 2, 26), (2023, 12, 29)]:
            with self.subTest(year=year, month=month):
                self.assertEqual(monthly_date(year, month, condition), date(year, month, expected))

    def test_cutoff_15_is_inclusive_and_only_moves_back_over_weekends(self):
        condition = {'kind': 'monthly_weekday_before', 'day': 15}
        for year, month, expected in [(2025, 2, 14), (2025, 6, 13), (2026, 10, 15)]:
            self.assertEqual(monthly_date(year, month, condition), date(year, month, expected))
            self.assertTrue(matches_date(date(year, month, expected), condition))
            self.assertFalse(matches_date(date(year, month, expected) + timedelta(days=1), condition))

    def test_absent_day_clamps_and_first_day_can_move_to_previous_month(self):
        condition = {'kind': 'monthly_weekday_before', 'day': 31}
        self.assertEqual(monthly_date(2026, 2, condition), date(2026, 2, 27))
        condition = {'kind': 'monthly_weekday_before', 'day': 1}
        self.assertEqual(monthly_date(2026, 2, condition), date(2026, 1, 30))
        self.assertTrue(matches_date(date(2026, 1, 30), condition))
        self.assertFalse(matches_date(date(2026, 2, 1), condition))
        self.assertTrue(matches_date(date(2022, 12, 30), condition))  # Jan 1, 2023 is Sunday.

    def test_regular_monthly_date_and_weekly_and_daily_have_separate_rules(self):
        self.assertTrue(matches_date(date(2026, 2, 28), {'kind': 'monthly_day', 'day': 31}))
        self.assertFalse(matches_date(date(2026, 2, 27), {'kind': 'monthly_day', 'day': 31}))
        self.assertTrue(matches_date(date(2026, 10, 23), {'kind': 'weekly', 'weekdays': [0, 4]}))
        self.assertFalse(matches_date(date(2026, 10, 24), {'kind': 'weekly', 'weekdays': [0, 4]}))
        self.assertTrue(matches_date(date(2026, 10, 24), {'kind': 'daily'}))
        # Weekdays deliberately include Japanese public holidays.
        self.assertEqual(monthly_date(2026, 11, {'kind': 'monthly_weekday_before', 'day': 23}), date(2026, 11, 23))

    def test_due_window_includes_exact_minute_but_excludes_ten_minutes(self):
        now = datetime(2026, 10, 30, 17, 0, tzinfo=timezone.utc)
        self.assertIsNone(due_time(self.rule, now - timedelta(seconds=1)))
        self.assertEqual(due_time(self.rule, now), now)
        self.assertEqual(due_time(self.rule, now + timedelta(seconds=599)), now)
        self.assertIsNone(due_time(self.rule, now + timedelta(minutes=10)))
        self.rule['enabled'] = False
        self.assertIsNone(due_time(self.rule, now))

    def test_next_occurrence_spans_year_and_handles_cutoff_one(self):
        self.assertEqual(next_occurrence(self.rule, datetime(2023, 12, 29, 17, 1)), datetime(2024, 1, 31, 17))
        self.rule['condition'] = {'kind': 'monthly_weekday_before', 'day': 1}
        self.assertEqual(next_occurrence(self.rule, datetime(2026, 1, 3)), datetime(2026, 1, 30, 17))

    def test_invalid_documents_and_types_are_rejected_without_executing_code(self):
        invalid = []
        for key, value in [('id', 'bad/path'), ('enabled', 1), ('time', '24:00'), ('time', '9:00'),
                           ('message', ''), ('message', 'x' * 1001), ('name', ''), ('condition', {'kind': []}),
                           ('condition', {'kind': '__import__("os")'}),
                           ('condition', {'kind': 'monthly_weekday_before', 'day': True}),
                           ('condition', {'kind': 'monthly_day', 'day': 32}),
                           ('condition', {'kind': 'weekly', 'weekdays': []}),
                           ('condition', {'kind': 'weekly', 'weekdays': [0, 0]})]:
            row = deepcopy(self.rule); row[key] = value
            invalid.append(document(row))
        invalid += [document(self.rule, self.rule), {'schema_version': True, 'notifications': []},
                    {'schema_version': 1, 'notifications': [new_rule() for _ in range(101)]}]
        for value in invalid:
            with self.subTest(value=str(value)[:120]), self.assertRaises(ReminderError):
                validate(value)

    def test_json_store_starts_empty_backs_up_and_keeps_runtime_on_save_failure(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'reminders.json'
            store = ReminderStore(path)
            self.assertEqual(store.data, document())
            self.assertFalse(path.exists())
            store.save(document(self.rule))
            before = path.read_bytes()
            store.save(document())
            self.assertEqual(path.with_suffix('.json.bak').read_bytes(), before)
            with patch('companion.reminders.Path.replace', side_effect=OSError('test failure')):
                with self.assertRaises(OSError): store.save(document(self.rule))
            self.assertEqual(store.data, document())
            self.assertEqual(ReminderStore(path).data, document())
            path.write_text('{broken', encoding='utf-8')
            broken = ReminderStore(path)
            self.assertTrue(broken.error)
            self.assertEqual(broken.data, document())
            self.assertEqual(path.read_text(), '{broken')


class ReminderEngineTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'history.json'
        self.settings = Settings(chatter=False, quiet_start='00:00', quiet_end='00:00')
        self.engine = Engine(self.settings, self.path)
        self.rule = new_rule()
        self.engine.reminders.save(document(self.rule))
        self.now = datetime(2026, 10, 30, 17, tzinfo=timezone.utc)

    def test_once_per_occurrence_persists_across_restart_and_allows_next_month(self):
        notice = self.engine.next_notice(self.now, [])
        self.assertEqual(notice.text, self.rule['message'])
        self.assertEqual(notice.heading, '')
        self.assertEqual(notice.kind, 'reminder')
        self.assertIsNone(self.engine.next_notice(self.now + timedelta(seconds=15), []))
        restarted = Engine(self.settings, self.path)
        self.assertIsNone(restarted.next_notice(self.now, []))
        self.assertIsNotNone(restarted.next_notice(self.now.replace(month=11, day=30), []))
        state = self.path.read_text()
        self.assertNotIn(self.rule['message'], state)
        self.assertNotIn(self.rule['name'], state)

    def test_hidden_quiet_paused_and_expired_do_not_consume_notification(self):
        self.assertIsNone(self.engine.next_notice(self.now, [], hidden=True))
        self.settings.quiet_start, self.settings.quiet_end = '17:00', '18:00'
        self.assertIsNone(self.engine.next_notice(self.now, []))
        self.settings.quiet_start = self.settings.quiet_end = '00:00'
        self.engine.paused_until = self.now + timedelta(hours=1)
        self.assertIsNone(self.engine.next_notice(self.now, []))
        self.engine.paused_until = None
        self.assertIsNone(self.engine.next_notice(self.now + timedelta(minutes=10), []))
        self.assertFalse(self.engine.custom_notified)
        self.assertIsNotNone(self.engine.next_notice(self.now, []))

    def test_calendar_has_priority_then_same_time_rules_are_delivered_one_by_one(self):
        other = new_rule(); other['message'] = '別の通知'
        self.engine.reminders.save(document(self.rule, other))
        event = Event('test-event', self.now + timedelta(minutes=5), self.now + timedelta(minutes=35))
        self.assertEqual(self.engine.next_notice(self.now, [event], connected=True).kind, 'calendar')
        self.assertIsNone(self.engine.next_notice(self.now, [], allow_reminders=False))
        self.assertFalse(self.engine.custom_notified)
        self.assertEqual(self.engine.next_notice(self.now, []).text, self.rule['message'])
        self.assertEqual(self.engine.next_notice(self.now, []).text, other['message'])
        self.assertIsNone(self.engine.next_notice(self.now, []))

    def test_daily_delivery_dates_and_deleted_rule_state_are_bounded(self):
        self.rule['condition'] = {'kind': 'daily'}
        self.engine.reminders.save(document(self.rule))
        self.assertIsNotNone(self.engine.custom_notice(self.now))
        self.assertIsNotNone(self.engine.custom_notice(self.now + timedelta(days=1)))
        self.engine.reminders.save(document())
        self.engine.persist(self.now)
        self.assertEqual(self.engine.custom_notified, {})

    def test_history_write_failure_does_not_consume_a_notification_that_was_not_shown(self):
        with patch.object(self.engine, 'persist', side_effect=OSError('disk full')):
            with self.assertRaises(OSError): self.engine.custom_notice(self.now)
        self.assertEqual(self.engine.custom_notified, {})
        self.assertIsNotNone(self.engine.custom_notice(self.now))


class ReminderInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from companion.ui import create_application
        cls.app = create_application()

    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.store = ReminderStore(Path(self.temp.name) / 'reminders.json')
        from companion.reminder_editor import ReminderEditor
        self.editor = ReminderEditor(self.store)
        self.addCleanup(self.editor.hide)

    def test_editor_saves_condition_time_message_and_next_date_without_affecting_unsaved_runtime(self):
        from PySide6.QtCore import QTime
        editor = self.editor
        editor.add_rule()
        editor.name.setText('15日締め')
        editor.kind.setCurrentIndex(editor.kind.findData('monthly_weekday_before'))
        editor.day.setValue(15)
        editor.time.setTime(QTime(16, 30))
        editor.message.setPlainText('申請を確認してください。')
        self.assertTrue(editor.day.isEnabled())
        self.assertIn('次回対象日', editor.next_date.text())
        self.assertEqual(self.store.data, document())
        self.assertTrue(editor.save())
        row = ReminderStore(self.store.path).data['notifications'][0]
        self.assertEqual(row['condition'], {'kind': 'monthly_weekday_before', 'day': 15})
        self.assertEqual(row['time'], '16:30')
        self.assertEqual(row['message'], '申請を確認してください。')
        self.assertFalse(editor.dirty)

    def test_weekly_requires_days_and_failed_save_keeps_previous_runtime(self):
        editor = self.editor
        editor.add_rule()
        self.assertTrue(editor.save())
        before = deepcopy(self.store.data)
        editor.kind.setCurrentIndex(editor.kind.findData('weekly'))
        for check in editor.weekdays: check.setChecked(False)
        self.assertFalse(editor.save())
        self.assertEqual(self.store.data, before)
        self.assertIn('曜日', editor.status.text())
        editor.weekdays[0].setChecked(True)
        self.assertTrue(editor.save())
        self.assertEqual(self.store.data['notifications'][0]['condition']['weekdays'], [0])
        with patch.object(self.store, 'save', side_effect=OSError('disk full')):
            editor.message.setPlainText('新しい編集')
            self.assertFalse(editor.save())
        self.assertNotEqual(self.store.data['notifications'][0]['message'], '新しい編集')

    def test_add_delete_revert_and_disabled_schedule_preview(self):
        editor = self.editor
        editor.add_rule()
        editor.enabled.setChecked(False)
        self.assertIn('現在は無効', editor.next_date.text())
        editor.save()
        editor.remove_rule()
        self.assertEqual(len(editor.draft['notifications']), 0)
        self.assertEqual(len(self.store.data['notifications']), 1)
        editor.revert()
        self.assertEqual(editor.rules.count(), 1)
        self.assertFalse(editor.dirty)

    def test_close_cancel_preserves_unsaved_edit_and_save_failure_prevents_closing(self):
        from PySide6.QtWidgets import QMessageBox
        editor = self.editor
        editor.show()
        editor.add_rule()
        with patch('companion.reminder_editor.QMessageBox.question', return_value=QMessageBox.StandardButton.Cancel):
            self.assertFalse(editor.close())
        self.assertTrue(editor.dirty)
        with patch('companion.reminder_editor.QMessageBox.question', return_value=QMessageBox.StandardButton.Save), patch.object(self.store, 'save', side_effect=OSError('disk full')):
            self.assertFalse(editor.close())
        with patch('companion.reminder_editor.QMessageBox.question', return_value=QMessageBox.StandardButton.Discard):
            self.assertTrue(editor.close())
        self.assertFalse(editor.dirty)

    def test_controller_registers_notifications_and_waits_for_open_bubble(self):
        from companion.ui import Controller
        with patch.dict(os.environ, {'LOCALAPPDATA': self.temp.name}):
            root = Path(self.temp.name) / 'Yohaku'
            settings = Settings(context_enabled=False, mail_enabled=False, chatter=False, animation=False,
                                quiet_start='00:00', quiet_end='00:00')
            save_json(root / 'settings.json', asdict(settings))
            controller = Controller(self.app)
        c = controller
        try:
            c.panel.hide()
            c.show_reminder_editor()
            c.reminder_editor.add_rule()
            c.reminder_editor.kind.setCurrentIndex(c.reminder_editor.kind.findData('daily'))
            now = datetime.now().astimezone().replace(second=0, microsecond=0)
            from PySide6.QtCore import QTime, Qt, QPoint
            from PySide6.QtTest import QTest
            c.reminder_editor.time.setTime(QTime(now.hour, now.minute))
            c.reminder_editor.save()
            self.assertIn('有効1件', c.panel.reminders_status.text())
            c.reminder_editor.hide()
            c.bubble.display(Notice('', '先の吹き出し'))
            c.tick()
            self.assertEqual(c.bubble.text.text(), '先の吹き出し')
            self.assertFalse(c.engine.custom_notified)
            c.bubble.hide()
            c.tick()
            self.assertEqual(c.bubble.kind, 'reminder')
            self.assertFalse(c.bubble.heading.isVisible())
            self.assertFalse(c.bubble.choice_row.isVisible())
            QTest.mouseClick(c.bubble.text, Qt.MouseButton.LeftButton, pos=QPoint(4, 4))
            self.assertFalse(c.bubble.isVisible())
            c.tick()
            self.assertFalse(c.bubble.isVisible())
            c.show_reminder_editor()
            c.user_hidden = True
            c.apply_visibility()
            self.assertFalse(c.reminder_editor.isVisible())
        finally:
            for timer in (c.tick_timer, c.poll_timer, c.animation_timer, c.activity_timer, c.context_timer): timer.stop()
            c.shutdown()
            for widget in (c.panel, c.resident, c.bubble, c.history_window): widget.hide()
            c.tray.hide()
            c.deleteLater()
            self.app.processEvents()


if __name__ == '__main__': unittest.main()
