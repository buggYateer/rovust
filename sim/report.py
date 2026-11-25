"""Mission reports: a self-contained HTML page with the statistics, both maps
and the sensor / link state, saved under reports/ and (optionally) uploaded
to the team's shared Google Drive folder through a small Apps Script bridge.

Folder name:  Mission #<n> - <title>
where <title> is a name the operator typed when sending, or by default
<YYYY-MM-DD HH-MM-SS> - <environment> (<machine>).

The number is assigned by the Drive bridge when the report is uploaded (it
looks at the folders already in the shared folder and takes the next one),
so numbers are unique across the whole team. Until then the local copy is
called "Mission #new - ...". Every report also carries the run's ``key``:
reports of the same run (one sent mid-mission, one at the end) get the
same number from the bridge.

Upload is fire-and-forget with a local queue: a report that cannot be sent
(no network, bridge not configured) stays in reports/pending.json and is
retried every 30 s and at the next start, so nothing is lost when the laptop
is offline during the demo.
"""
from __future__ import annotations

import base64
import getpass
import html
import json
import os
import platform
import re
import socket
import threading
import urllib.error
import urllib.request
from datetime import datetime

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPORTS_DIR = os.path.join(ROOT, "reports")
CONFIG_PATH = os.path.join(ROOT, "report_config.json")
PENDING_PATH = os.path.join(REPORTS_DIR, "pending.json")
INDEX_CSV = os.path.join(REPORTS_DIR, "missions.csv")

from . import meta as T


# ------------------------------------------------------------------ config
def load_config() -> dict:
    """report_config.json lives in the repository so every teammate gets the
    same bridge URL. {"upload_url": "https://script.google.com/.../exec",
    "auto_send": true}"""
    try:
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"upload_url": "", "auto_send": True}


def save_config(cfg: dict):
    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(cfg, f, indent=2)


# ------------------------------------------------------------------ build
def next_mission_number() -> int:
    os.makedirs(REPORTS_DIR, exist_ok=True)
    n = 0
    for name in os.listdir(REPORTS_DIR):
        if name.startswith("Mission #"):
            try:
                n = max(n, int(name[9:].split(" ")[0]))
            except ValueError:
                pass
    return n + 1


def machine_tag() -> str:
    try:
        return getpass.getuser()
    except Exception:
        return platform.node() or "pc"


PENDING_NUMBER = "new"


_BAD_CHARS = re.compile(r'[<>:"/\|?*\x00-\x1f]')


def default_title(mission, stamp: datetime | None = None) -> str:
    """The automatic report title: <date time> - <environment> (<machine>)."""
    stamp = stamp or datetime.now()
    return f"{stamp.strftime('%Y-%m-%d %H-%M-%S')} - {mission.cfg.name} ({machine_tag()})"


def clean_title(title: str | None) -> str:
    """Make a typed title safe as a folder name (Windows forbids the characters < > : " / | ? * and backslash);
    returns "" when nothing usable is left."""
    t = _BAD_CHARS.sub("", title or "").strip(" .")
    return " ".join(t.split())[:80]


