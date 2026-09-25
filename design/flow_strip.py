# One page showing the whole path, from the Super User's Overview to holding an Admin's workstation.
#
# It is built from the REAL screenshots in design/shots -- not a redrawing of them -- so what it shows
# is what the boards actually render. Every step names the gesture that got you there and what the
# crumb says, because the claim being checked is that this is ONE gesture repeated rather than five
# different navigations.
#
#   environ-engine\Scripts\python.exe design\flow_strip.py
#   then screenshot design/boards/FLOW.html at 1440x1560

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
    ("gui-super_user.png", "1", "Must see", "where a Super User starts",
     "no crumb — this is the top", "The running app", OK),
    ("gui-super_user-authority.png", "2", "Authority, opened", "double-click the Authority cell",
     "Must see › Authority", "The running app", OK),
    ("DP05-Department.png", "3", "Operations", "double-click the department in the map",
     "Authority › Operations", "Design only", ACCENT),
    ("DP06-Entering.png", "4", "R. Mensah, chosen", "double-click the Admin in Who governs",
     "Authority › Operations › R. Mensah", "Design only", ACCENT),
    ("DP07-Held.png", "5", "Holding their workstation", "press Enter — the window does not move",
     "crumb unchanged; the status line changes", "Design only", ACCENT),
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
    <span style="font-family:{SANS};font-size:22px;font-weight:700;color:#fff;">Super User → department → Admin → held</span>
    <span style="font-family:{SANS};font-size:13px;color:{DIM};">one gesture repeated, five times — single click inspects, double click enters, Escape comes back</span>
  </div>
  <div style="font-family:{SANS};font-size:12.5px;color:{FAINT};padding:8px 0 20px 22px;">
    Steps 1–2 are screenshots of the running app. Steps 3–5 are boards, because no QML exists for them yet.
    What to check across the join: the rail, the crumb and the kit should carry, and depth should be told by
    the crumb and the title rather than by restyling.
  </div>
  <div style="display:flex;flex-wrap:wrap;gap:34px 60px;">{cards}</div>
</div>
</body></html>'''

(OUT / "FLOW.html").write_text(html, encoding="utf-8")
print("wrote", OUT / "FLOW.html")
