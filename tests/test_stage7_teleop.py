import json
import urllib.request

import pytest

from sim.mission import Mission
from sim.teleop.server import ConsoleServer, png_bytes


def run(m, steps, drive=None):
    for i in range(steps):
        if drive is not None and i % 5 == 0:
            m.operator_drive(*drive)
        m.step()


def test_assisted_drive_moves_and_safety_layers_still_apply():
    m = Mission("cave", "dfs", seed=1)
    m.mode = "assisted"
    run(m, 400, drive=(1.0, 0.0))
    assert m.robot.distance > 1.5
    assert m.arbiter.active_name in ("TELEOP", "AVOID", "ESCAPE", "CLIFF")
    # drive straight into the wall for a long time: AVOID or ESCAPE must have taken over
    names = set()
    for _ in range(600):
        m.operator_drive(1.0, 0.0)
        m.step()
        names.add(m.arbiter.active_name)
    assert names & {"AVOID", "ESCAPE"}
    assert not m.robot.fell


def test_manual_mode_disables_safety_layers():
    m = Mission("cave", "dfs", seed=1)
    m.mode = "manual"
    names = set()
    for _ in range(600):
        m.operator_drive(1.0, 0.0)
        m.step()
        names.add(m.arbiter.active_name)
    assert names == {"TELEOP"}
    assert m.robot.collisions > 0          # nothing stopped it from hitting the wall


def test_watchdog_stops_the_rover_without_commands():
    m = Mission("mars", "dfs", seed=1)
    m.mode = "manual"
    run(m, 100, drive=(1.0, 0.0))
    run(m, 120)                           # 6 s of silence (the Mars link adds 2 s of latency)
    assert abs(m.robot.drive.v) < 0.02


def test_link_latency_on_mars_delays_commands():
    m = Mission("mars", "dfs", seed=1)
    m.mode = "manual"
    m.operator_drive(1.0, 0.0)
    for _ in range(30):                   # 1.5 s < 2 s latency
        m.step()
    assert m.operator_cmd == (0.0, 0.0)
    for _ in range(20):
        m.step()
    assert m.operator_cmd[0] > 0


def test_link_loss_falls_back_to_autonomy_and_returns_home():
    m = Mission("cave", "dfs", seed=1)
    m.mode = "manual"
    m.on_link_loss = "home"
    m.robot.pose.x, m.robot.pose.y = 13.0, 9.0     # deep in the cave, many walls from the base
    dropped_before = m.link.dropped
    for _ in range(200):
        m.operator_drive(1.0, 0.0)
        m.step()
    assert m.link.state == "lost"
    assert m.link.dropped > dropped_before
    assert m.link_fallback and m.effective_mode == "autonomous"
    assert m.returning and m.stats["return_reason"] == "link lost"


def test_console_server_round_trip():
    m = Mission("underwater", "dfs", seed=2)
    srv = ConsoleServer(lambda: m, port=8097)
    srv.start()
    try:
        base = "http://127.0.0.1:8097"
        page = urllib.request.urlopen(base + "/", timeout=5).read()
        assert b"<canvas" in page and b"Who drives" in page
        st = json.loads(urllib.request.urlopen(base + "/api/state", timeout=5).read())
        assert st["mission"] and st["env"] == "underwater" and len(st["sonar"]) == 12

        def cmd(d):
            req = urllib.request.Request(base + "/api/cmd", data=json.dumps(d).encode(),
                                         headers={"Content-Type": "application/json"})
            return json.loads(urllib.request.urlopen(req, timeout=5).read())["ok"]
        assert cmd({"type": "mode", "mode": "assisted"})
        assert cmd({"type": "drive", "x": 0.0, "y": 1.0})
        assert cmd({"type": "lights", "on": True})
        for _ in range(30):
            m.step()
        assert m.mode == "assisted" and m.robot.headlights
        assert m.operator_cmd[0] > 0
        png = urllib.request.urlopen(base + "/api/map.png", timeout=5).read()
        assert png[:8] == b"\x89PNG\r\n\x1a\n"
        assert urllib.request.urlopen(base + "/api/camera.png", timeout=5).read()[:4] == b"\x89PNG"
    finally:
        srv.stop()


def test_png_encoder():
    import numpy as np
    data = png_bytes(np.zeros((4, 6, 3), np.uint8))
    assert data[:8] == b"\x89PNG\r\n\x1a\n" and b"IEND" in data
