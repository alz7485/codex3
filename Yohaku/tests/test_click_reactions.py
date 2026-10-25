"""Exercise click bursts, JSON migrations and face recovery with synthetic input."""
from copy import deepcopy
from pathlib import Path
import tempfile
import unittest

from companion.core import Engine, Settings
from companion.dialogue import DialogueError, defaults, upgrade, validate
from companion.motion import ClickReactions, Motion


class ClickReactionTests(unittest.TestCase):
    def test_burst_escalates_and_recovers_only_after_a_pause(self):
        options = defaults()['options']
        clicks = ClickReactions()
        self.assertEqual([clicks.click(i * .2, options) for i in range(7)],
                         [None, None, None, 'click_concern', None, None, 'click_angry'])
        # The rolling window empties, but continuing to poke keeps the mood.
        self.assertIsNone(clicks.click(8, options))
        self.assertIsNone(clicks.click(18, options))
        self.assertEqual(len(clicks.clicks), 1)

    def test_spaced_clicks_disabled_reactions_and_clock_rollback(self):
        options = defaults()['options']
        clicks = ClickReactions()
        self.assertTrue(all(clicks.click(i * 6, options) is None for i in range(12)))
        for i in range(7): clicks.click(100 + i * .1, options)
        self.assertEqual(clicks.stage, 2)
        options['click_reactions'] = False
        self.assertIsNone(clicks.click(102, options))
        self.assertEqual(clicks.stage, 0)
        options['click_reactions'] = True
        self.assertIsNone(clicks.click(1, options))

    def test_custom_thresholds_and_bounded_session_memory(self):
        options = defaults()['options']
        options.update(click_window_seconds=2, click_concern_count=2, click_angry_count=3, click_recovery_seconds=4)
        clicks = ClickReactions()
        self.assertIsNone(clicks.click(0, options))
        self.assertEqual(clicks.click(.1, options), 'click_concern')
        self.assertEqual(clicks.click(.2, options), 'click_angry')
        for i in range(1000): clicks.click(1 + i * .001, options)
        self.assertEqual(len(clicks.clicks), 60)
        self.assertIsNone(clicks.click(6, options))

    def test_each_character_uses_editable_reaction_lines_and_expression(self):
        with tempfile.TemporaryDirectory() as tmp:
            for character in 'ABE':
                engine = Engine(Settings(character=character), Path(tmp) / 'history.json', choose=lambda items: items[0])
                for i in range(3): self.assertIsNone(engine.click_reaction(i * .1))
                concern = engine.click_reaction(.3)
                self.assertEqual(concern.expression, 'troubled')
                angry = [engine.click_reaction(.4 + i * .1) for i in range(3)][-1]
                self.assertEqual(angry.expression, 'angry')
                self.assertEqual(angry.kind, 'message')
                engine.dialogue.rule('click_angry')['enabled'] = False
                self.assertIsNone(engine.click_reaction(.8))
                self.assertIsNone(engine.click_reaction(11))

    def test_old_json_upgrades_once_without_overwriting_custom_content(self):
        old = defaults()
        old.pop('click_reactions_version')
        old['options'] = {k: v for k, v in old['options'].items() if not k.startswith('click_')}
        old['rules'] = [r for r in old['rules'] if not r['id'].startswith('click_')]
        for bank in old['phrases'].values():
            bank.pop('click_concern'); bank.pop('click_angry')
            bank['chat'][0] = '自分で編集した文'
        migrated = validate(upgrade(old))
        self.assertNotIn('click_reactions_version', old)
        self.assertTrue(migrated['options']['click_reactions'])
        self.assertTrue(all(b['chat'][0] == '自分で編集した文' for b in migrated['phrases'].values()))
        migrated['options']['click_concern_count'] = 6
        next(r for r in migrated['rules'] if r['id'] == 'click_angry')['enabled'] = False
        self.assertEqual(upgrade(migrated), migrated)

    def test_invalid_thresholds_are_rejected(self):
        for updates in ({'click_concern_count': 7}, {'click_recovery_seconds': 4},
                        {'click_window_seconds': 0}, {'click_reactions': 1}):
            doc = defaults()
            doc['options'].update(updates)
            with self.assertRaises(DialogueError): validate(doc)

    def test_front_emotion_persists_while_talking_and_expires(self):
        motion = Motion()
        self.assertEqual(motion.frame(), 24)
        motion.react('angry', seconds=10, speaking=True)
        motion.face_front(10)
        for elapsed in (.3, .5, 1.3, 9.9):
            motion.elapsed = elapsed
            self.assertEqual(motion.frame(), 27)
        motion.elapsed = 10.1
        self.assertEqual(motion.frame(), 24)
        motion.react('happy', speaking=True)
        motion.face_front()
        self.assertEqual(motion.frame(), 24)
        motion.walking = True
        self.assertIn(motion.frame(), range(16, 24))


if __name__ == '__main__':
    unittest.main()
