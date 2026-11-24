"""Regenerate the images that show the rover's name (sim/meta.py: ROVER_NAME).

    python tools/make_media.py            everything
    python tools/make_media.py about gif  only the named parts: about, report, console, gif, app

Writes into docs/screenshots and docs/media:
    about.png                 the About dialog
    report.png                a mission report page
    console_phone_light.jpg   the operator console at phone size, light
    console_tablet_dark.jpg   the operator console at tablet size, dark
    demo.gif                  the README animation: true world next to the robot's map
    app_*.png, main_*.png,    the desktop application (part "app"): start screen, running in
    tab_*.png, controller.png English / Arabic, light / dark, each bottom tab, the map pop-up,
    map_popup.png, guide.png  the controller card, mission over, the user guide
    mission_over.png

The "app" part restores the saved language, theme and panel state afterwards
and never sends a report.

Nothing is uploaded: reports are written to a temporary folder. The report and
console pictures need Edge or Chrome (same as build_presentation.py).
"""
from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from PIL import Image
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont, QImage
from PySide6.QtWidgets import QApplication, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from build_presentation import find_browser
from sim import meta as T
from sim import report as R
from sim.ai.brain import AIBrain
from sim.mission import Mission
from sim.qtui.mapview import MapWidget
from sim.qtui.panels import AboutDialog, SetupPanel
from sim.qtui.theme_qt import apply_theme
from sim.teleop.server import ConsoleServer

SHOTS = os.path.join(ROOT, "docs", "screenshots")
MEDIA = os.path.join(ROOT, "docs", "media")


def new_mission(env, strategy, seed=1):
    ai = AIBrain()
    m = Mission(env, strategy, seed=seed, localisation="fused", ai=ai)
    ai.attach(m)
    return m


def show_offscreen(w: QWidget):
    """Lay the widget out as if it were shown, without putting it on the screen."""
    w.setAttribute(Qt.WidgetAttribute.WA_DontShowOnScreen, True)
    w.show()
    QApplication.processEvents()


