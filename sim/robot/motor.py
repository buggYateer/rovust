"""DC motor + H-bridge + PWM (lecture: Actuators 1).

The controller only ever sees a *duty cycle* in [-1, 1]; the sign selects the
H-bridge direction (SW1+SW2 forward, SW3+SW4 reverse). The motor turns that
into a shaft speed through a first-order model with a non-linear duty ->
effective-voltage curve, a static-friction dead band and a load-dependent
steady state, so the relation between duty and speed is not linear and needs
calibration, exactly as in the lecture's "motor calibration table".
"""
from __future__ import annotations

import math

from ..config import MotorConfig


class HBridge:
    """Four switches. We only model the logical state."""
    FORWARD, REVERSE, BRAKE, COAST = "forward", "reverse", "brake", "coast"

    def __init__(self, vcc: float):
        self.vcc = vcc
        self.state = self.COAST

    def apply(self, duty: float) -> float:
        """Return the signed supply voltage for a signed duty cycle."""
        if duty > 0:
            self.state = self.FORWARD
            return self.vcc
        if duty < 0:
            self.state = self.REVERSE
            return -self.vcc
        self.state = self.BRAKE
        return 0.0


class DCMotor:
    def __init__(self, cfg: MotorConfig, mismatch: float = 0.0, name: str = "M"):
        self.cfg = cfg
        self.name = name
        self.bridge = HBridge(cfg.vcc)
        self.kv = cfg.kv * (1.0 + mismatch)   # the two motors are never identical
        self.omega = 0.0          # motor-shaft angular velocity [rad/s]
        self.angle = 0.0          # cumulative shaft angle [rad] (what the encoder sees)
        self.duty = 0.0
        self.load = 0.0           # 0..1, set by the drive from the terrain
        self.current = 0.0        # [A], rough estimate for the battery model

    def set_duty(self, duty: float):
        self.duty = max(-1.0, min(1.0, duty))

    def effective_voltage(self) -> float:
        """PWM: average voltage = duty * Vcc, but static friction eats the
        small duties and the real curve is not linear."""
        d = abs(self.duty)
        if d < self.cfg.deadband:
            return 0.0
        d = (d - self.cfg.deadband) / (1 - self.cfg.deadband)
        return math.copysign(self.cfg.vcc * d ** self.cfg.duty_exponent, self.duty)

    def step(self, dt: float):
        v = self.effective_voltage()
        self.bridge.apply(self.duty)
        # steady-state speed falls with load (vehicle weight, rough ground)
        omega_ss = self.kv * v * (1.0 - 0.6 * self.load)
        # first-order response: tau * d(omega)/dt = omega_ss - omega
        self.omega += (omega_ss - self.omega) * (dt / self.cfg.tau)
        self.angle += self.omega * dt
        self.current = abs(self.duty) * (0.3 + 1.2 * self.load)

    @property
    def wheel_omega(self) -> float:
        return self.omega / self.cfg.gear_ratio

    @property
    def power(self) -> float:
        return abs(self.effective_voltage()) * self.current


def calibration_table(cfg: MotorConfig, steps: int = 11, load: float = 0.0):
    """Measure steady-state wheel speed for several duty cycles (lecture:
    'motor calibration is done by measuring the motor speed at various
    settings of duty cycle')."""
    rows = []
    for i in range(steps):
        duty = i / (steps - 1)
        m = DCMotor(cfg)
        m.load = load
        m.set_duty(duty)
        for _ in range(int(2.0 / 0.01)):
            m.step(0.01)
        rows.append((duty, m.wheel_omega))
    return rows
