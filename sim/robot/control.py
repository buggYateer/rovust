"""Feedback controllers from the Control lecture.

All controllers map (desired, actual) -> motor output R in [-1, 1].
The PID uses the discrete incremental form derived in the lecture:

    R_n = R_{n-1} + Kp (e_n - e_{n-1}) + Ki (e_n + e_{n-1}) / 2
                  + Kd (e_n - 2 e_{n-1} + e_{n-2})

so only the previous output and the last two errors are stored.
"""
from __future__ import annotations


class OnOffController:
    """Bang-bang: full power when too slow, zero otherwise."""

    def __init__(self, kc: float = 1.0):
        self.kc = kc
        self.output = 0.0

    def update(self, desired: float, actual: float, dt: float) -> float:
        self.output = self.kc if actual < desired else 0.0
        return self.output

    def reset(self):
        self.output = 0.0


class HysteresisController:
    """On-off with a band: switch on below v_on, off above v_off."""

    def __init__(self, kc: float = 1.0, band: float = 0.1):
        self.kc, self.band = kc, band
        self.output = 0.0

    def update(self, desired: float, actual: float, dt: float) -> float:
        if actual < desired * (1 - self.band):
            self.output = self.kc
        elif actual > desired * (1 + self.band):
            self.output = 0.0
        return self.output

    def reset(self):
        self.output = 0.0


class PIDController:
    def __init__(self, kp: float, ki: float = 0.0, kd: float = 0.0,
                 limit: float = 1.0):
        self.kp, self.ki, self.kd = kp, ki, kd
        self.limit = limit
        self.reset()

    def reset(self):
        self.output = 0.0
        self.e1 = 0.0   # e_{n-1}
        self.e2 = 0.0   # e_{n-2}
        self.error = 0.0

    def update(self, desired: float, actual: float, dt: float) -> float:
        e = desired - actual
        r = (self.output
             + self.kp * (e - self.e1)
             + self.ki * dt * (e + self.e1) / 2.0
             + self.kd / dt * (e - 2 * self.e1 + self.e2))
        # clamp (and because the form is incremental, clamping is also anti-windup)
        self.output = max(-self.limit, min(self.limit, r))
        self.e2, self.e1, self.error = self.e1, e, e
        return self.output


class IntegralController:
    """Pure I term, used by the 'driving straight' structure of the lecture
    to integrate the difference between the two encoder counts."""

    def __init__(self, ki: float, limit: float = 1.0):
        self.ki, self.limit = ki, limit
        self.sum = 0.0

    def update(self, error: float, dt: float) -> float:
        self.sum += error * dt
        self.sum = max(-self.limit / self.ki, min(self.limit / self.ki, self.sum))
        return self.ki * self.sum

    def reset(self):
        self.sum = 0.0
