"""Headless experiments: the same robot in every environment, many seeds.

    python -m sim.experiments.run_batch                     # everything, 10 seeds
    python -m sim.experiments.run_batch --envs cave mars --strategies frontier dfs --seeds 5
    python -m sim.experiments.run_batch --ablation          # switch sensors off one by one
    python -m sim.experiments.run_batch --localisation      # fused vs odometry vs perfect

Results go to results/<name>.csv and results/<name>_*.png (matplotlib).
"""
from __future__ import annotations

import argparse
import csv
import os
import time
from concurrent.futures import ProcessPoolExecutor

from ..ai.brain import AIBrain
from ..mission import Mission

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "results")
ENVS = ["cave", "mars", "underwater"]
STRATEGIES = ["frontier", "dfs", "utility"]
SAMPLE_EVERY = 100   # steps between coverage samples


def run_one(args):
    env, strategy, seed, localisation, max_steps, fault = args
    ai = AIBrain() if strategy == "utility" or fault else None
    m = Mission(env, strategy, seed=seed, localisation=localisation, ai=ai)
    if ai is not None:
        ai.attach(m)
    if fault:
        name, mode = fault
        for s in m.robot.sensors.sensors:
            if s.name == name or s.name.startswith(name):
                s.set_fault(mode)
    curve = []
    while not m.done and m.step_count < max_steps:
        m.step()
        if m.step_count % SAMPLE_EVERY == 0:
            curve.append((m.time, m.coverage()))
    row = m.metrics()
    row["localisation"] = localisation
    row["fault"] = f"{fault[0]}:{fault[1]}" if fault else ""
    row["max_steps"] = max_steps
    row["curve"] = ";".join(f"{t:.0f}:{c:.3f}" for t, c in curve)
    return row


def write_csv(rows, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--envs", nargs="+", default=ENVS)
    ap.add_argument("--strategies", nargs="+", default=STRATEGIES)
    ap.add_argument("--seeds", type=int, default=10)
    ap.add_argument("--steps", type=int, default=8000, help="max simulation steps (0.05 s each)")
    ap.add_argument("--ablation", action="store_true")
    ap.add_argument("--localisation", action="store_true")
    ap.add_argument("--name", default=None)
    ap.add_argument("--workers", type=int, default=max(1, (os.cpu_count() or 2) - 1))
    a = ap.parse_args()

    jobs = []
    if a.ablation:
        name = a.name or "ablation"
        faults = [None, ("sonar", "dead"), ("ir", "dead"), ("cliff", "dead"), ("gyro", "dead"),
                  ("compass", "dead"), ("sun", "dead"), ("optflow", "dead"), ("dvl", "dead"), ("bump", "dead")]
        for env in a.envs:
            for seed in range(a.seeds):
                for f in faults:
                    jobs.append((env, "dfs", seed, "fused", a.steps, f))
    elif a.localisation:
        name = a.name or "localisation"
        for env in a.envs:
            for seed in range(a.seeds):
                for loc in ("fused", "odometry", "perfect"):
                    jobs.append((env, "dfs", seed, loc, a.steps, None))
    else:
        name = a.name or "strategies"
        for env in a.envs:
            for st in a.strategies:
                for seed in range(a.seeds):
                    jobs.append((env, st, seed, "fused", a.steps, None))

    print(f"{len(jobs)} runs on {a.workers} workers ...")
    t0 = time.time()
    rows = []
    with ProcessPoolExecutor(a.workers) as ex:
        for i, row in enumerate(ex.map(run_one, jobs)):
            rows.append(row)
            print(f"[{i + 1}/{len(jobs)}] {row['env']:10} {row['strategy']:9} seed {row['seed']:2d} "
                  f"{row['localisation']:9} {row['fault']:14} cov {row['coverage']:.2f} "
                  f"path {row['path_length_m']:6.1f} m  bumps {row['bumps']:3d} loc {row['loc_error_mean_m']:.2f} m  {row['status']}")
    path = os.path.join(RESULTS, f"{name}.csv")
    write_csv(rows, path)
    print(f"wrote {path} in {time.time() - t0:.0f} s")
    from .plots import make_plots
    make_plots(path)


if __name__ == "__main__":
    main()
