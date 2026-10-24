import math

import numpy as np
import pytest

from sim.config import MotorConfig, PIDConfig, DriveConfig, get_env
from sim.core import Pose, Terrain
from sim.robot.control import PIDController, OnOffController, HysteresisController
from sim.robot.motor import DCMotor, calibration_table
from sim.robot.encoder import IncrementalEncoder
from sim.robot.drive import DifferentialDrive
from sim.robot.robot import Robot
from sim.world import World


def test_motor_calibration_is_monotonic_and_nonlinear():
    rows = calibration_table(MotorConfig())
    speeds = [w for _, w in rows]
    assert speeds[0] == 0.0
    assert all(b >= a for a, b in zip(speeds, speeds[1:]))
    # non-linear: half duty gives clearly less than half speed
    assert speeds[5] < 0.5 * speeds[-1]


def test_motor_slows_under_load():
    free = calibration_table(MotorConfig(), steps=2, load=0.0)[-1][1]
    loaded = calibration_table(MotorConfig(), steps=2, load=0.5)[-1][1]
    assert loaded < free


def test_encoder_counts_ticks_with_direction():
    enc = IncrementalEncoder(16, 30.0)
    enc.update(2 * math.pi)          # one motor rev forward
    assert enc.count == 16 and enc.direction == 1
    enc.update(0.0)
    assert enc.count == 0 and enc.direction == -1
    assert enc.wheel_angle() == pytest.approx(0.0)


def test_pid_reaches_setpoint_without_steady_state_error():
    cfg = MotorConfig()
    m = DCMotor(cfg)
    enc = IncrementalEncoder(cfg.encoder_ticks, cfg.gear_ratio)
    pid = PIDController(0.08, 0.6, 0.002)
    dt, target = 0.05, 6.0
    for _ in range(200):
        enc.update(m.angle)
        m.set_duty(pid.update(target, enc.wheel_speed(dt), dt))
        m.step(dt)
    assert m.wheel_omega == pytest.approx(target, rel=0.05)


def test_p_only_keeps_steady_state_error():
    cfg = MotorConfig()
    m = DCMotor(cfg)
    enc = IncrementalEncoder(cfg.encoder_ticks, cfg.gear_ratio)
    pid = PIDController(0.08, 0.0, 0.0)
    dt, target = 0.05, 6.0
    for _ in range(200):
        enc.update(m.angle)
        m.set_duty(pid.update(target, enc.wheel_speed(dt), dt))
        m.step(dt)
    # pure P in incremental form behaves like an integrator on the output
    # only via Kp*(e_n-e_{n-1}); it cannot remove the offset
    assert abs(m.wheel_omega - target) > 0.2


def test_onoff_and_hysteresis_oscillate_around_target():
    for ctrl in (OnOffController(), HysteresisController(band=0.1)):
        m = DCMotor(MotorConfig())
        enc = IncrementalEncoder(16, 30.0)
        dt = 0.05
        samples = []
        for _ in range(300):
            enc.update(m.angle)
            m.set_duty(ctrl.update(5.0, enc.wheel_speed(dt), dt))
            m.step(dt)
            samples.append(m.wheel_omega)
        assert 3.0 < np.mean(samples[100:]) < 7.0


def test_drive_goes_straight_despite_motor_mismatch():
    rng = np.random.default_rng(0)
    drive = DifferentialDrive(DriveConfig(slip_noise=0.0), MotorConfig(mismatch=0.1), PIDConfig(), rng)
    pose = Pose()
    drive.set_velocity(0.3, 0.0)
    for _ in range(400):
        pose = drive.step(0.05, pose, Terrain.FREE, Terrain.FREE)
    assert pose.x > 3.0
    assert abs(pose.y) < 0.15
    assert abs(pose.theta) < 0.08


def test_drive_turns_on_the_spot():
    rng = np.random.default_rng(0)
    drive = DifferentialDrive(DriveConfig(), MotorConfig(), PIDConfig(), rng)
    pose = Pose()
    drive.set_velocity(0.0, 1.0)
    for _ in range(40):   # 2 s -> about 1.5 rad, still inside the wrap range
        pose = drive.step(0.05, pose, Terrain.FREE, Terrain.FREE)
    assert math.hypot(pose.x, pose.y) < 0.05
    assert 1.0 < pose.theta < 2.5


@pytest.mark.parametrize("env", ["cave", "mars", "underwater"])
def test_world_generates_and_is_connected(env):
    cfg = get_env(env, seed=3)
    w = World(cfg)
    sx, sy = w.to_cell(*w.start)
    assert not w.is_obstacle(sx, sy)
    assert w.reachable_count > 0.15 * w.w * w.h
    d, n = w.raycast(w.start[0], w.start[1], 0.0, 50.0)
    assert d < 50.0 and n is not None


def test_robot_collides_with_walls_and_counts():
    cfg = get_env("cave", seed=1)
    w = World(cfg)
    r = Robot(cfg, w, np.random.default_rng(1))
    r.pose.theta = math.pi  # drive into the left border wall
    r.drive.set_velocity(0.4, 0.0)
    for _ in range(200):
        r.step(0.05)
    assert r.collisions > 0
    assert not w.circle_hits_obstacle(r.pose.x, r.pose.y, r.radius)
    assert r.battery.energy_wh < cfg.battery_wh
