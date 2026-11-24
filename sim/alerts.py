"""What is happening to the rover right now, as one calm alert at a time.

Both the desktop status bar and the phone console show the single most
important condition (stuck in mud, weak link, gas, low battery, a failed
sensor...). Raw conditions flicker as the rover moves, so the tracker

* only counts a condition once it has lasted ``DEBOUNCE`` seconds,
* keeps the alert it shows for at least ``HOLD`` seconds, unless a more
  serious one arrives (that may take over after ``PREEMPT`` seconds),
* keeps a short log of what started and what ended.

Alerts carry a translation key and arguments, not text: each interface
words them in its own language.
"""
from __future__ import annotations

import time
from dataclasses import dataclass, field

from .core import Terrain

SEV_ORDER = {"bad": 0, "warn": 1, "info": 2, "good": 3}


@dataclass
class Alert:
    id: str                 # stable identity ("link", "gas", "fault:sonar0"...)
    sev: str                # "bad" | "warn" | "info" | "good"
    key: str                # translation key
    args: tuple = ()
    act: str | None = None  # an action the interface may offer ("lights")

    def to_dict(self, more: int = 0) -> dict:
        return {"id": self.id, "sev": self.sev, "key": self.key, "args": list(self.args), "more": more, "act": self.act}


OK = Alert("ok", "good", "ok")


@dataclass
class LogEntry:
    t: float                # mission time (s)
    alert: Alert
    ended: bool = False


def conditions(m, paused: bool = False, operated: bool = True) -> list[Alert]:
    """Every condition that holds right now, unfiltered. ``operated``: someone
    is driving or watching over the radio, so the link matters."""
    if m.done:
        return [Alert("ended", "info", "ended")]
    out: list[Alert] = []
    r = m.robot
    if paused:
        out.append(Alert("paused", "info", "paused"))
    # stuck: soft ground under the wheels and most of the wheel motion lost to slip
    terr = m.world.terrain_at(r.pose.x, r.pose.y)
    slip = max(r.drive.slip_l, r.drive.slip_r)
    if terr in (Terrain.MUD, Terrain.SAND) and slip > 0.2 and abs(m.cmd[0]) > 0.02:
        out.append(Alert("stuck", "warn", "stuck", ("mud" if terr == Terrain.MUD else "sand", round(slip * 100))))
    if operated:
        lk = m.link
        if lk.state == "lost":
            out.append(Alert("link", "bad", "linkLost", (round(lk.lost_for(m.time)),)))
        elif lk.state == "weak":
            out.append(Alert("link", "warn", "linkWeak", (round(lk.strength * 100),)))
    bat = r.battery.fraction
    if bat < 0.25:
        out.append(Alert("batt", "bad" if bat < 0.15 else "warn", "batt", (round(bat * 100),)))
    gas = getattr(r.sensors, "gas", None)
    if gas is not None and gas.healthy and gas.fault == "ok" and gas.value > 0.25:
        out.append(Alert("gas", "bad" if gas.value > 0.6 else "warn", "gas", (round(gas.value * 100),)))
    for s in r.sensors.sensors:
        if s.fault != "ok" or not s.healthy:
            # the AI fault detector marks a sensor unhealthy once it stops using it
            out.append(Alert("fault:" + s.name, "warn" if not s.healthy else "bad", "fault", (s.name, not s.healthy)))
    if m.cfg.ambient_light < 0.3 and not r.headlights and r.sensors.camera is not None:
        out.append(Alert("dark", "info", "dark", act="lights"))
    return out


@dataclass
class AlertTracker:
    DEBOUNCE: float = 0.8
    HOLD: float = 3.0
    PREEMPT: float = 1.0
    clock: object = time.monotonic
    first: dict = field(default_factory=dict)       # id -> when the condition was first seen
    active: dict = field(default_factory=dict)      # id -> Alert, the confirmed ones last update
    shown: Alert | None = None
    shown_at: float = 0.0
    more: int = 0
    log: list = field(default_factory=list)          # newest first
    changed: bool = False                           # the shown alert changed on the last update

    def reset(self):
        self.first.clear()
        self.active.clear()
        self.shown, self.shown_at, self.more = None, 0.0, 0
        self.log.clear()

    def update(self, raw: list[Alert], mission_time: float = 0.0) -> Alert:
        now = self.clock()
        ids = {a.id for a in raw}
        for a in raw:
            self.first.setdefault(a.id, now)
        for gone in [i for i in self.first if i not in ids]:
            del self.first[gone]
        confirmed = sorted((a for a in raw if now - self.first[a.id] >= self.DEBOUNCE), key=lambda a: SEV_ORDER[a.sev])
        cur_ids = {a.id: a for a in confirmed}
        # the event log: what started, what ended
        for a in confirmed:
            if a.id not in self.active and a.id not in ("paused", "ended"):
                self.log.insert(0, LogEntry(mission_time, a))
        for i, a in self.active.items():
            if i not in cur_ids and i not in ("paused", "ended"):
                self.log.insert(0, LogEntry(mission_time, a, ended=True))
        del self.log[80:]
        self.active = cur_ids
        best = confirmed[0] if confirmed else OK
        cur = self.shown
        held = now - self.shown_at
        self.changed = False
        if cur is None or (best.id != cur.id and (cur.id == "ok" or held >= self.HOLD
                                                   or (held >= self.PREEMPT and SEV_ORDER[best.sev] < SEV_ORDER[cur.sev]))):
            # "all good" never holds a real alert back
            self.changed = cur is None or best.id != cur.id
            self.shown, self.shown_at = best, now
        elif cur.id in cur_ids:
            self.shown = cur_ids[cur.id]            # same alert, fresh numbers
        self.more = sum(1 for a in confirmed if a.id != self.shown.id and a.sev != "info")
        return self.shown

    @property
    def problems(self) -> int:
        return sum(1 for a in self.active.values() if a.sev in ("bad", "warn"))
