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
        self.assertEqual(frames, set(range(16, 24)))

    def test_interaction_blocks_walking_and_resume_is_not_a_jump(self):
        motion = Motion()
        motion.wait = 0
        self.assertEqual(motion.advance(0.1, 100, 0, 200, False), 100)
        self.assertFalse(motion.walking)
        x = motion.advance(10000, 100, 0, 200, True)
        self.assertLessEqual(abs(x - 100), 2)

    def test_acceleration_breathing_and_all_expression_reactions(self):
        from companion.motion import EXPRESSION_FRAMES
        motion = Motion(uniform=lambda a, b: a)
        motion.wait = 0
        x, steps = 150, []
        for _ in range(60):
            new_x = motion.advance(1 / 60, x, 0, 300, True)
            steps.append(abs(new_x - x))
            x = new_x
        self.assertLess(steps[0], steps[-1])
        self.assertLessEqual(max(steps), 20 / 60)
        before = motion.pose()
        motion.advance(1 / 60, x, 0, 300, False)
        after = motion.pose()
        self.assertTrue(all(abs(a - b) < 0.3 for a, b in zip(before, after)))
        for expression, frame in EXPRESSION_FRAMES.items():
            motion.react(expression)
            self.assertEqual(motion.frame(), frame)

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