def build_report(mission, images: dict[str, bytes], extra: dict | None = None, title: str | None = None,
                 key: str = "") -> str:
    """Write the report folder and return its path. ``images`` maps a file
    name (true_world.png, robot_map.png, ...) to PNG bytes. ``title`` is the
    operator's name for the report (default: date, environment, machine).
    The mission number stays "new" until the Drive bridge assigns one."""
    n = PENDING_NUMBER
    stamp = datetime.now()
    title = clean_title(title) or default_title(mission, stamp)
    folder = os.path.join(REPORTS_DIR, f"Mission #{n} - {title}")
    k = 2
    while os.path.exists(folder):       # two reports in the same second: never overwrite one
        folder = os.path.join(REPORTS_DIR, f"Mission #{n} - {title} ({k})")
        k += 1
    os.makedirs(folder, exist_ok=True)

    metrics = mission.metrics()
    metrics.update({
        "mission_number": n, "mission_key": key, "title": title, "timestamp": stamp.isoformat(timespec="seconds"), "machine": machine_tag(),
        "localisation": mission.estimator.mode, "mode": mission.mode, "on_link_loss": mission.on_link_loss,
        "link_delivered": mission.link.delivered, "link_dropped": mission.link.dropped,
        "link_losses": mission.stats.get("link_losses", 0), "end_reason": mission.end_reason(),
        "ai": mission.ai is not None,
        "terrain_accuracy": round(mission.ai.terrain_accuracy_live, 3) if (mission.ai and mission.ai.terrain) else None,
        "faulty_sensors": [s.name for s in mission.robot.sensors.sensors if s.fault != "ok" or not s.healthy],
    })
    if extra:
        metrics.update(extra)
    for name, data in images.items():
        with open(os.path.join(folder, name), "wb") as f:
            f.write(data)
    with open(os.path.join(folder, "metrics.json"), "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=2)
    with open(os.path.join(folder, "report.html"), "w", encoding="utf-8") as f:
        f.write(render_html(mission, metrics, images))
    _append_index(metrics)
    return folder


def _append_index(m: dict):
    cols = ["mission_number", "timestamp", "machine", "env", "strategy", "localisation", "mode", "seed", "status",
            "time_s", "coverage", "path_length_m", "backtracks", "collisions", "bumps", "cliff_events", "energy_wh",
            "loc_error_mean_m", "link_delivered", "link_dropped", "end_reason"]
    new = not os.path.exists(INDEX_CSV)
    with open(INDEX_CSV, "a", encoding="utf-8", newline="") as f:
        if new:
            f.write(",".join(cols) + "\n")
        f.write(",".join(str(m.get(c, "")).replace(",", ";") for c in cols) + "\n")


def render_html(mission, m: dict, images: dict[str, bytes]) -> str:
    def img(name, caption):
        if name not in images:
            return ""
        b64 = base64.b64encode(images[name]).decode()
        return f'<figure><img src="data:image/png;base64,{b64}" alt="{caption}"><figcaption>{caption}</figcaption></figure>'

    rows = [
        ("Environment", T.ENV_TITLES.get(m["env"], m["env"])), ("Exploration strategy", m["strategy"]),
        ("Localisation", m["localisation"]), ("Driving mode", m["mode"]), ("Seed", m["seed"]),
        ("Outcome", f'{m["status"]} - {html.escape(m["end_reason"] or "mission still running")}'),
        ("Mission time", f'{m["time_s"]} s  ({m["steps"]} control steps)'),
        ("Coverage of reachable area", f'{m["coverage"]:.1%}'), ("Path length", f'{m["path_length_m"]} m'),
        ("Backtracking events", m["backtracks"]), ("Collisions / bumper events", f'{m["collisions"]} / {m["bumps"]}'),
        ("Cliff events", m["cliff_events"]), ("Energy used", f'{m["energy_wh"]} Wh'),
        ("Localisation error (mean / final)", f'{m["loc_error_mean_m"]} m / {m["loc_error_m"]} m'),
        ("Radio packets delivered / dropped", f'{m["link_delivered"]} / {m["link_dropped"]}  (link lost {m["link_losses"]} times)'),
        ("AI terrain classifier", f'{m["terrain_accuracy"]:.1%} live accuracy' if m.get("terrain_accuracy") is not None else "off"),
        ("Faulty / injected sensors", ", ".join(m["faulty_sensors"]) or "none"),
    ]
    table = "".join(f"<tr><th>{html.escape(str(k))}</th><td>{v}</td></tr>" for k, v in rows)
    team = "".join(f"<li>{html.escape(n)}</li>" for n in T.TEAM)
    return f"""<!doctype html><html lang="en"><head><meta charset="utf-8">
<title>{T.ROVER_NAME} - Mission #{m['mission_number']}</title>
<style>
body{{font:15px/1.5 "Segoe UI",system-ui,sans-serif;color:#141a1f;background:#eef1f4;margin:0;padding:24px}}
.card{{background:#fff;border:1px solid #d5dde4;border-radius:14px;padding:20px 24px;max-width:1100px;margin:0 auto 16px}}
h1{{margin:0 0 4px;font-size:22px}} .sub{{color:#5c6b78;margin:0 0 16px}}
table{{border-collapse:collapse;width:100%}} th{{text-align:left;color:#5c6b78;font-weight:600;padding:6px 10px 6px 0;width:38%;border-bottom:1px solid #eef1f4}}
td{{padding:6px 0;border-bottom:1px solid #eef1f4;font-variant-numeric:tabular-nums}}
.maps{{display:grid;grid-template-columns:1fr 1fr;gap:16px}} figure{{margin:0}} img{{width:100%;border-radius:10px;border:1px solid #d5dde4}}
figcaption{{color:#5c6b78;font-size:13px;margin-top:6px}} ul{{columns:3;margin:0;padding-left:18px}} .foot{{color:#5c6b78;font-size:13px}}
@media(max-width:700px){{.maps{{grid-template-columns:1fr}} ul{{columns:1}}}}
</style></head><body>
<div class="card"><h1>{T.ROVER_NAME} &mdash; Mission #{m['mission_number']}</h1>
<p class="sub">{html.escape(m.get('title', ''))} &middot; {m['timestamp'].replace('T', ' ')} &middot; recorded on {html.escape(m['machine'])}</p>
<table>{table}</table></div>
<div class="card"><div class="maps">{img('true_world.png', 'True world: terrain, true path (yellow), sonar and IR beams')}{img('robot_map.png', "The rover's own map: occupancy, terrain and hazards; fused estimate (green), encoders only (red)")}</div></div>
<div class="card"><p class="foot"><b>{html.escape(T.COURSE)}</b> &middot; Supervisor {html.escape(T.DOCTOR)} &middot; Faculty of Engineering &ndash; Computer and Systems Department</p>
<ul>{team}</ul></div>
</body></html>"""


# ------------------------------------------------------------------ upload
class ReportUploader:
    """Sends report folders to the Apps Script bridge; keeps a pending queue."""

    def __init__(self):
        self.cfg = load_config()
        self.pending: list[str] = self._load_pending()
        self.last_result = ""
        self.busy = False
        self.lock = threading.Lock()

    @property
    def configured(self) -> bool:
        return bool(self.cfg.get("upload_url", "").startswith("https://"))

    def _load_pending(self) -> list[str]:
        try:
            with open(PENDING_PATH, encoding="utf-8") as f:
                return [p for p in json.load(f) if os.path.isdir(p)]
        except (OSError, json.JSONDecodeError):
            return []

    def _save_pending(self):
        os.makedirs(REPORTS_DIR, exist_ok=True)
        with open(PENDING_PATH, "w", encoding="utf-8") as f:
            json.dump(self.pending, f, indent=2)

    def queue(self, folder: str):
        with self.lock:
            if folder not in self.pending:
                self.pending.append(folder)
                self._save_pending()

    def online(self) -> bool:
        try:
            socket.create_connection(("script.google.com", 443), timeout=3).close()
            return True
        except OSError:
            return False

    def send_folder(self, folder: str) -> tuple[bool, str]:
        if not self.configured:
            return False, "Drive bridge not configured"
        files = []
        for name in sorted(os.listdir(folder)):
            path = os.path.join(folder, name)
            if not os.path.isfile(path):
                continue
            mime = {"html": "text/html", "png": "image/png", "json": "application/json", "csv": "text/csv"}.get(name.rsplit(".", 1)[-1], "application/octet-stream")
            with open(path, "rb") as f:
                files.append({"name": name, "mime": mime, "b64": base64.b64encode(f.read()).decode()})
        base = os.path.basename(folder)
        suffix = base.split(" - ", 1)[1] if " - " in base else base      # the title after "Mission #new - "
        key = ""
        try:
            with open(os.path.join(folder, "metrics.json"), encoding="utf-8") as f:
                key = json.load(f).get("mission_key", "") or ""
        except (OSError, json.JSONDecodeError):
            pass
        body = json.dumps({"name": base, "suffix": suffix, "key": key, "files": files}).encode()
        req = urllib.request.Request(self.cfg["upload_url"], data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=90) as resp:
                answer = json.loads(resp.read() or b"{}")
            if answer.get("ok"):
                final = answer.get("name") or base
                self._apply_number(folder, final, answer.get("number"))
                return True, final
            return False, answer.get("error", "bridge refused the report")
        except (urllib.error.URLError, TimeoutError, json.JSONDecodeError, OSError) as e:
            return False, str(e)

    @staticmethod
    def _apply_number(folder: str, final_name: str, number) -> str:
        """Rename the local copy to the name the bridge chose and write the
        number into the report files."""
        if number is None:
            return folder
        for fn in ("report.html", "metrics.json"):
            path = os.path.join(folder, fn)
            if os.path.exists(path):
                with open(path, encoding="utf-8") as f:
                    txt = f.read()
                txt = txt.replace(f"Mission #{PENDING_NUMBER}", f"Mission #{number}").replace('"mission_number": "new"', f'"mission_number": {number}')
                with open(path, "w", encoding="utf-8") as f:
                    f.write(txt)
        new_path = os.path.join(os.path.dirname(folder), final_name)
        try:
            if new_path != folder and not os.path.exists(new_path):
                os.rename(folder, new_path)
                return new_path
        except OSError:
            pass
        return folder

    def flush(self, status_cb=None) -> None:
        """Try to send everything pending. Runs in a worker thread."""
        if self.busy or not self.pending or not self.configured:
            return
        self.busy = True

        def work():
            try:
                if not self.online():
                    self.last_result = f"offline - {len(self.pending)} report(s) waiting"
                    if status_cb:
                        status_cb(self.last_result)
                    return
                for folder in list(self.pending):
                    if not os.path.isdir(folder):
                        with self.lock:
                            self.pending.remove(folder)
                            self._save_pending()
                        continue
                    ok, info = self.send_folder(folder)
                    if ok:
                        with self.lock:
                            self.pending.remove(folder)
                            self._save_pending()
                        self.last_result = f"report uploaded as {info}"
                    else:
                        self.last_result = f"upload failed ({info}) - will retry"
                        break
                if status_cb:
                    status_cb(self.last_result)
            finally:
                self.busy = False
        threading.Thread(target=work, daemon=True).start()
