"""Light / dark palettes for the Qt interface and the application icon."""
from __future__ import annotations

import os

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QImage, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import QApplication

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")
ICON_PNG = os.path.join(ASSETS, "icon.png")
ICON_ICO = os.path.join(ASSETS, "icon.ico")

FONTS_DIR = os.path.join(ASSETS, "fonts")
# the same type as the web designs: Inter for Latin text, IBM Plex Sans Arabic for
# Arabic, Chakra Petch for live numbers. Bundled under assets/fonts (SIL Open Font
# Licence); without them the system fonts are used.
UI = '"Inter", "IBM Plex Sans Arabic", "Segoe UI Variable Text", "Segoe UI", sans-serif'
MONO = '"Chakra Petch", "Bahnschrift", "Cascadia Mono", Consolas, monospace'
_fonts_loaded = False


def load_fonts():
    global _fonts_loaded
    if _fonts_loaded or not os.path.isdir(FONTS_DIR):
        return
    from PySide6.QtGui import QFontDatabase
    for name in sorted(os.listdir(FONTS_DIR)):
        if name.lower().endswith((".ttf", ".otf")):
            QFontDatabase.addApplicationFont(os.path.join(FONTS_DIR, name))
    _fonts_loaded = True

QSS = """
* {{ font-family: {ui}; font-size: 10pt; }}
QMainWindow, QDialog {{ background: {bg}; }}
QWidget {{ color: {text}; }}
QMenuBar {{ background: {panel}; padding: 2px 8px; border-bottom: 1px solid {line}; }}
QMenuBar::item {{ padding: 5px 10px; border-radius: 6px; color: {muted}; }}
QMenuBar::item:selected {{ background: {raised}; color: {text}; }}
QMenu {{ background: {panel}; border: 1px solid {line}; border-radius: 10px; padding: 6px; }}
QMenu::item {{ padding: 6px 26px 6px 12px; border-radius: 6px; }}
QMenu::item:selected {{ background: {raised2}; }}
QMenu::separator {{ height: 1px; background: {line}; margin: 6px 4px; }}
QToolBar#appbarTb {{ background: {panel}; border: none; border-bottom: 1px solid {line}; padding: 0; spacing: 0; }}
QWidget#appbar {{ background: {panel}; }}
QLabel#brand {{ font-family: {mono}; font-size: 13pt; font-weight: 700; }}
QFrame#mchip {{ background: {raised}; border: 1px solid {line}; border-radius: 10px; }}
QFrame#sep {{ background: {line2}; border: none; }}
QLabel#mono {{ font-family: {mono}; font-weight: 600; }}
QLabel#pill {{ border-radius: 10px; padding: 2px 10px; font-weight: 600; font-size: 9pt; background: {accent_soft}; color: {accent}; }}
QLabel#pill[sev="warn"] {{ background: {warn_soft}; color: {warn}; }}
QLabel#pill[sev="bad"] {{ background: {bad_soft}; color: {bad}; }}
QLabel#pill[sev="info"], QLabel#pill[sev="idle"] {{ background: {raised2}; color: {muted}; }}
QFrame#grp {{ background: {raised}; border: 1px solid {line}; border-radius: 10px; }}
QPushButton#tb {{ background: transparent; border: none; border-radius: 7px; padding: 5px 11px; color: {text}; }}
QPushButton#tb:hover {{ background: {raised2}; }}
QPushButton#tb:checked {{ background: {panel}; color: {accent}; font-weight: 600; }}
QPushButton#tb:disabled {{ color: {faint}; }}
QPushButton#tb[danger="true"] {{ color: {bad}; }}
QPushButton#tb[danger="true"]:disabled {{ color: {faint}; }}
QLineEdit#seed {{ font-family: {mono}; font-weight: 600; padding: 4px 6px; }}
QPushButton#tbx {{ background: {raised}; border: 1px solid {line}; border-radius: 9px; padding: 6px 12px; }}
QPushButton#tbx:hover {{ border-color: {line2}; background: {raised2}; }}
QPushButton#tbx:checked {{ background: {accent_soft}; color: {accent}; border-color: {accent}; }}
QPushButton#primary {{ background: {accent}; color: {on_accent}; border: 1px solid {accent}; border-radius: 9px; padding: 6px 14px; font-weight: 600; }}
QPushButton#primary:hover {{ background: {accent_hover}; }}
QPushButton#tbx:disabled, QPushButton#primary:disabled {{ color: {faint}; background: {raised}; border-color: {line}; }}
QComboBox:disabled {{ color: {faint}; }}
QToolButton#iconbtn {{ background: transparent; border: 1px solid transparent; border-radius: 8px; padding: 4px; }}
QToolButton#iconbtn:hover {{ background: {raised2}; border-color: {line}; }}
QStatusBar {{ background: {panel}; border-top: 1px solid {line}; min-height: 32px; }}
QStatusBar::item {{ border: none; }}
QStatusBar QLabel {{ color: {muted}; padding: 0 8px; }}
QPushButton#alert {{ border-radius: 8px; padding: 3px 10px; border: 1px solid {line}; background: {raised}; color: {muted}; font-weight: 500; }}
QPushButton#alert[sev="good"] {{ color: {good}; border-color: {good_line}; background: {good_soft}; }}
QPushButton#alert[sev="warn"] {{ color: {warn}; border-color: {warn}; background: {warn_soft}; }}
QPushButton#alert[sev="bad"] {{ color: {bad}; border-color: {bad}; background: {bad_soft}; }}
QPushButton#alertAct {{ border-radius: 6px; padding: 2px 10px; border: none; background: {accent}; color: {on_accent}; font-weight: 600; }}
QLabel#more {{ background: {raised2}; color: {text}; border-radius: 6px; padding: 1px 6px; font-family: {mono}; font-size: 8pt; }}
QDockWidget {{ background: {panel}; }}
QWidget#side, QWidget#sideStrip, QWidget#sideInner {{ background: {panel}; }}
QLabel#sideTitle {{ font-size: 11pt; font-weight: 600; }}
QLabel#cardTitle {{ color: {muted}; font-weight: 600; font-size: 9pt; }}
QLabel#hint, QLabel#muted {{ color: {muted}; }}
QFrame#card {{ background: {raised}; border: 1px solid {line}; border-radius: 12px; }}
QFrame#kpi {{ background: {panel}; border: 1px solid {line}; border-radius: 12px; }}
QLabel#kpiLabel {{ color: {muted}; font-size: 9pt; }}
QLabel#kpiValue {{ font-family: {mono}; font-size: 15pt; font-weight: 600; }}
QLabel#kpiText {{ font-size: 11pt; font-weight: 600; }}
QFrame#mapcard {{ background: {panel}; border: 1px solid {line}; border-radius: 12px; }}
QLabel#mapTitle {{ font-weight: 600; }}
QLabel#mapSub {{ color: {muted}; font-size: 9pt; }}
QToolButton#envcard {{ background: {raised}; border: 1px solid {line}; border-radius: 12px; padding: 8px 4px; font-weight: 600; }}
QToolButton#envcard:hover {{ border-color: {line2}; }}
QToolButton#envcard:checked {{ border: 2px solid {accent}; background: {accent_soft}; color: {text}; }}
QFrame#seg {{ background: {panel}; border: 1px solid {line}; border-radius: 10px; }}
QPushButton#segbtn {{ background: transparent; border: none; border-radius: 7px; padding: 6px 2px; color: {muted}; font-size: 9pt; }}
QPushButton#segbtn:hover {{ color: {text}; }}
QPushButton#segbtn:checked {{ background: {raised2}; color: {text}; font-weight: 600; }}
QPushButton#chip {{ background: {panel}; border: 1px solid {line}; border-radius: 11px; padding: 3px 10px; font-size: 9pt; color: {text}; }}
QPushButton#chip:checked {{ background: {panel}; color: {text}; border-color: {line2}; font-weight: 400; }}
QPushButton#chip:!checked {{ color: {faint}; }}
QPushButton#start {{ background: {accent}; color: {on_accent}; border: none; border-radius: 10px; padding: 10px; font-weight: 700; font-size: 11pt; }}
QPushButton#start:hover {{ background: {accent_hover}; }}
QPushButton#secondary {{ background: {warn_soft}; color: {warn}; border: 1px solid {warn}; border-radius: 9px; padding: 7px 12px; font-weight: 600; }}
QPushButton#secondary:checked {{ background: {warn}; color: #141a1f; }}
QFrame#pad {{ background: {panel}; border: 1px solid {line}; border-radius: 9px; }}
QFrame#pad[on="true"] {{ border-color: {accent}; }}
QScrollArea {{ background: transparent; border: none; }}
QScrollArea > QWidget > QWidget {{ background: transparent; }}
QGroupBox {{ border: 1px solid {line}; border-radius: 10px; margin-top: 16px; padding: 10px 8px 8px; background: {raised}; }}
QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; left: 10px; padding: 0 6px; color: {muted}; font-weight: 600; }}
QPushButton {{ background: {raised2}; border: 1px solid {line}; border-radius: 8px; padding: 6px 12px; }}
QPushButton:hover {{ border-color: {line2}; }}
QPushButton:checked {{ background: {accent}; color: {on_accent}; border-color: {accent}; font-weight: 600; }}
QPushButton:disabled {{ color: {faint}; }}
QComboBox, QSpinBox, QLineEdit {{ background: {panel}; border: 1px solid {line}; border-radius: 8px; padding: 5px 10px; min-height: 22px; }}
QComboBox:hover, QSpinBox:hover {{ border-color: {line2}; }}
QComboBox::drop-down {{ border: none; width: 24px; }}
QComboBox QAbstractItemView {{ background: {panel}; border: 1px solid {line}; border-radius: 8px; padding: 4px; selection-background-color: {raised2}; selection-color: {text}; }}
QSpinBox {{ font-family: {mono}; font-weight: 600; color: {text}; }}
QCheckBox {{ spacing: 8px; padding: 2px 0; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid {line2}; background: {panel}; }}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}
QWidget#teleWrap {{ background: {panel}; border-top: 1px solid {line}; }}
QTabWidget#tele::pane {{ border: none; border-top: 1px solid {line}; background: {panel}; top: 0px; }}
QTabWidget#tele::tab-bar {{ left: 0px; }}
QTabBar::tab {{ background: transparent; color: {muted}; padding: 9px 16px; border: none; border-bottom: 2px solid transparent; }}
QTabBar::tab:hover {{ color: {text}; }}
QTabBar::tab:selected {{ color: {text}; font-weight: 600; border-bottom: 2px solid {accent}; }}
QTableWidget {{ background: {panel}; gridline-color: transparent; border: none; selection-background-color: {raised}; }}
QTableWidget::item {{ border-bottom: 1px solid {line}; }}
QHeaderView {{ background: {panel}; }}
QHeaderView::section {{ background: {panel}; color: {muted}; padding: 6px; border: none; border-bottom: 1px solid {line}; border-right: 1px solid {line}; font-weight: 600; font-size: 9pt; }}
QFrame#faults {{ background: {raised}; border: 1px solid {line}; border-radius: 8px; }}
QPushButton#faultbtn {{ background: transparent; border: none; padding: 0 8px; border-radius: 6px; font-size: 9pt; color: {muted}; min-width: 34px; }}
QPushButton#faultbtn:hover {{ color: {text}; }}
QPushButton#faultbtn:checked {{ background: {panel}; color: {text}; font-weight: 600; }}
QPushButton#faultbtn[broken="true"]:checked {{ background: {bad_soft}; color: {bad}; }}
QWidget#cell {{ background: {panel}; }}
QLabel#health {{ color: {good}; font-weight: 600; background: {panel}; }}
QLabel#health[sev="warn"] {{ color: {warn}; }}
QLabel#health[sev="bad"] {{ color: {bad}; }}
QLabel#reading {{ font-family: {mono}; font-weight: 600; }}
QProgressBar {{ border: none; border-radius: 3px; background: {raised2}; text-align: center; color: {text}; max-height: 6px; min-height: 6px; }}
QProgressBar::chunk {{ border-radius: 3px; background: {accent}; }}
QProgressBar#big {{ max-height: 12px; min-height: 12px; border-radius: 6px; }}
QListWidget#events {{ background: {panel}; border: none; }}
QListWidget#events::item {{ padding: 5px 10px; border-bottom: 1px solid {line}; }}
QPlainTextEdit, QTextBrowser {{ background: {panel}; border: 1px solid {line}; border-radius: 8px; padding: 6px; }}
QScrollBar:vertical {{ background: transparent; width: 8px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {line}; border-radius: 3px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {line2}; }}
QScrollBar::handle:vertical:pressed {{ background: {faint}; }}
QScrollBar:horizontal {{ background: transparent; height: 8px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {line}; border-radius: 3px; min-width: 30px; }}
QScrollBar::handle:horizontal:hover {{ background: {line2}; }}
QScrollBar::handle:horizontal:pressed {{ background: {faint}; }}
QScrollBar::add-line, QScrollBar::sub-line {{ width: 0; height: 0; border: none; background: none; }}
QScrollBar::add-page, QScrollBar::sub-page {{ background: none; }}
QSplitter::handle {{ background: transparent; }}
QMainWindow::separator {{ background: {bg}; width: 6px; height: 6px; border: none; }}
QMainWindow::separator:hover {{ background: {line2}; }}
QTabBar {{ qproperty-drawBase: 0; background: transparent; }}
QToolTip {{ background: {panel}; color: {text}; border: 1px solid {line}; border-radius: 6px; padding: 6px; }}
"""

