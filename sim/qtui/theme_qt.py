"""Light / dark palettes for the Qt interface and the application icon."""
from __future__ import annotations

import os

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QBrush, QColor, QIcon, QImage, QPainter, QPainterPath, QPalette, QPen, QPixmap
from PySide6.QtWidgets import QApplication

ASSETS = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets")
ICON_PNG = os.path.join(ASSETS, "icon.png")
ICON_ICO = os.path.join(ASSETS, "icon.ico")


def apply_theme(app: QApplication, dark: bool):
    app.setStyle("Fusion")
    p = QPalette()
    if dark:
        base, surface, text, muted, hi = QColor(20, 26, 31), QColor(30, 38, 45), QColor(230, 237, 243), QColor(139, 154, 167), QColor(45, 212, 191)
        p.setColor(QPalette.ColorRole.Window, surface)
        p.setColor(QPalette.ColorRole.WindowText, text)
        p.setColor(QPalette.ColorRole.Base, base)
        p.setColor(QPalette.ColorRole.AlternateBase, surface)
        p.setColor(QPalette.ColorRole.ToolTipBase, surface)
        p.setColor(QPalette.ColorRole.ToolTipText, text)
        p.setColor(QPalette.ColorRole.Text, text)
        p.setColor(QPalette.ColorRole.Button, QColor(38, 48, 58))
        p.setColor(QPalette.ColorRole.ButtonText, text)
        p.setColor(QPalette.ColorRole.BrightText, QColor(255, 255, 255))
        p.setColor(QPalette.ColorRole.Highlight, hi)
        p.setColor(QPalette.ColorRole.HighlightedText, base)
        p.setColor(QPalette.ColorRole.PlaceholderText, muted)
        p.setColor(QPalette.ColorRole.Link, hi)
        p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.Text, muted)
        p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.ButtonText, muted)
        p.setColor(QPalette.ColorGroup.Disabled, QPalette.ColorRole.WindowText, muted)
        app.setPalette(p)
        app.setStyleSheet("QToolTip { color: #e6edf3; background: #26303a; border: 1px solid #2f3b46; }")
    else:
        app.setPalette(app.style().standardPalette())
        app.setStyleSheet("")


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
