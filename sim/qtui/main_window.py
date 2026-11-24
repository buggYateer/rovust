"""The main window: a slim header, the mission setup panel (collapsible),
live KPIs, the two maps, the telemetry tabs (collapsible) and a status bar
that shows one calm alert at a time. English or Egyptian Arabic."""
from __future__ import annotations

import os
import time

from PySide6.QtCore import QBuffer, QIODevice, QSettings, QSize, Qt, QTimer, QUrl
from PySide6.QtGui import QAction, QActionGroup, QDesktopServices, QKeySequence
from PySide6.QtWidgets import (QApplication, QButtonGroup, QCheckBox, QDialog, QDialogButtonBox, QDockWidget,
                               QFormLayout, QFrame, QHBoxLayout, QLabel, QLineEdit, QMainWindow, QProgressBar,
                               QPushButton, QScrollArea, QSizePolicy, QSplitter, QStackedWidget, QTabWidget,
                               QToolBar, QToolButton, QVBoxLayout, QWidget)

from .. import meta as T
from ..ai.brain import AIBrain
from ..alerts import AlertTracker, conditions
from ..mission import Mission
from ..report import REPORTS_DIR, ReportUploader, build_report, default_title, load_config, save_config
from ..teleop.server import ConsoleServer
from .gamepad import Gamepad
from .i18n import LANG, alert_text, behaviour, saved_language, tr
from .icons import icon
from .mapview import MapWidget
from .panels import (AboutDialog, ControlsDialog, EventsTab, GuideDialog, MotorTab, SensorsTab, SetupPanel, StatsTab,
                     legend_html)
from .popup import MapPopup
from .radio import RadioTab
from .theme_qt import apply_theme, color, ensure_icon, restyle

SPEEDS = [1, 4, 8, 16]
MODES = ["autonomous", "assisted", "manual"]


class ReportNameDialog(QDialog):
    """Asked before a manual "Send report": name the report, or send it with
    the automatic name (date, environment, machine). The mission number is
    always added by the Drive folder."""

    def __init__(self, default: str, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("sendReport"))
        self.setMinimumWidth(460)
        lay = QVBoxLayout(self)
        lay.addWidget(QLabel(tr("rnAsk")))
        self.edit = QLineEdit()
        self.edit.setPlaceholderText(default)
        self.edit.setToolTip(tr("rnEmpty"))
        lay.addWidget(self.edit)
        hint = QLabel(tr("rnSaved", default))
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        lay.addWidget(hint)
        box = QDialogButtonBox()
        self.btn_named = box.addButton(tr("rnNamed"), QDialogButtonBox.ButtonRole.AcceptRole)
        self.btn_auto = box.addButton(tr("rnAuto"), QDialogButtonBox.ButtonRole.ActionRole)
        box.addButton(QDialogButtonBox.StandardButton.Cancel)
        box.accepted.connect(self.accept)
        box.rejected.connect(self.reject)
        self.btn_auto.clicked.connect(self._use_auto)
        self.edit.returnPressed.connect(self.accept)
        self.edit.textChanged.connect(lambda t: self.btn_named.setEnabled(bool(t.strip())))
        self.btn_named.setEnabled(False)
        lay.addWidget(box)
        self._auto = False

    def _use_auto(self):
        self._auto = True
        self.accept()

    def title(self) -> str | None:
        return None if self._auto else (self.edit.text().strip() or None)


def hbox(margins=(0, 0, 0, 0), spacing=6):
    w = QWidget()
    lay = QHBoxLayout(w)
    lay.setContentsMargins(*margins)
    lay.setSpacing(spacing)
    return w, lay


def vsep():
    f = QFrame()
    f.setObjectName("sep")
    f.setFixedSize(1, 14)
    return f


class Kpi(QFrame):
    """One live number: label, value, optional meter."""

    def __init__(self, key: str, meter: bool = False, text: bool = False):
        super().__init__()
        self.setObjectName("kpi")
        self.key = key
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 8, 14, 10)
        lay.setSpacing(3)
        self.label = QLabel()
        self.label.setObjectName("kpiLabel")
        self.value = QLabel("-")
        self.value.setObjectName("kpiText" if text else "kpiValue")
        lay.addWidget(self.label)
        lay.addWidget(self.value)
        self.meter = None
        if meter:
            self.meter = QProgressBar()
            self.meter.setRange(0, 1000)
            self.meter.setTextVisible(False)
            lay.addWidget(self.meter)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)


