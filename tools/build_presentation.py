"""Build the Rovust presentation from docs/presentation/slides/*.html.

Outputs (in docs/presentation/):
    Rovust_presentation.html            standalone viewer: arrow keys, N = notes, L = notes language (EN / مصري), F = fullscreen
    Rovust_presentation.pdf             the 30 slides as pages
    Rovust_presentation.pptx            PowerPoint with the slides as pictures and a push between them (no notes in it: they show
                                        when the file is opened; the notes are in speaker_notes.md)
    SPEAKER_NOTES.md                   both languages, slide by slide
    png/<nn>-<id>.png                  one 1920x1080 picture per slide (rendered with headless Edge / Chrome)

Run:  python tools/build_presentation.py            (needs the venv: python-pptx, Pillow)
      python tools/build_presentation.py --html-only  (no browser rendering; just the viewer and the notes)
"""
from __future__ import annotations

import html
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import urllib.parse
import time

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PRES = os.path.join(ROOT, "docs", "presentation")
VIDEO_LINK = "../media/rovust_demo.mp4"   # the demo video, linked from the Demo slide (relative to this folder)
# slides that carry a video: id -> (file, box in slide pixels or None for the full slide)
VIDEOS = {"demo-video": (VIDEO_LINK, None),
          "model-3d": ("../media/rovust_3d.mp4", (352, 290, 1216, 684))}
SLIDES = os.path.join(PRES, "slides")
PNG_DIR = os.path.join(PRES, "png")

BROWSERS = [
    r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
    r"C:\Program Files\Google\Chrome\Application\chrome.exe",
    r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
    "/usr/bin/google-chrome", "/usr/bin/chromium", "/usr/bin/chromium-browser",
]

# The slide files use the Claude Slides inline-style subset: a 1920x1080 section,
# flex/grid children, pinned (absolute) children, h1-h3/p/ul/table/img/svg and
# <x-shape>. This CSS gives those elements the defaults that format assumes.
BASE_CSS = """
*{box-sizing:border-box;margin:0}
html,body{background:#0b0f13}
section.slide{position:relative;width:1920px;height:1080px;overflow:hidden;display:flex;flex-direction:column;flex-shrink:0}
section.slide div{min-width:0}
section.slide div:not([style*="display"]){display:flex;flex-direction:column}
section.slide h1{font-size:96px;font-weight:600;line-height:1.1}
section.slide h2{font-size:64px;font-weight:600;line-height:1.15}
section.slide h3{font-size:44px;font-weight:600;line-height:1.2}
section.slide p{font-size:32px;line-height:1.4}
section.slide ul,section.slide ol{font-size:32px;line-height:1.4;padding-left:1.1em}
section.slide li{padding-left:.15em}
section.slide a{color:inherit}
section.slide b{font-weight:600}
section.slide img{display:block}
section.slide table{border-collapse:collapse;width:100%;table-layout:fixed}
section.slide th,section.slide td{padding:.35em .6em;text-align:left;vertical-align:top;border-bottom:1px solid rgba(146,161,175,.35);overflow-wrap:break-word}
section.slide th{font-weight:600}
section.slide svg{display:block}
section.slide hr{border:0;border-top:1px solid currentColor;width:100%}
section.slide x-shape{display:block;flex-shrink:0}
section.slide x-shape[kind=arrow-right]{clip-path:polygon(0 25%,60% 25%,60% 0,100% 50%,60% 100%,60% 75%,0 75%)}
section.slide x-shape[kind=arrow-left]{clip-path:polygon(100% 25%,40% 25%,40% 0,0 50%,40% 100%,40% 75%,100% 75%)}
section.slide x-shape[kind=ellipse]{border-radius:50%}
section.slide x-shape[kind=diamond]{clip-path:polygon(50% 0,100% 50%,50% 100%,0 50%)}
section.slide aside{display:none}
/* the slide format paints flow content above earlier pinned backdrops: give flow children a stacking position */
section.slide > *:not([style*="position:absolute"]):not([style*="position: absolute"]){position:relative}
"""

