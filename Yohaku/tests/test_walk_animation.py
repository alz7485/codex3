"""Alternating contacts verified against actual rendered foot layers."""
from pathlib import Path
import unittest
from PySide6.QtCore import QRect
from PySide6.QtGui import QPixmap,QRegion
from companion.ui import create_application,character_frames
from companion.walk_animation import RIGS,leg_phase,foot_layer


class WalkAnimationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.app=create_application()

    def test_contacts_and_lift_alternate_between_the_two_legs(self):
        self.assertEqual(leg_phase(0,0),(1,0))
        self.assertEqual(leg_phase(.5,0),(-1,0))
        self.assertEqual(leg_phase(0,1),(-1,0))
        self.assertEqual(leg_phase(.5,1),(1,0))
        self.assertEqual(leg_phase(.25,0),(0,0))
        self.assertAlmostEqual(leg_phase(.25,1)[1],1)
        self.assertAlmostEqual(leg_phase(.75,0)[1],1)
        self.assertEqual(leg_phase(.75,1),(0,0))

    def test_rendered_leading_foot_swaps_and_support_foot_keeps_ground_contact(self):
        assets=Path(__file__).resolve().parents[1]/'companion/assets/characters'
        for character in RIGS:
            sheet=QPixmap(str(assets/(character.lower()+'_motion.png')))
            base=sheet.copy(QRect(0,0,sheet.width()//6,sheet.height()//4))
            for phase in (0,.5):
                boxes=[QRegion(foot_layer(base,character,phase,leg,128,248).mask()).boundingRect() for leg in (0,1)]
                self.assertTrue(all(box.bottom()==248 for box in boxes))
                if phase==0:self.assertGreater(boxes[0].center().x(),boxes[1].center().x())
                else:self.assertLess(boxes[0].center().x(),boxes[1].center().x())
            for phase,support in ((.25,0),(.75,1)):
                boxes=[QRegion(foot_layer(base,character,phase,leg,128,248).mask()).boundingRect() for leg in (0,1)]
                self.assertEqual(boxes[support].bottom(),248)
                self.assertLessEqual(boxes[1-support].bottom(),242)

    def test_torso_does_not_change_scale_or_position_between_opposite_steps(self):
        for character in RIGS:
            frames=character_frames(character)
            head=frames[16].copy(0,0,frames[16].width(),frames[16].height()//2).toImage()
            for index in range(16,24):
                self.assertEqual(frames[index].size(),frames[0].size())
                self.assertEqual(frames[index].copy(0,0,frames[index].width(),frames[index].height()//2).toImage(),head)
            self.assertNotEqual(frames[16].toImage(),frames[20].toImage())
