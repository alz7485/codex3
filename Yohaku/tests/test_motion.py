import unittest
from companion.motion import Motion


class MotionTests(unittest.TestCase):
    def test_walk_moves_alternates_frames_and_stays_inside_bounds(self):
        motion = Motion(uniform=lambda a, b: a)
        motion.wait = 0
        x, positions, frames = 200, [], set()
        for _ in range(400):
            x = motion.advance(0.1, x, 10, 200, True)
            positions.append(x)
            if motion.walking:
                frames.add(motion.frame())
        self.assertTrue(all(10 <= p <= 200 for p in positions))
        self.assertLess(min(positions), 200)
        self.assertEqual(frames, {4, 5})

    def test_interaction_blocks_walking_and_resume_is_not_a_jump(self):
        motion = Motion()
        motion.wait = 0
        self.assertEqual(motion.advance(0.1, 100, 0, 200, False), 100)
        self.assertFalse(motion.walking)
        x = motion.advance(10000, 100, 0, 200, True)
        self.assertLessEqual(abs(x - 100), 2)

    def test_blink_reaction_expiration_and_small_screen_clamp(self):
        motion = Motion()
        motion.elapsed = 5.1
        self.assertEqual(motion.frame(), 1)
        motion.react("happy", 1)
        self.assertEqual(motion.frame(), 2)
        motion.react("notice", 1)
        self.assertEqual(motion.frame(), 3)
        motion.elapsed += 2
        self.assertEqual(motion.frame(), 0)
        self.assertEqual(motion.advance(0.1, 100, 10, 10, True), 10)


if __name__ == "__main__":
    unittest.main()