VIEWER_CSS = """
body{font-family:'IBM Plex Sans',Segoe UI,Arial,sans-serif;color:#e6edf3;height:100vh;overflow:hidden;display:flex;flex-direction:column}
#stage{flex:1;position:relative;display:flex;align-items:center;justify-content:center;overflow:hidden}
#frame{position:relative;flex:none;width:1920px;height:1080px;transform-origin:center center;box-shadow:0 20px 80px rgba(0,0,0,.6)}
#frame section.slide{position:absolute;left:0;top:0}
#frame section.slide:not(.current){display:none!important}
#bar{height:44px;display:flex;align-items:center;gap:14px;padding:0 16px;background:#11161b;border-top:1px solid #2f3b46;font-size:14px;color:#92a1af;flex-shrink:0}
#bar b{color:#e6edf3;font-weight:600}
#bar button{background:#1b232a;color:#e6edf3;border:1px solid #2f3b46;border-radius:6px;padding:4px 10px;font:inherit;cursor:pointer}
#bar button:hover{border-color:#2dd4bf}
#bar .sp{flex:1}
#notes{display:none;height:26vh;min-height:140px;overflow:auto;padding:14px 22px;background:#0f1419;border-top:1px solid #2f3b46;font-size:clamp(15px,1.6vw,22px);line-height:1.55;color:#d6e0e6;flex-shrink:0}
#notes.on{display:block}
#notes.ar{direction:rtl;text-align:right;font-family:'IBM Plex Sans Arabic','Segoe UI',Tahoma,Arial,sans-serif}
#notes .lbl{font:600 12px/1 'JetBrains Mono',monospace;letter-spacing:2px;color:#2dd4bf;margin-bottom:8px;text-transform:uppercase}
#notes.ar .lbl{font-family:'JetBrains Mono',monospace;direction:ltr;text-align:right}
kbd{background:#1b232a;border:1px solid #2f3b46;border-radius:4px;padding:1px 6px;font:12px 'JetBrains Mono',monospace;color:#bfd0d8}
.bare body{height:auto;overflow:visible;display:block}
.bare #bar,.bare #notes{display:none!important}
.bare #stage{display:block;width:1920px;height:1080px}
.bare #frame{transform:none!important;box-shadow:none}
"""

