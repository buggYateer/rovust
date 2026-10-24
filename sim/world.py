"""The true world. The robot never reads this directly; only sensors do."""
from __future__ import annotations

import math
from collections import deque

import numpy as np

from .config import EnvConfig
from .core import OBSTACLES, Terrain


class World:
    def __init__(self, cfg: EnvConfig):
        self.cfg = cfg
        self.w, self.h = cfg.width, cfg.height
        self.cell = cfg.cell_size
        self.rng = np.random.default_rng(cfg.seed)
        self.grid = np.full((self.h, self.w), Terrain.FREE, dtype=np.int8)
        self.gas = np.zeros((self.h, self.w), dtype=np.float32)      # 0..1 concentration
        self.slope = np.zeros((self.h, self.w), dtype=np.float32)    # tilt in radians
        self.start = (0.0, 0.0)
        self.time = 0.0
        generator = {"cave": self._gen_cave, "mars": self._gen_mars, "underwater": self._gen_underwater}[cfg.name]
        generator()
        self._ensure_connected()

    # ------------------------------------------------------------------ geometry
    def to_cell(self, x: float, y: float) -> tuple[int, int]:
        return int(x / self.cell), int(y / self.cell)

    def to_world(self, cx: int, cy: int) -> tuple[float, float]:
        return (cx + 0.5) * self.cell, (cy + 0.5) * self.cell

    def in_bounds(self, cx: int, cy: int) -> bool:
        return 0 <= cx < self.w and 0 <= cy < self.h

    def terrain_at(self, x: float, y: float) -> Terrain:
        cx, cy = self.to_cell(x, y)
        if not self.in_bounds(cx, cy):
            return Terrain.WALL
        return Terrain(self.grid[cy, cx])

    def is_obstacle(self, cx: int, cy: int) -> bool:
        return (not self.in_bounds(cx, cy)) or self.grid[cy, cx] in OBSTACLES

    def circle_hits_obstacle(self, x: float, y: float, r: float) -> bool:
        cx0, cy0 = self.to_cell(x - r, y - r)
        cx1, cy1 = self.to_cell(x + r, y + r)
        for cy in range(cy0, cy1 + 1):
            for cx in range(cx0, cx1 + 1):
                if self.is_obstacle(cx, cy):
                    # closest point of the cell to the circle centre
                    px = min(max(x, cx * self.cell), (cx + 1) * self.cell)
                    py = min(max(y, cy * self.cell), (cy + 1) * self.cell)
                    if (px - x) ** 2 + (py - y) ** 2 < r * r:
                        return True
        return False

    def circle_over_pit(self, x: float, y: float, r: float) -> bool:
        for dx, dy in ((r, 0), (-r, 0), (0, r), (0, -r), (0, 0)):
            if self.terrain_at(x + dx, y + dy) == Terrain.PIT:
                return True
        return False

    def raycast(self, x: float, y: float, angle: float, max_range: float):
        """March a ray through the grid.

        Returns (distance, normal_angle) of the first obstacle hit, or
        (max_range, None) if nothing is within range. Uses a DDA so the hit
        face (and hence the surface normal) is known, which the sonar model
        needs for specular reflection.
        """
        dx, dy = math.cos(angle), math.sin(angle)
        cx, cy = self.to_cell(x, y)
        if self.is_obstacle(cx, cy):
            return 0.0, angle + math.pi
        step_x = 1 if dx > 0 else -1
        step_y = 1 if dy > 0 else -1
        t_delta_x = abs(self.cell / dx) if dx != 0 else math.inf
        t_delta_y = abs(self.cell / dy) if dy != 0 else math.inf
        next_bx = (cx + (1 if dx > 0 else 0)) * self.cell
        next_by = (cy + (1 if dy > 0 else 0)) * self.cell
        t_max_x = (next_bx - x) / dx if dx != 0 else math.inf
        t_max_y = (next_by - y) / dy if dy != 0 else math.inf
        t = 0.0
        while t < max_range:
            if t_max_x < t_max_y:
                t = t_max_x
                t_max_x += t_delta_x
                cx += step_x
                normal = math.pi if step_x > 0 else 0.0
            else:
                t = t_max_y
                t_max_y += t_delta_y
                cy += step_y
                normal = -math.pi / 2 if step_y > 0 else math.pi / 2
            if t > max_range:
                break
            if self.is_obstacle(cx, cy):
                return t, normal
        return max_range, None

    # ---------------------------------------------------------------- generators
    def _border(self):
        self.grid[0, :] = Terrain.WALL
        self.grid[-1, :] = Terrain.WALL
        self.grid[:, 0] = Terrain.WALL
        self.grid[:, -1] = Terrain.WALL

    def _blob(self, cx, cy, r, terrain, prob=1.0):
        for y in range(max(0, int(cy - r)), min(self.h, int(cy + r + 1))):
            for x in range(max(0, int(cx - r)), min(self.w, int(cx + r + 1))):
                if (x - cx) ** 2 + (y - cy) ** 2 <= r * r and self.rng.random() < prob:
                    self.grid[y, x] = terrain

    def _gen_cave(self):
        """Maze-like cave: a DFS maze on a coarse lattice, corridors 3 cells wide,
        with occasional chambers, pits and gas pockets. Produces branching
        corridors and many dead ends, which is what DFS-with-backtracking is for."""
        self.grid[:] = Terrain.WALL
        pitch = 7                      # lattice spacing in cells
        cw = 4                         # corridor width (0.8 m for a 0.44 m robot)
        nx, ny = (self.w - 3) // pitch, (self.h - 3) // pitch
        visited = np.zeros((ny, nx), bool)
        stack = [(0, 0)]
        visited[0, 0] = True

        def carve(ax, ay, bx, by):
            x0, x1 = sorted((ax * pitch + 2, bx * pitch + 2))
            y0, y1 = sorted((ay * pitch + 2, by * pitch + 2))
            self.grid[y0:y1 + cw, x0:x1 + cw] = Terrain.FREE

        carve(0, 0, 0, 0)
        while stack:
            x, y = stack[-1]
            nbrs = [(x + dx, y + dy) for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1))
                    if 0 <= x + dx < nx and 0 <= y + dy < ny and not visited[y + dy, x + dx]]
            if not nbrs:
                stack.pop()
                continue
            nxt = nbrs[self.rng.integers(len(nbrs))]
            visited[nxt[1], nxt[0]] = True
            carve(x, y, *nxt)
            stack.append(nxt)
        # a few chambers
        for _ in range(4):
            cx, cy = self.rng.integers(6, self.w - 6), self.rng.integers(6, self.h - 6)
            self._blob(cx, cy, self.rng.integers(3, 5), Terrain.FREE)
        # rough walls: nibble some wall cells next to corridors so the sonar sees irregular surfaces
        free = self.grid == Terrain.FREE
        for _ in range(int(0.02 * self.w * self.h)):
            x, y = self.rng.integers(1, self.w - 1), self.rng.integers(1, self.h - 1)
            if self.grid[y, x] == Terrain.WALL and free[y - 1:y + 2, x - 1:x + 2].any():
                self.grid[y, x] = Terrain.ROCK if self.rng.random() < 0.3 else Terrain.FREE
        # mud patches, pits and gas pockets inside corridors
        free_cells = np.argwhere(self.grid == Terrain.FREE)
        for _ in range(5):
            y, x = free_cells[self.rng.integers(len(free_cells))]
            self._blob(x, y, 2, Terrain.MUD, prob=0.8)
        for _ in range(4):
            y, x = free_cells[self.rng.integers(len(free_cells))]
            if math.hypot(x - 3, y - 3) > 12:
                self._blob(x, y, 1.2, Terrain.PIT)
        for _ in range(3):
            y, x = free_cells[self.rng.integers(len(free_cells))]
            yy, xx = np.mgrid[0:self.h, 0:self.w]
            self.gas += np.exp(-((xx - x) ** 2 + (yy - y) ** 2) / (2 * 4.0 ** 2)).astype(np.float32)
        self.gas = np.clip(self.gas, 0, 1)
        self._border()
        self.start = self.to_world(3, 3)
        self.grid[2:5, 2:5] = Terrain.FREE

    def _gen_mars(self):
        """Open planetary surface: rock fields, craters with rims, sand and bedrock."""
        self.grid[:] = Terrain.FREE
        yy, xx = np.mgrid[0:self.h, 0:self.w]
        # sand dunes and bedrock as low-frequency noise
        field = np.zeros((self.h, self.w))
        for _ in range(6):
            cx, cy = self.rng.uniform(0, self.w), self.rng.uniform(0, self.h)
            s = self.rng.uniform(6, 14)
            field += self.rng.uniform(-1, 1) * np.exp(-((xx - cx) ** 2 + (yy - cy) ** 2) / (2 * s * s))
        self.grid[field > 0.35] = Terrain.SAND
        self.grid[field < -0.35] = Terrain.BEDROCK
        # craters: pit centre with a rocky rim
        for _ in range(5):
            cx, cy = self.rng.integers(10, self.w - 10), self.rng.integers(10, self.h - 10)
            r = self.rng.integers(2, 5)
            if math.hypot(cx - 4, cy - 4) < 10:
                continue
            self._blob(cx, cy, r + 1.5, Terrain.ROCK, prob=0.35)
            self._blob(cx, cy, r, Terrain.PIT)
            self.slope[max(0, cy - r - 2):cy + r + 3, max(0, cx - r - 2):cx + r + 3] = 0.25
        # rock fields
        for _ in range(14):
            cx, cy = self.rng.integers(3, self.w - 3), self.rng.integers(3, self.h - 3)
            if math.hypot(cx - 4, cy - 4) < 8:
                continue
            self._blob(cx, cy, self.rng.uniform(1, 3), Terrain.ROCK, prob=0.6)
        # a ridge wall to create partial enclosure
        for _ in range(3):
            x0 = self.rng.integers(10, self.w - 25)
            y0 = self.rng.integers(10, self.h - 10)
            length = self.rng.integers(10, 25)
            horizontal = self.rng.random() < 0.5
            for i in range(length):
                x, y = (x0 + i, y0) if horizontal else (x0, min(self.h - 2, y0 + i))
                if self.in_bounds(x, y):
                    self.grid[y, x] = Terrain.WALL
        self._border()
        self.start = self.to_world(4, 4)
        self.grid[2:7, 2:7] = Terrain.FREE

    def _gen_underwater(self):
        """Flooded site: cellular-automata reef walls, mud flats, open water."""
        self.grid[:] = Terrain.WATER
        noise = self.rng.random((self.h, self.w)) < 0.42
        for _ in range(4):
            padded = np.pad(noise, 1, constant_values=True)
            counts = sum(padded[1 + dy:self.h + 1 + dy, 1 + dx:self.w + 1 + dx]
                         for dy in (-1, 0, 1) for dx in (-1, 0, 1)) - padded[1:-1, 1:-1]
            noise = counts >= 5
        self.grid[noise] = Terrain.WALL
        free_cells = np.argwhere(self.grid == Terrain.WATER)
        for _ in range(6):
            y, x = free_cells[self.rng.integers(len(free_cells))]
            self._blob(x, y, self.rng.uniform(2, 4), Terrain.MUD, prob=0.85)
        self._border()
        self.start = self.to_world(4, 4)
        self.grid[2:7, 2:7] = Terrain.WATER

    def _ensure_connected(self):
        """Everything the robot cannot reach from the start becomes wall, so
        'coverage' statistics are measured against reachable area only."""
        sx, sy = self.to_cell(*self.start)
        reach = np.zeros_like(self.grid, dtype=bool)
        q = deque([(sx, sy)])
        reach[sy, sx] = True
        while q:
            x, y = q.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                nx_, ny_ = x + dx, y + dy
                if self.in_bounds(nx_, ny_) and not reach[ny_, nx_] and not self.is_obstacle(nx_, ny_) \
                        and self.grid[ny_, nx_] != Terrain.PIT:
                    reach[ny_, nx_] = True
                    q.append((nx_, ny_))
        unreachable = (~reach) & (~np.isin(self.grid, list(OBSTACLES))) & (self.grid != Terrain.PIT)
        self.grid[unreachable] = Terrain.WALL
        self.reachable = reach
        self.reachable_count = int(reach.sum())
