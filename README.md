# Multi-Environment Autonomous Exploration Rover

A Python simulation of an autonomous exploration rover, built from the actuator
and sensor level up (DC motors, PWM, encoders, PID, a full on-board sensor
suite) to mapping, exploration and AI terrain classification. One robot, three
selectable environments: **cave**, **Mars**, **underwater**.

Robotics course project — Dr. Elshaimaa Nabil Nada.

## Setup

```bash
python -m venv .venv
.venv\Scripts\activate        # Windows
pip install -r requirements.txt
```

## Run

```bash
python main.py                # interactive simulator (environment menu)
python -m sim.experiments.run_batch --help   # headless experiments
pytest                        # unit tests
```

See [docs/Task1_v2.md](docs/Task1_v2.md) for the full proposal.
