"""Radio link between the robot and the operator's base station.

The base station sits at the start point. Signal strength falls with distance
and with every wall between the two (line-of-sight count through the true
map). Commands travel with a latency (seconds) and are dropped when the link
is weak; when it is lost the robot gets no commands at all and the
teleoperation layer has to fall back to autonomy. This is the course's
"communication" activity, plus the Mars delay argument from the proposal.
"""
from __future__ import annotations

import math
from collections import deque

from .config import LinkConfig

WEAK_LEVEL = 0.35
LOST_LEVEL = 0.12


class RadioLink:
    STATES = ("ok", "weak", "lost")

    def __init__(self, world, cfg: LinkConfig, rng):
        self.world = world
        self.cfg = cfg
        self.rng = rng
        self.base = world.start
        self.strength = 1.0
        self.state = "ok"
        self.queue: deque = deque()       # (deliver_time, command)
        self.dropped = 0
        self.delivered = 0
        self.lost_since = None
        self.walls = 0                    # obstacle cells on the line of sight (for the display)
        self.distance = 0.0
        self.log: deque = deque(maxlen=120)   # (t, "TX"/"RX"/"DROP", command) for the radio panel

    def update(self, pose, t: float):
        d = math.hypot(pose.x - self.base[0], pose.y - self.base[1])
        # count obstacle cells between the base station and the robot
        n = max(2, int(d / self.world.cell))
        walls = 0
        for i in range(1, n):
            x = self.base[0] + (pose.x - self.base[0]) * i / n
            y = self.base[1] + (pose.y - self.base[1]) * i / n
            if self.world.is_obstacle(*self.world.to_cell(x, y)):
                walls += 1
        self.walls, self.distance = walls, d
        s = max(0.0, 1.0 - 0.65 * (d / self.cfg.range_m) ** 2) * max(0.0, 1.0 - self.cfg.wall_loss * walls)
        s += self.rng.normal(0, 0.02)
        self.strength = min(1.0, max(0.0, 0.8 * self.strength + 0.2 * s))   # smoothed RSSI
        if self.strength < LOST_LEVEL:
            self.state = "lost"
            if self.lost_since is None:
                self.lost_since = t
        elif self.strength < WEAK_LEVEL:
            self.state = "weak"
            self.lost_since = None
        else:
            self.state = "ok"
            self.lost_since = None

    def send(self, command: dict, t: float) -> bool:
        """Operator -> robot. Returns False if the packet was dropped."""
        if self.state == "lost" or (self.state == "weak" and self.rng.random() < 0.5):
            self.dropped += 1
            self.log.append((t, "DROP", command))
            return False
        self.queue.append((t + self.cfg.latency_s, command))
        self.log.append((t, "TX", command))
        return True

    def receive(self, t: float) -> list[dict]:
        out = []
        while self.queue and self.queue[0][0] <= t:
            cmd = self.queue.popleft()[1]
            out.append(cmd)
            self.delivered += 1
            self.log.append((t, "RX", cmd))
        return out

    def lost_for(self, t: float) -> float:
        return 0.0 if self.lost_since is None else t - self.lost_since
