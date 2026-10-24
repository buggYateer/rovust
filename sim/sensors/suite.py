r"""Mounts the sensors an environment calls for and updates them every step.

Placement (robot frame, x forward, y left):

              [cam]                 camera: front, tilted down
        cliffL       cliffR         IR switches ahead of the front corners
   S3    IR+30  IR0  IR-30   S1     3 IR PSDs on the front bumper
      \                    /
   S4 --  gyro/compass/   -- S0     sonar ring, S0 = straight ahead
      /   accel (centre)   \
   S5         bat           S7
              S6                    sonar S4 looks straight back
"""
from __future__ import annotations

import math

import numpy as np

from ..config import EnvConfig
from .base import ADC, Sensor
from .camera import Camera
from .internal_sensors import (DVL, Accelerometer, BatteryMonitor, Compass, GasSensor, Gyro,
                               LightSensor, PressureSensor)
from .range_sensors import Bumper, CliffSensor, IRDistance, Sonar


class SensorSuite:
    def __init__(self, cfg: EnvConfig, rng: np.random.Generator):
        self.cfg = cfg
        sc = cfg.sensors
        r = cfg.drive.robot_radius
        self.adc = ADC(sc.adc_bits, sc.adc_vref)
        self.sensors: list[Sensor] = []
        self.sonars: list[Sonar] = []
        self.irs: list[IRDistance] = []
        self.cliffs: list[CliffSensor] = []
        self.bumpers: list[Bumper] = []
        underwater = cfg.drive.kind == "thrusters"

        for i in range(sc.sonar_count):
            a = 2 * math.pi * i / sc.sonar_count
            s = Sonar(f"sonar{i}", rng, r * math.cos(a), r * math.sin(a), a,
                      sc.sonar_range, sc.sonar_cone_deg, sc.sonar_noise, sc.sonar_crosstalk,
                      sc.sonar_specular_deg, underwater)
            self.sonars.append(s)
        for i, s in enumerate(self.sonars):
            s.neighbours = [self.sonars[(i - 1) % len(self.sonars)], self.sonars[(i + 1) % len(self.sonars)]]
        self.sensors += self.sonars

        # IR PSDs all face forward, spread across the body width, so anything
        # the body is about to hit lies in at least one beam (the sonar cones
        # at 0 and +/-45 deg leave a blind strip there). Recessed so nothing
        # can get closer than the minimum range.
        ir_offsets = {0: [], 1: [("irC", 0.0)], 2: [("irL", 0.7 * r), ("irR", -0.7 * r)],
                      3: [("irC", 0.0), ("irL", 0.75 * r), ("irR", -0.75 * r)]}[min(sc.ir_count, 3)]
        for name, dy in ir_offsets:
            self.irs.append(IRDistance(name, rng, r - sc.ir_min_range, dy, 0.0,
                                       sc.ir_range, sc.ir_min_range, sc.ir_noise, self.adc))
        self.sensors += self.irs

        if sc.cliff_sensors:
            # front pair looks ahead of the wheels; the rear pair exists because
            # the escape behaviours *reverse*, and a pit behind the robot is
            # just as fatal as one in front
            # plus a side pair: the body can brush a pit while turning or
            # steering around an obstacle, which no front sensor can see
            self.cliffs = [CliffSensor("cliffFL", rng, r + sc.cliff_lookahead, 0.6 * r),
                           CliffSensor("cliffFR", rng, r + sc.cliff_lookahead, -0.6 * r),
                           CliffSensor("cliffL", rng, 0.0, r + sc.cliff_lookahead * 0.5),
                           CliffSensor("cliffR", rng, 0.0, -(r + sc.cliff_lookahead * 0.5)),
                           CliffSensor("cliffRL", rng, -(r + sc.cliff_lookahead), 0.6 * r),
                           CliffSensor("cliffRR", rng, -(r + sc.cliff_lookahead), -0.6 * r)]
            self.sensors += self.cliffs
        if sc.bumpers:
            self.bumpers = [Bumper("bumpL", rng, +1), Bumper("bumpR", rng, -1)]
            self.sensors += self.bumpers

        self.compass = Compass("compass", rng, sc.compass_noise_deg, sc.compass_disturbance) if sc.compass else None
        # Mars has no usable magnetic field: rovers take absolute heading from the sun instead
        self.sun = Compass("sun", rng, sc.sun_noise_deg, 0.0) if sc.sun_sensor else None
        self.gyro = Gyro("gyro", rng, sc.gyro_noise, sc.gyro_bias) if sc.imu else None
        self.accel = Accelerometer("accel", rng) if sc.imu else None
        self.camera = Camera("camera", rng, r + sc.camera_range) if sc.camera else None
        self.battery = BatteryMonitor("battery", rng, self.adc)
        self.light = LightSensor("light", rng, self.adc) if sc.light_sensor else None
        self.gas = GasSensor("gas", rng, self.adc) if sc.gas_sensor else None
        self.pressure = PressureSensor("pressure", rng, self.adc) if sc.pressure_sensor else None
        self.dvl = DVL("dvl", rng) if sc.dvl else (DVL("optflow", rng, noise=0.015) if sc.optical_flow else None)
        for s in (self.compass, self.sun, self.gyro, self.accel, self.camera, self.battery,
                  self.light, self.gas, self.pressure, self.dvl):
            if s is not None:
                self.sensors.append(s)
        self.by_name = {s.name: s for s in self.sensors}

    def update(self, robot, world, dt: float):
        for s in self.sensors:
            s.update(robot, world, dt)

    def set_fault(self, name: str, mode: str):
        self.by_name[name].set_fault(mode)

    def names(self):
        return [s.name for s in self.sensors]

    @property
    def heading_ref(self):
        """Whichever absolute heading sensor is mounted and healthy."""
        for s in (self.compass, self.sun):
            if s is not None and s.healthy:
                return s
        return None

    # convenience views used by the behaviours ---------------------------------
    def sonar_front(self) -> float:
        n = len(self.sonars)
        if not n:
            return math.inf
        idx = [0, 1, n - 1] if n >= 3 else [0]
        return min(self.sonars[i].value for i in idx if self.sonars[i].healthy) if any(self.sonars[i].healthy for i in idx) else math.inf

    def sonar_sector(self, angle: float, half_width: float = 0.6) -> float:
        """Minimum healthy sonar reading whose mount angle is within +/- half_width of angle."""
        vals = [s.value for s in self.sonars
                if s.healthy and abs(math.atan2(math.sin(s.angle - angle), math.cos(s.angle - angle))) <= half_width]
        return min(vals) if vals else math.inf

    def ir_front(self) -> float:
        vals = [s.value for s in self.irs if s.healthy and s.value < s.max_range * 0.7]
        return min(vals) if vals else math.inf

    def cliff(self) -> bool:
        return any(c.value > 0.5 for c in self.cliffs if c.healthy)

    def cliff_front(self) -> bool:
        return any(c.value > 0.5 for c in self.cliffs if c.healthy and c.dx > 0)

    def cliff_rear(self) -> bool:
        return any(c.value > 0.5 for c in self.cliffs if c.healthy and c.dx < 0)

    def cliff_side(self) -> int:
        """+1 if the left side sensor sees a drop, -1 for the right, 0 otherwise."""
        for c in self.cliffs:
            if c.healthy and c.dx == 0 and c.value > 0.5:
                return 1 if c.dy > 0 else -1
        return 0

    def bumped(self) -> tuple[bool, bool]:
        if not self.bumpers:
            return False, False
        return self.bumpers[0].value > 0.5, self.bumpers[1].value > 0.5
