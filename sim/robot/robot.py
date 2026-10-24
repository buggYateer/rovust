"""The rover body: drive, battery and (from stage 2) the sensor suite."""
from __future__ import annotations

import math

import numpy as np

from ..config import EnvConfig
from ..core import Pose, Terrain
from ..world import World
from .drive import DifferentialDrive


class Battery:
    def __init__(self, capacity_wh: float, idle_w: float):
        self.capacity_wh = capacity_wh
        self.energy_wh = capacity_wh
        self.idle_w = idle_w
        self.power = 0.0

    def step(self, dt: float, load_w: float):
        self.power = self.idle_w + load_w
        self.energy_wh = max(0.0, self.energy_wh - self.power * dt / 3600.0)

    @property
    def fraction(self) -> float:
        return self.energy_wh / self.capacity_wh

    @property
    def voltage(self) -> float:
        """Terminal voltage sags with charge; what the battery monitor reads."""
        return 10.5 + 2.1 * self.fraction


class Robot:
    def __init__(self, cfg: EnvConfig, world: World, rng: np.random.Generator):
        self.cfg = cfg
        self.world = world
        self.rng = rng
        self.pose = Pose(world.start[0], world.start[1], 0.0)
        self.drive = DifferentialDrive(cfg.drive, cfg.motor, cfg.pid, rng)
        self.battery = Battery(cfg.battery_wh, cfg.battery_idle_w)
        self.headlights = False
        self.radius = cfg.drive.robot_radius
        self.collided = False       # true if the last move was blocked by an obstacle
        self.fell = False           # drove into a pit: mission over
        self.collisions = 0
        self.distance = 0.0
        from ..sensors.suite import SensorSuite   # local import: the suite reads the robot
        self.sensors = SensorSuite(cfg, rng)
        self.headlights = cfg.ambient_light < 0.3

    # ------------------------------------------------------------ helpers
    def wheel_positions(self) -> tuple[tuple[float, float], tuple[float, float]]:
        L = self.cfg.drive.wheel_base / 2
        s, c = math.sin(self.pose.theta), math.cos(self.pose.theta)
        left = (self.pose.x - L * s, self.pose.y + L * c)
        right = (self.pose.x + L * s, self.pose.y - L * c)
        return left, right

    def body_point(self, dx: float, dy: float) -> tuple[float, float]:
        """Robot-frame offset (forward, left) -> world coordinates."""
        c, s = math.cos(self.pose.theta), math.sin(self.pose.theta)
        return self.pose.x + dx * c - dy * s, self.pose.y + dx * s + dy * c

    # --------------------------------------------------------------- step
    def step(self, dt: float):
        w = self.world
        (lx, ly), (rx, ry) = self.wheel_positions()
        tl, tr = w.terrain_at(lx, ly), w.terrain_at(rx, ry)
        cur = self.cfg.water_current
        if self.cfg.current_noise:
            cur = (cur[0] + self.rng.normal(0, self.cfg.current_noise),
                   cur[1] + self.rng.normal(0, self.cfg.current_noise))
        new = self.drive.step(dt, self.pose, tl, tr, extra_vel=cur)

        self.collided = False
        if w.circle_hits_obstacle(new.x, new.y, self.radius):
            # blocked: keep heading change, lose the translation, bumper fires
            self.collided = True
            self.collisions += 1
            new.x, new.y = self.pose.x, self.pose.y
            self.drive.left.omega *= 0.2
            self.drive.right.omega *= 0.2
        if w.circle_over_pit(new.x, new.y, self.radius * 0.6):
            self.fell = True
        self.distance += math.hypot(new.x - self.pose.x, new.y - self.pose.y)
        self.pose = new

        load = self.drive.left.power + self.drive.right.power
        if self.headlights:
            load += self.cfg.headlight_w
        self.battery.step(dt, load)
        w.time += dt
        self.sensors.update(self, w, dt)
