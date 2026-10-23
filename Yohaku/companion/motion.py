"""Frame-independent eased locomotion, breathing, gestures and expression state."""
import math
import random

EXPRESSION_FRAMES = {
    "neutral": 0, "blink": 1, "happy": 2, "notice": 3, "think": 4, "sleepy": 5,
    "proud": 6, "concern": 7, "wink": 8, "laugh": 9, "curious": 10,
    "relaxed": 11, "nod": 12, "talk": 13, "greet": 14, "stretch": 15,
}


class Motion:
    def __init__(self, uniform=random.uniform):
        self.uniform = uniform
        self.elapsed = 0.0
        self.wait = 15.0
        self.distance = 0.0
        self.direction = -1
        self.facing = 1
        self.walking = False
        self.speed = 0.0
        self.gait = 0.0
        self.walk_weight = 0.0
        self.expression = None
        self.expression_until = 0.0
        self.talk_until = 0.0
        self.idle_at = 12.0

    def react(self, expression, seconds=8.0, speaking=False):
        self.expression = expression if expression in EXPRESSION_FRAMES else "neutral"
        self.expression_until = self.elapsed + seconds
        self.talk_until = self.elapsed + 2.8 if speaking else 0.0

    def advance(self, dt, x, lower, upper, walk_allowed):
        dt = max(0.0, min(0.1, dt))  # Never jump after sleep/resume.
        self.elapsed += dt
        self.walking = False
        if self.elapsed >= self.idle_at:
            if self.elapsed >= self.expression_until:
                gestures = ("think", "curious", "relaxed", "nod", "wink", "stretch", "proud")
                self.react(gestures[min(len(gestures) - 1, int(self.uniform(0, len(gestures))))], 2.5)
            self.idle_at = self.elapsed + self.uniform(12, 22)
        next_x = min(upper, max(lower, x))
        if walk_allowed and upper > lower:
            self.wait -= dt
            if self.wait <= 0:
                if self.distance <= 0:
                    self.distance = self.uniform(70, 160)
                    if x >= upper - 4:
                        self.direction = -1
                    elif x <= lower + 4:
                        self.direction = 1
                # Accelerate gently; slow down over the last 12 pixels.
                target = 20 * min(1.0, max(0.12, self.distance / 12))
                self.speed += (target - self.speed) * (1 - math.exp(-dt * 6))
                amount = min(self.speed * dt, self.distance)
                next_x = min(upper, max(lower, x + amount * self.direction))
                moved = abs(next_x - x)
                self.distance -= moved
                self.gait += moved / 22
                self.walking = moved > 0
                if self.walking:
                    self.facing = self.direction
                if self.distance < 0.08 or next_x in (lower, upper):
                    self.wait = self.uniform(25, 55)
                    self.distance = 0
                    self.direction *= -1
        if not self.walking:
            self.speed = 0
        self.walk_weight += ((1.0 if self.walking else 0.0) - self.walk_weight) * (1 - math.exp(-dt * 9))
        return next_x

    def frame(self):
        if self.walking:
            return 16 + int(self.gait * 8) % 8
        if self.elapsed < self.talk_until and int(self.elapsed * 4) % 2:
            return EXPRESSION_FRAMES["talk"]
        if self.expression and self.elapsed < self.expression_until:
            return EXPRESSION_FRAMES[self.expression]
        return 1 if self.elapsed % 5.2 > 5.02 else 0

    def pose(self):
        """Continuous transforms between sprite frames; amplitudes are in logical pixels."""
        phase = self.gait * 2 * math.pi
        weight = self.walk_weight
        bob = -abs(math.sin(phase)) * 1.2 * weight
        sway = math.sin(phase) * 1.3 * weight
        breath = math.sin(self.elapsed * 1.7) * 0.007 * (1 - weight)
        return bob, sway, 1 - breath / 2, 1 + breath
