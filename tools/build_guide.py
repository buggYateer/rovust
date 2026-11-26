"""One file for the team guide, pictures inside: opens on a phone or a laptop
with nothing next to it (send it on WhatsApp, open it from Drive).

    python tools/build_guide.py      -> docs/Rovust_team_guide.html

The source is docs/source/team_guide_ar.html (edit that one); its picture
paths are relative to docs/, shrunk to the size they are shown at, and embedded.
"""
import base64
import io
import os
import re

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
SRC = os.path.join(DOCS, "source", "team_guide_ar.html")
OUT = os.path.join(DOCS, "Rovust_team_guide.html")


def data_uri(rel: str) -> str:
    path = os.path.normpath(os.path.join(DOCS, rel))
    if path.lower().endswith(".gif"):                     # keep the animation
        raw, mime = open(path, "rb").read(), "image/gif"
    else:
        im = Image.open(path)
        has_alpha = im.mode in ("RGBA", "LA") or (im.mode == "P" and "transparency" in im.info)
        if im.width > 1400:
            im = im.resize((1400, round(im.height * 1400 / im.width)), Image.Resampling.LANCZOS)
        buf = io.BytesIO()
        if has_alpha and im.width <= 300:                 # small icons: keep the transparent corners
            im.convert("RGBA").save(buf, "PNG", optimize=True)
            mime = "image/png"
        else:
            im.convert("RGB").save(buf, "JPEG", quality=84, optimize=True, progressive=True)
            mime = "image/jpeg"
        raw = buf.getvalue()
    return f"data:{mime};base64," + base64.b64encode(raw).decode()


def main():
    html = open(SRC, encoding="utf-8").read()
    cache = {}

    def swap(m):
        attr, rel = m.group(1), m.group(2)
        if rel.startswith(("http:", "https:", "data:", "#")):
            return m.group(0)
        if rel not in cache:
            cache[rel] = data_uri(rel)
        return f'{attr}="{cache[rel]}"'
    html = re.sub(r'\b(src|href)="([^"]+\.(?:png|jpg|jpeg|gif))"', swap, html)
    html = html.replace("<title>Rovust — دليل الفريق</title>",
                        "<title>Rovust — دليل الفريق</title>\n<!-- built by tools/build_guide.py from docs/source/team_guide_ar.html: edit that file, not this one -->", 1)
    open(OUT, "w", encoding="utf-8", newline="\n").write(html)
    print(f"{os.path.relpath(OUT, ROOT)}  {len(cache)} pictures  {os.path.getsize(OUT) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
