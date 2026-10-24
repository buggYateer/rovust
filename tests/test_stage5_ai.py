import numpy as np

from sim.ai.brain import AIBrain
from sim.ai.faults import FaultDetector
from sim.ai.terrain import TerrainClassifier
from sim.mission import Mission
from sim.sensors.camera import CLASSES, synth_patch


def test_terrain_classifier_learns_the_textures(tmp_path):
    clf = TerrainClassifier(model_path=str(tmp_path / "rf.pkl"))
    acc = clf.train(n_per_class=150, seed=1)
    assert acc > 0.8
    rng = np.random.default_rng(5)
    hits = sum(clf.predict(synth_patch(c, rng, 0.9))[0] == c for c in CLASSES for _ in range(5))
    assert hits > 0.7 * 5 * len(CLASSES)


def test_fault_detector_catches_injected_faults_and_tolerates_open_space():
    m = Mission("mars", "frontier", seed=2)
    det = FaultDetector(m.robot.sensors)
    for _ in range(200):
        m.step()
        det.update(m.robot)
    # open terrain: sonars reading max range are not alarms
    assert all(v == "ok" for v in det.report().values())
    s = m.robot.sensors.sonars[0]
    s.set_fault("noisy")
    ir = m.robot.sensors.irs[0]
    ir.value = 0.31          # frozen at a mid-range reading (a frozen max reading looks like open space)
    ir.set_fault("stuck")
    for _ in range(200):
        m.step()
        det.update(m.robot)
    rep = det.report()
    assert rep[s.name] == "noisy" and not s.healthy
    assert rep[ir.name] == "stuck" and not ir.healthy


def test_utility_explorer_runs_with_brain():
    ai = AIBrain()
    m = Mission("mars", "utility", seed=3, ai=ai)
    ai.attach(m)
    for _ in range(1500):
        m.step()
        if m.done:
            break
    assert m.explorer.name == "utility"
    assert m.coverage() > 0.05
    assert ai.terrain.predictions > 50
    # the classifier wrote something into the planner's terrain layer
    assert (m.grid.terrain_label >= 0).sum() > 10
