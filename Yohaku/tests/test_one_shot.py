"""Once-only persistence, overdue delivery and bubble input flow."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from companion.core import Engine, Settings
from companion.one_shot import OneShotStore, OneShotError


class OneShotLogicTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'one_shot_notifications.json'
        self.store = OneShotStore(self.path)
        self.now = datetime(2026, 10, 24, 12, 0, tzinfo=timezone.utc)
        self.when = self.now + timedelta(minutes=5)

    def test_persists_and_delivers_once_without_a_recurring_rule(self):
        self.store.add(self.when, '  確認してください。  ', self.now)
        store = OneShotStore(self.path)
        self.assertIsNone(store.take_due(self.when-timedelta(seconds=1)))
        self.assertEqual(store.take_due(self.when), '確認してください。')
        self.assertIsNone(store.take_due(self.when+timedelta(days=1)))
        self.assertIsNone(OneShotStore(self.path).take_due(self.when))
        self.assertEqual(store.data['notifications'], [])

    def test_multiple_overdue_notifications_keep_order_and_survive_long_absence(self):
        for offset in (8, 2, 4):
            self.store.add(self.now+timedelta(minutes=offset), str(offset), self.now)
        later = self.now+timedelta(days=3)
        self.assertEqual([self.store.take_due(later) for _ in range(4)], ['2','4','8',None])

    def test_invalid_inputs_and_limit_leave_previous_content_unchanged(self):
        self.store.add(self.when, '既存', self.now)
        before = self.path.read_bytes()
        for when, text in ((self.now, '過去'), (self.now-timedelta(days=1), '過去'), (self.when, '  '), (self.when, '長'*1001)):
            with self.subTest(when=when,text=text[:5]), self.assertRaises(OneShotError):
                self.store.add(when,text,self.now)
            self.assertEqual(self.path.read_bytes(),before)
        candidate = deepcopy(self.store.data)
        for at in ('2026-02-30T10:00','2026-10-24T24:00','2026-10-24T12:00+09:00',None):
            candidate['notifications'][0]['at']=at
            with self.assertRaises(OneShotError): self.store.save(candidate)
        for index in range(99): self.store.add(self.when, str(index), self.now)
        with self.assertRaises(OneShotError): self.store.add(self.when,'101',self.now)
        self.assertEqual(len(self.store.data['notifications']),100)

    def test_failed_add_or_delivery_is_atomic_and_can_retry(self):
        self.store.add(self.when,'既存',self.now)
        before=self.path.read_bytes()
        with patch('pathlib.Path.replace',side_effect=OSError('disk full')):
            with self.assertRaises(OSError):self.store.add(self.when,'追加',self.now)
            with self.assertRaises(OSError):self.store.take_due(self.when)
        self.assertEqual(self.path.read_bytes(),before)
        self.assertEqual(len(self.store.data['notifications']),1)
        self.assertFalse(self.path.with_suffix('.json.tmp').exists())
        self.assertEqual(self.store.take_due(self.when),'既存')

    def test_corrupt_file_is_retained_and_cannot_be_overwritten_by_add(self):
        self.path.write_text('{broken')
        store=OneShotStore(self.path)
        self.assertTrue(store.error)
        with self.assertRaises(OneShotError):store.add(self.when,'追加',self.now)
        self.assertIsNone(store.take_due(self.when))
        self.assertEqual(self.path.read_text(),'{broken')

    def test_engine_suppression_defers_pending_until_allowed_and_never_repeats(self):
        settings=Settings(chatter=False,quiet_start='00:00',quiet_end='00:00')
        path=self.path.parent/'history.json'
        engine=Engine(settings,path)
        engine.one_shots.add(self.when,'単発',self.now)
        self.assertIsNone(engine.next_notice(self.when,[],hidden=True))
        self.assertIsNone(engine.next_notice(self.when,[],allow_reminders=False))
        settings.quiet_start,settings.quiet_end='12:00','13:00'
        self.assertIsNone(engine.next_notice(self.when,[]))
        settings.quiet_start=settings.quiet_end='00:00'
        engine.paused_until=self.when+timedelta(hours=1)
        self.assertIsNone(engine.next_notice(self.when,[]))
        engine.paused_until=None
        notice=engine.next_notice(self.when+timedelta(days=1),[])
        self.assertEqual((notice.heading,notice.text,notice.kind),('','単発','reminder'))
        self.assertFalse(engine.reminders.data['notifications'])
        self.assertIsNone(Engine(settings,path).next_notice(self.when+timedelta(days=2),[]))

    def test_source_packaging_excludes_one_shot_contents_and_backups(self):
        spec=importlib.util.spec_from_file_location('oneshot_package',Path(__file__).parents[1]/'scripts/package_source.py')
        module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
        for suffix in ('.json','.json.bak','.json.tmp'):
            (self.path.parent/('one_shot_notifications'+suffix)).write_text('private')
        self.assertEqual(module.source_files(self.path.parent),[])


class OneShotInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from companion.ui import create_application
        cls.app=create_application()

    def setUp(self):
        from companion.ui import Controller
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        with patch.dict(os.environ,{'LOCALAPPDATA':self.temp.name}):self.c=Controller(self.app)
        c=self.c
        for timer in (c.tick_timer,c.poll_timer,c.animation_timer,c.activity_timer,c.context_timer):timer.stop()
        c.panel.hide();c.settings.quiet_start=c.settings.quiet_end='00:00'
        c.settings.departure_enabled=False;c.clear_reaction();c.user_hidden=False;c.hidden=False
        c.select_content('one_shot');self.app.processEvents()
        self.addCleanup(self.cleanup_controller)

    def cleanup_controller(self):
        c=self.c;c.bubble.hide();c.shutdown();c.tray.hide()
        for widget in (c.panel,c.resident,c.bubble,c.history_window):widget.hide()
        c.deleteLater();self.app.processEvents()

    def fill_future(self,text='打合せの準備'):
        from PySide6.QtCore import QDate,QTime
        now=datetime.now()+timedelta(days=1)
        self.c.bubble.reminder_date.setDate(QDate(now.year,now.month,now.day))
        self.c.bubble.reminder_time.setTime(QTime(10,30))
        self.c.bubble.reminder_message.setPlainText(text)

    def test_five_actions_and_today_default_with_no_auto_dismissal_or_headers(self):
        from PySide6.QtCore import QDate
        b=self.c.bubble
        self.assertEqual(list(b.buttons),['calendar','activity','settings','one_shot','hide'])
        self.assertEqual(b.reminder_date.date(),QDate.currentDate())
        self.assertFalse(b.choice_row.isVisible());self.assertTrue(b.one_shot_form.isVisible())
        self.assertFalse(b.timer.isActive());self.assertFalse(b.heading.isVisible())
        self.assertEqual(b.reminder_ok.text(),'OK');self.assertEqual(b.reminder_cancel.text(),'キャンセル')

    def test_clicking_date_text_opens_calendar_and_selection_updates_field(self):
        from PySide6.QtCore import QDate,Qt,QPoint
        from PySide6.QtTest import QTest
        field=self.c.bubble.reminder_date
        QTest.mouseClick(field.lineEdit(),Qt.MouseButton.LeftButton,pos=QPoint(10,8));self.app.processEvents()
        self.assertTrue(field.date_popup.isVisible())
        selected=QDate.currentDate().addDays(2)
        field.popup_calendar.clicked.emit(selected)
        self.assertEqual(field.date(),selected);self.assertFalse(field.date_popup.isVisible())

    def test_save_confirmation_then_due_delivery_and_restart(self):
        b=self.c.bubble;self.fill_future()
        b.reminder_ok.click();self.app.processEvents()
        self.assertFalse(b.one_shot_form.isVisible());self.assertIn('一度だけ',b.text.text())
        self.assertTrue(b.timer.isActive())
        self.assertEqual(len(OneShotStore(self.c.engine.one_shots.path).data['notifications']),1)
        self.assertEqual(self.c.engine.reminders.data['notifications'],[])
        b.dismiss();self.c.tick();self.assertFalse(b.isVisible())
        row=self.c.engine.one_shots.data['notifications'][0]
        due=datetime.fromisoformat(row['at']).astimezone()
        notice=self.c.engine.next_notice(due,[],allow_chatter=False)
        self.assertEqual(notice.text,'打合せの準備')
        self.assertIsNone(self.c.engine.next_notice(due,[],allow_chatter=False))

    def test_invalid_input_and_write_failure_keep_form_and_text_for_retry(self):
        b=self.c.bubble;self.fill_future('')
        b.reminder_ok.click();self.assertIn('通知内容',b.reminder_status.text())
        self.assertTrue(b.one_shot_form.isVisible())
        self.fill_future()
        with patch.object(self.c.engine.one_shots,'save',side_effect=OSError('denied')):b.reminder_ok.click()
        self.assertIn('保存できません',b.reminder_status.text())
        self.assertEqual(b.reminder_message.toPlainText(),'打合せの準備')
        self.assertFalse(self.c.engine.one_shots.data['notifications'])
        b.reminder_ok.click();self.assertEqual(len(self.c.engine.one_shots.data['notifications']),1)

    def test_cancel_and_escape_save_nothing_and_date_popup_hides(self):
        from PySide6.QtCore import Qt
        from PySide6.QtTest import QTest
        b=self.c.bubble;self.fill_future();b.reminder_cancel.click()
        self.assertFalse(b.isVisible());self.assertFalse(self.c.engine.one_shots.path.exists())
        self.c.select_content('one_shot');QTest.keyClick(b.reminder_message,Qt.Key.Key_Escape)
        self.assertFalse(b.isVisible());self.assertFalse(self.c.engine.one_shots.path.exists())

    def test_controls_and_body_do_not_discard_input_and_left_character_is_blocked(self):
        from PySide6.QtCore import Qt,QPoint
        from PySide6.QtTest import QTest
        b=self.c.bubble;self.fill_future()
        QTest.mouseClick(b.reminder_message.viewport(),Qt.MouseButton.LeftButton,pos=QPoint(10,10))
        QTest.mouseClick(b.text,Qt.MouseButton.LeftButton,pos=QPoint(5,5))
        self.c.show_message();self.c.tick()
        self.assertTrue(b.one_shot_form.isVisible());self.assertEqual(b.reminder_message.toPlainText(),'打合せの準備')
        self.c.open_choices();self.assertTrue(b.choice_row.isVisible());self.assertFalse(b.one_shot_form.isVisible())
        QTest.mouseClick(b.text,Qt.MouseButton.LeftButton,pos=QPoint(5,5))
        self.assertFalse(b.isVisible());self.assertFalse(self.c.user_hidden)

    def test_mail_is_immediate_in_form_without_destroying_input(self):
        c=self.c;b=c.bubble;self.fill_future()
        c.settings.outlook_enabled=True;c.settings.mail_enabled=True
        c.mail_result(c.mail_generation,{'messages':[{'kind':'mail'}]},'')
        self.assertTrue(b.one_shot_form.isVisible());self.assertTrue(b.inline_mail.isVisible())
        self.assertIn('メールが届きました。',b.inline_mail.text())
        self.assertEqual(b.reminder_message.toPlainText(),'打合せの準備')
        self.assertFalse(b.timer.isActive())


if __name__=='__main__':unittest.main()
