"""Path planning and exploration target selection on the robot's own map.

* ``build_costmap``  - inflate obstacles by the robot radius (configuration
                       space), add a proximity penalty so paths stay centred,
                       multiply by the terrain cost from the AI layer.
* ``astar``          - 8-connected A* with an octile heuristic.
* ``find_frontiers`` - boundary cells between known-free and unknown space,
                       clustered into targets.
* ``FrontierExplorer`` / ``DFSExplorer`` - the two strategies compared in the
                       experiments. ``UtilityExplorer`` (AI stage) subclasses
                       FrontierExplorer with a learned/utility score.
"""
from __future__ import annotations

import heapq
import math
from dataclasses import dataclass, field

import numpy as np
from scipy import ndimage

from .core import Pose
from .mapping import OccupancyGrid

UNKNOWN_COST = 8.0      # unknown cells may be crossed, but known-free is strongly preferred
PROXIMITY_COST = 1.5    # extra cost right next to the inflated obstacle band


@dataclass
class CostMap:
    cost: np.ndarray        # float, inf = not traversable
    blocked: np.ndarray     # bool, inflated obstacles + hazards
    unknown: np.ndarray


def build_costmap(grid: OccupancyGrid, robot_radius: float) -> CostMap:
    occ = grid.occupied_mask()
    r_cells = max(1, int(round(robot_radius / grid.cell)))
    blocked = ndimage.binary_dilation(occ, iterations=r_cells)
    near = ndimage.binary_dilation(blocked, iterations=1) & ~blocked
    unknown = grid.unknown_mask()
    cost = np.where(unknown, UNKNOWN_COST, 1.0).astype(np.float32)
    cost *= grid.terrain_cost
    cost[near] += PROXIMITY_COST
    cost[blocked] = np.inf
    return CostMap(cost, blocked, unknown)


