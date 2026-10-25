"""One exploration run: world + robot + estimator + map + explorer + behaviours."""
from __future__ import annotations

import math

import numpy as np

from .behaviors import (Arbiter, AvoidObstacle, BumperEscape, CliffStop, Context, EmergencyStop,
                        Explore, InitialScan, PathFollower, ReturnHome, SlopeRefuse, Teleop, Wander)
from .comms import RadioLink
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
            AvoidObstacle(), Teleop(), ReturnHome(follower), Explore(follower), Wander(),
        ])
        self.ctx = Context(self)
        self.step_count = 0
        self.time = 0.0
        self.returning = False
        self.finished = False
        self.stats = {"bumps": 0, "cliff_events": 0, "return_reason": ""}
        self.cmd = (0.0, 0.0)
        # ---- teleoperation
        self.mode = "autonomous"            # "autonomous" | "assisted" | "manual" (what the operator chose)
        self.on_link_loss = "explore"       # "hold" | "explore" | "home": what the robot does when the link drops
        self.link = RadioLink(self.world, self.cfg.link, self.rng)
        self.operator_cmd = (0.0, 0.0)
        self.operator_cmd_time = -10.0
        self.link_fallback = False          # True while autonomy has taken over because the link was lost
        self.operator_speed = 0.35          # m/s at full stick
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

    # --------------------------------------------------------- teleoperation
    @property
    def effective_mode(self) -> str:
        """The operator's mode, unless the link is gone and autonomy took over."""
        if self.mode == "autonomous" or self.link_fallback:
            return "autonomous"
        return self.mode

    def operator_drive(self, forward: float, turn: float) -> bool:
        """Stick input in [-1, 1] each, sent over the radio link. Returns
        False when the packet was dropped."""
        forward = max(-1.0, min(1.0, forward))
        turn = max(-1.0, min(1.0, turn))
        return self.link.send({"type": "drive", "v": forward * self.operator_speed, "w": turn * 1.5}, self.time)

    def operator_command(self, command: dict) -> bool:
        """Any other operator command (mode, lights, stop, home), over the link."""
        return self.link.send(command, self.time)

    def _apply_operator(self, c: dict):
        t = c.get("type")
        if t == "drive":
            self.operator_cmd = (c["v"], c["w"])
            self.operator_cmd_time = self.time
            if self.link_fallback:
                self.link_fallback = False          # the operator is back
                self.returning = False if self.stats["return_reason"] == "link lost" else self.returning
        elif t == "mode":
            self.mode = c["mode"]
            self.link_fallback = False
            self.operator_cmd = (0.0, 0.0)
        elif t == "lights":
            self.robot.headlights = bool(c["on"])
        elif t == "stop":
            self.operator_cmd = (0.0, 0.0)
            self.operator_cmd_time = self.time
        elif t == "home":
            self.mode = "autonomous"
            self.returning = True
            self.stats["return_reason"] = "operator"
        elif t == "link_loss":
            self.on_link_loss = c["action"]

    def _update_link(self):
        self.link.update(self.robot.pose, self.time)
        for c in self.link.receive(self.time):
            self._apply_operator(c)
        if self.mode != "autonomous" and not self.link_fallback and self.link.lost_for(self.time) > 3.0:
            # three seconds without a radio link: the robot is on its own
            self.link_fallback = True
            self.operator_cmd = (0.0, 0.0)
            self.stats["link_losses"] = self.stats.get("link_losses", 0) + 1
            if self.on_link_loss == "home":
                self.returning = True
                self.stats["return_reason"] = "link lost"
            elif self.on_link_loss == "hold":
                self.explorer.done = False      # Teleop stays active with a zero command -> robot waits
        if self.link_fallback and self.on_link_loss == "hold":
            return "hold"
        return None

    # ------------------------------------------------------------------ step
    def step(self):
        if self.done:
            self.robot.drive.stop()
            return
        hold = self._update_link()
        if hold == "hold":
            v, w = 0.0, 0.0
            self.arbiter.active_name = "HOLD"
        else:
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
