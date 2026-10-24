"""Incremental two-phase shaft encoder (lecture: Sensors 1).

Mounted on the motor shaft *before* the gearbox, so a 16-tick disk with a
30:1 gearbox gives 480 ticks per wheel revolution. Two sensors with a phase
shift tell the direction; here we emulate that by counting signed ticks.
"""
from __future__ import annotations

import math


class IncrementalEncoder:
    def __init__(self, ticks_per_rev: int, gear_ratio: float):
        self.ticks_per_rev = ticks_per_rev
        self.gear_ratio = gear_ratio
        self.count = 0            # total signed ticks (what the pulse-counting register holds)
        self._last_angle = 0.0
        self._delta = 0
        self.direction = 0        # +1 cw, -1 ccw, 0 stopped

    def update(self, shaft_angle: float):
        """Sample the true shaft angle and emit the ticks that passed."""
        ticks_now = math.floor(shaft_angle / (2 * math.pi) * self.ticks_per_rev)
        ticks_before = math.floor(self._last_angle / (2 * math.pi) * self.ticks_per_rev)
        self._delta = ticks_now - ticks_before
        self.count += self._delta
        self._last_angle = shaft_angle
        self.direction = (self._delta > 0) - (self._delta < 0)

    def read_delta(self) -> int:
        return self._delta

    def wheel_speed(self, dt: float) -> float:
        """Measured wheel angular velocity [rad/s] from the last tick delta.
        Quantised: this is the only speed feedback the PID ever gets."""
        return self._delta / self.ticks_per_rev * 2 * math.pi / self.gear_ratio / dt

    def wheel_angle(self) -> float:
        return self.count / self.ticks_per_rev * 2 * math.pi / self.gear_ratio

    def reset(self):
        self.count = 0
        self._delta = 0
