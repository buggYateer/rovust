"""Radio link tab: the rover's communication module as the operator sees it.

Left: a diagram of the base station and the rover with the line of sight
coloured by signal strength and the walls in between. Right: RSSI bars,
state, latency, packet counters and a live log of the packets that arrive
from the phone / tablet console or the keyboard.
"""
from __future__ import annotations

import math

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import QFormLayout, QHBoxLayout, QLabel, QPlainTextEdit, QVBoxLayout, QWidget

from .i18n import LANG, tr

C_OK, C_WEAK, C_LOST = QColor(45, 212, 191), QColor(245, 165, 36), QColor(239, 68, 68)


def link_color(state: str) -> QColor:
    return {"ok": C_OK, "weak": C_WEAK}.get(state, C_LOST)


class LinkDiagram(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mission = None
        self.setMinimumSize(300, 160)

    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        r = self.rect().adjusted(1, 1, -1, -1)
        p.fillRect(r, pal.base())
        p.setPen(QPen(pal.mid().color(), 1))
        p.drawRect(r)
        m = self.mission
        if m is None:
            return
        lk = m.link
        col = link_color(lk.state)
        bx, by = r.left() + 60, r.center().y()
        rx, ry = r.right() - 70, r.center().y()
        # line of sight, dashed when weak, dotted when lost
        pen = QPen(col, 3)
        pen.setStyle({"ok": Qt.PenStyle.SolidLine, "weak": Qt.PenStyle.DashLine}.get(lk.state, Qt.PenStyle.DotLine))
        p.setPen(pen)
        p.drawLine(QPointF(bx + 18, by), QPointF(rx - 22, ry))
        # walls on the line of sight
        if lk.walls:
            n = min(lk.walls, 30)
            for i in range(n):
                x = bx + 30 + (rx - bx - 60) * (i + 0.5) / n
                p.fillRect(QRectF(x - 2, by - 14, 4, 28), QColor(90, 90, 90))
        # base station: mast + waves
        p.setPen(QPen(pal.text().color(), 2))
        p.drawLine(QPointF(bx, by + 30), QPointF(bx, by - 25))
        p.drawLine(QPointF(bx - 12, by + 30), QPointF(bx + 12, by + 30))
        for k, rad in enumerate((10, 18, 26)):
            p.setPen(QPen(col if lk.strength > (k + 1) / 3.5 else pal.mid().color(), 2))
            p.drawArc(QRectF(bx - rad, by - 25 - rad, 2 * rad, 2 * rad), 20 * 16, 140 * 16)
        # rover: body + antenna
        p.setPen(QPen(pal.text().color(), 1.5))
        p.setBrush(QColor(255, 140, 0))
        p.drawRoundedRect(QRectF(rx - 18, ry - 12, 36, 24), 5, 5)
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawLine(QPointF(rx + 10, ry - 12), QPointF(rx + 16, ry - 28))
        p.setPen(col)
        p.setBrush(col)
        p.drawEllipse(QPointF(rx + 16, ry - 28), 3, 3)
        # labels
        p.setPen(pal.text().color())
        p.setFont(QFont(self.font().family(), 9))
        p.drawText(QRectF(bx - 50, by + 34, 100, 18), Qt.AlignmentFlag.AlignCenter, tr("r_base"))
        p.drawText(QRectF(rx - 50, ry + 34, 100, 18), Qt.AlignmentFlag.AlignCenter, tr("r_rover"))
        mid = (bx + rx) / 2
        p.drawText(QRectF(mid - 120, r.top() + 8, 240, 18), Qt.AlignmentFlag.AlignCenter,
                   tr("r_between", lk.distance, lk.walls))
        p.setPen(col)
        p.setFont(QFont(self.font().family(), 10, QFont.Weight.Bold))
        p.drawText(QRectF(mid - 120, by - 40, 240, 18), Qt.AlignmentFlag.AlignCenter,
                   f"{tr('link_' + lk.state)}   RSSI {lk.strength:.0%}")


class RadioTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.mission = None
        lay = QHBoxLayout(self)
        left = QVBoxLayout()
        self.diagram = LinkDiagram()
        left.addWidget(self.diagram, 1)
        self.hint = QLabel()
        self.hint.setWordWrap(True)
        self.hint.setObjectName("hint")
        left.addWidget(self.hint)
        w = QWidget()
        w.setLayout(left)
        lay.addWidget(w, 3)

        right = QVBoxLayout()
        form = QFormLayout()
        self.labels = {}
        self.titles = {}
        for key in ("state", "latency", "packets", "mode", "last", "clients"):
            lab = QLabel("-")
            self.labels[key] = lab
            self.titles[key] = QLabel()
            form.addRow(self.titles[key], lab)
        right.addLayout(form)
        self.log = QPlainTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumBlockCount(60)
        self.log.setFont(QFont("Consolas", 9))
        self.log.setLayoutDirection(Qt.LayoutDirection.LeftToRight)       # the packet log is technical: always left to right
        right.addWidget(self.log, 1)
        w2 = QWidget()
        w2.setLayout(right)
        lay.addWidget(w2, 2)
        self._logged = 0
        LANG.changed.connect(self.retranslate)
        self.retranslate()

    def retranslate(self, *_):
        self.hint.hide()
        self.diagram.setToolTip(tr("r_hint"))
        for k, lab in self.titles.items():
            lab.setText(tr("r_" + k) + ":")
        self.refresh()
        self.diagram.update()

    def set_mission(self, mission):
        self.mission = mission
        self.diagram.mission = mission
        self.log.clear()
        self._logged = 0

    def refresh(self):
        m = self.mission
        if m is None:
            return
        lk = m.link
        L = self.labels
        L["state"].setText(f"{tr('link_' + lk.state)}   RSSI {lk.strength:.0%}   " + tr("r_walls", lk.distance, lk.walls))
        L["state"].setStyleSheet(f"color: {link_color(lk.state).name()}; font-weight: 600;")
        L["latency"].setText(f"{m.cfg.link.latency_s:.1f} s")
        L["packets"].setText(f"{lk.delivered} / {lk.dropped}")
        loss = {"home": "lossHome", "explore": "lossExplore", "hold": "lossHold"}.get(m.on_link_loss, "lossHome")
        L["mode"].setText(tr(m.mode) + (tr("r_fallback", tr(loss)) if m.link_fallback else ""))
        last = next((e for e in reversed(lk.log) if e[1] == "RX"), None)
        if last is not None:
            t, _, c = last
            L["last"].setText(self._fmt(c) + "   " + tr("r_at", t))
        src = {e[2].get("from", "") for e in lk.log if e[2].get("from")}
        L["clients"].setText(", ".join(sorted(src)) if src else tr("r_nobody"))
        # append new log lines
        entries = list(lk.log)
        new = entries[max(0, len(entries) - (len(entries) - self._logged)):] if self._logged < len(entries) else []
        if self._logged > len(entries):      # deque wrapped: resync
            new = entries
        for t, kind, c in new[-20:]:
            self.log.appendPlainText(f"{t:7.1f} s  {kind:4}  {self._fmt(c)}")
        self._logged = len(entries)
        self.diagram.update()

    @staticmethod
    def _fmt(c: dict) -> str:
        t = c.get("type")
        src = c.get("from", "")
        if t == "drive":
            body = f"drive  v={c['v']:+.2f} m/s  w={c['w']:+.2f} rad/s"
        else:
            body = t + (" " + str({k: v for k, v in c.items() if k not in ("type", "from")}) if len(c) > 2 else "")
        return f"{body}   [{src}]" if src else body
