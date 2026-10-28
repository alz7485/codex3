"""Functional speech follows saved personalities without losing operation facts."""
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime
import json
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import QDate,QTime,Qt
from PySide6.QtWidgets import QSystemTrayIcon
from companion.core import Engine,Settings,save_json
from companion.dialogue import AUTO_PERSONALITY,DialogueError,DialogueStore,VOICE_NAMES,defaults,document_size,read_document
from companion.dialogue_editor import DialogueEditor
from companion.system_dialogue import SYSTEM_LABELS,render_system_phrase,system_fields
from companion.ui import Controller,InteractionBubble,create_application


class SystemDialogueTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=create_application()
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.root=Path(self.temp.name)
        self.store=DialogueStore(self.root/'dialogue.json');self.settings=Settings(personality='馴れ馴れしい関西弁')
        self.engine=Engine(self.settings,self.root/'history.json',dialogue=self.store,choose=lambda xs:xs[0])
    def test_all_topics_cover_all_voices_and_keep_factual_placeholders_and_literal_file_names(self):
        values=dict(when='2026/10/28 17:45',level='12',name='テスト実績',time='17:46',detail='入力を確認',path='C:/'+('長い名前'*40)+'/{level}.txt')
        for voice in VOICE_NAMES:
            for key in SYSTEM_LABELS:
                text=render_system_phrase(voice,key,self.store.data,values)
                for field in system_fields(key):self.assertIn(values[field],text,(voice,key))
                self.assertTrue(text.strip())
        self.assertIn('どない',self.engine.system_phrase('drop_action'))
        self.settings.personality='寡黙な先輩';self.assertEqual(self.engine.system_phrase('one_shot_prompt'),'日時と内容を。')
        self.settings.personality='孤高のギャンブラー';self.assertIn('手札',self.engine.system_phrase('shelf_items'))
        self.settings.personality=AUTO_PERSONALITY;self.store.data['profiles']['A']['voice']='馴れ馴れしい関西弁'
        self.assertIn('どない',self.engine.system_phrase('drop_action'))
    def test_existing_and_edited_documents_reload_without_overwriting_custom_phrases_or_source(self):
        old=defaults();old.pop('system_phrases');old['phrases']['寡黙な先輩']['call']=['自分の呼びかけ。']
        path=self.root/'old.json';path.write_text(json.dumps(old,ensure_ascii=False),encoding='utf-8');before=path.read_bytes()
        loaded=read_document(path);self.assertIn('system_phrases',loaded);self.assertEqual(path.read_bytes(),before)
        self.assertEqual(loaded['phrases']['寡黙な先輩']['call'],['自分の呼びかけ。'])
        loaded['system_phrases']['馴れ馴れしい関西弁']['one_shot_saved']=['{when}、覚えとくで。']
        self.store.save(loaded);restored=DialogueStore(self.store.path)
        self.assertEqual(restored.data,loaded)
    def test_size_limited_legacy_document_keeps_runtime_fallback_without_forcing_new_rules_or_writes(self):
        old=defaults();old.pop('system_phrases');path=self.root/'compact.json'
        raw=json.dumps(old,ensure_ascii=False,separators=(',',':'));path.write_text(raw,encoding='utf-8')
        with patch('companion.dialogue.MAX_BYTES',document_size(old)+1):loaded=read_document(path)
        self.assertNotIn('system_phrases',loaded);self.assertEqual(len(loaded['rules']),len(old['rules']))
        self.assertEqual(path.read_text(),raw)
        self.assertIn('どない',render_system_phrase('馴れ馴れしい関西弁','drop_action',loaded))
    def test_invalid_banks_or_removed_required_information_do_not_replace_saved_content(self):
        self.store.save(self.store.data);original=self.store.path.read_bytes()
        for mutate in (
            lambda d:d['system_phrases'].pop('寡黙な先輩'),
            lambda d:d['system_phrases']['寡黙な先輩'].update(growth_level=['上がった。']),
            lambda d:d['system_phrases']['寡黙な先輩'].update(one_shot_saved=['{when} {unsupported}']),
            lambda d:d['system_phrases']['寡黙な先輩'].update(drop_action=['']),
        ):
            draft=deepcopy(self.store.data);mutate(draft)
            with self.assertRaises(DialogueError):self.store.save(draft)
            self.assertEqual(self.store.path.read_bytes(),original)
    def test_editor_updates_system_speech_and_keeps_ordinary_rules_and_phrases(self):
        editor=DialogueEditor(self.store)
        try:
            original=deepcopy(editor.draft['phrases']);rules=deepcopy(editor.draft['rules'])
            editor.voice.setCurrentText('馴れ馴れしい関西弁')
            row=next(n for n in range(editor.phrase_topics.count()) if editor.phrase_topics.item(n).data(Qt.ItemDataRole.UserRole)=='one_shot_saved')
            editor.phrase_topics.setCurrentRow(row);self.assertIn('{when}',editor.phrase_hint.text())
            editor.line_edit.setPlainText('{when}、任しといてや。');editor.add_line()
            self.assertEqual(editor.line_edit.toPlainText(),'{when}、任しといてや。');editor.remove_line()
            self.assertTrue(editor.save(),editor.status.text())
            self.assertEqual(self.store.data['phrases'],original);self.assertEqual(self.store.data['rules'],rules)
            self.assertEqual(self.engine.system_phrase('one_shot_saved',{'when':'明日17:00'}),'明日17:00、任しといてや。')
        finally:editor.dirty=False;editor.hide();editor.deleteLater();self.app.processEvents()
    def test_bubble_prompts_and_validation_use_current_voice_and_preserve_the_form(self):
        bubble=InteractionBubble();bubble.system_phrase=self.engine.system_phrase
        try:
            file=self.root/'test.pdf';file.write_bytes(b'synthetic')
            for voice in VOICE_NAMES:
                self.settings.personality=voice
                for stage,key in [('action','drop_action'),('destination','drop_destination'),('paper','drop_paper')]:
                    bubble.show_drop_stage(file,stage);self.assertIn(self.engine.system_phrase(key),bubble.text.text())
                    self.assertIn(file.name,bubble.text.text())
                bubble.show_shelf([]);self.assertEqual(bubble.text.text(),self.engine.system_phrase('shelf_empty'))
                bubble.show_one_shot_form();self.assertEqual(bubble.text.text(),self.engine.system_phrase('one_shot_prompt'))
                bubble.reminder_message.setPlainText('編集途中の内容');bubble.reminder_time.setText('99:99');bubble.refresh_one_shot_bounds()
                self.assertFalse(bubble.reminder_ok.isEnabled());self.assertEqual(bubble.reminder_status.text(),self.engine.system_phrase('one_shot_time_invalid'))
                self.assertEqual(bubble.reminder_message.toPlainText(),'編集途中の内容')
        finally:bubble.hide();bubble.deleteLater();self.app.processEvents()
    def test_departure_default_follows_voice_but_custom_message_and_boot_facts_stay_literal(self):
        self.settings.departure_enabled=True;self.settings.departure_time='17:00';self.settings.departure_weekdays=False
        self.settings.quiet_start=self.settings.quiet_end='00:00';now=datetime(2026,10,28,17,0).astimezone()
        notice=self.engine.departure_notice(now,uptime_provider=lambda:3600)
        self.assertIn(self.engine.system_phrase('departure_default'),notice.text);self.assertIn('PC起動：10/28 16:00',notice.text)
        self.settings.departure_message='ユーザーが登録した文章 {literal}';self.engine.departure_date=''
        notice=self.engine.departure_notice(now,uptime_provider=lambda:None)
        self.assertTrue(notice.text.startswith(self.settings.departure_message));self.assertIn(self.engine.system_phrase('uptime_unavailable'),notice.text)
    def test_actual_controller_registration_history_shelf_file_result_and_growth_follow_personality(self):
        save_json(self.root/'Data/settings.json',asdict(Settings(context_enabled=False,mail_enabled=False,personality='馴れ馴れしい関西弁',quiet_start='00:00',quiet_end='00:00')))
        with patch.object(QSystemTrayIcon,'isSystemTrayAvailable',return_value=True):host=Controller(self.app,data_path=self.root/'Data')
        try:
            for timer in (host.tick_timer,host.poll_timer,host.animation_timer,host.activity_timer,host.context_timer,host.growth_service.timer):timer.stop()
            host.panel.hide();host.select_content('one_shot');host.bubble.reminder_message.setPlainText('自分の通知')
            host.bubble.reminder_date.setDate(QDate.currentDate().addDays(1));host.bubble.reminder_time.setTime(QTime(9,0))
            host.save_one_shot()
            self.assertIn('一回だけ知らせるで',host.bubble.text.text());self.assertEqual(host.engine.one_shots.data['notifications'][0]['message'],'自分の通知')
            host.show_today_history();self.assertIn('今日の記録はまだないで',host.bubble.text.text())
            host.shelf_service.show();self.assertIn('預かってへんで',host.bubble.text.text())
            host.file_drop_service.finished({'printed':1},'');self.assertIn('送ったで',host.bubble.text.text())
            host.bubble.hide();host.resident.clear_props();host.growth_service.notifications=[dict(kind='level',level=4,character='A')]
            with patch('companion.growth_ui.session_locked',return_value=False):notice=host.growth_service.next_notice(datetime.now().astimezone())
            self.assertIn('Lv.4になったで',notice.text)
        finally:
            host.shutdown();host.tray.hide()
            for w in (host.panel,host.resident,host.bubble,host.history_window):w.hide()
            host.deleteLater();self.app.processEvents()
