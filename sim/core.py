"""Shared primitives: pose, angles, terrain table."""
from __future__ import annotations

import math
from dataclasses import dataclass
from enum import IntEnum


def wrap_angle(a: float) -> float:
    """Wrap an angle to (-pi, pi]."""
    return (a + math.pi) % (2 * math.pi) - math.pi


@dataclass
class Pose:
    x: float = 0.0  # metres
    y: float = 0.0  # metres
    theta: float = 0.0  # radians, 0 = +x, counter-clockwise

    def copy(self) -> "Pose":
        return Pose(self.x, self.y, self.theta)

    def distance_to(self, other: "Pose") -> float:
        return math.hypot(self.x - other.x, self.y - other.y)

    def as_tuple(self):
        return (self.x, self.y, self.theta)


class Terrain(IntEnum):
    """Cell classes of the true world map."""
    FREE = 0      # plain ground
    WALL = 1      # solid obstacle (cave wall, reef)
    ROCK = 2      # small solid obstacle (boulder)
    SAND = 3      # traversable, slow, high wheel slip
    MUD = 4       # traversable, very slow, high slip
    BEDROCK = 5   # traversable, fast, low slip
    PIT = 6       # crater / hole: entering it ends the mission (cliff sensors must catch it)
    WATER = 7     # underwater: open water (free)


@dataclass(frozen=True)
class TerrainProps:
    name: str
    traversable: bool
    move_cost: float   # multiplier used by the planner
    slip: float        # fraction of wheel motion lost to slip (0..1)
    load: float        # extra motor load (0..1) -> lowers steady-state speed
    color: tuple       # RGB for the renderer
    camera_class: str  # label the camera/AI sees ("" = not a terrain class)


TERRAIN: dict[Terrain, TerrainProps] = {
    Terrain.FREE:    TerrainProps("free",    True,  1.0, 0.02, 0.00, (205, 200, 190), "ground"),
    Terrain.WALL:    TerrainProps("wall",    False, 0.0, 0.00, 0.00, (60, 55, 50),    ""),
    Terrain.ROCK:    TerrainProps("rock",    False, 0.0, 0.00, 0.00, (120, 100, 90),  "rock"),
    Terrain.SAND:    TerrainProps("sand",    True,  2.5, 0.25, 0.30, (225, 190, 120), "sand"),
    Terrain.MUD:     TerrainProps("mud",     True,  4.0, 0.40, 0.50, (110, 85, 60),   "mud"),
    Terrain.BEDROCK: TerrainProps("bedrock", True,  0.8, 0.00, 0.00, (150, 150, 160), "bedrock"),
    Terrain.PIT:     TerrainProps("pit",     False, 0.0, 0.00, 0.00, (20, 15, 15),    "pit"),
    Terrain.WATER:   TerrainProps("water",   True,  1.0, 0.30, 0.10, (40, 90, 140),   "water"),
}

OBSTACLES = {Terrain.WALL, Terrain.ROCK}
HAZARDS = {Terrain.PIT}
