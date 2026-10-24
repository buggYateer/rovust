"""Forward camera tilted down: it sees a small ground patch ahead of the robot
and returns a tiny grayscale image (lecture: 60x80 is enough; we use 16x16).

The image is synthesised from the true terrain class with a texture model,
noise and the ambient light level. The AI terrain classifier is trained on
images produced by the same generator, so the classifier never touches the
true map: it only sees pixels.
"""
from __future__ import annotations

import numpy as np

from ..core import TERRAIN, Terrain
from .base import Sensor, SensorClass

PATCH = 16
CLASSES = ["ground", "sand", "rock", "mud", "bedrock", "water", "pit"]


def synth_patch(label: str, rng: np.random.Generator, light: float = 1.0) -> np.ndarray:
    """Procedural texture per terrain class, 16x16 floats in [0, 1]."""
    yy, xx = np.mgrid[0:PATCH, 0:PATCH] / PATCH
    if label == "ground":
        img = 0.55 + 0.08 * rng.standard_normal((PATCH, PATCH))
    elif label == "sand":
        # smooth ripples
        f, ph = rng.uniform(2, 4), rng.uniform(0, 6.28)
        img = 0.75 + 0.1 * np.sin(2 * np.pi * f * (xx * 0.8 + yy * 0.6) + ph) + 0.03 * rng.standard_normal((PATCH, PATCH))
    elif label == "rock":
        # high-contrast blobs with sharp edges
        img = np.full((PATCH, PATCH), 0.45)
        for _ in range(rng.integers(2, 5)):
            cx, cy, r = rng.uniform(0, 1), rng.uniform(0, 1), rng.uniform(0.12, 0.3)
            img[(xx - cx) ** 2 + (yy - cy) ** 2 < r * r] = rng.uniform(0.2, 0.35)
        img += 0.06 * rng.standard_normal((PATCH, PATCH))
    elif label == "mud":
        img = 0.3 + 0.04 * rng.standard_normal((PATCH, PATCH))
        img += 0.05 * np.sin(2 * np.pi * rng.uniform(1, 2) * yy)
    elif label == "bedrock":
        # flat, slightly brighter, with thin dark cracks
        img = np.full((PATCH, PATCH), 0.66)
        for _ in range(rng.integers(2, 4)):
            a, b = rng.uniform(0, 1), rng.uniform(-1, 1)
            img[np.abs(yy - (a + b * xx)) < 0.04] = 0.3
        img += 0.015 * rng.standard_normal((PATCH, PATCH))
    elif label == "water":
        # fine caustic ripples in both directions, smooth, no blobs
        img = 0.42 + 0.07 * np.sin(2 * np.pi * rng.uniform(4, 7) * xx + rng.uniform(0, 6)) \
            + 0.05 * np.sin(2 * np.pi * rng.uniform(3, 5) * yy + rng.uniform(0, 6)) \
            + 0.02 * rng.standard_normal((PATCH, PATCH))
    else:  # pit: dark, featureless, vignette
        img = 0.08 + 0.05 * (1 - ((xx - 0.5) ** 2 + (yy - 0.5) ** 2) * 2) + 0.02 * rng.standard_normal((PATCH, PATCH))
    img = img * (0.25 + 0.75 * light)
    img += (0.05 + 0.25 * (1 - light)) * rng.standard_normal((PATCH, PATCH))  # sensor noise in the dark
    return np.clip(img, 0, 1).astype(np.float32)


class Camera(Sensor):
    cls = SensorClass("local", "external", "passive", "digital")

    def __init__(self, name, rng, look_ahead: float):
        super().__init__(name, rng, dx=0.0, dy=0.0, angle=0.0)
        self.look_ahead = look_ahead
        self.image = np.zeros((PATCH, PATCH), np.float32)
        self.label = "ground"           # true class of the patch (for evaluation only)
        self.light = 1.0

    def _measure(self, robot, world, dt):
        x, y = robot.body_point(self.look_ahead, 0.0)
        t = world.terrain_at(x, y)
        self.label = TERRAIN[t].camera_class or "rock"
        self.light = min(1.0, world.cfg.ambient_light + (0.6 if robot.headlights else 0.0))
        self.image = synth_patch(self.label, self.rng, self.light)
        return float(CLASSES.index(self.label)), float(self.image.mean()), int(self.image.mean() * 255)

    def _dead_value(self):
        self.image[:] = 0
        return 0.0, 0
