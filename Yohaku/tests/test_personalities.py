"""Seven editable voices, legacy document upgrade, and actual selection UI."""
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import json
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import re
import tempfile
import unittest
from unittest.mock import patch

from companion.core import CHARACTERS, Engine, Settings, save_json
from companion.dialogue import (ADDED_VOICE_NAMES, AUTO_PERSONALITY, ORIGINAL_VOICE_NAMES,
    VOICE_NAMES, DialogueError, DialogueStore, defaults, read_document, upgrade, validate, voice_for)


def legacy_document():
    document=defaults()
    for voice in ADDED_VOICE_NAMES:document['phrases'].pop(voice)
    document.pop('personality_expansion_version')
    return document


class PersonalityTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'dialogue.json'

    def test_debtor_style_updates_stock_preserving_custom_text_order_and_source_file(self):
        document=defaults();document.pop('debtor_style_version')
        document['phrases']['孤高の債務者']['call']=['独自の呼びかけ','呼んだな。\n聞こう……用件を。']
        self.path.write_text(json.dumps(document,ensure_ascii=False));raw=self.path.read_bytes()
        store=DialogueStore(self.path)
        self.assertFalse(store.error);self.assertEqual(self.path.read_bytes(),raw)
        self.assertEqual(store.data['phrases']['孤高の債務者']['call'],['独自の呼びかけ','聞かせてほしい……いまの用件。'])
        store.save(store.data)
        self.assertEqual(read_document(self.path),store.data)
        self.assertEqual(self.path.with_suffix('.json.bak').read_bytes(),raw)

    def test_debtor_style_marker_preserves_later_edit_and_custom_topic_is_not_rewritten(self):
        document=defaults()
        document['phrases']['孤高の債務者']['call']=['呼んだな。\n聞こう……用件を。']
        self.assertEqual(upgrade(document),document)
        document.pop('debtor_style_version')
        custom=deepcopy(next(r for r in document['rules'] if r['id']=='chat'));custom.update(id='my_style',label='独自の話題')
        document['rules'].append(custom)
        for bank in document['phrases'].values():bank['my_style']=['呼んだな。\n聞こう……用件を。']
        result=validate(upgrade(document))
        self.assertEqual(result['phrases']['孤高の債務者']['my_style'],['呼んだな。\n聞こう……用件を。'])
        self.assertEqual(result['rules'],document['rules'])

    def test_legacy_debtor_name_migrates_settings_profile_and_edited_bank(self):
        document=defaults()
        document['phrases']['倒置法の使い手']=document['phrases'].pop('孤高の債務者')
        document['phrases']['倒置法の使い手']['chat']=['自分で編集した語り']
        document['profiles']['A']['voice']='倒置法の使い手'
        self.path.write_text(json.dumps(document,ensure_ascii=False));raw=self.path.read_bytes()
        store=DialogueStore(self.path)
        self.assertFalse(store.error);self.assertEqual(self.path.read_bytes(),raw)
        self.assertNotIn('倒置法の使い手',store.data['phrases'])
        self.assertEqual(store.data['phrases']['孤高の債務者']['chat'],['自分で編集した語り'])
        self.assertEqual(voice_for(Settings(),store.data),'孤高の債務者')
        settings_path=self.path.with_name('settings.json')
        save_json(settings_path,{'personality':'倒置法の使い手'})
        self.assertEqual(Settings.load(settings_path).personality,'孤高の債務者')

    def test_debtor_wording_updates_exact_stock_only_and_preserves_custom_lines(self):
        document=defaults();document.pop('debtor_voice_version')
        bank=document['phrases']['孤高の債務者']
        bank['smalltalk']=['待っていられる……呼ばれるまでの、静かな時間も。','独自のひとこと']
        bank['chat']=['ここで待っている。\n戻るのは、そのペースでいい……こちらへは。','独自の本文']
        result=validate(upgrade(document))
        self.assertIn('返済',result['phrases']['孤高の債務者']['chat'][0])
        self.assertEqual(result['phrases']['孤高の債務者']['chat'][1],'独自の本文')
        self.assertEqual(result['phrases']['孤高の債務者']['smalltalk'],bank['smalltalk'])

    def test_all_seven_voices_cover_every_topic_with_independent_original_phrases(self):
        document=defaults();ids={r['id'] for r in document['rules']}
        self.assertEqual(len(VOICE_NAMES),7);self.assertEqual(len(ids),64)
        self.assertEqual(tuple(document['phrases']),VOICE_NAMES)
        for voice,bank in document['phrases'].items():
            self.assertEqual(set(bank),ids)
            self.assertEqual(sum(map(len,bank.values())),181)
            for key,lines in bank.items():
                self.assertEqual(len(lines),len(set(lines)),(voice,key))
        self.assertEqual(sum(sum(map(len,bank.values())) for bank in document['phrases'].values()),1267)
        self.assertLess(max(map(len,(line for lines in document['phrases']['寡黙な先輩'].values() for line in lines))),90)

    def test_old_four_voice_document_adds_three_without_rewriting_file_or_user_edits(self):
        old=legacy_document()
        old['phrases']['控えめな皮肉屋']['chat']=['自分で編集した一言。']
        old['profiles']['A'].update(voice='冷静な案内役',description='独自の説明',tagline='独自の代表文')
        old['options']['interval_minutes']=23
        old['rules'][2]['enabled']=False
        self.path.write_text(json.dumps(old,ensure_ascii=False))
        raw=self.path.read_bytes();store=DialogueStore(self.path)
        self.assertFalse(store.error);self.assertEqual(self.path.read_bytes(),raw)
        self.assertEqual(store.data['profiles'],old['profiles'])
        self.assertEqual(store.data['rules'],old['rules'])
        self.assertEqual(store.data['options'],old['options'])
        for voice in ORIGINAL_VOICE_NAMES:self.assertEqual(store.data['phrases'][voice],old['phrases'][voice])
        store.save(store.data)
        self.assertEqual(read_document(self.path),store.data)
        self.assertEqual(self.path.with_suffix('.json.bak').read_bytes(),raw)

    def test_upgrade_respects_deleted_topics_and_copies_custom_topic_words_for_editing(self):
        old=legacy_document();old['rules']=[r for r in old['rules'] if r['id']!='water']
        custom=deepcopy(next(r for r in old['rules'] if r['id']=='chat'));custom.update(id='custom_topic',label='独自の話題')
        old['rules'].append(custom)
        for voice,bank in old['phrases'].items():
            bank.pop('water');bank['custom_topic']=['独自の本文：{work_start}']
        new=validate(upgrade(old))
        for voice in ADDED_VOICE_NAMES:
            self.assertNotIn('water',new['phrases'][voice])
            self.assertEqual(new['phrases'][voice]['custom_topic'],['独自の本文：{work_start}'])
        self.assertEqual(new['rules'],old['rules'])
        self.assertEqual(upgrade(new),new)

    def test_partial_existing_added_bank_is_preserved_and_missing_topics_are_rejected(self):
        old=legacy_document()
        old['phrases'][ADDED_VOICE_NAMES[0]]=deepcopy(defaults()['phrases'][ADDED_VOICE_NAMES[0]])
        old['phrases'][ADDED_VOICE_NAMES[0]]['call']=['独自の呼びかけ']
        upgraded=validate(upgrade(old))
        self.assertEqual(upgraded['phrases'][ADDED_VOICE_NAMES[0]]['call'],['独自の呼びかけ'])
        upgraded['phrases'][ADDED_VOICE_NAMES[1]].pop('chat')
        with self.assertRaises(DialogueError):validate(upgrade(upgraded))

    def test_missing_original_voice_is_not_silently_repaired(self):
        old=legacy_document();old['phrases'].pop(ORIGINAL_VOICE_NAMES[0])
        with self.assertRaises(DialogueError):validate(upgrade(old))

    def test_schema_one_upgrade_also_expands_to_seven(self):
        old=legacy_document();old['schema_version']=1
        upgraded=validate(upgrade(old))
        self.assertEqual(set(upgraded['phrases']),set(VOICE_NAMES))
        self.assertEqual(upgraded['schema_version'],2)

    def test_each_new_voice_persists_for_all_characters_and_auto_mapping_is_unchanged(self):
        for character in CHARACTERS:
            settings=Settings(character=character)
            self.assertEqual(voice_for(settings),defaults()['profiles'][character]['voice'])
            for voice in ADDED_VOICE_NAMES:
                settings.personality=voice
                path=self.path.with_name('settings.json');save_json(path,asdict(settings))
                reloaded=Settings.load(path)
                self.assertEqual((reloaded.character,reloaded.personality,voice_for(reloaded)),(character,voice,voice))

    def test_all_new_template_tokens_resolve_and_remaining_time_stays_readable(self):
        store=DialogueStore(self.path);settings=Settings();engine=Engine(settings,self.path.with_name('history.json'),dialogue=store,choose=lambda values:values[0])
        context={'until_work_end_minutes':100,'file_name':'テスト.xlsx','file_open_count':3,
            'target_name':'月次確認','target_open_count':4,'open_office_files':8,'desktop_files':99,
            'weekly_events':10,'daily_events':6,'unread_mail_count':12,'cpu_percent':90,'memory_percent':88,
            'daily_meeting_minutes':240,'consecutive_meetings':3,'next_meeting_gap_minutes':5,'battery_percent':20}
        engine.context.update(context)
        for rule in store.data['rules']:rule['enabled']=True
        for voice in ADDED_VOICE_NAMES:
            settings.personality=voice
            for key,lines in store.data['phrases'][voice].items():
                for index in range(len(lines)):
                    engine.choose=lambda values,i=index:i
                    text=engine.phrase(key)
                    self.assertNotRegex(text,r'\{[a-z_]+\}',(voice,key,text))
                    if key=='before_end' and 'hours_to_end' in lines[index]:self.assertIn('1時間40分',text)
            for line in store.data['phrases'][voice]['mail_received']:
                self.assertNotRegex(line,r'\{|件|さん|送信者|件名')

    def test_new_voice_obeys_existing_cadence_and_click_reaction_logic(self):
        now=datetime(2026,10,26,10,tzinfo=timezone.utc)
        for voice in ADDED_VOICE_NAMES:
            settings=Settings(personality=voice,quiet_start='00:00',quiet_end='00:00')
            store=DialogueStore(self.path)
            for rule in store.data['rules']:rule['enabled']=rule['id'] in ('chat','click_concern','click_angry')
            engine=Engine(settings,self.path.with_name('history.json'),dialogue=store,choose=lambda values:values[0])
            engine.last_display=now-timedelta(minutes=10)
            notice=engine.next_notice(now,[])
            self.assertIn(notice.text,store.data['phrases'][voice]['chat'])
            self.assertIsNone(engine.next_notice(now+timedelta(minutes=9),[]))
            for index in range(4):reaction=engine.click_reaction(index/10)
            self.assertIn(reaction.text,store.data['phrases'][voice]['click_concern'])
            self.assertEqual(reaction.expression,store.rule('click_concern')['expression'])


class PersonalityInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from companion.ui import create_application
        cls.app=create_application()

    def setUp(self):
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup)
        self.store=DialogueStore(Path(self.temp.name)/'dialogue.json')

    def test_settings_selector_has_auto_plus_seven_and_updates_quote_immediately(self):
        from companion.ui import Panel
        from PySide6.QtWidgets import QComboBox
        settings=Settings();panel=Panel(settings,self.store);self.addCleanup(panel.hide)
        selector=next(w for w in panel.findChildren(QComboBox) if w.accessibleName()=='キャラの性格')
        self.assertEqual([selector.itemText(i) for i in range(selector.count())],[AUTO_PERSONALITY,*VOICE_NAMES])
        for voice in ADDED_VOICE_NAMES:
            selector.setCurrentText(voice)
            self.assertEqual(settings.personality,voice)
            self.assertEqual(panel.personality_badge.text(),voice)
            self.assertEqual(panel.hero_quote.text(),self.store.data['phrases'][voice]['chat'][0])
            panel.update_setting('character','F')
            self.assertEqual(settings.personality,voice)
        selector.setCurrentText(AUTO_PERSONALITY)
        self.assertEqual(panel.personality_badge.text(),self.store.data['profiles']['F']['voice'])

    def test_editor_saves_each_new_voice_and_uses_it_for_character_profile(self):
        from companion.dialogue_editor import DialogueEditor
        editor=DialogueEditor(self.store);self.addCleanup(editor.hide)
        self.assertEqual([editor.voice.itemText(i) for i in range(editor.voice.count())],list(VOICE_NAMES))
        for voice in ADDED_VOICE_NAMES:
            editor.voice.setCurrentText(voice)
            editor.phrase_topics.setCurrentRow(0)
            editor.line_edit.setPlainText(voice+'の編集した呼びかけ')
            self.assertTrue(editor.save())
            self.assertEqual(read_document(self.store.path)['phrases'][voice]['call'][0],voice+'の編集した呼びかけ')
        editor.profile_key.setCurrentIndex(0);editor.profile_voice.setCurrentText(ADDED_VOICE_NAMES[0])
        self.assertTrue(editor.save())
        self.assertEqual(voice_for(Settings(),self.store.data),ADDED_VOICE_NAMES[0])
        editor.add_rule();key=editor.draft['rules'][-1]['id']
        self.assertTrue(all(key in bank for bank in editor.draft['phrases'].values()))
        self.assertTrue(editor.save());editor.dirty=False


if __name__=='__main__':unittest.main()
