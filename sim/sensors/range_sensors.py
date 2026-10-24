"""Active range sensors (lecture: Sensors 2): sonar, IR PSD, IR cliff switch."""
from __future__ import annotations

import math

import numpy as np

from ..core import Terrain
from .base import ADC, Sensor, SensorClass

SPEED_OF_SOUND_AIR = 343.0
SPEED_OF_SOUND_WATER = 1480.0


class Sonar(Sensor):
    """Time-of-flight ultrasonic sensor with a cone, specular reflection
    loss and cross-talk with its neighbours."""
    cls = SensorClass("local", "external", "active", "digital")
    units = "m"

    def __init__(self, name, rng, dx, dy, angle, max_range, cone_deg, noise, crosstalk,
                 specular_deg, underwater=False):
        super().__init__(name, rng, dx, dy, angle)
        self.max_range = max_range
        self.cone = math.radians(cone_deg)
        self.noise = noise
        self.crosstalk = crosstalk
        self.specular = math.radians(specular_deg)
        self.c = SPEED_OF_SOUND_WATER if underwater else SPEED_OF_SOUND_AIR
        self.neighbours: list["Sonar"] = []
        self.tof_us = 0.0
        self.value = max_range
        self.history = [max_range] * 3     # last readings (the fault detector looks at them)
        self.unfiltered = max_range

    def _measure(self, robot, world, dt):
        x, y, a = self.world_position(robot)
        best = self.max_range
        true_best = self.max_range
        for k in range(-2, 3):
            ray = a + k * self.cone / 4
            d, normal = world.raycast(x, y, ray, self.max_range)
            true_best = min(true_best, d)
            if normal is None:
                continue
            # angle between the incoming ray and the surface normal
            incidence = abs(math.atan2(math.sin(ray + math.pi - normal), math.cos(ray + math.pi - normal)))
            if incidence > self.specular:
                continue            # echo bounces away: obstacle seems to be missing
            best = min(best, d)
        if self.neighbours and self.rng.random() < self.crosstalk:
            best = self.neighbours[self.rng.integers(len(self.neighbours))].value * self.rng.uniform(0.6, 1.4)
        if best < self.max_range:
            best += self.rng.normal(0, self.noise * best + 0.005)   # timing error grows with range
        best = min(max(best, 0.02), self.max_range)
        self.tof_us = 2 * best / self.c * 1e6
        self.unfiltered = best
        self.history = self.history[1:] + [best]
        # no temporal filter: a filtered value lags while the robot turns and
        # paints walls in the wrong direction; single cross-talk spikes are
        # rejected by the map instead (one echo never makes a cell occupied)
        return true_best, best, int(self.tof_us)

    def _dead_value(self):
        return self.max_range, int(2 * self.max_range / self.c * 1e6)


class IRDistance(Sensor):
    """Sharp GP2D12-style infrared position-sensitive device.

    Analog, non-linear: V = 24 / (d_cm + 4). Below the minimum range the
    output *drops* so a very near object looks far away (lecture: "the safest
    solution is to mechanically mount the sensor so an obstacle can never get
    closer than 6cm"). The reading is linearised by a lookup table that is
    built once per sensor by calibration.
    """
    cls = SensorClass("local", "external", "active", "analog")
    units = "m"

    def __init__(self, name, rng, dx, dy, angle, max_range, min_range, noise, adc: ADC):
        super().__init__(name, rng, dx, dy, angle)
        self.max_range, self.min_range, self.noise = max_range, min_range, noise
        self.adc = adc
        self.lut = self._calibrate()
        self.value = max_range

    def volts_for(self, d: float) -> float:
        d_cm = d * 100
        if d < self.min_range:
            # the characteristic folds back below the minimum range
            return self.volts_for(self.min_range) * (d / self.min_range)
        return min(2.8, 24.0 / (d_cm + 4.0))

    def _calibrate(self) -> np.ndarray:
        """Lookup table raw ADC count -> distance, by sweeping the sensor."""
        lut = np.full(self.adc.levels + 1, self.max_range)
        for d in np.linspace(self.min_range, self.max_range, 400)[::-1]:
            lut[self.adc.convert(self.volts_for(d))] = d
        # fill holes between calibrated counts
        for i in range(1, len(lut)):
            if lut[i] == self.max_range and lut[i - 1] < self.max_range:
                lut[i] = lut[i - 1]
        return lut

    def _measure(self, robot, world, dt):
        x, y, a = self.world_position(robot)
        true, _ = world.raycast(x, y, a, self.max_range)
        volts = self.volts_for(true) + self.rng.normal(0, self.noise)
        raw = self.adc.convert(volts)
        return true, float(self.lut[raw]), raw

    def _dead_value(self):
        return self.max_range, 0


class CliffSensor(Sensor):
    """Downward-looking IR proximity switch at a front corner: 1 = no ground
    return (pit / edge). Binary, like the lecture's IR proximity switch."""
    cls = SensorClass("local", "external", "active", "binary")

    def __init__(self, name, rng, dx, dy):
        super().__init__(name, rng, dx, dy, 0.0)

    def _measure(self, robot, world, dt):
        x, y = robot.body_point(self.dx, self.dy)
        t = world.terrain_at(x, y)
        cliff = 1.0 if t == Terrain.PIT or not world.in_bounds(*world.to_cell(x, y)) else 0.0
        return cliff, cliff, int(cliff)


class Bumper(Sensor):
    """Tactile switch: the simplest binary sensor."""
    cls = SensorClass("local", "external", "passive", "binary")

    def __init__(self, name, rng, side: int):
        super().__init__(name, rng, 0.0, 0.0, 0.0)
        self.side = side     # +1 left, -1 right

    def _measure(self, robot, world, dt):
        if not robot.collided:
            return 0.0, 0.0, 0
        # the bumper is a strip across the front: it only closes when the
        # contact is on its own front corner or head-on. A body pushed
        # sideways into a wall (by a current) does not press the front bumper.
        r = robot.radius
        x, y = robot.body_point(r * 0.95, self.side * r * 0.55)
        hit = world.circle_hits_obstacle(x, y, r * 0.3)
        if not hit:
            fx, fy = robot.body_point(r * 1.0, 0.0)
            hit = world.circle_hits_obstacle(fx, fy, r * 0.25)     # head-on: both sides close
        return float(hit), float(hit), int(hit)
