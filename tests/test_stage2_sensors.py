import math

import numpy as np
import pytest

from sim.config import get_env
from sim.core import Terrain
from sim.robot.robot import Robot
from sim.sensors.base import ADC
from sim.sensors.camera import CLASSES, synth_patch
from sim.sensors.range_sensors import IRDistance
from sim.world import World


def make(env="cave", seed=0):
    cfg = get_env(env, seed)
    w = World(cfg)
    r = Robot(cfg, w, np.random.default_rng(seed))
    return cfg, w, r


def test_adc_quantises():
    adc = ADC(10, 5.0)
    assert adc.convert(5.0) == 1023 and adc.convert(0) == 0
    assert adc.convert(2.5) == 512
    assert adc.to_volts(adc.convert(1.234)) == pytest.approx(1.234, abs=0.005)


def test_ir_lookup_table_linearises_nonlinear_response():
    ir = IRDistance("ir", np.random.default_rng(0), 0, 0, 0, 0.8, 0.06, 0.0, ADC(10, 5.0))
    for d in (0.1, 0.2, 0.4, 0.7):
        raw = ir.adc.convert(ir.volts_for(d))
        assert ir.lut[raw] == pytest.approx(d, abs=0.03)
    # below the minimum range the sensor reports something far away
    raw_close = ir.adc.convert(ir.volts_for(0.02))
    assert ir.lut[raw_close] > 0.2


def test_every_environment_mounts_the_right_suite():
    cfg, w, r = make("cave")
    names = r.sensors.names()
    assert "gas" in names and "light" in names and "compass" in names and "cliffL" in names
    cfg, w, r = make("mars")
    names = r.sensors.names()
    assert "compass" not in names and "cliffL" in names and "gyro" in names
    cfg, w, r = make("underwater")
    names = r.sensors.names()
    assert "dvl" in names and "pressure" in names and not any(n.startswith("ir") for n in names)
    assert len(r.sensors.sonars) == 12


def test_sonar_sees_wall_and_specular_loses_it():
    cfg, w, r = make("cave")
    r.step(0.05)
    s0 = r.sensors.sonars[0]
    assert 0 < s0.true_value <= s0.max_range
    # head-on wall: reading close to truth
    r.pose.theta = math.pi
    r.step(0.05)
    assert abs(s0.value - s0.true_value) < 0.3 or s0.value == s0.max_range


def test_sensor_faults():
    cfg, w, r = make("mars")
    r.step(0.05)
    s = r.sensors.sonars[0]
    s.set_fault("dead")
    r.step(0.05)
    assert s.value == s.max_range
    s.set_fault("stuck")
    v = s.value
    r.pose.theta += 1.0
    r.step(0.05)
    assert s.value == v
    s.set_fault("ok")


def test_gyro_bias_drifts_but_compass_does_not():
    cfg, w, r = make("cave")
    g, c = r.sensors.gyro, r.sensors.compass
    for _ in range(400):   # 20 s standing still
        r.step(0.05)
    assert abs(g.integrated) > 0.03          # drifted
    assert abs(c.value - r.pose.theta) < 0.3  # bounded error


def test_cliff_sensor_fires_at_pit():
    cfg, w, r = make("mars", seed=2)
    pits = np.argwhere(w.grid == Terrain.PIT)
    assert len(pits)
    py, px = pits[0]
    x, y = w.to_world(px, py)
    # park the robot just left of the pit, looking at it
    r.pose.x, r.pose.y, r.pose.theta = x - 0.5, y, 0.0
    r.sensors.update(r, w, 0.05)
    assert r.sensors.cliff()


def test_bumper_fires_on_collision():
    cfg, w, r = make("cave")
    r.pose.theta = math.pi
    r.drive.set_velocity(0.4, 0.0)
    fired = False
    for _ in range(200):
        r.step(0.05)
        if any(r.sensors.bumped()):
            fired = True
            break
    assert fired


def test_camera_patches_are_distinguishable():
    rng = np.random.default_rng(0)
    means = {c: np.mean([synth_patch(c, rng).mean() for _ in range(20)]) for c in CLASSES}
    assert means["sand"] > means["mud"] > means["pit"]
    cfg, w, r = make("cave")
    r.step(0.05)
    assert r.sensors.camera.image.shape == (16, 16)