VIEWER_JS = """
(function(){
  const q=new URLSearchParams(location.search);
  const slides=[...document.querySelectorAll('#frame section.slide')];
  const notesEn=NOTES_EN, notesAr=NOTES_AR;
  const bare=q.has('bare');
  if(bare) document.documentElement.classList.add('bare');
  let i=0; const want=q.get('slide');
  if(want){const k=slides.findIndex(s=>s.id===want); if(k>=0) i=k;}
  const store={get:k=>{try{return localStorage.getItem(k);}catch(e){return null;}},set:(k,v)=>{try{localStorage.setItem(k,v);}catch(e){}}};
  let lang=store.get('rovust-notes-lang')||'en';
  let notesOn=store.get('rovust-notes')==='1';
  const frame=document.getElementById('frame'), stage=document.getElementById('stage');
  const notes=document.getElementById('notes'), counter=document.getElementById('counter'), title=document.getElementById('title');
  function fit(){ if(bare) return; const r=stage.getBoundingClientRect(); const s=Math.min(r.width/1920,r.height/1080)*0.98; frame.style.transform='scale('+s+')'; }
  // the original renderer shrinks an over-full slide's text; emulate that with CSS zoom on the flow children
  function fitSlide(sec){
    if(sec.dataset.fitted) return; sec.dataset.fitted='1';
    const kids=[...sec.children].filter(c=>c.tagName!=='ASIDE'&&getComputedStyle(c).position!=='absolute');
    const limit=1080-parseFloat(getComputedStyle(sec).paddingBottom);
    const over=()=>{const r=sec.getBoundingClientRect(); const k=1080/r.height; return Math.max(...kids.map(c=>(c.getBoundingClientRect().bottom-r.top)*k))>limit+1;};
    let z=1; while(z>0.55&&over()){ z=Math.round((z-0.02)*100)/100; kids.forEach(c=>c.style.zoom=z); }
  }
  function show(k){
    i=Math.max(0,Math.min(slides.length-1,k));
    slides.forEach((s,j)=>s.classList.toggle('current',j===i));
    if(bare){ slides.forEach((s,j)=>{ if(j!==i) s.remove(); }); slides[i].style.display='flex'; }
    try{ (document.fonts&&document.fonts.ready?document.fonts.ready:Promise.resolve()).then(()=>{ try{ fitSlide(slides[i]); }catch(e){} }); }catch(e){}
    counter.textContent=(i+1)+' / '+slides.length;
    const h=slides[i].querySelector('h1,h2'); title.textContent=h?h.textContent.trim():slides[i].id;
    const n=(lang==='ar'?notesAr:notesEn)[slides[i].id]||'';
    notes.className=(notesOn?'on ':'')+(lang==='ar'?'ar':'');
    notes.innerHTML='<div class="lbl">'+(lang==='ar'?'ملاحظات المتحدث · مصري':'Speaker notes · English')+'</div>'+n.replace(/&/g,'&amp;').replace(/</g,'&lt;');
    fit();
    if(!bare){ try{ const u=new URL(location); u.searchParams.set('slide',slides[i].id); history.replaceState(null,'',u); }catch(e){} }
  }
  function toggleNotes(){ notesOn=!notesOn; store.set('rovust-notes',notesOn?'1':'0'); show(i); }
  function toggleLang(){ lang=lang==='ar'?'en':'ar'; store.set('rovust-notes-lang',lang); show(i); }
  document.getElementById('prev').onclick=()=>show(i-1);
  document.getElementById('next').onclick=()=>show(i+1);
  document.getElementById('bnotes').onclick=toggleNotes;
  document.getElementById('blang').onclick=toggleLang;
  document.getElementById('bfull').onclick=()=>document.documentElement.requestFullscreen&&document.documentElement.requestFullscreen();
  addEventListener('keydown',e=>{
    if(e.key==='ArrowRight'||e.key==='PageDown'||e.key===' ') {show(i+1);e.preventDefault();}
    else if(e.key==='ArrowLeft'||e.key==='PageUp'){show(i-1);e.preventDefault();}
    else if(e.key==='Home') show(0); else if(e.key==='End') show(slides.length-1);
    else if(e.key==='n'||e.key==='N') toggleNotes(); else if(e.key==='l'||e.key==='L') toggleLang();
    else if(e.key==='f'||e.key==='F') document.getElementById('bfull').click();
  });
  stage.addEventListener('click',e=>{ if(bare) return; const r=stage.getBoundingClientRect(); show(e.clientX-r.left<r.width/3?i-1:i+1); });
  addEventListener('resize',fit);
  show(i);
})();
"""


def load_deck():
    idx = json.load(open(os.path.join(PRES, "deck.json"), encoding="utf-8"))
    notes_ar = json.load(open(os.path.join(PRES, "notes_ar.json"), encoding="utf-8"))
    slides, notes_en = [], {}
    for sid in idx["order"]:
        s = open(os.path.join(SLIDES, sid + ".html"), encoding="utf-8").read()
        m = re.search(r"<aside>(.*?)</aside>", s, re.S)
        notes_en[sid] = html.unescape(m.group(1).strip()) if m else ""
        s = re.sub(r'<section id="([^"]+)"', r'<section class="slide" id="\1"', s, count=1)
        slides.append((sid, s))
    return idx, slides, notes_en, notes_ar


def write_viewer(idx, slides, notes_en, notes_ar) -> str:
    fonts = "".join(f'<link rel="stylesheet" href="{html.escape(f["href"])}">' for f in idx["faces"].values() if f.get("href"))
    fonts += '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans+Arabic:wght@400;500&display=swap">'
    body = "\n".join(s for _, s in slides)
    page = f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(idx["title"])}</title>
