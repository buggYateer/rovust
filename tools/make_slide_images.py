"""Pictures made for the presentation: the explored maps of each world, drawn
by the application's own map widget, at slide resolution.

    python tools/make_slide_images.py      -> docs/presentation/img/*.png
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from sim.ai import AIBrain  # noqa: E402
from sim.mission import Mission  # noqa: E402
from sim.qtui.mapview import MapWidget  # noqa: E402
from sim.qtui.theme_qt import apply_theme, load_fonts  # noqa: E402

OUT = os.path.join(ROOT, "docs", "presentation", "img")
LAYERS = {"sonar": False, "ir": False, "terrain": True, "frontiers": True, "visited": False, "true_path": False}


def run(env, seconds, seed=1):
    ai = AIBrain()
    m = Mission(env, "utility", seed=seed, localisation="fused", ai=ai)
    ai.attach(m)
    while m.time < seconds and not m.done:
        m.step()
    return m


def grab(m, kind, w, h, name, dark=True):
    view = MapWidget("")
    view.set_mission(m, kind, dict(LAYERS, true_path=(kind == "world")))
    view.banner_enabled = False
    view.resize(w, h)
    view.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    view.show()
    QApplication.processEvents()
    view._geo = view._geometry()
    _, ox, oy, pw, ph = view._geo
    # just the map: no margin, no frame, square corners
    view.grab().copy(int(ox) + 1, int(oy) + 1, int(pw) - 2, int(ph) - 2).save(os.path.join(OUT, name))
    print(name)


def main():
    app = QApplication.instance() or QApplication([])
    load_fonts()
    apply_theme(app, True)
    os.makedirs(OUT, exist_ok=True)
    cave = run("cave", 330)
    grab(cave, "world", 1100, 900, "cover_world.png")
    grab(cave, "belief", 1100, 900, "cover_map.png")
    for env, secs in (("cave", 330), ("mars", 330), ("underwater", 330)):
        m = cave if env == "cave" else run(env, secs)
        grab(m, "world", 900, 700, f"world_{env}.png")


if __name__ == "__main__":
    main()
