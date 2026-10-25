"""Controller-level walking under quiet hours, open panels and resumed input."""
from dataclasses import asdict
from datetime import datetime, timedelta, timezone
import os
os.environ.setdefault('QT_QPA_PLATFORM', 'offscreen')
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from PySide6.QtCore import QPoint, QRect
from PySide6.QtWidgets import QWidget, QSystemTrayIcon
from companion.core import Notice, Settings, save_json
from companion.motion import Motion
from companion.ui import Controller, create_application


class Evening(datetime):
    @classmethod
    def now(cls, tz=None):
        return cls(2026, 10, 26, 21, 0, tzinfo=timezone.utc)


class WalkingPolicyTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_application()

    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(); self.addCleanup(self.temporary.cleanup)
        save_json(Path(self.temporary.name)/'Yohaku/settings.json', asdict(Settings(context_enabled=False, mail_enabled=False)))
        with patch.dict(os.environ, LOCALAPPDATA=self.temporary.name), patch.object(QSystemTrayIcon, 'isSystemTrayAvailable', return_value=True):
            self.c = Controller(self.app)
        self.addCleanup(self.cleanup)
        for timer in (self.c.tick_timer, self.c.poll_timer, self.c.animation_timer, self.c.activity_timer, self.c.context_timer):
            timer.stop()
        self.clock = 1000.
        self.patches = [patch('companion.ui.datetime', Evening),
                        patch('companion.ui.time.monotonic', side_effect=lambda: self.clock),
                        patch.object(self.c, 'resident_area', return_value=QRect(0, 0, 800, 600)),
                        patch.object(self.c.resident, 'underMouse', return_value=False)]
        for p in self.patches:
            p.start(); self.addCleanup(p.stop)
        self.c.panel.hide(); self.c.motion_y = 500; self.reset_motion()

    def reset_motion(self):
        self.c.motion = Motion(uniform=lambda a, b: b)
        self.c.motion_x = 200.; self.c.last_motion_time = self.clock

    def advance(self, seconds=1):
        for _ in range(round(seconds/.02)):
            self.clock += .02; self.c.animate()

    def cleanup(self):
        self.c.shutdown(); self.c.tray.hide()
        for widget in (self.c.panel, self.c.resident, self.c.bubble, self.c.history_window):
            widget.hide()
        self.c.deleteLater(); self.app.processEvents()

    def test_quiet_hours_suppress_notices_but_walk_frequently_for_a_full_minute(self):
        c = self.c; c.update_animation_policy()
        self.assertTrue(c.animation_timer.isActive())
        self.assertIsNone(c.engine.next_notice(Evening.now(), []))
        first = None; stationary = longest = 0.
        for step in range(3000):
            before = c.motion_x; self.advance(.02)
            if c.motion_x != before:
                first = first if first is not None else (step+1)*.02
                stationary = 0
            else:
                stationary += .02; longest = max(longest, stationary)
        self.assertIsNotNone(first); self.assertLessEqual(first, .7)
        self.assertLessEqual(longest, 2.0)

    def test_open_settings_history_and_editors_do_not_pin_the_character(self):
        c = self.c
        c.settings.quiet_start = c.settings.quiet_end = '00:00'
        widgets = [c.panel, c.history_window]
        for attr in ('editor', 'reminder_editor', 'context_editor'):
            widget = QWidget(); setattr(c, attr, widget); widgets.append(widget)
        try:
            for widget in widgets:
                with self.subTest(window=widget):
                    self.reset_motion(); widget.show(); self.advance()
                    self.assertNotEqual(c.motion_x, 200.)
                    widget.hide()
        finally:
            for attr in ('editor', 'reminder_editor', 'context_editor'):
                getattr(c, attr).hide(); setattr(c, attr, None)

    def test_choices_and_unread_reactions_still_stop_walking_until_dismissed(self):
        c = self.c; c.open_choices(); self.advance(); self.assertEqual(c.motion_x, 200.)
        c.bubble.dismiss(); self.advance(); self.assertNotEqual(c.motion_x, 200.)
        self.reset_motion(); c.pending_reaction = Notice('', '少し待って。', expression='angry')
        self.advance(); self.assertEqual(c.motion_x, 200.)
        c.clear_reaction(); self.advance(); self.assertNotEqual(c.motion_x, 200.)

    def test_animation_walking_pause_and_visibility_switches_still_stop_motion(self):
        c = self.c
        for attr in ('animation', 'walking', 'user_hidden', 'hidden'):
            with self.subTest(setting=attr):
                previous = getattr(c.settings if attr in ('animation', 'walking') else c, attr)
                target = c.settings if attr in ('animation', 'walking') else c
                setattr(target, attr, attr in ('user_hidden', 'hidden'))
                self.reset_motion(); self.advance(); self.assertEqual(c.motion_x, 200.)
                setattr(target, attr, previous)
        c.engine.paused_until = Evening.now() + timedelta(hours=1)
        self.reset_motion(); self.advance(); self.assertEqual(c.motion_x, 200.)
        c.engine.paused_until = None; c.update_animation_policy(); self.advance()
        self.assertNotEqual(c.motion_x, 200.)

    def test_drag_release_and_reshow_drop_long_wait_and_stale_press(self):
        c = self.c; c.motion.wait = 55
        c.finish_drag(); self.advance(); self.assertNotEqual(c.motion_x, 200.)
        c.resident.press_position = c.resident.press_origin = QPoint(20, 20); c.resident.dragging = True
        c.resident.hide(); self.assertIsNone(c.resident.press_position); self.assertFalse(c.resident.dragging)
        c.resident.show(); self.reset_motion(); c.motion.wait = 55
        c.animation_timer.stop(); c.update_animation_policy(); self.advance()
        self.assertNotEqual(c.motion_x, 200.)

    def test_tiny_pointer_jitter_does_not_extend_hover_pause_indefinitely(self):
        c = self.c
        with patch.object(c.resident, 'underMouse', return_value=True), patch('companion.ui.QCursor.pos') as cursor:
            for step in range(50):
                cursor.return_value = QPoint(220 + step % 2, 500)
                self.advance(.02)
        self.assertNotEqual(c.motion_x, 200.)
