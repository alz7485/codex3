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

    def test_each_shoe_moves_relative_to_its_own_hip_and_support_keeps_ground_contact(self):
        assets=Path(__file__).resolve().parents[1]/'companion/assets/characters'
        for character in RIGS:
            sheet=QPixmap(str(assets/(character.lower()+'_motion.png')))
            base=sheet.copy(QRect(0,0,sheet.width()//6,sheet.height()//4))
            contacts=[]
            for phase in (0,.5):
                boxes=[QRegion(foot_layer(base,character,phase,leg,128,248).mask()).boundingRect() for leg in (0,1)]
                self.assertTrue(all(box.bottom()==248 for box in boxes));contacts.append(boxes)
            self.assertGreater(contacts[0][0].center().x(),contacts[1][0].center().x())
            self.assertLess(contacts[0][1].center().x(),contacts[1][1].center().x())
            for phase,support in ((.25,0),(.75,1)):
                boxes=[QRegion(foot_layer(base,character,phase,leg,128,248).mask()).boundingRect() for leg in (0,1)]
                self.assertEqual(boxes[support].bottom(),248)
                self.assertLessEqual(boxes[1-support].bottom(),242)

    def test_body_scale_stays_fixed_with_only_a_small_vertical_settle(self):
        for character in RIGS:
            frames=character_frames(character)
            bounds=[]
            for index in range(16,24):
                self.assertEqual(frames[index].size(),frames[0].size())
                bounds.append(QRegion(frames[index].copy(0,0,frames[index].width(),frames[index].height()//2).mask()).boundingRect())
            self.assertLessEqual(max(b.top() for b in bounds)-min(b.top() for b in bounds),2)
            self.assertLessEqual(max(b.width() for b in bounds)-min(b.width() for b in bounds),2)
            self.assertNotEqual(frames[16].toImage(),frames[20].toImage())

    def test_fixed_hip_stays_connected_and_tsuzuri_legs_contain_no_book_colours(self):
        import math
        assets=Path(__file__).resolve().parents[1]/'companion/assets/characters'
        for character,rig in RIGS.items():
            sheet=QPixmap(str(assets/(character.lower()+'_motion.png')))
            base=sheet.copy(QRect(0,0,sheet.width()//6,sheet.height()//4))
            for index in range(8):
                phase=index/8;bob=-round(1.5*abs(math.sin(math.tau*phase)))
                for leg in (0,1):
                    image=foot_layer(base,character,phase,leg,128,248).toImage()
                    hip_x=128+(-rig['hip'] if leg==0 else rig['hip'])
                    self.assertGreater(image.pixelColor(hip_x,rig['cut']-4+bob).alpha(),128)
                    if character=='A':
                        pixels=[image.pixelColor(x,y) for y in range(image.height()) for x in range(image.width()) if image.pixelColor(x,y).alpha()>128]
                        self.assertTrue(pixels);self.assertLess(max(max(c.red(),c.green(),c.blue()) for c in pixels),200)
