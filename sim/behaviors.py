"""Subsumption architecture (lecture: Robot Behavior).

Behaviours are stacked by priority. Every control step each layer looks at
the sensors and says whether it wants control; the highest active layer
drives the motors and *subsumes* everything below it:

    7 EmergencyStop   mission over (fell / battery empty)
    6 BumperEscape    tactile contact -> reverse, turn away from the side that hit
    5 CliffStop       cliff switch -> stop, back off, mark hazard
    4 SlopeRefuse     accelerometer tilt too steep -> back off
    3 AvoidObstacle   sonar/IR too close -> steer to the freer side (feedback)
    2 ReturnHome      battery only just enough to get back -> drive to start
    1 Explore         follow the planned path to the exploration target
    0 Wander          nothing to do: random walk (Monte Carlo) until a plan exists
"""
from __future__ import annotations

import math

from .core import wrap_angle


class Context:
    """What a behaviour may look at: sensors, estimate, plan, mission flags."""

    def __init__(self, mission):
        self.m = mission

    @property
    def suite(self):
        return self.m.robot.sensors

    @property
    def pose(self):
        return self.m.estimator.pose

    @property
    def dt(self):
        return self.m.dt


class Behavior:
    name = "behavior"

    def __init__(self):
        self.timer = 0.0

    def active(self, ctx: Context) -> bool:
        raise NotImplementedError

    def act(self, ctx: Context) -> tuple[float, float]:
        raise NotImplementedError


class EmergencyStop(Behavior):
    name = "STOP"

    def active(self, ctx):
        return ctx.m.robot.fell or ctx.m.robot.battery.energy_wh <= 0

    def act(self, ctx):
        return 0.0, 0.0


class BumperEscape(Behavior):
    name = "ESCAPE"
    REVERSE_T, TURN_T = 0.7, 0.8

    def __init__(self):
        super().__init__()
        self.turn_dir = 1

    def active(self, ctx):
        left, right = ctx.suite.bumped()
        if (left or right) and self.timer <= 0:
            self.timer = self.REVERSE_T + self.TURN_T
            # "if the robot has a pair of bumpers it can work out which way to turn"
            self.turn_dir = -1 if left and not right else (1 if right and not left else ctx.m.rng.choice((-1, 1)))
            ctx.m.stats["bumps"] += 1
            ctx.m.explorer.path = None
            # whatever we were heading for is behind something the map did not show
            if ctx.m.explorer.target is not None:
                ctx.m.explorer.blacklist[ctx.m.explorer.target] = ctx.m.step_count + 300
        if self.timer > 0:
            self.timer -= ctx.dt
            return True
        return False

    def act(self, ctx):
        if self.timer > self.TURN_T:
            if ctx.suite.cliff_rear():
                return 0.0, 1.2 * self.turn_dir   # a pit behind: turn instead of reversing
            return -0.15, 0.0
        return 0.0, 1.2 * self.turn_dir


class CliffStop(Behavior):
    name = "CLIFF"

    def __init__(self):
        super().__init__()
        self.away = -1.0      # drive direction that leads away from the edge

    def active(self, ctx):
        s = ctx.suite
        if s.cliff() and self.timer <= 0:
            self.timer = 1.6
            self.away = 1.0 if (s.cliff_rear() and not s.cliff_front()) else -1.0
            ctx.m.stats["cliff_events"] += 1
            ctx.m.explorer.path = None
            # the mapper already marked the hazard; also blacklist the target
            if ctx.m.explorer.target is not None:
                ctx.m.explorer.blacklist[ctx.m.explorer.target] = ctx.m.step_count + 600
        if self.timer > 0:
            self.timer -= ctx.dt
            # never keep moving toward an edge that just appeared on the other side
            if (self.away < 0 and ctx.suite.cliff_rear()) or (self.away > 0 and ctx.suite.cliff_front()):
                self.timer = min(self.timer, 0.8)
            return True
        return False

    def act(self, ctx):
        return (0.15 * self.away, 0.0) if self.timer > 0.8 else (0.0, 1.3)


