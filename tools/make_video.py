"""The demo video: the real application, driven by a script, filmed by a virtual
camera that zooms in on what matters and back out, with one short caption at a
time - like a screen recording, without a person at the mouse.

    python tools/make_video.py            -> docs/media/rovust_demo.mp4

The window is rendered at twice its size, so the zoomed-in shots stay sharp.
The phone is the real console page in a headless Edge, driven with real
pointer events on its joystick (Chrome DevTools protocol); the commands go
over the simulated radio like a real phone's. Nothing is uploaded: reports go
to a temporary folder and the Drive bridge is switched off.
Needs ffmpeg on the PATH and Edge or Chrome.
"""
from __future__ import annotations

import base64
import json
import math
import os
import shutil
import socket
import struct
import subprocess
import sys
import tempfile
import time
import urllib.parse
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
os.environ["QT_QPA_PLATFORM"] = "offscreen"
os.environ["QT_SCALE_FACTOR"] = "2"

from PySide6.QtCore import QPoint, QPointF, QRect, QRectF, QSettings, Qt  # noqa: E402
from PySide6.QtGui import QColor, QFont, QImage, QPainter, QPainterPath, QPen  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

import sim.report as R  # noqa: E402

W, H, FPS = 1920, 1080, 25
OUT = os.path.join(ROOT, "docs", "media", "rovust_demo.mp4")
TEAL, AMBER, BG = QColor("#2dd4bf"), QColor("#f5a524"), QColor("#0d1216")


def find_browser():
    for p in (r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
              r"C:\Program Files\Google\Chrome\Application\chrome.exe"):
        if os.path.exists(p):
            return p
    return shutil.which("msedge") or shutil.which("chrome")


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


# ------------------------------------------------------------------ a tiny DevTools client (standard library only)
class CDP:
    def __init__(self, ws_url):
        u = urllib.parse.urlparse(ws_url)
        self.s = socket.create_connection((u.hostname, u.port), timeout=30)
        key = base64.b64encode(os.urandom(16)).decode()
        self.s.sendall((f"GET {u.path} HTTP/1.1\r\nHost: {u.hostname}:{u.port}\r\nUpgrade: websocket\r\n"
                        f"Connection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n").encode())
        buf = b""
        while b"\r\n\r\n" not in buf:
            buf += self.s.recv(4096)
        self.rest = buf.split(b"\r\n\r\n", 1)[1]
        self.id = 0

    def _read(self, n):
        while len(self.rest) < n:
            chunk = self.s.recv(1 << 20)
            if not chunk:
                raise ConnectionError("devtools closed")
            self.rest += chunk
        out, self.rest = self.rest[:n], self.rest[n:]
        return out

    def _frame(self):
        data = b""
        while True:
            b0, b1 = self._read(2)
            n = b1 & 0x7F
            if n == 126:
                n = struct.unpack(">H", self._read(2))[0]
            elif n == 127:
                n = struct.unpack(">Q", self._read(8))[0]
            data += self._read(n)
            if b0 & 0x80:
                return data

    def call(self, method, **params):
        self.id += 1
        msg = json.dumps({"id": self.id, "method": method, "params": params}).encode()
        mask = os.urandom(4)
        n = len(msg)
        head = bytes([0x81]) + (bytes([0x80 | n]) if n < 126 else bytes([0xFE]) + struct.pack(">H", n) if n < 65536
                                else bytes([0xFF]) + struct.pack(">Q", n))
        self.s.sendall(head + mask + bytes(c ^ mask[i % 4] for i, c in enumerate(msg)))
        while True:
            r = json.loads(self._frame())
            if r.get("id") == self.id:
                return r.get("result", {})


