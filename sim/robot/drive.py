"""Differential drive: two motors, two encoders, two PID velocity loops and
the 'driving straight' structure of the Control lecture (Fig. 5.16):

    desired v, omega  ->  desired wheel speeds (+/- curve offset)
                      ->  PID per wheel using encoder feedback
                      ->  I-controller on the *position* difference of the
                          two encoders, fed back to both wheels.

The rover has four wheels: each motor drives both wheels of its side
(skid-steer), so "left wheel" / "right wheel" below mean the left and right
side, and the kinematics are those of a differential drive.

The same class drives the underwater vehicle: there the "wheels" are two
thrusters and the "slip" is water.
"""
from __future__ import annotations

import math

import numpy as np

from ..config import DriveConfig, MotorConfig, PIDConfig
from ..core import TERRAIN, Pose, Terrain, wrap_angle
from .control import IntegralController, PIDController
from .encoder import IncrementalEncoder
from .motor import DCMotor


class DifferentialDrive:
    def __init__(self, dcfg: DriveConfig, mcfg: MotorConfig, pcfg: PIDConfig, rng: np.random.Generator):
        self.cfg, self.mcfg = dcfg, mcfg
        self.rng = rng
        self.left = DCMotor(mcfg, mismatch=+mcfg.mismatch / 2, name="L")
        self.right = DCMotor(mcfg, mismatch=-mcfg.mismatch / 2, name="R")
        self.enc_l = IncrementalEncoder(mcfg.encoder_ticks, mcfg.gear_ratio)
        self.enc_r = IncrementalEncoder(mcfg.encoder_ticks, mcfg.gear_ratio)
        self.pid_l = PIDController(pcfg.kp, pcfg.ki, pcfg.kd)
        self.pid_r = PIDController(pcfg.kp, pcfg.ki, pcfg.kd)
        self.straight = IntegralController(ki=0.4, limit=0.3)
        self.straight_enabled = True
        self.closed_loop = True          # False = open loop (duty set directly) for the demo
        self.des_wl = self.des_wr = 0.0  # desired wheel speeds [rad/s]
        self.meas_wl = self.meas_wr = 0.0
        self.v = self.omega = 0.0        # true body velocities
        self.slip_l = self.slip_r = 0.0
        self.ground_dl = self.ground_dr = 0.0  # true wheel ground travel in the last step

    # --------------------------------------------------------------- commands
    def set_velocity(self, v: float, omega: float):
        """Body command (m/s, rad/s) -> desired wheel speeds. Saturates at the
        wheel limit while preserving the turn ratio."""
        r, L = self.cfg.wheel_radius, self.cfg.wheel_base
        wl = (v - omega * L / 2) / r
        wr = (v + omega * L / 2) / r
        m = max(abs(wl), abs(wr), 1e-9)
        if m > self.cfg.max_wheel_speed:
            wl, wr = wl / m * self.cfg.max_wheel_speed, wr / m * self.cfg.max_wheel_speed
        self.des_wl, self.des_wr = wl, wr

    def stop(self):
        self.des_wl = self.des_wr = 0.0

    # ------------------------------------------------------------------- step
    def step(self, dt: float, pose: Pose, terrain_l: Terrain, terrain_r: Terrain,
             extra_vel: tuple[float, float] = (0.0, 0.0)) -> Pose:
        """Advance motors, encoders and kinematics; return the new true pose."""
        # 1. encoders sample the shafts -> measured wheel speed (quantised)
        self.enc_l.update(self.left.angle)
        self.enc_r.update(self.right.angle)
        self.meas_wl = self.enc_l.wheel_speed(dt)
        self.meas_wr = self.enc_r.wheel_speed(dt)

        # 2. controllers -> duty cycles
        if self.closed_loop:
            corr = 0.0
            if self.straight_enabled:
                # position difference of the two wheels, minus what the curve
                # command itself should produce
                expected = (self.des_wr - self.des_wl) * dt
                actual = self.enc_r.read_delta() - self.enc_l.read_delta()
                actual *= 2 * math.pi / (self.mcfg.encoder_ticks * self.mcfg.gear_ratio)
                corr = self.straight.update(expected - actual, dt)
            self.left.set_duty(self.pid_l.update(self.des_wl - corr, self.meas_wl, dt))
            self.right.set_duty(self.pid_r.update(self.des_wr + corr, self.meas_wr, dt))

        # 3. terrain load and slip (the encoders never see the slip)
        pl, pr = TERRAIN[terrain_l], TERRAIN[terrain_r]
        self.left.load, self.right.load = pl.load, pr.load
        self.left.step(dt)
        self.right.step(dt)
        self.slip_l = min(0.95, max(0.0, pl.slip + self.rng.normal(0, self.cfg.slip_noise)))
        self.slip_r = min(0.95, max(0.0, pr.slip + self.rng.normal(0, self.cfg.slip_noise)))
        r, L = self.cfg.wheel_radius, self.cfg.wheel_base
        vl = self.left.wheel_omega * r * (1 - self.slip_l)
        vr = self.right.wheel_omega * r * (1 - self.slip_r)
        self.ground_dl, self.ground_dr = vl * dt, vr * dt

        # 4. differential-drive kinematics
        self.v = (vl + vr) / 2
        self.omega = (vr - vl) / L
        new = pose.copy()
        new.theta = wrap_angle(pose.theta + self.omega * dt)
        mid = pose.theta + self.omega * dt / 2
        new.x = pose.x + self.v * math.cos(mid) * dt + extra_vel[0] * dt
        new.y = pose.y + self.v * math.sin(mid) * dt + extra_vel[1] * dt
        return new

    def reset_controllers(self):
        for c in (self.pid_l, self.pid_r, self.straight):
            c.reset()
