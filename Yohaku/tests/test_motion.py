import unittest
from companion.motion import Motion


class MotionTests(unittest.TestCase):
    def test_uninterrupted_idle_has_frequent_short_walks_without_long_front_holds(self):
        for pick in (lambda a, b: a, lambda a, b: b):
            with self.subTest(range_end=pick(0, 1)):
                motion = Motion(uniform=pick)
                x, starts, distances = 200.0, [], []
                previous_walking, trip_distance, stationary, longest_pause = False, 0.0, 0.0, 0.0
                for step in range(3000):
                    previous_x = x
                    x = motion.advance(.02, x, 0, 500, True)
                    if motion.walking:
                        if not previous_walking:
                            starts.append((step + 1) * .02)
                        trip_distance += abs(x - previous_x)
                        stationary = 0.0
                    else:
                        stationary += .02
                        longest_pause = max(longest_pause, stationary)
                        if previous_walking:
                            distances.append(trip_distance)
                            trip_distance = 0.0
                    previous_walking = motion.walking
                self.assertLessEqual(starts[0], 4.5)
                self.assertGreaterEqual(len(starts), 6)
                self.assertLessEqual(longest_pause, 5.7)
                self.assertTrue(distances)
                self.assertTrue(all(23.9 <= distance <= 56.1 for distance in distances))

    def test_reading_a_bubble_keeps_still_then_resumes_after_a_short_pause(self):
        motion = Motion(uniform=lambda a, b: b)
        motion.wait = 55  # A long pause must not survive a completed interaction.
        for _ in range(600):
            self.assertEqual(motion.advance(.1, 150, 0, 300, False), 150)
            self.assertFalse(motion.walking)
        x = 150
        first_move = None
        for step in range(30):
            previous = x
            x = motion.advance(.1, x, 0, 300, True)
            self.assertLessEqual(abs(x - previous), 2)
            if x != previous and first_move is None:
                first_move = (step + 1) * .1
        self.assertIsNotNone(first_move)
        self.assertGreaterEqual(first_move, .8)
        self.assertLessEqual(first_move, 2.0)

    def test_facing_is_retained_when_a_walk_finishes(self):
        motion = Motion(uniform=lambda a, b: a)
        motion.wait = 0
        motion.distance = 0.01
        for _ in range(5): motion.advance(0.1, 100, 0, 200, True)
        self.assertEqual(motion.direction, 1)  # Next trip faces the other way.
        self.assertEqual(motion.facing, -1)  # Current pose keeps its actual direction.
        motion.advance(0.1, 100, 0, 200, False)
        self.assertEqual(motion.facing, -1)

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
        self.assertEqual(motion.frame(), 25)
        motion.react("happy", 1)
        self.assertEqual(motion.frame(), 2)
        motion.react("notice", 1)
        self.assertEqual(motion.frame(), 3)
        motion.elapsed += 2
        self.assertEqual(motion.frame(), 24)
        self.assertEqual(motion.advance(0.1, 100, 10, 10, True), 10)


if __name__ == "__main__":
    unittest.main()