class Browser:
    def __init__(self):
        self.opened = None            # (url, w, h, scale, mobile): reopened after a restart
        self.after_open = ""          # script run once the page has loaded (and again after a restart)
        self.press = None             # where the pointer went down and where it is now
        self._start()

    def _start(self):
        self.port = free_port()
        self.profile = tempfile.mkdtemp(prefix="rovust-video-")
        self.proc = subprocess.Popen([find_browser(), "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run",
                                      f"--remote-debugging-port={self.port}", f"--user-data-dir={self.profile}",
                                      "--window-size=800,1000", "about:blank"],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        for _ in range(100):
            try:
                pages = json.loads(urllib.request.urlopen(f"http://127.0.0.1:{self.port}/json/list", timeout=2).read())
                page = [p for p in pages if p.get("type") == "page"][0]
                break
            except Exception:
                time.sleep(0.2)
        self.cdp = CDP(page["webSocketDebuggerUrl"])

    def open(self, url, w, h, scale, mobile):
        self.opened = (url, w, h, scale, mobile)
        self.cdp.call("Emulation.setDeviceMetricsOverride", width=w, height=h, deviceScaleFactor=scale, mobile=mobile)
        self.cdp.call("Page.enable")
        self.cdp.call("Page.navigate", url=url)

    def shot(self, last=None) -> QImage | None:
        """A screenshot. Headless Edge on some machines now and then stops drawing for
        good: then a fresh browser opens the same page and the film goes on."""
        for attempt in range(2):
            try:
                self.cdp.s.settimeout(5)
                data = self.cdp.call("Page.captureScreenshot", format="jpeg", quality=88)["data"]
                return QImage.fromData(base64.b64decode(data))
            except (TimeoutError, OSError, ConnectionError) as e:
                print("browser stalled, restarting it:", e, file=sys.stderr, flush=True)
                self.restart()
        return last

    def restart(self):
        self.close()
        self._start()
        if self.opened:
            self.open(*self.opened)
            time.sleep(2.5)
            if self.after_open:
                self.cdp.call("Runtime.evaluate", expression=self.after_open)
                time.sleep(0.5)
        if self.press:
            (px, py), (mx, my) = self.press
            self.mouse("mousePressed", px, py)
            self.mouse("mouseMoved", mx, my)

    def rect_of(self, element_id):
        r = self.cdp.call("Runtime.evaluate", returnByValue=True,
                          expression=f"JSON.stringify(document.getElementById('{element_id}').getBoundingClientRect())")
        return json.loads(r["result"]["value"])

    def mouse(self, kind, x, y):
        if kind == "mousePressed":
            self.press = ((x, y), (x, y))
        elif kind == "mouseMoved" and self.press:
            self.press = (self.press[0], (x, y))
        elif kind == "mouseReleased":
            self.press = None
        self.cdp.s.settimeout(10)
        self.cdp.call("Input.dispatchMouseEvent", type=kind, x=x, y=y, button="left",
                      buttons=1 if kind != "mouseReleased" else 0, clickCount=1, pointerType="mouse")

    def close(self):
        self.proc.kill()
        shutil.rmtree(self.profile, ignore_errors=True)


# ------------------------------------------------------------------ the film
def ease(t):
    return 4 * t ** 3 if t < 0.5 else 1 - (-2 * t + 2) ** 3 / 2


def lerp_rect(a: QRectF, b: QRectF, t: float) -> QRectF:
    return QRectF(a.x() + (b.x() - a.x()) * t, a.y() + (b.y() - a.y()) * t,
                  a.width() + (b.width() - a.width()) * t, a.height() + (b.height() - a.height()) * t)


class Film:
    def __init__(self, w, app):
        self.w, self.app = w, app
        self.full = QRectF(0, 0, W, H)
        self.cam = QRectF(self.full)
        self.cam_from = self.cam_to = QRectF(self.full)
        self.cam_t, self.cam_n = 1, 1
        self.caption, self.cap_alpha, self.cap_target = "", 0.0, ""
        self.split, self.split_to = 0.0, 0.0
        self.phone = None
        self.overlay, self.ov_alpha, self.ov_to = None, 0.0, 0.0
        self.ripples = []
        self.card = None                  # "title" / "end" / None
        self.card_alpha = 0.0
        self.frames = 0
        self.ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24",
                                    "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-", "-c:v", "libx264", "-preset", "medium",
                                    "-crf", "21", "-threads", "4", "-pix_fmt", "yuv420p", "-movflags", "+faststart", OUT],
                                   stdin=subprocess.PIPE)
        self.font_cap = QFont("Inter", 27)
        self.font_cap.setWeight(QFont.Weight.Bold)

    # ---- direction
    def rect_of(self, *widgets, pad=24) -> QRectF:
        r = QRect()
        for wd in widgets:
            top_left = wd.mapTo(self.w, QPoint(0, 0))
            r = r.united(QRect(top_left, wd.size()))
        return QRectF(r).adjusted(-pad, -pad, pad, pad)

    def look(self, target=None, frames=22):
        """Move the camera to a rectangle (expanded to 16:9, kept inside the window), or back to the whole window."""
        if target is None:
            t = QRectF(self.full)
        else:
            t = QRectF(target)
            if t.width() / t.height() > W / H:
                h = t.width() * H / W
                t = QRectF(t.x(), t.center().y() - h / 2, t.width(), h)
            else:
                w_ = t.height() * W / H
                t = QRectF(t.center().x() - w_ / 2, t.y(), w_, t.height())
            if t.width() < W / 3.2:                   # never more than 3.2x
                c = t.center()
                t = QRectF(c.x() - W / 6.4, c.y() - H / 6.4, W / 3.2, H / 3.2)
            t.moveLeft(min(max(t.x(), 0), W - t.width()))
            t.moveTop(min(max(t.y(), 0), H - t.height()))
        self.cam_from, self.cam_to, self.cam_t, self.cam_n = QRectF(self.cam), t, 0, frames

    def say(self, text):
        if text and text != self.cap_target:
            t = self.frames / FPS
            print(f"CUE {int(t // 60)}:{t % 60:04.1f}  {text}".encode("ascii", "replace").decode(), flush=True)
        self.cap_target = text

    def click(self, widget):
        c = self.rect_of(widget, pad=0).center()
        self.ripples.append((c, 0))

    # ---- one frame
    def frame(self, ticks=1):
        for _ in range(ticks):
            self.w._on_tick()
        self.app.processEvents()
        if self.cam_t < self.cam_n:
            self.cam_t += 1
            self.cam = lerp_rect(self.cam_from, self.cam_to, ease(self.cam_t / self.cam_n))
        # caption cross-fade
        if self.caption != self.cap_target:
            self.cap_alpha = max(0.0, self.cap_alpha - 0.15)
            if self.cap_alpha == 0.0:
                self.caption = self.cap_target
        elif self.caption:
            self.cap_alpha = min(1.0, self.cap_alpha + 0.12)
        self.split += (self.split_to - self.split) * 0.16 if abs(self.split_to - self.split) > 0.002 else (self.split_to - self.split)
        self.ov_alpha += (self.ov_to - self.ov_alpha) * 0.2 if abs(self.ov_to - self.ov_alpha) > 0.01 else (self.ov_to - self.ov_alpha)
        self._render()

    def _render(self):
        img = QImage(W, H, QImage.Format.Format_RGB888)
        img.fill(BG)
        p = QPainter(img)
        p.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        if self.card != "only":
            shot = self.w.grab().toImage()
            sx = shot.width() / self.w.width()
            s = ease(min(1.0, max(0.0, self.split)))
            target = lerp_rect(QRectF(0, 0, W, H), QRectF(56, 150, 1290, 1290 * H / W), s)
            src = QRectF(self.cam.x() * sx, self.cam.y() * sx, self.cam.width() * sx, self.cam.height() * sx)
            if s > 0.01:
                path = QPainterPath()
                path.addRoundedRect(target, 14 * s, 14 * s)
                p.save()
                p.setClipPath(path)
                p.drawImage(target, shot, src)
                p.restore()
            else:
                p.drawImage(target, shot, src)
            # click ripples
            for i, (c, age) in enumerate(self.ripples):
                k = age / 16
                pt = QPointF(target.x() + (c.x() - self.cam.x()) / self.cam.width() * target.width(),
                             target.y() + (c.y() - self.cam.y()) / self.cam.height() * target.height())
                col = QColor(TEAL)
                col.setAlphaF(max(0.0, 0.85 * (1 - k)))
                p.setPen(QPen(col, 5))
                p.setBrush(Qt.BrushStyle.NoBrush)
                r = 14 + 46 * k
                p.drawEllipse(pt, r, r)
                self.ripples[i] = (c, age + 1)
            self.ripples = [x for x in self.ripples if x[1] < 16]
            # the phone, sliding in from the right
            if self.phone is not None and s > 0.01:
                ph = 920
                pw = ph * self.phone.width() / self.phone.height()
                x = W + 40 - (W + 40 - (W - 120 - pw)) * s
                frame_r = QRectF(x - 14, (H - ph) / 2 - 14, pw + 28, ph + 28)
                p.setPen(Qt.PenStyle.NoPen)
                p.setBrush(QColor("#000000"))
                p.drawRoundedRect(frame_r, 52, 52)
                inner = QRectF(x, (H - ph) / 2, pw, ph)
                path = QPainterPath()
                path.addRoundedRect(inner, 40, 40)
                p.save()
                p.setClipPath(path)
                p.drawImage(inner, self.phone)
                p.restore()
        # a dialog or a page over the window
        if self.overlay is not None and not self.overlay.isNull() and self.ov_alpha > 0.01:
            dim = QColor(0, 0, 0)
            dim.setAlphaF(0.55 * self.ov_alpha)
            p.fillRect(QRectF(0, 0, W, H), dim)
            o = self.overlay
            ow = min(W * 0.8, o.width() / (o.width() / 1500 if o.width() > 1500 else 1))
            ow = min(ow, H * 0.82 * o.width() / o.height())
            oh = ow * o.height() / o.width()
            k = 0.94 + 0.06 * self.ov_alpha
            r = QRectF(W / 2 - ow * k / 2, H / 2 - oh * k / 2 - 30, ow * k, oh * k)
            p.setOpacity(self.ov_alpha)
            path = QPainterPath()
            path.addRoundedRect(r, 16, 16)
            p.save()
            p.setClipPath(path)
            p.drawImage(r, o)
            p.restore()
            p.setOpacity(1.0)
        # title / end cards
        if self.card:
            self._card(p)
        # caption pill
        if self.caption and self.cap_alpha > 0.01:
            p.setFont(self.font_cap)
            fm = p.fontMetrics()
            tw = fm.horizontalAdvance(self.caption)
            k = ease(min(1.0, max(0.0, self.split)))          # beside the phone: under the desktop
            cx = W / 2 * (1 - k) + (56 + 1290 / 2) * k
            r = QRectF(cx - tw / 2 - 34, H - 124 + 10 * k, tw + 68, 72)
            # a light card on the dark app: readable from the back of the room
            p.setPen(Qt.PenStyle.NoPen)
            sh = QColor(0, 0, 0)
            sh.setAlphaF(0.45 * self.cap_alpha)
            p.setBrush(sh)
            p.drawRoundedRect(r.translated(0, 5).adjusted(-3, -3, 3, 3), 20, 20)
            bg = QColor("#f7fafc")
            bg.setAlphaF(0.97 * self.cap_alpha)
            p.setBrush(bg)
            p.drawRoundedRect(r, 18, 18)
            bar = QColor("#0d9483")
            bar.setAlphaF(self.cap_alpha)
            p.setBrush(bar)
            p.drawRoundedRect(QRectF(r.x() + 10, r.y() + 14, 7, r.height() - 28), 3.5, 3.5)
            col = QColor("#0b1418")
            col.setAlphaF(self.cap_alpha)
            p.setPen(col)
            p.drawText(r, Qt.AlignmentFlag.AlignCenter, self.caption)
        p.end()
        ptr = img.constBits()
        self.ff.stdin.write(bytes(ptr)[: W * H * 3] if img.bytesPerLine() == W * 3 else
                            b"".join(bytes(img.constScanLine(y))[: W * 3] for y in range(H)))
        self.frames += 1

    def _card(self, p):
        a = self.card_alpha
        if self.card != "only":
            bg = QColor(BG)
            bg.setAlphaF(a)
            p.fillRect(QRectF(0, 0, W, H), bg)
        else:
            p.fillRect(QRectF(0, 0, W, H), BG)
        p.setOpacity(a if self.card != "only" else 1.0)
        logo = QImage(os.path.join(ROOT, "assets", "icon@2x.png"))
        p.drawImage(QRectF(W / 2 - 110, 250, 220, 220), logo)
        f = QFont("Space Grotesk", 96)
        f.setWeight(QFont.Weight.Bold)
        p.setFont(f)
        p.setPen(QColor("#e6edf3"))
        p.drawText(QRectF(0, 500, W, 140), Qt.AlignmentFlag.AlignCenter, "Rovust" if self.card_text is None else self.card_text)
        f2 = QFont("Inter", 30)
        p.setFont(f2)
        p.setPen(QColor("#92a1af"))
        p.drawText(QRectF(0, 650, W, 60), Qt.AlignmentFlag.AlignCenter, self.card_sub)
        p.setOpacity(1.0)

    def hold(self, seconds, ticks=1, each=None):
        n = int(seconds * FPS)
        for i in range(n):
            if each:
                each(i, n)
            self.frame(ticks)

    def close(self):
        self.ff.stdin.close()
        self.ff.wait()


