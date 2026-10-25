"""Side panel (mission setup), bottom tabs (sensors, motor control, statistics) and the About dialog."""
from __future__ import annotations

from collections import deque

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QComboBox, QDialog, QDialogButtonBox, QFormLayout,
                               QFrame, QGroupBox, QHBoxLayout, QHeaderView, QLabel, QProgressBar, QPushButton,
                               QSizePolicy, QSpinBox, QTableWidget, QTableWidgetItem, QVBoxLayout, QWidget)

from ..sensors.base import FAULT_MODES
from ..ui import theme as T

ENV_ORDER = ["cave", "mars", "underwater"]


class SetupPanel(QWidget):
    """Left panel: choose environment, strategy, localisation, options; start."""
    start_requested = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(10, 10, 10, 10)
        lay.setSpacing(10)

        g = QGroupBox("Environment")
        f = QVBoxLayout(g)
        self.env = QComboBox()
        for e in ENV_ORDER:
            self.env.addItem(T.ENV_TITLES[e], e)
        self.env_desc = QLabel()
        self.env_desc.setWordWrap(True)
        self.env_desc.setStyleSheet("color: #777;")
        self.env.currentIndexChanged.connect(self._env_changed)
        f.addWidget(self.env)
        f.addWidget(self.env_desc)
        lay.addWidget(g)

        g = QGroupBox("Exploration strategy")
        f = QVBoxLayout(g)
        self.strategy = QComboBox()
        for k, label in T.STRATEGIES:
            self.strategy.addItem(label, k)
        f.addWidget(self.strategy)
        lay.addWidget(g)

        g = QGroupBox("Localisation used by the robot")
        f = QVBoxLayout(g)
        self.loc = QComboBox()
        for k, label in T.LOCALISATION:
            self.loc.addItem(label, k)
        f.addWidget(self.loc)
        lay.addWidget(g)

        g = QGroupBox("Options")
        f = QFormLayout(g)
        self.ai = QCheckBox("Terrain classifier + fault detector")
        self.ai.setChecked(True)
        self.seed = QSpinBox()
        self.seed.setRange(0, 999)
        self.seed.setValue(1)
        self.seed.setToolTip("Changes the generated map and the sensor noise")
        f.addRow("AI", self.ai)
        f.addRow("Seed", self.seed)
        lay.addWidget(g)

        self.start_btn = QPushButton("Start mission")
        self.start_btn.setMinimumHeight(36)
        font = self.start_btn.font()
        font.setBold(True)
        self.start_btn.setFont(font)
        self.start_btn.clicked.connect(self.start_requested.emit)
        lay.addWidget(self.start_btn)

        g = QGroupBox("Remote control")
        f = QVBoxLayout(g)
        self.mode = QComboBox()
        for k, label in [("autonomous", "Autonomous - the rover drives itself"),
                         ("assisted", "Assisted - you steer, safety layers stay on"),
                         ("manual", "Manual - you drive, nothing stops you")]:
            self.mode.addItem(label, k)
        f.addWidget(self.mode)
        self.loss = QComboBox()
        for k, label in [("home", "Link lost: return home"), ("explore", "Link lost: explore alone"),
                         ("hold", "Link lost: wait for the link")]:
            self.loss.addItem(label, k)
        f.addWidget(self.loss)
        self.server_btn = QPushButton("Open console for phone / tablet")
        self.server_btn.setCheckable(True)
        f.addWidget(self.server_btn)
        self.server_url = QLabel("")
        self.server_url.setWordWrap(True)
        self.server_url.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        self.server_url.setStyleSheet("color: #2a9d8f; font-weight: 600;")
        f.addWidget(self.server_url)
        hint = QLabel("Keyboard: arrow keys or W A S D drive the rover in assisted / manual mode.")
        hint.setWordWrap(True)
        hint.setStyleSheet("color: #777;")
        f.addWidget(hint)
        lay.addWidget(g)

        g = QGroupBox("Map layers")
        f = QVBoxLayout(g)
        self.layer_boxes = {}
        for key, label in [("sonar", "Sonar echoes"), ("ir", "IR beams"), ("terrain", "Terrain layer (AI)"),
                           ("frontiers", "Frontiers and target"), ("visited", "Visited cells"), ("true_path", "True path")]:
            cb = QCheckBox(label)
            cb.setChecked(key != "visited")
            self.layer_boxes[key] = cb
            f.addWidget(cb)
        lay.addWidget(g)
        lay.addStretch(1)
        self._env_changed(0)

    def _env_changed(self, _):
        self.env_desc.setText(T.ENV_BLURB[self.env.currentData()].replace("\n\n", " ").replace("\n", " "))

    def layers(self):
        return {k: cb.isChecked() for k, cb in self.layer_boxes.items()}

    def config(self):
        return dict(env=self.env.currentData(), strategy=self.strategy.currentData(),
                    localisation=self.loc.currentData(), ai=self.ai.isChecked(), seed=self.seed.value())


