"""Simulate working days and conversation context without waiting in real time."""
from datetime import datetime, timedelta, timezone
from pathlib import Path
import tempfile
import unittest

from companion.core import CHARACTERS, Engine, Event, Settings, save_json
from companion.dialogue import AUTO_PERSONALITY, PHRASES, PROFILES, voice_for


class ConversationTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'history.json'
        self.now = datetime(2026, 10, 23, 9, 0, tzinfo=timezone.utc)
        self.settings = Settings()
        self.engine = Engine(self.settings, self.path, choose=lambda values: values[0])
        self.engine.started = self.engine.last_display = self.now

    def test_eight_hour_day_uses_ten_minute_rhythm_and_varied_topics(self):
        remarks, topics = [], []
        self.assertIsNone(self.engine.next_notice(self.now + timedelta(minutes=9, seconds=59), []))
        for step in range(1, 49):
            now = self.now + timedelta(minutes=step * 10)
            remark = self.engine.next_notice(now, [])
            self.assertIsNotNone(remark)
            remarks.append(remark.text)
            topics.append(self.engine.last_category)
            self.assertIsNone(self.engine.next_notice(now + timedelta(seconds=15), []))
        self.assertEqual(topics[0], 'startup')
        self.assertGreaterEqual(len(set(remarks)), 35)
        self.assertGreaterEqual(len(set(topics)), 10)
        self.assertTrue(all(a != b for a, b in zip(remarks, remarks[1:])))
        self.assertTrue(all(a != b for a, b in zip(topics, topics[1:])))

    def test_character_has_distinct_voice_and_explicit_override_is_preserved(self):
        self.assertEqual(self.settings.personality, AUTO_PERSONALITY)
        calls = []
        for key in CHARACTERS:
            self.settings.character = key
            self.assertEqual(voice_for(self.settings), PROFILES[key][0])
            calls.append(self.engine.phrase('call'))
        self.assertEqual(len(set(calls)), len(CHARACTERS))
        self.settings.personality = '冷静な案内役'
        self.settings.character = 'E'
        self.assertIn(self.engine.phrase('call'), PHRASES['冷静な案内役']['call'])

    def test_time_weekday_and_session_context_are_eligible_only_when_relevant(self):
        self.engine.session_spoken = True
        for target, now in [('morning', self.now), ('lunch', self.now.replace(hour=12)),
                            ('afternoon', self.now.replace(hour=15)), ('evening', self.now.replace(hour=17)),
                            ('friday', self.now), ('monday', self.now + timedelta(days=3)),
                            ('weekend', self.now + timedelta(days=1)), ('long_session', self.now + timedelta(hours=2))]:
            with self.subTest(target=target):
                self.engine.category_last.clear()
                self.engine.last_category = None
                self.engine.choose = lambda choices: target if target in choices else choices[0]
                self.engine.conversation(now)
                self.assertEqual(self.engine.last_category, target)
        self.engine.category_last.clear()
        self.engine.last_category = None
        self.engine.choose = lambda choices: 'lunch' if 'lunch' in choices else choices[0]
        self.engine.conversation(self.now)
        self.assertNotEqual(self.engine.last_category, 'lunch')

    def test_calendar_context_requires_connection_and_has_topic_cooldown(self):
        self.engine.session_spoken = True
        now = self.now + timedelta(hours=2)
        event = Event('opaque', now + timedelta(minutes=20), now + timedelta(minutes=50), 'PRIVATE_TITLE')
        for target, instant in [('before_meeting', now), ('after_meeting', event.end + timedelta(minutes=1))]:
            self.engine.choose = lambda choices: target if target in choices else choices[0]
            remark = self.engine.conversation(instant, [event], connected=True)
            self.assertEqual(self.engine.last_category, target)
            self.assertNotIn('PRIVATE_TITLE', remark.text)
            self.engine.conversation(instant + timedelta(minutes=10), [event], connected=True)
            self.assertNotEqual(self.engine.last_category, target)
            self.engine.category_last.clear()
            self.engine.conversation(instant, [event], connected=False)
            self.assertNotEqual(self.engine.last_category, target)

    def test_manual_remarks_rotate_and_repeat_history_survives_restart(self):
        self.engine.session_spoken = True
        self.engine.choose = lambda choices: 'chat' if 'chat' in choices else choices[0]
        remarks = [self.engine.conversation(self.now).text for _ in range(18)]
        self.assertTrue(all(a != b for a, b in zip(remarks, remarks[1:])))
        before = self.engine.phrase('chat')
        self.engine.persist(self.now)
        restarted = Engine(self.settings, self.path, choose=lambda values: values[0])
        self.assertNotEqual(before, restarted.phrase('chat'))

    def test_upgrade_adopts_new_rhythm_once_and_keeps_new_custom_interval(self):
        path = Path(self.temp.name) / 'settings.json'
        for version in (None, 'broken', 1):
            save_json(path, {'interval': 90, 'personality': '冷静な案内役', 'conversation_version': version})
            settings = Settings.load(path)
            self.assertEqual(settings.interval, 10)
            self.assertEqual(settings.personality, '冷静な案内役')
        save_json(path, {'interval': 30, 'conversation_version': 2})
        self.assertEqual(Settings.load(path).interval, 30)

    def test_pause_quiet_hidden_and_meeting_do_not_queue_casual_remarks(self):
        due = self.now + timedelta(minutes=10)
        for kwargs in ({'hidden': True}, {'allow_chatter': False}):
            self.assertIsNone(self.engine.next_notice(due, [], **kwargs))
        self.engine.paused_until = due + timedelta(hours=1)
        self.assertIsNone(self.engine.next_notice(due, []))
        self.engine.paused_until = None
        self.assertIsNone(self.engine.next_notice(due.replace(hour=18), []))
        event = Event('ongoing', due - timedelta(minutes=2), due + timedelta(minutes=30))
        self.assertIsNone(self.engine.next_notice(due, [event], connected=True))
        self.assertIsNotNone(self.engine.next_notice(event.end, [event], connected=True))
        self.assertIsNone(self.engine.next_notice(event.end + timedelta(seconds=15), []))


if __name__ == '__main__':
    unittest.main()
