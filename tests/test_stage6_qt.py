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


def test_stop_and_restart_ask_about_the_report(tmp_path, monkeypatch):
    """Stop / Restart ask first; a report sent mid-mission keeps the run's key
    (same number on Drive) and does not replace the final report."""
    import json

    from PySide6.QtWidgets import QApplication
    import sim.report as R
    from sim.qtui.main_window import MainWindow

    monkeypatch.setattr(R, "REPORTS_DIR", str(tmp_path))
    monkeypatch.setattr(R, "INDEX_CSV", str(tmp_path / "missions.csv"))
    monkeypatch.setattr(R, "PENDING_PATH", str(tmp_path / "pending.json"))
    app = QApplication.instance() or QApplication([])
    w = MainWindow()
    w.uploader.cfg = {"upload_url": "", "auto_send": False}     # never upload from a test
    w.uploader.pending = []
    answers = []
    monkeypatch.setattr(w, "_ask_report", lambda kind: answers.pop(0))

    def missions():
        return sorted(p for p in tmp_path.iterdir() if p.is_dir())

    def reports():
        return sorted(r for p in missions() for r in p.iterdir() if r.is_dir())

    w.start_mission()
    for _ in range(3):
        w._on_tick()
    key = w._mission_key
    answers.append(None)                 # cancel: nothing happens
    w.stop_mission()
    assert not w.mission.done and reports() == []

    w.send_report()                      # mid-mission snapshot
    assert len(reports()) == 1 and w._report_sent_for is not w.mission
    answers.append("send")               # stop and send report
    w.stop_mission()
    assert w.mission.done and len(reports()) == 2 and w._report_sent_for is w.mission
    keys = {json.load(open(p / "metrics.json", encoding="utf-8"))["mission_key"] for p in reports()}
    assert keys == {key}
    # one folder for the run, the reports numbered inside it
    assert len(missions()) == 1
    assert [r.name.split(" - ")[0] for r in reports()] == ["Report 1", "Report 2"]

    old = w.mission
    w.restart_mission()                  # already over: restarts without asking
    assert w.mission is not old and w._mission_key != key
    answers.append("plain")              # restart a running mission without a report
    old = w.mission
    w.restart_mission()
    assert old.done and w.mission is not old and len(reports()) == 2
    w.close()

    sent = {}

    class Resp:
        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

        def read(self):
            return b'{"ok": true, "number": 7, "name": "x"}'

    def fake_urlopen(req, timeout=0):
        sent.update(json.loads(req.data))
        return Resp()

    monkeypatch.setattr(R.urllib.request, "urlopen", fake_urlopen)
    up = R.ReportUploader.__new__(R.ReportUploader)
    up.cfg = {"upload_url": "https://example.invalid/exec"}
    up.pending = [str(r) for r in reports()]
    up.lock = __import__("threading").Lock()
    first, second = reports()
    ok, _ = up.send_folder(str(first))
    assert ok and sent["key"] == key and sent["report"] == first.name
    assert sent["name"].startswith("Mission #new - ")
    # the bridge named the run "x": the local folder follows, and the report still waiting moves with it
    assert (tmp_path / "x" / second.name).is_dir()
    assert str(tmp_path / "x" / second.name) in up.pending
    assert "Mission #7" in (tmp_path / "x" / first.name / "report.html").read_text(encoding="utf-8")
