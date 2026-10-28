"""Floating EXP feedback uses committed amounts and never takes mouse input."""
from pathlib import Path
import unittest
from PySide6.QtCore import Qt
from companion.exp_popup import ExpPopup,exp_text,visual_state
from companion.ui import Resident,create_application

class ExpPopupTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=create_application()
    def setUp(self):
        self.clock=1000.;self.allowed=True;self.animated=True
        self.resident=Resident('A');self.resident.move(400,400);self.resident.show();self.app.processEvents()
        self.popup=ExpPopup(self.resident,lambda:self.allowed and self.resident.isVisible(),lambda:self.animated,lambda:self.clock)
    def tearDown(self):
        self.popup.cancel();self.resident.hide();self.resident.deleteLater();self.app.processEvents()
    def image_alpha(self):
        image=self.popup.grab().toImage()
        return max(image.pixelColor(x,y).alpha() for y in range(image.height()) for x in range(image.width()))
    def test_text_rises_above_head_tracks_horizontal_movement_and_expires(self):
        self.popup.show_gain(10);initial=self.popup.pos();self.clock+=.6;self.popup.advance()
        self.assertLess(self.popup.y(),initial.y());self.assertTrue(self.popup.isVisible())
        old_x=self.popup.x();self.resident.move(self.resident.x()+40,self.resident.y());self.popup.advance()
        self.assertEqual(self.popup.x(),old_x+40)
        self.clock+=1.41;self.popup.advance();self.assertFalse(self.popup.isVisible());self.assertFalse(self.popup.timer.isActive())
    def test_actual_text_fades_in_out_and_green_remains_visible_inside_white_outline(self):
        # A gentle entrance, then start fading before the final second ends.
        self.assertAlmostEqual(visual_state(.15)[1],.5)
        self.assertAlmostEqual(visual_state(.30)[1],1.)
        self.assertAlmostEqual(visual_state(.90)[1],1.)
        self.assertLess(visual_state(1.)[1],1.)
        self.assertEqual(visual_state(1.6),(28.,0.))
        self.popup.show_gain(5);self.assertEqual(self.image_alpha(),0)
        self.clock+=.05;early=self.image_alpha();self.clock+=.55;peak=self.image_alpha()
        image=self.popup.grab().toImage();green=sum(1 for y in range(image.height()) for x in range(image.width())
            if image.pixelColor(x,y).alpha()>180 and image.pixelColor(x,y).green()>image.pixelColor(x,y).red()+20)
        self.assertGreater(green,15);self.clock+=.9;late=self.image_alpha()
        self.assertGreater(peak,early);self.assertGreater(peak,late);self.assertGreater(early,0);self.assertGreater(late,0)
    def test_popup_is_click_through_and_does_not_accept_focus(self):
        self.assertTrue(self.popup.testAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents))
        self.assertTrue(self.popup.testAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating))
        self.assertTrue(self.popup.windowFlags()&Qt.WindowType.WindowTransparentForInput)
        self.assertEqual(self.popup.focusPolicy(),Qt.FocusPolicy.NoFocus)
    def test_simultaneous_gains_queue_once_and_parent_hide_clears_all_pending_text(self):
        self.popup.show_gain(5);self.popup.show_gain(2);self.popup.show_gain(3)
        self.assertEqual(list(self.popup.pending),[5]);self.clock+=2.01;self.popup.advance()
        self.assertEqual(self.popup.amount,5);self.assertFalse(self.popup.pending)
        self.popup.show_gain(4);self.resident.hide();self.assertFalse(self.popup.timer.isActive());self.assertFalse(self.popup.pending)
        self.resident.show();self.app.processEvents();self.assertFalse(self.popup.isVisible())
    def test_hidden_or_disabled_visibility_never_starts_or_leaves_queued_gains(self):
        self.allowed=False;self.popup.show_gain(5);self.assertFalse(self.popup.timer.isActive())
        self.allowed=True;self.popup.show_gain(5);self.allowed=False;self.popup.advance()
        self.assertFalse(self.popup.isVisible());self.assertFalse(self.popup.pending)
    def test_animation_off_shows_static_feedback_and_still_expires(self):
        self.animated=False;self.popup.show_gain(10);point=self.popup.pos();self.clock+=1.;self.popup.advance()
        self.assertEqual(self.popup.pos(),point);self.assertEqual(self.image_alpha(),255)
        self.clock+=1.01;self.popup.advance();self.assertFalse(self.popup.isVisible())
    def test_gain_label_uses_actual_amount_and_exp_spelling_without_trailing_decimal_zeroes(self):
        for amount,text in ((5,'+5 EXP'),(10,'+10 EXP'),(2.5,'+2.5 EXP'),(.005,'+0.005 EXP')):self.assertEqual(exp_text(amount),text)
    def test_popup_can_follow_each_supported_character(self):
        for character in ('A','B','E'):
            self.resident.set_character(character);self.popup.show_gain(5);self.clock+=.5;self.popup.advance()
            self.assertTrue(self.popup.isVisible());self.assertGreater(self.image_alpha(),0);self.popup.cancel()
