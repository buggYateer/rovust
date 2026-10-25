"""Light / dark palettes for the Qt interface and the application icon."""
from __future__ import annotations

import os

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QImage, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import QApplication

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")
ICON_PNG = os.path.join(ASSETS, "icon.png")
ICON_ICO = os.path.join(ASSETS, "icon.ico")


QSS = """
* {{ font-family: "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif; font-size: 10pt; }}
QMainWindow, QDialog {{ background: {bg}; }}
QWidget {{ color: {text}; }}
QMenuBar {{ background: {bg}; padding: 2px 6px; }}
QMenuBar::item {{ padding: 6px 10px; border-radius: 6px; }}
QMenuBar::item:selected {{ background: {surface2}; }}
QMenu {{ background: {surface}; border: 1px solid {line}; border-radius: 8px; padding: 6px; }}
QMenu::item {{ padding: 6px 26px 6px 12px; border-radius: 6px; }}
QMenu::item:selected {{ background: {accent}; color: {on_accent}; }}
QMenu::separator {{ height: 1px; background: {line}; margin: 6px 4px; }}
QToolBar {{ background: {bg}; border: none; padding: 4px 8px; spacing: 4px; }}
QToolBar::separator {{ width: 1px; background: {line}; margin: 6px 6px; }}
QToolButton {{ padding: 6px 12px; border-radius: 6px; border: 1px solid transparent; }}
QToolButton:hover {{ background: {surface2}; border-color: {line}; }}
QToolButton:checked {{ background: {accent}; color: {on_accent}; font-weight: 600; }}
QStatusBar {{ background: {surface}; border-top: 1px solid {line}; }}
QStatusBar QLabel {{ color: {muted}; padding: 0 6px; }}
QDockWidget::title {{ background: {bg}; padding: 8px 10px; color: {muted}; font-weight: 600; text-align: left; }}
QGroupBox {{ border: 1px solid {line}; border-radius: 10px; margin-top: 16px; padding: 10px 8px 8px; background: {surface}; }}
QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; left: 10px; padding: 0 6px; color: {muted}; font-weight: 600; }}
QPushButton {{ background: {surface2}; border: 1px solid {line}; border-radius: 8px; padding: 7px 14px; }}
QPushButton:hover {{ border-color: {accent}; }}
QPushButton:pressed {{ background: {line}; }}
QPushButton:checked {{ background: {accent}; color: {on_accent}; border-color: {accent}; font-weight: 600; }}
QPushButton:disabled {{ color: {muted}; }}
QPushButton#primary {{ background: {accent}; color: {on_accent}; border-color: {accent}; font-weight: 600; }}
QPushButton#primary:hover {{ background: {accent_hover}; }}
QComboBox, QSpinBox, QLineEdit {{ background: {surface2}; border: 1px solid {line}; border-radius: 8px; padding: 5px 10px; min-height: 22px; }}
QComboBox:hover, QSpinBox:hover {{ border-color: {accent}; }}
QComboBox::drop-down {{ border: none; width: 26px; subcontrol-origin: padding; subcontrol-position: center right; }}
QComboBox QAbstractItemView {{ background: {surface}; border: 1px solid {line}; border-radius: 8px; padding: 4px; selection-background-color: {accent}; selection-color: {on_accent}; }}
QSpinBox::up-button, QSpinBox::down-button {{ width: 18px; border: none; }}
QCheckBox {{ spacing: 8px; padding: 2px 0; }}
QCheckBox::indicator {{ width: 16px; height: 16px; border-radius: 4px; border: 1px solid {line}; background: {surface2}; }}
QCheckBox::indicator:checked {{ background: {accent}; border-color: {accent}; }}
QTabWidget::pane {{ border: 1px solid {line}; border-radius: 10px; background: {surface}; top: -1px; }}
QTabBar::tab {{ background: transparent; color: {muted}; padding: 8px 18px; margin-right: 4px; border: 1px solid transparent; border-bottom: none; border-top-left-radius: 8px; border-top-right-radius: 8px; }}
QTabBar::tab:hover {{ color: {text}; }}
QTabBar::tab:selected {{ background: {surface}; color: {text}; font-weight: 600; border-color: {line}; }}
QTableWidget {{ background: {surface}; alternate-background-color: {surface2}; gridline-color: {line}; border: none; border-radius: 8px; selection-background-color: {surface2}; }}
QHeaderView::section {{ background: {surface}; color: {muted}; padding: 6px; border: none; border-bottom: 1px solid {line}; font-weight: 600; }}
QTableWidget QComboBox {{ padding: 1px 6px; min-height: 18px; border-radius: 5px; }}
QProgressBar {{ border: none; border-radius: 6px; background: {surface2}; text-align: center; color: {text}; min-height: 12px; }}
QProgressBar::chunk {{ border-radius: 6px; background: {accent}; }}
QPlainTextEdit, QTextBrowser {{ background: {surface}; border: 1px solid {line}; border-radius: 8px; padding: 6px; }}
QScrollBar:vertical {{ background: transparent; width: 10px; margin: 2px; }}
QScrollBar::handle:vertical {{ background: {line}; border-radius: 5px; min-height: 30px; }}
QScrollBar::handle:vertical:hover {{ background: {muted}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
QScrollBar:horizontal {{ background: transparent; height: 10px; margin: 2px; }}
QScrollBar::handle:horizontal {{ background: {line}; border-radius: 5px; min-width: 30px; }}
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
QSplitter::handle {{ background: transparent; }}
QToolTip {{ background: {surface}; color: {text}; border: 1px solid {line}; border-radius: 6px; padding: 6px; }}
QLabel#hint {{ color: {muted}; }}
"""