<link rel="icon" href="../../assets/icon.png">
{fonts}
<style>{BASE_CSS}{VIEWER_CSS}</style>
</head><body>
<div id="stage"><div id="frame">
<noscript><p style="color:#e6edf3;font-size:40px;padding:120px">This viewer needs JavaScript. Use Rovust_presentation.pdf instead.</p></noscript>
{body}
</div></div>
<div id="notes"></div>
<div id="bar"><button id="prev" title="Previous (←)">&#8592;</button><button id="next" title="Next (→)">&#8594;</button>
<b id="counter"></b><span id="title"></span><span class="sp"></span>
<button id="bnotes">Notes <kbd>N</kbd></button><button id="blang">EN / مصري <kbd>L</kbd></button><button id="bfull">Fullscreen <kbd>F</kbd></button></div>
<script>const NOTES_EN={json.dumps(notes_en, ensure_ascii=False)};const NOTES_AR={json.dumps(notes_ar, ensure_ascii=False)};{VIEWER_JS}document.addEventListener('click',e=>{{const v={json.dumps({k: v[0] for k, v in VIDEOS.items()})};for(const k in v)if(e.target.closest('section#'+k))window.open(v[k],'_blank');}});</script>
</body></html>"""
    out = os.path.join(PRES, "Rovust_presentation.html")
    open(out, "w", encoding="utf-8", newline="\n").write(page)
    return out


def write_notes_md(idx, slides, notes_en, notes_ar):
    lines = [f"# {idx['title']} — speaker notes", "",
             "English notes first, then the same note in Egyptian Arabic. One entry per slide, in deck order.", ""]
    for n, (sid, s) in enumerate(slides, 1):
        m = re.search(r"<h[12][^>]*>(.*?)</h[12]>", s, re.S)
        head = html.unescape(re.sub(r"<[^>]+>", "", m.group(1))).strip() if m else sid
        lines += [f"## {n}. {head}", "", notes_en[sid], "", f'<div dir="rtl" align="right">', "", notes_ar.get(sid, ""), "", "</div>", ""]
    open(os.path.join(PRES, "SPEAKER_NOTES.md"), "w", encoding="utf-8", newline="\n").write("\n".join(lines))


def find_browser() -> str | None:
    for p in BROWSERS:
        if os.path.exists(p):
            return p
    return shutil.which("msedge") or shutil.which("chrome") or shutil.which("chromium")


def render_pngs(viewer: str, order: list[str]) -> list[str]:
    browser = find_browser()
    if not browser:
        print("no Edge/Chrome found: skipping PNG/PDF/PPTX", file=sys.stderr)
        return []
    os.makedirs(PNG_DIR, exist_ok=True)
    for f in os.listdir(PNG_DIR):  # renumbered slides leave old pictures behind
        if f.endswith(".png"):
            os.remove(os.path.join(PNG_DIR, f))
    url ="file:///" + urllib.parse.quote(viewer.replace("\\", "/"))
    profile = tempfile.mkdtemp(prefix="rovust-render-")
    outs = []
    t0 = time.time()
    for n, sid in enumerate(order, 1):
        out = os.path.join(PNG_DIR, f"{n:02d}-{sid}.png")
        cmd = [browser, "--headless=new", "--disable-gpu", "--hide-scrollbars", "--no-first-run", "--disable-extensions",
               # each slide gets its own profile, so a stuck Edge cannot block the next one
               f"--user-data-dir={os.path.join(profile, sid)}", "--window-size=1920,1080", "--force-device-scale-factor=1",
               "--virtual-time-budget=6000", "--run-all-compositor-stages-before-draw",
               f"--screenshot={out}", f"{url}?slide={sid}&bare=1"]
        if os.path.exists(out):
            os.remove(out)
        for _ in range(3):
            # headless Edge sometimes writes the screenshot and then never exits:
            # stop it as soon as the file is there and has stopped growing
            proc = subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            t1, size = time.time(), -1
            while proc.poll() is None and time.time() - t1 < 60:
                time.sleep(0.3)
                if os.path.exists(out):
                    s = os.path.getsize(out)
                    if s > 0 and s == size:
                        break
                    size = s
            if proc.poll() is None:
                proc.kill()
                proc.wait()
            if os.path.exists(out):
                break
            print("  retry", sid, file=sys.stderr)
        if not os.path.exists(out):
            print("render failed:", sid, file=sys.stderr)
            continue
        outs.append(out)
        print(f"  {n:02d} {sid}")
    shutil.rmtree(profile, ignore_errors=True)
    print(f"rendered {len(outs)} slides in {time.time() - t0:.0f} s")
    return outs


def write_pdf(pngs: list[str]):
    from PIL import Image
    imgs = [Image.open(p).convert("RGB") for p in pngs]
    out = os.path.join(PRES, "Rovust_presentation.pdf")
    imgs[0].save(out, save_all=True, append_images=imgs[1:], resolution=144.0, title="Rovust presentation")
    print("pdf:", os.path.relpath(out, ROOT), f"{os.path.getsize(out) / 1e6:.1f} MB")


def write_pptx(pngs: list[str], order: list[str], name: str):
    from lxml import etree
    from pptx import Presentation
    from pptx.util import Inches
    prs = Presentation()
    prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)
    blank = prs.slide_layouts[6]
    for png, sid in zip(pngs, order):
        slide = prs.slides.add_slide(blank)
        link, box = VIDEOS.get(sid, (None, None))
        video = os.path.normpath(os.path.join(PRES, link)) if link else None
        if video and os.path.exists(video) and box is None:
            # the video itself, inside the file: it plays in the slide on a click, wherever the
            # .pptx is copied to (the slide picture is its poster)
            slide.shapes.add_movie(video, 0, 0, prs.slide_width, prs.slide_height,
                                   poster_frame_image=png, mime_type="video/mp4")
        elif video and os.path.exists(video):
            # a video in a frame on the slide: the slide picture behind it, the movie on the frame,
            # its poster cut from the same picture so nothing jumps when it starts
            from PIL import Image
            slide.shapes.add_picture(png, 0, 0, prs.slide_width, prs.slide_height)
            x, y, w, h = box
            poster = os.path.join(tempfile.gettempdir(), f"rovust-poster-{sid}.png")
            Image.open(png).crop((x, y, x + w, y + h)).save(poster)
            k = prs.slide_width / 1920
            slide.shapes.add_movie(video, int(x * k), int(y * k), int(w * k), int(h * k),
                                   poster_frame_image=poster, mime_type="video/mp4")
        else:
            slide.shapes.add_picture(png, 0, 0, prs.slide_width, prs.slide_height)
        # the next slide pushes the old one out; a part-opening slide comes up from below
        # (python-pptx has no API for transitions: add the element by hand, where the schema
        # wants it: after clrMapOvr, before timing)
        pml = "{http://schemas.openxmlformats.org/presentationml/2006/main}"
        tr = etree.SubElement(slide._element, pml + "transition")
        tr.set("spd", "med")
        etree.SubElement(tr, pml + "push").set("dir", "u" if sid.startswith("sec-") else "l")
        timing = slide._element.find(pml + "timing")
        if timing is not None:
            timing.addprevious(tr)
    out = os.path.join(PRES, name)
    prs.save(out)
    print("pptx:", os.path.relpath(out, ROOT), f"{os.path.getsize(out) / 1e6:.1f} MB")


def main():
    idx, slides, notes_en, notes_ar = load_deck()
    viewer = write_viewer(idx, slides, notes_en, notes_ar)
    write_notes_md(idx, slides, notes_en, notes_ar)
    print("viewer:", os.path.relpath(viewer, ROOT))
    if "--html-only" in sys.argv:
        return 0
    pngs = render_pngs(viewer, idx["order"])
    if len(pngs) != len(idx["order"]):
        print("not every slide rendered; PDF/PPTX skipped", file=sys.stderr)
        return 1
    write_pdf(pngs)
    write_pptx(pngs, idx["order"], "Rovust_presentation.pptx")
    return 0


if __name__ == "__main__":
    sys.exit(main())
