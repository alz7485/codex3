import unittest
from companion.motion import Motion


class MotionTests(unittest.TestCase):
    def test_short_rests_and_pointer_pauses_do_not_flash_front_during_a_stroll(self):
        for pick in (lambda a, b: a, lambda a, b: b):
            motion = Motion(uniform=pick)
            x = 75.0
            started = False
            resting_frames = 0
            turns = 0
            previous_direction = motion.facing
            for step in range(3000):
                # Includes screen-edge turns, idle gestures and a transient
                # hover pause, all without an explicit face-front request.
                x = motion.advance(.02, x, 0, 100, not (300 <= step < 310))
                started = started or motion.walking
                if started:
                    self.assertLess(motion.frame(), 24)
                    if not motion.walking:
                        resting_frames += 1
                    if motion.facing != previous_direction:
                        turns += 1
                previous_direction = motion.facing
            self.assertGreater(resting_frames, 20)
            self.assertGreater(turns, 5)

    def test_resuming_walk_clears_old_front_hold_before_the_next_rest(self):
        motion = Motion(uniform=lambda a, b: a)
        motion.react('front', 8)
        motion.face_front(8)
        motion.start_soon()
        self.assertEqual(motion.frame(), 24)
        x = 100.0
        walked = False
        for _ in range(400):
            x = motion.advance(.02, x, 0, 300, True)
            walked = walked or motion.walking
            if walked:
                self.assertLess(motion.frame(), 24)
                if not motion.walking:
                    self.assertLess(motion.elapsed, 8)
                    break
        else:
            self.fail('Expected a short rest within the old front hold')

    def test_explicit_interaction_still_faces_front_after_a_stroll(self):
        motion = Motion(uniform=lambda a, b: a)
        x = 100.0
        for _ in range(100):
            x = motion.advance(.02, x, 0, 300, True)
        self.assertTrue(motion.side_idle)
        motion.react('front', 8)
        motion.face_front(8)
        motion.advance(.02, x, 0, 300, False)
        self.assertEqual(motion.frame(), 24)
        motion.react('angry', seconds=float('inf'))
        self.assertEqual(motion.frame(), 27)

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
                self.assertLessEqual(starts[0], 0.7)
                self.assertGreaterEqual(len(starts), 10)
                self.assertLessEqual(longest_pause, 2.0)
                self.assertTrue(distances)
                self.assertTrue(all(23.9 <= distance <= 56.1 for distance in distances))

    def test_interactive_input_keeps_still_then_resumes_promptly(self):
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
        self.assertGreaterEqual(first_move, .2)
        self.assertLessEqual(first_move, .7)

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

    def test_step_phase_follows_distance_at_different_update_rates_and_freezes_when_blocked(self):
        phases=[]
        for count in (10,25,60):
            motion=Motion(uniform=lambda a,b:a);motion.phase='walk';motion.wait=0
            motion.distance=10000;motion.speed=20;motion.stride_pixels=28
            x=200.
            for _ in range(count):x=motion.advance(1/count,x,0,1000,True)
            self.assertAlmostEqual(x,180.)
            self.assertAlmostEqual(motion.gait,20/28)
            phases.append(motion.gait)
            motion.advance(.1,x,0,1000,False)
            self.assertAlmostEqual(motion.gait,phases[-1])
            self.assertEqual(motion.pose()[0],0)  # No whole-sprite bounce of a planted foot.
        self.assertAlmostEqual(phases[0],phases[-1])

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
