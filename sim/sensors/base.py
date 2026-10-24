"""Sensor base class (lecture: Sensors 1).

Every sensor carries its classification (local/global, internal/external,
active/passive, binary/analog/digital), a mounting position in the robot
frame, and can be faulted at run time. Analog sensors go through a modelled
A/D converter so the controller only ever sees quantised integers.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True)
class SensorClass:
    locality: str   # "local" (on-board) | "global"
    scope: str      # "internal" | "external"
    mode: str       # "active" | "passive"
    signal: str     # "binary" | "analog" | "digital"

    def __str__(self):
        return f"{self.locality}/{self.scope}/{self.mode}/{self.signal}"


class ADC:
    """n-bit A/D converter: value = round(V / Vref * (2^n - 1))."""

    def __init__(self, bits: int = 10, vref: float = 5.0):
        self.bits, self.vref = bits, vref
        self.levels = 2 ** bits - 1

    def convert(self, volts: float) -> int:
        volts = min(max(volts, 0.0), self.vref)
        return int(round(volts / self.vref * self.levels))

    def to_volts(self, raw: int) -> float:
        return raw / self.levels * self.vref


FAULT_MODES = ("ok", "stuck", "dead", "noisy")


class Sensor:
    cls: SensorClass = SensorClass("local", "external", "passive", "analog")
    units: str = ""

    def __init__(self, name: str, rng: np.random.Generator, dx: float = 0.0, dy: float = 0.0,
                 angle: float = 0.0):
        self.name = name
        self.rng = rng
        self.dx, self.dy, self.angle = dx, dy, angle   # mounting in the robot frame
        self.fault = "ok"
        self.value = 0.0        # processed reading the controller uses
        self.raw = 0            # what came off the wire (ADC counts, ticks, bits)
        self.true_value = 0.0   # ground truth, for the interface only
        self.healthy = True     # set False by the fault detector (AI stage)

    # ---------------------------------------------------------------- geometry
    def world_position(self, robot) -> tuple[float, float, float]:
        x, y = robot.body_point(self.dx, self.dy)
        return x, y, robot.pose.theta + self.angle

    # ------------------------------------------------------------------- read
    def update(self, robot, world, dt: float):
        true, value, raw = self._measure(robot, world, dt)
        self.true_value = true
        if self.fault == "stuck":
            return                                   # keeps reporting the last value
        if self.fault == "dead":
            value, raw = self._dead_value()
        elif self.fault == "noisy":
            value = value + self.rng.normal(0, 0.3 * (abs(value) + 1e-3))
        self.value, self.raw = value, raw

    def _measure(self, robot, world, dt: float):
        """Return (true_value, processed_value, raw)."""
        raise NotImplementedError

    def _dead_value(self):
        return 0.0, 0

    def set_fault(self, mode: str):
        assert mode in FAULT_MODES
        self.fault = mode

    def describe(self) -> str:
        return f"{self.name:10} {self.value:8.3f}{self.units}"
