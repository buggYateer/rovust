"""Internal / orientation / environment sensors (lecture: Sensors 2)."""
from __future__ import annotations

import math

from ..core import wrap_angle
from .base import ADC, Sensor, SensorClass


class Compass(Sensor):
    """Digital compass, 1 deg resolution. Suffers local magnetic disturbance
    (iron in the cave walls) modelled as a slowly varying field."""
    cls = SensorClass("local", "internal", "passive", "digital")
    units = "rad"

    def __init__(self, name, rng, noise_deg, disturbance):
        super().__init__(name, rng)
        self.noise = math.radians(noise_deg)
        self.disturbance = disturbance

    def _measure(self, robot, world, dt):
        true = robot.pose.theta
        dist = self.disturbance * math.sin(robot.pose.x * 0.7) * math.cos(robot.pose.y * 0.5)
        meas = wrap_angle(true + dist + self.rng.normal(0, self.noise))
        raw = int(round(math.degrees(meas) % 360))
        return true, math.radians(raw), raw


class Gyro(Sensor):
    """MEMS rate gyro (one axis, yaw). Has a constant bias, so integrating it
    alone drifts: that is why the compass is needed."""
    cls = SensorClass("local", "internal", "passive", "digital")
    units = "rad/s"

    def __init__(self, name, rng, noise, bias):
        super().__init__(name, rng)
        self.noise = noise
        self.bias = bias * rng.choice((-1, 1))
        self.integrated = 0.0

    def _measure(self, robot, world, dt):
        true = robot.drive.omega
        meas = true + self.bias + self.rng.normal(0, self.noise)
        self.integrated = wrap_angle(self.integrated + meas * dt)
        return true, meas, int(meas * 1000)


class Accelerometer(Sensor):
    """Reports pitch (tilt) from the gravity vector plus forward acceleration.
    Used to refuse slopes that are too steep."""
    cls = SensorClass("local", "internal", "passive", "digital")
    units = "rad"

    def __init__(self, name, rng, noise=0.01):
        super().__init__(name, rng)
        self.noise = noise
        self._last_v = 0.0

    def _measure(self, robot, world, dt):
        cx, cy = world.to_cell(robot.pose.x, robot.pose.y)
        tilt = float(world.slope[cy, cx]) if world.in_bounds(cx, cy) else 0.0
        accel = (robot.drive.v - self._last_v) / dt
        self._last_v = robot.drive.v
        meas = tilt + accel / 9.81 + self.rng.normal(0, self.noise)
        return tilt, meas, int(meas * 1000)


class BatteryMonitor(Sensor):
    cls = SensorClass("local", "internal", "passive", "analog")
    units = "V"

    def __init__(self, name, rng, adc: ADC):
        super().__init__(name, rng)
        self.adc = adc

    def _measure(self, robot, world, dt):
        v = robot.battery.voltage
        raw = self.adc.convert(v / 3.0)       # voltage divider 1:3 into the ADC
        return v, self.adc.to_volts(raw) * 3.0, raw


class LightSensor(Sensor):
    """Photodiode: ambient light plus the robot's own headlights."""
    cls = SensorClass("local", "external", "passive", "analog")

    def __init__(self, name, rng, adc: ADC):
        super().__init__(name, rng)
        self.adc = adc

    def _measure(self, robot, world, dt):
        level = world.cfg.ambient_light + (0.6 if robot.headlights else 0.0)
        level = min(1.0, level)
        raw = self.adc.convert(level * self.adc.vref + self.rng.normal(0, 0.05))
        return level, self.adc.to_volts(raw) / self.adc.vref, raw


class GasSensor(Sensor):
    """MQ-type gas sensor: analog, slow (first-order lag)."""
    cls = SensorClass("local", "external", "passive", "analog")

    def __init__(self, name, rng, adc: ADC):
        super().__init__(name, rng)
        self.adc = adc
        self._filtered = 0.0

    def _measure(self, robot, world, dt):
        cx, cy = world.to_cell(robot.pose.x, robot.pose.y)
        true = float(world.gas[cy, cx]) if world.in_bounds(cx, cy) else 0.0
        self._filtered += (true - self._filtered) * min(1.0, dt / 0.8)
        raw = self.adc.convert(self._filtered * self.adc.vref + self.rng.normal(0, 0.03))
        return true, self.adc.to_volts(raw) / self.adc.vref, raw


class PressureSensor(Sensor):
    """Depth from hydrostatic pressure (underwater)."""
    cls = SensorClass("local", "external", "passive", "analog")
    units = "m"

    def __init__(self, name, rng, adc: ADC, depth=12.0):
        super().__init__(name, rng)
        self.adc, self.depth = adc, depth

    def _measure(self, robot, world, dt):
        true = self.depth + 0.2 * math.sin(world.time * 0.5)
        raw = self.adc.convert(true / 30.0 * self.adc.vref + self.rng.normal(0, 0.01))
        return true, self.adc.to_volts(raw) / self.adc.vref * 30.0, raw


class DVL(Sensor):
    """Doppler velocity log: ground-relative body velocity (v, omega).
    Underwater there are no wheels to count, so this replaces the encoders as
    the odometry source."""
    cls = SensorClass("local", "external", "active", "digital")
    units = "m/s"

    def __init__(self, name, rng, noise=0.01):
        super().__init__(name, rng)
        self.noise = noise
        self.omega = 0.0

    def _measure(self, robot, world, dt):
        cur = robot.cfg.water_current
        # ground-relative velocity includes the current pushing the body
        c, s = math.cos(robot.pose.theta), math.sin(robot.pose.theta)
        v_ground = robot.drive.v + cur[0] * c + cur[1] * s
        self.omega = robot.drive.omega + self.rng.normal(0, self.noise)
        meas = v_ground + self.rng.normal(0, self.noise)
        return v_ground, meas, int(meas * 1000)
