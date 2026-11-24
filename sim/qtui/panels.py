"""Side panel (mission setup), bottom tabs (sensors, motor control, statistics, events) and the About dialog."""
from __future__ import annotations

from collections import deque

import numpy as np
from PySide6.QtCore import QEvent, QObject, QPointF, QRectF, QSize, Qt, Signal
from PySide6.QtGui import QColor, QFont, QImage, QIntValidator, QPainter, QPen, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QComboBox, QDialog,
                               QDialogButtonBox, QFormLayout, QFrame, QGridLayout, QHBoxLayout, QHeaderView, QLabel,
                               QLineEdit,
                               QListWidget, QListWidgetItem, QProgressBar, QPushButton, QSizePolicy, QSpinBox,
                               QTableWidget, QTableWidgetItem, QToolButton, QToolTip, QVBoxLayout, QWidget)

from .. import meta as T
from ..sensors.base import FAULT_MODES
from .i18n import LANG, alert_end_text, alert_text, behaviour, tr
from .guide import CONTROLS, GUIDE
from .icons import icon
from .theme_qt import color, restyle


class NoWheel(QObject):
    """Swallow mouse-wheel events on combo boxes and spin boxes, so scrolling
    the panel never changes a setting by accident."""

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Type.Wheel:
            event.ignore()
            return True
        return False


def no_wheel(widget):
    f = NoWheel(widget)
    widget.installEventFilter(f)
    widget.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    return widget


class SeedBox(QLineEdit):
    """A small number field 0..999 (a QSpinBox without arrows draws its text
    one pixel wide under this stylesheet)."""

    def __init__(self, value: int = 1):
        super().__init__(str(value))
        self.setValidator(QIntValidator(0, 999, self))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedWidth(64)
        self.setObjectName("seed")

    def value(self) -> int:
        try:
            return int(self.text())
        except ValueError:
            return 0

    def setValue(self, v: int):
        self.setText(str(int(v)))


def qr_pixmap(text: str, size: int) -> QPixmap | None:
    """The text as a QR code, black on white with a quiet border (phones need
    the white margin to find the code). None when segno is not installed."""
    try:
        import segno
    except ImportError:
        return None
    rows = [list(r) for r in segno.make(text, error="m").matrix]
    n, quiet = len(rows), 2
    cell = max(1, size // (n + 2 * quiet))
    side = cell * (n + 2 * quiet)
    pm = QPixmap(side, side)
    pm.fill(QColor("white"))
    p = QPainter(pm)
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor("black"))
    for y, row in enumerate(rows):
        for x, on in enumerate(row):
            if on:
                p.drawRect((x + quiet) * cell, (y + quiet) * cell, cell, cell)
    p.end()
    return pm


class PadView(QWidget):
    """The controller as the program sees it: the left stick's position and
    the buttons held, live. Pressing something and seeing it move here
    tells you the controller is understood."""
    XBOX = {"a": "A", "b": "B", "x": "X", "y": "Y", "start": "Start", "leftshoulder": "LB", "rightshoulder": "RB", "RT": "RT", "LT": "LT"}
    PS = {"a": "✕", "b": "○", "x": "□", "y": "△", "start": "Start", "leftshoulder": "L1", "rightshoulder": "R1", "RT": "R2", "LT": "L2"}
    NAMES = XBOX

    def __init__(self, parent=None):
        super().__init__(parent)
        self.x = self.y = 0.0
        self.held = set()
        self.setFixedSize(256, 64)

    def set_state(self, x, y, held: str):
        self.x, self.y, self.held = x, y, set(held.split())
        self.update()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        # stick: ring + dot (stick up = up)
        c = QPointF(32, 32)
        p.setPen(QPen(color("line2"), 1.5))
        p.setBrush(color("raised2"))
        p.drawEllipse(c, 28, 28)
        moving = abs(self.x) > 0.01 or abs(self.y) > 0.01
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(color("accent") if moving else color("faint"))
        p.drawEllipse(QPointF(c.x() + self.x * 20, c.y() - self.y * 20), 7, 7)
        # buttons: light up while held
        f = QFont(self.font().family(), 8, QFont.Weight.DemiBold)
        p.setFont(f)
        keys = ["a", "y", "b", "x", "start", "leftshoulder", "rightshoulder", "RT", "LT"]
        for i, k in enumerate(keys):
            col, row = i % 5, i // 5
            r = QRectF(70 + col * 37, 6 + row * 28, 34 if k != "start" else 34, 22)
            on = k in self.held
            p.setPen(QPen(color("accent") if on else color("line2"), 1))
            p.setBrush(color("accent_soft") if on else color("panel"))
            p.drawRoundedRect(r, 6, 6)
            p.setPen(color("accent") if on else color("muted"))
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, self.NAMES[k])


