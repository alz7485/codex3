"""Frame-independent eased locomotion, breathing, gestures and expression state."""
import math
import random
from collections import deque

EXPRESSION_FRAMES = {
    "neutral": 0, "blink": 1, "happy": 2, "notice": 3, "think": 4, "sleepy": 5,
    "proud": 6, "concern": 7, "wink": 8, "laugh": 9, "curious": 10,
    "relaxed": 11, "nod": 12, "talk": 13, "greet": 14, "stretch": 15,
    "front": 24, "front_blink": 25, "troubled": 26, "angry": 27,
}


class ClickReactions:
    """Session-only left-click bursts, measured with a monotonic clock."""
    def __init__(self):
        self.reset()

    def reset(self):
        self.clicks = deque(maxlen=60)
        self.last = None
        self.stage = 0
        self.announced = {}

    def reset_burst(self):
        self.clicks.clear()
        self.stage = 0

    def click(self, now, options):
        if not options['click_reactions']:
            self.reset()
            return None
        if self.last is not None and now < self.last:
            self.reset()
        elif self.last is not None and now - self.last >= options['click_recovery_seconds']:
            self.reset_burst()
        self.last = now
        while self.clicks and now - self.clicks[0] > options['click_window_seconds']:
            self.clicks.popleft()
        self.clicks.append(now)
        count = len(self.clicks)
        self.stage = max(self.stage, 2 if count >= options['click_angry_count'] else
                         1 if count >= options['click_concern_count'] else 0)
        if not self.stage:
            return None
        previous = self.announced.get(self.stage)
        if previous is not None and now - previous < options['click_repeat_seconds']:
            return None
        self.announced[self.stage] = now
        return 'click_concern' if self.stage == 1 else 'click_angry'


class Motion:
    def __init__(self, uniform=random.uniform):
        self.uniform = uniform
        self.elapsed = 0.0
        self.wait = self.uniform(0.05, 0.2)
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
        self.idle_at = 5.0
        self.front_until = 0.0
        self.phase = 'idle'
        self.phase_elapsed = 0.0
        self.was_blocked = False

    def face_front(self, seconds=8.0):
        self.front_until = self.elapsed + seconds
        self.walking = False
        self.phase = 'idle'
        self.speed = 0.0
        self.wait = max(self.wait, 0.6)

    def react(self, expression, seconds=8.0, speaking=False):
        self.expression = expression if expression in EXPRESSION_FRAMES else "neutral"
        self.expression_until = self.elapsed + seconds
        self.talk_until = self.elapsed + 2.8 if speaking else 0.0

    def start_soon(self):
        self.wait = self.uniform(0.05, 0.2)
        self.phase, self.phase_elapsed = 'idle', 0.0
        self.speed = 0.0
        self.walking = False

    def advance(self, dt, x, lower, upper, walk_allowed):
        dt = max(0.0, min(0.1, dt))  # Never jump after sleep/resume.
        self.elapsed += dt
        self.walking = False
        if self.elapsed >= self.idle_at:
            if self.elapsed >= self.expression_until:
                gestures = ("think", "curious", "relaxed", "nod", "wink", "stretch", "proud")
                self.react(gestures[min(len(gestures) - 1, int(self.uniform(0, len(gestures))))], 2.5)
            self.idle_at = self.elapsed + self.uniform(5, 9)
        next_x = min(upper, max(lower, x))
        if walk_allowed and upper > lower and self.was_blocked:
            # Let the pointer/menu interaction finish, then resume promptly
            # instead of carrying a long pre-interaction pause forward.
            self.wait = self.uniform(0.05, 0.2)
            self.was_blocked = False
        if not walk_allowed or upper <= lower:
            self.was_blocked = True
            if self.phase != 'idle':
                self.phase = 'idle'
                self.wait = max(self.wait, 0.6)
            self.phase_elapsed = 0.0
        elif self.phase == 'settle':
            self.phase_elapsed += dt
            if self.phase_elapsed >= 0.22:
                self.phase = 'idle'
                self.phase_elapsed = 0.0
        else:
            self.wait -= dt
            if self.wait <= 0:
                if self.phase == 'idle':
                    if x >= upper - 4:
                        self.direction = -1
                    elif x <= lower + 4:
                        self.direction = 1
                    self.facing = self.direction
                    self.phase, self.phase_elapsed = 'look', 0.0
                self.phase_elapsed += dt
                if self.phase == 'look' and self.phase_elapsed >= 0.18:
                    self.phase, self.phase_elapsed = 'lean', 0.0
                elif self.phase == 'lean' and self.phase_elapsed >= 0.14:
                    self.phase, self.phase_elapsed = 'walk', 0.0
                if self.phase != 'walk':
                    self.speed = 0.0
                    self.walk_weight *= math.exp(-dt * 9)
                    return next_x
                if self.distance <= 0:
                    self.distance = self.uniform(24, 56)
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
                    self.wait = self.uniform(0.4, 1.2)
                    self.distance = 0
                    self.direction *= -1
                    self.phase, self.phase_elapsed = 'settle', 0.0
        if not self.walking:
            self.speed = 0
        self.walk_weight += ((1.0 if self.walking else 0.0) - self.walk_weight) * (1 - math.exp(-dt * 9))
        return next_x

    def frame(self):
        if self.walking:
            return 16 + int(self.gait * 8) % 8
        if self.phase in ('look', 'lean', 'settle'):
            return 0
        # Keep the emotional face visible instead of alternating to the old
        # side-facing talking frame during repeated-click reactions.
        if self.expression and self.elapsed < self.expression_until and EXPRESSION_FRAMES[self.expression] >= 24:
            return EXPRESSION_FRAMES[self.expression]
        if self.elapsed < self.front_until:
            return 25 if self.elapsed % 5.2 > 5.02 else 24
        if self.elapsed < self.talk_until and int(self.elapsed * 4) % 2:
            return EXPRESSION_FRAMES["talk"]
        if self.expression and self.elapsed < self.expression_until:
            return EXPRESSION_FRAMES[self.expression]
        return 25 if self.elapsed % 5.2 > 5.02 else 24

    def pose(self):
        """Continuous transforms between sprite frames; amplitudes are in logical pixels."""
        phase = self.gait * 2 * math.pi
        weight = self.walk_weight
        bob = -abs(math.sin(phase)) * 1.2 * weight
        sway = math.sin(phase) * 1.3 * weight
        if self.phase == 'lean':
            sway += self.direction * 0.8 * min(1.0, self.phase_elapsed / 0.14)
        breath = math.sin(self.elapsed * 1.7) * 0.007 * (1 - weight)
        return bob, sway, 1 - breath / 2, 1 + breath
