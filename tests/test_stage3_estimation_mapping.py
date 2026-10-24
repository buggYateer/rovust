import math

import numpy as np

from sim.config import get_env
from sim.core import Pose, Terrain
from sim.estimation import PoseEstimator
from sim.mapping import Mapper, OccupancyGrid
from sim.robot.robot import Robot
from sim.world import World


def make(env="cave", seed=0):
    cfg = get_env(env, seed)
    w = World(cfg)
    r = Robot(cfg, w, np.random.default_rng(seed))
    return cfg, w, r


def drive_loop(r, est, steps, v=0.25, omega=0.0):
    r.drive.set_velocity(v, omega)
    for _ in range(steps):
        r.step(0.05)
        est.update(0.05)


def test_dead_reckoning_tracks_without_slip():
    cfg, w, r = make("mars", seed=1)
    cfg.drive.slip_noise = 0.0
    # bedrock everywhere under the robot: slip 0
    w.grid[w.grid != Terrain.WALL] = Terrain.BEDROCK
    w.grid[w.grid == Terrain.PIT] = Terrain.BEDROCK
    est = PoseEstimator(r, mode="odometry")
    drive_loop(r, est, 60)
    assert est.odom.distance_to(r.pose) < 0.05


def test_fused_beats_odometry_on_a_long_curved_run():
    cfg, w, r = make("cave", seed=4)
    est = PoseEstimator(r)
    err_odom, err_fused = [], []
    for k in range(6):
        drive_loop(r, est, 40, v=0.2, omega=0.6 * (1 if k % 2 else -1))
        err_odom.append(est.odom.distance_to(r.pose))
        err_fused.append(est.fused.distance_to(r.pose))
    assert abs(math.sin(est.fused.theta - r.pose.theta)) < 0.25
    assert np.mean(err_fused) <= np.mean(err_odom) + 0.05


def test_perfect_mode_returns_true_pose():
    cfg, w, r = make("mars")
    est = PoseEstimator(r, mode="perfect")
    drive_loop(r, est, 10)
    assert est.pose is r.pose


def test_occupancy_grid_beam_update():
    g = OccupancyGrid(20, 20, 0.25)
    for _ in range(5):
        g.update_beam(1.0, 1.0, 0.0, 2.0, hit=True)
    assert g.is_free(*g.to_cell(2.0, 1.0))
    assert g.is_occupied(*g.to_cell(3.0, 1.0))
    assert g.unknown_mask()[0, 0]
    assert g.known_count() > 5


def test_mapper_builds_a_map_that_matches_the_world():
    cfg, w, r = make("cave", seed=2)
    est = PoseEstimator(r, mode="perfect")
    g = OccupancyGrid(w.w, w.h, w.cell)
    m = Mapper(g, r)
    for _ in range(80):
        r.drive.set_velocity(0.0, 0.8)   # spin in place and look around
        r.step(0.05)
        est.update(0.05)
        m.update(est.pose)
    occ = g.occupied_mask()
    known = ~g.unknown_mask()
    assert known.sum() > 50
    truth_obstacle = np.isin(w.grid, [Terrain.WALL, Terrain.ROCK])
    # most cells we call occupied really are obstacles
    precision = (occ & truth_obstacle).sum() / max(1, occ.sum())
    assert precision > 0.6
    # cells we call free really are free
    free = g.free_mask()
    assert (free & ~truth_obstacle).sum() / max(1, free.sum()) > 0.8
    # now drive along the corridor: the side walls get perpendicular hits and
    # the map gets better, not worse
    r.pose.theta = math.pi / 2          # the start corridor runs along +y
    est.heading.theta = r.pose.theta
    r.drive.set_velocity(0.25, 0.0)
    for _ in range(120):
        r.step(0.05)
        est.update(0.05)
        m.update(est.pose)
    free = g.free_mask()
    assert (free & ~truth_obstacle).sum() / max(1, free.sum()) > 0.85
    assert free.sum() > 30


def test_cliff_marks_hazard_layer():
    cfg, w, r = make("mars", seed=2)
    pits = np.argwhere(w.grid == Terrain.PIT)
    py, px = pits[0]
    x, y = w.to_world(px, py)
    r.pose.x, r.pose.y, r.pose.theta = x - 0.5, y, 0.0
    r.sensors.update(r, w, 0.05)
    g = OccupancyGrid(w.w, w.h, w.cell)
    Mapper(g, r).update(r.pose)
    assert g.hazard.any()
