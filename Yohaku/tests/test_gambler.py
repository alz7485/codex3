"""Gambler voice migration, original dialogue and preservation of edited JSON."""
from copy import deepcopy
from dataclasses import asdict
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import tempfile
import unittest

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from companion.core import Engine, Settings, save_json
from companion.dialogue import (DEFAULT_PATH, DEBTOR_VOICE, GAMBLER_VOICE, LEGACY_DEBTOR_VOICE,
                               MAX_BYTES, DialogueError, DialogueStore, defaults, read_document,
                               upgrade, validate, voice_for)


def previous_document(alias=DEBTOR_VOICE):
    document = defaults()
    document.pop('gambler_voice_version')
    rows = json.loads(DEFAULT_PATH.with_name('gambler_wording_v1.json').read_text(encoding='utf-8'))
    bank = document['phrases'].pop(GAMBLER_VOICE)
    for topic, changes in rows.items():
        bank[topic] = [row['before'] for row in changes]
    document['phrases'][alias] = bank
    return document


class GamblerMigrationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name)/'dialogue.json'

    def test_both_previous_names_migrate_setting_profile_and_bank_without_losing_custom_words(self):
        for alias in (DEBTOR_VOICE, LEGACY_DEBTOR_VOICE):
            with self.subTest(alias=alias):
                old = previous_document(alias)
                old['profiles']['A']['voice'] = alias
                old['phrases'][alias]['chat'] = ['自分の手で編集した本文。', old['phrases'][alias]['chat'][0]]
                old['options']['interval_minutes'] = 23
                old['rules'][2]['enabled'] = False
                self.path.write_text(json.dumps(old, ensure_ascii=False), encoding='utf-8')
                original = self.path.read_bytes()
                store = DialogueStore(self.path)
                self.assertFalse(store.error)
                self.assertNotIn(alias, store.data['phrases'])
                self.assertEqual(store.data['phrases'][GAMBLER_VOICE]['chat'],
                                 ['自分の手で編集した本文。', defaults()['phrases'][GAMBLER_VOICE]['chat'][0]])
                self.assertEqual(store.data['rules'], old['rules'])
                self.assertEqual(store.data['options'], old['options'])
                self.assertEqual(voice_for(Settings(), store.data), GAMBLER_VOICE)
                for voice in old['phrases']:
                    if voice != alias:
                        self.assertEqual(store.data['phrases'][voice], old['phrases'][voice])
                self.assertEqual(self.path.read_bytes(), original)
                settings_path = self.path.with_name('settings.json')
                save_json(settings_path, asdict(Settings(personality=alias)))
                self.assertEqual(Settings.load(settings_path).personality, GAMBLER_VOICE)
                store.save(store.data)
                self.assertEqual(self.path.with_suffix('.json.bak').read_bytes(), original)
                self.assertEqual(read_document(self.path), store.data)

    def test_all_stock_lines_update_from_previous_release_with_six_other_voices_unchanged(self):
        old = previous_document()
        before = deepcopy(old)
        updated = validate(upgrade(old))
        self.assertEqual(updated, defaults())
        self.assertEqual(old, before)
        self.assertEqual(sum(map(len, updated['phrases'][GAMBLER_VOICE].values())), 217)

    def test_custom_topic_order_deletion_and_migration_marker_are_preserved(self):
        old = previous_document()
        bank = old['phrases'][DEBTOR_VOICE]
        original = bank['chat'][0]
        bank['chat'] = ['独自の言葉', original, 'さらに独自の言葉']
        old['rules'] = [r for r in old['rules'] if r['id'] != 'water']
        rule = deepcopy(next(r for r in old['rules'] if r['id'] == 'chat'))
        rule.update(id='custom_gambler', label='自分の話題')
        old['rules'].append(rule)
        for rows in old['phrases'].values():
            rows.pop('water')
            rows['custom_gambler'] = [original]
        updated = validate(upgrade(old))
        self.assertEqual(updated['rules'], old['rules'])
        self.assertEqual(updated['phrases'][GAMBLER_VOICE]['custom_gambler'], [original])
        self.assertEqual(updated['phrases'][GAMBLER_VOICE]['chat'][::2], ['独自の言葉', 'さらに独自の言葉'])
        self.assertNotIn('water', updated['phrases'][GAMBLER_VOICE])
        updated['phrases'][GAMBLER_VOICE]['chat'] = [original]
        self.assertEqual(upgrade(updated), updated)

    def test_ambiguous_alias_banks_are_rejected_without_replacing_original_file(self):
        document = defaults()
        document['phrases'][DEBTOR_VOICE] = deepcopy(document['phrases'][GAMBLER_VOICE])
        self.path.write_text(json.dumps(document, ensure_ascii=False), encoding='utf-8')
        original = self.path.read_bytes()
        with self.assertRaises(DialogueError):
            read_document(self.path)
        self.assertTrue(DialogueStore(self.path).error)
        self.assertEqual(self.path.read_bytes(), original)

    def test_valid_previous_size_limit_retains_content_and_saves_with_new_name(self):
        old = previous_document()
        old['padding'] = ''
        size = len(json.dumps(old, ensure_ascii=False).encode('utf-8'))
        old['padding'] = 'x' * (MAX_BYTES-size)
        self.path.write_text(json.dumps(old, ensure_ascii=False), encoding='utf-8', newline='\n')
        original = self.path.read_bytes()
        store = DialogueStore(self.path)
        self.assertFalse(store.error)
        self.assertEqual(store.data['padding'], old['padding'])
        self.assertIn(GAMBLER_VOICE, store.data['phrases'])
        self.assertEqual(self.path.read_bytes(), original)
        store.save(store.data)
        self.assertLessEqual(self.path.stat().st_size, MAX_BYTES)
        self.assertEqual(read_document(self.path), store.data)


class GamblerInterfaceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from companion.ui import create_application
        cls.app = create_application()

    def test_select_edit_render_and_save_new_voice_across_all_topics(self):
        from companion.dialogue_editor import DialogueEditor
        from companion.ui import InteractionBubble
        from companion.core import Notice
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'dialogue.json'
            store = DialogueStore(path)
            editor = DialogueEditor(store)
            bubble = InteractionBubble()
            settings = Settings(personality=GAMBLER_VOICE)
            engine = Engine(settings, path.with_name('history.json'), dialogue=store)
            engine.context.update(unread_mail_count=12, cpu_percent=87, memory_percent=88,
                until_work_end_minutes=100,
                file_name='テスト.xlsx', file_open_count=3, target_name='確認用', target_open_count=4,
                open_office_files=9, desktop_files=120, weekly_events=10, daily_events=5,
                daily_meeting_minutes=240, consecutive_meetings=3, next_meeting_gap_minutes=5,
                battery_percent=20, overlapping_meetings=2, next_meeting_duration_minutes=90,
                remaining_meeting_minutes=180, daily_active_minutes=160)
            try:
                self.assertGreaterEqual(editor.voice.findText(GAMBLER_VOICE), 0)
                self.assertEqual(editor.voice.findText(DEBTOR_VOICE), -1)
                count = 0
                for topic, lines in store.data['phrases'][GAMBLER_VOICE].items():
                    for i in range(len(lines)):
                        engine.choose = lambda values, i=i: i
                        text = engine.phrase(topic)
                        self.assertNotRegex(text, r'\{[a-z_]+\}')
                        bubble.display(Notice('', text))
                        self.app.processEvents()
                        self.assertEqual(bubble.text.text(), text)
                        self.assertEqual(bubble.content_scroll.verticalScrollBar().maximum(), 0)
                        count += 1
                self.assertEqual(count, 217)
                editor.voice.setCurrentText(GAMBLER_VOICE)
                editor.phrase_topics.setCurrentRow(0)
                editor.line_edit.setPlainText('自分で決めた、今日の一手。')
                self.assertTrue(editor.save())
                self.assertEqual(read_document(path)['phrases'][GAMBLER_VOICE]['call'][0],
                                 '自分で決めた、今日の一手。')
            finally:
                editor.dirty = False
                bubble.hide(); bubble.deleteLater()
                editor.hide(); editor.deleteLater(); self.app.processEvents()


if __name__ == '__main__':
    unittest.main()
