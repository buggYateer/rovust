"""The main window: menus, toolbar, setup dock, two maps, bottom tabs, status bar."""
from __future__ import annotations

import os

from PySide6.QtCore import QSettings, Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtCore import QBuffer, QIODevice, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QDialogButtonBox, QDockWidget, QFormLayout, QLabel,
                               QLineEdit, QMainWindow, QScrollArea, QSplitter, QTabWidget, QToolBar, QVBoxLayout,
                               QWidget)

from ..ai.brain import AIBrain
from ..mission import Mission
from ..ui import theme as T
from .mapview import MapWidget
from .panels import (LEGEND_HTML, AboutDialog, ControlsDialog, GuideDialog, MotorTab, SensorsTab, SetupPanel,
                     StatsTab)
from ..report import ReportUploader, build_report, load_config, save_config, REPORTS_DIR
from .popup import MapPopup
from .radio import RadioTab
from .theme_qt import apply_theme, ensure_icon
from ..teleop.server import ConsoleServer

SPEEDS = [1, 4, 8, 16]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"{T.ROVER_NAME} - Multi-Environment Exploration Rover")
        self.setWindowIcon(ensure_icon())
        self.resize(1500, 950)
        self.setMinimumSize(1100, 700)
        self.mission: Mission | None = None
        self.paused = False
        self.speed = 1
        self._tick = 0
        self.settings = QSettings("RoboticsTeamProject", "RoverSimulator")
        self.server: ConsoleServer | None = None
        self._keys = set()
        self.uploader = ReportUploader()
        self._report_sent_for = None       # mission object that already got its automatic report

        # ---- central: the two maps + legend
        central = QWidget()
        v = QVBoxLayout(central)
        v.setContentsMargins(6, 6, 6, 0)
        self.map_world = MapWidget("TRUE WORLD  (the robot never sees this)")
        self.map_belief = MapWidget("ROBOT'S MAP  (built from its own sensors)")
        self.map_world.clicked.connect(lambda: self._toggle_popup("world"))
        self.map_belief.clicked.connect(lambda: self._toggle_popup("belief"))
        self.popups = {}
        split = QSplitter(Qt.Orientation.Horizontal)
        split.addWidget(self.map_world)
        split.addWidget(self.map_belief)
        split.setSizes([1, 1])
        v.addWidget(split, 1)
        legend = QLabel(LEGEND_HTML)
        legend.setStyleSheet("color:#444; padding: 2px 4px;")
        v.addWidget(legend)
        self.setCentralWidget(central)

        # ---- left dock: mission setup
        self.setup = SetupPanel()
        self.setup.start_requested.connect(self.start_mission)
        for cb in self.setup.layer_boxes.values():
            cb.toggled.connect(self._layers_changed)
        self.setup.mode.currentIndexChanged.connect(self._mode_changed)
        self.setup.loss.currentIndexChanged.connect(self._loss_changed)
        self.setup.server_btn.toggled.connect(self._toggle_server)
        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)
        dock = QDockWidget("Mission setup", self)
        dock.setObjectName("setupDock")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)   # never a sideways scroller
        scroll.setWidget(self.setup)
        scroll.setMinimumWidth(320)
        self.setup.setMinimumWidth(0)
        dock.setWidget(scroll)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        self.setup_dock = dock
        self.resizeDocks([dock], [360], Qt.Orientation.Horizontal)

        # ---- bottom dock: tabs
        self.tabs = QTabWidget()
        self.sensors_tab = SensorsTab()
        self.motor_tab = MotorTab()
        self.stats_tab = StatsTab()
        self.radio_tab = RadioTab()
        self.tabs.addTab(self.sensors_tab, "Sensors")
        self.tabs.addTab(self.motor_tab, "Motor control")
        self.tabs.addTab(self.stats_tab, "Statistics")
        self.tabs.addTab(self.radio_tab, "Radio link")
        dock = QDockWidget("Telemetry", self)
        dock.setObjectName("telemetryDock")
        dock.setWidget(self.tabs)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        self.telemetry_dock = dock
        self.resizeDocks([dock], [300], Qt.Orientation.Vertical)

        self._build_menus()
        self._build_toolbar()
        self._build_statusbar()

        QApplication.instance().installEventFilter(self)
        self.report_timer = QTimer(self)
        self.report_timer.setInterval(30000)
        self.report_timer.timeout.connect(lambda: self.uploader.flush(self._report_status))
        self.report_timer.start()
        QTimer.singleShot(3000, lambda: self.uploader.flush(self._report_status))
        if self.uploader.pending:
            self.st_report.setText(f"{len(self.uploader.pending)} report(s) waiting to upload   ")
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start()

    # ------------------------------------------------------------------ menus
    def _build_menus(self):
        mb = self.menuBar()
        m_file = mb.addMenu("&File")
        self.act_new = QAction("&New mission", self, shortcut=QKeySequence("Ctrl+N"), triggered=self.start_mission)
        self.act_restart = QAction("&Restart mission", self, shortcut=QKeySequence("R"), triggered=self.restart_mission)
        self.act_exit = QAction("E&xit", self, shortcut=QKeySequence("Ctrl+Q"), triggered=self.close)
        m_file.addActions([self.act_new, self.act_restart])
        m_file.addSeparator()
        self.act_report = QAction("&Send report", self, shortcut=QKeySequence("Ctrl+S"), triggered=self.send_report)
        self.act_report.setToolTip("Save a report of this mission (statistics + maps) and upload it to the team's Drive folder")
        m_file.addAction(self.act_report)
        m_file.addAction(QAction("Open reports &folder", self, triggered=lambda: (os.makedirs(REPORTS_DIR, exist_ok=True), QDesktopServices.openUrl(QUrl.fromLocalFile(REPORTS_DIR)))))
        m_file.addAction(QAction("Report se&ttings...", self, triggered=self._report_settings))
        m_file.addSeparator()
        m_file.addAction(self.act_exit)

        m_mission = mb.addMenu("&Mission")
        self.act_pause = QAction("&Pause", self, shortcut=QKeySequence("Space"), checkable=True, triggered=self._toggle_pause)
        self.act_stop = QAction("&Stop mission", self, shortcut=QKeySequence("Ctrl+."), triggered=self.stop_mission)
        self.act_stop.setToolTip("End the mission here and keep everything on screen (you can still send a report)")
        m_mission.addAction(self.act_pause)
        m_mission.addAction(self.act_stop)
        speed_menu = m_mission.addMenu("&Speed")
        self.speed_group = QActionGroup(self)
        self.speed_actions = {}
        for i, s in enumerate(SPEEDS):
            a = QAction(f"x{s}", self, checkable=True, shortcut=QKeySequence(str(i + 1)))
            a.triggered.connect(lambda checked, s=s: self.set_speed(s))
            self.speed_group.addAction(a)
            speed_menu.addAction(a)
            self.speed_actions[s] = a
        self.speed_actions[1].setChecked(True)
        m_mission.addSeparator()
        self.act_lights = QAction("&Headlights", self, shortcut=QKeySequence("H"), checkable=True, triggered=self._toggle_lights)
        self.act_home = QAction("Return &home now", self, triggered=self._return_home)
        m_mission.addActions([self.act_lights, self.act_home])

        m_view = mb.addMenu("&View")
        self.layer_actions = {}
        for key, label in [("sonar", "Sonar echoes"), ("ir", "IR beams"), ("terrain", "Terrain layer (AI)"),
                           ("frontiers", "Frontiers and target"), ("visited", "Visited cells"), ("true_path", "True path")]:
            a = QAction(label, self, checkable=True)
            a.setChecked(self.setup.layer_boxes[key].isChecked())
            a.toggled.connect(lambda on, key=key: self.setup.layer_boxes[key].setChecked(on))
            self.layer_actions[key] = a
            m_view.addAction(a)
        m_view.addSeparator()
        m_view.addAction(self.setup_dock.toggleViewAction())
        m_view.addAction(self.telemetry_dock.toggleViewAction())
        m_view.addSeparator()
        self.act_dark = QAction("&Dark mode", self, checkable=True, shortcut=QKeySequence("Ctrl+D"))
        self.act_dark.setChecked(self.settings.value("dark", False, type=bool))
        self.act_dark.toggled.connect(self._set_dark)
        m_view.addAction(self.act_dark)
        self._set_dark(self.act_dark.isChecked())

        m_help = mb.addMenu("&Help")
        m_help.addAction(QAction("&User guide", self, shortcut=QKeySequence("F1"), triggered=lambda: GuideDialog(self).exec()))
        m_help.addAction(QAction("&Controls", self, triggered=lambda: ControlsDialog(self).exec()))
        m_help.addSeparator()
        m_help.addAction(QAction("&About", self, triggered=lambda: AboutDialog(self).exec()))

    def _build_toolbar(self):
        tb = QToolBar("Mission")
        tb.setObjectName("missionToolbar")
        tb.setMovable(False)
        tb.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextOnly)
        tb.addAction(self.act_new)
        tb.addAction(self.act_pause)
        tb.addAction(self.act_stop)
        tb.addAction(self.act_restart)
        tb.addSeparator()
        tb.addWidget(QLabel("  Speed: "))
        for s in SPEEDS:
            tb.addAction(self.speed_actions[s])
        tb.addSeparator()
        tb.addAction(self.act_lights)
        tb.addSeparator()
        tb.addAction(self.act_report)
        tb.addSeparator()
        tb.addAction(self.act_dark)
        self.addToolBar(tb)

    def _build_statusbar(self):
        sb = self.statusBar()
        self.st_status = QLabel("Ready - configure a mission on the left and press Start")
        self.st_time = QLabel("")
        self.st_cov = QLabel("")
        self.st_beh = QLabel("")
        self.st_link = QLabel("")
        self.st_report = QLabel("")
        sb.addWidget(self.st_status, 1)
        sb.addPermanentWidget(self.st_report)
        sb.addPermanentWidget(self.st_link)
        sb.addPermanentWidget(self.st_beh)
        sb.addPermanentWidget(self.st_cov)
        sb.addPermanentWidget(self.st_time)

    # --------------------------------------------------------------- actions
    def start_mission(self):
        cfg = self.setup.config()
        ai = AIBrain() if cfg["ai"] else None
        self.mission = Mission(cfg["env"], cfg["strategy"], seed=cfg["seed"], localisation=cfg["localisation"], ai=ai)
        if ai is not None:
            ai.attach(self.mission)
        self.paused = False
        self.act_pause.setChecked(False)
        self.act_lights.setChecked(self.mission.robot.headlights)
        self.mission.mode = self.setup.mode.currentData()
        self.mission.on_link_loss = self.setup.loss.currentData()
        layers = self.setup.layers()
        self.map_world.set_mission(self.mission, "world", layers)
        self.map_belief.set_mission(self.mission, "belief", layers)
        self.sensors_tab.set_mission(self.mission)
        self.motor_tab.set_mission(self.mission)
        self.stats_tab.set_mission(self.mission)
        self.radio_tab.set_mission(self.mission)
        for pop in self.popups.values():
            pop.set_mission(self.mission, layers)
        self.setWindowTitle(f"{T.ROVER_NAME} - {T.ENV_TITLES[cfg['env']]} / {self.mission.explorer.name} / {cfg['localisation']}")

    def restart_mission(self):
        if self.mission is not None:
            self.start_mission()

    def _toggle_pause(self, checked):
        self.paused = checked
        self.act_pause.setText("Resume" if checked else "Pause")

    def stop_mission(self):
        if self.mission is not None and not self.mission.done:
            self.mission.stop()
            self.paused = False
            self.act_pause.setChecked(False)

    def set_speed(self, s):
        self.speed = s
        self.speed_actions[s].setChecked(True)

    def _toggle_lights(self, on):
        if self.mission is not None:
            self.mission.robot.headlights = on

    def _return_home(self):
        if self.mission is not None and not self.mission.done:
            self.mission.returning = True
            self.mission.stats["return_reason"] = "operator"

    # -------------------------------------------------------------- reports
    def _grab_png(self, widget) -> bytes:
        widget.banner_enabled = False
        widget.repaint()
        pix = widget.grab()
        widget.banner_enabled = True
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        pix.save(buf, "PNG")
        return bytes(buf.data())

    def send_report(self):
        m = self.mission
        if m is None:
            self.st_report.setText("start a mission first   ")
            return
        images = {"true_world.png": self._grab_png(self.map_world), "robot_map.png": self._grab_png(self.map_belief)}
        folder = build_report(m, images)
        self._report_sent_for = m
        if self.uploader.configured:
            self.uploader.queue(folder)
            self.st_report.setText("report saved - uploading...   ")
            self.uploader.flush(self._report_status)
        else:
            self.st_report.setText(f"report saved locally ({os.path.basename(folder)}) - set the Drive bridge in File > Report settings   ")

    def _report_status(self, text):
        # called from the upload thread: hop back to the GUI thread
        QTimer.singleShot(0, lambda: self.st_report.setText(text + "   "))

    def _report_settings(self):
        cfg = load_config()
        dlg = QDialog(self)
        dlg.setWindowTitle("Report settings")
        lay = QFormLayout(dlg)
        url = QLineEdit(cfg.get("upload_url", ""))
        url.setPlaceholderText("https://script.google.com/macros/s/.../exec")
        url.setMinimumWidth(460)
        auto = QCheckBox("Send a report automatically when a mission ends")
        auto.setChecked(bool(cfg.get("auto_send", True)))
        hint = QLabel('The URL comes from the Google Apps Script bridge described in docs/DRIVE_REPORTS.md. '
                      'Reports are always saved under reports/ as well.')
        hint.setWordWrap(True)
        hint.setObjectName("hint")
        lay.addRow("Drive bridge URL:", url)
        lay.addRow("", auto)
        lay.addRow(hint)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Save | QDialogButtonBox.StandardButton.Cancel)
        bb.accepted.connect(dlg.accept)
        bb.rejected.connect(dlg.reject)
        lay.addRow(bb)
        if dlg.exec():
            cfg["upload_url"] = url.text().strip()
            cfg["auto_send"] = auto.isChecked()
            save_config(cfg)
            self.uploader.cfg = cfg
            self.uploader.flush(self._report_status)

    # ----------------------------------------------------------- map pop-up
    def _toggle_popup(self, kind):
        if self.mission is None:
            return
        pop = self.popups.get(kind)
        if pop is not None and pop.isVisible():
            pop.close()
            return
        title = "True world (the robot never sees this)" if kind == "world" else "Robot's map (built from its own sensors)"
        pop = MapPopup(self, title, self.mission, kind, self.setup.layers())
        self.popups[kind] = pop
        pop.show()

    # ----------------------------------------------------------- teleop
    def _mode_changed(self, _):
        if self.mission is not None:
            # the operator's own console is wired to the rover, not radio
            self.mission.mode = self.setup.mode.currentData()
            self.mission.link_fallback = False
            self.mission.operator_cmd = (0.0, 0.0)
        self.setFocus()

    def _loss_changed(self, _):
        if self.mission is not None:
            self.mission.on_link_loss = self.setup.loss.currentData()
        self.setFocus()

    def _toggle_server(self, on):
        if on:
            try:
                self.server = ConsoleServer(lambda: self.mission, port=8080)
                self.server.start()
                self.setup.server_url.setText(f"On the phone or tablet (same Wi-Fi) open:\n{self.server.url}")
                self.setup.server_btn.setText("Close console")
                self.tabs.setCurrentWidget(self.radio_tab)
            except OSError as e:
                self.setup.server_url.setText(f"Could not start the console: {e}")
                self.setup.server_btn.setChecked(False)
        else:
            if self.server is not None:
                self.server.stop()
                self.server = None
            self.setup.server_url.setText("")
            self.setup.server_btn.setText("Open console for phone / tablet")
        self.setFocus()

    def _set_dark(self, dark):
        apply_theme(QApplication.instance(), dark)
        self.settings.setValue("dark", dark)
        self.update()

    # Windows virtual-key codes of the physical W A S D keys: these do not change
    # with the keyboard layout (an Arabic layout sends Arabic letters as text,
    # but the key itself is still VK 0x57 etc.)
    VK_TO_KEY = {0x57: Qt.Key.Key_W, 0x41: Qt.Key.Key_A, 0x53: Qt.Key.Key_S, 0x44: Qt.Key.Key_D}
    DRIVE_KEYS = {Qt.Key.Key_Up, Qt.Key.Key_Down, Qt.Key.Key_Left, Qt.Key.Key_Right,
                  Qt.Key.Key_W, Qt.Key.Key_A, Qt.Key.Key_S, Qt.Key.Key_D}
    KEY_TURN = 0.75        # keyboard steering authority (full stick would be 1.0)

    def _drive_key(self, event):
        key = self.VK_TO_KEY.get(event.nativeVirtualKey(), event.key())
        return key if key in self.DRIVE_KEYS else None

    def eventFilter(self, obj, event):
        """Driving keys work wherever the focus is (a combo box, the table...),
        as long as a mission is in assisted or manual mode."""
        from PySide6.QtCore import QEvent
        from PySide6.QtWidgets import QAbstractSpinBox, QLineEdit
        if event.type() in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            key = self._drive_key(event)
            m = self.mission
            if key is not None and m is not None and m.mode != "autonomous"                     and not isinstance(QApplication.focusWidget(), (QLineEdit, QAbstractSpinBox)):
                if not event.isAutoRepeat():
                    if event.type() == QEvent.Type.KeyPress:
                        self._keys.add(key)
                    else:
                        self._keys.discard(key)
                    self._key_drive()
                return True
        return super().eventFilter(obj, event)

    def _key_drive(self):
        m = self.mission
        if m is None or m.mode == "autonomous":
            return
        k = self._keys
        fwd = (1 if (Qt.Key.Key_Up in k or Qt.Key.Key_W in k) else 0) - (1 if (Qt.Key.Key_Down in k or Qt.Key.Key_S in k) else 0)
        turn = (1 if (Qt.Key.Key_Left in k or Qt.Key.Key_A in k) else 0) - (1 if (Qt.Key.Key_Right in k or Qt.Key.Key_D in k) else 0)
        m.operator_drive(fwd, self.KEY_TURN * turn)

    def _layers_changed(self):
        layers = self.setup.layers()
        for key, a in self.layer_actions.items():
            if a.isChecked() != layers[key]:
                a.blockSignals(True)
                a.setChecked(layers[key])
                a.blockSignals(False)
        self.map_world.layers = layers
        self.map_belief.layers = layers
        for pop in self.popups.values():
            pop.view.layers = layers

    # ------------------------------------------------------------------ loop
    def _on_tick(self):
        if self.server is not None and self.server.restart_requested:
            self.server.restart_requested = False
            self.restart_mission()
        m = self.mission
        if m is None:
            return
        if not self.paused and not m.done:
            if self._keys and m.mode != "autonomous" and self._tick % 8 == 0:
                self._key_drive()                   # keep the watchdog fed while a key is held
            for _ in range(self.speed):
                m.step()
                self.motor_tab.push_sample()
                if m.done:
                    break
        if m.done and self._report_sent_for is not m and self.uploader.cfg.get("auto_send", True):
            self.send_report()
        self._tick += 1
        self.map_world.update()
        self.map_belief.update()
        for pop in self.popups.values():
            pop.refresh()
        if self._tick % 3 == 0:
            idx = self.tabs.currentIndex()
            if idx == 0:
                self.sensors_tab.refresh()
            elif idx == 1:
                self.motor_tab.refresh()
            elif idx == 2:
                self.stats_tab.refresh()
            else:
                self.radio_tab.refresh()
            status = m.status.upper() + (f" ({m.stats['return_reason']})" if m.stats["return_reason"] else "")
            if self.paused:
                status += "  -  PAUSED"
            self.st_status.setText(status)
            self.st_beh.setText(f"behaviour: {m.arbiter.active_name}   ")
            lk = m.link
            if m.mode == "autonomous" and self.server is None:
                self.st_link.setText("")
            else:
                extra = "  (rover on its own)" if m.link_fallback else ""
                keys = "   drive: hold arrow keys / W A S D" if m.mode != "autonomous" else ""
                self.st_link.setText(f"link: {lk.state} {lk.strength:.0%}{extra}{keys}   ")
            self.st_cov.setText(f"coverage {m.coverage():.1%}   ")
            self.st_time.setText(f"t = {m.time:.1f} s   x{self.speed}")

    def closeEvent(self, event):
        self.timer.stop()
        if self.server is not None:
            self.server.stop()
        event.accept()


def run():
    import sys
    if sys.platform == "win32":
        # Without its own AppUserModelID the taskbar groups the window under
        # python.exe and shows Python's icon instead of ours.
        try:
            import ctypes
            ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(f"RoboticsTeamProject.{T.ROVER_NAME}.Simulator.1")
        except Exception:
            pass
    app = QApplication(sys.argv)
    app.setApplicationName(f"{T.ROVER_NAME} Rover Simulator")
    app.setOrganizationName("Robotics Team Project")
    icon = ensure_icon()
    app.setWindowIcon(icon)
    w = MainWindow()
    w.setWindowIcon(icon)
    w.showMaximized()
    return app.exec()
