"""Colouring the true world and the belief map as RGB arrays (numpy only; no GUI toolkit)."""
from __future__ import annotations

import numpy as np

from .core import TERRAIN, Terrain
from .sensors.camera import CLASSES

TERRAIN_RGB = np.array([TERRAIN[Terrain(i)].color for i in range(len(Terrain))], dtype=np.uint8)
CLASS_RGB = {"ground": (205, 200, 190), "sand": (225, 190, 120), "rock": (120, 100, 90), "mud": (110, 85, 60),
             "bedrock": (150, 150, 160), "water": (40, 90, 140), "pit": (20, 15, 15)}


def world_rgb(world, light: float = 1.0) -> np.ndarray:
    rgb = TERRAIN_RGB[world.grid].astype(np.float32)
    gas = world.gas[..., None] * np.array([80, 160, 40], np.float32)
    rgb = np.clip(rgb * (0.55 + 0.45 * light) + gas, 0, 255)
    return rgb.astype(np.uint8)


def belief_rgb(grid, show_terrain=True, show_hazard=True, show_visited=False) -> np.ndarray:
    p = grid.prob
    g = (235 - p * 215).astype(np.uint8)           # free = light, occupied = dark
    rgb = np.stack([g, g, g], -1).astype(np.int16)
    unknown = grid.unknown_mask()
    rgb[unknown] = (52, 56, 70)
    if show_terrain:
        for i, c in enumerate(CLASSES):
            m = (grid.terrain_label == i) & ~unknown & (p < 0.5)
            rgb[m] = (np.array(CLASS_RGB[c]) * 0.6 + rgb[m] * 0.4).astype(np.int16)
    if show_visited:
        rgb[grid.visited] = (rgb[grid.visited] * 0.7 + np.array((60, 120, 200)) * 0.3).astype(np.int16)
    if show_hazard:
        rgb[grid.hazard] = (230, 60, 60)
    return np.clip(rgb, 0, 255).astype(np.uint8)
