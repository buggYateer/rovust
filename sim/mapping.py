"""The robot's own map: a log-odds occupancy grid plus terrain and hazard layers.

Every cell holds log(p/(1-p)) that it is occupied. Each range reading lowers
the odds of the cells along the beam and raises the odds of the end cell, so
noisy single readings average out instead of flipping the map.
"""
from __future__ import annotations

import math

import numpy as np

from .core import Pose

L_FREE = -0.4
L_OCC = 0.7
L_MAX = 5.0
P_FREE = 0.35
P_OCC = 0.65


class OccupancyGrid:
    def __init__(self, width: int, height: int, cell: float):
        self.w, self.h, self.cell = width, height, cell
        self.logodds = np.zeros((height, width), np.float32)
        self.terrain_cost = np.ones((height, width), np.float32)   # from the AI classifier
        self.terrain_label = np.full((height, width), -1, np.int8)
        self.hazard = np.zeros((height, width), bool)               # cliffs, gas
        self.visited = np.zeros((height, width), bool)
        self.updates = 0

    # ------------------------------------------------------------- queries
    def to_cell(self, x: float, y: float) -> tuple[int, int]:
        return int(x / self.cell), int(y / self.cell)

    def to_world(self, cx: int, cy: int) -> tuple[float, float]:
        return (cx + 0.5) * self.cell, (cy + 0.5) * self.cell

    def in_bounds(self, cx: int, cy: int) -> bool:
        return 0 <= cx < self.w and 0 <= cy < self.h

    @property
    def prob(self) -> np.ndarray:
        return 1.0 / (1.0 + np.exp(-self.logodds))

    def free_mask(self) -> np.ndarray:
        return (self.prob < P_FREE) & ~self.hazard

    def occupied_mask(self) -> np.ndarray:
        return (self.prob > P_OCC) | self.hazard

    def unknown_mask(self) -> np.ndarray:
        p = self.prob
        return (p >= P_FREE) & (p <= P_OCC) & ~self.hazard

    def known_count(self) -> int:
        return int((~self.unknown_mask()).sum())

    def is_free(self, cx: int, cy: int) -> bool:
        return self.in_bounds(cx, cy) and self.logodds[cy, cx] < math.log(P_FREE / (1 - P_FREE)) and not self.hazard[cy, cx]

    def is_occupied(self, cx: int, cy: int) -> bool:
        return (not self.in_bounds(cx, cy)) or self.logodds[cy, cx] > math.log(P_OCC / (1 - P_OCC)) or self.hazard[cy, cx]

    # ------------------------------------------------------------- updates
    def _cells_along(self, x0, y0, angle, dist):
        n = max(1, int(dist / (self.cell * 0.5)))
        xs = x0 + np.cos(angle) * np.linspace(0, dist, n, endpoint=False)
        ys = y0 + np.sin(angle) * np.linspace(0, dist, n, endpoint=False)
        cx = (xs / self.cell).astype(int)
        cy = (ys / self.cell).astype(int)
        ok = (cx >= 0) & (cx < self.w) & (cy >= 0) & (cy < self.h)
        return cx[ok], cy[ok]

    def update_beam(self, x0: float, y0: float, angle: float, dist: float, hit: bool, weight: float = 1.0):
        cx, cy = self._cells_along(x0, y0, angle, max(0.0, dist - self.cell * 0.5))
        self.logodds[cy, cx] = np.maximum(-L_MAX, self.logodds[cy, cx] + L_FREE * weight)
        if hit:
            ex, ey = self.to_cell(x0 + math.cos(angle) * dist, y0 + math.sin(angle) * dist)
            if self.in_bounds(ex, ey):
                self.logodds[ey, ex] = min(L_MAX, self.logodds[ey, ex] + L_OCC * weight)
        self.updates += 1

    def mark_visited(self, pose: Pose, radius: float):
        cx, cy = self.to_cell(pose.x, pose.y)
        r = max(1, int(math.ceil(radius / self.cell)))
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                x, y = cx + dx, cy + dy
                if not self.in_bounds(x, y):
                    continue
                wx, wy = self.to_world(x, y)
                # only cells whose centre is really under the body
                if (wx - pose.x) ** 2 + (wy - pose.y) ** 2 <= (radius * 0.9) ** 2:
                    self.visited[y, x] = True
                    self.logodds[y, x] = min(self.logodds[y, x], -1.0)

    def mark_hazard(self, x: float, y: float, radius_cells: int = 1):
        cx, cy = self.to_cell(x, y)
        for dy in range(-radius_cells, radius_cells + 1):
            for dx in range(-radius_cells, radius_cells + 1):
                if self.in_bounds(cx + dx, cy + dy):
                    self.hazard[cy + dy, cx + dx] = True

    def set_terrain(self, x: float, y: float, label: int, cost: float, radius_cells: int = 1):
        cx, cy = self.to_cell(x, y)
        for dy in range(-radius_cells, radius_cells + 1):
            for dx in range(-radius_cells, radius_cells + 1):
                if self.in_bounds(cx + dx, cy + dy):
                    self.terrain_label[cy + dy, cx + dx] = label
                    self.terrain_cost[cy + dy, cx + dx] = cost


class Mapper:
    """Feeds the sensor suite into the grid using the *estimated* pose."""

    def __init__(self, grid: OccupancyGrid, robot):
        self.grid = grid
        self.robot = robot

    def update(self, est: Pose):
        r = self.robot
        suite = r.sensors
        c, s = math.cos(est.theta), math.sin(est.theta)

        def at(dx, dy):
            return est.x + dx * c - dy * s, est.y + dx * s + dy * c

        for sn in suite.sonars:
            if not sn.healthy:
                continue
            x, y = at(sn.dx, sn.dy)
            hit = sn.value < sn.max_range * 0.98
            if not hit:
                # A missing echo is usually a lost (specular) reflection off a
                # wall at a grazing angle, not free space: leave the beam unknown.
                continue
            # the cone: the axis clears the beam and places the obstacle; the
            # cone edges only weakly clear the near part, because an edge ray
            # may have grazed a wall the axis ray did not see
            self.grid.update_beam(x, y, est.theta + sn.angle, sn.value, True, weight=1.0)
            for k in (-1, 1):
                self.grid.update_beam(x, y, est.theta + sn.angle + k * sn.cone / 2, 0.7 * sn.value,
                                      False, weight=0.25)
        for ir in suite.irs:
            if not ir.healthy:
                continue
            x, y = at(ir.dx, ir.dy)
            hit = ir.value < ir.max_range * 0.95
            self.grid.update_beam(x, y, est.theta + ir.angle, ir.value, hit, weight=0.8)
        for cl in suite.cliffs:
            if cl.healthy and cl.value > 0.5:
                x, y = at(cl.dx, cl.dy)
                self.grid.mark_hazard(x, y, 1)
        if suite.gas is not None and suite.gas.healthy and suite.gas.value > 0.5:
            self.grid.mark_hazard(est.x, est.y, 2)
        self.grid.mark_visited(est, r.radius)
