"""AI 2: utility-based frontier selection.

Nearest-frontier is greedy on distance only. The utility explorer scores
each frontier cluster by

    U = information_gain / (path_cost + k)  -  hazard_penalty  -  battery_penalty

where information gain is the number of unknown cells around the frontier
(how much we expect to learn), path cost is the A* cost through the terrain
layer (so sand and mud count), hazard penalty grows near known hazards and
the battery penalty discourages far targets when energy is low. The
weights are tuned by experiment (see experiments/), which is the
"learning" part: a grid search over (w_gain, w_cost) on the batch runs.
"""
from __future__ import annotations

import math

import numpy as np
from scipy import ndimage

from ..core import Pose
from ..planning import CostMap, Frontier, FrontierExplorer, astar, nearest_free_cell


class UtilityExplorer(FrontierExplorer):
    name = "utility"

    def __init__(self, grid, robot_radius, rng, ai=None, w_gain: float = 1.0, w_cost: float = 1.0,
                 w_hazard: float = 2.0):
        super().__init__(grid, robot_radius, rng)
        self.ai = ai
        self.w_gain, self.w_cost, self.w_hazard = w_gain, w_cost, w_hazard
        self.battery_fraction = 1.0
        self._hazard_near = None

    def _information_gain(self, f: Frontier, cm: CostMap) -> float:
        x, y = f.target
        r = 6
        sub = cm.unknown[max(0, y - r):y + r + 1, max(0, x - r):x + r + 1]
        return float(sub.sum()) + f.size

    def score(self, f: Frontier, pose: Pose, cm: CostMap) -> float:
        tx, ty = self.grid.to_world(*f.target)
        dist = math.hypot(tx - pose.x, ty - pose.y)
        # terrain-aware distance: the straight line sampled on the cost layer
        n = max(2, int(dist / self.grid.cell))
        xs = np.linspace(pose.x, tx, n) / self.grid.cell
        ys = np.linspace(pose.y, ty, n) / self.grid.cell
        cx = np.clip(xs.astype(int), 0, self.grid.w - 1)
        cy = np.clip(ys.astype(int), 0, self.grid.h - 1)
        terrain = float(np.mean(self.grid.terrain_cost[cy, cx]))
        cost = dist * terrain
        if self._hazard_near is None or self._hazard_near.shape != cm.blocked.shape:
            self._hazard_near = ndimage.binary_dilation(self.grid.hazard, iterations=3)
        hazard = 1.0 if self._hazard_near[f.target[1], f.target[0]] else 0.0
        gain = self._information_gain(f, cm)
        battery_pen = (1.0 - self.battery_fraction) * dist * 0.5
        return self.w_gain * gain / (self.w_cost * cost + 1.0) - self.w_hazard * hazard - battery_pen

    def plan(self, pose: Pose, step: int):
        self._hazard_near = None
        return super().plan(pose, step)