DARK = dict(bg="#11161b", panel="#171e24", raised="#1e262d", raised2="#26303a", line="#2a343e", line2="#36424e",
            text="#e6edf3", muted="#8b9aa7", faint="#5d6b77",
            accent="#2dd4bf", accent_hover="#5eead4", accent_soft="#173a37", on_accent="#0b1114",
            warn="#f5a524", warn_soft="#3a2e14", bad="#f87171", bad_soft="#3b1c1f",
            good="#4ade80", good_soft="#15301f", good_line="#22553a")
LIGHT = dict(bg="#eef1f4", panel="#ffffff", raised="#f5f7f9", raised2="#e9eef2", line="#dce3e9", line2="#c9d3dc",
             text="#141a1f", muted="#5c6b78", faint="#8b9aa7",
             accent="#0f9d8a", accent_hover="#13b39d", accent_soft="#dcf3ef", on_accent="#ffffff",
             warn="#b45309", warn_soft="#fff4e0", bad="#dc2626", bad_soft="#fde8e8",
             good="#15803d", good_soft="#e5f6ea", good_line="#a7dcb7")
CURRENT = DARK


def apply_theme(app: QApplication, dark: bool):
    """Fusion base + a palette + one stylesheet: the same design language as the
    operator console (slate surfaces, teal accent, rounded controls)."""
    global CURRENT
    app.setStyle("Fusion")
    t = DARK if dark else LIGHT
    CURRENT = t
    p = QPalette()

    def c(k):
        return QColor(t[k])
    p.setColor(QPalette.ColorRole.Window, c("bg"))
    p.setColor(QPalette.ColorRole.WindowText, c("text"))
    p.setColor(QPalette.ColorRole.Base, c("panel"))
    p.setColor(QPalette.ColorRole.AlternateBase, c("raised"))
    p.setColor(QPalette.ColorRole.ToolTipBase, c("panel"))
    p.setColor(QPalette.ColorRole.ToolTipText, c("text"))
    p.setColor(QPalette.ColorRole.Text, c("text"))
    p.setColor(QPalette.ColorRole.Button, c("raised2"))
    p.setColor(QPalette.ColorRole.ButtonText, c("text"))
    p.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
    p.setColor(QPalette.ColorRole.Highlight, c("accent"))
    p.setColor(QPalette.ColorRole.HighlightedText, c("on_accent"))
    p.setColor(QPalette.ColorRole.PlaceholderText, c("muted"))
    p.setColor(QPalette.ColorRole.Mid, c("line"))
    p.setColor(QPalette.ColorRole.Link, c("accent"))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        p.setColor(QPalette.ColorGroup.Disabled, role, c("faint"))
    app.setPalette(p)
    load_fonts()
    app.setStyleSheet(QSS.format(mono=MONO, ui=UI, **t))