class QrLabel(QLabel):
    """A small QR code; a click opens it big, easy to scan from a distance."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.text_ = ""
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)

    def set_text(self, text: str) -> bool:
        self.text_ = text
        pm = qr_pixmap(text, 132) if text else None
        if pm is None:
            self.clear()
            return False
        self.setPixmap(pm)
        return True

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton and self.text_:
            dlg = QDialog(self.window())
            dlg.setWindowTitle(self.text_)
            lay = QVBoxLayout(dlg)
            big = QLabel()
            big.setPixmap(qr_pixmap(self.text_, 380))
            big.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lay.addWidget(big)
            url = QLabel(self.text_)
            url.setAlignment(Qt.AlignmentFlag.AlignCenter)
            url.setObjectName("mono")
            lay.addWidget(url)
            dlg.exec()
        super().mouseReleaseEvent(event)


ENV_ORDER = ["cave", "mars", "underwater"]
MODES = ["autonomous", "assisted", "manual"]
LAYERS = ["sonar", "ir", "terrain", "frontiers", "visited", "true_path"]


def card(title_key: str | None = None):
    """A rounded card with an optional small title; returns (frame, layout, title label)."""
    f = QFrame()
    f.setObjectName("card")
    lay = QVBoxLayout(f)
    lay.setContentsMargins(12, 10, 12, 12)
    lay.setSpacing(8)
    lab = None
    if title_key:
        lab = QLabel()
        lab.setObjectName("cardTitle")
        lab.setProperty("i18n", title_key)
        lay.addWidget(lab)
    return f, lay, lab


class Segmented(QFrame):
    """A row of exclusive buttons that drives a (hidden) combo box, so the rest
    of the program keeps reading ``combo.currentData()``."""

    def __init__(self, combo: QComboBox, keys: list[str], parent=None):
        super().__init__(parent)
        self.setObjectName("seg")
        self.combo = combo
        lay = QHBoxLayout(self)
        lay.setContentsMargins(3, 3, 3, 3)
        lay.setSpacing(2)
        self.group = QButtonGroup(self)
        self.buttons = {}
        for k in keys:
            b = QPushButton()
            b.setObjectName("segbtn")
            b.setCheckable(True)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            b.setMinimumWidth(0)
            b.clicked.connect(lambda _=False, k=k: self.combo.setCurrentIndex(self.combo.findData(k)))
            self.group.addButton(b)
            lay.addWidget(b)
            self.buttons[k] = b
        combo.currentIndexChanged.connect(self._sync)
        self._sync()

    def _sync(self, *_):
        b = self.buttons.get(self.combo.currentData())
        if b is not None:
            b.setChecked(True)


def env_thumbnail(env: str, w: int = 92, h: int = 52) -> QPixmap:
    """A small picture of the generated world, for the environment cards."""
    try:
        from ..config import get_env
        from ..render import world_rgb
        from ..world import World
        cfg = get_env(env, 1)
        arr = np.ascontiguousarray(world_rgb(World(cfg), max(0.6, cfg.ambient_light))[::-1])
        hh, ww, _ = arr.shape
        img = QImage(arr.data, ww, hh, 3 * ww, QImage.Format.Format_RGB888).copy()
        return QPixmap.fromImage(img).scaled(w, h, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation).copy(0, 0, w, h)
    except Exception:
        pm = QPixmap(w, h)
        pm.fill(QColor(*T.ENV_COLORS[env]))
        return pm


class SetupPanel(QWidget):
    """Left panel: choose environment, strategy, localisation, options; start;
    remote control. The combo boxes are kept (hidden) as the single source of
    truth; the cards and segmented buttons drive them."""
    start_requested = Signal()
    _thumbs: dict = {}

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("sideInner")
        lay = QVBoxLayout(self)
        lay.setContentsMargins(12, 4, 12, 12)
        lay.setSpacing(12)
        self._i18n = []                # (widget, key, kind)

        # ---- environment: three picture cards
        f, fl, t = card("env")
        self._i18n.append((t, "env", "text"))
        self.env = self._hidden_combo(ENV_ORDER)
        row = QHBoxLayout()
        row.setSpacing(6)
        self.env_group = QButtonGroup(self)
        self.env_cards = {}
        for e in ENV_ORDER:
            if e not in SetupPanel._thumbs:
                SetupPanel._thumbs[e] = env_thumbnail(e)
            b = QToolButton()
            b.setObjectName("envcard")
            b.setCheckable(True)
            b.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextUnderIcon)
            b.setIcon(SetupPanel._thumbs[e])
            b.setIconSize(QSize(84, 48))
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setSizePolicy(QSizePolicy.Policy.Ignored, QSizePolicy.Policy.Fixed)
            b.setMinimumWidth(0)
            b.setMinimumHeight(86)
            b.clicked.connect(lambda _=False, e=e: self.env.setCurrentIndex(ENV_ORDER.index(e)))
            self.env_group.addButton(b)
            row.addWidget(b)
            self.env_cards[e] = b
        fl.addLayout(row)
        self.env_desc = QLabel()            # kept for the tooltip text only
        self.env_desc.hide()
        self.env.currentIndexChanged.connect(self._env_changed)
        lay.addWidget(f)

        # ---- strategy and localisation: segmented buttons
        f, fl, t = card("strategy")
        self._i18n.append((t, "strategy", "text"))
        self.strategy = self._hidden_combo([k for k, _ in T.STRATEGIES])
        self.strategy_seg = Segmented(self.strategy, [k for k, _ in T.STRATEGIES])
        fl.addWidget(self.strategy_seg)
        f2l = fl
        f2l.addSpacing(4)
        t2 = QLabel()
        t2.setObjectName("cardTitle")
        self._i18n.append((t2, "loc", "text"))
        f2l.addWidget(t2)
        self.loc = self._hidden_combo([k for k, _ in T.LOCALISATION])
        self.loc_seg = Segmented(self.loc, [k for k, _ in T.LOCALISATION])
        f2l.addWidget(self.loc_seg)
        lay.addWidget(f)

        # ---- options
        f, fl, t = card("options")
        self._i18n.append((t, "options", "text"))
        self.ai = QCheckBox()
        self.ai.setChecked(True)
        fl.addWidget(self.ai)
        row = QHBoxLayout()
        row.setSpacing(10)
        self.seed_label = QLabel()
        self.seed = SeedBox(1)
        self.seed_hint = QLabel()
        self.seed_hint.setObjectName("hint")
        row.addWidget(self.seed_label)
        row.addWidget(self.seed)
        row.addStretch(1)
        self.seed_hint.hide()
        fl.addLayout(row)
        lay.addWidget(f)

        self.start_btn = QPushButton()
        self.start_btn.setObjectName("start")
        self.start_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_btn.setMinimumHeight(42)
        self.start_btn.clicked.connect(self.start_requested.emit)
        lay.addWidget(self.start_btn)

        # ---- remote control
        f, fl, t = card("remote")
        self._i18n.append((t, "remote", "text"))
        self.mode = self._hidden_combo(MODES)
        self.mode_seg = Segmented(self.mode, MODES)
        fl.addWidget(self.mode_seg)
        row = QHBoxLayout()
        self.loss_label = QLabel()
        self.loss_label.setObjectName("hint")
        self.loss = no_wheel(QComboBox())
        for k in ("home", "explore", "hold"):
            self.loss.addItem(k, k)
        row.addWidget(self.loss_label)
        row.addWidget(self.loss, 1)
        fl.addLayout(row)
        self.server_btn = QPushButton()
        self.server_btn.setCheckable(True)
        self.server_btn.setObjectName("secondary")
        self.server_btn.setMinimumHeight(36)
        self.server_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        fl.addWidget(self.server_btn)
        self.server_msg = QLabel("")
        self.server_msg.setWordWrap(True)
        self.server_msg.setObjectName("hint")
        self.server_msg.setVisible(False)
        fl.addWidget(self.server_msg)
        url_row = QHBoxLayout()
        url_row.setContentsMargins(0, 0, 0, 0)
        url_row.setSpacing(6)
        self.server_link = QLabel("")
        self.server_link.setOpenExternalLinks(True)          # click: opens the console in this computer's browser
        self.server_link.setTextInteractionFlags(Qt.TextInteractionFlag.TextBrowserInteraction)
        self.server_link.setLayoutDirection(Qt.LayoutDirection.LeftToRight)
        url_row.addWidget(self.server_link, 1)
        self.copy_btn = QToolButton()
        self.copy_btn.setObjectName("iconbtn")
        self.copy_btn.setAutoRaise(True)
        self.copy_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.copy_btn.clicked.connect(self._copy_url)
        url_row.addWidget(self.copy_btn, 0)
        fl.addLayout(url_row)
        self.qr = QrLabel()                      # scan it with the phone instead of typing the address
        self.qr.hide()
        fl.addWidget(self.qr, 0, Qt.AlignmentFlag.AlignHCenter)
        self._console_url = ""
        self._console_err = None
        self.keys_hint = QLabel()
        self.keys_hint.setWordWrap(True)
        self.keys_hint.setObjectName("hint")
        self.keys_hint.hide()              # said in the mode buttons' tooltips instead
        # game controller status
        self.pad_row = QFrame()
        self.pad_row.setObjectName("pad")
        pr = QHBoxLayout(self.pad_row)
        pr.setContentsMargins(10, 6, 10, 6)
        pr.setSpacing(8)
        self.pad_icon = QLabel()
        self.pad_text = QLabel()
        self.pad_text.setWordWrap(True)
        self.pad_text.setObjectName("hint")
        pv = QVBoxLayout()
        pv.setSpacing(6)
        top = QHBoxLayout()
        top.addWidget(self.pad_icon)
        top.addWidget(self.pad_text, 1)
        pv.addLayout(top)
        self.pad_view = PadView()
        self.pad_view.hide()
        pv.addWidget(self.pad_view, 0, Qt.AlignmentFlag.AlignHCenter)
        self.pad_map = QLabel()                  # what each control does, only while a controller is there
        self.pad_map.setWordWrap(True)
        self.pad_map.setObjectName("hint")
        self.pad_map.hide()
        pv.addWidget(self.pad_map)
        pr.addLayout(pv, 1)
        fl.addWidget(self.pad_row)
        self._pad = (False, "")             # (available, connected name)
        lay.addWidget(f)
        lay.addStretch(1)

        # ---- map layer chips: created here (``layers()`` reads them), shown above the maps
        self.layer_boxes = {}
        for key in LAYERS:
            b = QPushButton()
            b.setObjectName("chip")
            b.setCheckable(True)
            b.setChecked(key != "visited")
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            self.layer_boxes[key] = b

        LANG.changed.connect(self.retranslate)
        self.retranslate()
        self._env_changed(0)
        self.show_console_url(None)

    def _hidden_combo(self, keys):
        c = no_wheel(QComboBox(self))
        for k in keys:
            c.addItem(k, k)
        c.hide()
        return c

    # ---------------------------------------------------------------- text
    def retranslate(self, *_):
        for w, key, _kind in self._i18n:
            w.setText(tr(key))
        for e, b in self.env_cards.items():
            b.setText(tr(e))
        for i, e in enumerate(ENV_ORDER):
            self.env.setItemText(i, tr(e))
        for k, b in self.strategy_seg.buttons.items():
            b.setText(tr(k))
        for k, b in self.loc_seg.buttons.items():
            b.setText(tr(k))
            b.setToolTip(tr(k + "S"))
        for k, b in self.mode_seg.buttons.items():
            b.setText(tr(k))
            b.setToolTip(tr(k + "Tip") + ("" if k == "autonomous" else "\n" + tr("keys")))
        for e, b in self.env_cards.items():
            b.setToolTip(tr("envBlurb_" + e))
        for i, k in enumerate(("lossHome", "lossExplore", "lossHold")):
            self.loss.setItemText(i, tr(k))
        self.loss_label.setText(tr("lossL"))
        self.ai.setText(tr("ai"))
        self.seed_label.setText(tr("seed"))
        self.seed_hint.setText(tr("seedHint"))
        self.seed.setToolTip(tr("seedHint"))
        self.start_btn.setText(tr("start"))
        self.server_btn.setText(tr("closeConsole") if self.server_btn.isChecked() else tr("openConsole"))
        self.copy_btn.setToolTip(tr("copy"))
        self.keys_hint.setText(tr("keys"))
        for key, b in self.layer_boxes.items():
            b.setText(tr(key))
        self._env_changed(0)
        self.show_console_url(self._console_url or None, self._console_err)
        self.set_pad(*self._pad)
        self.recolor()

    def recolor(self):
        self.copy_btn.setIcon(icon("copy", color("muted")))
        self.pad_icon.setPixmap(icon("gamepad", color("accent" if self._pad[1] else "muted"), 18).pixmap(18, 18))

    def set_pad(self, available: bool, name: str = ""):
        self._pad = (available, name)
        if not available:
            self.pad_text.setText(tr("padMissing"))
        else:
            self.pad_text.setText(tr("padOn", name) if name else tr("padOff"))
        self.pad_row.setToolTip("" if name or not available else tr("padHow"))
        self.pad_view.setVisible(bool(name))
        self.pad_map.setVisible(bool(name))
        from .gamepad import is_playstation
        ps = is_playstation(name)
        self.pad_view.NAMES = PadView.PS if ps else PadView.XBOX
        self.pad_view.update()
        self.pad_map.setText(tr("padMapPs" if ps else "padMap"))
        self.pad_row.setProperty("on", "true" if name else "false")
        restyle(self.pad_row)
        self.pad_icon.setPixmap(icon("gamepad", color("accent" if name else "muted"), 18).pixmap(18, 18))

    def _env_changed(self, _):
        e = self.env.currentData()
        self.env_desc.setText(tr("envBlurb_" + e))
        if e in self.env_cards:
            self.env_cards[e].setChecked(True)

    def layers(self):
        return {k: cb.isChecked() for k, cb in self.layer_boxes.items()}

    def config(self):
        return dict(env=self.env.currentData(), strategy=self.strategy.currentData(),
                    localisation=self.loc.currentData(), ai=self.ai.isChecked(), seed=self.seed.value())

    def show_console_url(self, url: str | None, error: str | None = None):
        """Show the console address as a clickable link with a copy button,
        an error message, or nothing."""
        self._console_url = url or ""
        self._console_err = error
        acc = color("accent").name()
        if url:
            self.server_msg.setText("")
            self.server_link.setToolTip(tr("openOn"))
            self.server_link.setText(f'<a href="{url}" style="color:{acc};font-weight:600;text-decoration:none">{url}</a>')
        elif error:
            self.server_msg.setText(tr("consoleErr", error))
            self.server_link.setText("")
        else:
            self.server_msg.setText("")
            self.server_link.setText("")
        self.server_msg.setVisible(bool(error))
        self.server_link.setVisible(bool(url))
        self.copy_btn.setVisible(bool(url))
        self.qr.setVisible(bool(url) and self.qr.set_text(url or ""))
        self.qr.setToolTip(tr("qrTip"))

    def _copy_url(self):
        if self._console_url:
            QApplication.clipboard().setText(self._console_url)
            QToolTip.showText(self.copy_btn.mapToGlobal(self.copy_btn.rect().bottomLeft()), tr("copied"), self.copy_btn, self.copy_btn.rect(), 1500)


def centred(text=""):
    it = QTableWidgetItem(text)
    it.setTextAlignment(Qt.AlignmentFlag.AlignCenter)
    return it


class SensorsTab(QWidget):
    """Every sensor: type, live reading with a range bar, fault buttons, health.
    Every column but the last can be resized by dragging its edge in the
    header (double-click the edge: back to the default), never below a
    minimum that keeps its content readable. Health is the last column, so
    it has no edge to drag. When the window grows, the reading column takes
    the spare room. Everything is centred."""
    COL_W = [110, 170, 260, 280, 110]         # default widths
    COL_MIN = [90, 130, 190, 250, 100]        # below this the content would be cut
    READ, LAST = 2, 4

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mission = None
        lay = QHBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        self.table = QTableWidget(0, 5)
        self.table.verticalHeader().setVisible(False)
        self.table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.table.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.table.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.table.setShowGrid(False)
        self.table.setHorizontalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        self.table.setVerticalScrollMode(QAbstractItemView.ScrollMode.ScrollPerPixel)
        hdr = self.table.horizontalHeader()
        hdr.setDefaultAlignment(Qt.AlignmentFlag.AlignCenter)
        hdr.setMinimumSectionSize(min(self.COL_MIN))
        hdr.setHighlightSections(False)
        hdr.setStretchLastSection(False)
        for i, w in enumerate(self.COL_W):
            hdr.setSectionResizeMode(i, QHeaderView.ResizeMode.Fixed if i == self.LAST else QHeaderView.ResizeMode.Interactive)
            self.table.setColumnWidth(i, w)
        self._fitting = False
        self._extra = 0                           # width the reading column got from _fill, not from you
        hdr.sectionResized.connect(self._on_resized)
        hdr.sectionHandleDoubleClicked.connect(self._reset_column)
        self.table.viewport().installEventFilter(self)
        lay.addWidget(self.table, 1)
        side = QVBoxLayout()
        side.setContentsMargins(12, 10, 12, 10)
        self.cam_label = QLabel()
        self.cam_label.setObjectName("cardTitle")
        self.cam = QLabel()
        self.cam.setFixedSize(112, 112)
        self.cam.setStyleSheet("border-radius: 8px;")
        self.cam_pred = QLabel("")
        self.cam_pred.setWordWrap(True)
        self.cam_pred.setObjectName("hint")
        self.alarm = QLabel("")
        self.alarm.setWordWrap(True)
        side.addWidget(self.cam_label)
        side.addWidget(self.cam)
        side.addWidget(self.cam_pred)
        side.addWidget(self.alarm)
        side.addStretch(1)
        w = QWidget()
        w.setLayout(side)
        w.setFixedWidth(180)
        lay.addWidget(w)
        self.bars, self.readings, self.health = [], [], []
        LANG.changed.connect(self.retranslate)
        self.retranslate()

    # ------------------------------------------------------------ column widths
    def _on_resized(self, i, old, new):
        if self._fitting:
            return
        if i == self.READ:
            self._extra = 0                       # you sized it yourself: that is its width now
        if new < self.COL_MIN[i]:                 # never narrower than its content needs
            self._set_width(i, self.COL_MIN[i])

    def _set_width(self, i, w):
        self._fitting = True
        self.table.setColumnWidth(i, w)
        self._fitting = False

    def _reset_column(self, i):
        self._set_width(i, self.COL_W[i])
        self._fill()

    def _fill(self):
        """When the window changes size: if the columns don't reach the edge,
        widen the reading column to close the gap; if they overflow, first
        give back what was added that way. Your own column sizes are kept."""
        avail = self.table.viewport().width()
        if avail <= 0:
            return
        gap = avail - sum(self.table.columnWidth(i) for i in range(5))
        w = self.table.columnWidth(self.READ)
        if gap > 0:
            self._set_width(self.READ, w + gap)
            self._extra += gap
        elif gap < 0 and self._extra > 0:
            take = min(self._extra, -gap, w - self.COL_MIN[self.READ])
            if take > 0:
                self._set_width(self.READ, w - take)
                self._extra -= take

    def eventFilter(self, obj, event):
        if obj is self.table.viewport() and event.type() == QEvent.Type.Resize:
            self._fill()
        return False

    def retranslate(self, *_):
        self.table.setHorizontalHeaderLabels([tr(k) for k in ("thSensor", "thClass", "thReading", "thFault", "thHealth")])
        self.cam_label.setText(tr("camera"))
        if self.mission is not None:
            self.set_mission(self.mission)

    def set_mission(self, mission):
        self.mission = mission
        sensors = mission.robot.sensors.sensors
        # drop the old row widgets now (not later): after a language switch they would
        # otherwise linger, mirrored, until the next event-loop turn
        for r in range(self.table.rowCount()):
            for c in range(self.table.columnCount()):
                w = self.table.cellWidget(r, c)
                if w is not None:
                    self.table.removeCellWidget(r, c)
                    w.hide()
        self.table.setRowCount(len(sensors))
        self.bars, self.readings, self.health = [], [], []
        for i, s in enumerate(sensors):
            self.table.setItem(i, 0, centred(s.name))
            it = centred(" · ".join(tr("c_" + w) for w in (s.cls.mode, s.cls.signal)))
            it.setToolTip(" / ".join(tr("c_" + w) for w in (s.cls.locality, s.cls.scope, s.cls.mode, s.cls.signal)))
            self.table.setItem(i, 1, it)
            # reading: the number and its range bar in one cell
            holder = QWidget()
            holder.setObjectName("cell")
            holder.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            hl = QHBoxLayout(holder)
            hl.setContentsMargins(12, 0, 12, 0)
            hl.setSpacing(10)
            val = QLabel("-")
            val.setObjectName("reading")
            val.setAlignment(Qt.AlignmentFlag.AlignCenter)
            val.setMinimumWidth(96)
            bar = QProgressBar()
            bar.setRange(0, 1000)
            bar.setTextVisible(False)
            mx = getattr(s, "max_range", None)
            if mx is None or s.cls.signal == "binary":
                bar.setVisible(False)
                hl.addStretch(1)
                hl.addWidget(val)
                hl.addStretch(1)
            else:
                hl.addWidget(val)
                hl.addWidget(bar, 1)
            self.table.setCellWidget(i, 2, holder)
            self.bars.append(bar)
            self.readings.append(val)
            self.table.setCellWidget(i, 3, self._fault_buttons(s))
            h = QLabel()
            h.setObjectName("health")
            h.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
            h.setAlignment(Qt.AlignmentFlag.AlignCenter)
            self.table.setCellWidget(i, 4, h)
            self.health.append(h)
            self.table.setItem(i, 4, centred(""))
            self.table.setRowHeight(i, 32)
        self.alarm.setText("")
        self.refresh()

    def _fault_buttons(self, sensor):
        """Four small exclusive buttons in the cell: one tap injects the fault."""
        outer = QWidget()
        outer.setObjectName("cell")
        outer.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        ol = QHBoxLayout(outer)
        ol.setContentsMargins(4, 3, 4, 3)
        w = QFrame()
        w.setObjectName("faults")
        lay = QHBoxLayout(w)
        lay.setContentsMargins(2, 2, 2, 2)
        lay.setSpacing(1)
        group = QButtonGroup(w)
        group.setExclusive(True)
        for mode in FAULT_MODES:
            b = QPushButton(tr(mode))
            b.setCheckable(True)
            b.setChecked(mode == sensor.fault)
            b.setObjectName("faultbtn")
            b.setProperty("broken", "true" if mode != "ok" else "false")
            b.setProperty("mode", mode)
            b.setFixedHeight(22)
            b.setCursor(Qt.CursorShape.PointingHandCursor)
            b.setToolTip(tr({"ok": "fOkTip", "stuck": "fStuckTip", "dead": "fDeadTip", "noisy": "fNoisyTip"}[mode]))
            b.clicked.connect(lambda checked, sensor=sensor, mode=mode: self._set_fault(sensor, mode))
            group.addButton(b)
            lay.addWidget(b)
        ol.addStretch(1)
        ol.addWidget(w)
        ol.addStretch(1)
        return outer

    def _set_fault(self, sensor, mode):
        sensor.set_fault(mode)
        if mode == "ok":
            sensor.healthy = True

    def refresh(self):
        m = self.mission
        if m is None:
            return
        for i, s in enumerate(m.robot.sensors.sensors):
            if i >= len(self.readings):
                break
            if s.cls.signal == "binary":
                val = "ON" if s.value > 0.5 else "off"
            elif s.name == "camera" and m.ai is not None:
                val = f"{m.ai.last[0]} ({m.ai.last[1]:.0%})"
            else:
                val = f"{s.value:.3f} {s.units}"
            self.readings[i].setText(val)
            mx = getattr(s, "max_range", None)
            if mx and s.cls.signal != "binary":
                self.bars[i].setValue(int(1000 * max(0.0, min(1.0, s.value / mx))))
            h = self.health[i]
            if not s.healthy:
                txt, sev = tr("hFaulty"), "bad"
            elif s.fault != "ok":
                txt, sev = tr("hInjected"), "warn"
            else:
                txt, sev = tr("hOk"), "good"
            if h.text() != txt:
                h.setText(txt)
                h.setProperty("sev", sev)
                restyle(h)
        cam = m.robot.sensors.camera
        if cam is not None:
            g = (np.clip(cam.image, 0, 1) * 255).astype(np.uint8)
            rgb = np.ascontiguousarray(np.stack([g, g, g], -1))
            self._cam_arr = rgb
            img = QImage(rgb.data, 16, 16, 48, QImage.Format.Format_RGB888)
            self.cam.setPixmap(QPixmap.fromImage(img).scaled(112, 112))
            if m.ai is not None:
                self.cam_pred.setText(tr("aiSays", tr("g_" + m.ai.last[0]), m.ai.last[1]) + "\n" + tr("truth", tr("g_" + cam.label)))
        if m.ai is not None and m.ai.detector is not None:
            # the latest verdict on a sensor the detector still distrusts: a brief false
            # alarm that cleared again must not stay on screen
            distrusted = {s.name for s in m.robot.sensors.sensors if not s.healthy}
            last = next(((n, v) for n, v in reversed(m.ai.detector.alarms) if n in distrusted), None)
            txt = tr("faultMsg", last[0], tr(last[1]) if last[1] in FAULT_MODES else last[1]) if last else ""
            if self.alarm.text() != txt:
                self.alarm.setText(txt)
                self.alarm.setStyleSheet(f"color: {color('bad').name()};")


class PlotWidget(QWidget):
    """Rolling plot of desired / measured wheel speed and PWM duty."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.hist = deque(maxlen=240)
        self.vmax = 12.0
        self.setMinimumHeight(140)

    def push(self, des, meas, duty):
        self.hist.append((des, meas, duty))

    def clear(self):
        self.hist.clear()

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        r = self.rect().adjusted(8, 8, -8, -8)
        p.setPen(QPen(color("line"), 1))
        p.setBrush(color("raised"))
        p.drawRoundedRect(r, 10, 10)
        mid = r.center().y()
        p.drawLine(r.left() + 8, mid, r.right() - 8, mid)
        cols = (QColor(245, 165, 36), QColor(45, 212, 191), QColor(248, 113, 113))
        keys = ("m_want", "m_meas", "m_duty")
        x = r.left() + 12
        p.setFont(QFont(self.font().family(), 8))
        for c, k in zip(cols, keys):
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(c)
            p.drawRoundedRect(QRectF(x, r.top() + 10, 10, 4), 2, 2)
            p.setPen(color("muted"))
            txt = tr(k)
            p.drawText(QPointF(x + 14, r.top() + 16), txt)
            x += 26 + p.fontMetrics().horizontalAdvance(txt)
        n = len(self.hist)
        if n < 2:
            return
        dx = (r.width() - 16) / (self.hist.maxlen - 1)
        h2 = r.height() / 2 - 14

        def series(idx, scale, c, width=1.6):
            p.setPen(QPen(c, width))
            pts = [QPointF(r.left() + 8 + i * dx, mid - self.hist[i][idx] / scale * h2) for i in range(n)]
            p.drawPolyline(pts)
        series(0, self.vmax, cols[0])
        series(1, self.vmax, cols[1])
        series(2, 1.0, cols[2], 1.0)


