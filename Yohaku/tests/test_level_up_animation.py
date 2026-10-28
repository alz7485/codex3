"""Celebrations stay within one resident window and yield to real interaction."""
import unittest
from unittest.mock import Mock
from PySide6.QtCore import QPoint,Qt
from PySide6.QtTest import QTest
from companion.level_up_animation import DURATION,pose
from companion.ui import Resident,create_application


class LevelUpAnimationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=create_application()
    def setUp(self):
        self.resident=Resident('A');self.resident.show();self.app.processEvents()
        self.clock=100.;self.effect=self.resident.level_up;self.effect.clock=lambda:self.clock
    def tearDown(self):
        self.effect.cancel();self.resident.hide();self.resident.deleteLater();self.app.processEvents()
    def test_all_characters_have_distinct_bounded_motion_and_return_to_rest(self):
        tracks=[]
        for character in ('A','B','E'):
            track=[pose(character,n*.05) for n in range(57)];tracks.append(track)
            self.assertTrue(any(y<-.03 for y,angle,sx,sy,frame,opacity in track))
            for y,angle,sx,sy,frame,opacity in track:
                self.assertGreaterEqual(y,-.09);self.assertLessEqual(abs(angle),9.)
                self.assertGreater(sx,.8);self.assertGreater(sy,.8);self.assertIn(frame,(2,6,9))
                self.assertGreaterEqual(opacity,0.);self.assertLessEqual(opacity,1.)
            y,angle,sx,sy,frame,opacity=pose(character,DURATION)
            self.assertEqual((y,angle,sx,sy,opacity),(0.,0.,1.,1.,0.))
        self.assertNotEqual(tracks[0],tracks[1]);self.assertNotEqual(tracks[0],tracks[2])
    def test_expiry_stops_timer_and_does_not_move_the_native_window_or_change_normal_frame(self):
        self.resident.frame_index=24;position=self.resident.pos();self.effect.start()
        self.assertTrue(self.effect.active);self.clock+=.6;self.effect.advance()
        self.assertEqual(self.resident.pos(),position);self.assertEqual(self.resident.frame_index,24)
        self.clock+=DURATION;self.effect.advance()
        self.assertFalse(self.effect.active);self.assertFalse(self.effect.timer.isActive())
    def test_each_character_renders_a_changing_pose_and_uses_its_costume_frame(self):
        renderer=Mock();renderer.compose.side_effect=lambda image,character,frame:image
        self.resident.costumes=renderer
        for character in ('A','B','E'):
            self.resident.set_character(character);self.effect.start();self.clock+=.5
            first=self.resident.grab().toImage();self.clock+=.4;second=self.resident.grab().toImage()
            self.assertNotEqual(first,second);self.assertFalse(first.isNull())
            self.assertEqual(renderer.compose.call_args.args[1],character)
            self.assertIn(renderer.compose.call_args.args[2],(2,6,9));self.effect.cancel()
    def test_hide_character_change_and_animation_disabled_cancel_without_replaying(self):
        self.effect.start();self.resident.hide();self.assertFalse(self.effect.active)
        self.resident.show();self.app.processEvents();self.assertFalse(self.effect.active)
        self.effect.start();self.resident.set_character('E');self.assertFalse(self.effect.active)
        self.effect.start();self.resident.prop_animation_enabled=False;self.effect.advance()
        self.assertFalse(self.effect.active);self.effect.start();self.assertFalse(self.effect.active)
    def test_either_mouse_button_interrupts_celebration_and_still_delivers_actions(self):
        clicked=Mock();called=Mock();self.resident.clicked.connect(clicked);self.resident.context_requested.connect(called)
        self.effect.start();QTest.mouseClick(self.resident,Qt.MouseButton.LeftButton,pos=QPoint(40,40))
        self.assertFalse(self.effect.active);clicked.assert_called_once()
        self.effect.start();QTest.mouseClick(self.resident,Qt.MouseButton.RightButton,pos=QPoint(40,40))
        self.assertFalse(self.effect.active);called.assert_called_once()
    def test_mail_and_notification_form_props_interrupt_instead_of_overlapping(self):
        for action in (self.resident.raise_mail,self.resident.check_calendar,self.resident.take_notes):
            self.resident.clear_props();self.effect.start();action()
            self.assertFalse(self.effect.active)
            self.effect.start();self.assertFalse(self.effect.active)
