# One page showing the whole path, from the Super User's Overview to holding an Admin's workstation.
#
# It is built from the REAL screenshots in design/shots -- not a redrawing of them -- so what it shows
# is what the boards actually render. Every step names the gesture that got you there and what the
# crumb says, because the claim being checked is that this is ONE gesture repeated rather than five
# different navigations.
#
#   environ-engine\Scripts\python.exe design\flow_strip.py
#   then screenshot design/boards/MAXIMISE.html at 1440x1120

import pathlib

HERE = pathlib.Path(__file__).parent
SHOTS = (HERE / "shots").resolve()
OUT = HERE / "boards"
OUT.mkdir(exist_ok=True)

GRADIENT = "linear-gradient(155deg, #121220 0%, #2A1F50 45%, #4B2F8A 100%)"
INK, DIM, FAINT = "#E8ECF2", "rgba(255,255,255,0.68)", "rgba(255,255,255,0.42)"
OK, ACCENT, DANGER = "#7FB396", "#8AA6E0", "#DD8A8A"
SANS = "'IBM Plex Sans', 'Segoe UI', sans-serif"
MONO = "'IBM Plex Mono', Consolas, monospace"

STEPS = [
    ("gui-super_user.png", "1", "Must see", "where a Super User starts — the running app",
     "no crumb — this is the top", "The running app", OK),
    ("gui-super_user-authority.png", "2", "Authority, opened",
     "DOUBLE click a cell — the area recomposes around it",
     "Must see › Authority", "The running app", OK),
    ("DP16-Dept-Selected.png", "3", "Operations selected",
     "SINGLE click the department — it is ringed and its text arrives beside the map",
     "crumb unchanged — nothing has opened", "Design only", ACCENT),
    ("DP12-Big.png", "4", "Operations",
     "DOUBLE click the same mark — now you are there",
     "Authority › Operations", "Design only", ACCENT),
    ("DP15-Admin-Selected.png", "5", "A. Quaye selected",
     "SINGLE click their line — the cell swaps to draw them",
     "crumb unchanged — still just looking", "Design only", ACCENT),
    ("DP17-Admin-Entered.png", "6", "A. Quaye, entered",
     "DOUBLE click — the cost is stated before the act",
     "Authority › Operations › A. Quaye", "Design only", ACCENT),
    ("DP13-Hover.png", "7", "Escape, then a chart",
     "back out, and put the pointer on Its machines",
     "the cell advertises itself: “— maximise ›”", "Design only", ACCENT),
    ("DP11-Maximised.png", "8", "Maximised",
     "DOUBLE click a chart — it opens into itself, and the names come back",
     "Authority › Operations › Its machines", "Design only", ACCENT),
]

TW, TH = 640, 400


def card(fn, n, title, gesture, crumb, state, tone):
    img = (SHOTS / fn).as_uri()
    badge = (f'<span style="display:inline-flex;align-items:center;height:20px;padding:0 9px;border-radius:6px;'
             f'background:rgba(255,255,255,0.10);color:{tone};font-family:{MONO};font-size:10.5px;'
             f'font-weight:500;">{state}</span>')
    num = (f'<span style="display:inline-flex;align-items:center;justify-content:center;width:22px;height:22px;'
           f'border-radius:7px;background:rgba(255,255,255,0.14);color:#fff;font-family:{MONO};font-size:12px;'
           f'font-weight:600;flex:none;">{n}</span>')
    return f'''<div style="width:{TW}px;">
  <div style="display:flex;align-items:center;gap:10px;padding-bottom:8px;">
    {num}<span style="font-family:{SANS};font-size:15px;font-weight:600;color:#fff;">{title}</span>
    <span style="flex:1;"></span>{badge}
  </div>
  <img src="{img}" width="{TW}" height="{TH}"
       style="display:block;border-radius:10px;box-shadow:0 10px 30px rgba(0,0,0,0.45),0 0 0 1px rgba(255,255,255,0.10);">
  <div style="display:flex;gap:10px;align-items:baseline;padding-top:9px;">
    <span style="font-family:{SANS};font-size:12.5px;color:{DIM};">{gesture}</span>
  </div>
  <div style="font-family:{MONO};font-size:11.5px;color:{FAINT};padding-top:3px;">{crumb}</div>
</div>'''


cards = "".join(card(*s) for s in STEPS)
html = f'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><title>The path</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
</head>
<body style="margin:0;background:{GRADIENT};">
<div style="width:1440px;box-sizing:border-box;padding:30px 40px 34px;">
  <div style="display:flex;align-items:center;gap:12px;">
    <span style="width:10px;height:26px;border-radius:3px;background:#fff;"></span>
    <span style="font-family:{SANS};font-size:22px;font-weight:700;color:#fff;">Super User, all the way down</span>
    <span style="font-family:{SANS};font-size:13px;color:{DIM};">one gesture the whole way — what changes is what the container is about</span>
  </div>
  <div style="font-family:{SANS};font-size:12.5px;color:{FAINT};padding:8px 0 20px 22px;">
    Steps 1–2 are the running app; 3–8 are boards. The odd steps are the SINGLE click — selecting, which was
    missing from the first version of this page and is the step you were looking for. It rings or swaps, brings
    text beside it, and never grows the crumb. The even steps are the DOUBLE click, which does grow it. What the
    double click lands on decides what you get: a cell recomposes its area, a place takes you there, a chart
    opens into itself. Escape reverses all of them exactly.
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:34px 60px;">{cards}</div>
</div>
</body></html>'''

(OUT / "JOURNEY.html").write_text(html, encoding="utf-8")
print("wrote", OUT / "JOURNEY.html")
