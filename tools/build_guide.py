"""The team guide as one file, pictures inside: opens on a phone or a laptop
with nothing next to it (send it on WhatsApp, open it from Drive).

    python tools/build_guide.py      -> docs/Rovust_team_guide.html

Source: docs/source/guide/. ``shell.html`` is the page (styles, menu,
navigation); every other ``*.html`` there is one chapter (a ``<section
class="ch">`` of ``<article>`` lessons), joined in file-name order. Picture
paths are relative to docs/; they are shrunk and embedded. The fonts in
``fonts/`` are embedded too.
"""
import base64
import io
import os
import re

from PIL import Image

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DOCS = os.path.join(ROOT, "docs")
SRC = os.path.join(DOCS, "source", "guide")
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


def fonts_css() -> str:
    """The three fonts (fonts/fonts.css + its .woff2 files) as one <style>, so
    the guide looks the same with no internet."""
    folder = os.path.join(SRC, "fonts")
    css = open(os.path.join(folder, "fonts.css"), encoding="utf-8").read()

    def swap(m):
        raw = open(os.path.join(folder, m.group(1)), "rb").read()
        return "url(data:font/woff2;base64," + base64.b64encode(raw).decode() + ")"
    return "<style>\n" + re.sub(r"url\(([\w.-]+\.woff2)\)", swap, css) + "</style>"


def main():
    shell = open(os.path.join(SRC, "shell.html"), encoding="utf-8").read()
    parts = sorted(f for f in os.listdir(SRC) if f.endswith(".html") and f != "shell.html")
    chapters = "\n".join(open(os.path.join(SRC, f), encoding="utf-8").read() for f in parts)
    ids = re.findall(r'<article id="([^"]+)"', chapters)
    assert len(ids) == len(set(ids)), "duplicate lesson id"
    for target in re.findall(r'href="#([^"]+)"', chapters):
        assert target in ids, f"link to a lesson that does not exist: #{target}"
    assert shell.count("<!--CHAPTERS-->") == 1
    html = shell.replace("<!--CHAPTERS-->", chapters)
    assert html.count("<!--FONTS-->") == 1
    html = html.replace("<!--FONTS-->", fonts_css())
    cache = {}

    def swap(m):
        attr, rel = m.group(1), m.group(2)
        if rel.startswith(("http:", "https:", "data:", "#")):
            return m.group(0)
        if rel not in cache:
            cache[rel] = data_uri(rel)
        return f'{attr}="{cache[rel]}"'
    html = re.sub(r'\b(src|href)="([^"]+\.(?:png|jpg|jpeg|gif))"', swap, html)
    html = html.replace("<title>", "<!-- built by tools/build_guide.py from docs/source/guide/: edit those files, not this one -->\n<title>", 1)
    open(OUT, "w", encoding="utf-8", newline="\n").write(html)
    print(f"{os.path.relpath(OUT, ROOT)}  {len(parts)} chapters  {len(ids)} lessons  {len(cache)} pictures  {os.path.getsize(OUT) / 1e6:.1f} MB")


if __name__ == "__main__":
    main()
