"""Small deterministic animation/movement state; independent from Qt."""
import random


class Motion:
    def __init__(self, uniform=random.uniform):
        self.uniform = uniform
        self.elapsed = 0.0
        self.wait = 15.0
        self.distance = 0.0
        self.direction = -1
        self.walking = False
        self.expression = None
        self.expression_until = 0.0

    def react(self, expression, seconds=3.0):
        self.expression = expression
        self.expression_until = self.elapsed + seconds

    def advance(self, dt, x, lower, upper, walk_allowed):
        dt = max(0.0, min(0.1, dt))  # Never jump after sleep/resume.
        self.elapsed += dt
        self.walking = False
        if not walk_allowed or upper <= lower:
            return min(upper, max(lower, x))
        self.wait -= dt
        if self.wait > 0:
            return min(upper, max(lower, x))
        if self.distance <= 0:
            self.distance = self.uniform(70, 160)
            if x >= upper - 4:
                self.direction = -1
            elif x <= lower + 4:
                self.direction = 1
        amount = min(20 * dt, self.distance)
        next_x = min(upper, max(lower, x + amount * self.direction))
        self.distance -= amount
        self.walking = next_x != x
        if self.distance <= 0 or next_x in (lower, upper):
            self.wait = self.uniform(25, 55)
            self.distance = 0
            self.direction *= -1
        return next_x

    def frame(self):
        if self.expression and self.elapsed < self.expression_until:
            return {"happy": 2, "notice": 3}.get(self.expression, 0)
        if self.walking:
            return 4 + int(self.elapsed * 5) % 2
        # Brief blink, not a flashing continuous animation.
        return 1 if self.elapsed % 5.2 > 5.02 else 0
