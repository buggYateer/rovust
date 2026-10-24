import numpy as np
import pytest

from sim.mapping import OccupancyGrid
from sim.mission import Mission
from sim.planning import astar, build_costmap, find_frontiers


def test_astar_finds_path_around_wall():
    g = OccupancyGrid(20, 20, 0.2)
    g.logodds[:] = -3.0                   # all free
    g.logodds[5:15, 10] = 5.0             # vertical wall with gaps top and bottom
    cm = build_costmap(g, 0.1)
    path = astar(cm, (2, 10), (18, 10))
    assert path and path[0] == (2, 10) and path[-1] == (18, 10)
    assert all(not cm.blocked[y, x] for x, y in path)


def test_astar_returns_none_when_blocked():
    g = OccupancyGrid(20, 20, 0.2)
    g.logodds[:] = -3.0
    g.logodds[:, 10] = 5.0
    cm = build_costmap(g, 0.1)
    assert astar(cm, (2, 10), (18, 10)) is None


def test_frontiers_sit_between_free_and_unknown():
    g = OccupancyGrid(30, 30, 0.2)
    g.logodds[10:20, 10:20] = -3.0        # a known free square in unknown space
    cm = build_costmap(g, 0.1)
    fr = find_frontiers(g, cm)
    assert fr
    for f in fr:
        for x, y in f.cells:
            assert g.is_free(x, y)


@pytest.mark.parametrize("env", ["cave", "mars", "underwater"])
@pytest.mark.parametrize("strategy", ["frontier", "dfs"])
def test_mission_explores_without_crashing(env, strategy):
    m = Mission(env, strategy, seed=1)
    for _ in range(1500):
        m.step()
        if m.done:
            break
    assert m.coverage() > 0.03
    assert m.robot.distance > 1.0
    assert not m.robot.fell
    assert m.arbiter.active_name != ""


def test_behaviours_subsume_in_priority_order():
    m = Mission("cave", "frontier", seed=2)
    names = set()
    for _ in range(2500):
        m.step()
        names.add(m.arbiter.active_name)
        if m.done:
            break
    assert "EXPLORE" in names
    # a cave run is long enough to need at least one reactive layer
    assert names & {"AVOID", "ESCAPE", "CLIFF"}


def test_return_home_when_battery_is_low():
    m = Mission("mars", "frontier", seed=3)
    m.robot.battery.energy_wh = 0.4
    for _ in range(3000):
        m.step()
        if m.done or m.returning:
            break
    assert m.returning
    assert m.stats["return_reason"] == "battery"