class SlopeRefuse(Behavior):
    name = "SLOPE"
    LIMIT = 0.2       # rad (about 11 deg): crater rims are 0.25

    def active(self, ctx):
        a = ctx.suite.accel
        if a is not None and a.healthy and abs(a.value) > self.LIMIT and self.timer <= 0:
            self.timer = 1.0
            ctx.m.explorer.path = None
        if self.timer > 0:
            self.timer -= ctx.dt
            return True
        return False

    def act(self, ctx):
        if self.timer > 0.4 and not ctx.suite.cliff_rear():
            return -0.15, 0.0
        return 0.0, 1.0


class AvoidObstacle(Behavior):
    """Reactive avoidance with the ranging sensors: negative feedback on the
    distance to the nearest obstacle in front, steering toward the freer side."""
    name = "AVOID"

    STUCK_T = 3.0       # continuous avoidance longer than this -> reverse out

    def __init__(self, near: float = 0.32, side: float = 0.14, hysteresis: float = 1.6):
        super().__init__()
        self.near, self.side, self.hyst = near, side, hysteresis
        self.turn = 1.0
        self.engaged = False
        self.active_t = 0.0
        self.reverse_t = 0.0

    def _ranges(self, s):
        front = min(s.sonar_sector(0.0, 0.1), s.ir_front())
        diag_l, diag_r = s.sonar_sector(+0.8, 0.3), s.sonar_sector(-0.8, 0.3)
        return front, diag_l, diag_r

    def active(self, ctx):
        front, dl, dr = self._ranges(ctx.suite)
        # on-off with a hysteresis band: switch on when close, switch off only
        # once the way ahead is clearly open, so the robot does not chatter
        on = front < self.near or dl < self.side or dr < self.side
        off = front > self.near * self.hyst and dl > self.side * self.hyst and dr > self.side * self.hyst
        if not self.engaged and on:
            self.engaged = True
            self.turn = 1.0 if dl >= dr else -1.0
            self.active_t = 0.0
        elif self.engaged and off and self.reverse_t <= 0:
            self.engaged = False
        if self.engaged:
            self.active_t += ctx.dt
            if self.active_t > self.STUCK_T and self.reverse_t <= 0:
                self.reverse_t = 1.2                  # trapped in a corner: back out
                self.active_t = 0.0
                ctx.m.stats["stuck_escapes"] = ctx.m.stats.get("stuck_escapes", 0) + 1
                if ctx.m.explorer.target is not None:
                    ctx.m.explorer.blacklist[ctx.m.explorer.target] = ctx.m.step_count + 300
            return True
        return False

    def act(self, ctx):
        front, dl, dr = self._ranges(ctx.suite)
        if self.reverse_t > 0:
            self.reverse_t -= ctx.dt
            if ctx.suite.cliff_rear():
                return 0.0, 1.2 * self.turn
            return -0.15, 0.4 * self.turn
        if front < self.near * 0.55:
            return -0.06, 1.1 * self.turn         # very close: back off while turning
        if front < self.near:
            return 0.04, 0.9 * self.turn          # turn mostly in place
        return 0.12, 0.6 * self.turn              # a side is close: steer away while moving


class PathFollower:
    """Pure-pursuit style tracking of a cell path with a look-ahead point."""

    def __init__(self, grid, v_max=0.35, k_turn=2.5, lookahead=0.35):
        self.grid = grid
        self.v_max, self.k_turn, self.lookahead = v_max, k_turn, lookahead
        self.idx = 0

    def reset(self):
        self.idx = 0

    def control(self, pose, path):
        if not path:
            return 0.0, 0.0, True
        # advance along the path to the look-ahead point
        while self.idx < len(path) - 1:
            x, y = self.grid.to_world(*path[self.idx])
            if math.hypot(x - pose.x, y - pose.y) < self.lookahead:
                self.idx += 1
            else:
                break
        x, y = self.grid.to_world(*path[self.idx])
        dist = math.hypot(x - pose.x, y - pose.y)
        err = wrap_angle(math.atan2(y - pose.y, x - pose.x) - pose.theta)
        omega = max(-1.5, min(1.5, self.k_turn * err))
        v = self.v_max * max(0.0, 1.0 - abs(err) / (math.pi / 3))
        if abs(err) > math.pi / 3:
            v = 0.0                                   # turn in place first
        done = self.idx >= len(path) - 1 and dist < 0.2
        return v, omega, done


