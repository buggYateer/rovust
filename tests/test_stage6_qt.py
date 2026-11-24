import os

import pytest

pytest.importorskip("PySide6")
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")


def test_qt_window_runs_a_mission():
    from PySide6.QtWidgets import QApplication
    from sim.qtui.main_window import MainWindow
    from sim.qtui.panels import AboutDialog, GuideDialog

    from sim.qtui.i18n import LANG
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    LANG.set("en")
    w.show()
    w.setup.env.setCurrentIndex(1)          # mars
    w.setup.strategy.setCurrentIndex(2)     # utility (AI)
    w.start_mission()
    w.set_speed(8)
    for _ in range(30):
        w._on_tick()
        app.processEvents()
    assert w.mission.step_count >= 200
    for i in range(5):
        w.tabs.setCurrentIndex(i)
        w._on_tick()
        app.processEvents()
    # inject a fault through the table's buttons
    from PySide6.QtWidgets import QPushButton
    cell = w.sensors_tab.table.cellWidget(0, 3)
    dead = [b for b in cell.findChildren(QPushButton) if b.property("mode") == "dead"][0]
    dead.click()
    assert w.mission.robot.sensors.sensors[0].fault == "dead"
    assert AboutDialog(w) is not None and GuideDialog(w) is not None
    w.close()


def test_arabic_layout_and_alert_footer():
    from PySide6.QtCore import Qt
    from PySide6.QtWidgets import QApplication
    from sim.qtui.i18n import LANG, tr
    from sim.qtui.main_window import MainWindow

    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    w.show()
    LANG.set("ar")
    assert app.layoutDirection() == Qt.LayoutDirection.RightToLeft
    assert w.setup.start_btn.text() == tr("start") != "Start mission"
    w.start_mission()
    w.set_speed(8)
    for _ in range(40):
        w._on_tick()
        app.processEvents()
    assert w.alert_btn.text()                      # one alert (or "all good") is always shown
    assert w.tabs.count() == 5                     # sensors, motor, stats, radio, events
    w._collapse_tele(True)
    w._collapse_tele(False)
    w._collapse_side(True)
    w._collapse_side(False)
    LANG.set("en")
    assert app.layoutDirection() == Qt.LayoutDirection.LeftToRight
    w.close()


def test_sensor_columns_resize_sensibly():
    from PySide6.QtWidgets import QApplication, QHeaderView
    from sim.qtui.panels import SensorsTab

    app = QApplication.instance() or QApplication([])
    tab = SensorsTab()
    tab.resize(1200, 300)
    tab.show()
    app.processEvents()
    t, hdr = tab.table, tab.table.horizontalHeader()
    # the columns fill the table: the reading column took the spare room
    assert sum(t.columnWidth(i) for i in range(5)) == t.viewport().width()
    # widening a column widens that column (it is never inverted)
    w = t.columnWidth(3)
    hdr.resizeSection(3, w + 60)
    assert t.columnWidth(3) == w + 60
    # no column goes below its minimum
    for i in range(4):
        hdr.resizeSection(i, 10)
        assert t.columnWidth(i) == SensorsTab.COL_MIN[i]
    # the last column has no edge to drag
    assert hdr.sectionResizeMode(4) == QHeaderView.ResizeMode.Fixed
    tab.close()


def test_console_address_has_a_qr_code():
    pytest.importorskip("segno")
    from sim.qtui.panels import qr_pixmap

    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    pm = qr_pixmap("http://192.168.1.4:8080", 132)
    assert pm is not None and pm.width() == pm.height() and pm.width() >= 100
