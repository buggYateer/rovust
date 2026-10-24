"""Glue: runs the AI components inside a mission every step."""
from __future__ import annotations

from .faults import FaultDetector
from .terrain import TerrainClassifier


class AIBrain:
    def __init__(self, terrain: bool = True, faults: bool = True):
        self.use_terrain, self.use_faults = terrain, faults
        self.terrain = TerrainClassifier() if terrain else None
        self.detector: FaultDetector | None = None
        self.camera_every = 4          # classify every 4th frame (5 Hz)
        self.last = ("?", 0.0)

    def attach(self, mission):
        if self.use_faults:
            self.detector = FaultDetector(mission.robot.sensors)
        if self.terrain is not None:
            self.terrain.ensure()
        if hasattr(mission.explorer, "battery_fraction"):
            mission.explorer.ai = self

    def observe(self, mission):
        r, suite = mission.robot, mission.robot.sensors
        if self.detector is not None:
            self.detector.update(r)
        cam = suite.camera
        if self.terrain is not None and cam is not None and cam.healthy and mission.step_count % self.camera_every == 0:
            label, p = self.terrain.predict(cam.image)
            self.last = (label, p)
            self.terrain.predictions += 1
            self.terrain.correct += int(label == cam.label)
            est = mission.estimator.pose
            x, y = est.x + cam.look_ahead * __import__("math").cos(est.theta), est.y + cam.look_ahead * __import__("math").sin(est.theta)
            from ..sensors.camera import CLASSES
            if p > 0.45:
                mission.grid.set_terrain(x, y, CLASSES.index(label), self.terrain.cost_for(label), radius_cells=1)
        if hasattr(mission.explorer, "battery_fraction"):
            mission.explorer.battery_fraction = r.battery.fraction

    @property
    def terrain_accuracy_live(self) -> float:
        if self.terrain is None or not self.terrain.predictions:
            return 0.0
        return self.terrain.correct / self.terrain.predictions