class ReturnHome(Behavior):
    name = "HOME"

    def __init__(self, follower: PathFollower):
        super().__init__()
        self.follower = follower
        self.path = None
        self.engaged = False

    def active(self, ctx):
        m = ctx.m
        if m.returning:
            return True
        # energy needed to get home: distance * (W / speed), with a 60 % margin
        home = m.grid.to_world(*m.home_cell)
        d = math.hypot(home[0] - ctx.pose.x, home[1] - ctx.pose.y)
        need_wh = d / 0.25 * (m.robot.battery.idle_w + 8.0) / 3600.0 * 1.6 + 0.02 * m.robot.battery.capacity_wh
        if m.robot.battery.energy_wh < need_wh or m.explorer.done:
            m.returning = True
            m.stats["return_reason"] = "battery" if m.robot.battery.energy_wh < need_wh else "explored"
            self.path = None
            return True
        return False

    def act(self, ctx):
        m = ctx.m
        from .planning import build_costmap, astar, nearest_free_cell
        if self.path is None or m.step_count % 40 == 0:
            cm = build_costmap(m.grid, m.robot.radius)
            start = nearest_free_cell(cm, m.grid.to_cell(ctx.pose.x, ctx.pose.y))
            self.path = astar(cm, start, m.home_cell) if start else None
            self.follower.reset()
        if not self.path:
            return 0.0, 0.6                              # turn and look for a way
        v, w, done = self.follower.control(ctx.pose, self.path)
        if done:
            m.finished = True
        return v, w


class InitialScan(Behavior):
    """Stand still for a moment (the heading filter learns the gyro bias),
    then turn a full circle so the sonar ring fills the map before moving."""
    name = "SCAN"
    CALIBRATE = 1.5
    SPIN = 2 * math.pi / 0.9 + 0.3

    def __init__(self):
        super().__init__()
        self.timer = self.CALIBRATE + self.SPIN

    def active(self, ctx):
        if self.timer > 0:
            self.timer -= ctx.dt
            return True
        return False

    def act(self, ctx):
        return (0.0, 0.0) if self.timer > self.SPIN else (0.0, 0.9)


class Explore(Behavior):
    name = "EXPLORE"
    REPLAN_EVERY = 30

    def __init__(self, follower: PathFollower):
        super().__init__()
        self.follower = follower

    def active(self, ctx):
        return not ctx.m.explorer.done

    def act(self, ctx):
        m, ex = ctx.m, ctx.m.explorer
        if ex.path is None or ex.target_reached(ctx.pose) or m.step_count % self.REPLAN_EVERY == 0:
            ex.plan(ctx.pose, m.step_count)
            self.follower.reset()
        if not ex.path:
            return 0.0, 0.8
        v, w, done = self.follower.control(ctx.pose, ex.path)
        return v, w


class Wander(Behavior):
    name = "WANDER"

    def __init__(self):
        super().__init__()
        self.v, self.w = 0.2, 0.0

    def active(self, ctx):
        return True

    def act(self, ctx):
        if self.timer <= 0:
            self.timer = ctx.m.rng.uniform(0.5, 2.0)
            self.w = ctx.m.rng.uniform(-1.0, 1.0)
        self.timer -= ctx.dt
        return self.v, self.w


class Arbiter:
    def __init__(self, layers: list[Behavior]):
        self.layers = layers          # highest priority first
        self.active_name = ""

    def decide(self, ctx: Context) -> tuple[float, float]:
        for b in self.layers:
            if b.active(ctx):
                self.active_name = b.name
                return b.act(ctx)
        return 0.0, 0.0
