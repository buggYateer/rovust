"""AI 1: terrain classification from the camera (scikit-learn).

The camera returns a 16x16 grayscale patch of the ground ahead. A Random
Forest trained on synthetic patches (the same texture generator the camera
uses, but the classifier never sees the true map) predicts the terrain
class. The predicted class is written into the terrain-cost layer of the
robot's map, so the A* planner avoids sand and mud and prefers bedrock.
Only pixels go in; the robot's own cost map comes out.
"""
from __future__ import annotations

import os
import pickle

import numpy as np
from sklearn.ensemble import RandomForestClassifier

from ..sensors.camera import CLASSES, PATCH, synth_patch

MODEL_PATH = os.path.join(os.path.dirname(__file__), "terrain_rf.pkl")

# planner cost per predicted class (mirrors TerrainProps.move_cost)
CLASS_COST = {"ground": 1.0, "sand": 2.5, "rock": 6.0, "mud": 4.0, "bedrock": 0.8, "water": 1.0, "pit": 8.0}


def features(img: np.ndarray) -> np.ndarray:
    """Hand-crafted texture features: cheap, and enough for 7 classes.
    (A small CNN would do the same job with more compute.)"""
    img = img.astype(np.float32)
    gx = np.diff(img, axis=1)
    gy = np.diff(img, axis=0)
    hist, _ = np.histogram(img, bins=8, range=(0, 1))
    f = [img.mean(), img.std(), np.abs(gx).mean(), np.abs(gy).mean(), gx.std(), gy.std(),
         np.percentile(img, 10), np.percentile(img, 90),
         (np.abs(gx) > 0.15).mean(),                       # fraction of sharp edges
         np.abs(np.fft.rfft(img.mean(axis=0))[1:5]).sum(),  # horizontal periodicity (ripples)
         np.abs(np.fft.rfft(img.mean(axis=1))[1:5]).sum()]
    return np.concatenate([f, hist / img.size])


class TerrainClassifier:
    def __init__(self, model_path: str = MODEL_PATH):
        self.model_path = model_path
        self.model: RandomForestClassifier | None = None
        self.accuracy = None
        self.predictions = 0
        self.correct = 0            # evaluated against the camera's true label (for the report only)
        self.last_label = "?"
        self.last_proba = 0.0

    # ----------------------------------------------------------------- train
    def train(self, n_per_class: int = 400, seed: int = 0, save: bool = True):
        rng = np.random.default_rng(seed)
        X, y = [], []
        for ci, c in enumerate(CLASSES):
            for _ in range(n_per_class):
                light = rng.uniform(0.05, 1.0)
                X.append(features(synth_patch(c, rng, light)))
                y.append(ci)
        X, y = np.array(X), np.array(y)
        idx = rng.permutation(len(X))
        n_test = len(X) // 5
        test, train = idx[:n_test], idx[n_test:]
        self.model = RandomForestClassifier(n_estimators=120, max_depth=14, random_state=seed)
        self.model.fit(X[train], y[train])
        self.accuracy = float((self.model.predict(X[test]) == y[test]).mean())
        if save:
            with open(self.model_path, "wb") as f:
                pickle.dump({"model": self.model, "accuracy": self.accuracy}, f)
        return self.accuracy

    def load(self) -> bool:
        if os.path.exists(self.model_path):
            with open(self.model_path, "rb") as f:
                d = pickle.load(f)
            self.model, self.accuracy = d["model"], d["accuracy"]
            return True
        return False

    def ensure(self):
        if self.model is None and not self.load():
            self.train()

    # --------------------------------------------------------------- predict
    def predict(self, img: np.ndarray) -> tuple[str, float]:
        self.ensure()
        proba = self.model.predict_proba(features(img)[None, :])[0]
        k = int(np.argmax(proba))
        self.last_label, self.last_proba = CLASSES[k], float(proba[k])
        return self.last_label, self.last_proba

    def cost_for(self, label: str) -> float:
        return CLASS_COST.get(label, 1.0)
