"""Entry point.

    python main.py             # desktop interface (Qt / PySide6)
"""
import sys


def main():
    try:
        from sim.qtui.main_window import run
    except ImportError as e:
        print("PySide6 is not installed. Run setup.bat (or: pip install -r requirements.txt).", e)
        return 1
    return run()


if __name__ == "__main__":
    sys.exit(main())
