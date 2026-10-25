"""Entry point.

    python main.py             # desktop interface (Qt / PySide6)
    python main.py --pygame    # legacy single-window Pygame interface
"""
import sys


def main():
    if "--pygame" in sys.argv:
        from sim.ui.app import App
        App().run()
        return 0
    try:
        from sim.qtui.main_window import run
    except ImportError as e:
        print("PySide6 is not installed (pip install PySide6); falling back to the Pygame interface.", e)
        from sim.ui.app import App
        App().run()
        return 0
    return run()


if __name__ == "__main__":
    sys.exit(main())
