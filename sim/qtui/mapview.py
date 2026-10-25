"""Map widgets: the true world and the robot's belief map, drawn with QPainter."""
from __future__ import annotations

import math

import numpy as np
from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPen
from PySide6.QtWidgets import QWidget

from ..ui.render import belief_rgb, world_rgb

C_TRUE_PATH = QColor(255, 215, 0)
C_FUSED = QColor(40, 170, 90)
C_ODOM = QColor(220, 60, 60)
C_PLAN = QColor(30, 120, 220)
C_FRONTIER = QColor(240, 160, 0)
C_SONAR = QColor(0, 120, 255)
C_SONAR_FAR = QColor(150, 170, 200)
C_IR = QColor(230, 80, 80)
C_ROBOT = QColor(255, 140, 0)
C_FAULT = QColor(220, 0, 0)


class MapWidget(QWidget):
    """Draws a (h, w, 3) RGB array scaled to fit, then calls an overlay painter."""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)
        self.title = title
        self.mission = None
        self.layers = {}
        self.kind = "world"          # "world" | "belief"
        self._img = None
        self._arr = None
        self.setMinimumSize(360, 260)
        self.setAutoFillBackground(True)

    def set_mission(self, mission, kind: str, layers: dict):
        self.mission = mission
        self.kind = kind
        self.layers = layers
        self._world_cache = None
        self.update()

    # ---------------------------------------------------------- transforms
    def _geometry(self):
        m = self.mission
        w_m, h_m = m.world.w * m.world.cell, m.world.h * m.world.cell
        avail_w, avail_h = self.width() - 12, self.height() - 30
        scale = min(avail_w / w_m, avail_h / h_m)
        pw, ph = w_m * scale, h_m * scale
        ox, oy = 6 + (avail_w - pw) / 2, 24 + (avail_h - ph) / 2
        return scale, ox, oy, pw, ph

    def to_px(self, x, y):
        s, ox, oy, pw, ph = self._geo
        return QPointF(ox + x * s, oy + ph - y * s)

    # --------------------------------------------------------------- paint
    def paintEvent(self, event):
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        pal = self.palette()
        p.fillRect(self.rect(), pal.base())
        p.setPen(pal.placeholderText().color())
        p.setFont(QFont(self.font().family(), 9, QFont.Weight.Bold))
        p.drawText(8, 16, self.title)
        if self.mission is None:
            p.setPen(pal.placeholderText().color())
            p.drawText(self.rect(), Qt.AlignmentFlag.AlignCenter, "No mission running")
            return
        m = self.mission
        self._geo = self._geometry()
        s, ox, oy, pw, ph = self._geo
        if self.kind == "world":
            if self._world_cache is None:
                self._world_cache = np.ascontiguousarray(world_rgb(m.world, m.cfg.ambient_light))
            arr = self._world_cache
        else:
            arr = np.ascontiguousarray(belief_rgb(m.grid, self.layers.get("terrain", True), True,
                                                  self.layers.get("visited", False)))
        self._arr = arr[::-1].copy()      # world y up
        h, w, _ = self._arr.shape
        img = QImage(self._arr.data, w, h, 3 * w, QImage.Format.Format_RGB888)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, False)
        p.drawImage(QRectF(ox, oy, pw, ph), img)
        p.setPen(QPen(pal.mid().color(), 1))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawRect(QRectF(ox, oy, pw, ph))
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.kind == "world":
            self._paint_world(p)
        else:
            self._paint_belief(p)

    def _path(self, p, poses, color, width):
        if len(poses) < 2:
            return
        p.setPen(QPen(color, width))
        pts = [self.to_px(q.x, q.y) for q in poses]
        for a, b in zip(pts, pts[1:]):
            p.drawLine(a, b)

    def _robot(self, p, pose, radius, fill, outline):
        c = self.to_px(pose.x, pose.y)
        r = max(3.0, radius * self._geo[0])
        p.setPen(QPen(outline, 1.5))
        p.setBrush(fill)
        p.drawEllipse(c, r, r)
        h = self.to_px(pose.x + radius * math.cos(pose.theta), pose.y + radius * math.sin(pose.theta))
        p.setPen(QPen(outline, 2))
        p.drawLine(c, h)

    def _paint_world(self, p):
        m = self.mission
        r = m.robot
        if self.layers.get("true_path", True):
            self._path(p, m.true_path, C_TRUE_PATH, 2)
        suite = r.sensors
        if self.layers.get("sonar", True):
            for s in suite.sonars:
                x, y, a = s.world_position(r)
                hit = s.value < s.max_range * 0.98
                col = C_FAULT if not s.healthy else (C_SONAR if hit else C_SONAR_FAR)
                p.setPen(QPen(col, 1))
                end = self.to_px(x + s.value * math.cos(a), y + s.value * math.sin(a))
                p.drawLine(self.to_px(x, y), end)
                if hit:
                    p.setBrush(col)
                    p.drawEllipse(end, 2.5, 2.5)
        if self.layers.get("ir", True):
            for s in suite.irs:
                x, y, a = s.world_position(r)
                p.setPen(QPen(C_FAULT if not s.healthy else C_IR, 1.2))
                p.drawLine(self.to_px(x, y), self.to_px(x + s.value * math.cos(a), y + s.value * math.sin(a)))
        for c in suite.cliffs:
            x, y = r.body_point(c.dx, c.dy)
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(QColor(220, 0, 0) if c.value > 0.5 else QColor(60, 180, 90))
            p.drawEllipse(self.to_px(x, y), 2.5, 2.5)
        self._link_line(p, r.pose)
        self._robot(p, r.pose, r.radius, C_ROBOT, QColor(40, 40, 40))

    def _link_line(self, p, pose):
        """Radio line of sight from the base station, drawn whenever the operator is in the loop."""
        m = self.mission
        if m.mode == "autonomous" and not m.link.log:
            return
        col = {"ok": QColor(45, 212, 191), "weak": QColor(245, 165, 36)}.get(m.link.state, QColor(239, 68, 68))
        pen = QPen(col, 2)
        pen.setStyle({"ok": Qt.PenStyle.SolidLine, "weak": Qt.PenStyle.DashLine}.get(m.link.state, Qt.PenStyle.DotLine))
        p.setPen(pen)
        base = self.to_px(*m.link.base)
        p.drawLine(base, self.to_px(pose.x, pose.y))
        p.setBrush(Qt.BrushStyle.NoBrush)
        for rad in (5, 9, 13):
            p.drawArc(QRectF(base.x() - rad, base.y() - rad, 2 * rad, 2 * rad), 30 * 16, 120 * 16)

    def _paint_belief(self, p):
        m = self.mission
        g = m.grid
        if self.layers.get("frontiers", True):
            p.setPen(QPen(C_FRONTIER, 2))
            for f in m.explorer.frontiers:
                for x, y in f.cells[::2]:
                    p.drawPoint(self.to_px(*g.to_world(int(x), int(y))))
            if m.explorer.target is not None:
                p.setBrush(Qt.BrushStyle.NoBrush)
                p.drawEllipse(self.to_px(*g.to_world(*m.explorer.target)), 6, 6)
        if m.explorer.path and len(m.explorer.path) > 1:
            p.setPen(QPen(C_PLAN, 2, Qt.PenStyle.DashLine))
            pts = [self.to_px(*g.to_world(*c)) for c in m.explorer.path]
            for a, b in zip(pts, pts[1:]):
                p.drawLine(a, b)
        self._path(p, m.odom_path, C_ODOM, 1)
        self._path(p, m.est_path, C_FUSED, 2)
        hx = self.to_px(*g.to_world(*m.home_cell))
        p.setPen(QPen(QColor(40, 40, 40), 1.5))
        p.setBrush(Qt.BrushStyle.NoBrush)
        p.drawEllipse(hx, 6, 6)
        self._link_line(p, m.estimator.pose)
        self._robot(p, m.estimator.odom, m.robot.radius * 0.6, QColor(255, 150, 150), C_ODOM)
        self._robot(p, m.estimator.pose, m.robot.radius, QColor(120, 220, 150), C_FUSED)
