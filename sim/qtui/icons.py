"""Small line icons drawn with QPainter, so they follow the theme colours
and need no image files (same shapes as the web mockup)."""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


def icon(name: str, color: QColor | str, size: int = 16) -> QIcon:
    pm = QPixmap(size * 2, size * 2)
    pm.setDevicePixelRatio(2)
    pm.fill(Qt.GlobalColor.transparent)
    p = QPainter(pm)
    p.setRenderHint(QPainter.RenderHint.Antialiasing)
    c = QColor(color)
    pen = QPen(c, 1.6, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin)
    p.setPen(pen)
    p.setBrush(Qt.BrushStyle.NoBrush)
    s = size / 24.0
    p.scale(s, s)
    DRAW.get(name, lambda p, c: None)(p, c)
    p.end()
    return QIcon(pm)


def _fill(p, c):
    p.setPen(Qt.PenStyle.NoPen)
    p.setBrush(c)


def _pause(p, c):
    _fill(p, c)
    p.drawRoundedRect(QRectF(6, 5, 4, 14), 1, 1)
    p.drawRoundedRect(QRectF(14, 5, 4, 14), 1, 1)


def _play(p, c):
    _fill(p, c)
    path = QPainterPath(QPointF(7, 4.5))
    path.lineTo(19, 12)
    path.lineTo(7, 19.5)
    path.closeSubpath()
    p.drawPath(path)


def _stop(p, c):
    _fill(p, c)
    p.drawRoundedRect(QRectF(6, 6, 12, 12), 2, 2)


def _restart(p, c):
    p.setPen(QPen(c, 2.2, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.drawArc(QRectF(4, 4, 16, 16), 135 * 16, -300 * 16)
    p.drawPolyline([QPointF(4, 4), QPointF(4, 8.5), QPointF(8.5, 8.5)])


def _bulb(p, c):
    path = QPainterPath()
    path.moveTo(9, 17)
    path.lineTo(9, 16.8)
    path.cubicTo(9, 16, 8.6, 15.2, 8, 14.7)
    path.arcTo(QRectF(5, 2, 14, 14), 225, -270)
    path.cubicTo(15.4, 15.2, 15, 16, 15, 16.8)
    path.lineTo(15, 17)
    path.closeSubpath()
    p.drawPath(path)
    p.drawLine(QPointF(9, 20), QPointF(15, 20))
    p.drawLine(QPointF(10, 22.5), QPointF(14, 22.5))


def _phone(p, c):
    p.drawRoundedRect(QRectF(7, 3, 10, 18), 2, 2)
    p.drawLine(QPointF(11, 17.5), QPointF(13, 17.5))


def _upload(p, c):
    p.setPen(QPen(c, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.drawLine(QPointF(12, 16), QPointF(12, 4))
    p.drawPolyline([QPointF(7, 9), QPointF(12, 4), QPointF(17, 9)])
    p.drawLine(QPointF(5, 20), QPointF(19, 20))


def _moon(p, c):
    path = QPainterPath()
    path.addEllipse(QRectF(4, 4, 16, 16))
    cut = QPainterPath()
    cut.addEllipse(QRectF(9, 1, 15, 15))
    _fill(p, c)
    p.drawPath(path.subtracted(cut))


def _sun(p, c):
    p.drawEllipse(QRectF(8, 8, 8, 8))
    for k in range(8):
        a = k * math.pi / 4
        p.drawLine(QPointF(12 + 6.5 * math.cos(a), 12 + 6.5 * math.sin(a)), QPointF(12 + 9 * math.cos(a), 12 + 9 * math.sin(a)))


def _panel(p, c):
    p.drawRoundedRect(QRectF(3, 4, 18, 16), 2.5, 2.5)
    p.drawLine(QPointF(9, 4), QPointF(9, 20))


def _chev_down(p, c):
    p.setPen(QPen(c, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.drawPolyline([QPointF(6, 9), QPointF(12, 15), QPointF(18, 9)])


def _chev_up(p, c):
    p.setPen(QPen(c, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap, Qt.PenJoinStyle.RoundJoin))
    p.drawPolyline([QPointF(6, 15), QPointF(12, 9), QPointF(18, 15)])


def _copy(p, c):
    p.drawRoundedRect(QRectF(9, 9, 11, 11), 2, 2)
    p.drawRoundedRect(QRectF(4, 4, 11, 11), 2, 2)


def _gamepad(p, c):
    path = QPainterPath()
    path.moveTo(6.7, 5)
    path.lineTo(17.3, 5)
    path.cubicTo(19.3, 5, 21, 6.4, 21.25, 8.4)
    path.lineTo(22.1, 14)
    path.cubicTo(22.5, 16.6, 19.1, 18.3, 17, 16.5)
    path.lineTo(15.5, 15)
    path.lineTo(8.5, 15)
    path.lineTo(7, 16.5)
    path.cubicTo(4.9, 18.3, 1.5, 16.6, 1.9, 14)
    path.lineTo(2.75, 8.4)
    path.cubicTo(3, 6.4, 4.7, 5, 6.7, 5)
    p.drawPath(path)
    p.drawLine(QPointF(6, 10), QPointF(10, 10))
    p.drawLine(QPointF(8, 8), QPointF(8, 12))
    _fill(p, c)
    p.drawEllipse(QPointF(15, 11), 1, 1)
    p.drawEllipse(QPointF(18, 9.5), 1, 1)


def _dot(p, c):
    _fill(p, c)
    p.drawEllipse(QPointF(12, 12), 4.5, 4.5)


DRAW = {"pause": _pause, "play": _play, "stop": _stop, "restart": _restart, "bulb": _bulb, "phone": _phone,
        "upload": _upload, "moon": _moon, "sun": _sun, "panel": _panel, "down": _chev_down, "up": _chev_up,
        "copy": _copy, "gamepad": _gamepad, "dot": _dot}