class MapCard(QFrame):
    def __init__(self, view: MapWidget, title_key: str):
        super().__init__()
        self.setObjectName("mapcard")
        self.title_key = title_key
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 8, 12, 10)
        lay.setSpacing(4)
        head = QHBoxLayout()
        self.title = QLabel()
        self.title.setObjectName("mapTitle")
        self.sub = QLabel()
        self.sub.setObjectName("mapSub")
        head.addWidget(self.title)
        head.addWidget(self.sub)
        head.addStretch(1)
        lay.addLayout(head)
        lay.addWidget(view, 1)
        self.view = view

    def retranslate(self):
        self.title.setText(tr(self.title_key))
        self.title.setToolTip(tr(self.title_key + "S"))
        self.sub.hide()
        self.view.setToolTip(tr("enlargeTip"))


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowIcon(ensure_icon())
        self.resize(1500, 950)
        self.setMinimumSize(1180, 720)
        self.mission: Mission | None = None
        self.mission_no = 0
        self.paused = False
        self.speed = 1
        self._tick = 0
        self.settings = QSettings("RoboticsTeamProject", "RoverSimulator")
        self.server: ConsoleServer | None = None
        self._keys = set()
        self.uploader = ReportUploader()
        self._report_sent_for = None       # mission object that already got its automatic report
        self._report_text = ""
        self.alerts = AlertTracker()
        self._pad_sent = (0.0, None)       # (when, last value) of the controller's last drive packet
        self.popups = {}
        LANG.code = saved_language() if saved_language() in ("en", "ar") else "en"

        self.setup = SetupPanel()
        self.setup.start_requested.connect(self.start_mission)
        for cb in self.setup.layer_boxes.values():
            cb.toggled.connect(self._layers_changed)
        self.setup.mode.currentIndexChanged.connect(self._mode_changed)
        self.setup.loss.currentIndexChanged.connect(self._loss_changed)
        self.setup.server_btn.toggled.connect(self._toggle_server)

        self._build_central()
        self._build_side()
        self._build_telemetry()
        self._build_actions()
        self._build_menus()
        self._build_appbar()
        self._build_statusbar()

        # game controller (optional)
        self.pad = Gamepad(self)
        self.setup.set_pad(self.pad.available, "")
        self.pad.connected.connect(lambda n: self.setup.set_pad(True, n))
        self.pad.disconnected.connect(lambda: self.setup.set_pad(True, ""))
        self.pad.steer.connect(self._pad_steer)
        self.pad.drive.connect(self._pad_drive)
        self.pad.button.connect(self._pad_button)
        self.pad.live.connect(self.setup.pad_view.set_state)

        LANG.changed.connect(self.retranslate)
        QApplication.instance().installEventFilter(self)
        self.report_timer = QTimer(self)
        self.report_timer.setInterval(30000)
        self.report_timer.timeout.connect(lambda: self.uploader.flush(self._report_status))
        self.report_timer.start()
        QTimer.singleShot(3000, lambda: self.uploader.flush(self._report_status))
        self.timer = QTimer(self)
        self.timer.setInterval(16)
        self.timer.timeout.connect(self._on_tick)
        self.timer.start()
        LANG.set(LANG.code)                # applies the layout direction and all text
        self._set_dark(self.act_dark.isChecked())
        if self.uploader.pending:
            self._set_report_text(tr("reportsWaiting", len(self.uploader.pending)))

    # ================================================================ layout
    def _build_central(self):
        central = QWidget()
        v = QVBoxLayout(central)
        v.setContentsMargins(14, 12, 14, 10)
        v.setSpacing(10)
        # KPI row
        row = QHBoxLayout()
        row.setSpacing(10)
        self.kpis = {k: Kpi(k, meter=k in ("kCov", "kBatt", "kLink"), text=k == "kBeh")
                     for k in ("kCov", "kDist", "kBatt", "kLink", "kBeh", "kErr")}
        for k in self.kpis.values():
            row.addWidget(k)
        v.addLayout(row)
        # layer chips + legend
        chips_w, chips = hbox(spacing=6)
        self.layers_label = QLabel()
        self.layers_label.setObjectName("hint")
        chips.addWidget(self.layers_label)
        for b in self.setup.layer_boxes.values():
            chips.addWidget(b)
        chips.addStretch(1)
        v.addWidget(chips_w)
        # the two maps
        self.map_world = MapWidget("")
        self.map_belief = MapWidget("")
        self.map_world.clicked.connect(lambda: self._toggle_popup("world"))
        self.map_belief.clicked.connect(lambda: self._toggle_popup("belief"))
        self.card_world = MapCard(self.map_world, "world")
        self.card_belief = MapCard(self.map_belief, "belief")
        split = QSplitter(Qt.Orientation.Horizontal)
        split.setHandleWidth(10)
        split.addWidget(self.card_world)
        split.addWidget(self.card_belief)
        split.setSizes([1, 1])
        v.addWidget(split, 1)
        self.legend = QLabel()
        self.legend.setObjectName("hint")
        self.legend.setWordWrap(True)
        v.addWidget(self.legend)
        self.setCentralWidget(central)

    def _build_side(self):
        dock = QDockWidget(self)
        dock.setObjectName("setupDock")
        dock.setTitleBarWidget(QWidget())
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable)
        self.side_stack = QStackedWidget()
        # full panel
        full = QWidget()
        full.setObjectName("side")
        fl = QVBoxLayout(full)
        fl.setContentsMargins(0, 10, 0, 0)
        fl.setSpacing(4)
        head_w, head = hbox((14, 0, 8, 0))
        self.side_title = QLabel()
        self.side_title.setObjectName("sideTitle")
        self.side_btn = QToolButton()
        self.side_btn.setObjectName("iconbtn")
        self.side_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.side_btn.clicked.connect(lambda: self._collapse_side(True))
        head.addWidget(self.side_title, 1)
        head.addWidget(self.side_btn)
        fl.addWidget(head_w)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)   # never a sideways scroller
        scroll.setWidget(self.setup)
        fl.addWidget(scroll, 1)
        self.side_scroll = scroll
        # collapsed strip
        strip = QWidget()
        strip.setObjectName("sideStrip")
        sl = QVBoxLayout(strip)
        sl.setContentsMargins(8, 10, 8, 10)
        self.side_open_btn = QToolButton()
        self.side_open_btn.setObjectName("iconbtn")
        self.side_open_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.side_open_btn.clicked.connect(lambda: self._collapse_side(False))
        sl.addWidget(self.side_open_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        self.side_start_btn = QToolButton()
        self.side_start_btn.setObjectName("iconbtn")
        self.side_start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.side_start_btn.clicked.connect(self.start_mission)
        sl.addWidget(self.side_start_btn, 0, Qt.AlignmentFlag.AlignHCenter)
        sl.addStretch(1)
        self.side_stack.addWidget(full)
        self.side_stack.addWidget(strip)
        dock.setWidget(self.side_stack)
        self.setCorner(Qt.Corner.BottomLeftCorner, Qt.DockWidgetArea.LeftDockWidgetArea)
        self.setCorner(Qt.Corner.BottomRightCorner, Qt.DockWidgetArea.RightDockWidgetArea)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)
        self.setup_dock = dock
        dock.setMinimumWidth(360)
        dock.setMaximumWidth(560)
        self.resizeDocks([dock], [390], Qt.Orientation.Horizontal)
        if self.settings.value("sideCollapsed", False, type=bool):
            QTimer.singleShot(0, lambda: self._collapse_side(True))

    def _collapse_side(self, collapse: bool):
        self.side_stack.setCurrentIndex(1 if collapse else 0)
        if collapse:
            self.setup_dock.setMinimumWidth(52)
            self.setup_dock.setMaximumWidth(52)
        else:
            self.setup_dock.setMinimumWidth(360)
            self.setup_dock.setMaximumWidth(560)
            self.resizeDocks([self.setup_dock], [390], Qt.Orientation.Horizontal)
        self.settings.setValue("sideCollapsed", collapse)

    def _build_telemetry(self):
        self.tabs = QTabWidget()
        self.tabs.setObjectName("tele")
        self.tabs.setDocumentMode(True)
        self.tabs.tabBar().setDrawBase(False)       # Qt's own base line is drawn white, whatever the theme
        self.sensors_tab = SensorsTab()
        self.motor_tab = MotorTab()
        self.stats_tab = StatsTab()
        self.radio_tab = RadioTab()
        self.events_tab = EventsTab()
        for w in (self.sensors_tab, self.motor_tab, self.stats_tab, self.radio_tab, self.events_tab):
            self.tabs.addTab(w, "")
        self.tele_btn = QToolButton()
        self.tele_btn.setObjectName("iconbtn")
        self.tele_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.tele_btn.clicked.connect(lambda: self._collapse_tele(not self._tele_collapsed))
        self.tabs.setCornerWidget(self.tele_btn, Qt.Corner.TopRightCorner)
        self.tabs.tabBarClicked.connect(lambda _: self._tele_collapsed and self._collapse_tele(False))
        self.tabs.currentChanged.connect(lambda _: self._refresh_tab())
        wrap = QWidget()
        wrap.setObjectName("teleWrap")
        wl = QVBoxLayout(wrap)
        wl.setContentsMargins(6, 0, 6, 0)
        wl.addWidget(self.tabs)
        dock = QDockWidget(self)
        dock.setObjectName("telemetryDock")
        dock.setTitleBarWidget(QWidget())
        dock.setFeatures(QDockWidget.DockWidgetFeature.DockWidgetClosable)
        dock.setWidget(wrap)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, dock)
        self.telemetry_dock = dock
        self._tele_collapsed = False
        self.resizeDocks([dock], [300], Qt.Orientation.Vertical)

    def _collapse_tele(self, collapse: bool):
        self._tele_collapsed = collapse
        bar_h = self.tabs.tabBar().sizeHint().height() + 4
        if collapse:
            self._tele_h = max(200, self.telemetry_dock.height())
            self.tabs.widget(self.tabs.currentIndex()).hide()
            self.telemetry_dock.setMinimumHeight(bar_h)
            self.telemetry_dock.setMaximumHeight(bar_h)
        else:
            self.telemetry_dock.setMinimumHeight(120)
            self.telemetry_dock.setMaximumHeight(16777215)
            self.tabs.currentWidget().show()
            self.resizeDocks([self.telemetry_dock], [getattr(self, "_tele_h", 300)], Qt.Orientation.Vertical)
        self._recolor()

    # ================================================================ actions + menus
    def _build_actions(self):
        A = lambda **kw: QAction(self, **kw)
        self.act_new = A(shortcut=QKeySequence("Ctrl+N"), triggered=self.start_mission)
        self.act_restart = A(shortcut=QKeySequence("R"), triggered=self.restart_mission)
        self.act_exit = A(shortcut=QKeySequence("Ctrl+Q"), triggered=self.close)
        self.act_report = A(shortcut=QKeySequence("Ctrl+S"), triggered=lambda: self.send_report(ask=True))
        self.act_open_reports = A(triggered=lambda: (os.makedirs(REPORTS_DIR, exist_ok=True), QDesktopServices.openUrl(QUrl.fromLocalFile(REPORTS_DIR))))
        self.act_report_settings = A(triggered=self._report_settings)
        self.act_pause = A(shortcut=QKeySequence("Space"), checkable=True, triggered=self._toggle_pause)
        self.act_stop = A(shortcut=QKeySequence("Ctrl+."), triggered=self.stop_mission)
        self.speed_group = QActionGroup(self)
        self.speed_actions = {}
        for i, s in enumerate(SPEEDS):
            a = QAction(f"×{s}", self, checkable=True, shortcut=QKeySequence(str(i + 1)))
            a.triggered.connect(lambda checked, s=s: self.set_speed(s))
            self.speed_group.addAction(a)
            self.speed_actions[s] = a
        self.speed_actions[1].setChecked(True)
        self.act_lights = A(shortcut=QKeySequence("H"), checkable=True, triggered=self._toggle_lights)
        self.act_home = A(triggered=self._return_home)
        self.layer_actions = {}
        for key in self.setup.layer_boxes:
            a = QAction(self, checkable=True)
            a.setChecked(self.setup.layer_boxes[key].isChecked())
            a.toggled.connect(lambda on, key=key: self.setup.layer_boxes[key].setChecked(on))
            self.layer_actions[key] = a
        self.act_side = self.setup_dock.toggleViewAction()
        self.act_tele = self.telemetry_dock.toggleViewAction()
        self.act_dark = A(checkable=True, shortcut=QKeySequence("Ctrl+D"))
        self.act_dark.setChecked(self.settings.value("dark", True, type=bool))
        self.act_dark.toggled.connect(self._set_dark)
        self.act_lang = A(shortcut=QKeySequence("Ctrl+L"), triggered=self._toggle_lang)
        self.act_guide = A(shortcut=QKeySequence("F1"), triggered=lambda: GuideDialog(self).exec())
        self.act_controls = A(triggered=lambda: ControlsDialog(self).exec())
        self.act_about = A(triggered=lambda: AboutDialog(self).exec())

    def _build_menus(self):
        mb = self.menuBar()
        self.m_file = mb.addMenu("")
        self.m_file.addActions([self.act_new, self.act_restart])
        self.m_file.addSeparator()
        self.m_file.addActions([self.act_report, self.act_open_reports, self.act_report_settings])
        self.m_file.addSeparator()
        self.m_file.addAction(self.act_exit)
        self.m_mission = mb.addMenu("")
        self.m_mission.addActions([self.act_pause, self.act_stop])
        self.m_speed = self.m_mission.addMenu("")
        for s in SPEEDS:
            self.m_speed.addAction(self.speed_actions[s])
        self.m_mission.addSeparator()
        self.m_mission.addActions([self.act_lights, self.act_home])
        self.m_view = mb.addMenu("")
        self.m_view.addActions(list(self.layer_actions.values()))
        self.m_view.addSeparator()
        self.m_view.addActions([self.act_side, self.act_tele])
        self.m_view.addSeparator()
        self.m_view.addActions([self.act_dark, self.act_lang])
        self.m_help = mb.addMenu("")
        self.m_help.addActions([self.act_guide, self.act_controls])
        self.m_help.addSeparator()
        self.m_help.addAction(self.act_about)

    def _tb(self, action: QAction | None = None, name="tb", checkable=False):
        b = QPushButton()
        b.setObjectName(name)
        b.setCursor(Qt.CursorShape.PointingHandCursor)
        b.setCheckable(checkable)
        if action is not None:
            b.clicked.connect(lambda checked=False: action.trigger())
            if action.isCheckable():
                b.setCheckable(True)
                action.toggled.connect(b.setChecked)
                b.setChecked(action.isChecked())
        return b

    def _build_appbar(self):
        bar = QWidget()
        bar.setObjectName("appbar")
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(14, 8, 14, 8)
        lay.setSpacing(12)
        brand = QLabel(T.ROVER_NAME.upper())
        brand.setObjectName("brand")
        lay.addWidget(brand)
        # mission chip: number, environment, clock, status
        chip = QFrame()
        chip.setObjectName("mchip")
        cl = QHBoxLayout(chip)
        cl.setContentsMargins(12, 5, 8, 5)
        cl.setSpacing(10)
        self.chip_no = QLabel()
        self.chip_env = QLabel()
        self.chip_clock = QLabel("00:00")
        self.chip_clock.setObjectName("mono")
        self.pill = QLabel()
        self.pill.setObjectName("pill")
        for w in (self.chip_no, vsep(), self.chip_env, vsep(), self.chip_clock, self.pill):
            cl.addWidget(w)
        chip.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        lay.addWidget(chip)
        # transport
        grp = QFrame()
        grp.setObjectName("grp")
        gl = QHBoxLayout(grp)
        gl.setContentsMargins(3, 3, 3, 3)
        gl.setSpacing(2)
        self.b_new = self._tb(self.act_new, "primary")
        lay.addWidget(self.b_new)
        self.b_pause = self._tb(self.act_pause)
        self.b_stop = self._tb(self.act_stop)
        self.b_stop.setProperty("danger", "true")
        self.b_restart = self._tb(self.act_restart)
        for b in (self.b_pause, self.b_stop, self.b_restart):
            gl.addWidget(b)
        lay.addWidget(grp)
        # speed
        grp = QFrame()
        grp.setObjectName("grp")
        gl = QHBoxLayout(grp)
        gl.setContentsMargins(3, 3, 3, 3)
        gl.setSpacing(2)
        self.b_speed = {}
        for s in SPEEDS:
            b = self._tb(self.speed_actions[s])
            b.setText(f"×{s}")
            gl.addWidget(b)
            self.b_speed[s] = b
        lay.addWidget(grp)
        lay.addStretch(1)
        self.b_lights = self._tb(self.act_lights, "tbx")
        self.b_console = self._tb(None, "tbx", checkable=True)
        self.b_console.toggled.connect(self.setup.server_btn.setChecked)
        self.setup.server_btn.toggled.connect(lambda on: (self.b_console.blockSignals(True), self.b_console.setChecked(on), self.b_console.blockSignals(False)))
        self.b_report = self._tb(self.act_report, "tbx")
        self.b_lang = self._tb(self.act_lang, "tbx")
        self.b_theme = QToolButton()
        self.b_theme.setObjectName("iconbtn")
        self.b_theme.setCursor(Qt.CursorShape.PointingHandCursor)
        self.b_theme.clicked.connect(self.act_dark.toggle)
        for w in (self.b_lights, self.b_console, self.b_report, self.b_lang, self.b_theme):
            lay.addWidget(w)
        tb = QToolBar()
        tb.setObjectName("appbarTb")
        tb.setMovable(False)
        tb.setFloatable(False)
        tb.toggleViewAction().setVisible(False)
        tb.addWidget(bar)
        bar.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.addToolBar(tb)

    def _build_statusbar(self):
        sb = self.statusBar()
        sb.setSizeGripEnabled(False)
        aw, al = hbox((6, 3, 6, 3), 6)
        self.alert_btn = QPushButton()
        self.alert_btn.setObjectName("alert")
        self.alert_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.alert_btn.clicked.connect(self._alert_clicked)
        self.alert_btn.setMaximumWidth(560)
        self.alert_act = QPushButton()
        self.alert_act.setObjectName("alertAct")
        self.alert_act.setCursor(Qt.CursorShape.PointingHandCursor)
        self.alert_act.clicked.connect(lambda: self.act_lights.isChecked() or self.act_lights.trigger())
        self.alert_act.hide()
        self.alert_more = QLabel()
        self.alert_more.setObjectName("more")
        self.alert_more.hide()
        al.addWidget(self.alert_btn)
        al.addWidget(self.alert_act)
        al.addWidget(self.alert_more)
        al.addStretch(1)
        sb.addWidget(aw, 1)
        self.st_report = QLabel("")
        self.st_link = QLabel("")
        self.st_beh = QLabel("")
        self.st_cov = QLabel("")
        self.st_time = QLabel("")
        for w in (self.st_report, self.st_link, self.st_cov, self.st_beh, self.st_time):
            sb.addPermanentWidget(w)
        self._shown_alert = None

    # ================================================================ language / theme
    def _toggle_lang(self):
        LANG.set("en" if LANG.code == "ar" else "ar")

    def _place_side(self):
        """The setup panel sits on the reading side: left in English, right in Arabic."""
        area = Qt.DockWidgetArea.RightDockWidgetArea if LANG.rtl else Qt.DockWidgetArea.LeftDockWidgetArea
        if self.dockWidgetArea(self.setup_dock) != area:
            # Qt already mirrors dock areas in a right-to-left window, so "left" is drawn on the right
            pass
        self.resizeDocks([self.setup_dock], [52 if self.side_stack.currentIndex() else 390], Qt.Orientation.Horizontal)

    def retranslate(self, *_):
        self._place_side()
        self.setWindowTitle(f"{T.ROVER_NAME} - {tr('appTitle')}")
        for m, k in ((self.m_file, "mFile"), (self.m_mission, "mMission"), (self.m_view, "mView"), (self.m_help, "mHelp"), (self.m_speed, "mSpeed")):
            m.setTitle(tr(k))
        for a, k in ((self.act_new, "newMission"), (self.act_restart, "restartMission"), (self.act_exit, "exit"),
                     (self.act_report, "sendReport"), (self.act_open_reports, "openReports"), (self.act_report_settings, "reportSettings"),
                     (self.act_stop, "stopMission"), (self.act_lights, "lights"), (self.act_home, "homeNow"),
                     (self.act_side, "showSetup"), (self.act_tele, "showTele"), (self.act_dark, "darkMode"),
                     (self.act_lang, "language"), (self.act_guide, "guide"), (self.act_controls, "controls"), (self.act_about, "about")):
            a.setText(tr(k))
        self.act_pause.setText(tr("resume") if self.paused else tr("pause"))
        self.act_stop.setToolTip(tr("stopTip"))
        self.act_report.setToolTip(tr("reportTip"))
        for key, a in self.layer_actions.items():
            a.setText(tr(key))
        # header
        self.b_pause.setText(tr("resume") if self.paused else tr("pause"))
        self.b_stop.setText(tr("stopMission"))
        self.b_stop.setToolTip(tr("stopTip"))
        self.b_restart.setText(tr("restart"))
        self.b_lights.setText(tr("lights"))
        self.b_console.setText(tr("console"))
        self.b_report.setText(tr("sendReport"))
        self.b_new.setText(tr("newBtn"))
        self.b_report.setToolTip(tr("reportTip"))
        self.b_lang.setText(tr("language"))
        self.b_lang.setToolTip(tr("langTip"))
        self.b_theme.setToolTip(tr("themeTip"))
        self._update_chip()
        # panels
        self.side_title.setText(tr("setup"))
        self.side_btn.setToolTip(tr("collapse"))
        self.side_open_btn.setToolTip(tr("expand"))
        self.side_start_btn.setToolTip(tr("start"))
        for k in self.kpis.values():
            k.label.setText(tr(k.key))
        self.layers_label.setText(tr("layers") + ":")
        self.card_world.retranslate()
        self.card_belief.retranslate()
        self.legend.setText(legend_html())
        for i, k in enumerate(("tSens", "tMotor", "tStats", "tRadio", "tEvents")):
            self.tabs.setTabText(i, tr(k))
        self.tele_btn.setToolTip(tr("teleExpand") if self._tele_collapsed else tr("teleCollapse"))
        self.alert_btn.setToolTip(tr("a_tip"))
        self.alert_act.setText(tr("a_darkBtn"))
        if self.mission is None:
            self._show_alert_text(None)
        self._shown_alert = None
        self.events_tab.show_log(self.alerts.log, force=True)
        self.map_world.update()
        self.map_belief.update()
        self._recolor()
        self._update_status(force=True)

    def _recolor(self):
        mut, txt, bad = color("muted"), color("text"), color("bad")
        self.b_pause.setIcon(icon("play" if self.paused else "pause", txt))
        self.b_stop.setIcon(icon("stop", bad if getattr(self, "_live", False) else color("faint")))
        self.b_restart.setIcon(icon("restart", txt))
        self.b_lights.setIcon(icon("bulb", color("accent") if self.act_lights.isChecked() else txt))
        self.b_console.setIcon(icon("phone", color("accent") if self.b_console.isChecked() else txt))
        self.b_report.setIcon(icon("upload", color("text")))
        self.b_new.setIcon(icon("play", color("on_accent")))
        self.b_theme.setIcon(icon("sun" if self.act_dark.isChecked() else "moon", mut, 18))
        self.side_btn.setIcon(icon("panel", mut, 18))
        self.side_open_btn.setIcon(icon("panel", mut, 18))
        self.side_start_btn.setIcon(icon("play", color("accent"), 18))
        self.tele_btn.setIcon(icon("up" if self._tele_collapsed else "down", mut, 18))
        for w in (self.b_new, self.b_pause, self.b_stop, self.b_restart, self.b_lights, self.b_console, self.b_report, self.b_lang):
            w.setIconSize(QSize(15, 15))
            # reserve room for the widest look of the button (bold / checked), so no letter is ever cut
            f = w.font()
            f.setBold(True)
            from PySide6.QtGui import QFontMetrics
            text_w = QFontMetrics(f).horizontalAdvance(w.text())
            w.setMinimumWidth(text_w + (24 if w.icon().isNull() else 46))
        self._update_enabled()
        self.setup.recolor()

    def _set_dark(self, dark):
        apply_theme(QApplication.instance(), dark)
        self.settings.setValue("dark", dark)
        self._recolor()
        self.setup.show_console_url(self.setup._console_url or None, self.setup._console_err)
        self.legend.setText(legend_html())
        self.events_tab.show_log(self.alerts.log, force=True)
        self.update()

    # ================================================================ missions
    def start_mission(self):
        cfg = self.setup.config()
        ai = AIBrain() if cfg["ai"] else None
        self.mission = Mission(cfg["env"], cfg["strategy"], seed=cfg["seed"], localisation=cfg["localisation"], ai=ai)
        if ai is not None:
            ai.attach(self.mission)
        self.mission_no += 1
        self.paused = False
        self.act_pause.setChecked(False)
        self._toggle_pause(False)
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
        self.alerts.reset()
        self._shown_alert = None
        self.events_tab.show_log(self.alerts.log, force=True)
        for pop in self.popups.values():
            pop.set_mission(self.mission, layers)
        self._update_chip()
        self._recolor()
        self._update_enabled()

    def restart_mission(self):
        if self.mission is not None:
            self.start_mission()

    def _toggle_pause(self, checked):
        self.paused = checked
        txt = tr("resume") if checked else tr("pause")
        self.act_pause.setText(txt)
        if hasattr(self, "b_pause"):
            self.b_pause.setText(txt)
            self.b_pause.setIcon(icon("play" if checked else "pause", color("text")))

    def stop_mission(self):
        if self.mission is not None and not self.mission.done:
            self.mission.stop()
            self.paused = False
            self.act_pause.setChecked(False)
            self._toggle_pause(False)

    def set_speed(self, s):
        self.speed = s
        self.speed_actions[s].setChecked(True)

    def _toggle_lights(self, on):
        if self.mission is not None:
            self.mission.robot.headlights = on
        if hasattr(self, "b_lights"):
            self.b_lights.setIcon(icon("bulb", color("accent") if on else color("text")))

    def _return_home(self):
        if self.mission is not None and not self.mission.done:
            self.mission.returning = True
            self.mission.stats["return_reason"] = "operator"

    def _update_enabled(self):
        """A control is clickable only when it can do something: nothing that
        needs a mission works before one starts, nothing that drives works
        once it is over."""
        if not hasattr(self, "b_pause"):
            return
        m = self.mission
        has, live = m is not None, m is not None and not m.done
        for a, b, on in ((self.act_pause, self.b_pause, live), (self.act_stop, self.b_stop, live),
                         (self.act_restart, self.b_restart, has), (self.act_lights, self.b_lights, live),
                         (self.act_report, self.b_report, has), (self.act_home, None, live)):
            a.setEnabled(on)
            if b is not None:
                b.setEnabled(on)
        # the link-lost choice only matters when someone drives over the radio
        self.setup.loss.setEnabled(self.setup.mode.currentData() != "autonomous")
        self.setup.loss_label.setEnabled(self.setup.loss.isEnabled())
        if getattr(self, "_live", None) != live:
            self._live = live
            self.b_stop.setIcon(icon("stop", color("bad") if live else color("faint")))

    def _update_chip(self):
        m = self.mission
        self.chip_no.setText(f"{tr('mission')} #{self.mission_no}" if m else tr("noMission"))
        self.chip_env.setText(tr(m.cfg.name) if m else "")
        if m is None:
            self.chip_clock.setText("00:00")

    # ================================================================ reports
    def _grab_png(self, widget) -> bytes:
        widget.banner_enabled = False
        widget.repaint()
        pix = widget.grab()
        widget.banner_enabled = True
        buf = QBuffer()
        buf.open(QIODevice.OpenModeFlag.WriteOnly)
        pix.save(buf, "PNG")
        return bytes(buf.data())

    def send_report(self, ask: bool = False):
        """Save (and upload) a report of the running mission. With ``ask`` the
        operator may type a name for it; the automatic send at the end of a
        mission uses the default name."""
        m = self.mission
        if m is None:
            self._set_report_text(tr("startFirst"))
            return
        title = None
        if ask:
            dlg = ReportNameDialog(default_title(m), self)
            if dlg.exec() != QDialog.DialogCode.Accepted:
                return
            title = dlg.title()
        images = {"true_world.png": self._grab_png(self.map_world), "robot_map.png": self._grab_png(self.map_belief)}
        folder = build_report(m, images, title=title)
        self._report_sent_for = m
        if self.uploader.configured:
            self.uploader.queue(folder)
            self._set_report_text(tr("reportSaved"))
            self.uploader.flush(self._report_status)
        else:
            self._set_report_text(tr("reportLocal", os.path.basename(folder)))

    def _set_report_text(self, text):
        self.st_report.setText(text)

    def _report_status(self, text):
        # called from the upload thread: hop back to the GUI thread
        QTimer.singleShot(0, lambda: self._set_report_text(text))

    def _report_settings(self):
        cfg = load_config()
        dlg = QDialog(self)
        dlg.setWindowTitle(tr("reportSettings").replace("&", ""))
        lay = QFormLayout(dlg)
        url = QLineEdit(cfg.get("upload_url", ""))
        url.setPlaceholderText("https://script.google.com/macros/s/.../exec")
        url.setMinimumWidth(460)
        auto = QCheckBox(tr("rsAuto"))
        auto.setChecked(bool(cfg.get("auto_send", True)))
        hint = QLabel(tr("rsHint"))
        hint.setWordWrap(True)
        hint.setObjectName("hint")
        lay.addRow(tr("rsUrl"), url)
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

    # ================================================================ map pop-up
    def _toggle_popup(self, kind):
        if self.mission is None:
            return
        pop = self.popups.get(kind)
        if pop is not None and pop.isVisible():
            pop.close()
            return
        title = f"{tr(kind)} ({tr(kind + 'S')})"
        pop = MapPopup(self, title, self.mission, kind, self.setup.layers())
        self.popups[kind] = pop
        pop.show()

    # ================================================================ teleop
    def _mirror_mission_controls(self, m):
        """Commands from the phone console (mode, link-loss policy, headlights)
        change the mission directly; show that state on the desktop controls
        too, without re-sending it."""
        for combo, value in ((self.setup.mode, m.mode), (self.setup.loss, m.on_link_loss)):
            i = combo.findData(value)
            if i >= 0 and i != combo.currentIndex():
                combo.blockSignals(True)
                combo.setCurrentIndex(i)
                combo.blockSignals(False)
                if combo is self.setup.mode:
                    self.setup.mode_seg._sync()
        if self.act_lights.isChecked() != m.robot.headlights:
            self.act_lights.blockSignals(True)
            self.act_lights.setChecked(m.robot.headlights)
            self.act_lights.blockSignals(False)
            self.b_lights.setChecked(m.robot.headlights)
            self._toggle_lights(m.robot.headlights)

    def _mode_changed(self, _):
        if self.mission is not None:
            # the operator's own console is wired to the rover, not radio
            self.mission.mode = self.setup.mode.currentData()
            self.mission.link_fallback = False
            self.mission.operator_cmd = (0.0, 0.0)
        self._update_enabled()
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
                self.setup.show_console_url(self.server.url)
                self.tabs.setCurrentWidget(self.radio_tab)
                if self.side_stack.currentIndex() == 1:
                    self._collapse_side(False)          # the QR code lives in the panel: show it
                # bring the QR code into view so the phone can scan it straight away
                QTimer.singleShot(50, lambda: self.side_scroll.ensureWidgetVisible(self.setup.qr, 0, 16))
            except OSError as e:
                self.server = None
                self.setup.show_console_url(None, str(e))
                self.setup.server_btn.setChecked(False)
        else:
            if self.server is not None:
                self.server.stop()
                self.server = None
            self.setup.show_console_url(None)
        self.setup.server_btn.setText(tr("closeConsole") if self.server is not None else tr("openConsole"))
        self._recolor()
        self.setFocus()

    # ---- game controller
    def _pad_ready(self) -> bool:
        m = self.mission
        if m is None or m.done or self.paused:
            return False
        if m.mode == "autonomous":
            # touching the stick means "I want to drive": hand over, keep the safety layers on
            self.setup.mode.setCurrentIndex(MODES.index("assisted"))
        return True

    def _pad_send(self, value, send):
        """Rate-limit the controller: a packet when the stick moves, and every
        0.3 s while it is held (that keeps the rover's watchdog fed)."""
        now = time.monotonic()
        last_t, last_v = self._pad_sent
        moved = last_v is None or max(abs(a - b) for a, b in zip(value, last_v)) > 0.08
        if moved or now - last_t > 0.3 or value == (0.0, 0.0):
            send()
            self._pad_sent = (now, value)

    def _pad_steer(self, x, y):
        if (x or y) and not self._pad_ready():
            return
        m = self.mission
        if m is not None and not m.done:
            self._pad_send((x, y), lambda: m.operator_steer(x, y, source="controller"))

    def _pad_drive(self, fwd, turn):
        if (fwd or turn) and not self._pad_ready():
            return
        m = self.mission
        if m is not None and not m.done:
            self._pad_send((fwd, turn), lambda: m.operator_drive(fwd, turn, source="controller"))

    def _pad_button(self, name):
        m = self.mission
        if m is None or m.done:
            return
        if name == "start":
            m.operator_command({"type": "stop", "from": "controller"})
        elif name == "b":
            self.act_lights.trigger()
        elif name == "x":
            m.operator_command({"type": "home", "from": "controller"})
        elif name in ("leftshoulder", "rightshoulder"):
            i = MODES.index(m.mode) + (1 if name == "rightshoulder" else -1)
            self.setup.mode.setCurrentIndex(i % len(MODES))

    # ---- keyboard
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
        from PySide6.QtWidgets import QAbstractSpinBox
        if event.type() in (QEvent.Type.KeyPress, QEvent.Type.KeyRelease):
            key = self._drive_key(event)
            m = self.mission
            if key is not None and m is not None and m.mode != "autonomous" \
                    and not isinstance(QApplication.focusWidget(), (QLineEdit, QAbstractSpinBox)):
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

    # ================================================================ alerts + status
    def _alert_clicked(self):
        """The status-bar alert opens the event log."""
        if self._tele_collapsed:
            self._collapse_tele(False)
        self.telemetry_dock.show()
        self.tabs.setCurrentWidget(self.events_tab)

    def _show_alert_text(self, a, more: int = 0):
        if a is None:
            self.alert_btn.setText(tr("ready"))
            sev = "info"
        else:
            self.alert_btn.setText(alert_text(a))
            sev = a.sev
        if self.alert_btn.property("sev") != sev:
            self.alert_btn.setProperty("sev", sev)
            restyle(self.alert_btn)
        dot = {"bad": "bad", "warn": "warn", "info": "muted", "good": "good"}[sev]
        self.alert_btn.setIcon(icon("dot", color(dot), 12))
        self.alert_act.setVisible(a is not None and a.act == "lights" and not self.act_lights.isChecked())
        self.alert_more.setVisible(more > 0)
        self.alert_more.setText(f"+{more}")

    def _update_alerts(self, m):
        operated = m.mode != "autonomous" or self.server is not None
        shown = self.alerts.update(conditions(m, paused=self.paused, operated=operated), m.time)
        if self.server is not None:
            self.server.paused = self.paused
        key = (shown.id, shown.args, self.alerts.more, LANG.code, self.act_lights.isChecked())
        if key != self._shown_alert:
            self._shown_alert = key
            self._show_alert_text(shown, self.alerts.more)
        n = self.alerts.problems
        label = tr("tEvents") + (f"  ({n})" if n else "")
        if self.tabs.tabText(4) != label:
            self.tabs.setTabText(4, label)
        if self.tabs.currentWidget() is self.events_tab:
            self.events_tab.show_log(self.alerts.log)
        return shown

    def _update_status(self, force=False):
        m = self.mission
        if m is None:
            self.pill.setText(tr("st_ready"))
            self.pill.setProperty("sev", "idle")
            restyle(self.pill)
            for k in self.kpis.values():
                k.value.setText("-")
            return
        shown = self.alerts.shown
        st = "paused" if self.paused and not m.done else m.status
        sev = "info" if m.done or self.paused else (shown.sev if shown is not None and shown.sev in ("bad", "warn") else "good")
        self.pill.setText(tr("st_" + st))
        if self.pill.property("sev") != sev or force:
            self.pill.setProperty("sev", sev)
            restyle(self.pill)
        mm, ss = divmod(int(m.time), 60)
        self.chip_clock.setText(f"{mm:02d}:{ss:02d}")
        cov = m.coverage()
        K = self.kpis
        K["kCov"].value.setText(f"{cov:.0%}")
        K["kCov"].meter.setValue(int(cov * 1000))
        K["kDist"].value.setText(f"{m.robot.distance:.1f} m")
        bat = m.robot.battery.fraction
        K["kBatt"].value.setText(f"{bat:.0%}")
        K["kBatt"].meter.setValue(int(bat * 1000))
        lk = m.link
        if m.mode == "autonomous" and self.server is None:
            K["kLink"].value.setText(tr("linkNone"))
            K["kLink"].value.setObjectName("kpiText")
            K["kLink"].meter.setValue(0)
        else:
            K["kLink"].value.setText(f"{lk.strength:.0%}")
            K["kLink"].value.setObjectName("kpiValue")
            K["kLink"].meter.setValue(int(lk.strength * 1000))
        if K["kLink"].value.property("_shape") != K["kLink"].value.objectName():
            K["kLink"].value.setProperty("_shape", K["kLink"].value.objectName())
            restyle(K["kLink"].value)
        K["kBeh"].value.setText(behaviour(m.arbiter.active_name) if not m.done else "-")
        K["kErr"].value.setText(f"{m.estimator.error():.2f} m")
        # status bar, right side
        if m.mode == "autonomous" and self.server is None:
            self.st_link.setText("")
        else:
            self.st_link.setText(f"{tr('sbLink')} {lk.strength:.0%}")
        self.st_cov.setText(f"{tr('sbCov')} {cov:.1%}")
        self.st_beh.setText(f"{tr('sbBeh')}: {behaviour(m.arbiter.active_name)}")
        self.st_time.setText(f"t = {m.time:.1f} s   ×{self.speed}")

    def _refresh_tab(self):
        idx = self.tabs.currentIndex()
        if idx == 0:
            self.sensors_tab.refresh()
        elif idx == 1:
            self.motor_tab.refresh()
        elif idx == 2:
            self.stats_tab.refresh()
        elif idx == 3:
            self.radio_tab.refresh()
        else:
            self.events_tab.show_log(self.alerts.log)

    # ================================================================ loop
    def _on_tick(self):
        if self.server is not None and self.server.restart_requested:
            self.server.restart_requested = False
            self.restart_mission()
        m = self.mission
        if m is None:
            if self._tick % 30 == 0:
                self._update_status()
            self._tick += 1
            return
        if not self.paused and not m.done:
            if self._keys and m.mode != "autonomous" and self._tick % 8 == 0:
                self._key_drive()                   # keep the watchdog fed while a key is held
            # at most ~12 ms of simulation per frame: at high speed the simulation runs
            # as fast as it can, but the window never stops responding
            t0 = time.perf_counter()
            for _ in range(self.speed):
                m.step()
                self.motor_tab.push_sample()
                if m.done or time.perf_counter() - t0 > 0.018:
                    break
        if m.done and self._report_sent_for is not m and self.uploader.cfg.get("auto_send", True):
            self.send_report()
        self._tick += 1
        if self._tick % 2 == 0 or m.done:                # 30 frames a second is plenty for the maps
            self.map_world.update()
            self.map_belief.update()
            for pop in self.popups.values():
                pop.refresh()
        if getattr(self, "_live", None) != (not m.done):
            self._update_enabled()
        if self._tick % 3 == 0:
            self._mirror_mission_controls(m)
            self._update_alerts(m)
            if not self._tele_collapsed:
                self._refresh_tab()
            self._update_status()

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
    icon_ = ensure_icon()
    app.setWindowIcon(icon_)
    w = MainWindow()
    w.setWindowIcon(icon_)
    w.showMaximized()
    return app.exec()