def color(key: str) -> QColor:
    """A colour of the current theme, for widgets that paint themselves."""
    return QColor(CURRENT[key])


def restyle(widget):
    """Re-apply the stylesheet after a dynamic property (sev, on, broken) changed."""
    st = widget.style()
    st.unpolish(widget)
    st.polish(widget)


def is_dark(app: QApplication) -> bool:
    return app.palette().color(QPalette.ColorRole.Window).lightness() < 128


def paint_icon(size: int = 256) -> QImage:
    """A rover seen from above inside a sonar ring: body, two wheel pairs,
    three echo arcs ahead. Amber on slate, like the console."""
    img = QImage(size, size, QImage.Format.Format_ARGB32)
    img.fill(Qt.GlobalColor.transparent)
    p = QPainter(img)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    s = size
    # tile
    path = QPainterPath()
    path.addRoundedRect(QRectF(0, 0, s, s), s * 0.22, s * 0.22)
    p.fillPath(path, QColor(20, 26, 31))
    # sonar arcs (ahead = up)
    pen = QPen(QColor(45, 212, 191), s * 0.045, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    # the rover sits in the lower half; the echo arcs fan out above it so the
    # whole figure is centred on the tile
    cx, cy = s * 0.5, s * 0.66
    for k, rad in enumerate((0.27, 0.36, 0.45)):
        p.setOpacity(1.0 - k * 0.28)
        p.drawArc(QRectF(cx - s * rad, cy - s * rad, 2 * s * rad, 2 * s * rad), 52 * 16, 76 * 16)
    p.setOpacity(1.0)
    # wheels
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(230, 237, 243))
    for dx in (-1, 1):
        for dy in (-1, 1):
            p.drawRoundedRect(QRectF(cx + dx * s * 0.19 - s * 0.045, cy + dy * s * 0.095 - s * 0.07, s * 0.09, s * 0.14), s * 0.02, s * 0.02)
    # body
    p.setBrush(QColor(245, 165, 36))
    p.drawRoundedRect(QRectF(cx - s * 0.15, cy - s * 0.18, s * 0.30, s * 0.36), s * 0.06, s * 0.06)
    # camera "eye" at the front
    p.setBrush(QColor(20, 26, 31))
    p.drawEllipse(QRectF(cx - s * 0.045, cy - s * 0.14, s * 0.09, s * 0.09))
    p.end()
    return img


def ensure_icon() -> QIcon:
    os.makedirs(ASSETS, exist_ok=True)
    if not os.path.exists(ICON_PNG):
        paint_icon(256).save(ICON_PNG)
    icon = QIcon()
    for sz in (16, 32, 48, 64, 128, 256):
        icon.addPixmap(QPixmap.fromImage(paint_icon(sz)))
    if not os.path.exists(ICON_ICO):
        paint_icon(256).save(ICON_ICO)
    return icon
