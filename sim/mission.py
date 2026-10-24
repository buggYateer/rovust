"""One exploration run: world + robot + estimator + map + explorer + behaviours."""
from __future__ import annotations

import math

import numpy as np

from .behaviors import (Arbiter, AvoidObstacle, BumperEscape, CliffStop, Context, EmergencyStop,
                        Explore, InitialScan, PathFollower, ReturnHome, SlopeRefuse, Wander)
from .config import EnvConfig, get_env
from .estimation import PoseEstimator
from .mapping import Mapper, OccupancyGrid
from .planning import DFSExplorer, FrontierExplorer
from .robot.robot import Robot
from .world import World

STRATEGIES = {"frontier": FrontierExplorer, "dfs": DFSExplorer}


class Mission:
    def __init__(self, env: str | EnvConfig, strategy: str = "frontier", seed: int = 0,
                 localisation: str = "fused", dt: float = 0.05, ai=None):
        self.cfg = get_env(env, seed) if isinstance(env, str) else env
        self.seed = seed
        self.rng = np.random.default_rng(seed + 1000)
        self.dt = dt
        self.world = World(self.cfg)
        self.robot = Robot(self.cfg, self.world, np.random.default_rng(seed + 7))
        self.estimator = PoseEstimator(self.robot, mode=localisation)
        self.grid = OccupancyGrid(self.world.w, self.world.h, self.world.cell)
        self.mapper = Mapper(self.grid, self.robot)
        self.strategy = strategy
        if strategy in STRATEGIES:
            self.explorer = STRATEGIES[strategy](self.grid, self.robot.radius, self.rng)
        else:
            from .ai.exploration import UtilityExplorer   # AI stage
            self.explorer = UtilityExplorer(self.grid, self.robot.radius, self.rng, ai)
        self.ai = ai
        self.home_cell = self.grid.to_cell(*self.world.start)
        follower = PathFollower(self.grid)
        self.arbiter = Arbiter([
            EmergencyStop(), BumperEscape(), CliffStop(), SlopeRefuse(), InitialScan(),
            AvoidObstacle(), ReturnHome(follower), Explore(follower), Wander(),
        ])
        self.ctx = Context(self)
        self.step_count = 0
        self.time = 0.0
        self.returning = False
        self.finished = False
        self.stats = {"bumps": 0, "cliff_events": 0, "return_reason": ""}
        self.cmd = (0.0, 0.0)
        self.true_path = [self.robot.pose.copy()]
        self.est_path = [self.estimator.pose.copy()]
        self.odom_path = [self.estimator.odom.copy()]

    # ---------------------------------------------------------------- status
    @property
    def status(self) -> str:
        if self.robot.fell:
            return "fell"
        if self.robot.battery.energy_wh <= 0:
            return "battery_dead"
        if self.finished:
            return "returned"
        return "returning" if self.returning else "exploring"

    @property
    def done(self) -> bool:
        return self.status in ("fell", "battery_dead", "returned")

    def coverage(self) -> float:
        """Fraction of the reachable world the robot has mapped."""
        known = ~self.grid.unknown_mask()
        return float((known & self.world.reachable).sum() / max(1, self.world.reachable_count))

    def metrics(self) -> dict:
        return {
            "env": self.cfg.name, "strategy": self.explorer.name, "seed": self.seed,
            "status": self.status, "time_s": round(self.time, 1), "steps": self.step_count,
            "coverage": round(self.coverage(), 4), "path_length_m": round(self.robot.distance, 2),
            "backtracks": self.explorer.backtracks, "collisions": self.robot.collisions,
            "bumps": self.stats["bumps"], "cliff_events": self.stats["cliff_events"],
            "energy_wh": round(self.cfg.battery_wh - self.robot.battery.energy_wh, 3),
            "loc_error_m": round(self.estimator.error(), 3),
            "loc_error_mean_m": round(float(np.mean(self.estimator.error_history)), 3) if self.estimator.error_history else 0.0,
            "return_reason": self.stats["return_reason"],
        }

    # ------------------------------------------------------------------ step
    def step(self):
        if self.done:
            self.robot.drive.stop()
            return
        v, w = self.arbiter.decide(self.ctx)
        self.cmd = (v, w)
        self.robot.drive.set_velocity(v, w)
        self.robot.step(self.dt)
        self.estimator.update(self.dt)
        self.mapper.update(self.estimator.pose)
        if self.ai is not None:
            self.ai.observe(self)
        self.step_count += 1
        self.time += self.dt
        if self.step_count % 4 == 0:
            self.true_path.append(self.robot.pose.copy())
            self.est_path.append(self.estimator.pose.copy())
            self.odom_path.append(self.estimator.odom.copy())

    def run(self, max_steps: int = 12000) -> dict:
        while not self.done and self.step_count < max_steps:
            self.step()
        return self.metrics()
