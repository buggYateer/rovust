"""Operator console server (standard library only, runs in a daemon thread).

    GET  /                 the console page (sim/teleop/console.html)
    GET  /api/state        JSON telemetry for the page (5 Hz polling)
    GET  /api/map.png      the robot's belief map with its estimate and path
    GET  /api/camera.png   the camera patch, enlarged
    POST /api/cmd          {"type": "drive", "x": -1..1, "y": -1..1} or
                           {"type": "mode"|"lights"|"stop"|"home"|"link_loss"|"speed", ...}

Everything the page sends goes through ``Mission.operator_drive`` /
``operator_command``, i.e. over the simulated radio link with its range,
walls, latency and packet loss. The page never touches the robot directly.
"""
from __future__ import annotations

import json
import math
import os
import socket
import struct
import threading
import zlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import numpy as np

from ..render import belief_rgb

PAGE = os.path.join(os.path.dirname(__file__), "console.html")
ICON = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "assets", "icon.png")


def png_bytes(rgb: np.ndarray) -> bytes:
    """Minimal PNG encoder for an (h, w, 3) uint8 array."""
    h, w, _ = rgb.shape
    raw = b"".join(b"\x00" + rgb[y].tobytes() for y in range(h))

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)
    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(raw, 6)) + chunk(b"IEND", b""))


def lan_ip() -> str:
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except OSError:
        return "127.0.0.1"