def browser_shot(url: str, out: str, width: int, height: int, scale: float = 1.0, dark: bool = False,
                 wait_ms: int = 4000, keep_alive=None) -> bool:
    """Screenshot a page with headless Edge/Chrome. ``keep_alive`` is called
    repeatedly while the browser runs (the console needs the mission stepping)."""
    browser = find_browser()
    if not browser:
        print("no Edge/Chrome found: skipping", os.path.basename(out), file=sys.stderr)
        return False
    profile = tempfile.mkdtemp(prefix="rovust-media-")
    cmd = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--disable-extensions",
           f"--user-data-dir={profile}", f"--window-size={width},{height}", f"--force-device-scale-factor={scale}",
           "--run-all-compositor-stages-before-draw", f"--screenshot={out}"]
    if wait_ms:
        cmd.append(f"--virtual-time-budget={wait_ms}")
    if dark:
        cmd += ["--force-dark-mode", "--blink-settings=preferredColorScheme=0"]
    if os.path.exists(out):
        os.remove(out)
    proc = subprocess.Popen(cmd + [url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    t0 = time.time()
    while proc.poll() is None and time.time() - t0 < 120:
        if keep_alive:
            keep_alive()
        time.sleep(0.02)
    if proc.poll() is None:
        proc.kill()
    shutil.rmtree(profile, ignore_errors=True)
    return os.path.exists(out)


def to_jpg(png: str, jpg: str):
    Image.open(png).convert("RGB").save(jpg, quality=88, optimize=True)
    os.remove(png)


# ------------------------------------------------------------------ parts
def make_about():
    dlg = AboutDialog()
    show_offscreen(dlg)
    out = os.path.join(SHOTS, "about.png")
    dlg.grab().save(out, "PNG")
    dlg.close()
    print("about:", os.path.relpath(out, ROOT))


def make_report(layers):
    m = new_mission("underwater", "dfs")
    for _ in range(3840):                      # 192 s at 20 Hz, then the operator stops it
        m.step()
        if m.done:
            break
    m.stop()
    images = {}
    for kind, title in (("world", "TRUE WORLD  (the robot never sees this)"),
                        ("belief", "ROBOT'S MAP  (built from its own sensors)")):
        w = MapWidget(title)
        w.resize(566, 398)
        w.banner_enabled = False
        w.set_mission(m, kind, layers)
        show_offscreen(w)
        tmp = os.path.join(tempfile.gettempdir(), f"rovust-{kind}.png")
        w.grab().save(tmp, "PNG")
        images["true_world.png" if kind == "world" else "robot_map.png"] = open(tmp, "rb").read()
        os.remove(tmp)
        w.close()
    work = tempfile.mkdtemp(prefix="rovust-report-")
    R.REPORTS_DIR, R.INDEX_CSV = work, os.path.join(work, "missions.csv")     # keep the real reports/ untouched
    folder = R.build_report(m, images)
    out = os.path.join(SHOTS, "report.png")
    url = "file:///" + os.path.join(folder, "report.html").replace("\\", "/").replace(" ", "%20").replace("#", "%23")
    ok = browser_shot(url, out, 1000, 1500)
    shutil.rmtree(work, ignore_errors=True)
    if ok:
        print("report:", os.path.relpath(out, ROOT))


def make_console():
    m = new_mission("cave", "utility")
    m.mode = "assisted"
    m.robot.headlights = True
    for _ in range(200):
        m.step()
    import socket

    def free_port():
        with socket.socket() as sk:          # another local server may already use a fixed port
            sk.bind(("127.0.0.1", 0))
            return sk.getsockname()[1]
    port, wait_port = free_port(), free_port()
    server = ConsoleServer(lambda: m, port=port)
    server.start()

    # The browser takes its picture when the page has finished loading. This
    # answers one request slowly, so the console has a few real seconds to
    # fetch its state, map and camera first.
    class Slow(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            time.sleep(5)
            self.send_response(204)
            self.end_headers()

    slow = ThreadingHTTPServer(("127.0.0.1", wait_port), Slow)
    threading.Thread(target=slow.serve_forever, daemon=True).start()
    # A headless browser window cannot be narrower than about 500 px, so the
    # console is shown in a frame of the wanted size and the picture cropped to it.
    frame = os.path.join(tempfile.gettempdir(), "rovust-console-frame.html")
    try:
        for name, w, h, scale, dark, out_w in (("console_phone_light", 390, 844, 2.0, False, 780),
                                               ("console_tablet_dark", 1100, 764, 1.0, True, 800)):
            with open(frame, "w", encoding="utf-8") as f:
                f.write(f'<!doctype html><meta name="color-scheme" content="dark light"><body style="margin:0">'
                        f'<iframe src="http://127.0.0.1:{port}/" style="border:0;display:block;width:{w}px;height:{h}px">'
                        f'</iframe><img src="http://127.0.0.1:{wait_port}/wait" width="0" height="0">')
            png = os.path.join(SHOTS, name + ".png")
            url = "file:///" + frame.replace("\\", "/")
            if browser_shot(url, png, max(w, 600), h, scale, dark, wait_ms=0):
                im = Image.open(png)
                im = im.crop((0, 0, int(w * scale), int(h * scale)))
                if im.width != out_w:
                    im = im.resize((out_w, round(im.height * out_w / im.width)), Image.Resampling.LANCZOS)
                im.save(png)
                to_jpg(png, os.path.join(SHOTS, name + ".jpg"))
                print("console:", os.path.relpath(os.path.join(SHOTS, name + ".jpg"), ROOT))
    finally:
        server.stop()
        slow.shutdown()
        slow.server_close()
        if os.path.exists(frame):
            os.remove(frame)


def make_gif(layers, frames=110, steps_per_frame=40):
    m = new_mission("cave", "utility")
    m.robot.headlights = True
    box = QWidget()
    box.setFixedSize(850, 326)
    box.setStyleSheet("background:#ffffff;")
    v = QVBoxLayout(box)
    v.setContentsMargins(0, 2, 0, 0)
    v.setSpacing(0)
    head = QLabel()
    head.setFont(QFont(box.font().family(), 9, QFont.Weight.DemiBold))
    head.setStyleSheet("color:#1b1f24; padding:2px 6px;")
    head.setFixedHeight(22)
    v.addWidget(head)
    row = QHBoxLayout()
    row.setSpacing(0)
    views = []
    for kind, title in (("world", "TRUE WORLD"), ("belief", "ROBOT'S MAP")):
        w = MapWidget(title)
        w.set_mission(m, kind, layers)
        row.addWidget(w)
        views.append(w)
    v.addLayout(row)
    show_offscreen(box)
    shots = []
    for _ in range(frames):
        for _ in range(steps_per_frame):
            if not m.done:
                m.step()
        head.setText(f"{T.ROVER_NAME}  -  cave, utility explorer     t = {m.time:4.0f} s    "
                     f"coverage {m.coverage():4.0%}    behaviour {m.arbiter.active_name.upper()}")
        for w in views:
            w.repaint()
        QApplication.processEvents()
        img = box.grab().toImage().convertToFormat(QImage.Format.Format_RGB888)
        shot = Image.frombytes("RGB", (img.width(), img.height()), bytes(img.constBits()), "raw", "RGB",
                               img.bytesPerLine())
        if shot.size != (850, 326):                # a scaled display grabs more pixels than the layout has
            shot = shot.resize((850, 326), Image.Resampling.LANCZOS)
        shots.append(shot)
    box.close()
    # one shared palette keeps the file small and stops the colours flickering between frames
    pal = shots[len(shots) // 2].quantize(colors=128, method=Image.Quantize.MEDIANCUT)
    quant = [s.quantize(palette=pal, dither=Image.Dither.NONE) for s in shots]
    out = os.path.join(MEDIA, "demo.gif")
    quant[0].save(out, save_all=True, append_images=quant[1:], duration=120, loop=0, optimize=True)
    print("gif:", os.path.relpath(out, ROOT), f"{os.path.getsize(out) / 1e6:.1f} MB,", f"mission ended at t = {m.time:.0f} s")


def make_app():
    """Screenshots of the desktop application, off-screen, with no report sent."""
    from PySide6.QtCore import QSettings
    from sim.qtui.i18n import LANG
    from sim.qtui.main_window import MainWindow
    from sim.qtui.panels import GuideDialog
    from sim.qtui.popup import MapPopup
    settings = QSettings("RoboticsTeamProject", "RoverSimulator")
    saved = {k: settings.value(k) for k in ("lang", "dark", "sideCollapsed")}
    app = QApplication.instance()
    w = MainWindow()
    w.uploader.cfg["auto_send"] = False          # pictures only: nothing goes to the team's Drive
    w.resize(1600, 950)
    w.move(-4000, 0)
    w.show()

    def run(n=1):
        for _ in range(n):
            w._on_tick()
            app.processEvents()

    def save(widget, name):
        out = os.path.join(SHOTS, name)
        widget.grab().save(out, "PNG")
        print("app:", os.path.relpath(out, ROOT))

    try:
        LANG.set("en")
        w.act_dark.setChecked(False)
        run(5)
        save(w, "app_start.png")                      # before the first mission: only New mission is live
        # cave, utility explorer, exploring by itself for a few minutes
        w.setup.env.setCurrentIndex(0)
        w.setup.strategy.setCurrentIndex(2)
        w.setup.mode.setCurrentIndex(0)
        w.start_mission()
        w.set_speed(16)
        while w.mission.time < 330 and not w.mission.done:
            run(20)
        w.set_speed(1)
        w.tabs.setCurrentIndex(0)
        run(6)
        save(w, "main_light.png")
        for i, name in ((1, "tab_motor.png"), (2, "tab_stats.png"), (4, "tab_events.png")):
            w.tabs.setCurrentIndex(i)
            run(6)
            save(w.telemetry_dock, name)
        # dark, someone driving from the phone: assisted, console open with its QR code, radio tab
        w.setup.mode.setCurrentIndex(1)
        w.act_dark.setChecked(True)
        w.setup.server_btn.setChecked(True)
        run(10)
        w.tabs.setCurrentIndex(3)
        run(6)
        save(w, "main_dark_radio.png")
        w.setup.server_btn.setChecked(False)
        # a controller, as the setup panel shows it while ✕ is held and the stick pushed
        w.setup.set_pad(True, "Twin USB Joystick")
        w.setup.pad_view.set_state(0.55, 0.45, "a")
        w.side_scroll.ensureWidgetVisible(w.setup.pad_row)
        run(3)
        save(w.setup.pad_row, "controller.png")
        # Arabic, back to exploring by itself
        w.setup.mode.setCurrentIndex(0)
        LANG.set("ar")
        w.tabs.setCurrentIndex(0)
        run(8)
        save(w, "main_ar.png")
        LANG.set("en")
        w.act_dark.setChecked(False)
        run(4)
        pop = MapPopup(w, "Robot's map (built from its own sensors)", w.mission, "belief", w.setup.layers())
        pop.resize(1000, 760)
        pop.move(-4000, 0)
        pop.show()
        pop.refresh()
        app.processEvents()
        save(pop, "map_popup.png")
        pop.close()
        dlg = GuideDialog(w)
        dlg.move(-4000, 0)
        dlg.show()
        app.processEvents()
        save(dlg, "guide.png")
        dlg.close()
        w.stop_mission()
        for _ in range(4):                            # alerts wait 0.8 s of real time before they show
            run(3)
            time.sleep(0.4)
        save(w, "mission_over.png")
    finally:
        w.close()
        for k, v in saved.items():
            if v is None:
                settings.remove(k)
            else:
                settings.setValue(k, v)


def main():
    parts = [a for a in sys.argv[1:] if not a.startswith("-")] or ["about", "report", "console", "gif", "app"]
    app = QApplication.instance() or QApplication(sys.argv)
    apply_theme(app, False)
    layers = SetupPanel().layers()
    if "about" in parts:
        make_about()
    if "report" in parts:
        make_report(layers)
    if "console" in parts:
        make_console()
    if "gif" in parts:
        make_gif(layers)
    if "app" in parts:
        make_app()
    return 0


if __name__ == "__main__":
    sys.exit(main())
