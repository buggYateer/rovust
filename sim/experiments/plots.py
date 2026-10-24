"""Plots for the experiment CSVs (matplotlib, headless)."""
from __future__ import annotations

import csv
import os
from collections import defaultdict

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

COLORS = {"frontier": "#4c9be8", "dfs": "#e8884c", "utility": "#5ac878",
          "fused": "#5ac878", "odometry": "#e85c5c", "perfect": "#aaaaaa"}


def load(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def parse_curve(s):
    pts = [p.split(":") for p in s.split(";") if p]
    return np.array([(float(t), float(c)) for t, c in pts]) if pts else np.zeros((0, 2))


def _bar(ax, groups, metric, title, ylabel):
    """groups: {env: {key: [values]}}"""
    envs = list(groups)
    keys = sorted({k for g in groups.values() for k in g})
    width = 0.8 / max(1, len(keys))
    for i, k in enumerate(keys):
        means = [np.mean(groups[e].get(k, [0])) for e in envs]
        errs = [np.std(groups[e].get(k, [0])) for e in envs]
        ax.bar(np.arange(len(envs)) + i * width, means, width, yerr=errs, capsize=3,
               label=k, color=COLORS.get(k))
    ax.set_xticks(np.arange(len(envs)) + width * (len(keys) - 1) / 2)
    ax.set_xticklabels(envs)
    ax.set_title(title)
    ax.set_ylabel(ylabel)
    ax.grid(axis="y", alpha=0.3)
    ax.legend(fontsize=8)


def make_plots(csv_path):
    rows = load(csv_path)
    base = os.path.splitext(csv_path)[0]
    name = os.path.basename(base)
    key_field = "localisation" if name.startswith("localisation") else ("fault" if name.startswith("ablation") else "strategy")

    def grouped(metric):
        g = defaultdict(lambda: defaultdict(list))
        for r in rows:
            g[r["env"]][r[key_field] or "none"].append(float(r[metric]))
        return g

    fig, axes = plt.subplots(2, 3, figsize=(16, 9))
    _bar(axes[0, 0], grouped("coverage"), "coverage", "Area coverage", "fraction of reachable area")
    _bar(axes[0, 1], grouped("path_length_m"), "path_length_m", "Path length", "metres")
    _bar(axes[0, 2], grouped("backtracks"), "backtracks", "Backtracking events", "count")
    _bar(axes[1, 0], grouped("bumps"), "bumps", "Bumper events", "count")
    _bar(axes[1, 1], grouped("loc_error_mean_m"), "loc_error_mean_m", "Mean localisation error", "metres")
    _bar(axes[1, 2], grouped("energy_wh"), "energy_wh", "Energy used", "Wh")
    fig.suptitle(f"{name}: {len(rows)} runs", fontsize=14)
    fig.tight_layout()
    fig.savefig(base + "_summary.png", dpi=130)
    plt.close(fig)

    # coverage over time, one panel per environment
    envs = sorted({r["env"] for r in rows})
    fig, axes = plt.subplots(1, len(envs), figsize=(6 * len(envs), 4.5), squeeze=False)
    for ax, env in zip(axes[0], envs):
        by_key = defaultdict(list)
        for r in rows:
            if r["env"] == env:
                by_key[r[key_field] or "none"].append(parse_curve(r["curve"]))
        for k, curves in sorted(by_key.items()):
            curves = [c for c in curves if len(c)]
            if not curves:
                continue
            n = min(len(c) for c in curves)
            t = curves[0][:n, 0]
            cov = np.array([c[:n, 1] for c in curves])
            ax.plot(t, cov.mean(0), label=k, color=COLORS.get(k))
            ax.fill_between(t, cov.mean(0) - cov.std(0), cov.mean(0) + cov.std(0), alpha=0.15, color=COLORS.get(k))
        ax.set_title(f"{env}: coverage over time")
        ax.set_xlabel("time [s]")
        ax.set_ylabel("coverage")
        ax.set_ylim(0, 1)
        ax.grid(alpha=0.3)
        ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(base + "_coverage.png", dpi=130)
    plt.close(fig)
    print("plots:", base + "_summary.png", base + "_coverage.png")


if __name__ == "__main__":
    import sys
    make_plots(sys.argv[1])