class ConsoleServer:
    def __init__(self, get_mission, port: int = 8080):
        self.get_mission = get_mission       # callable -> Mission or None (the window swaps missions)
        self.port = port
        self.httpd = None
        self.thread = None
        self.clients = 0
        self.last_cmd_ok = True
        self.restart_requested = False      # set from the console, consumed by the window's timer

    # ------------------------------------------------------------ lifecycle
    def start(self):
        server = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):      # keep the Qt console quiet
                pass

            def _send(self, code, body, ctype):
                self.send_response(code)
                self.send_header("Content-Type", ctype)
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(body)

            def do_GET(self):
                try:
                    if self.path in ("/", "/index.html"):
                        with open(PAGE, "rb") as f:
                            self._send(200, f.read(), "text/html; charset=utf-8")
                    elif self.path.startswith("/api/state"):
                        self._send(200, json.dumps(server.state()).encode(), "application/json")
                    elif self.path.startswith("/api/map.png"):
                        self._send(200, server.map_png(), "image/png")
                    elif self.path.startswith("/api/camera.png"):
                        self._send(200, server.camera_png(), "image/png")
                    elif self.path.startswith(("/favicon", "/icon.png", "/apple-touch-icon")):
                        with open(ICON, "rb") as f:
                            self._send(200, f.read(), "image/png")
                    else:
                        self._send(404, b"not found", "text/plain")
                except Exception as e:          # never kill the thread on a race with a restarting mission
                    self._send(500, str(e).encode(), "text/plain")

            def do_POST(self):
                n = int(self.headers.get("Content-Length", 0))
                try:
                    cmd = json.loads(self.rfile.read(n) or b"{}")
                    cmd["from"] = self.client_address[0]
                    ok = server.command(cmd)
                    m = server.get_mission()
                    reason = "" if ok else ("mission_over" if (m is not None and m.done and cmd.get("type") != "restart") else "no_link")
                    self._send(200, json.dumps({"ok": ok, "reason": reason}).encode(), "application/json")
                except Exception as e:
                    self._send(400, str(e).encode(), "text/plain")

        self.httpd = ThreadingHTTPServer(("0.0.0.0", self.port), Handler)
        self.httpd.daemon_threads = True
        self.thread = threading.Thread(target=self.httpd.serve_forever, daemon=True)
        self.thread.start()

    def stop(self):
        if self.httpd is not None:
            self.httpd.shutdown()
            self.httpd.server_close()
            self.httpd = None

    @property
    def url(self) -> str:
        return f"http://{lan_ip()}:{self.port}"

    # -------------------------------------------------------------- bridge
    def command(self, cmd: dict) -> bool:
        m = self.get_mission()
        if m is None:
            return False
        t = cmd.get("type")
        if t == "restart":
            self.restart_requested = True
            return True
        if m.done:
            return False                        # nothing listens once the mission is over
        if t == "drive":
            # stick right (+x) must turn the rover right: a clockwise turn is a
            # negative angular velocity in the robot's frame
            ok = m.operator_drive(float(cmd.get("y", 0.0)), -float(cmd.get("x", 0.0)), source=cmd.get("from", "console"))
        elif t == "speed":
            m.operator_speed = max(0.05, min(0.6, float(cmd.get("value", 0.35))))
            ok = True
        elif t in ("mode", "link_loss"):
            # console settings: they describe how the operator wants to work, so
            # they apply at once (the rover follows them whenever it can hear us)
            m._apply_operator(cmd)
            ok = True
        elif t in ("lights", "stop", "home"):
            ok = m.operator_command(cmd)        # physical commands travel over the radio
        else:
            ok = False
        self.last_cmd_ok = ok
        return ok

    def state(self) -> dict:
        m = self.get_mission()
        if m is None:
            return {"mission": False}
        r, s = m.robot, m.robot.sensors
        est = m.estimator.pose
        sonar = [{"a": round(math.degrees(x.angle)), "d": round(x.value, 2), "max": x.max_range, "ok": x.healthy}
                 for x in s.sonars]
        cliffs = [c.value > 0.5 for c in s.cliffs]
        return {
            "mission": True, "env": m.cfg.name, "status": m.status, "time": round(m.time, 1),
            "done": m.done, "end_reason": m.end_reason(),
            "mode": m.mode, "effective_mode": m.effective_mode, "fallback": m.link_fallback,
            "on_link_loss": m.on_link_loss, "behaviour": m.arbiter.active_name,
            "link": {"state": m.link.state, "strength": round(m.link.strength, 2),
                     "latency": m.cfg.link.latency_s, "dropped": m.link.dropped, "delivered": m.link.delivered,
                     "lost_for": round(m.link.lost_for(m.time), 1)},
            "battery": {"fraction": round(r.battery.fraction, 3), "voltage": round(r.battery.voltage, 2),
                        "power": round(r.battery.power, 1)},
            "pose": {"x": round(est.x, 2), "y": round(est.y, 2), "theta": round(est.theta, 2)},
            "speed": {"v": round(r.drive.v, 2), "w": round(r.drive.omega, 2), "max": m.operator_speed},
            "coverage": round(m.coverage(), 3), "distance": round(r.distance, 1),
            "sonar": sonar, "ir": [round(x.value, 2) for x in s.irs], "cliff": cliffs,
            "bumper": list(s.bumped()), "headlights": r.headlights,
            "terrain": (m.ai.last[0] if m.ai is not None else None),
            "collisions": r.collisions, "bumps": m.stats["bumps"], "cliff_events": m.stats["cliff_events"],
            "map_size": [m.world.w * m.world.cell, m.world.h * m.world.cell],
        }

    def map_png(self) -> bytes:
        m = self.get_mission()
        if m is None:
            return png_bytes(np.zeros((8, 8, 3), np.uint8))
        rgb = belief_rgb(m.grid, True, True, False).copy()
        g = m.grid
        for p in m.est_path[::2]:
            cx, cy = g.to_cell(p.x, p.y)
            if g.in_bounds(cx, cy):
                rgb[cy, cx] = (40, 170, 90)
        est = m.estimator.pose
        cx, cy = g.to_cell(est.x, est.y)
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                if g.in_bounds(cx + dx, cy + dy):
                    rgb[cy + dy, cx + dx] = (255, 140, 0)
        hx, hy = g.to_cell(est.x + 0.4 * math.cos(est.theta), est.y + 0.4 * math.sin(est.theta))
        if g.in_bounds(hx, hy):
            rgb[hy, hx] = (255, 255, 255)
        bx, by = m.home_cell
        rgb[by, bx] = (255, 255, 255)
        # 1x pixels: tiny PNG, the page scales it with image-rendering: pixelated
        return png_bytes(np.ascontiguousarray(rgb[::-1]))   # y up

    def camera_png(self) -> bytes:
        m = self.get_mission()
        cam = None if m is None else m.robot.sensors.camera
        if cam is None:
            return png_bytes(np.zeros((16, 16, 3), np.uint8))
        g = (np.clip(cam.image, 0, 1) * 255).astype(np.uint8)
        return png_bytes(np.ascontiguousarray(np.stack([g, g, g], -1)))
