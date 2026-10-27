"""Separate notice lifetime and promptly resume smooth desktop movement."""
from copy import deepcopy
import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from companion.core import Notice
from companion.dialogue import DialogueStore, MAX_BYTES, defaults, upgrade, validate
from companion.motion import Motion


class TimingMigrationTests(unittest.TestCase):
    def test_old_default_moves_to_twenty_once_and_custom_durations_survive(self):
        for seconds, expected in [(60, 20), (85, 85), (20, 20)]:
            with self.subTest(seconds=seconds):
                document = defaults()
                document.pop('display_timing_version')
                document['options']['bubble_seconds'] = seconds
                before = deepcopy(document)
                updated = validate(upgrade(document))
                self.assertEqual(updated['options']['bubble_seconds'], expected)
                self.assertEqual(document, before)
                self.assertEqual(updated['rules'], before['rules'])
                self.assertEqual(updated['phrases'], before['phrases'])
                updated['options']['bubble_seconds'] = 60
                self.assertEqual(upgrade(updated)['options']['bubble_seconds'], 60)

    def test_click_restart_discards_long_wait_but_retains_smooth_takeoff(self):
        motion = Motion(uniform=lambda a, b: b)
        motion.wait = 55
        motion.face_front()
        motion.start_soon()
        x, first_move = 200., None
        for step in range(50):
            before = x
            x = motion.advance(.02, x, 0, 500, True)
            self.assertLessEqual(abs(x-before), 20*.02)
            if x != before and first_move is None:
                first_move = (step+1)*.02
        self.assertIsNotNone(first_move)
        self.assertLessEqual(first_move, .7)

    def test_timing_migration_at_size_limit_keeps_valid_document_and_edits(self):
        document = defaults()
        document.pop('display_timing_version')
        document['options']['bubble_seconds'] = 60
        document['padding'] = ''
        size = len(json.dumps(document, ensure_ascii=False).encode('utf-8'))
        document['padding'] = 'x' * (MAX_BYTES - size)
        validate(document)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary)/'dialogue.json'
            path.write_text(json.dumps(document, ensure_ascii=False), encoding='utf-8', newline='\n')
            original = path.read_bytes()
            store = DialogueStore(path)
            self.assertFalse(store.error)
            self.assertEqual(store.data['options']['bubble_seconds'], 20)
            self.assertEqual(store.data['padding'], document['padding'])
            self.assertEqual(path.read_bytes(), original)
            store.save(store.data)
            self.assertLessEqual(path.stat().st_size, MAX_BYTES)


class BubbleTimingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from companion.ui import create_application
        cls.app = create_application()

    def setUp(self):
        from companion.ui import Controller
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        with patch.dict(os.environ, {'LOCALAPPDATA': self.temp.name}):
            self.c = Controller(self.app,data_path=Path(os.environ["LOCALAPPDATA"])/"Yohaku")
        for timer in (self.c.tick_timer, self.c.poll_timer, self.c.animation_timer,
                      self.c.activity_timer, self.c.context_timer):
            timer.stop()
        self.c.panel.hide()
        self.c.settings.quiet_start = self.c.settings.quiet_end = '00:00'
        self.addCleanup(self.cleanup_controller)

    def cleanup_controller(self):
        c = self.c
        c.shutdown(); c.tray.hide()
        for widget in (c.panel, c.resident, c.bubble, c.history_window):
            widget.hide()
        c.deleteLater(); self.app.processEvents()

    def test_all_notice_categories_use_twenty_or_sixty_seconds(self):
        c = self.c
        for kind, important, expected in [('message', False, 20000), ('calendar', False, 20000),
            ('calendar', True, 60000), ('notification', True, 60000),
            ('reminder', True, 60000), ('departure', True, 60000)]:
            with self.subTest(kind=kind, important=important):
                c.bubble.display(Notice('', '合成メッセージ', important, kind=kind))
                self.assertEqual(c.bubble.timer.interval(), expected)
        c.bubble.open_choices()
        self.assertEqual(c.bubble.timer.interval(), 20000)

    def test_passive_click_message_moves_within_one_second_even_under_stationary_pointer(self):
        c = self.c
        c.settings.walking = True
        c.motion = Motion(uniform=lambda a, b: b)
        c.motion.wait = 55
        c.motion_x = 200.
        clock = [1000.]
        c.last_motion_time = clock[0]
        with patch('companion.ui.time.monotonic', side_effect=lambda: clock[0]), \
             patch.object(c.resident, 'underMouse', return_value=True):
            c.show_message()
            self.assertTrue(c.bubble.isVisible())
            for _ in range(50):
                clock[0] += .02
                c.animate()
            self.assertNotEqual(c.motion_x, 200.)
            self.assertTrue(c.bubble.isVisible())
            self.assertEqual(c.bubble.timer.interval(), 20000)
            c.open_choices()
            stopped = c.motion_x
            for _ in range(50):
                clock[0] += .02
                c.animate()
            self.assertEqual(c.motion_x, stopped)

    def test_mail_burst_and_timing_edits_keep_notice_at_one_minute_and_form_open(self):
        c = self.c
        c.settings.outlook_enabled = c.settings.mail_enabled = True
        payload = {'messages': [{'kind': 'mail'}]}
        c.mail_result(c.mail_generation, payload, '')
        self.assertEqual(c.bubble.timer.interval(), 60000)
        c.dialogue.data['options']['bubble_seconds'] = 85
        c.dialogue_saved()
        self.assertEqual(c.bubble.timer.interval(), 60000)
        c.mail_result(c.mail_generation, payload, '')
        self.assertEqual(c.bubble.timer.interval(), 60000)
        c.select_content('one_shot')
        c.bubble.reminder_message.setPlainText('編集中の本文')
        c.dialogue_saved()
        self.assertFalse(c.bubble.timer.isActive())
        self.assertEqual(c.bubble.reminder_message.toPlainText(), '編集中の本文')


if __name__ == '__main__':
    unittest.main()