class SensorsTab(QWidget):
    COLS = ["Sensor", "Class (local/scope/mode/signal)", "Reading", "", "Fault", "Health"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mission = None
        lay = QHBoxLayout(self)
        self.table = QTableWidget(0, len(self.COLS))
        self.table.setHorizontalHeaderLabels(self.COLS)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        hdr = self.table.horizontalHeader()
        hdr.setSectionResizeMode(1, QHeaderView.ResizeMode.Stretch)
        self.table.setColumnWidth(0, 90)
        self.table.setColumnWidth(2, 110)
        self.table.setColumnWidth(3, 90)
        self.table.setColumnWidth(4, 90)
        self.table.setColumnWidth(5, 70)
        lay.addWidget(self.table, 1)
        side = QVBoxLayout()
        self.cam_label = QLabel("camera")
        self.cam = QLabel()
        self.cam.setFixedSize(96, 96)
        self.cam.setFrameShape(QFrame.Shape.Box)
        self.cam_pred = QLabel("")
        self.cam_pred.setWordWrap(True)
        self.alarm = QLabel("")
        self.alarm.setStyleSheet("color: #e05252;")
        self.alarm.setWordWrap(True)
        side.addWidget(self.cam_label)
        side.addWidget(self.cam)
        side.addWidget(self.cam_pred)
        side.addWidget(self.alarm)
        side.addStretch(1)
        w = QWidget()
        w.setLayout(side)
        w.setFixedWidth(170)
        lay.addWidget(w)
        self.bars = []

    def set_mission(self, mission):
        self.mission = mission
        sensors = mission.robot.sensors.sensors
        self.table.setRowCount(len(sensors))
        self.bars = []
        for i, s in enumerate(sensors):
            self.table.setItem(i, 0, QTableWidgetItem(s.name))
            self.table.setItem(i, 1, QTableWidgetItem(str(s.cls)))
            self.table.setItem(i, 2, QTableWidgetItem(""))
            bar = QProgressBar()
            bar.setRange(0, 100)
            bar.setTextVisible(False)
            bar.setFixedHeight(12)
            mx = getattr(s, "max_range", None)
            if mx is None or s.cls.signal == "binary":
                bar.setVisible(False)
            self.table.setCellWidget(i, 3, bar)
            self.bars.append(bar)
            combo = QComboBox()
            combo.addItems(FAULT_MODES)
            combo.currentTextChanged.connect(lambda mode, sensor=s: self._set_fault(sensor, mode))
            self.table.setCellWidget(i, 4, combo)
            self.table.setItem(i, 5, QTableWidgetItem("ok"))
            self.table.setRowHeight(i, 24)
        self.alarm.setText("")

    def _set_fault(self, sensor, mode):
        sensor.set_fault(mode)
        if mode == "ok":
            sensor.healthy = True

    def refresh(self):
        m = self.mission
        if m is None:
            return
        for i, s in enumerate(m.robot.sensors.sensors):
            if s.cls.signal == "binary":
                val = "ON" if s.value > 0.5 else "off"
            elif s.name == "camera" and m.ai is not None:
                val = f"{m.ai.last[0]} ({m.ai.last[1]:.0%})"
            else:
                val = f"{s.value:.3f} {s.units}"
            self.table.item(i, 2).setText(val)
            mx = getattr(s, "max_range", None)
            if mx and s.cls.signal != "binary":
                self.bars[i].setValue(int(100 * min(1.0, s.value / mx)))
            h = self.table.item(i, 5)
            if not s.healthy:
                h.setText("FAULTY")
                h.setForeground(QColor(200, 0, 0))
            elif s.fault != "ok":
                h.setText("injected")
                h.setForeground(QColor(200, 120, 0))
            else:
                h.setText("ok")
                h.setForeground(QColor(0, 130, 60))
        cam = m.robot.sensors.camera
        if cam is not None:
            g = (np.clip(cam.image, 0, 1) * 255).astype(np.uint8)
            rgb = np.ascontiguousarray(np.stack([g, g, g], -1))
            self._cam_arr = rgb
            img = QImage(rgb.data, 16, 16, 48, QImage.Format.Format_RGB888)
            self.cam.setPixmap(QPixmap.fromImage(img).scaled(96, 96))
            if m.ai is not None:
                self.cam_pred.setText(f"AI says: {m.ai.last[0]} ({m.ai.last[1]:.0%})\ntruth: {cam.label}")
        if m.ai is not None and m.ai.detector is not None and m.ai.detector.alarms:
            name, verdict = m.ai.detector.alarms[-1]
            self.alarm.setText(f"Fault detector: {name} looks {verdict} - no longer used")


class PlotWidget(QWidget):
    """Rolling plot of desired / measured wheel speed and PWM duty."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hist = deque(maxlen=240)
        self.vmax = 12.0
        self.setMinimumHeight(140)

    def push(self, des, meas, duty):
        self.hist.append((des, meas, duty))
        self.update()

    def clear(self):
        self.hist.clear()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(1, 1, -1, -1)
        pal = self.palette()
        p.fillRect(r, pal.base())
        p.setPen(QPen(pal.mid().color(), 1))
        p.drawRect(r)
        mid = r.center().y()
        p.drawLine(r.left(), mid, r.right(), mid)
        n = len(self.hist)
        if n < 2:
            return
        dx = r.width() / (self.hist.maxlen - 1)

        def series(idx, scale, color, width=1.5):
            p.setPen(QPen(color, width))
            pts = [QPointF(r.left() + i * dx, mid - self.hist[i][idx] / scale * (r.height() / 2 - 4)) for i in range(n)]
            for a, b in zip(pts, pts[1:]):
                p.drawLine(a, b)
        series(0, self.vmax, QColor(230, 120, 0))
        series(1, self.vmax, QColor(30, 150, 70))
        series(2, 1.0, QColor(200, 40, 40), 1.0)
        p.setPen(QColor(230, 120, 0))
        p.drawText(r.left() + 6, r.top() + 14, "desired wheel speed")
        p.setPen(QColor(30, 150, 70))
        p.drawText(r.left() + 140, r.top() + 14, "measured (encoder)")
        p.setPen(QColor(200, 40, 40))
        p.drawText(r.left() + 270, r.top() + 14, "PWM duty")


class MotorTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mission = None
        lay = QHBoxLayout(self)
        form = QFormLayout()
        self.labels = {}
        for key, title in [("behaviour", "Active behaviour"), ("cmd", "Command (v, w)"),
                           ("left", "Left motor"), ("right", "Right motor"), ("slip", "Wheel slip (L / R)"),
                           ("straight", "Straight-drive I term"), ("enc", "Encoder counts (L / R)")]:
            lab = QLabel("-")
            lab.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.labels[key] = lab
            form.addRow(title + ":", lab)
        w = QWidget()
        w.setLayout(form)
        w.setMinimumWidth(380)
        lay.addWidget(w)
        self.plot = PlotWidget()
        lay.addWidget(self.plot, 1)

    def set_mission(self, mission):
        self.mission = mission
        self.plot.vmax = mission.cfg.drive.max_wheel_speed
        self.plot.clear()

    def push_sample(self):
        d = self.mission.robot.drive
        self.plot.push(d.des_wl, d.meas_wl, d.left.duty)

    def refresh(self):
        m = self.mission
        if m is None:
            return
        d = m.robot.drive
        L = self.labels
        L["behaviour"].setText(m.arbiter.active_name)
        L["cmd"].setText(f"v = {m.cmd[0]:+.2f} m/s    w = {m.cmd[1]:+.2f} rad/s")
        L["left"].setText(f"duty {d.left.duty:+.2f}   want {d.des_wl:5.2f}  measured {d.meas_wl:5.2f} rad/s   H-bridge {d.left.bridge.state}")
        L["right"].setText(f"duty {d.right.duty:+.2f}   want {d.des_wr:5.2f}  measured {d.meas_wr:5.2f} rad/s   H-bridge {d.right.bridge.state}")
        L["slip"].setText(f"{d.slip_l:.2f} / {d.slip_r:.2f}")
        L["straight"].setText(f"{d.straight.sum * d.straight.ki:+.3f}")
        L["enc"].setText(f"{d.enc_l.count} / {d.enc_r.count}")


class StatsTab(QWidget):
    ROWS = [("status", "Status"), ("coverage", "Coverage of reachable area"), ("mapped", "Mapped cells"),
            ("path", "Path length"), ("time", "Steps / time"), ("backtracks", "Backtracking events"),
            ("bumps", "Collisions / bumper events"), ("cliff", "Cliff events"), ("loc", "Localisation error (used estimate)"),
            ("odom", "Encoders-only error"), ("battery", "Battery"), ("frontiers", "Frontiers known"), ("ai", "AI terrain accuracy (live)")]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mission = None
        lay = QVBoxLayout(self)
        form = QFormLayout()
        self.labels = {}
        for key, title in self.ROWS:
            lab = QLabel("-")
            self.labels[key] = lab
            form.addRow(title + ":", lab)
        lay.addLayout(form)
        self.bar = QProgressBar()
        self.bar.setRange(0, 1000)
        self.bar.setFormat("coverage %p%")
        lay.addWidget(self.bar)
        lay.addStretch(1)

    def set_mission(self, mission):
        self.mission = mission

    def refresh(self):
        m = self.mission
        if m is None:
            return
        L = self.labels
        cov = m.coverage()
        bat = m.robot.battery
        L["status"].setText(m.status + (f" ({m.stats['return_reason']})" if m.stats["return_reason"] else ""))
        L["coverage"].setText(f"{cov:.1%}")
        L["mapped"].setText(str(m.grid.known_count()))
        L["path"].setText(f"{m.robot.distance:.1f} m")
        L["time"].setText(f"{m.step_count} / {m.time:.0f} s")
        L["backtracks"].setText(str(m.explorer.backtracks))
        L["bumps"].setText(f"{m.robot.collisions} / {m.stats['bumps']}")
        L["cliff"].setText(str(m.stats["cliff_events"]))
        L["loc"].setText(f"{m.estimator.error():.2f} m")
        L["odom"].setText(f"{m.estimator.odom.distance_to(m.robot.pose):.2f} m")
        L["battery"].setText(f"{bat.fraction:.0%}   {bat.voltage:.1f} V   {bat.power:.1f} W")
        L["frontiers"].setText(str(len(m.explorer.frontiers)))
        if m.ai is not None and m.ai.terrain is not None:
            L["ai"].setText(f"{m.ai.terrain_accuracy_live:.1%}  ({m.ai.terrain.predictions} frames)")
        else:
            L["ai"].setText("AI off")
        self.bar.setValue(int(cov * 1000))


LEGEND_HTML = (
    '<span style="color:#d4af00">&#9632;</span> true path &nbsp;&nbsp; '
    '<span style="color:#28aa5a">&#9632;</span> fused estimate &nbsp;&nbsp; '
    '<span style="color:#dc3c3c">&#9632;</span> encoders only &nbsp;&nbsp; '
    '<span style="color:#1e78dc">&#9632;</span> planned path &nbsp;&nbsp; '
    '<span style="color:#f0a000">&#9632;</span> frontiers / target &nbsp;&nbsp; '
    '<span style="color:#e63c3c">&#9632;</span> hazard &nbsp;&nbsp; '
    '<span style="color:#0078ff">&#9632;</span> sonar echo &nbsp;&nbsp; '
    '<span style="color:#e65050">&#9632;</span> IR beam &nbsp;&nbsp; '
    '<span style="color:#3cb464">&#9632;</span>/<span style="color:#dc0000">&#9632;</span> cliff switch'
)


class AboutDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("About")
        self.setMinimumWidth(560)
        lay = QVBoxLayout(self)
        title = QLabel(f"{T.ROVER_NAME} - {T.PROJECT_TITLE}")
        f = QFont(title.font())
        f.setPointSize(13)
        f.setBold(True)
        title.setFont(f)
        lay.addWidget(title)
        sub = QLabel(T.PROJECT_SUB)
        sub.setStyleSheet("color:#555")
        lay.addWidget(sub)
        lay.addSpacing(8)
        desc = QLabel(
            "One exploration robot, three unknown environments (cave, Mars, underwater). The rover is "
            "simulated from the bottom up: DC motors with PWM and an H-bridge, shaft encoders and PID "
            "velocity control, a full on-board sensor suite through a modelled A/D converter, dead "
            "reckoning corrected by gyro and compass, a log-odds occupancy grid, a subsumption behaviour "
            "architecture, frontier / DFS exploration with A* planning, and an AI terrain classifier, "
            "sensor fault detector and utility-based exploration.")
        desc.setWordWrap(True)
        lay.addWidget(desc)
        lay.addSpacing(10)
        course = QLabel(f"<b>{T.COURSE}</b><br>Supervisor: <b>{T.DOCTOR}</b><br>Faculty of Engineering &ndash; Computer and Systems Department")
        lay.addWidget(course)
        lay.addSpacing(6)
        team = QLabel("<b>Team</b><br>" + "<br>".join(f"{i + 1}. {n}" for i, n in enumerate(T.TEAM)))
        lay.addWidget(team)
        lay.addSpacing(6)
        tools = QLabel("Python, NumPy, SciPy, scikit-learn, PySide6, Pygame (legacy interface)")
        tools.setStyleSheet("color:#555")
        lay.addWidget(tools)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        bb.accepted.connect(self.accept)
        lay.addWidget(bb)


GUIDE_HTML = """
<h2>User guide</h2>

<h3>1. Starting a mission</h3>
<p>Use the <b>Mission setup</b> panel on the left:</p>
<ul>
<li><b>Environment</b> &ndash; the unknown world the robot is dropped into. <i>Cave</i>: narrow branching
corridors, dead ends, darkness, mud, pits and gas pockets. <i>Mars surface</i>: open terrain with rock fields,
craters and sandy ground where the wheels slip. <i>Underwater site</i>: reef walls, mud flats and a steady
current; the vehicle uses thrusters, sonar and a Doppler velocity log instead of wheels, light sensors and
encoders. The robot's software is the same in all three; only the configuration and the mounted sensors change.</li>
<li><b>Exploration strategy</b> &ndash; how the robot decides where to go next. <i>Nearest frontier</i> drives to
the closest boundary between mapped and unmapped space. <i>DFS + backtracking</i> walks a lattice of waypoints
depth-first and drives back when it meets a dead end. <i>Utility (AI)</i> scores every frontier by expected
information gain, terrain cost, hazards and battery.</li>
<li><b>Localisation</b> &ndash; which position estimate the robot trusts. <i>Fused</i> combines the gyro,
the compass or sun sensor and the optical-flow / DVL ground-speed sensor. <i>Encoders only</i> is pure dead
reckoning (watch the map tear apart as it drifts). <i>Perfect</i> uses the true position, for comparison only.</li>
<li><b>AI</b> &ndash; enables the camera terrain classifier (feeds the planner's cost map) and the sensor
fault detector. <b>Seed</b> changes the generated map and the sensor noise; the same seed always gives the
same world.</li>
</ul>
<p>Press <b>Start mission</b>. The robot first stands still for 1.5 s (learning the gyro bias), turns a full
circle to fill its map, then explores. It returns to the start point when the map is complete or when the
battery is only just enough to get home.</p>

<h3>2. The two maps</h3>
<p><b>True world</b> (left) is the ground truth the robot never has access to: terrain colours, the robot's
true position (orange), its true path (yellow), the sonar cones (blue, a dot where an echo returns; grey when
nothing is in range), the IR beams (red) and the cliff switches (green dots that turn red over a drop).</p>
<p><b>Robot's map</b> (right) is everything the robot believes: white = free, black = occupied, blue-grey =
unknown, red = hazard (cliff edges), tinted cells = terrain class predicted by the AI. The green robot and
path are the fused estimate, the small red one is where the encoders alone think the robot is, the dashed blue
line is the planned A* path, orange dots are frontiers and the circled one is the current target. The hollow
circle marks the start point.</p>

<h3>3. Bottom panels</h3>
<ul>
<li><b>Sensors</b> &ndash; every mounted sensor with its classification (local/global, internal/external,
active/passive, binary/analog/digital), live reading, a range bar, and a <i>Fault</i> selector. Choose
<i>stuck</i>, <i>dead</i> or <i>noisy</i> to break a sensor while the mission runs and watch what the robot
does; the AI fault detector marks the ranging sensors it has decided to ignore. The camera's latest image and
the classifier's answer are on the right.</li>
<li><b>Motor control</b> &ndash; the control loop of the lecture: PWM duty cycle &rarr; H-bridge &rarr; DC motor
&rarr; shaft encoder &rarr; PID. The plot shows the desired and measured wheel speed of the left wheel and the
duty cycle the PID produces; the labels show both motors, the wheel slip the encoders cannot see and the
straight-driving correction term.</li>
<li><b>Statistics</b> &ndash; coverage of the reachable area, path length, backtracking events, collisions,
cliff events, localisation error of the estimate in use versus encoders-only, battery and the live accuracy
of the terrain classifier.</li>
</ul>

<h3>4. Driving the rover yourself (remote control)</h3>
<p>The <b>Remote control</b> group in the left panel switches who drives:</p>
<ul>
<li><b>Autonomous</b> &ndash; the rover explores and returns by itself (default).</li>
<li><b>Assisted</b> &ndash; you steer with the arrow keys / W A S D, or from a phone or tablet; the safety
layers (bumper escape, cliff stop, slope, obstacle avoidance) keep working and override you when needed.
This is shared control, the way real rovers are driven.</li>
<li><b>Manual</b> &ndash; you drive and nothing stops you, not even a cliff. Useful to show what the safety
layers were doing.</li>
</ul>
<p>Press <b>Open console for phone / tablet</b>: the simulator starts a small web server and shows an address
such as <i>http://192.168.1.4:8080</i>. Open it in the browser of any phone or tablet on the same Wi-Fi.
The console shows a joystick inside a ring of the rover's sonar readings (the ring turns amber and red where
something is close), the camera, the rover's map, link and battery, and buttons for the driving mode,
headlights, return home and stop.</p>
<p>Every command travels over a <b>simulated radio link</b> to a base station at the start point. The signal
weakens with distance and with every wall between the rover and the base (cave: rock, underwater: an acoustic
modem with a 0.4 s delay, Mars: a relay with a 2 s delay). When the link is weak, commands are dropped; when it
is lost for 3 s the rover acts on the <b>Link lost</b> setting: wait, explore alone, or return home. A watchdog
stops the rover one second after the last command, so letting go of the stick (or losing the link) never
leaves it driving blind.</p>

<h3>5. Controls</h3>
<p><b>Space</b> pause / resume &nbsp;&middot;&nbsp; <b>1 2 3 4</b> speed &times;1 &times;4 &times;8 &times;16
&nbsp;&middot;&nbsp; <b>R</b> restart &nbsp;&middot;&nbsp; <b>H</b> headlights. Map layers can be switched
in the left panel or the View menu. The panels are dockable: drag them to rearrange, or hide them from the
View menu.</p>

<h3>6. What to look for in a demonstration</h3>
<ul>
<li>Switch to <i>Assisted</i>, open the console on a tablet, and drive into a wall: the rover refuses.
Switch to <i>Manual</i> and do it again.</li>
<li>Drive deep into the cave in <i>Manual</i> with <i>Link lost: return home</i>: watch the link bars drop,
the commands stop arriving, and the rover come back by itself.</li>
<li>Switch localisation to <i>Encoders only</i> in the cave and watch the red estimate drift and the map
duplicate walls &ndash; then run the same seed with <i>Fused</i>.</li>
<li>On Mars, set the <i>optflow</i> sensor to <i>dead</i>: the fused estimate now relies on the encoders and
slips in the sand.</li>
<li>Set all four <i>cliff</i> sensors to <i>dead</i> near a crater.</li>
<li>Set <i>sonar0</i> to <i>noisy</i> and wait for the fault detector to flag it.</li>
<li>Compare DFS and the utility explorer on the same seed with the Statistics tab open.</li>
</ul>
"""


class GuideDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("User guide")
        self.resize(760, 640)
        lay = QVBoxLayout(self)
        from PySide6.QtWidgets import QTextBrowser
        tb = QTextBrowser()
        tb.setHtml(GUIDE_HTML)
        lay.addWidget(tb)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        bb.accepted.connect(self.accept)
        lay.addWidget(bb)


class ControlsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Controls")
        lay = QVBoxLayout(self)
        txt = QLabel(
            "<b>Mission</b><br>"
            "Space &nbsp;&nbsp; pause / resume<br>"
            "1 / 2 / 3 / 4 &nbsp;&nbsp; simulation speed x1 / x4 / x8 / x16<br>"
            "R &nbsp;&nbsp; restart the same mission<br>"
            "H &nbsp;&nbsp; headlights on / off<br><br>"
            "<b>Sensors</b><br>"
            "In the Sensors tab, use the <i>Fault</i> column to inject a fault into any sensor: "
            "stuck (keeps its last value), dead (reports nothing), noisy. The AI fault detector watches "
            "the ranging sensors and stops using one it judges faulty.<br><br>"
            "<b>Maps</b><br>"
            "Left: the true world the robot never sees. Right: the robot's own map built from its sensors. "
            "Layers can be switched in the View menu or the left panel.")
        txt.setWordWrap(True)
        lay.addWidget(txt)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        bb.accepted.connect(self.accept)
        lay.addWidget(bb)
