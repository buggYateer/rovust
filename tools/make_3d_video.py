"""The 3D video of the rover: docs/model/rovust_3d_video.html, filmed frame by frame.

    python tools/make_3d_video.py            -> docs/media/rovust_3d.mp4

The page draws every frame from the time alone (window.__seek(t)), so the
video is the same every run. Headless Edge renders it at 1920x1080, 30 fps,
straight into ffmpeg. Needs ffmpeg on the PATH, Edge, and the internet
(three.js and the fonts load from their CDNs). Takes about ten minutes.
"""
from __future__ import annotations

import os
import pathlib
import subprocess
import sys
import tempfile

from playwright.sync_api import sync_playwright

ROOT = pathlib.Path(__file__).resolve().parents[1]
PAGE = ROOT / "docs" / "model" / "rovust_3d_video.html"
OUT = ROOT / "docs" / "media" / "rovust_3d.mp4"
FPS = 30


def main(stills: list[float] | None = None):
    url = PAGE.as_uri() + "?rec=1"
    with sync_playwright() as p:
        b = p.chromium.launch(channel="msedge", headless=True, args=["--ignore-gpu-blocklist"])
        pg = b.new_page(viewport={"width": 1920, "height": 1080})
        pg.goto(url, wait_until="networkidle")
        pg.wait_for_function("window.THREE && window.__seek && document.fonts.status === 'loaded'", timeout=60000)
        if stills:                                   # python tools/make_3d_video.py 9 40 70  -> a few frames to look at
            for t in stills:
                pg.evaluate(f"window.__seek({t})")
                pg.screenshot(path=str(ROOT / f"still_{t:05.1f}.jpg"), type="jpeg", quality=85)
            b.close()
            return
        n = int(pg.evaluate("window.__total") * FPS)
        raw = pathlib.Path(tempfile.gettempdir()) / "rovust_3d_raw.mp4"
        ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "image2pipe", "-framerate", str(FPS), "-c:v", "mjpeg", "-i", "-",
                               "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "20", str(raw)], stdin=subprocess.PIPE)
        for i in range(n):
            pg.evaluate(f"window.__seek({i / FPS})")
            ff.stdin.write(pg.screenshot(type="jpeg", quality=92))
            if i % 300 == 0:
                print(f"frame {i} / {n}", flush=True)
        ff.stdin.close()
        ff.wait()
        b.close()
    # the copy in the repo and the presentation: smaller, same picture
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(raw), "-c:v", "libx264", "-crf", "26", "-preset", "slow",
                    "-pix_fmt", "yuv420p", "-movflags", "+faststart", str(OUT)], check=True)
    os.remove(raw)
    print("video:", OUT.relative_to(ROOT), f"{OUT.stat().st_size / 1e6:.1f} MB")


if __name__ == "__main__":
    main([float(a) for a in sys.argv[1:]] or None)