_NBRS = [(1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
         (1, 1, math.sqrt(2)), (1, -1, math.sqrt(2)), (-1, 1, math.sqrt(2)), (-1, -1, math.sqrt(2))]


def astar(cm: CostMap, start: tuple[int, int], goal: tuple[int, int], max_expansions: int = 60000):
    """Return a list of (cx, cy) from start to goal, or None."""
    h, w = cm.cost.shape
    sx, sy = start
    gx, gy = goal
    if not (0 <= gx < w and 0 <= gy < h) or not (0 <= sx < w and 0 <= sy < h):
        return None
    if np.isinf(cm.cost[gy, gx]):
        return None

    def heur(x, y):
        dx, dy = abs(x - gx), abs(y - gy)
        return (dx + dy) + (math.sqrt(2) - 2) * min(dx, dy)

    g = {start: 0.0}
    parent = {}
    open_ = [(heur(sx, sy), 0.0, start)]
    closed = set()
    n = 0
    while open_:
        f, gc, cur = heapq.heappop(open_)
        if cur in closed:
            continue
        if cur == goal:
            path = [cur]
            while cur in parent:
                cur = parent[cur]
                path.append(cur)
            return path[::-1]
        closed.add(cur)
        n += 1
        if n > max_expansions:
            return None
        x, y = cur
        for dx, dy, d in _NBRS:
            nx_, ny_ = x + dx, y + dy
            if not (0 <= nx_ < w and 0 <= ny_ < h):
                continue
            c = cm.cost[ny_, nx_]
            if np.isinf(c):
                continue
            if dx and dy and (np.isinf(cm.cost[y, nx_]) or np.isinf(cm.cost[ny_, x])):
                continue        # no cutting corners through blocked cells
            ng = gc + d * c
            nxt = (nx_, ny_)
            if ng < g.get(nxt, math.inf):
                g[nxt] = ng
                parent[nxt] = cur
                heapq.heappush(open_, (ng + heur(nx_, ny_), ng, nxt))
    return None


def nearest_free_cell(cm: CostMap, cell: tuple[int, int], max_r: int = 6):
    """If the robot's own cell is inside the inflated band (it happens after
    a bump), find the nearest traversable cell to plan from."""
    x0, y0 = cell
    if not np.isinf(cm.cost[y0, x0]):
        return cell
    h, w = cm.cost.shape
    for r in range(1, max_r + 1):
        for dy in range(-r, r + 1):
            for dx in range(-r, r + 1):
                x, y = x0 + dx, y0 + dy
                if 0 <= x < w and 0 <= y < h and not np.isinf(cm.cost[y, x]):
                    return (x, y)
    return None


# ----------------------------------------------------------------- frontiers
@dataclass
class Frontier:
    cells: np.ndarray           # (n, 2) as (cx, cy)
    centroid: tuple[float, float]
    size: int
    target: tuple[int, int]     # the frontier cell closest to the centroid


def find_frontiers(grid: OccupancyGrid, cm: CostMap, min_size: int = 2) -> list[Frontier]:
    free = grid.free_mask() & ~cm.blocked
    unknown = cm.unknown
    unknown_nb = ndimage.binary_dilation(unknown, structure=np.ones((3, 3), bool))
    frontier = free & unknown_nb
    labels, n = ndimage.label(frontier, structure=np.ones((3, 3), bool))
    out = []
    for i in range(1, n + 1):
        ys, xs = np.nonzero(labels == i)
        if len(xs) < min_size:
            continue
        cx, cy = xs.mean(), ys.mean()
        k = int(np.argmin((xs - cx) ** 2 + (ys - cy) ** 2))
        out.append(Frontier(np.stack([xs, ys], 1), (cx, cy), len(xs), (int(xs[k]), int(ys[k]))))
    return out


# ---------------------------------------------------------------- explorers
class Explorer:
    name = "base"

    def __init__(self, grid: OccupancyGrid, robot_radius: float, rng: np.random.Generator):
        self.grid = grid
        self.robot_radius = robot_radius
        self.rng = rng
        self.target: tuple[int, int] | None = None
        self.path: list[tuple[int, int]] | None = None
        self.blacklist: dict[tuple[int, int], int] = {}
        self.backtracks = 0
        self.done = False
        self.frontiers: list[Frontier] = []

    def plan(self, pose: Pose, step: int) -> list[tuple[int, int]] | None:
        raise NotImplementedError

    def target_reached(self, pose: Pose, tol: float = 0.35) -> bool:
        if self.target is None:
            return False
        tx, ty = self.grid.to_world(*self.target)
        return math.hypot(tx - pose.x, ty - pose.y) < tol

    def _route(self, cm: CostMap, pose: Pose, goal: tuple[int, int]):
        start = nearest_free_cell(cm, self.grid.to_cell(pose.x, pose.y))
        if start is None:
            return None
        return astar(cm, start, goal)


class FrontierExplorer(Explorer):
    """Nearest-frontier: go to the closest boundary between known and unknown."""
    name = "frontier"

    def score(self, f: Frontier, pose: Pose, cm: CostMap) -> float:
        tx, ty = self.grid.to_world(*f.target)
        return -math.hypot(tx - pose.x, ty - pose.y)        # nearest wins

    def plan(self, pose: Pose, step: int):
        cm = build_costmap(self.grid, self.robot_radius)
        self.frontiers = find_frontiers(self.grid, cm)
        self.blacklist = {k: v for k, v in self.blacklist.items() if v > step}
        # stay committed to the current target while it is still a frontier,
        # otherwise the robot oscillates between two equally near frontiers
        if self.target is not None and self.target not in self.blacklist and not self.target_reached(pose):
            tx, ty = self.target
            still = any(((f.cells[:, 0] == tx) & (f.cells[:, 1] == ty)).any() for f in self.frontiers)
            if still:
                path = self._route(cm, pose, self.target)
                if path:
                    self.path = path
                    return path
                self.blacklist[self.target] = step + 400
        cands = [f for f in self.frontiers if f.target not in self.blacklist]
        cands.sort(key=lambda f: -self.score(f, pose, cm))
        for f in cands[:6]:
            path = self._route(cm, pose, f.target)
            if path:
                self.target, self.path = f.target, path
                return path
            self.blacklist[f.target] = step + 400
        self.target, self.path = None, None
        # finished only once the map has substance and nothing is left to see;
        # frontiers that are merely blacklisted may become reachable later
        self.done = not self.frontiers and self.grid.known_count() > 80 and step > 200
        return None


class DFSExplorer(Explorer):
    """Depth-first search with backtracking on a graph of waypoints.

    Nodes are world points. From the node the robot stands on, try to step
    ``STEP`` metres in each of the four world directions (forward first,
    then left, right, back). A direction is open if the straight segment
    does not cross known obstacles and leads somewhere not visited yet.
    Dead end -> pop the stack and drive back to the previous node: that is a
    'backtracking event'. When the whole stack is exhausted but unknown
    space is still reachable, the search restarts from the nearest frontier
    (otherwise a single closed loop would end the mission)."""
    name = "dfs"
    STEP = 1.0          # metres between nodes
    VISIT_R = 0.55      # a point closer than this to a visited node counts as visited

    def __init__(self, grid, robot_radius, rng):
        super().__init__(grid, robot_radius, rng)
        self.stack: list[tuple[float, float]] = []
        self.visited: list[tuple[float, float]] = []

    def _is_visited(self, p):
        return any(math.hypot(p[0] - v[0], p[1] - v[1]) < self.VISIT_R for v in self.visited)

    def _segment_open(self, cm: CostMap, a, b) -> bool:
        h, w = cm.cost.shape
        n = int(math.hypot(b[0] - a[0], b[1] - a[1]) / self.grid.cell) + 2
        for t in np.linspace(0, 1, n):
            cx, cy = self.grid.to_cell(a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t)
            if not (0 <= cx < w and 0 <= cy < h) or np.isinf(cm.cost[cy, cx]):
                return False
        return True

    def plan(self, pose: Pose, step: int):
        cm = build_costmap(self.grid, self.robot_radius)
        self.frontiers = find_frontiers(self.grid, cm)
        here = (pose.x, pose.y)
        if not self.stack:
            self.stack.append(here)
            self.visited.append(here)
        cur = self.stack[-1]
        # heading-relative order: forward, left, right, back
        hx, hy = round(math.cos(pose.theta)), round(math.sin(pose.theta))
        if hx == 0 and hy == 0:
            hx = 1
        for dx, dy in [(hx, hy), (-hy, hx), (hy, -hx), (-hx, -hy)]:
            for length in (self.STEP, 0.6 * self.STEP):
                nxt = (cur[0] + dx * length, cur[1] + dy * length)
                if self._is_visited(nxt) or not self._segment_open(cm, cur, nxt):
                    continue
                goal = self.grid.to_cell(*nxt)
                path = self._route(cm, pose, goal)
                if path:
                    self.visited.append(nxt)
                    self.stack.append(nxt)
                    self.target, self.path = goal, path
                    return path
        # dead end: backtrack to the previous node
        self.stack.pop()
        if self.stack:
            self.backtracks += 1
            goal = self.grid.to_cell(*self.stack[-1])
            path = self._route(cm, pose, goal)
            self.target, self.path = goal, path
            return path
        # stack exhausted: restart from the nearest reachable frontier
        self.blacklist = {k: v for k, v in self.blacklist.items() if v > step}
        cands = [f for f in self.frontiers if f.target not in self.blacklist]
        cands.sort(key=lambda f: math.hypot(*(np.array(self.grid.to_world(*f.target)) - (pose.x, pose.y))))
        for f in cands[:6]:
            path = self._route(cm, pose, f.target)
            if path:
                node = self.grid.to_world(*f.target)
                self.stack.append(node)
                self.visited.append(node)
                self.target, self.path = f.target, path
                return path
            self.blacklist[f.target] = step + 400
        self.target, self.path = None, None
        self.done = not self.frontiers and self.grid.known_count() > 80 and step > 200
        if not self.done:
            self.stack.append(here)
        return None
