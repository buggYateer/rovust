"""Control-lecture demo: step response of the motor under on-off, hysteresis,
P, PI and PID control, plus the PWM calibration curve.

    python -m sim.experiments.pid_demo      -> results/pid_step_response.png
"""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from ..config import MotorConfig
from ..robot.control import HysteresisController, OnOffController, PIDController
from ..robot.encoder import IncrementalEncoder
from ..robot.motor import DCMotor, calibration_table

RESULTS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "results")


def step_response(controller, target=6.0, t_end=6.0, dt=0.05, load_at=3.0):
    cfg = MotorConfig()
    m = DCMotor(cfg)
    enc = IncrementalEncoder(cfg.encoder_ticks, cfg.gear_ratio)
    ts, ws, duties = [], [], []
    t = 0.0
    while t < t_end:
        enc.update(m.angle)
        m.load = 0.5 if t > load_at else 0.0          # a hill at t = 3 s
        m.set_duty(controller.update(target, enc.wheel_speed(dt), dt))
        m.step(dt)
        ts.append(t)
        ws.append(m.wheel_omega)
        duties.append(m.duty)
        t += dt
    return ts, ws, duties


def main():
    os.makedirs(RESULTS, exist_ok=True)
    fig, axes = plt.subplots(1, 3, figsize=(17, 4.8))
    ctrls = [("on-off", OnOffController()), ("hysteresis", HysteresisController(band=0.1)),
             ("P", PIDController(0.08)), ("PI", PIDController(0.08, 0.6)), ("PID", PIDController(0.08, 0.6, 0.002))]
    for name, c in ctrls:
        ts, ws, duties = step_response(c)
        axes[0].plot(ts, ws, label=name)
        axes[1].plot(ts, duties, label=name)
    axes[0].axhline(6.0, color="k", ls="--", lw=1, label="desired")
    axes[0].axvline(3.0, color="gray", ls=":", lw=1)
    axes[0].set_title("Wheel speed step response (load applied at t = 3 s)")
    axes[0].set_xlabel("time [s]")
    axes[0].set_ylabel("wheel speed [rad/s]")
    axes[0].legend(fontsize=8)
    axes[0].grid(alpha=0.3)
    axes[1].set_title("PWM duty cycle")
    axes[1].set_xlabel("time [s]")
    axes[1].set_ylabel("duty")
    axes[1].grid(alpha=0.3)
    for load in (0.0, 0.3, 0.6):
        rows = calibration_table(MotorConfig(), steps=21, load=load)
        axes[2].plot([d for d, _ in rows], [w for _, w in rows], marker="o", ms=3, label=f"load {load}")
    axes[2].set_title("Motor calibration: duty cycle vs steady-state wheel speed")
    axes[2].set_xlabel("PWM duty")
    axes[2].set_ylabel("wheel speed [rad/s]")
    axes[2].legend(fontsize=8)
    axes[2].grid(alpha=0.3)
    fig.tight_layout()
    out = os.path.join(RESULTS, "pid_step_response.png")
    fig.savefig(out, dpi=130)
    print("wrote", out)


if __name__ == "__main__":
    main()
