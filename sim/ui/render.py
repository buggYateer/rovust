"""Drawing the true world, the belief map, the robot and the sensor overlays."""
from __future__ import annotations

import math

import numpy as np
import pygame

from ..core import TERRAIN, Terrain
from ..sensors.camera import CLASSES
from . import theme as T

TERRAIN_RGB = np.array([TERRAIN[Terrain(i)].color for i in range(len(Terrain))], dtype=np.uint8)
CLASS_RGB = {"ground": (205, 200, 190), "sand": (225, 190, 120), "rock": (120, 100, 90), "mud": (110, 85, 60),
             "bedrock": (150, 150, 160), "water": (40, 90, 140), "pit": (20, 15, 15)}


class MapView:
    """Maps world coordinates to a screen rectangle at a uniform scale."""

    def __init__(self, rect: pygame.Rect, world):
        self.rect = pygame.Rect(rect)
        self.world = world
        self.scale = min(rect.w / (world.w * world.cell), rect.h / (world.h * world.cell))
        self.px_w = int(world.w * world.cell * self.scale)
        self.px_h = int(world.h * world.cell * self.scale)
        self.origin = (rect.x + (rect.w - self.px_w) // 2, rect.y + (rect.h - self.px_h) // 2)

    def to_px(self, x: float, y: float) -> tuple[int, int]:
        # world y grows upward on screen
        return (int(self.origin[0] + x * self.scale), int(self.origin[1] + self.px_h - y * self.scale))

    def cells_to_surface(self, rgb: np.ndarray) -> pygame.Surface:
        """rgb: (h, w, 3) uint8 in grid orientation -> scaled surface."""
        surf = pygame.surfarray.make_surface(np.transpose(rgb[::-1], (1, 0, 2)))
        return pygame.transform.scale(surf, (self.px_w, self.px_h))

    def blit_cells(self, screen, rgb):
        screen.blit(self.cells_to_surface(rgb), self.origin)


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


def draw_path(screen, view: MapView, poses, color, width=2):
    if len(poses) < 2:
        return
    pts = [view.to_px(p.x, p.y) for p in poses]
    pygame.draw.lines(screen, color, False, pts, width)


def draw_cell_path(screen, view: MapView, grid, cells, color):
    if not cells or len(cells) < 2:
        return
    pts = [view.to_px(*grid.to_world(*c)) for c in cells]
    pygame.draw.lines(screen, color, False, pts, 2)


def draw_robot(screen, view: MapView, pose, radius, color=T.ACCENT2, outline=T.WHITE):
    cx, cy = view.to_px(pose.x, pose.y)
    r = max(3, int(radius * view.scale))
    pygame.draw.circle(screen, color, (cx, cy), r)
    pygame.draw.circle(screen, outline, (cx, cy), r, 1)
    hx, hy = view.to_px(pose.x + radius * math.cos(pose.theta), pose.y + radius * math.sin(pose.theta))
    pygame.draw.line(screen, outline, (cx, cy), (hx, hy), 2)


def draw_sensor_rays(screen, view: MapView, robot, show_sonar=True, show_ir=True):
    suite = robot.sensors
    if show_sonar:
        for s in suite.sonars:
            x, y, a = s.world_position(robot)
            col = T.BAD if not s.healthy else ((120, 200, 255) if s.value < s.max_range * 0.98 else (70, 90, 120))
            end = (x + s.value * math.cos(a), y + s.value * math.sin(a))
            pygame.draw.line(screen, col, view.to_px(x, y), view.to_px(*end), 1)
            if s.value < s.max_range * 0.98:
                pygame.draw.circle(screen, col, view.to_px(*end), 2)
    if show_ir:
        for s in suite.irs:
            x, y, a = s.world_position(robot)
            col = T.BAD if not s.healthy else (255, 120, 120)
            end = (x + s.value * math.cos(a), y + s.value * math.sin(a))
            pygame.draw.line(screen, col, view.to_px(x, y), view.to_px(*end), 1)
    for c in suite.cliffs:
        x, y = robot.body_point(c.dx, c.dy)
        pygame.draw.circle(screen, T.BAD if c.value > 0.5 else (90, 200, 120), view.to_px(x, y), 3)


def draw_frontiers(screen, view: MapView, grid, frontiers, target):
    for f in frontiers:
        for x, y in f.cells[::2]:
            px, py = view.to_px(*grid.to_world(int(x), int(y)))
            screen.set_at((px, py), (255, 220, 90))
    if target is not None:
        px, py = view.to_px(*grid.to_world(*target))
        pygame.draw.circle(screen, (255, 220, 90), (px, py), 5, 2)


def camera_surface(img: np.ndarray, size: int) -> pygame.Surface:
    g = (np.clip(img, 0, 1) * 255).astype(np.uint8)
    rgb = np.stack([g, g, g], -1)
    surf = pygame.surfarray.make_surface(np.transpose(rgb, (1, 0, 2)))
    return pygame.transform.scale(surf, (size, size))
