"""The calm one-at-a-time alert and point-to-go steering."""
import math

from sim.alerts import Alert, AlertTracker, conditions
from sim.mission import Mission


class Clock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t


def test_blips_never_show_and_alerts_are_held():
    c = Clock()
    tr = AlertTracker(clock=c)
    gas = Alert("gas", "warn", "gas", (40,))
    assert tr.update([]).id == "ok"
    # a 0.5 s blip never shows
    for _ in range(5):
        c.t += 0.1
        assert tr.update([gas]).id == "ok"
    c.t += 0.1
    tr.update([])
    # a lasting condition shows after 0.8 s ...
    for _ in range(9):
        c.t += 0.1
        shown = tr.update([gas])
    assert shown.id == "gas"
    # ... and stays at least 3 s after it ends
    c.t += 0.1
    assert tr.update([]).id == "gas"
    c.t += 2.0
    assert tr.update([]).id == "gas"
    c.t += 1.0
    assert tr.update([]).id == "ok"
    assert [e.ended for e in tr.log] == [True, False]


def test_more_serious_alert_takes_over_after_one_second():
    c = Clock()
    tr = AlertTracker(clock=c)
    warn = Alert("batt", "warn", "batt", (20,))
    bad = Alert("link", "bad", "linkLost", (4,))
    for _ in range(10):
        c.t += 0.1
        tr.update([warn])
    assert tr.shown.id == "batt"
    for _ in range(12):
        c.t += 0.1
        tr.update([warn, bad])
    assert tr.shown.id == "link"
    assert tr.more == 1


def test_conditions_see_a_dark_cave_and_injected_faults():
    m = Mission("cave", "dfs", seed=1)
    m.robot.headlights = False
    m.robot.sensors.sensors[0].set_fault("dead")
    ids = {a.id for a in conditions(m)}
    assert "dark" in ids
    assert "fault:" + m.robot.sensors.sensors[0].name in ids


def test_point_to_go_turns_towards_the_stick():
    m = Mission("cave", "dfs", seed=1)
    m.mode = "manual"
    for _ in range(40):
        m.step()
    th0 = m.estimator.pose.theta
    tx, ty = math.cos(th0 + math.pi / 2), math.sin(th0 + math.pi / 2)    # stick 90 degrees to the left
    fwd, turn = m.steer_to_drive(tx, ty)
    assert fwd == 0.0 and turn > 0.9                                       # far off: spin first, no driving
    for i in range(80):
        if i % 3 == 0:
            m.operator_steer(tx, ty)
        m.step()
    err = math.atan2(math.sin(th0 + math.pi / 2 - m.estimator.pose.theta), math.cos(th0 + math.pi / 2 - m.estimator.pose.theta))
    assert abs(err) < math.radians(25)
    assert m.steer_to_drive(0.0, 0.0) == (0.0, 0.0)


def test_gamepad_reads_only_names_pygame_has():
    """Every pygame constant the controller reader uses must exist (a wrong
    module once made a recognised controller disconnect on its first read)."""
    import re
    import pytest
    pygame = pytest.importorskip("pygame")
    import sim.qtui.gamepad as gp
    src = open(gp.__file__, encoding="utf-8").read()
    names = set(re.findall(r"pg\.(CONTROLLER_[A-Z_]+)", src))
    assert names and all(hasattr(pygame, n) for n in names)
    assert gp.is_playstation("Twin USB Joystick") and not gp.is_playstation("Xbox Wireless Controller")


class FakeStick:
    """A plain joystick: axes 0/1 left stick, 2 right x; buttons 0 ✕, 1 ○, 2 □, 3 △, 9 Start; one hat."""
    def __init__(self, axes=(0, 0, 0), buttons=(), hat=(0, 0)):
        self.axes, self.buttons, self.hat = axes, set(buttons), hat
    def get_numaxes(self): return 3
    def get_axis(self, i): return self.axes[i]
    def get_numbuttons(self): return 12
    def get_button(self, i): return i in self.buttons
    def get_numhats(self): return 1
    def get_hat(self, i): return self.hat


def test_controller_drives_like_a_game():
    pytest = __import__("pytest")
    pytest.importorskip("pygame")
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from sim.qtui.gamepad import Gamepad
    g = Gamepad()
    if not g.available:
        pytest.skip("no SDL")
    def read(**kw):
        g.pad = FakeStick(**kw)
        return g._read()
    # ✕ alone: straight ahead
    (sx, sy), (fwd, turn), _ = read(buttons={0})
    assert (sx, sy) == (0, 0) and fwd == 1.0 and turn == 0
    # ✕ + right arrow: forward and to the right (negative turn = clockwise)
    _, (fwd, turn), _ = read(buttons={0}, hat=(1, 0))
    assert fwd == 1.0 and turn < 0
    # △ + left on the stick: reverse, steering left
    _, (fwd, turn), _ = read(buttons={3}, axes=(-1.0, 0, 0))
    assert fwd == -1.0 and turn > 0
    # the arrows alone and the stick alone do the same thing
    (s1, _), _, _ = read(hat=(1, 0))
    (s2, _), _, _ = read(axes=(1.0, 0, 0))
    assert s1 == s2 == 1.0
    # Start is a button press of its own
    *_, pressed = read(buttons={9})
    assert pressed["start"]
    g.pad = None
