"""The main window: menus, toolbar, setup dock, two maps, bottom tabs, status bar."""
from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction, QActionGroup, QKeySequence
from PySide6.QtWidgets import (QApplication, QDockWidget, QLabel, QMainWindow, QScrollArea, QSplitter, QTabWidget,
                               QToolBar, QVBoxLayout, QWidget)

from ..ai.brain import AIBrain
from ..mission import Mission
from ..ui import theme as T
from .mapview import MapWidget
from .panels import (LEGEND_HTML, AboutDialog, ControlsDialog, GuideDialog, MotorTab, SensorsTab, SetupPanel,
                     StatsTab)

SPEEDS = [1, 4, 8, 16]


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Exploration Rover Simulator")
        self.resize(1500, 950)
        self.setMinimumSize(1100, 700)
        self.mission: Mission | None = None
        self.paused = False
        self.speed = 1
        self._tick = 0

        # ---- central: the two maps + legend
        central = QWidget()
        v = QVBoxLayout(central)
        v.setContentsMargins(6, 6, 6, 0)
        self.map_world = MapWidget("TRUE WORLD  (the robot never sees this)")
        self.map_belief = MapWidget("ROBOT'S MAP  (built from its own sensors)")
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
        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)
        dock = QDockWidget("Mission setup", self)
        dock.setObjectName("setupDock")
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setWidget(self.setup)
        scroll.setMinimumWidth(290)
        dock.setWidget(scroll)
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetMovable | QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        self.setup_dock = dock

        # ---- bottom dock: tabs
        self.tabs = QTabWidget()
        self.sensors_tab = SensorsTab()
        self.motor_tab = MotorTab()
        self.stats_tab = StatsTab()
        self.tabs.addTab(self.sensors_tab, "Sensors")
        self.tabs.addTab(self.motor_tab, "Motor control")
        self.tabs.addTab(self.stats_tab, "Statistics")
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
        m_file.addAction(self.act_exit)

        m_mission = mb.addMenu("&Mission")
        self.act_pause = QAction("&Pause", self, shortcut=QKeySequence("Space"), checkable=True, triggered=self._toggle_pause)
        m_mission.addAction(self.act_pause)
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
        tb.addAction(self.act_restart)
        tb.addSeparator()
        tb.addWidget(QLabel("  Speed: "))
        for s in SPEEDS:
            tb.addAction(self.speed_actions[s])
        tb.addSeparator()
        tb.addAction(self.act_lights)
        self.addToolBar(tb)

    def _build_statusbar(self):
        sb = self.statusBar()
        self.st_status = QLabel("Ready - configure a mission on the left and press Start")
        self.st_time = QLabel("")
        self.st_cov = QLabel("")
        self.st_beh = QLabel("")
        sb.addWidget(self.st_status, 1)
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
        layers = self.setup.layers()
        self.map_world.set_mission(self.mission, "world", layers)
        self.map_belief.set_mission(self.mission, "belief", layers)
        self.sensors_tab.set_mission(self.mission)
        self.motor_tab.set_mission(self.mission)
        self.stats_tab.set_mission(self.mission)
        self.setWindowTitle(f"Exploration Rover Simulator - {T.ENV_TITLES[cfg['env']]} / {self.mission.explorer.name} / {cfg['localisation']}")

    def restart_mission(self):
        if self.mission is not None:
            self.start_mission()

    def _toggle_pause(self, checked):
        self.paused = checked
        self.act_pause.setText("Resume" if checked else "Pause")

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

    def _layers_changed(self):
        layers = self.setup.layers()
        for key, a in self.layer_actions.items():
            if a.isChecked() != layers[key]:
                a.blockSignals(True)
                a.setChecked(layers[key])
                a.blockSignals(False)
        self.map_world.layers = layers
        self.map_belief.layers = layers

    # ------------------------------------------------------------------ loop
    def _on_tick(self):
        m = self.mission
        if m is None:
            return
        if not self.paused and not m.done:
            for _ in range(self.speed):
                m.step()
                self.motor_tab.push_sample()
                if m.done:
                    break
        self._tick += 1
        self.map_world.update()
        self.map_belief.update()
        if self._tick % 3 == 0:
            idx = self.tabs.currentIndex()
            if idx == 0:
                self.sensors_tab.refresh()
            elif idx == 1:
                self.motor_tab.refresh()
            else:
                self.stats_tab.refresh()
            status = m.status.upper() + (f" ({m.stats['return_reason']})" if m.stats["return_reason"] else "")
            if self.paused:
                status += "  -  PAUSED"
            self.st_status.setText(status)
            self.st_beh.setText(f"behaviour: {m.arbiter.active_name}   ")
            self.st_cov.setText(f"coverage {m.coverage():.1%}   ")
            self.st_time.setText(f"t = {m.time:.1f} s   x{self.speed}")

    def closeEvent(self, event):
        self.timer.stop()
        event.accept()


def run():
    import sys
    app = QApplication(sys.argv)
    app.setApplicationName("Exploration Rover Simulator")
    app.setOrganizationName("Robotics Team Project")
    w = MainWindow()
    w.show()
    return app.exec()
