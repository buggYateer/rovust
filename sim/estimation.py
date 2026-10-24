"""Where am I? (lecture: Sensors 2, dead reckoning and its unbounded error)

Three estimates are kept side by side so the interface can show them:

* ``odom``   - dead reckoning from the encoders alone (drifts: slip + heading)
* ``fused``  - the same displacement, but the heading comes from the gyro
               corrected by the compass (complementary filter) and the gyro
               bias is learned while the robot stands still
* ``pose``   - whichever of the two the behaviours use (``mode``), or the true
               pose when ``mode == "perfect"`` for comparison runs.

Underwater the DVL replaces the encoders as the displacement source.
"""
from __future__ import annotations

import math

from .core import Pose, wrap_angle


class HeadingFilter:
    def __init__(self, compass_gain: float = 0.05, bias_gain: float = 0.02):
        self.theta = 0.0
        self.bias = 0.0
        self.compass_gain = compass_gain
        self.bias_gain = bias_gain

    def update(self, gyro_rate: float | None, compass: float | None, stationary: bool, dt: float) -> float:
        if gyro_rate is not None:
            if stationary:
                # standing still: whatever the gyro says is bias
                self.bias += (gyro_rate - self.bias) * self.bias_gain
            self.theta = wrap_angle(self.theta + (gyro_rate - self.bias) * dt)
        if compass is not None:
            self.theta = wrap_angle(self.theta + self.compass_gain * wrap_angle(compass - self.theta))
        return self.theta


class PoseEstimator:
    MODES = ("odometry", "fused", "perfect")

    def __init__(self, robot, mode: str = "fused"):
        self.robot = robot
        self.mode = mode
        start = robot.pose.copy()
        self.odom = start.copy()
        self.fused = start.copy()
        self.heading = HeadingFilter()
        self.heading.theta = start.theta
        self._last_l = robot.drive.enc_l.wheel_angle()
        self._last_r = robot.drive.enc_r.wheel_angle()
        self.error_history: list[float] = []
        self.v_est = 0.0
        self.omega_est = 0.0

    @property
    def pose(self) -> Pose:
        if self.mode == "perfect":
            return self.robot.pose
        return self.fused if self.mode == "fused" else self.odom

    def update(self, dt: float):
        r = self.robot
        suite = r.sensors
        drive = r.drive
        wr = r.cfg.drive.wheel_radius
        # ---- displacement source: encoders (or DVL underwater)
        if suite.dvl is not None and suite.dvl.healthy:
            ds = suite.dvl.value * dt
            dth_odom = suite.dvl.omega * dt
        else:
            al, ar = drive.enc_l.wheel_angle(), drive.enc_r.wheel_angle()
            dl, dr = (al - self._last_l) * wr, (ar - self._last_r) * wr
            self._last_l, self._last_r = al, ar
            ds = (dl + dr) / 2
            dth_odom = (dr - dl) / r.cfg.drive.wheel_base
        self.v_est, self.omega_est = ds / dt, dth_odom / dt
        # ---- odometry only
        mid = self.odom.theta + dth_odom / 2
        self.odom.x += ds * math.cos(mid)
        self.odom.y += ds * math.sin(mid)
        self.odom.theta = wrap_angle(self.odom.theta + dth_odom)
        # ---- fused heading
        gyro = suite.gyro.value if (suite.gyro is not None and suite.gyro.healthy) else None
        compass = suite.compass.value if (suite.compass is not None and suite.compass.healthy) else None
        stationary = abs(drive.des_wl) < 1e-6 and abs(drive.des_wr) < 1e-6 and abs(ds) < 1e-4
        if gyro is None and compass is None:
            theta = wrap_angle(self.fused.theta + dth_odom)
            self.heading.theta = theta
        else:
            theta = self.heading.update(gyro, compass, stationary, dt)
        mid = self.fused.theta + wrap_angle(theta - self.fused.theta) / 2
        self.fused.x += ds * math.cos(mid)
        self.fused.y += ds * math.sin(mid)
        self.fused.theta = theta
        self.error_history.append(self.pose.distance_to(r.pose))

    def error(self) -> float:
        return self.pose.distance_to(self.robot.pose)
