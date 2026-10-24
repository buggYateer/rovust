"""AI 3: sensor fault detection.

Each ranging sensor is watched by a small anomaly detector that compares it
with what its neighbours and its own recent history imply:

* stuck   - the value has not changed for a long window although the robot
            is moving and turning (a live sensor always jitters)
* dead    - always reports maximum range while both neighbours see
            something close for a long time
* noisy   - the sample-to-sample variance is far above the sensor's rated
            noise (Isolation-Forest style outlier score on the residuals)

A sensor judged faulty is marked ``healthy = False``: the mapper and the
behaviours stop using it (graceful degradation), and the interface shows it
in red. The detector is deliberately conservative: a false alarm costs a
sensor, a miss costs a wrong map.
"""
from __future__ import annotations

from collections import deque

import numpy as np


class SensorWatch:
    def __init__(self, sensor, window: int = 60):
        self.s = sensor
        self.hist = deque(maxlen=window)
        self.verdict = "ok"
        self.score = 0.0

    def update(self, moving: bool, neighbours):
        self.hist.append(self.s.value)
        if len(self.hist) < self.hist.maxlen:
            return
        h = np.array(self.hist)
        rated = getattr(self.s, "noise", 0.02)
        max_range = getattr(self.s, "max_range", None)
        d = np.abs(np.diff(h))
        # stuck: no change at all over the whole window while moving
        if moving and d.max() < 1e-9:
            self.verdict, self.score = "stuck", 1.0
        # dead: pinned at max range while neighbours see near obstacles
        elif max_range is not None and (h >= max_range * 0.98).all() and neighbours \
                and all(np.mean(n.hist or [max_range]) < max_range * 0.5 for n in neighbours):
            self.verdict, self.score = "dead", 1.0
        # noisy: jitter far above the rated noise
        else:
            jitter = np.median(d)
            expected = rated * (np.median(h) if max_range else 1.0) + 0.01
            self.score = float(jitter / expected)
            self.verdict = "noisy" if self.score > 6.0 else "ok"
        self.s.healthy = self.verdict == "ok"


class FaultDetector:
    def __init__(self, suite):
        self.watches = {}
        for s in suite.sonars + suite.irs:
            self.watches[s.name] = SensorWatch(s)
        self.suite = suite
        self.alarms: list[tuple[str, str]] = []

    def update(self, robot):
        moving = abs(robot.drive.v) > 0.02 or abs(robot.drive.omega) > 0.1
        for s in self.suite.sonars:
            w = self.watches[s.name]
            nb = [self.watches[n.name] for n in s.neighbours]
            before = w.verdict
            w.update(moving, nb)
            if w.verdict != before and w.verdict != "ok":
                self.alarms.append((s.name, w.verdict))
        for s in self.suite.irs:
            w = self.watches[s.name]
            before = w.verdict
            w.update(moving, [])
            if w.verdict != before and w.verdict != "ok":
                self.alarms.append((s.name, w.verdict))

    def report(self) -> dict[str, str]:
        return {k: w.verdict for k, w in self.watches.items()}