DARK = dict(bg="#141a1f", surface="#1e262d", surface2="#26303a", line="#2f3b46", text="#e6edf3", muted="#8b9aa7",
            accent="#2dd4bf", accent_hover="#5eead4", on_accent="#0b1114")
LIGHT = dict(bg="#eef1f4", surface="#ffffff", surface2="#f3f6f8", line="#d5dde4", text="#141a1f", muted="#5c6b78",
             accent="#0f9d8a", accent_hover="#13b39d", on_accent="#ffffff")


def apply_theme(app: QApplication, dark: bool):
    """Fusion base + a palette + one stylesheet: the same design language as the
    operator console (slate surfaces, teal accent, rounded controls)."""
    app.setStyle("Fusion")
    t = DARK if dark else LIGHT
    p = QPalette()

    def c(k):
        return QColor(t[k])
    p.setColor(QPalette.ColorRole.Window, c("bg"))
    p.setColor(QPalette.ColorRole.WindowText, c("text"))
    p.setColor(QPalette.ColorRole.Base, c("surface"))
    p.setColor(QPalette.ColorRole.AlternateBase, c("surface2"))
    p.setColor(QPalette.ColorRole.ToolTipBase, c("surface"))
    p.setColor(QPalette.ColorRole.ToolTipText, c("text"))
    p.setColor(QPalette.ColorRole.Text, c("text"))
    p.setColor(QPalette.ColorRole.Button, c("surface2"))
    p.setColor(QPalette.ColorRole.ButtonText, c("text"))
    p.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
    p.setColor(QPalette.ColorRole.Highlight, c("accent"))
    p.setColor(QPalette.ColorRole.HighlightedText, c("on_accent"))
    p.setColor(QPalette.ColorRole.PlaceholderText, c("muted"))
    p.setColor(QPalette.ColorRole.Mid, c("line"))
    p.setColor(QPalette.ColorRole.Link, c("accent"))
    for role in (QPalette.ColorRole.Text, QPalette.ColorRole.ButtonText, QPalette.ColorRole.WindowText):
        p.setColor(QPalette.ColorGroup.Disabled, role, c("muted"))
    app.setPalette(p)
    app.setStyleSheet(QSS.format(**t))


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
    cx, cy = s * 0.5, s * 0.58
    for k, rad in enumerate((0.30, 0.40, 0.50)):
        p.setOpacity(1.0 - k * 0.28)
        p.drawArc(QRectF(cx - s * rad, cy - s * rad, 2 * s * rad, 2 * s * rad), 50 * 16, 80 * 16)
    p.setOpacity(1.0)
    # wheels
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(QColor(230, 237, 243))
    for dx in (-1, 1):
        for dy in (-1, 1):
            p.drawRoundedRect(QRectF(cx + dx * s * 0.19 - s * 0.045, cy + dy * s * 0.10 - s * 0.07, s * 0.09, s * 0.14), s * 0.02, s * 0.02)
    # body
    p.setBrush(QColor(245, 165, 36))
    p.drawRoundedRect(QRectF(cx - s * 0.15, cy - s * 0.19, s * 0.30, s * 0.38), s * 0.06, s * 0.06)
    # camera "eye" at the front
    p.setBrush(QColor(20, 26, 31))
    p.drawEllipse(QRectF(cx - s * 0.045, cy - s * 0.15, s * 0.09, s * 0.09))
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
