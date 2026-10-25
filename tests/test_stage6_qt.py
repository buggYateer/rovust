import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_qt_window_runs_a_mission():
    from PySide6.QtWidgets import QApplication
    from sim.qtui.main_window import MainWindow
    from sim.qtui.panels import AboutDialog, GuideDialog

    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    w.show()
    w.setup.env.setCurrentIndex(1)          # mars
    w.setup.strategy.setCurrentIndex(2)     # utility (AI)
    w.start_mission()
    w.set_speed(8)
    for _ in range(30):
        w._on_tick()
        app.processEvents()
    assert w.mission.step_count >= 200
    for i in range(3):
        w.tabs.setCurrentIndex(i)
        w._on_tick()
        app.processEvents()
    # inject a fault through the table's combo box
    combo = w.sensors_tab.table.cellWidget(0, 4)
    combo.setCurrentText("dead")
    assert w.mission.robot.sensors.sensors[0].fault == "dead"
    assert AboutDialog(w) is not None and GuideDialog(w) is not None
    w.close()
