"""Safe, Unicode-aware message emphasis and durable user-selected styles."""
import os
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
from copy import deepcopy
from datetime import datetime,timedelta
from pathlib import Path
import tempfile
import unittest
from PySide6.QtGui import QTextCursor
from companion.message_format import message_html,validate_styles
from companion.message_format_ui import MessageEditor
from companion.core import Engine, Notice, Settings
from companion.one_shot import OneShotStore
from companion.reminders import ReminderStore,new_rule
from companion.ui import InteractionBubble,create_application

class MessageFormatTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=create_application()

    def test_times_durations_dates_and_mail_are_emphasized_without_html_injection(self):
        html=message_html('17:00にメール。あと1時間40分。6/15\n<img src="file:///private">')
        for word in ('17:00','メール','1時間40分','6/15'):self.assertIn('<b>'+word+'</b>',html)
        self.assertIn('&lt;img',html);self.assertNotIn('<img',html);self.assertIn('<br/>',html)
        self.assertNotIn('<b>',message_html('17:00 メール',False))

    def test_invalid_ranges_colors_and_overlapping_styles_are_rejected(self):
        valid=dict(start=0,length=2,bold=True,color='#7650a3')
        for changes in (dict(start=-1),dict(length=0),dict(length=99),dict(bold=1),dict(color='red; background:url(x)'),dict(start=True)):
            with self.subTest(changes=changes),self.assertRaises(ValueError):validate_styles('text',[dict(valid,**changes)])
        with self.assertRaises(ValueError):validate_styles('text',[valid,valid])
        self.assertEqual(validate_styles('text',[valid]),[valid])

    def test_unicode_selection_round_trips_bold_and_color_to_json_ranges(self):
        editor=MessageEditor();editor.set_message('😀確認して\nメールです')
        cursor=editor.textCursor();cursor.setPosition(2);cursor.setPosition(6,QTextCursor.MoveMode.KeepAnchor)
        editor.setTextCursor(cursor);editor.apply_format(bold=True,color='#7650a3')
        styles=editor.styles()
        self.assertEqual(styles,[dict(start=1,length=4,bold=True,color='#7650a3')])
        editor.set_message(editor.toPlainText(),styles);self.assertEqual(editor.styles(),styles)
        cursor=editor.textCursor();cursor.select(QTextCursor.SelectionType.Document);editor.setTextCursor(cursor)
        editor.apply_format(reset=True);self.assertEqual(editor.styles(),[])
        editor.hide();editor.deleteLater()

    def test_recurring_and_one_shot_store_styles_and_legacy_plain_text_is_unchanged(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary);style=[dict(start=0,length=2,bold=True,color='#b0443a')]
            recurring=ReminderStore(root/'reminders.json');rule=new_rule();rule.update(message='提出してください',message_styles=style)
            recurring.save(dict(schema_version=1,notifications=[rule]))
            self.assertEqual(ReminderStore(recurring.path).data['notifications'][0]['message_styles'],style)
            now=datetime(2026,10,1,12);when=now+timedelta(minutes=1)
            store=OneShotStore(root/'one_shot.json');store.add(when,' 提出してください ',now,[dict(style[0],start=1)])
            self.assertEqual(OneShotStore(store.path).take_due(when,with_styles=True)['message_styles'],style)
            store=OneShotStore(store.path);store.add(when,'装飾なし',now);self.assertEqual(store.take_due(when),'装飾なし')

    def test_engine_passes_selected_styles_from_both_notification_stores(self):
        with tempfile.TemporaryDirectory() as temporary:
            now=datetime(2026,10,1,12).astimezone();when=now+timedelta(minutes=1)
            engine=Engine(Settings(chatter=False,quiet_start='00:00',quiet_end='00:00'),Path(temporary)/'history.json')
            styles=[dict(start=0,length=2,bold=True,color='#7650a3')]
            engine.one_shots.add(when,'提出です',now,styles)
            notice=engine.next_notice(when,[])
            self.assertEqual(notice.styles,styles);self.assertEqual(notice.text,'提出です')
            rule=new_rule();rule.update(message='提出です',message_styles=styles,time=when.strftime('%H:%M'),condition={'kind':'daily'})
            engine.reminders.save(dict(schema_version=1,notifications=[rule]))
            self.assertEqual(engine.custom_notice(when).styles,styles)

    def test_bubble_highlights_notices_only_and_does_not_inherit_rich_text(self):
        bubble=InteractionBubble()
        try:
            for kind in ('calendar','notification','reminder','departure'):
                bubble.display(Notice('','17:00 メール',True,kind=kind))
                self.assertIn('<b>メール</b>',bubble.text.rich_html)
                self.assertEqual(bubble.text.text(),'17:00 メール')
            bubble.display(Notice('','<b>普通のひとこと</b>'))
            self.assertFalse(bubble.text.rich_html);self.assertEqual(bubble.text.text(),'<b>普通のひとこと</b>')
        finally:bubble.hide();bubble.deleteLater()

    def test_explicit_style_overrides_automatic_emphasis_only_in_its_range(self):
        html=message_html('メールは17:00',True,[dict(start=0,length=3,bold=False,color='#28744f')])
        self.assertIn('color:#28744f">メール</span>',html);self.assertIn('<b>17:00</b>',html)
