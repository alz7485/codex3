from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from companion.core import Engine, Event, Settings
from companion.dialogue import DialogueError, DialogueStore, defaults, matches, read_document


class DialogueJsonTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'dialogue.json'
        self.store = DialogueStore(self.path)
        self.settings = Settings()
        self.engine = Engine(self.settings, self.path.with_name('history.json'), choose=lambda xs: xs[0], dialogue=self.store)
        self.now = datetime(2026, 10, 23, 10, tzinfo=timezone.utc)
        self.engine.started = self.now - timedelta(hours=2)
        self.engine.last_display = self.now
        self.engine.session_spoken = True

    def test_utf8_multiline_save_reload_and_live_engine(self):
        draft = deepcopy(self.store.data)
        voice = draft['profiles']['A']['voice']
        draft['phrases'][voice]['call'] = ['お呼びですか？\nご用件をどうぞ。']
        self.store.save(draft)
        self.assertEqual(self.engine.phrase('call'), 'お呼びですか？\nご用件をどうぞ。')
        restarted = DialogueStore(self.path)
        self.assertEqual(restarted.data, draft)
        self.assertIn('お呼びですか', self.path.read_text())

    def test_profile_mapping_and_action_responses_use_saved_json(self):
        draft = deepcopy(self.store.data)
        draft['profiles']['A'].update(voice='冷静な案内役', description='カスタムの性格説明', tagline='カスタムの代表的な一言')
        draft['phrases']['冷静な案内役']['settings_open'] = ['保存した設定案内です。']
        self.store.save(draft)
        self.assertEqual(self.engine.phrase('settings_open'), '保存した設定案内です。')
        self.assertEqual(DialogueStore(self.path).data['profiles']['A']['description'], 'カスタムの性格説明')

    def test_invalid_fields_reject_without_changing_file_or_active_data(self):
        self.store.save(self.store.data)
        original = self.path.read_bytes()
        mutations = [lambda d: d['rules'][0].update(expression=[]),
                     lambda d: d['rules'][0].update(condition={'kind': []}),
                     lambda d: d['options'].update(interval_minutes=True),
                     lambda d: d['options'].update(bubble_seconds=0),
                     lambda d: d['rules'][3].update(condition={'kind': 'weekday', 'days': []}),
                     lambda d: d['phrases']['控えめな皮肉屋'].update(call=['']),
                     lambda d: d.update(schema_version=99)]
        for mutate in mutations:
            draft = deepcopy(self.store.data)
            mutate(draft)
            with self.assertRaises(DialogueError): self.store.save(draft)
            self.assertEqual(self.path.read_bytes(), original)
            self.assertEqual(self.store.data, json.loads(original))

    def test_backup_and_failed_replace_keep_active_and_saved_document(self):
        self.store.save(self.store.data)
        first = deepcopy(self.store.data)
        updated = deepcopy(first)
        updated['options']['bubble_seconds'] = 90
        self.store.save(updated)
        self.assertEqual(read_document(self.path.with_suffix('.json.bak')), first)
        with patch.object(Path, 'replace', side_effect=OSError('read only')):
            with self.assertRaises(OSError): self.store.save(first)
        self.assertEqual(self.store.data, updated)
        self.assertEqual(read_document(self.path), updated)
        self.assertFalse(self.path.with_suffix('.json.tmp').exists())

    def test_bad_startup_json_uses_defaults_and_preserves_original(self):
        self.path.write_text('{broken', encoding='utf-8')
        store = DialogueStore(self.path)
        self.assertTrue(store.error)
        self.assertEqual(store.data, defaults())
        self.assertEqual(self.path.read_text(), '{broken')

    def test_custom_rule_time_range_weekdays_and_connection_boundaries(self):
        base = {'condition': {'kind': 'time_range', 'start': '23:00', 'end': '02:00'}}
        for hour, expected in ((23, True), (0, True), (2, False), (22, False)):
            self.assertEqual(matches(base, self.now.replace(hour=hour), self.now, False, [], False), expected)
        base['condition'] = {'kind': 'weekday', 'days': [4]}
        self.assertTrue(matches(base, self.now, self.now, False, [], False))
        self.assertFalse(matches(base, self.now + timedelta(days=1), self.now, False, [], False))
        event = Event('opaque', self.now + timedelta(minutes=20), self.now + timedelta(minutes=50))
        base['condition'] = {'kind': 'before_meeting', 'minimum_minutes': 10, 'maximum_minutes': 20}
        self.assertTrue(matches(base, self.now, self.now, False, [event], True))
        self.assertFalse(matches(base, self.now, self.now, False, [event], False))
        self.assertFalse(matches(base, self.now + timedelta(minutes=10), self.now, False, [event], True))

    def test_json_controls_cadence_cooldown_and_disabling_all_topics(self):
        draft = deepcopy(self.store.data)
        draft['options']['interval_minutes'] = 3
        for rule in draft['rules']:
            rule['enabled'] = rule['id'] == 'chat'
            if rule['id'] == 'chat': rule['cooldown_minutes'] = 15
        self.store.save(draft)
        self.assertIsNone(self.engine.next_notice(self.now + timedelta(minutes=2), []))
        self.assertIsNotNone(self.engine.next_notice(self.now + timedelta(minutes=3), []))
        self.assertIsNone(self.engine.next_notice(self.now + timedelta(minutes=6), []))
        self.assertIsNotNone(self.engine.next_notice(self.now + timedelta(minutes=18), []))
        draft['rules'][2]['enabled'] = False
        self.store.save(draft)
        self.assertIsNone(self.engine.conversation(self.now + timedelta(hours=1)))
        self.assertIsNone(self.engine.next_notice(self.now + timedelta(hours=1), []))

    def test_json_controls_reminder_lead_time_and_expression(self):
        draft = deepcopy(self.store.data)
        draft['options']['meeting_lead_minutes'] = 3
        reminder = next(r for r in draft['rules'] if r['id'] == 'meeting')
        reminder['expression'] = 'think'
        self.store.save(draft)
        event = Event('opaque', self.now + timedelta(minutes=4), self.now + timedelta(minutes=30))
        self.assertIsNone(self.engine.next_notice(self.now, [event], connected=True))
        notice = self.engine.next_notice(self.now + timedelta(minutes=1), [event], connected=True)
        self.assertTrue(notice.important)
        self.assertEqual(notice.expression, 'think')

    def test_weighted_selection_uses_json_weights(self):
        draft = deepcopy(self.store.data)
        draft['options']['selection_policy'] = 'weighted'
        for rule in draft['rules']:
            rule['enabled'] = rule['id'] in ('chat', 'focus')
            rule['weight'] = 7 if rule['id'] == 'focus' else 1
        self.store.save(draft)
        pools = []
        def choose(values):
            if isinstance(values[0], str): pools.append(values)
            return values[0]
        self.engine.choose = choose
        self.engine.conversation(self.now)
        self.assertEqual(pools[0].count('focus'), 7)
        self.assertEqual(pools[0].count('chat'), 1)

    def test_unread_topic_is_a_slightly_prioritized_normal_conversation(self):
        draft = deepcopy(self.store.data)
        for rule in draft['rules']:
            rule['enabled'] = rule['id'] in ('chat', 'mail_unread')
        self.store.save(draft)
        self.engine.session_spoken = True
        self.engine.context['unread_mail_count'] = 4
        self.engine.conversation(self.now)
        self.assertEqual(self.engine.last_category, 'chat')
        self.engine.context['unread_mail_count'] = 12
        self.engine.last_category = 'other'
        self.engine.category_last['mail_unread'] = self.now - timedelta(hours=2)
        self.engine.category_last.pop('chat', None)
        pools = []
        def choose(values):
            if isinstance(values[0], str):
                pools.append(values)
                return 'mail_unread' if 'mail_unread' in values else values[0]
            return values[0]
        self.engine.choose = choose
        notice = self.engine.conversation(self.now)
        self.assertEqual(pools[0].count('chat'), 1)
        self.assertEqual(pools[0].count('mail_unread'), 2)
        self.assertIn('12', notice.text)
        self.assertEqual(notice.kind, 'message')
        self.assertFalse(notice.important)
        self.engine.conversation(self.now + timedelta(minutes=10), manual=False)
        self.assertNotEqual(self.engine.last_category, 'mail_unread')

    def test_version_two_mail_upgrade_preserves_other_edits_and_user_deletion(self):
        from companion.dialogue import upgrade
        old = deepcopy(self.store.data)
        old.pop('content_revision', None)
        old['rules'] = [r for r in old['rules'] if r['id'] != 'mail_unread']
        for bank in old['phrases'].values():
            bank.pop('mail_unread', None)
            bank['mail_received'] = ['新着メールが{mail_count}件あります。']
            bank['chat'] = ['編集したセリフです。']
        upgraded = upgrade(old)
        self.assertEqual(upgraded['content_revision'], 3)
        self.assertIn('mail_unread', [r['id'] for r in upgraded['rules']])
        for bank in upgraded['phrases'].values():
            self.assertEqual(bank['chat'], ['編集したセリフです。'])
            self.assertNotIn('{mail_count}', bank['mail_received'][0])
        upgraded['rules'] = [r for r in upgraded['rules'] if r['id'] != 'mail_unread']
        self.assertNotIn('mail_unread', [r['id'] for r in upgrade(upgraded)['rules']])

    def test_mail_sentence_upgrade_keeps_custom_text_and_the_sender_is_not_persisted(self):
        from companion.dialogue import upgrade
        draft = deepcopy(self.store.data)
        draft.pop('mail_wording_version', None)
        bank = draft['phrases']['控えめな皮肉屋']
        bank['mail_received'] = ['メールが届きました。読む時間にも余白をどうぞ。', '自分で編集した案内です。']
        upgraded = upgrade(draft)
        self.assertEqual(upgraded['phrases']['控えめな皮肉屋']['mail_received'][0], 'メールが届きました。')
        self.assertEqual(upgraded['phrases']['控えめな皮肉屋']['mail_received'][1], '自分で編集した案内です。')
        self.store.save(upgraded)
        self.engine.choose = lambda values: values[0]
        self.assertEqual(self.engine.phrase('mail_received', {'mail_from': '山田さんから'}), 'メールが届きました。')
        self.engine.persist(self.now)
        self.assertNotIn('山田', self.engine.history_path.read_text())
        self.assertNotIn('山田', self.store.path.read_text())

    def test_naming_upgrade_replaces_stock_self_references_and_keeps_custom_json(self):
        from companion.dialogue import LEGACY_SELF_REFERENCES, upgrade
        legacy = deepcopy(self.store.data)
        legacy.pop('naming_version')
        voice = legacy['profiles']['A']['voice']
        legacy['phrases'][voice]['call'] = [
            'はい、余白の出番ですか？', '自分で書いた余白の呼びかけです。', '予定に余白がありますね。']
        legacy['profiles']['A']['tagline'] = '自分の代表的な一言'
        legacy['options']['interval_minutes'] = 23
        self.path.write_text(json.dumps(legacy, ensure_ascii=False), encoding='utf-8')
        original_bytes = self.path.read_bytes()
        restored = DialogueStore(self.path)
        self.assertFalse(restored.error)
        expected = deepcopy(legacy)
        expected['naming_version'] = 1
        expected['phrases'][voice]['call'][0] = LEGACY_SELF_REFERENCES['はい、余白の出番ですか？']
        self.assertEqual(restored.data, expected)
        self.assertEqual(self.path.read_bytes(), original_bytes)
        self.assertEqual(upgrade(restored.data), restored.data)
        restored.save(restored.data)
        self.assertEqual(self.path.with_suffix('.json.bak').read_bytes(), original_bytes)
        # Later deliberate edits of the stock wording must survive subsequent loads.
        restored.data['phrases'][voice]['call'][0] = 'はい、余白の出番ですか？'
        restored.save(restored.data)
        self.assertEqual(DialogueStore(self.path).data['phrases'][voice]['call'][0], 'はい、余白の出番ですか？')