class MotorTab(QWidget):
    KEYS = ["behaviour", "cmd", "left", "right", "slip", "straight", "enc"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mission = None
        lay = QHBoxLayout(self)
        lay.setContentsMargins(12, 6, 6, 6)
        form = QFormLayout()
        form.setVerticalSpacing(6)
        self.labels, self.titles = {}, {}
        for key in self.KEYS:
            lab = QLabel("-")
            lab.setObjectName("mono")
            lab.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
            self.labels[key] = lab
            self.titles[key] = QLabel()
            self.titles[key].setObjectName("hint")
            form.addRow(self.titles[key], lab)
        w = QWidget()
        w.setLayout(form)
        w.setMinimumWidth(420)
        lay.addWidget(w)
        self.plot = PlotWidget()
        lay.addWidget(self.plot, 1)
        LANG.changed.connect(self.retranslate)
        self.retranslate()

    def retranslate(self, *_):
        for k, lab in self.titles.items():
            lab.setText(tr("m_" + k))
        self.plot.update()
        self.refresh()

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
        L["behaviour"].setText(behaviour(m.arbiter.active_name))
        L["cmd"].setText(f"v = {m.cmd[0]:+.2f} m/s    w = {m.cmd[1]:+.2f} rad/s")
        L["left"].setText(f"duty {d.left.duty:+.2f}   want {d.des_wl:5.2f}  meas {d.meas_wl:5.2f} rad/s   {d.left.bridge.state}")
        L["right"].setText(f"duty {d.right.duty:+.2f}   want {d.des_wr:5.2f}  meas {d.meas_wr:5.2f} rad/s   {d.right.bridge.state}")
        L["slip"].setText(f"{d.slip_l:.2f} / {d.slip_r:.2f}")
        L["straight"].setText(f"{d.straight.sum * d.straight.ki:+.3f}")
        L["enc"].setText(f"{d.enc_l.count} / {d.enc_r.count}")
        self.plot.update()


class StatsTab(QWidget):
    """The mission's numbers as a grid of small cards."""
    KEYS = ["status", "coverage", "mapped", "path", "time", "backtracks", "bumps", "cliff", "loc", "odom",
            "battery", "frontiers", "ai"]

    def __init__(self, parent=None):
        super().__init__(parent)
        self.mission = None
        grid = QGridLayout(self)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setSpacing(8)
        self.labels, self.titles = {}, {}
        for i, key in enumerate(self.KEYS):
            f = QFrame()
            f.setObjectName("card")
            v = QVBoxLayout(f)
            v.setContentsMargins(12, 6, 12, 8)
            v.setSpacing(2)
            t = QLabel()
            t.setObjectName("kpiLabel")
            lab = QLabel("-")
            lab.setObjectName("mono")
            v.addWidget(t)
            v.addWidget(lab)
            self.titles[key], self.labels[key] = t, lab
            grid.addWidget(f, i // 5, i % 5)
        grid.setRowStretch(3, 1)
        LANG.changed.connect(self.retranslate)
        self.retranslate()

    def retranslate(self, *_):
        for k, lab in self.titles.items():
            lab.setText(tr("s_" + k))
        self.refresh()

    def set_mission(self, mission):
        self.mission = mission

    def refresh(self):
        m = self.mission
        if m is None:
            return
        L = self.labels
        cov = m.coverage()
        bat = m.robot.battery
        st = tr("st_" + m.status)
        if m.stats["return_reason"] and ("why_" + m.stats["return_reason"]) in __import__("sim.qtui.i18n", fromlist=["STR"]).STR["en"]:
            st += " (" + tr("why_" + m.stats["return_reason"]) + ")"
        L["status"].setText(st)
        L["coverage"].setText(f"{cov:.1%}")
        L["mapped"].setText(str(m.grid.known_count()))
        L["path"].setText(f"{m.robot.distance:.1f} m")
        L["time"].setText(f"{m.step_count} / {m.time:.0f} s")
        L["backtracks"].setText(str(m.explorer.backtracks))
        L["bumps"].setText(f"{m.robot.collisions} / {m.stats['bumps']}")
        L["cliff"].setText(str(m.stats["cliff_events"]))
        L["loc"].setText(f"{m.estimator.error():.2f} m")
        L["odom"].setText(f"{m.estimator.odom.distance_to(m.robot.pose):.2f} m")
        L["battery"].setText(f"{bat.fraction:.0%}  {bat.voltage:.1f} V  {bat.power:.1f} W")
        L["frontiers"].setText(str(len(m.explorer.frontiers)))
        if m.ai is not None and m.ai.terrain is not None:
            L["ai"].setText(f"{m.ai.terrain_accuracy_live:.1%}  · " + tr("s_frames", m.ai.terrain.predictions))
        else:
            L["ai"].setText(tr("s_aiOff"))


class EventsTab(QWidget):
    """What started and what ended, newest first (from the alert tracker)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        self.list = QListWidget()
        self.list.setObjectName("events")
        self.list.setSelectionMode(QAbstractItemView.SelectionMode.NoSelection)
        self.list.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        lay.addWidget(self.list)
        self._shown = None

    def show_log(self, log, force=False):
        key = (len(log), id(log[0]) if log else 0)
        if key == self._shown and not force:
            return
        self._shown = key
        self.list.clear()
        if not log:
            it = QListWidgetItem(tr("evEmpty"))
            it.setForeground(color("muted"))
            self.list.addItem(it)
            return
        for e in log:
            mm, ss = divmod(int(e.t), 60)
            text = alert_end_text(e.alert) if e.ended else alert_text(e.alert)
            it = QListWidgetItem(f"{mm:02d}:{ss:02d}    {text}")
            sev = "good" if e.ended else e.alert.sev
            it.setIcon(icon("dot", color({"bad": "bad", "warn": "warn", "info": "muted", "good": "good"}[sev]), 12))
            if e.ended:
                it.setForeground(color("muted"))
            self.list.addItem(it)


def legend_html() -> str:
    cols = ["#d4af00", "#28aa5a", "#dc3c3c", "#1e78dc", "#f0a000", "#e63c3c", "#0078ff", "#e65050", "#3cb464"]
    return " &nbsp;&nbsp; ".join(f'<span style="color:{c}">&#9632;</span> {t}' for c, t in zip(cols, tr("legend")))


LEGEND_HTML = legend_html  # kept for old imports: call it for the current language


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
        sub.setObjectName("hint")
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
        tools = QLabel("Python, NumPy, SciPy, scikit-learn, PySide6, pygame-ce (game controller)")
        tools.setObjectName("hint")
        lay.addWidget(tools)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        bb.accepted.connect(self.accept)
        lay.addWidget(bb)


GUIDE_HTML = GUIDE["en"]   # kept for old imports


class GuideDialog(QDialog):
    """Help > User guide (F1), in the interface language."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("guide").replace("&", ""))
        self.resize(780, 680)
        lay = QVBoxLayout(self)
        from PySide6.QtWidgets import QTextBrowser
        tb = QTextBrowser()
        tb.setOpenExternalLinks(True)
        tb.setHtml(GUIDE.get(LANG.code, GUIDE["en"]))
        lay.addWidget(tb)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        bb.rejected.connect(self.reject)
        bb.accepted.connect(self.accept)
        lay.addWidget(bb)


class ControlsDialog(QDialog):
    """Help > Controls: every shortcut, the keyboard and the game controller."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(tr("controls").replace("&", ""))
        self.setMinimumWidth(560)
        lay = QVBoxLayout(self)
        txt = QLabel(CONTROLS.get(LANG.code, CONTROLS["en"]))
        txt.setWordWrap(True)
        lay.addWidget(txt)
        bb = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok)
        bb.accepted.connect(self.accept)
        lay.addWidget(bb)