def main():
    from sim.qtui.i18n import LANG
    from sim.qtui.main_window import ConfirmDialog, MainWindow
    from sim.qtui.i18n import tr
    from sim.qtui.theme_qt import load_fonts

    settings = QSettings("RoboticsTeamProject", "RoverSimulator")
    saved = {k: settings.value(k) for k in ("lang", "dark", "sideCollapsed")}
    work = tempfile.mkdtemp(prefix="rovust-video-reports-")
    R.REPORTS_DIR, R.INDEX_CSV, R.PENDING_PATH = work, os.path.join(work, "missions.csv"), os.path.join(work, "pending.json")
    app = QApplication.instance() or QApplication([])
    load_fonts()
    # off screen, Qt has no Windows font fallback: give it the symbol font for ✕ △ ○ □
    from PySide6.QtGui import QFontDatabase
    sym = os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "seguisym.ttf")
    if os.path.exists(sym):
        QFontDatabase.addApplicationFont(sym)
        for fam in ("Inter", "IBM Plex Sans Arabic", "Chakra Petch", "Segoe UI", "Space Grotesk"):
            QFont.insertSubstitutions(fam, ["Segoe UI Symbol"])
    from sim.qtui.theme_qt import apply_theme
    apply_theme(app, True)
    LANG.set("en")
    w = MainWindow()
    w.uploader.cfg = {"upload_url": "", "auto_send": False}      # nothing leaves this computer
    w.uploader.pending = []
    if getattr(w, "pad", None) is not None and getattr(w.pad, "available", False):
        w.pad.timer.stop()                                       # a real controller must not join the film
    w.timer.stop()
    w.resize(W, H)
    w.show()
    w.act_dark.setChecked(True)
    for _ in range(5):
        w._on_tick()
        app.processEvents()

    print('window', w.width(), w.height(), 'grab', w.grab().size().toTuple(), flush=True)
    browser = Browser()                     # started now, while the computer is still quiet
    film = Film(w, app)
    film.card_text, film.card_sub = None, "Multi-Environment Autonomous Exploration Rover"
    try:
        # ---------------------------------------------------------- title
        film.card, film.card_alpha = "only", 1.0
        film.hold(3.6)
        film.card = "fade"
        film.hold(0.8, each=lambda i, n: setattr(film, "card_alpha", 1 - (i + 1) / n))
        film.card = None

        # ---------------------------------------------------------- setup and start
        film.say("Pick a world, an exploration strategy and a localisation mode")
        film.look(film.rect_of(w.setup, pad=30))
        film.hold(1.6)
        w.setup.env.setCurrentIndex(0)
        w.setup.strategy.setCurrentIndex(2)
        w.setup.mode.setCurrentIndex(0)
        w.setup.loss.setCurrentIndex(w.setup.loss.findData("home"))
        film.hold(1.6)
        film.click(w.setup.start_btn)
        film.hold(0.4)
        w.setup.start_btn.click()
        w.speed = 1
        film.look(None, 26)
        film.say("It stands still to learn its gyro bias, then turns once to scan with the sonar ring")
        film.hold(5.5)

        # ---------------------------------------------------------- exploring
        film.say("Left: the real cave. Right: the map the rover builds by itself")
        film.look(film.rect_of(w.map_world, w.map_belief, pad=16), 30)
        film.hold(14, ticks=2)
        film.say("The AI picks the most promising unknown area and plans a path to it with A*")
        film.look(film.rect_of(w.map_belief, pad=10), 26)
        film.hold(10, ticks=2)

        # ---------------------------------------------------------- layers
        chips = list(w.setup.layer_boxes.values())
        film.say("Map layers: sonar, IR beams, AI terrain, frontiers")
        film.look(film.rect_of(*chips, pad=40), 24)
        film.hold(1.2)
        for key in ("sonar", "ir", "terrain"):
            b = w.setup.layer_boxes[key]
            film.click(b)
            b.click()
            film.hold(0.7)
        film.look(film.rect_of(w.map_world, w.map_belief, pad=16), 24)
        film.hold(1.8)
        for key in ("sonar", "ir", "terrain"):
            w.setup.layer_boxes[key].click()
        film.hold(2.2)

        # ---------------------------------------------------------- motor loop
        w.tabs.setCurrentIndex(1)
        film.say("Each wheel: encoder → PID → PWM, live")
        film.look(film.rect_of(w.telemetry_dock, pad=10), 26)
        film.hold(7)

        # ---------------------------------------------------------- break a sensor
        w.tabs.setCurrentIndex(0)
        film.say("Break a sensor: the AI fault detector drops it, the rover keeps going")
        film.look(film.rect_of(w.telemetry_dock, pad=10), 20)
        film.hold(1.5)
        from PySide6.QtWidgets import QPushButton
        cell = w.sensors_tab.table.cellWidget(0, 3)
        dead = [b for b in cell.findChildren(QPushButton) if b.property("mode") == "dead"][0]
        film.look(film.rect_of(cell, pad=140), 20)
        film.hold(1.2)
        film.click(dead)
        dead.click()
        film.hold(3.5, ticks=2)
        film.look(None, 26)
        film.hold(3, ticks=2)

        # ---------------------------------------------------------- headlights
        film.say("Too dark for the camera? Headlights on: the AI sees the ground again")
        film.look(film.rect_of(w.b_lights, pad=140), 20)
        film.hold(1.0)
        film.click(w.b_lights)
        w.act_lights.setChecked(not w.act_lights.isChecked())
        film.hold(1.6)
        film.look(None, 22)
        film.hold(2.4, ticks=2)

        # ---------------------------------------------------------- the estimate
        film.say("Green: the fused estimate · Red: what the encoders alone would believe")
        film.look(film.rect_of(w.map_belief, pad=0), 26)
        film.hold(6, ticks=3)

        # ---------------------------------------------------------- statistics, events, the large map
        w.tabs.setCurrentIndex(2)
        film.say("Live statistics: coverage, distance, energy, bumps")
        film.look(film.rect_of(w.telemetry_dock, pad=10), 24)
        film.hold(6, ticks=2)
        w.tabs.setCurrentIndex(4)
        film.say("Every alert is logged with its time")
        film.hold(4, ticks=2)
        from sim.qtui.popup import MapPopup
        pop = MapPopup(w, "Robot's map (built from its own sensors)", w.mission, "belief", w.setup.layers())
        pop.resize(1000, 760)
        pop.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        pop.show()
        film.click(w.map_belief)
        film.look(None, 18)
        film.say("Click a map to open it large")

        def popup_frame(i, n):
            pop.refresh()
            app.processEvents()
            film.overlay = pop.grab().toImage()
        film.ov_to = 1.0
        film.hold(6, ticks=2, each=popup_frame)
        film.ov_to = 0.0
        film.hold(0.6, ticks=2, each=popup_frame)
        pop.close()
        film.overlay = None

        # ---------------------------------------------------------- the radio fails
        w.tabs.setCurrentIndex(3)
        film.say("The radio weakens with distance and rock")
        film.look(None, 24)
        w.speed = 8
        n = 0
        while w.mission.link.state != "lost" and n < 6 * FPS:
            film.frame()
            n += 1
        while w.mission.link.state != "lost" and not w.mission.done and w.mission.time < 600:
            w.mission.step()                                  # off camera, until the link is really gone
        w.speed = 1
        w.setup.mode.setCurrentIndex(1)                       # someone is driving over the radio now
        film.look(film.rect_of(w.telemetry_dock, pad=10), 24)
        film.say("Link lost for 3 s: the rover drives itself back into range")
        n = 0
        while not w.mission.link_fallback and n < 5 * FPS:
            film.frame()
            n += 1
        w.speed = 2
        film.look(None, 26)
        n = 0
        while w.mission.link.state == "lost" and n < 12 * FPS:
            film.frame()
            n += 1
        film.hold(1.5, ticks=1)
        w.mission.operator_drive(0.0, 0.0, source="console")  # the operator is back: stop returning
        w.speed = 1

        # ---------------------------------------------------------- the phone
        film.say("Drive it from a phone: open the console and scan the QR code")
        w.b_console.setChecked(True)
        film.hold(0.6)
        film.look(film.rect_of(w.setup.qr, pad=80), 24)
        film.hold(3)
        film.look(None, 20)
        if w.server is not None:
            browser.open(f"http://127.0.0.1:{w.server.port}/", 390, 844, 2, True)
            t0 = time.time()
            while time.time() - t0 < 4:
                w._on_tick()
                app.processEvents()
                time.sleep(0.03)
            browser.after_open = "if (document.documentElement.lang === 'ar') document.getElementById('langbtn').click()"
            browser.cdp.call("Runtime.evaluate", expression=browser.after_open)
            time.sleep(0.6)
            film.phone = browser.shot() or QImage(780, 1688, QImage.Format.Format_RGB888)
            film.split_to = 1.0
            film.say("The phone and the desktop, live: the same rover over the same radio")
            stick = browser.rect_of("stick")
            cx, cy = stick["x"] + stick["width"] / 2, stick["y"] + stick["height"] / 2
            r = stick["width"] / 2 * 0.5
            moves = [(0, 0, 2.0), (0.0, 0.9, 3.5), (0.9, 0.0, 3.5), (0.0, -0.9, 3.5), (-0.8, 0.5, 3.5), (0.6, 0.6, 3.5), (0.0, 0.9, 3.5), (0, 0, 1.6)]
            pressed = False
            for mx, my, secs in moves:
                if mx or my:
                    px, py = cx + mx * r, cy - my * r
                    if not pressed:
                        browser.mouse("mousePressed", cx, cy)
                        pressed = True
                    browser.mouse("mouseMoved", px, py)
                elif pressed:
                    browser.mouse("mouseReleased", cx, cy)
                    pressed = False
                if mx == 0.9:
                    film.say("Assisted mode: drive anywhere, the safety layers still stop it at a wall")
                for i in range(int(secs * FPS)):
                    if i % 2 == 0:
                        film.phone = browser.shot(film.phone)
                    film.frame()
            film.split_to = 0.0
            film.hold(1.0)
            film.phone = None

        # ---------------------------------------------------------- the game controller
        w.setup.set_pad(True, "DualShock 4 Wireless Controller")
        w.side_scroll.ensureWidgetVisible(w.setup.pad_row)
        film.say("Or a game controller: Cross for gas, Triangle to reverse, the stick steers")
        film.look(film.rect_of(w.setup.pad_row, pad=60), 24)
        film.hold(1.2)
        plan = [(0.0, 0.0, "a", 1.4, (0.7, 0.0)), (0.6, 0.0, "a", 1.6, (0.7, 0.6)), (-0.6, 0.0, "a", 1.4, (0.6, -0.6)),
                (0.0, 0.0, "y", 1.4, (-0.5, 0.0)), (0.0, 0.0, "", 0.8, (0.0, 0.0))]
        for sx, sy, held, secs, (fwd, turn) in plan:
            w.setup.pad_view.set_state(sx, sy, held)
            for i in range(int(secs * FPS)):
                w._pad_drive(fwd, turn)
                film.frame()
        w._pad_drive(0.0, 0.0)
        film.look(None, 24)
        film.hold(1.5)

        # ---------------------------------------------------------- fast forward
        w.setup.mode.setCurrentIndex(0)
        w.speed = 16
        film.say("×16: on its own again, the rover keeps mapping the cave")
        film.hold(9)
        w.speed = 1

        # ---------------------------------------------------------- stop and report
        film.say("Stop asks first: with a report, without one, or cancel")
        film.look(film.rect_of(w.b_stop, pad=120), 20)
        film.hold(1.0)
        film.click(w.b_stop)
        film.hold(0.5)
        dlg = ConfirmDialog(tr("cfStopTitle"), tr("cfStopMsg"), tr("cfStopSend"), tr("cfStopPlain"), w)
        dlg.adjustSize()
        dlg.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
        dlg.show()
        app.processEvents()
        film.overlay = dlg.grab().toImage()
        dlg.close()
        film.look(None, 16)
        film.ov_to = 1.0
        film.hold(2.4)
        film.ov_to = 0.0
        film.hold(0.5)
        w._ask_report = lambda kind: "send"
        w.stop_mission()
        film.hold(0.8)
        reports = [os.path.join(dp, "report.html") for dp, _, fs in os.walk(work) if "report.html" in fs]
        if reports:
            url = "file:///" + urllib.parse.quote(reports[-1].replace("\\", "/"), safe="/:")
            browser.open(url, 1400, 1000, 1, False)
            time.sleep(1.5)
            film.overlay = browser.shot() or QImage()
            film.say("Maps and numbers in one report, sent to the team's Drive folder")
            film.ov_to = 1.0
            film.hold(4.0, ticks=0)
            film.ov_to = 0.0
            film.hold(0.6, ticks=0)
        film.overlay = None

        # ---------------------------------------------------------- the other worlds
        w.setup.mode.setCurrentIndex(0)                           # exploring by itself
        for idx, text in ((1, "Mars: craters, sand dunes, no compass, every command 2 s late"),
                          (2, "Underwater: currents push it sideways, a DVL instead of wheels")):
            w.setup.env.setCurrentIndex(idx)
            w.start_mission()
            for _ in range(2600):                                 # explore off camera first
                w.mission.step()
            w.speed = 4
            film.say(text)
            film.look(film.rect_of(w.map_world, w.map_belief, pad=16), 1)
            film.hold(8.0)
        w.speed = 1

        # ---------------------------------------------------------- Arabic
        film.say("English / Egyptian Arabic, right to left")
        film.look(None, 18)
        LANG.set("ar")
        film.hold(6)
        LANG.set("en")

        # ---------------------------------------------------------- end
        film.say("")
        film.card, film.card_alpha = "fade", 0.0
        film.card_sub = "Cave · Mars · Underwater"
        film.hold(1.0, each=lambda i, n: setattr(film, "card_alpha", (i + 1) / n))
        film.card = "only"
        film.hold(2.5, ticks=0)
    finally:
        film.close()
        browser.close()
        if w.server is not None:
            w.b_console.setChecked(False)
        w.close()
        for k, v in saved.items():
            if v is not None:
                settings.setValue(k, v)
        shutil.rmtree(work, ignore_errors=True)
    print(f"{OUT}  {film.frames / FPS:.1f} s  {os.path.getsize(OUT) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
