"""Generates the Falcon Operator design canvas: one .dc.html per screen from a shared shell.

Tokens are defined once here (T) and every artboard is built from the same shell(), so the
visual language is literally defined once and applied everywhere.
"""
import json
import sys
from datetime import datetime, timezone

DARK = "--light" not in sys.argv            # the standard: dark surfaces, gradient frame (python gen.py --light for the old look)
from pathlib import Path

OUT = Path(__file__).parent / "boards"
OUT.mkdir(exist_ok=True)

W, H = 1440, 900

# ------------------------------------------------------------------ tokens
T = dict(
    # the frame: whose authority you are under right now
    frame_native="#24303D", frame_traversing="#7A4A08", frame_occupied="#6B1F24", frame_assisted="#0E5258",
    frame_text="#FFFFFF", frame_dim="rgba(255,255,255,0.68)", frame_faint="rgba(255,255,255,0.42)",
    frame_wash="rgba(255,255,255,0.10)", frame_wash2="rgba(255,255,255,0.18)",
    # the sheet
    ground="#EEF1F5", pane="#FFFFFF",
    side_native="#EAEEF3", side_traversing="#F4EEE3", side_occupied="#F5E9E9", side_assisted="#E4F0F1",
    ink="#1B2430", dim="#4E5A68", faint="#6E7A88",
    line="#DDE2E8", line2="#C5CCD5",
    accent="#2456B3", accent_soft="#E4ECFA",
    ok="#1B7F4E", ok_soft="#DFF3E7",
    warn="#B4650A", warn_soft="#FBEBD3",
    danger="#B92828", danger_soft="#FBE3E3",
    assist="#0E6E77", assist_soft="#DCEFF1",
    su="#B92828", admin="#2456B3", worker="#4E5A68",
    select="#2456B3", select_sub="rgba(255,255,255,0.72)", selectline="rgba(36,86,179,0.45)",
    sans="'IBM Plex Sans', 'Segoe UI', sans-serif", mono="'IBM Plex Mono', Consolas, monospace",
)

if DARK:
    T.update(
        frame_native="#1A1626",              # the solid the gradient starts from; used where a gradient can't go
        ground="#12151C", pane="#1B2028", side_native="#171C25",
        ink="#E8ECF2", dim="#A6B0BC", faint="#7D8896",
        line="#2A313C", line2="#3B4450",
        # four meanings, toned: selected/yours, good, careful, wrong. Nothing else gets a hue.
        accent="#8AA6E0", accent_soft="rgba(138,166,224,0.14)",
        ok="#7FB396", ok_soft="rgba(127,179,150,0.14)",
        warn="#D2A468", warn_soft="rgba(210,164,104,0.15)",
        danger="#DD8A8A", danger_soft="rgba(221,138,138,0.14)",
        assist="#8AA6E0", assist_soft="rgba(138,166,224,0.14)",     # assisted access reads as accent
        su="#C9CFD8", admin="#C9CFD8", worker="#C9CFD8",            # avatars are neutral; state is said by icons
        select="#33446B", select_sub="rgba(255,255,255,0.68)", selectline="rgba(138,166,224,0.40)",
    )
    SIDE = {k: T["side_native"] for k in ("native", "traversing", "occupied", "assisted")}
    # dark to purplish, angled: ink at the top left, violet at the bottom right
    GRADIENT = "linear-gradient(155deg, #121220 0%, #2A1F50 45%, #4B2F8A 100%)"
    FRAME = {k: GRADIENT for k in ("native", "traversing", "occupied", "assisted")}
else:
    FRAME = {k: T["frame_native"] for k in ("native", "traversing", "occupied", "assisted")}   # one frame, always
SIDE = {k: T["side_native"] for k in ("native", "traversing", "occupied", "assisted")}

# ------------------------------------------------------------------ icons (inline stroke svg)
ICONS = {
    "home": '<path d="M12 3v4M5 11h14M5 11v-2a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2v2M5 11v3M12 11v3M19 11v3M3 17h4v4H3zM10 17h4v4h-4zM17 17h4v4h-4z"/>',
    "tasks": '<path d="M9 11l2 2 4-4"/><rect x="3" y="3" width="18" height="18" rx="3"/>',
    "flows": '<circle cx="5" cy="6" r="2.2"/><circle cx="19" cy="6" r="2.2"/><circle cx="19" cy="18" r="2.2"/><path d="M7.2 6h9.6M12 6v12h4.8"/>',
    "automation": '<path d="M13 2L4 14h7l-1 8 9-12h-7l1-8z"/>',
    "assistance": '<path d="M4 5h16v11H9l-5 4V5z"/><path d="M8 9h8M8 12h5"/>',
    "reports": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 12h6M9 16h6"/>',
    "search": '<circle cx="11" cy="11" r="6.5"/><path d="M16 16l5 5"/>',
    "back": '<path d="M15 5l-7 7 7 7"/>',
    "fwd": '<path d="M9 5l7 7-7 7"/>',
    "min": '<path d="M5 12h14"/>',
    "close": '<path d="M6 6l12 12M18 6L6 18"/>',
    "clock": '<circle cx="12" cy="12" r="8.5"/><path d="M12 7.5V12l3 2"/>',
    "chev": '<path d="M9 6l6 6-6 6"/>',
    "chevd": '<path d="M6 9l6 6 6-6"/>',
    "chart": '<path d="M4 19V9M10 19V5M16 19v-6M22 19H2"/>',
    "plus": '<path d="M12 5v14M5 12h14"/>',
    "check": '<path d="M5 12l5 5 9-10"/>',
    "x": '<path d="M6 6l12 12M18 6L6 18"/>',
    "lock": '<rect x="5" y="11" width="14" height="10" rx="2"/><path d="M8 11V8a4 4 0 0 1 8 0v3"/>',
    "eye": '<path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7-10-7-10-7z"/><circle cx="12" cy="12" r="3"/>',
    "folder": '<path d="M3 6h6l2 2h10v11H3z"/>',
    "file": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4"/>',
    "pin": '<path d="M12 2l3 7 6 1-4.5 4.5L18 21l-6-3.5L6 21l1.5-6.5L3 10l6-1z"/>',
    "play": '<path d="M7 4l12 8-12 8z"/>',
    "stop": '<rect x="6" y="6" width="12" height="12" rx="2"/>',
    "warn": '<path d="M12 3l10 18H2z"/><path d="M12 10v4M12 17.5v.5"/>',
    "arrow": '<path d="M4 12h16M14 6l6 6-6 6"/>',
    "bell": '<path d="M6 16V11a6 6 0 0 1 12 0v5l2 2H4z"/><path d="M10 21h4"/>',
    "user": '<circle cx="12" cy="8" r="4"/><path d="M4 21a8 8 0 0 1 16 0"/>',
    "monitor": '<rect x="3" y="4" width="18" height="12" rx="2"/><path d="M8 20h8M12 16v4"/>',
    "dept": '<path d="M3 21h18M5 21V8l7-4 7 4v13"/><path d="M9 21v-5h6v5M9 11h2M13 11h2"/>',
    "ping": '<circle cx="12" cy="12" r="3"/><path d="M5.6 5.6a9 9 0 0 0 0 12.8M18.4 5.6a9 9 0 0 1 0 12.8"/>',
    "ext": '<path d="M12 5v14M5 12h14"/>',
    "pause": '<path d="M8 5v14M16 5v14"/>',
    "branch": '<circle cx="6" cy="5" r="2"/><circle cx="6" cy="19" r="2"/><circle cx="18" cy="9" r="2"/><path d="M6 7v10M6 12c0-3 3-3 6-3h4"/>',
    "shield": '<path d="M12 3l8 3v6c0 5-3.5 8-8 9-4.5-1-8-4-8-9V6z"/>',
    "camera": '<path d="M4 8h4l2-3h4l2 3h4v11H4z"/><circle cx="12" cy="13" r="3.5"/>',
    "pulse": '<path d="M3 12h3.5l2-7 3.5 14 2.5-7H21"/>',
    "keyboard": '<rect x="2" y="6" width="20" height="12" rx="2"/><path d="M6 10h.01M10 10h.01M14 10h.01M18 10h.01M7 14h10"/>',
    "globe": '<circle cx="12" cy="12" r="9"/><path d="M3 12h18M12 3c2.6 3 2.6 15 0 18M12 3c-2.6 3-2.6 15 0 18"/>',
    "cpu": '<rect x="4" y="4" width="16" height="16" rx="3"/><rect x="9" y="9" width="6" height="6"/><path d="M9 2v2M15 2v2M9 20v2M15 20v2M2 9h2M2 15h2M20 9h2M20 15h2"/>',
    "window": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M3 9h18M6.5 6.5h.01M9.5 6.5h.01"/>',
    "key": '<circle cx="8" cy="12" r="4"/><path d="M12 12h9M18 12v4"/>',
    "filewatch": '<path d="M6 3h8l4 4v5"/><path d="M14 3v4h4"/><circle cx="15" cy="16" r="4"/><path d="M18 19l3 3"/>',
    "power": '<path d="M12 3v9"/><path d="M6.5 7a8 8 0 1 0 11 0"/>',
    "terminal": '<rect x="3" y="4" width="18" height="16" rx="2"/><path d="M7 9l3 3-3 3M13 15h4"/>',
}


def ic(name, size=16, color="currentColor", sw=1.75):
    return (f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="{sw}" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{ICONS[name]}</svg>')


# ------------------------------------------------------------------ primitives
def s(**kw):
    """inline style from kwargs; underscores -> hyphens"""
    return " ".join(f"{k.replace('_', '-')}: {v};" for k, v in kw.items())


def row(*children, gap=8, align="center", justify="flex-start", extra="", tag="div", attrs=""):
    return f'<{tag} {attrs} style="display: flex; align-items: {align}; justify-content: {justify}; gap: {gap}px; {extra}">{"".join(children)}</{tag}>'


def col(*children, gap=8, extra="", tag="div", attrs=""):
    return f'<{tag} {attrs} style="display: flex; flex-direction: column; gap: {gap}px; {extra}">{"".join(children)}</{tag}>'


def txt(text, size=13, color=None, weight=400, mono=False, extra=""):
    color = color or T["ink"]
    fam = T["mono"] if mono else T["sans"]
    return f'<span style="font-family: {fam}; font-size: {size}px; font-weight: {weight}; color: {color}; line-height: 1.35; {extra}">{text}</span>'


def chip(text, tone="neutral", size=11, dot=False, mono=False, pulse=False):
    fills = {
        "neutral": (T["ground"], T["dim"]), "accent": (T["accent_soft"], T["accent"]), "ok": (T["ok_soft"], T["ok"]),
        "warn": (T["warn_soft"], T["warn"]), "danger": (T["danger_soft"], T["danger"]), "assist": (T["assist_soft"], T["assist"]),
        "su": (T["ground"], T["dim"]), "admin": (T["ground"], T["dim"]), "worker": (T["ground"], T["dim"]),
    }
    bg, fg = fills[tone]
    d = f'<span style="width: 6px; height: 6px; border-radius: 3px; background: {fg}; display: inline-block;"></span>' if dot else ""
    fam = T["mono"] if mono else T["sans"]
    ring = f"box-shadow: 0 0 0 3px {bg};" if pulse else ""
    return (f'<span style="display: inline-flex; align-items: center; gap: 6px; padding: 2px 8px; border-radius: 999px; '
            f'background: {bg}; color: {fg}; font-family: {fam}; font-size: {size}px; font-weight: 500; line-height: 1.5; white-space: nowrap; {ring}">{d}{text}</span>')


def btn(text, kind="secondary", icon=None, size="md", extra=""):
    pad = "5px 12px" if size == "md" else "3px 9px"
    fs = 13 if size == "md" else 12
    styles = {
        "primary": f"background: {'#2456B3' if not DARK else '#3B6FE0'}; color: #fff; border: 1px solid transparent;",
        "secondary": f"background: {T['pane']}; color: {T['ink']}; border: 1px solid {T['line2']};",
        "danger": f"background: #B92828; color: #fff; border: 1px solid transparent;",
        "warn": f"background: #B4650A; color: #fff; border: 1px solid transparent;",
        "ghost": f"background: transparent; color: {T['dim']}; border: 1px solid transparent;",
        "frame": f"background: {T['frame_wash2']}; color: #fff; border: 1px solid rgba(255,255,255,0.22);",
        "frameghost": f"background: transparent; color: {T['frame_dim']}; border: 1px solid transparent;",
    }[kind]
    i = ic(icon, 14) if icon else ""
    return (f'<button type="button" style="display: inline-flex; align-items: center; gap: 6px; padding: {pad}; border-radius: 6px; '
            f'font-family: {T["sans"]}; font-size: {fs}px; font-weight: 500; line-height: 1.4; cursor: pointer; white-space: nowrap; {styles} {extra}">{i}{text}</button>')


def iconbtn(icon, label, kind="frame", size=28, extra=""):
    color = "#fff" if kind == "frame" else T["dim"]
    bg = "transparent"
    return (f'<button type="button" aria-label="{label}" style="width: {size}px; height: {size}px; display: inline-flex; align-items: center; '
            f'justify-content: center; border-radius: 6px; border: 0; background: {bg}; color: {color}; cursor: pointer; {extra}">{ic(icon, 16)}</button>')


def dot(color, size=8, hollow=False):
    if hollow:
        return f'<span style="width: {size}px; height: {size}px; border-radius: {size}px; border: 1.5px solid {color}; display: inline-block; box-sizing: border-box; flex: none;"></span>'
    return f'<span style="width: {size}px; height: {size}px; border-radius: {size}px; background: {color}; display: inline-block; flex: none;"></span>'


def avatar(initials, tone="admin", size=28):
    bg, fg = (T["line2"], T["ink"]) if DARK else (T["ground"], T["ink"])
    return (f'<span style="width: {size}px; height: {size}px; border-radius: 9px; background: {bg}; color: {fg}; display: inline-flex; '
            f'align-items: center; justify-content: center; font-family: {T["sans"]}; font-size: {max(10, size // 2 - 2)}px; font-weight: 600; flex: none;">{initials}</span>')


def field(label, value, width="100%", mono=False, placeholder=False):
    fam = T["mono"] if mono else T["sans"]
    color = T["faint"] if placeholder else T["ink"]
    return col(
        f'<label style="font-family: {T["sans"]}; font-size: 12px; color: {T["dim"]}; font-weight: 500;">{label}</label>',
        f'<input type="text" value="{value}" style="height: 32px; padding: 0 10px; border: 1px solid {T["line2"]}; border-radius: 6px; font-family: {fam}; font-size: 13px; color: {color}; background: {T["pane"]}; box-sizing: border-box; width: 100%;">',
        gap=4, extra=f"width: {width};")


def hr(color=None, m="0"):
    return f'<div style="height: 1px; background: {color or T["line"]}; margin: {m};"></div>'


def pane_title(text, right=""):
    return row(txt(text, 15, weight=600), f'<span style="flex: 1;"></span>', right, extra="height: 44px; padding: 0 16px; box-sizing: border-box; border-bottom: 1px solid " + T["line"] + "; flex: none;")


def section(title, *children, note="", gap=8, pad="16px", extra=""):
    head = row(txt(title, 13, weight=600) if title else "", (txt(note, 12, T["faint"]) if note else ""), gap=10, extra="flex: none;") if (title or note) else ""
    return col(head, *children, gap=gap, extra=f"padding: {pad}; {extra}")


def pills(items, active, pad="10px 16px 0"):
    """ClassCap's horizontal tab list: one section of the body shows at a time. items = [(label, count)]"""
    out = []
    for label, count in items:
        on = label == active
        bg = T["select"] if on else "transparent"
        fg = "#fff" if on else T["dim"]
        c = f'<span style="margin-left: 6px; opacity: {0.8 if on else 0.7}; font-weight: 400;">{count}</span>' if count != "" else ""
        out.append(f'<a href="#{label.lower().replace(" ", "-")}" style="display: inline-flex; align-items: center; padding: 5px 12px; border-radius: 999px; background: {bg}; color: {fg}; '
                   f'font-family: {T["sans"]}; font-size: 12.5px; font-weight: 500; text-decoration: none; white-space: nowrap;">{label}{c}</a>')
    return row(*out, gap=2, extra=f"padding: {pad}; flex: none;")


def acc(title, *children, open_=True, count="", summary="", pad="0 16px", lead=""):
    """An accordion row: closed, it is one line with a summary; open, it reveals its children."""
    chev = ic("chevd" if open_ else "chev", 14, T["faint"])
    c = txt(count, 11.5, T["faint"]) if count != "" else ""
    sm = txt(summary, 12, T["faint"], extra="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;") if (summary and not open_) else ""
    head = (f'<button type="button" style="display: flex; align-items: center; gap: 10px; width: 100%; height: 42px; padding: 0; border: 0; background: transparent; '
            f'color: {T["ink"]}; font-family: {T["sans"]}; text-align: left; cursor: pointer;">{lead}{txt(title, 13, weight=600, extra="white-space: nowrap;")}{c}'
            f'<span style="flex: 1; min-width: 0; display: flex; justify-content: flex-end;">{sm}</span>{chev}</button>')
    body = col(*children, gap=8, extra="padding: 0 0 14px;") if open_ else ""
    return col(head, body, gap=0, extra=f"padding: {pad}; border-bottom: 1px solid {T['line']};")


def hscroll(title, count, cards, note=""):
    """One row that scrolls sideways. The last card is cut by a fade so it reads as a row, not a grid."""
    head = row(txt(title, 13, weight=600), txt(count, 11.5, T["faint"]), txt(note, 12, T["faint"]) if note else "", '<span style="flex: 1;"></span>',
               iconbtn("back", "Scroll left", kind="pane", size=24), iconbtn("fwd", "Scroll right", kind="pane", size=24), gap=8, extra="padding: 0 16px; height: 36px;")
    strip = (f'<div style="position: relative; overflow: hidden;">'
             f'<div style="display: flex; gap: 10px; padding: 2px 16px 12px; width: max-content;">{"".join(cards)}</div>'
             f'<div style="position: absolute; top: 0; right: 0; bottom: 0; width: 72px; background: linear-gradient(90deg, transparent, {T["pane"]});"></div></div>')
    return col(head, strip, gap=0, extra=f"border-bottom: 1px solid {T['line']}; flex: none;")


def list_row(left, right="", sub="", selected=False, tone=None, extra="", height=44):
    bg = T["accent_soft"] if selected else "transparent"
    main = txt(left, 13, weight=500 if selected else 400)
    subt = txt(sub, 12, T["faint"]) if sub else ""
    return row(col(main, subt, gap=1, extra="flex: 1; min-width: 0;"), right, gap=12,
               extra=f"min-height: {height}px; padding: 6px 16px; box-sizing: border-box; background: {bg}; border-radius: 0; {extra}")


def kv(k, v, mono=False):
    return row(txt(k, 12, T["faint"], extra="width: 110px; flex: none;"), txt(v, 12, T["ink"], mono=mono), gap=8)


# ------------------------------------------------------------------ the shell
NAV = [("home", "Hierarchy"), ("tasks", "Tasks"), ("flows", "Flows"), ("automation", "Automation"), ("assistance", "Assistance"), ("reports", "Reports")]


def icon_rail(active, role):
    items = []
    for key, label in NAV:
        on = key == active
        bg = T["frame_wash2"] if on else "transparent"
        color = "#fff" if on else T["frame_dim"]
        items.append(
            f'<a href="#{key}" aria-label="{label}" style="display: flex; flex-direction: column; align-items: center; gap: 3px; width: 56px; padding: 7px 0 6px; '
            f'border-radius: 10px; background: {bg}; color: {color}; text-decoration: none; font-family: {T["sans"]}; font-size: 10.5px; font-weight: 500;">'
            f'{ic(key, 20, sw=1.6)}<span>{label}</span></a>')
    initials, tone, rlabel = ("SU", "su", "Super User") if role == "su" else ("RM", "admin", "Admin")
    who = col(
        f'<span style="width: 34px; height: 34px; border-radius: 10px; background: #fff; color: {T["frame_native"]}; display: inline-flex; align-items: center; justify-content: center; font-family: {T["sans"]}; font-size: 12px; font-weight: 700;">{initials}</span>',
        txt(rlabel, 10.5, T["frame_dim"], 500, extra="text-align: center; white-space: nowrap;"),
        gap=4, extra="align-items: center;")
    return col(*items, '<span style="flex: 1;"></span>', who, gap=6,
               extra="width: 64px; flex: none; align-items: center; padding: 8px 0 10px; box-sizing: border-box;")


def crumb(text, kind="plain", icon=None):
    if kind == "you":
        bg, color, border = T["frame_wash2"], "#fff", "transparent"
    elif kind == "plain":
        bg, color, border = "transparent", T["frame_dim"], "transparent"
    else:
        bg, color, border = T["frame_wash"], "#fff", "rgba(255,255,255,0.18)"
    i = ic(icon, 13) if icon else ""
    return (f'<span style="display: inline-flex; align-items: center; gap: 6px; padding: 3px 9px; border-radius: 6px; background: {bg}; color: {color}; '
            f'border: 1px solid {border}; font-family: {T["sans"]}; font-size: 12.5px; font-weight: 500; white-space: nowrap;">{i}{text}</span>')


def sep():
    return f'<span style="color: {T["frame_faint"]}; font-size: 13px;">›</span>'


def indicator(text, tone, icon):
    fills = {"warn": T["warn"], "danger": T["danger"], "ok": T["ok"], "assist": T["assist"]}
    c = fills[tone]
    return (f'<button type="button" style="display: inline-flex; align-items: center; gap: 6px; height: 26px; padding: 0 10px 0 8px; border-radius: 999px; '
            f'border: 1px solid rgba(255,255,255,0.25); background: {T["frame_wash"]}; color: #fff; font-family: {T["sans"]}; font-size: 12px; font-weight: 500; cursor: pointer; white-space: nowrap;">'
            f'<span style="width: 7px; height: 7px; border-radius: 4px; background: {c}; box-shadow: 0 0 0 3px {c}55;"></span>{ic(icon, 13)}{text}</button>')


def topbar(crumbs, search_placeholder, indicators, right_extra=""):
    left = row(iconbtn("back", "Back"), iconbtn("fwd", "Forward"), *crumbs, gap=6, extra="flex: none;")
    search = (f'<label aria-label="Search files" style="display: flex; align-items: center; gap: 8px; width: 460px; height: 30px; padding: 0 12px; border-radius: 7px; '
              f'background: {T["frame_wash"]}; border: 1px solid rgba(255,255,255,0.14); color: {T["frame_dim"]}; box-sizing: border-box;">{ic("search", 15)}'
              f'<input class="fs" type="search" placeholder="{search_placeholder}" style="flex: 1; background: transparent; border: 0; outline: 0; color: #fff; font-family: {T["sans"]}; font-size: 13px;"></label>')
    inds = row(*indicators, gap=6)
    win = row(iconbtn("min", "Minimize"), iconbtn("close", "Close"), gap=0)
    return row(left, '<span style="flex: 1;"></span>', search, '<span style="flex: 1;"></span>', inds, right_extra, f'<span style="width: 1px; height: 18px; background: rgba(255,255,255,0.2); margin: 0 6px;"></span>', win,
               gap=10, extra="height: 44px; padding: 0 6px 0 4px; box-sizing: border-box; flex: none;")


def statusbar(state_text, right_text, tone="ok"):
    c = {"ok": "#5CD68C", "danger": "#FF7B7B", "warn": "#FFC46B"}[tone]
    return row(dot(c, 7), txt(state_text, 11.5, T["frame_dim"]), '<span style="flex: 1;"></span>', txt(right_text, 11.5, T["frame_faint"], mono=True),
               gap=8, extra="height: 24px; padding: 0 12px; box-sizing: border-box; flex: none;")


def band(text, tone, *actions):
    bg = {"danger": "#B92828", "warn": "#B4650A", "assist": "#0E6E77"}[tone]      # bands are always the deep solids
    return row(ic({"danger": "warn", "warn": "clock", "assist": "assistance"}[tone], 16, "#fff"), txt(text, 13, "#fff", 600), '<span style="flex: 1;"></span>', *actions,
               gap=10, extra=f"height: 40px; padding: 0 16px; box-sizing: border-box; background: {bg}; flex: none; border-radius: 10px 10px 0 0;")


SHEET_SHADOW = "0 6px 24px rgba(0,0,0,0.45)" if DARK else "0 1px 2px rgba(0,0,0,0.25)"


def sheet(sidebar, page, inspector=None, state="native", band_html="", side_w=280, insp_w=340):
    side = f'<div style="width: {side_w}px; flex: none; background: {SIDE[state]}; display: flex; flex-direction: column; border-right: 1px solid {T["line"]}; overflow: hidden;">{sidebar}</div>'
    main = f'<div style="flex: 1; min-width: 0; display: flex; flex-direction: column; overflow: hidden; background: {T["pane"]};">{page}</div>'
    insp = f'<div style="width: {insp_w}px; flex: none; background: {T["pane"]}; display: flex; flex-direction: column; border-left: 1px solid {T["line"]}; overflow: hidden;">{inspector}</div>' if inspector else ""
    body = f'<div style="display: flex; flex: 1; min-height: 0;">{side}{main}{insp}</div>'
    r = "0 0 10px 10px" if band_html else "10px"
    return (f'<div style="flex: 1; min-width: 0; display: flex; flex-direction: column; margin: 0 8px 0 0;">'
            f'{band_html}<div style="flex: 1; min-height: 0; display: flex; flex-direction: column; background: {T["pane"]}; border-radius: {r}; overflow: hidden; box-shadow: {SHEET_SHADOW};">{body}</div></div>')


def page(title_html, topbar_html, rail_html, sheet_html, status_html, state="native", extra_head=""):
    return f'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{title_html}</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@400;500;600;700&display=swap" rel="stylesheet">
<style>
body{{margin:0;font-family:{T["sans"]};color:{T["ink"]};background:{FRAME[state]}}}
a{{color:{T["accent"]}}}a:hover{{color:#1a4390}}
input,textarea{{background:{T["ground"]};color:{T["ink"]}}}
input::placeholder,textarea::placeholder{{color:{T["faint"]}}}
.fs::placeholder{{color:rgba(255,255,255,0.55)}}
button{{font-family:inherit}}
</style>
</helmet>
<div style="width: {W}px; height: {H}px; box-sizing: border-box; display: flex; flex-direction: column; background: {FRAME[state]}; color: {T["ink"]}; font-family: {T["sans"]}; overflow: hidden;">
{topbar_html}
<div style="display: flex; flex: 1; min-height: 0;">
{rail_html}
{sheet_html}
</div>
{status_html}
</div>
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{{"$preview":{{"width":{W},"height":{H}}}}}'>
class Component extends DCLogic {{
  renderVals() {{ return {{}}; }}
}}
</script>
</body>
</html>
'''


# ------------------------------------------------------------------ shared sidebar: the hierarchy
def sess(kind):
    """the one session vocabulary: free (hollow), native (grey), traversed (amber), assisted (teal), super user (red)"""
    return {"free": dot(T["line2"], 8, hollow=True), "native": dot(T["worker"], 8), "traversed": dot(T["warn"], 8),
            "assisted": dot(T["assist"], 8), "su": dot(T["su"], 8), "you": dot(T["accent"], 8)}[kind]


def tree_row(name, host, session, role="worker", selected=False, depth=1, right="", muted=False):
    pad = 12 + depth * 16
    bg = T["select"] if selected else "transparent"
    fg = "#fff" if selected else T["faint"] if muted else T["ink"]
    icon = ic("user", 14, "#fff" if selected else T["admin"]) if role == "admin" else ""
    return row(sess(session), icon, txt(name, 13, fg, 500 if selected else 400, extra="flex: 1; min-width: 0; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;"),
               txt(host, 11, T["faint"], mono=True) if host else "", right,
               gap=8, extra=f"height: 32px; padding: 0 12px 0 {pad}px; box-sizing: border-box; background: {bg}; border-radius: 6px; margin: 0 6px;")


def dept_head(name, count, open_=True, flag=""):
    return row(ic("chevd" if open_ else "chev", 14, T["faint"]), txt(name, 12.5, T["dim"], 600, extra="flex: 1;"), flag, txt(count, 11, T["faint"]),
               gap=6, extra="height: 30px; padding: 0 12px 0 14px; box-sizing: border-box; margin-top: 6px;")


def sidebar_admin(selected="OPS-07", state="native"):
    head = row(txt("Operations", 15, weight=700, extra="flex: 1;"), iconbtn("plus", "Register a PC", kind="pane", size=26),
               gap=6, extra="height: 44px; padding: 0 10px 0 16px; box-sizing: border-box; flex: none;")
    held = state == "occupied"                    # the Super User holds your session and is on OPS-07
    you = tree_row("You", "WS-OPS-A1", "su" if held else "you", role="admin", depth=0, right=chip("Admin", "admin", 10))
    peer = tree_row("A. Quaye", "WS-OPS-A2", "native", role="admin", depth=0)
    pcs = [
        ("Kojo", "OPS-01", "native"), ("Efua", "OPS-02", "free"), ("Yaw", "OPS-03", "native"), ("Adjoa", "OPS-04", "traversed"),
        ("Nana", "OPS-05", "native"), ("Kwame", "OPS-06", "free"), ("Ama", "OPS-07", "su" if held else "native"),
    ]
    rows = [tree_row(n, h, sm, selected=(h == selected)) for n, h, sm in pcs]
    legend = col(
        row(sess("free"), txt("Free", 11, T["faint"]), sess("native"), txt("At the PC", 11, T["faint"]), sess("traversed"), txt("Entered", 11, T["faint"]), sess("su"), txt("Super User", 11, T["faint"]), gap=6),
        gap=4, extra=f"padding: 10px 16px 12px; border-top: 1px solid {T['line']}; margin-top: auto;")
    return col(head, dept_head("Admins", "2"), you, peer, dept_head("Client PCs", "7"), *rows, legend, gap=2, extra="flex: 1; min-height: 0;")


def sidebar_su(open_dept="Operations", selected=None, inside=False):
    head = row(txt("All departments", 15, weight=700, extra="flex: 1;"), iconbtn("plus", "Create a department", kind="pane", size=26),
               gap=6, extra="height: 44px; padding: 0 10px 0 16px; box-sizing: border-box; flex: none;")
    ops = [dept_head("Operations", "2 admins, 7 PCs", True)]
    ops += [tree_row("R. Mensah", "WS-OPS-A1", "su" if inside else "native", role="admin", selected=(selected == "A1")),
            tree_row("A. Quaye", "WS-OPS-A2", "native", role="admin")]
    if inside:
        # sequential gating: the Admin's PCs appear only once Super User is inside that Admin's session
        ops += [tree_row(n, h, sm, depth=2, selected=(selected == h)) for n, h, sm in [("Kojo", "OPS-01", "native"), ("Efua", "OPS-02", "free"), ("Ama", "OPS-07", "su")]]
        ops += [row(txt("4 more", 11.5, T["faint"]), gap=4, extra="padding: 4px 12px 4px 60px;")]
    else:
        ops += [row(ic("lock", 12, T["faint"]), txt("Client PCs appear once you enter an Admin", 11.5, T["faint"]), gap=6, extra="padding: 4px 12px 6px 44px;")]
    fin = [dept_head("Finance", "1 admin, 4 PCs", False)]
    log = [dept_head("Logistics", "0 admins, 3 PCs", False, chip("No admin", "warn", 10))]
    legend = col(
        row(sess("free"), txt("Free", 11, T["faint"]), sess("native"), txt("At the PC", 11, T["faint"]), sess("traversed"), txt("Entered", 11, T["faint"]), gap=6),
        row(sess("assisted"), txt("Assisted", 11, T["faint"]), sess("su"), txt("You, inside", 11, T["faint"]), gap=6),
        gap=4, extra=f"padding: 10px 16px 12px; border-top: 1px solid {T['line']}; margin-top: auto;")
    return col(head, *ops, *fin, *log, legend, gap=2, extra="flex: 1; min-height: 0;")


# ------------------------------------------------------------------ shared inspector: a PC and its session
def inspector_pc(name="Ama", host="OPS-07", occupied_native=True):
    head = row(avatar("AM", "worker", 32), col(txt(name, 15, weight=600), row(txt(host, 12, T["faint"], mono=True), chip("Worker", "worker", 10), gap=6), gap=2),
               gap=10, extra=f"padding: 14px 16px; border-bottom: 1px solid {T['line']}; flex: none;")
    # the session is a control, not a row
    sess_box = col(
        row(sess("native"), txt("Ama is at the PC", 13, weight=600), '<span style="flex: 1;"></span>', txt("since 08:14", 11.5, T["faint"]), gap=8),
        txt("Entering blocks Ama for the length of your session. She sees the overlay, not who is inside.", 12, T["dim"]),
        row(btn("Block and enter", "primary", "lock"), btn("End her session", "secondary"), gap=8),
        row(ic("clock", 13, T["faint"]), txt("Sessions run 30 min. You can extend from inside.", 11.5, T["faint"]), gap=6),
        gap=10, extra=f"padding: 12px 14px; border: 1px solid {T['line2']}; border-radius: 8px; background: {T['pane']};")
    name_box = col(
        row(txt("Display name", 12, T["dim"], 500), '<span style="flex: 1;"></span>', row(ic("eye", 12, T["faint"]), txt("Only you see this", 11, T["faint"]), gap=4), gap=6),
        f'<input type="text" value="Ama" aria-label="Display name" style="height: 32px; padding: 0 10px; border: 1px solid {T["line2"]}; border-radius: 6px; font-family: {T["sans"]}; font-size: 13px; color: {T["ink"]}; box-sizing: border-box; width: 100%;">',
        txt("Ama sees you as <b>R. Mensah</b>. Change what workers see in your profile.", 11.5, T["faint"]),
        gap=6)
    ids = col(kv("Account", "4021", True), kv("PC", "17", True), kv("Bound since", "2026-03-02", True), kv("Version", "1.4.2  (current)", True), gap=6)
    work = col(
        list_row("Quarterly report", chip("Due 17:00", "warn", 10), "Task, started 09:02", height=40, extra="padding-left: 0; padding-right: 0;"),
        list_row("Payroll to Archive", chip("Syncing", "ok", 10), "Flow destination", height=40, extra="padding-left: 0; padding-right: 0;"),
        list_row("Restricted file found", chip("Open", "danger", 10, dot=True), "Violation in /workers/, 10:41", height=40, extra="padding-left: 0; padding-right: 0;"),
        gap=2)
    actions = row(btn("Ping", "secondary", "ping", "sm"), btn("Assign a task", "secondary", "tasks", "sm"), btn("Run an action", "secondary", "automation", "sm"), gap=6)
    body = col(col(sess_box, extra="padding: 14px 16px 6px;"),
               acc("On this PC", work, open_=True, count="3"),
               acc("Display name", name_box, open_=False, summary="Ama, only you see it"),
               acc("Details", ids, open_=False, summary="account 4021, PC 17, on 1.4.2"),
               gap=0, extra="overflow: hidden;")
    return col(head, body, row(actions, extra=f"padding: 10px 16px; border-top: 1px solid {T['line']}; margin-top: auto; flex: none;"), gap=0, extra="flex: 1; min-height: 0;")


# ================================================================== screens
def screen_admin_home():
    crumbs = [crumb("Operations", "box", "dept"), sep(), crumb("You, at your own level", "you")]
    inds = [indicator("2 pings", "warn", "ping"), indicator("Deadline reached", "danger", "clock"), indicator("Flow failed", "danger", "flows"), indicator("Task done", "ok", "check")]
    top = topbar(crumbs, "Search files in Operations and common", inds)
    rail = icon_rail("home", "admin")

    needs = section("",
        list_row("Kojo pinged for help", row(txt("4 min", 11.5, T["faint"]), btn("Respond", "primary", size="sm"), gap=8), "OPS-01, twice, no channel open", extra="padding-left: 0; padding-right: 0;"),
        list_row("Deadline reached: Quarterly report", row(txt("17:00", 11.5, T["faint"]), btn("Verify", "secondary", size="sm"), gap=8), "Ama, OPS-07. Two of three targets modified today", extra="padding-left: 0; padding-right: 0;"),
        list_row("Flow failed: Payroll to Archive", row(txt("10:52", 11.5, T["faint"]), btn("See the fix", "secondary", size="sm"), gap=8), "Destination unreachable on OPS-03. Other branches still running", extra="padding-left: 0; padding-right: 0;"),
        list_row("Restricted file outside its tier", row(txt("10:41", 11.5, T["faint"]), btn("Open", "secondary", size="sm"), gap=8), "budget-2026.xlsx found in /workers/ on OPS-07", extra="padding-left: 0; padding-right: 0;"), note="4 things stay lit until you address them",
        gap=2)

    def pc_card(name, host, session, line1, foot, tone="neutral", selected=False):
        ring = f"border: 1px solid {T['select']}; box-shadow: 0 0 0 1px {T['select']};" if selected else f"border: 1px solid {T['line']};"
        return col(row(sess(session), txt(name, 13, weight=600, extra="flex: 1;"), txt(host, 11, T["faint"], mono=True), gap=6),
                   txt(line1, 12, T["dim"], extra="flex: 1; line-height: 1.4;"),
                   row(chip(foot, tone, 10, dot=(tone != "neutral")), gap=6),
                   gap=6, extra=f"width: 208px; height: 96px; box-sizing: border-box; padding: 10px 12px; border-radius: 10px; background: {T['ground']}; {ring} flex: none;")
    pcs = hscroll("Client PCs", "7", [
        pc_card("Ama", "OPS-07", "native", "Quarterly report", "Deadline reached", "danger", selected=True),
        pc_card("Kojo", "OPS-01", "native", "Working on Onboarding pack", "Pinged you, 4 min", "warn"),
        pc_card("Efua", "OPS-02", "free", "No one signed in since 07:50", "Free", "neutral"),
        pc_card("Yaw", "OPS-03", "native", "No task in progress", "Flow failing", "danger"),
        pc_card("Adjoa", "OPS-04", "traversed", "You are inside since 10:20", "21:18 left", "warn"),
        pc_card("Nana", "OPS-05", "native", "Working on Invoice batch", "Due Friday", "neutral"),
        pc_card("Kwame", "OPS-06", "free", "No one signed in", "1.4.2 pending", "neutral"),
        f'<a href="#register" style="display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; width: 120px; height: 96px; box-sizing: border-box; border: 1px dashed {T["line2"]}; border-radius: 10px; color: {T["dim"]}; font-size: 12px; text-decoration: none; flex: none;">{ic("plus", 16)}Register a PC</a>',
    ], note="all reachable")
    routed = section("Routed to Operations",
        list_row("Listener report: channel Kojo and you", chip("Seen", "neutral", 10), "Today 09:30", extra="padding-left: 0; padding-right: 0;", height=38),
        list_row("Resource violation on OPS-07", btn("Mark addressed", "secondary", size="sm"), "Today 10:41", extra="padding-left: 0; padding-right: 0;", height=38), note="reports Super User sends your way",
        gap=2)
    ptitle = pane_title("Operations", row(txt("2 Admins, 7 PCs", 12, T["faint"]), btn("Department-wide action", "secondary", "automation", "sm"), gap=10))
    tabs = pills([("Needs you", "4"), ("Routed reports", "2"), ("Activity", "")], "Needs you", pad="12px 16px 0")
    body = col(pcs, tabs, needs, gap=0, extra="overflow: hidden;")
    pg = col(ptitle, body, gap=0, extra="flex: 1; min-height: 0;")
    sh = sheet(sidebar_admin("OPS-07"), pg, inspector_pc())
    status = statusbar("Connected to 127.0.0.1:7400 over TLS, pinned certificate", "session native   engine 1.4.2")
    return page("Admin, at home", top, rail, sh, status, "native")


def screen_su_home():
    crumbs = [crumb("Everything", "you", "shield")]
    inds = [indicator("Ping from R. Mensah", "warn", "ping"), indicator("Rollout stalled", "danger", "warn"), indicator("Assisted access report", "assist", "reports")]
    top = topbar(crumbs, "Search every file in the system", inds)
    rail = icon_rail("home", "su")

    def dept_row(name, admins, pcs, rollout, tone, note=""):
        return row(ic("dept", 16, T["dim"]), col(txt(name, 13, weight=600), txt(note, 12, T["faint"]) if note else "", gap=1, extra="width: 200px;"),
                   txt(admins, 12.5, T["dim"], extra="width: 90px;"), txt(pcs, 12.5, T["dim"], extra="width: 70px;"),
                   col(row(txt(rollout, 12, T["dim"]), gap=4), f'<div style="height: 4px; border-radius: 2px; background: {T["line"]}; width: 160px;"><div style="height: 4px; border-radius: 2px; background: { {"ok": T["ok"], "warn": T["warn"], "danger": T["danger"]}[tone]}; width: {rollout.split("/")[0].strip()}%;"></div></div>', gap=4),
                   '<span style="flex: 1;"></span>', btn("Enter an Admin", "secondary", size="sm"),
                   gap=16, extra=f"height: 52px; padding: 0 16px; box-sizing: border-box; border-bottom: 1px solid {T['line']};")
    head = row(txt("Department", 11.5, T["faint"], 500, extra="width: 224px;"), txt("Admins", 11.5, T["faint"], 500, extra="width: 90px;"), txt("PCs", 11.5, T["faint"], 500, extra="width: 70px;"), txt("On 1.4.2", 11.5, T["faint"], 500), gap=16, extra=f"height: 30px; padding: 0 16px 0 44px; box-sizing: border-box; border-bottom: 1px solid {T['line']}; background: {T['ground']};")
    depts = col(head,
        dept_row("Operations", "2", "7", "86 / 100", "ok"),
        dept_row("Finance", "1", "4", "50 / 100", "warn", "One PC failing since Monday"),
        dept_row("Logistics", "0", "3", "0 / 100", "danger", "No Admin. Nothing pauses, but nobody is accountable"),
        gap=0)
    rollout = section("Rollout 1.4.2",
        row(txt("12 of 14 PCs confirmed. 1.4.3 waits until all 14 are on 1.4.2.", 12.5, T["dim"]), '<span style="flex: 1;"></span>', btn("Notify Finance Admin", "secondary", "bell", "sm"), btn("Approve 1.4.3", "primary", size="sm", extra="opacity: 0.5;"), gap=8), note="approved by you, Mon 08:00")
    audit = section("",
        list_row("You entered R. Mensah, then OPS-04", txt("10:20 to 10:41, 21 min", 11.5, T["faint"], mono=True), "Operations", extra="padding-left: 0; padding-right: 0;", height=38),
        list_row("R. Mensah entered OPS-04", txt("10:20, still inside", 11.5, T["faint"], mono=True), "Operations, 21:18 left", extra="padding-left: 0; padding-right: 0;", height=38),
        list_row("A. Quaye assisted K. Boateng", txt("09:02 to 09:31, 29 min", 11.5, T["faint"], mono=True), "Operations helping Finance, by consent. Reported", extra="padding-left: 0; padding-right: 0;", height=38), note="traversal trail, last 24 hours",
        gap=2)
    ptitle = pane_title("Everything", row(txt("3 departments, 3 Admins, 14 PCs", 12, T["faint"]), btn("Create a department", "secondary", "plus", "sm"), gap=10))
    def dept_card(name, admins, pcs_, pct, tone, foot, selected=False):
        ring = f"border: 1px solid {T['select']}; box-shadow: 0 0 0 1px {T['select']};" if selected else f"border: 1px solid {T['line']};"
        bar = f'<div style="height: 4px; border-radius: 2px; background: {T["line"]};"><div style="height: 4px; border-radius: 2px; background: { {"ok": T["ok"], "warn": T["warn"], "danger": T["danger"]}[tone]}; width: {pct}%;"></div></div>'
        return col(row(ic("dept", 15, T["dim"]), txt(name, 13, weight=600, extra="flex: 1;"), chip(foot, tone, 10, dot=(tone != "ok")) if foot else "", gap=6),
                   row(txt(admins, 12, T["dim"]), txt(pcs_, 12, T["dim"]), '<span style="flex: 1;"></span>', txt(f"{pct} % on 1.4.2", 11.5, T["faint"]), gap=10),
                   bar,
                   gap=8, extra=f"width: 250px; height: 96px; box-sizing: border-box; padding: 10px 12px; border-radius: 10px; background: {T['ground']}; {ring} flex: none; justify-content: space-between;")
    depts_row = hscroll("Departments", "3", [
        dept_card("Operations", "2 Admins", "7 PCs", 86, "ok", "", selected=True),
        dept_card("Finance", "1 Admin", "4 PCs", 50, "warn", "1 PC failing"),
        dept_card("Logistics", "No Admin", "3 PCs", 0, "danger", "No Admin"),
        f'<a href="#create" style="display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; width: 120px; height: 96px; box-sizing: border-box; border: 1px dashed {T["line2"]}; border-radius: 10px; color: {T["dim"]}; font-size: 12px; text-decoration: none; flex: none;">{ic("plus", 16)}Create one</a>',
    ], note="3 Admins, 14 PCs")
    tabs = pills([("Who was where", ""), ("Rollout 1.4.2", "12 of 14"), ("Deviations", "0")], "Who was where", pad="12px 16px 0")
    pg = col(ptitle, depts_row, tabs, audit, gap=0, extra="flex: 1; min-height: 0; overflow: hidden;")

    # inspector: routing, the Super-User-only surface
    insp_head = row(col(txt("Report routing", 15, weight=600), txt("Reports always reach you. Routing adds a department", 12, T["faint"]), gap=2), gap=10, extra=f"padding: 14px 16px; border-bottom: 1px solid {T['line']}; flex: none;")

    def route(cat, to):
        return row(txt(cat, 13, extra="flex: 1;"), *(chip(d, "accent", 10) for d in to), iconbtn("plus", "Add a department", kind="pane", size=24), gap=6, extra=f"height: 38px; border-bottom: 1px solid {T['line']};")
    routes = col(route("Listener report", ["Operations"]), route("Resource violation", ["Operations", "Finance"]), route("Flow failure", []), route("Cross-department assistance", []), route("Deviation", []), gap=0)
    views = section("Addressed by whom",
        list_row("Resource violation, OPS-07", txt("R. Mensah, 10:55", 11.5, T["faint"]), "Marked addressed", extra="padding-left: 0; padding-right: 0;", height=36),
        list_row("Listener report", txt("A. Quaye, 09:40", 11.5, T["faint"]), "Seen, not addressed", extra="padding-left: 0; padding-right: 0;", height=36), note="only you see this", gap=2)
    insp = col(insp_head, col(routes, extra="padding: 0 16px;"), hr(), views, gap=0, extra="flex: 1; min-height: 0;")
    sh = sheet(sidebar_su(), pg, insp)
    status = statusbar("Connected to 127.0.0.1:7400 over TLS, pinned certificate", "session native   engine 1.4.2")
    return page("Super User, at home", top, rail, sh, status, "native")


def screen_traversing():
    # the Super User inside OPS-07 through R. Mensah: amber frame, countdown in the chrome, the page is the Admin's own
    crumbs = [crumb("Operations", "box", "dept"), sep(), crumb("R. Mensah", "box", "user"), sep(), crumb("Ama, OPS-07", "you", "monitor")]
    countdown = row(ic("clock", 14, "#fff"), txt("21:18", 13, "#fff", 600, mono=True), txt("left", 12, T["frame_dim"]), btn("Extend", "frame", size="sm"), btn("Leave", "frame", size="sm"),
                    gap=8, extra=f"height: 30px; padding: 0 6px 0 12px; border-radius: 7px; background: {T['frame_wash']}; border: 1px solid rgba(255,255,255,0.18);")
    inds = [indicator("Ping from R. Mensah", "warn", "ping")]
    top = topbar(crumbs, "Search every file in the system", inds)
    rail = icon_rail("home", "su")

    # the Admin's view of this PC, seen exactly as the Admin sees it, plus the things only Super User can see
    ptitle = pane_title("Ama, OPS-07", row(chip("You are inside as Super User", "warn", 11, dot=True), txt("Everything you do here is logged as you", 12, T["faint"]), gap=10))
    files = section("Files on this PC",
        f'<div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 8px;">'
        + "".join(col(row(ic("folder", 16, T["dim"]), txt(n, 13, weight=500), gap=8), row(chip(t, tone, 10), gap=6) if t else "", txt(c, 11.5, T["faint"]), gap=6,
                       extra=f"padding: 10px 12px; border: 1px solid {T['line']}; border-radius: 8px;")
                  for n, t, tone, c in [("Documents/Reports", "Task target", "accent", "3 files, 2 modified today"), ("resources", "Worker tier", "neutral", "12 files synced"),
                                        ("Personal", "Traversal-restricted", "warn", "Visible to Admins, openable only by you"), ("Projects/Q3", "Common", "neutral", "40 files"),
                                        ("Downloads", "", "neutral", "18 files"), ("HR-Notes", "Traversal-restricted", "warn", "2 files")])
        + "</div>", note="restricted folders open for you; they would not for R. Mensah")
    live = section("Live",
        row(col(txt("Screen", 12, T["faint"]), f'<div style="height: 150px; border-radius: 8px; background: linear-gradient(135deg, #2b3542, #1b2430); display: flex; align-items: center; justify-content: center; color: {T["frame_dim"]}; font-size: 12px;">Screenshot 10:41:02</div>', gap=4, extra="flex: 1;"),
            col(txt("Now", 12, T["faint"]), kv("Active window", "EXCEL.EXE"), kv("Idle", "0 s"), kv("CPU", "23 %"), kv("Memory", "6.1 / 16 GB"), kv("Last input", "just now"), gap=6, extra="width: 300px;"),
            gap=16, align="flex-start"), note="the Admin's dashboard for this PC")
    exp = lambda name, state, tone, sub: row(dot({"ok": T["ok"], "warn": T["warn"]}[tone], 8), txt(name, 12.5, mono=True, extra="width: 180px;"), txt(sub, 12, T["faint"], extra="flex: 1;"), chip(state, tone, 10), gap=10, extra="height: 34px;")
    task = section("Task in progress", exp("q3-report.docx", "Modified", "ok", "12 edits today, last 16:40"), exp("q3-figures.xlsx", "Modified", "ok", "3 edits, last 15:02"), exp("summary.pdf", "Not created", "warn", "expected in Documents/Reports"),
                   row(txt("Quarterly report, deadline reached at 17:00. R. Mensah verifies it; you could too, and it would be logged as you.", 12, T["faint"]), gap=4), note="Quarterly report, Ama, final deadline reached", gap=2)
    tabs = pills([("Files", ""), ("Live", ""), ("Task", "1"), ("Automation", "2 armed")], "Files")
    pg = col(ptitle, tabs, files, gap=0, extra="flex: 1; min-height: 0; overflow: hidden;")

    insp_head = row(avatar("AM", "worker", 32), col(txt("Ama", 15, weight=600), row(txt("OPS-07", 12, T["faint"], mono=True), chip("Worker", "worker", 10), gap=6), gap=2), gap=10, extra=f"padding: 14px 16px; border-bottom: 1px solid {T['line']}; flex: none;")
    sess_box = col(
        row(sess("su"), txt("You hold this session", 13, weight=600), '<span style="flex: 1;"></span>', txt("21:18", 12, T["warn"], 600, mono=True), gap=8),
        txt("Nobody can end or block you out of it. Ama sees the overlay. R. Mensah sees the countdown on his own screen.", 12, T["dim"]),
        row(btn("Extend 30 min", "warn", "clock"), btn("Leave", "secondary"), gap=8),
        gap=10, extra=f"padding: 12px 14px; border: 1px solid {T['warn']}; border-radius: 8px; background: {T['warn_soft']};")
    path = col(txt("How you got here", 12, T["dim"], 500),
               row(txt("Operations", 12.5), ic("chev", 12, T["faint"]), txt("R. Mensah", 12.5), ic("chev", 12, T["faint"]), txt("OPS-07", 12.5, weight=600), gap=4),
               txt("Blocked R. Mensah at 10:20, then entered OPS-07 at 10:22. Both logged.", 11.5, T["faint"]), gap=6)
    names = col(row(txt("Names", 12, T["dim"], 500), gap=4),
                kv("R. Mensah calls her", "Ama"), kv("You call him", "Mensah (Ops)"), txt("Neither name reaches the other side.", 11.5, T["faint"]), gap=6)
    insp = col(insp_head, col(sess_box, hr(), path, hr(), names, gap=14, extra="padding: 14px 16px;"), gap=0, extra="flex: 1; min-height: 0;")
    bnd = band("You are inside OPS-07 through R. Mensah, as Super User. 21:18 left.", "warn", btn("Extend 30 min", "frame", size="sm"), btn("Leave", "frame", size="sm"))
    sh = sheet(sidebar_su(inside=True, selected="OPS-07"), pg, insp, state="traversing", band_html=bnd)
    status = statusbar("Connected to 127.0.0.1:7400 over TLS, pinned certificate", "session traversing   OPS-07 via R. Mensah   21:18 left", "warn")
    return page("Super User, inside a PC", top, rail, sh, status, "traversing")


def screen_occupied():
    # the Admin whose view the Super User is inside: oxblood frame, the red band, nothing to do but wait or claim
    crumbs = [crumb("Operations", "box", "dept"), sep(), crumb("You, at your own level", "you")]
    inds = [indicator("2 pings", "warn", "ping"), indicator("Deadline reached", "danger", "clock")]
    top = topbar(crumbs, "Search files in Operations and common", inds)
    rail = icon_rail("home", "admin")
    bnd = band("Super User in charge. Your view is theirs for 21:18 more.", "danger", btn("Claim native session", "frame", size="sm"), txt("You can't end this; it ends from above.", 12, "rgba(255,255,255,0.8)"))
    ptitle = pane_title("Operations", row(txt("2 Admins, 7 PCs", 12, T["faint"]), gap=10))
    restricted = col(
        ic("lock", 28, T["danger"]),
        txt("Restricted view", 18, weight=600),
        txt("While Super User occupies your session, you can read but not act. Pings, deadlines and failures still light up and stay lit for when you're back.", 13, T["dim"], extra="max-width: 460px; text-align: center;"),
        row(chip("Reading", "danger", 11, dot=True), txt("since 10:20", 12, T["faint"]), gap=8),
        gap=10, extra="flex: 1; align-items: center; justify-content: center; padding: 40px;")
    pg = col(ptitle, restricted, gap=0, extra="flex: 1; min-height: 0;")
    insp_head = row(col(txt("Your session", 15, weight=600), txt("Held from above", 12, T["faint"]), gap=2), gap=10, extra=f"padding: 14px 16px; border-bottom: 1px solid {T['line']}; flex: none;")
    sess_box = col(
        row(sess("su"), txt("Super User is inside", 13, weight=600), '<span style="flex: 1;"></span>', txt("21:18", 12, T["danger"], 600, mono=True), gap=8),
        txt("They entered through your level at 10:20 and are now on OPS-07. When they leave, your session returns to you.", 12, T["dim"]),
        row(btn("Claim native session", "secondary", "lock"), gap=8),
        txt("Claiming succeeds only once the session is free. Try it, and you'll be told.", 11.5, T["faint"]),
        gap=10, extra=f"padding: 12px 14px; border: 1px solid {T['danger']}; border-radius: 8px; background: {T['danger_soft']};")
    still = section("Still yours while you wait",
        list_row("Kojo pinged for help", txt("4 min", 11.5, T["faint"]), "Answer when you're back", extra="padding-left: 0; padding-right: 0;", height=38),
        list_row("Deadline reached: Quarterly report", txt("17:00", 11.5, T["faint"]), "Ama, OPS-07", extra="padding-left: 0; padding-right: 0;", height=38), pad="0", gap=2)
    insp = col(insp_head, col(sess_box, hr(), still, gap=14, extra="padding: 14px 16px;"), gap=0, extra="flex: 1; min-height: 0;")
    sh = sheet(sidebar_admin("OPS-07", "occupied"), pg, insp, state="occupied", band_html=bnd)
    status = statusbar("Connected to 127.0.0.1:7400 over TLS, pinned certificate", "session held by Super User   21:18 left", "danger")
    return page("Admin, occupied from above", top, rail, sh, status, "occupied")


def screen_tasks():
    crumbs = [crumb("Operations", "box", "dept"), sep(), crumb("You, at your own level", "you")]
    inds = [indicator("2 pings", "warn", "ping"), indicator("Deadline reached", "danger", "clock")]
    top = topbar(crumbs, "Search files in Operations and common", inds)
    rail = icon_rail("tasks", "admin")

    # sidebar for tasks: the queue by state
    head = row(txt("Tasks", 15, weight=700, extra="flex: 1;"), btn("New task", "primary", "plus", "sm"), gap=6, extra="height: 44px; padding: 0 10px 0 16px; box-sizing: border-box; flex: none;")

    def trow(name, who, state, tone, selected=False):
        bg = T["select"] if selected else "transparent"
        return row(col(txt(name, 13, "#fff" if selected else None, 500 if selected else 400), txt(who, 11.5, T["select_sub"] if selected else T["faint"]), gap=1, extra="flex: 1; min-width: 0;"), chip(state, tone, 10), gap=8,
                   extra=f"padding: 7px 10px 7px 14px; margin: 0 6px; border-radius: 6px; background: {bg};")
    side = col(head,
        dept_head("Proposed, needs your review", "1"), trow("Q3 supplier reconciliation", "Draft for Nana, OPS-05", "Review", "accent", True),
        dept_head("In progress", "3"), trow("Quarterly report", "Ama, OPS-07", "Deadline", "danger"), trow("Onboarding pack", "Kojo, OPS-01", "Started", "neutral"), trow("Invoice batch", "Nana, OPS-05", "Fri", "neutral"),
        dept_head("Waiting for you to verify", "1"), trow("Fleet inventory", "Yaw, OPS-03", "Done?", "ok"),
        dept_head("Closed", "12"),
        gap=2, extra="flex: 1;")

    # the guided review: the LLM proposed, you decide. Decisions are the page.
    ptitle = pane_title("Q3 supplier reconciliation", row(chip("Proposed by the model", "accent", 11), txt("nothing is assigned until you confirm", 12, T["faint"]), gap=10))
    described = section("What you wrote",
        f'<div style="padding: 12px 14px; border-radius: 8px; background: {T["ground"]}; font-size: 13px; line-height: 1.5; color: {T["ink"]};">Reconcile the Q3 supplier invoices against <mark style="background: {T["accent_soft"]}; color: {T["accent"]}; padding: 0 3px; border-radius: 3px;">suppliers-q3.xlsx</mark> and produce <mark style="background: {T["accent_soft"]}; color: {T["accent"]}; padding: 0 3px; border-radius: 3px;">reconciliation-q3.docx</mark> by <mark style="background: {T["warn_soft"]}; color: {T["warn"]}; padding: 0 3px; border-radius: 3px;">Monday or Wednesday</mark>. Also archive last quarter&#39;s folder.</div>',
        gap=6)

    def decision(n, title, body, actions, tone="neutral", done=False, open_=False, summary=""):
        left = f'<span style="width: 24px; height: 24px; border-radius: 12px; display: inline-flex; align-items: center; justify-content: center; font-size: 12px; font-weight: 600; flex: none; background: {T["ok_soft"] if done else T["warn_soft"] if tone == "warn" else T["ground"]}; color: {T["ok"] if done else T["warn"] if tone == "warn" else T["dim"]};">{ic("check", 13) if done else n}</span>'
        return acc(title, col(body, row(*actions, gap=6) if actions else "", gap=10, extra="padding-left: 34px;"), open_=open_, summary=summary, lead=left, pad="0")
    target_row = lambda icon, name, intent, exp: row(ic(icon, 15, T["dim"]), txt(name, 12.5, mono=True, extra="width: 220px;"), chip(intent, "neutral", 10), txt(exp, 12, T["faint"], extra="flex: 1;"), iconbtn("x", "Remove", kind="pane", size=22), gap=8, extra=f"height: 30px;")
    d1 = decision(1, "Verification targets: two found", col(target_row("file", "suppliers-q3.xlsx", "Modify", "expect edits while she works"), target_row("file", "reconciliation-q3.docx", "Create", "expect it to appear, then grow"),
                                                        gap=2), [btn("Add a target", "secondary", "plus", "sm"), btn("No verification for this task", "ghost", size="sm")], done=True, summary="suppliers-q3.xlsx, reconciliation-q3.docx")
    d2 = decision(2, "Name collision on the file to create", txt("reconciliation-q3.docx already exists on OPS-05 in Documents/Finance, last changed 12 Aug. Creating it again would overwrite.", 12.5, T["dim"]),
                  [btn("Keep the name, overwrite is intended", "secondary", size="sm"), btn("Mean the existing file (Modify)", "secondary", size="sm"), btn("Rename", "secondary", size="sm")], tone="warn", open_=True)
    d3 = decision(3, "The deadline is ambiguous", txt("\u201cMonday or Wednesday\u201d. Pick one, or set both as soft and final.", 12.5, T["dim"]),
                  [btn("Soft Mon 29 Sep, final Wed 1 Oct", "secondary", "clock", "sm"), btn("Final Mon 29 Sep", "secondary", size="sm"), btn("Final Wed 1 Oct", "secondary", size="sm")], tone="warn", summary="\u201cMonday or Wednesday\u201d")
    d4 = decision(4, "This reads as two tasks", txt("\u201cArchive last quarter\u2019s folder\u201d has its own target and no deadline. Split it out, or keep one task.", 12.5, T["dim"]),
                  [btn("Split into two tasks", "secondary", "branch", "sm"), btn("Keep as one", "secondary", size="sm")], summary="\u201cArchive last quarter\u2019s folder\u201d")
    decisions = section("Decide", col(d1, d2, d3, d4, gap=0), note="3 of 4 still open. Each opens when it is next", gap=4, pad="8px 16px 16px")
    foot = row(txt("Assign to", 12.5, T["dim"]), chip("Nana, OPS-05", "worker", 11), '<span style="flex: 1;"></span>', btn("Discard", "ghost"), btn("Confirm and assign", "primary", "check", extra="opacity: 0.5;"), txt("after the 3 open decisions", 12, T["faint"]),
               gap=10, extra=f"padding: 12px 16px; border-top: 1px solid {T['line']}; flex: none;")
    tabs = pills([("Review", "3 open"), ("Targets", "2"), ("Deadline", ""), ("Assignee", "")], "Review")
    pg = col(ptitle, tabs, col(described, hr(), decisions, gap=0, extra="flex: 1; overflow: hidden;"), foot, gap=0, extra="flex: 1; min-height: 0;")

    # inspector: a task in progress with its expectations, and the verify control
    insp_head = row(col(txt("Quarterly report", 15, weight=600), row(txt("Ama, OPS-07", 12, T["faint"]), chip("Deadline reached", "danger", 10, dot=True), gap=6), gap=2), gap=10, extra=f"padding: 14px 16px; border-bottom: 1px solid {T['line']}; flex: none;")
    exp = lambda name, state, tone, sub: row(dot({"ok": T["ok"], "warn": T["warn"], "neutral": T["line2"]}[tone], 8), col(txt(name, 12.5, mono=True), txt(sub, 11.5, T["faint"]), gap=1, extra="flex: 1;"), chip(state, tone, 10), gap=8, extra="height: 40px;")
    stack = section("Expectations",
        exp("q3-report.docx", "Modified", "ok", "12 edits today, last 16:40"), exp("q3-figures.xlsx", "Modified", "ok", "3 edits, last 15:02"), exp("summary.pdf", "Not created", "warn", "expected in Documents/Reports"), note="soft signals, never proof", pad="14px 16px", gap=0)
    verify = col(txt("Only you can close this", 13, weight=600), txt("Check the work at each target, then decide for the whole task.", 12, T["dim"]),
                 row(btn("Open targets on OPS-07", "secondary", "folder", "sm"), gap=6),
                 row(btn("Complete", "primary", "check"), btn("Incomplete", "secondary"), gap=8),
                 gap=8, extra=f"padding: 12px 14px; border: 1px solid {T['line2']}; border-radius: 8px;")
    dl = col(kv("Soft deadline", "Today 15:00, nudged", True), kv("Final deadline", "Today 17:00, reached", True), kv("Started", "09:02", True), kv("Assigned", "Mon 15 Sep", True), gap=6)
    insp = col(insp_head, stack, hr(), col(verify, hr(), dl, gap=14, extra="padding: 14px 16px;"), gap=0, extra="flex: 1; min-height: 0;")
    sh = sheet(side, pg, insp)
    status = statusbar("Connected to 127.0.0.1:7400 over TLS, pinned certificate", "session native   engine 1.4.2")
    return page("Tasks", top, rail, sh, status, "native")


def screen_flows():
    crumbs = [crumb("Operations", "box", "dept"), sep(), crumb("You, at your own level", "you")]
    inds = [indicator("Flow failed", "danger", "flows")]
    top = topbar(crumbs, "Search files in Operations and common", inds)
    rail = icon_rail("flows", "admin")
    head = row(txt("Flows", 15, weight=700, extra="flex: 1;"), btn("New flow", "primary", "plus", "sm"), gap=6, extra="height: 44px; padding: 0 10px 0 16px; box-sizing: border-box; flex: none;")

    def frow(name, sub, state, tone, selected=False):
        bg = T["select"] if selected else "transparent"
        return row(col(txt(name, 13, "#fff" if selected else None, 500 if selected else 400), txt(sub, 11.5, T["select_sub"] if selected else T["faint"]), gap=1, extra="flex: 1; min-width: 0;"), chip(state, tone, 10, dot=(tone == "danger")), gap=8,
                   extra=f"padding: 7px 10px 7px 14px; margin: 0 6px; border-radius: 6px; background: {bg};")
    side = col(head, dept_head("Yours", "4"),
        frow("Payroll to Archive", "You to OPS-03, OPS-05", "Failing", "danger", True), frow("Worker resources", "/workers/ to 7 PCs", "Syncing", "ok"),
        frow("Common resources", "/common/ to everyone", "Syncing", "ok"), frow("Photos to shared", "OPS-02 to you", "Paused", "warn"),
        dept_head("Waiting for consent", "1"), frow("Finance handover", "A. Quaye into your space", "Consent?", "accent"),
        gap=2, extra="flex: 1;")

    # the graph: source -> stages -> destinations, left to right, edges drawn as svg
    def node(title, sub, icon, tone="neutral", w=200, badge=""):
        edge_c = {"neutral": T["line2"], "danger": T["danger"], "ok": T["ok"], "accent": T["accent"], "warn": T["warn"]}[tone]
        return (f'<div style="position: absolute; width: {w}px; box-sizing: border-box; padding: 10px 12px; border: 1px solid {edge_c}; border-radius: 8px; background: {T["pane"]}; display: flex; flex-direction: column; gap: 4px; box-shadow: 0 1px 2px rgba(0,0,0,0.06);">'
                + row(ic(icon, 15, T["dim"]), txt(title, 13, weight=600, extra="flex: 1; white-space: nowrap;"), gap=8) + txt(sub, 11.5, T["faint"], mono=True) + (row(badge, extra="margin-top: 2px;") if badge else "") + "</div>")

    def at(x, y, html):
        return html.replace("position: absolute;", f"position: absolute; left: {x}px; top: {y}px;", 1)
    graph_w, graph_h = 716, 380
    edges = f'''<svg width="{graph_w}" height="{graph_h}" viewBox="0 0 {graph_w} {graph_h}" style="position: absolute; left: 0; top: 0;" aria-hidden="true">
<defs><marker id="ah" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8z" fill="{T['line2']}"/></marker>
<marker id="ahd" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8z" fill="{T['danger']}"/></marker></defs>
<path d="M216 190 C 245 190, 245 190, 270 190" stroke="{T['line2']}" stroke-width="1.75" fill="none" marker-end="url(#ah)"/>
<path d="M450 190 C 480 190, 480 100, 508 100" stroke="{T['line2']}" stroke-width="1.75" fill="none" marker-end="url(#ah)"/>
<path d="M450 190 C 480 190, 480 280, 508 280" stroke="{T['danger']}" stroke-width="1.75" fill="none" stroke-dasharray="5 4" marker-end="url(#ahd)"/>
<path d="M300 100 L 300 100" />
</svg>'''
    nodes = [
        at(16, 156, node("Source", "You  C:\\Payroll\\out", "monitor", "accent", badge=chip("Yours", "admin", 10))),
        at(270, 158, node("Branch", "then Categorize by type", "branch", "neutral", w=180)),
        at(508, 60, node("OPS-05, Nana", "D:\\Archive\\payroll", "monitor", "ok", badge=chip("Synced 10:50", "ok", 10))),
        at(508, 240, node("OPS-03, Yaw", "D:\\Archive\\payroll", "monitor", "danger", badge=chip("Failing", "danger", 10, dot=True))),
        f'<a href="#add" style="position: absolute; left: 508px; top: 336px; display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; border: 1px dashed {T["line2"]}; border-radius: 8px; color: {T["dim"]}; font-size: 12px; text-decoration: none;">{ic("plus", 13)}Add a destination</a>',
        f'<a href="#stage" style="position: absolute; left: 270px; top: 236px; display: inline-flex; align-items: center; gap: 6px; padding: 6px 10px; border: 1px dashed {T["line2"]}; border-radius: 8px; color: {T["dim"]}; font-size: 12px; text-decoration: none;">{ic("plus", 13)}Transform before the branch</a>',
        f'<div style="position: absolute; left: 16px; top: 16px; display: flex; gap: 6px;">{chip("One direction: left to right", "neutral", 10)}{chip("No cycles", "ok", 10)}{chip("1 collision resolved", "neutral", 10)}</div>',
    ]
    graph = f'<div style="position: relative; width: {graph_w}px; height: {graph_h}px; border-radius: 10px; background: {T["ground"]}; background-image: radial-gradient({T["line2"]} 1px, transparent 1px); background-size: 16px 16px; overflow: hidden; flex: none;">{edges}{"".join(nodes)}</div>'
    ptitle = pane_title("Payroll to Archive", row(chip("Failing on one branch", "danger", 11, dot=True), btn("Pause", "secondary", "pause", "sm"), btn("Sync now", "secondary", "play", "sm"), gap=8))
    fix = col(txt("D:\\Archive\\payroll on OPS-03 is not reachable. The OPS-05 branch keeps running. This won't clear on its own.", 12.5, T["dim"]),
              row(txt("Suggested fix", 12, T["dim"], 500), txt("Check that D: is mounted on OPS-03, then the branch resumes by itself. Or move this destination.", 12.5), gap=8, align="flex-start"),
              row(btn("Ping Yaw", "secondary", "ping", "sm"), btn("Enter OPS-03", "secondary", "lock", "sm"), btn("Move destination", "secondary", size="sm"), gap=6),
              gap=8, extra=f"padding: 12px 14px; border: 1px solid {T['danger']}; border-radius: 8px; background: {T['danger_soft']};")
    tabs = pills([("Graph", ""), ("Sync log", "5"), ("Conflicts", "1"), ("Stages", "2")], "Graph")
    fix_acc = acc("1 branch failing: OPS-03", fix, open_=True, summary="since 10:52", pad="0 16px", lead=dot(T["danger"], 8))
    pg = col(ptitle, tabs, col(graph, extra="padding: 10px 16px 0;"), fix_acc, gap=0, extra="flex: 1; min-height: 0; overflow: hidden;")

    insp_head = row(col(txt("History", 15, weight=600), txt("this flow, newest first", 12, T["faint"]), gap=2), gap=10, extra=f"padding: 14px 16px; border-bottom: 1px solid {T['line']}; flex: none;")
    ev = lambda t, what, sub, tone="neutral": row(txt(t, 11.5, T["faint"], mono=True, extra="width: 42px; flex: none;"), dot({"neutral": T["line2"], "ok": T["ok"], "danger": T["danger"], "warn": T["warn"]}[tone], 8), col(txt(what, 12.5), txt(sub, 11.5, T["faint"]), gap=1), gap=10, align="flex-start", extra="padding: 6px 0;")
    hist = col(ev("10:52", "Sync failed to OPS-03", "destination unreachable", "danger"), ev("10:50", "Synced 14 files to OPS-05", "1.2 MB", "ok"),
               ev("10:12", "Conflict on OPS-05", "payroll-sept.csv changed outside the flow. Kept as payroll-sept-modified.csv, fresh copy synced", "warn"),
               ev("09:30", "Synced 3 files to both", "", "ok"), ev("Mon", "You confirmed the collision", "D:\\Archive\\payroll\\readme.txt existed on OPS-05. Overwrite intended", "neutral"),
               gap=0, extra="padding: 8px 16px;")
    consent = section("Consent",
        kv("OPS-05, Nana", "Your authority, no consent needed"), kv("OPS-03, Yaw", "Your authority, no consent needed"),
        txt("A destination in another Admin's space or above you would wait here until they accept.", 11.5, T["faint"]), note="who agreed to receive", gap=6)
    insp = col(insp_head, hist, hr(), consent, gap=0, extra="flex: 1; min-height: 0;")
    sh = sheet(side, pg, insp)
    status = statusbar("Connected to 127.0.0.1:7400 over TLS, pinned certificate", "session native   engine 1.4.2")
    return page("Flows", top, rail, sh, status, "native")


def screen_automation():
    crumbs = [crumb("Operations", "box", "dept"), sep(), crumb("You, at your own level", "you")]
    inds = [indicator("2 pings", "warn", "ping")]
    top = topbar(crumbs, "Search files in Operations and common", inds)
    rail = icon_rail("automation", "admin")
    # the mode switch is the sidebar head: Dashboard (live) or Editing (Events, Control, Monitoring, Custom)
    seg = row(f'<a href="#dash" style="flex: 1; text-align: center; padding: 5px 0; border-radius: 6px; background: {T["pane"]}; color: {T["ink"]}; font-size: 12.5px; font-weight: 600; text-decoration: none; box-shadow: 0 1px 2px rgba(0,0,0,0.08);">Dashboard</a>',
              f'<a href="#edit" style="flex: 1; text-align: center; padding: 5px 0; border-radius: 6px; color: {T["dim"]}; font-size: 12.5px; font-weight: 500; text-decoration: none;">Editing</a>',
              gap=2, extra=f"padding: 3px; border-radius: 8px; background: {T['line']}; margin: 8px 12px 4px;")
    head = row(txt("Automation", 15, weight=700, extra="flex: 1;"), gap=6, extra="height: 44px; padding: 0 10px 0 16px; box-sizing: border-box; flex: none;")

    def erow(name, sub, n="", selected=False):
        bg = T["select"] if selected else "transparent"
        return row(ic("automation", 14, "#fff" if selected else T["dim"]), col(txt(name, 13, "#fff" if selected else None, 500 if selected else 400), txt(sub, 11.5, T["select_sub"] if selected else T["faint"]), gap=1, extra="flex: 1; min-width: 0;"), txt(n, 11, T["select_sub"] if selected else T["faint"]), gap=8,
                   extra=f"padding: 7px 10px 7px 14px; margin: 0 6px; border-radius: 6px; background: {bg};")
    side = col(head, seg, dept_head("Running now", "2"), erow("USB inserted", "screenshot, then log", "1 running", True), erow("Idle over 20 min", "system metrics", "1 running"),
               dept_head("Armed", "5"), erow("Login", "screenshot"), erow("File change in Documents", "index, stalk"), erow("Every day 17:30", "shutdown warning"), erow("CPU over 90 % for 5 min", "process list"), erow("Logout", "clear temp (custom)"),
               gap=2, extra="flex: 1;")

    ptitle = pane_title("Dashboard", row(txt("live, this department", 12, T["faint"]), gap=10))
    tabs = pills([("All", "6"), ("Running", "2"), ("Done", "2"), ("Timeout", "1"), ("Error", "1")], "All")

    def run(name, pc, action, started, state, tone, out, timeout="60 s", open_=False, detail=""):
        lead = dot({"ok": T["ok"], "warn": T["warn"], "danger": T["danger"], "accent": T["accent"]}[tone], 8) + chip(state, tone, 10)
        summary = f"{action} on {pc}, {started}, {out}"
        body = col(row(txt("Started", 12, T["faint"], extra="width: 90px;"), txt(started, 12.5, mono=True), gap=8),
                   row(txt("Timeout", 12, T["faint"], extra="width: 90px;"), txt(timeout, 12.5, mono=True), txt("independent of the other actions on this event", 12, T["faint"]), gap=8),
                   row(txt("Result", 12, T["faint"], extra="width: 90px;"), txt(out, 12.5), gap=8),
                   (f'<pre style="margin: 4px 0 0; padding: 10px 12px; border-radius: 6px; background: {T["ground"]}; color: {T["ink"]}; font-family: {T["mono"]}; font-size: 11.5px; line-height: 1.5; overflow: hidden;">{detail}</pre>' if detail else ""),
                   row(btn("Terminate", "secondary", "stop", "sm") if tone == "accent" else btn("Run again", "secondary", "play", "sm"), btn("Open the event", "ghost", size="sm"), gap=6),
                   gap=6, extra="padding-left: 18px;")
        return acc(name, body, open_=open_, summary=summary, lead=lead, pad="0 16px")
    runs = col(
        run("USB inserted", "OPS-02", "Screenshot", "10:58:12", "Running", "accent", "12 s in", "30 s"),
        run("Idle over 20 min", "OPS-06", "System metrics", "10:55:00", "Running", "accent", "every 10 s, 18 samples", "10 min"),
        run("USB inserted", "OPS-02", "Log event", "10:58:12", "Done", "ok", "1 line written"),
        run("Login", "OPS-04", "Screenshot", "10:20:03", "Done", "ok", "1 image, 340 KB"),
        run("CPU over 90 % for 5 min", "OPS-03", "Process list", "10:02:40", "Timeout", "warn", "no reply in 60 s. Not an error", "60 s"),
        run("Logout", "OPS-01", "clear temp", "Mon 17:31", "Error", "danger", "exit 1", open_=True,
            detail="Remove-Item : Access to the path &#39;C:\\Temp\\lock&#39; is denied.\nAt line:2 char:3\n+   Remove-Item -Force -ErrorAction Stop\nexit code 1"),
        gap=0)
    pg = col(ptitle, tabs, col(runs, extra="padding-top: 6px;"), gap=0, extra="flex: 1; min-height: 0; overflow: hidden;")

    # inspector: editing an event, actions attached run independently
    insp_head = row(col(txt("USB inserted", 15, weight=600), row(chip("Native event", "neutral", 10), txt("armed on 7 PCs", 12, T["faint"]), gap=6), gap=2), gap=10, extra=f"padding: 14px 16px; border-bottom: 1px solid {T['line']}; flex: none;")
    act = lambda name, kind, to, tone="neutral": row(ic("camera" if kind == "Monitoring" else "automation" if kind == "Control" else "file", 15, T["dim"]), col(txt(name, 12.5, weight=500), txt(f"{kind}, timeout {to}", 11.5, T["faint"]), gap=1, extra="flex: 1;"), iconbtn("x", "Detach", kind="pane", size=22), gap=8, extra=f"height: 40px; padding: 0 10px; border: 1px solid {T['line']}; border-radius: 6px;")
    actions = section("Actions when it fires",
        act("Screenshot", "Monitoring", "30 s"), act("Log event", "Control", "10 s"), act("clear temp", "Custom, PowerShell", "60 s"),
        row(btn("Attach an action", "secondary", "plus", "sm"), gap=6), note="each on its own", pad="14px 16px", gap=6)
    custom = col(row(txt("clear temp", 13, weight=600), chip("Validated", "ok", 10), gap=8), txt("PowerShell, stdlib and Windows only. Checked here before send, and again on the PC.", 12, T["dim"]),
                 f'<pre style="margin: 0; padding: 10px 12px; border-radius: 6px; background: {T["ground"]}; color: {T["ink"]}; font-family: {T["mono"]}; font-size: 11.5px; line-height: 1.5; overflow: hidden;">Get-ChildItem C:\\Temp -Recurse |\n  Remove-Item -Force -ErrorAction Stop</pre>',
                 gap=6, extra=f"padding: 12px 14px; border: 1px solid {T['line2']}; border-radius: 8px;")
    insp = col(insp_head, actions, hr(), col(custom, gap=0, extra="padding: 14px 16px;"), gap=0, extra="flex: 1; min-height: 0;")
    sh = sheet(side, pg, insp)
    status = statusbar("Connected to 127.0.0.1:7400 over TLS, pinned certificate", "session native   engine 1.4.2")
    return page("Automation", top, rail, sh, status, "native")


def screen_assistance():
    crumbs = [crumb("Operations", "box", "dept"), sep(), crumb("You, at your own level", "you")]
    inds = [indicator("2 pings", "warn", "ping"), indicator("Help offered", "assist", "assistance")]
    top = topbar(crumbs, "Search files in Operations and common", inds)
    rail = icon_rail("assistance", "admin")
    head = row(txt("Assistance", 15, weight=700, extra="flex: 1;"), gap=6, extra="height: 44px; padding: 0 10px 0 16px; box-sizing: border-box; flex: none;")

    def crow(name, sub, right="", selected=False, tone=None):
        bg = T["select"] if selected else "transparent"
        return row(avatar(name[:2].upper(), "worker" if tone is None else tone, 24), col(txt(name, 13, "#fff" if selected else None, 500 if selected else 400), txt(sub, 11.5, T["select_sub"] if selected else T["faint"]), gap=1, extra="flex: 1; min-width: 0;"), right, gap=8,
                   extra=f"padding: 6px 10px 6px 14px; margin: 0 6px; border-radius: 6px; background: {bg};")
    side = col(head,
        dept_head("Pings, unanswered", "2"), crow("Kojo", "OPS-01, 4 min ago, twice", chip("2", "warn", 10)), crow("Nana", "OPS-05, 12 min ago", chip("1", "warn", 10)),
        dept_head("Open channels", "2"), crow("Ama", "your turn", chip("Your turn", "accent", 10), True), crow("Yaw", "waiting on Yaw", txt("10:31", 11, T["faint"])),
        dept_head("Listening in", "1"), crow("A. Quaye and Efua", "you were added by A. Quaye", ic("eye", 14, T["faint"]), tone="admin"),
        dept_head("Cross-department help", ""),
        col(row(sess("assisted"), txt("K. Boateng, Finance", 12.5, weight=500), gap=6), txt("Offers to help. Accepting opens an assisted session with a narrowed ceiling, not a traversal.", 11.5, T["faint"]),
            row(btn("Accept", "secondary", size="sm", extra=f"border-color: {T['assist']}; color: {T['assist']};"), btn("Decline", "ghost", size="sm"), gap=6),
            gap=6, extra=f"margin: 2px 12px; padding: 10px 12px; border: 1px solid {T['assist']}; border-radius: 8px; background: {T['assist_soft']};"),
        row(txt("You are", 12, T["dim"]), chip("reachable for help", "assist", 10), gap=6, extra="padding: 8px 16px; margin-top: auto;"),
        gap=2, extra="flex: 1;")

    # the channel reads as a conversation, with the turn lock made visible
    ptitle = pane_title("Ama", row(chip("Turn-based", "neutral", 10), txt("one message each, then the other", 12, T["faint"]), '<span style="width: 12px;"></span>', btn("Add a listener", "secondary", "eye", "sm"), btn("Close channel", "secondary", "x", "sm"), gap=8))

    def msg(who, tone, t, text, mine=False):
        return row(avatar(who[:2].upper(), tone, 30), col(row(txt(who, 13, weight=600), txt(t, 11.5, T["faint"]), gap=8), txt(text, 13.5, extra="line-height: 1.5;"), gap=3, extra="flex: 1;"),
                   gap=10, align="flex-start", extra=f"padding: 8px 16px; {'background: ' + T['ground'] + ';' if mine else ''}")
    sysline = lambda t: row('<span style="flex: 1; height: 1px; background: ' + T["line"] + ';"></span>', txt(t, 11.5, T["faint"]), '<span style="flex: 1; height: 1px; background: ' + T["line"] + ';"></span>', gap=10, extra="padding: 6px 16px;")
    convo = col(
        sysline("Ama pinged at 10:02. You responded at 10:05, which opened this channel"),
        msg("Ama", "worker", "10:05", "The figures sheet keeps asking for a password when I open it from Documents/Reports. I tried twice."),
        msg("You", "admin", "10:07", "That sheet is restricted. It was synced there by mistake. I\u2019ll move it back and send you an unlocked copy.", mine=True),
        msg("Ama", "worker", "10:09", "Thanks. I need it before 17:00 for the report."),
        sysline("You added A. Quaye as a listener at 10:10. Ama can\u2019t see listeners you add"),
        gap=0, extra="flex: 1; overflow: hidden; padding-top: 8px;")
    composer = col(row(chip("Your turn", "accent", 10, dot=True), txt("Ama is locked until you send", 12, T["faint"]), gap=8),
                   row(f'<input type="text" placeholder="Reply to Ama" aria-label="Reply" style="flex: 1; height: 36px; padding: 0 12px; border: 1px solid {T["line2"]}; border-radius: 8px; font-family: {T["sans"]}; font-size: 13px; color: {T["ink"]};">', btn("Send", "primary"), gap=8),
                   gap=8, extra=f"padding: 12px 16px; border-top: 1px solid {T['line']}; flex: none;")
    pg = col(ptitle, convo, composer, gap=0, extra="flex: 1; min-height: 0;")

    insp_head = row(col(txt("File search", 15, weight=600), txt("your restricted, workers, common and all admin-tier files", 12, T["faint"]), gap=2), gap=10, extra=f"padding: 14px 16px; border-bottom: 1px solid {T['line']}; flex: none;")
    q = f'<label style="display: flex; align-items: center; gap: 8px; height: 34px; padding: 0 10px; border: 1px solid {T["line2"]}; border-radius: 8px; margin: 12px 16px 4px; color: {T["faint"]};">{ic("search", 15)}<input type="search" value="q3 figures" aria-label="Search files" style="flex: 1; border: 0; outline: 0; font-family: {T["sans"]}; font-size: 13px; color: {T["ink"]};"></label>'
    res = lambda name, where, tier, tone: row(ic("file", 15, T["dim"]), col(txt(name, 12.5, mono=True), txt(where, 11.5, T["faint"]), gap=1, extra="flex: 1; min-width: 0;"), chip(tier, tone, 10), gap=8, extra="height: 44px; padding: 0 16px;")
    results = col(res("q3-figures.xlsx", "OPS-07  Documents/Reports", "Task target", "accent"), res("q3-figures-locked.xlsx", "You  /restricted/", "Restricted", "danger"), res("figures-template.xlsx", "You  /common/", "Common", "neutral"), res("q3-figures.xlsx", "A. Quaye  /workers/", "Worker tier", "neutral"), gap=0)
    insp = col(insp_head, q, txt("4 files", 11.5, T["faint"], extra="padding: 4px 16px 6px;"), results, gap=0, extra="flex: 1; min-height: 0;")
    sh = sheet(side, pg, insp)
    status = statusbar("Connected to 127.0.0.1:7400 over TLS, pinned certificate", "session native   engine 1.4.2")
    return page("Assistance", top, rail, sh, status, "native")


def screen_assisted():
    # the peer-help mode: teal frame, the ceiling made visible, no eviction, either party ends it
    crumbs = [crumb("Finance", "box", "dept"), sep(), crumb("Helping K. Boateng", "you", "assistance")]
    ceiling = row(ic("shield", 14, "#fff"), txt("Ceiling: files and screen only", 12.5, "#fff", 500), btn("End help", "frame", size="sm"), gap=8, extra=f"height: 30px; padding: 0 6px 0 12px; border-radius: 7px; background: {T['frame_wash']}; border: 1px solid rgba(255,255,255,0.18);")
    top = topbar(crumbs, "Search files in Operations and common", [indicator("2 pings", "warn", "ping")])
    rail = icon_rail("assistance", "admin")
    head = row(txt("Assisted access", 15, weight=700, extra="flex: 1;"), gap=6, extra="height: 44px; padding: 0 10px 0 16px; box-sizing: border-box; flex: none;")
    side = col(head,
        col(row(sess("assisted"), txt("K. Boateng, Finance", 13, weight=600), gap=6), txt("asked for help at 11:02. You accepted at 11:03.", 12, T["dim"]),
            txt("This is not a traversal. Nobody was blocked, nobody can be evicted, and it ends when either of you closes it.", 11.5, T["faint"]),
            gap=6, extra=f"margin: 4px 12px; padding: 12px; border: 1px solid {T['assist']}; border-radius: 8px; background: {T['pane']};"),
        dept_head("What you can reach", ""),
        row(ic("check", 14, T["assist"]), txt("Screen, read-only", 12.5), gap=8, extra="padding: 4px 16px;"),
        row(ic("check", 14, T["assist"]), txt("Files in /workers/ and /common/", 12.5), gap=8, extra="padding: 4px 16px;"),
        row(ic("x", 14, T["faint"]), txt("Control, actions, restricted files", 12.5, T["faint"]), gap=8, extra="padding: 4px 16px;"),
        row(ic("x", 14, T["faint"]), txt("Anything below the system ceiling K. Boateng narrowed", 12.5, T["faint"]), gap=8, extra="padding: 4px 16px;"),
        dept_head("Your own department", ""),
        row(txt("Operations is still yours. Switch back any time; help continues.", 12, T["faint"]), extra="padding: 2px 16px;"),
        gap=2, extra="flex: 1;")
    ptitle = pane_title("K. Boateng\u2019s screen", row(chip("Read only", "assist", 11, dot=True), txt("reported to Super User as Cross-Department Assistance", 12, T["faint"]), gap=10))
    screen = f'<div style="flex: 1; margin: 16px; border-radius: 10px; background: linear-gradient(135deg, #2b3542, #1b2430); display: flex; align-items: center; justify-content: center; color: {T["frame_dim"]}; font-size: 13px;">Live screen, FIN-02, refreshed every 2 s</div>'
    pg = col(ptitle, screen, gap=0, extra="flex: 1; min-height: 0;")
    insp_head = row(col(txt("With K. Boateng", 15, weight=600), txt("channel opened by the help request", 12, T["faint"]), gap=2), gap=10, extra=f"padding: 14px 16px; border-bottom: 1px solid {T['line']}; flex: none;")
    m = lambda who, tone, t, text: row(avatar(who[:2].upper(), tone, 26), col(row(txt(who, 12.5, weight=600), txt(t, 11, T["faint"]), gap=6), txt(text, 12.5, extra="line-height: 1.45;"), gap=2, extra="flex: 1;"), gap=8, align="flex-start", extra="padding: 8px 16px;")
    convo = col(m("K. Boateng", "admin", "11:02", "Payroll export hangs at 40 % every time since the update. Can you look?"), m("You", "admin", "11:05", "Looking now. Your export folder has a lock file from Monday. Delete it and retry."), gap=0, extra="flex: 1;")
    composer = row(f'<input type="text" placeholder="Message K. Boateng" aria-label="Message" style="flex: 1; height: 34px; padding: 0 12px; border: 1px solid {T["line2"]}; border-radius: 8px; font-family: {T["sans"]}; font-size: 13px;">', btn("Send", "primary", size="sm"), gap=8, extra=f"padding: 12px 16px; border-top: 1px solid {T['line']};")
    insp = col(insp_head, convo, composer, gap=0, extra="flex: 1; min-height: 0;")
    bnd = band("Helping K. Boateng in Finance by consent. Ceiling: files and screen only.", "assist", btn("End help", "frame", size="sm"))
    sh = sheet(side, pg, insp, state="assisted", band_html=bnd)
    status = statusbar("Connected to 127.0.0.1:7400 over TLS, pinned certificate", "session native   assisting FIN-02 by consent", "ok")
    return page("Assisted access", top, rail, sh, status, "assisted")


def screen_resources():
    crumbs = [crumb("Operations", "box", "dept"), sep(), crumb("You, at your own level", "you")]
    top = topbar(crumbs, "Search files in Operations and common", [indicator("Violation", "danger", "shield")])
    rail = icon_rail("home", "admin")
    head = row(txt("Resources", 15, weight=700, extra="flex: 1;"), btn("Add files", "primary", "plus", "sm"), gap=6, extra="height: 44px; padding: 0 10px 0 16px; box-sizing: border-box; flex: none;")

    def tier(name, who, n, tone, selected=False):
        bg = T["select"] if selected else "transparent"
        return row(ic("folder", 15, {"danger": T["danger"], "neutral": T["dim"], "ok": T["ok"]}[tone]), col(txt(name, 13, weight=600, mono=True), txt(who, 11.5, T["faint"]), gap=1, extra="flex: 1;"), txt(n, 11, T["faint"]), gap=8,
                   extra=f"padding: 8px 10px 8px 14px; margin: 0 6px; border-radius: 6px; background: {bg};")
    side = col(head, dept_head("Your tiers", "folders are the policy"),
        tier("/restricted/", "Only you, on your PC. Tracked by content, everywhere", "6", "danger", True), tier("/workers/", "Every worker in Operations", "31", "neutral"), tier("/common/", "Everyone in the system", "12", "ok"),
        dept_head("Violations", "1 open"),
        row(sess("su"), col(txt("budget-2026.xlsx", 12.5, mono=True), txt("restricted, found in /workers/ on OPS-07", 11.5, T["faint"]), gap=1), gap=8, extra="padding: 6px 16px;"),
        gap=2, extra="flex: 1;")
    ptitle = pane_title("/restricted/", row(chip("Admin only", "danger", 11), txt("if a file from here turns up where it shouldn\u2019t, you\u2019ll know", 12, T["faint"]), gap=10))
    frow = lambda name, size, when, tracked="Tracked": row(ic("file", 15, T["dim"]), txt(name, 13, mono=True, extra="flex: 1;"), txt(size, 12, T["faint"], mono=True, extra="width: 70px;"), txt(when, 12, T["faint"], extra="width: 110px;"), chip(tracked, "danger" if tracked != "Tracked" else "neutral", 10, dot=(tracked != "Tracked")), gap=12, extra=f"height: 40px; padding: 0 16px; border-bottom: 1px solid {T['line']};")
    files = col(frow("budget-2026.xlsx", "412 KB", "Mon 15 Sep", "Found outside"), frow("salaries-q3.xlsx", "88 KB", "Fri 12 Sep"), frow("supplier-contracts.pdf", "2.1 MB", "Fri 12 Sep"), frow("ops-review.docx", "140 KB", "Thu 11 Sep"), frow("access-list.txt", "3 KB", "Aug"), frow("q3-figures-locked.xlsx", "260 KB", "Aug"), gap=0)
    tabs = pills([("Files", "6"), ("Where copies are", ""), ("Violations", "1")], "Files")
    pg = col(ptitle, tabs, col(files, extra="padding-top: 8px;"), gap=0, extra="flex: 1; min-height: 0; overflow: hidden;")
    # the violation: a tier, a place, a resolution
    insp_head = row(col(txt("Violation", 15, weight=600), row(chip("Open", "danger", 10, dot=True), txt("since 10:41", 12, T["faint"]), gap=6), gap=2), gap=10, extra=f"padding: 14px 16px; border-bottom: 1px solid {T['line']}; flex: none;")
    where = col(
        row(txt("File", 12, T["faint"], extra="width: 70px;"), txt("budget-2026.xlsx", 12.5, mono=True), gap=8),
        row(txt("Tier", 12, T["faint"], extra="width: 70px;"), chip("/restricted/", "danger", 10), txt("yours", 12, T["dim"]), gap=8),
        row(txt("Found in", 12, T["faint"], extra="width: 70px;"), chip("/workers/", "neutral", 10), txt("on OPS-07, Ama", 12, T["dim"]), gap=8),
        row(txt("Matched by", 12, T["faint"], extra="width: 70px;"), txt("content hash, not name", 12.5), gap=8),
        gap=8)
    what = col(txt("What happened", 13, weight=600), txt("A copy of a restricted file appeared in a worker tier. It was logged, that one copy is ignored from now on, and Ama was told. The rest of /workers/ keeps syncing.", 12.5, T["dim"]), gap=4)
    resolve = col(txt("Resolve", 13, weight=600), row(btn("Ping Ama", "secondary", "ping", "sm"), btn("Enter OPS-07", "secondary", "lock", "sm"), gap=6), row(btn("Mark addressed", "primary", "check"), gap=6), txt("Super User sees this either way. Addressing tells them who handled it.", 11.5, T["faint"]), gap=8)
    insp = col(insp_head, col(where, hr(), what, hr(), resolve, gap=14, extra="padding: 14px 16px;"), gap=0, extra="flex: 1; min-height: 0;")
    sh = sheet(side, pg, insp)
    status = statusbar("Connected to 127.0.0.1:7400 over TLS, pinned certificate", "session native   engine 1.4.2")
    return page("Resources", top, rail, sh, status, "native")


def screen_reports():
    crumbs = [crumb("Operations", "box", "dept"), sep(), crumb("You, at your own level", "you")]
    top = topbar(crumbs, "Search files in Operations and common", [indicator("2 pings", "warn", "ping")])
    rail = icon_rail("reports", "admin")
    head = row(txt("Reports", 15, weight=700, extra="flex: 1;"), gap=6, extra="height: 44px; padding: 0 10px 0 16px; box-sizing: border-box; flex: none;")

    def nrow(name, n, selected=False, icon="reports"):
        bg = T["select"] if selected else "transparent"
        return row(ic(icon, 14, "#fff" if selected else T["dim"]), txt(name, 13, "#fff" if selected else None, 500 if selected else 400, extra="flex: 1;"), txt(n, 11, T["select_sub"] if selected else T["faint"]), gap=8, extra=f"height: 32px; padding: 0 10px 0 14px; margin: 0 6px; border-radius: 6px; background: {bg};")
    side = col(head, dept_head("Routed to Operations", "by Super User"), nrow("Listener reports", "3", True), nrow("Resource violations", "1"),
               dept_head("Yours", ""), nrow("Alerts you sent", "2", icon="bell"), nrow("Updates in Operations", "1 pending", icon="shield"), nrow("Deviations", "0", icon="warn"),
               row(txt("Categories not routed to you don\u2019t appear. Super User still gets them.", 11.5, T["faint"]), extra="padding: 10px 16px; margin-top: auto;"),
               gap=2, extra="flex: 1;")
    ptitle = pane_title("Listener reports", row(txt("3, routed to every Admin in Operations", 12, T["faint"]), gap=10))
    rep = lambda title, sub, when, state, tone, selected=False: row(col(txt(title, 13, weight=600), txt(sub, 12, T["faint"]), gap=2, extra="flex: 1;"), txt(when, 12, T["faint"], mono=True), chip(state, tone, 10), gap=12,
                                                                    extra=f"height: 56px; padding: 0 16px; border-bottom: 1px solid {T['line']}; {'background: ' + T['accent_soft'] + ';' if selected else ''}")
    reps = col(rep("Channel: Ama and you, listener A. Quaye", "Added 10:10. Written once when the listener was added", "Today 10:10", "Unseen", "warn", True),
               rep("Channel: Kojo and you, listener A. Quaye", "Added Mon 14:02", "Mon", "Seen", "neutral"),
               rep("Channel: Efua and A. Quaye, listener you", "Added Fri 09:40. You marked it addressed", "Fri", "Addressed", "ok"), gap=0)
    tabs = pills([("Unseen", "1"), ("Seen", "1"), ("Addressed", "1"), ("All", "3")], "All")
    pg = col(ptitle, tabs, col(reps, extra="padding-top: 8px;"), gap=0, extra="flex: 1; min-height: 0; overflow: hidden;")
    insp_head = row(col(txt("Listener report", 15, weight=600), txt("Today 10:10, written once", 12, T["faint"]), gap=2), gap=10, extra=f"padding: 14px 16px; border-bottom: 1px solid {T['line']}; flex: none;")
    body = col(kv("Channel", "Ama and you"), kv("Listener", "A. Quaye, added by you"), kv("Reached", "Super User, and Operations by routing"),
               txt("Marking it seen or addressed updates a view only Super User has. Your copy and theirs don\u2019t change.", 12, T["dim"]),
               row(btn("Mark seen", "secondary", size="sm"), btn("Mark addressed", "primary", "check", "sm"), gap=6), gap=10)
    alerts = section("Send an alert",
        f'<textarea aria-label="Alert text" placeholder="What everyone in Operations should know" style="height: 64px; padding: 8px 10px; border: 1px solid {T["line2"]}; border-radius: 6px; font-family: {T["sans"]}; font-size: 13px; resize: none;"></textarea>',
        row(chip("Operations", "accent", 10), chip("Admins only", "neutral", 10), '<span style="flex: 1;"></span>', btn("Send alert", "secondary", "bell", "sm"), gap=6), note="to Admins, or to Operations", pad="0", gap=8)
    upd = section("Update 1.4.2 in Operations",
        row(txt("6 of 7 confirmed. OPS-06 retries when idle and online.", 12.5, T["dim"]), gap=6),
        f'<div style="height: 6px; border-radius: 3px; background: {T["line"]};"><div style="height: 6px; border-radius: 3px; background: {T["ok"]}; width: 86%;"></div></div>',
        txt("OPS-06 keeps working on 1.4.1 meanwhile. You\u2019re escalated to after 5 failed retries.", 11.5, T["faint"]), note="rolling out", pad="0", gap=6)
    insp = col(insp_head, col(body, hr(), alerts, hr(), upd, gap=14, extra="padding: 14px 16px;"), gap=0, extra="flex: 1; min-height: 0;")
    sh = sheet(side, pg, insp)
    status = statusbar("Connected to 127.0.0.1:7400 over TLS, pinned certificate", "session native   engine 1.4.2")
    return page("Reports", top, rail, sh, status, "native")


def screen_states():
    """Six states, each designed: connect, loading, empty, error, refused (peer), disconnected."""
    def frame(title, inner, state="native", w=452, h=300):
        return col(txt(title, 12, T["frame_dim"], 500), f'<div style="width: {w}px; height: {h}px; box-sizing: border-box; border-radius: 10px; background: {T["pane"]}; overflow: hidden; display: flex; flex-direction: column; box-shadow: 0 1px 2px rgba(0,0,0,0.25);">{inner}</div>', gap=8)
    centre = lambda *c: col(*c, gap=10, extra="flex: 1; align-items: center; justify-content: center; padding: 24px; text-align: center;")
    # 1 connect
    connect = col(row(f'<span style="width: 10px; height: 22px; border-radius: 3px; background: {FRAME["native"]};"></span>', txt("Falcon", 18, weight=700), gap=8),
                  txt("Your identity is your account and the PC it is bound to. Nothing else to remember.", 12.5, T["dim"], extra="max-width: 340px;"),
                  row(field("Engine", "127.0.0.1:7400", "180px", mono=True), field("Account", "4001", "110px", mono=True), gap=8),
                  row(chip("Certificate pinned", "ok", 10, dot=True), txt("engine.crt, seen before", 11.5, T["faint"]), gap=6),
                  row(btn("Connect", "primary"), gap=6), gap=12, extra="flex: 1; align-items: flex-start; justify-content: center; padding: 24px 28px;")
    # 2 loading: skeleton rows
    sk = lambda w: f'<div style="height: 10px; width: {w}px; border-radius: 5px; background: {T["line"]};"></div>'
    loading = col(pane_title("Operations", txt("fetching the tree", 12, T["faint"])),
                  *[row(dot(T["line"], 8), sk(w), '<span style="flex: 1;"></span>', sk(50), gap=10, extra="height: 34px; padding: 0 16px;") for w in (120, 90, 140, 80, 110)],
                  txt("Loading takes the shape of what\u2019s coming, so nothing jumps.", 11.5, T["faint"], extra="padding: 8px 16px;"), gap=0)
    # 3 empty
    empty = col(pane_title("Tasks"), centre(ic("tasks", 28, T["line2"]), txt("No tasks yet", 15, weight=600), txt("Describe what a worker should do. The model drafts targets and a deadline; you confirm before anything is assigned.", 12.5, T["dim"], extra="max-width: 320px;"), btn("New task", "primary", "plus")), gap=0)
    # 4 error, typed and specific
    error = col(pane_title("Flows"), centre(ic("warn", 28, T["danger"]), txt("Couldn\u2019t create the flow", 15, weight=600),
        txt("It would loop: OPS-03 already flows into your source folder. Remove that destination or pick another source.", 12.5, T["dim"], extra="max-width: 340px;"),
        row(chip("flow.cycle", "danger", 10, mono=True), gap=6), row(btn("Change the source", "primary"), btn("Back", "secondary"), gap=8)), gap=0)
    # 5 refused: a peer's PC
    refused = col(row(avatar("EF", "worker", 32), col(txt("Efua", 15, weight=600), row(txt("OPS-02", 12, T["faint"], mono=True), gap=6), gap=2), gap=10, extra=f"padding: 14px 16px; border-bottom: 1px solid {T['line']};"),
                  col(row(sess("traversed"), txt("A. Quaye is inside", 13, weight=600), '<span style="flex: 1;"></span>', txt("14:02 left", 12, T["faint"], mono=True), gap=8),
                      txt("Another Admin holds this session. You can\u2019t block or end a peer; it ends on its own. You\u2019ll be able to enter then.", 12, T["dim"]),
                      row(btn("Enter", "primary", "lock", extra="opacity: 0.45;"), btn("Ping Efua instead", "secondary", "ping"), gap=8),
                      gap=10, extra=f"margin: 14px 16px; padding: 12px 14px; border: 1px solid {T['line2']}; border-radius: 8px;"), gap=0)
    # 6 disconnected: the frame goes dark, work stays visible
    disc = col(band("Connection lost. Reconnecting, attempt 3.", "danger", btn("Retry now", "frame", size="sm")),
               col(txt("What you were looking at stays put, greyed. Nothing you click sends until the link is back.", 12.5, T["dim"], extra="padding: 16px; opacity: 0.6;"),
                   *[row(dot(T["line2"], 8), txt(n, 13, T["dim"]), gap=10, extra="height: 32px; padding: 0 16px; opacity: 0.5;") for n in ("Kojo", "Efua", "Yaw")], gap=0), gap=0)
    grid = f'<div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 32px 24px; padding: 24px 32px;">' + "".join([
        frame("Connect: the only screen before the shell", connect), frame("Loading: skeleton in the shape of the data", loading), frame("Empty: an invitation, in the product\u2019s voice", empty),
        frame("Error: typed, specific, with the way out", error), frame("Refused: a peer\u2019s session, no way to force it", refused), frame("Disconnected: the frame darkens, the page waits", disc),
    ]) + "</div>"
    # the indicator tray, explained
    tray = row(txt("Indicators in the chrome", 12, T["frame_dim"], 500), indicator("2 pings", "warn", "ping"), indicator("Deadline reached", "danger", "clock"), indicator("Task done", "ok", "check"),
               indicator("Flow failed", "danger", "flows"), indicator("Violation", "danger", "shield"), indicator("Help offered", "assist", "assistance"),
               txt("They sit in the frame, so they survive every page change. They glow until addressed, never move, never stack into a badge count.", 11.5, T["frame_faint"], extra="max-width: 380px;"),
               gap=10, extra="padding: 0 32px;")
    inner = col(tray, grid, gap=0, extra=f"width: {W}px; height: {H}px; box-sizing: border-box; padding-top: 28px; background: {FRAME['native']}; overflow: hidden;")
    return page("States", "", "", inner, "", "native")


def screen_worker():
    """Worker-facing: the Overlay (a blocked PC) and the Dialog (a notification)."""
    overlay = (f'<div style="width: 800px; height: 500px; box-sizing: border-box; border-radius: 10px; background: linear-gradient(135deg, #2b3542, #1b2430); position: relative; overflow: hidden;">'
               f'<div style="position: absolute; inset: 0; background: rgba(36,48,61,0.72); backdrop-filter: blur(6px);"></div>'
               + col(row(ic("lock", 22, "#fff"), txt("This PC is in use by your Admin", 22, "#fff", 600), gap=12),
                     txt("Your screen, keyboard and mouse are theirs for the moment. Nothing you had open is closed. It will come back on its own.", 14, "rgba(255,255,255,0.75)", extra="max-width: 520px; line-height: 1.5;"),
                     row(txt("21:18", 28, "#fff", 600, mono=True), txt("left at most", 13, "rgba(255,255,255,0.6)"), gap=10, align="baseline"),
                     row(chip("Traversal in progress", "warn", 11, dot=True), txt("logged, as always", 12, "rgba(255,255,255,0.55)"), gap=8),
                     gap=16, extra="position: absolute; inset: 0; align-items: center; justify-content: center; text-align: center; padding: 40px;")
               + "</div>")
    dialog = (f'<div style="width: 400px; box-sizing: border-box; border-radius: 12px; background: {T["pane"]}; box-shadow: 0 12px 40px rgba(0,0,0,0.35); overflow: hidden;">'
              + row(f'<span style="width: 6px; height: 20px; border-radius: 3px; background: {T["warn"]};"></span>', txt("Falcon", 12.5, T["dim"], 600), '<span style="flex: 1;"></span>', txt("now", 11.5, T["faint"]), gap=8, extra="padding: 12px 16px 0;")
              + col(txt("Quarterly report is due at 17:00", 16, weight=600), txt("Two of three files you were expected to touch have changed today. summary.pdf hasn\u2019t appeared yet. Only R. Mensah can mark this done.", 13, T["dim"], extra="line-height: 1.5;"),
                    row(btn("Open the task", "primary"), btn("Ping R. Mensah", "secondary", "ping"), gap=8), gap=10, extra="padding: 8px 16px 16px;")
              + "</div>")
    dialog2 = (f'<div style="width: 400px; box-sizing: border-box; border-radius: 12px; background: {T["pane"]}; box-shadow: 0 12px 40px rgba(0,0,0,0.35); overflow: hidden;">'
               + row(f'<span style="width: 6px; height: 20px; border-radius: 3px; background: {T["danger"]};"></span>', txt("Falcon", 12.5, T["dim"], 600), '<span style="flex: 1;"></span>', txt("10:41", 11.5, T["faint"]), gap=8, extra="padding: 12px 16px 0;")
               + col(txt("A restricted file is in your resources", 16, weight=600), txt("budget-2026.xlsx doesn\u2019t belong in /resources/. It has been ignored and your Admin knows. Delete your copy when you can.", 13, T["dim"], extra="line-height: 1.5;"),
                     row(btn("Show the file", "secondary", "folder"), btn("Dismiss", "ghost"), gap=8), gap=10, extra="padding: 8px 16px 16px;")
               + "</div>")
    left = col(txt("Overlay: the whole screen, while the PC is entered", 12, T["frame_dim"], 500), overlay, gap=8)
    right = col(txt("Dialog: one notification, bottom right, the accent strip says what kind", 12, T["frame_dim"], 500), dialog, dialog2, gap=16)
    inner = row(left, right, gap=40, align="flex-start", extra=f"width: {W}px; height: {H}px; box-sizing: border-box; padding: 40px; background: {FRAME['native']}; overflow: hidden;")
    return page("Worker: Overlay and Dialog", "", "", inner, "", "native")


def screen_tokens():
    """The language, defined once."""
    sw = lambda name, hexv, textc="#fff", note="", label=None: col(f'<div style="height: 56px; border-radius: 8px; background: {hexv}; display: flex; align-items: flex-end; padding: 8px; color: {textc}; font-family: {T["mono"]}; font-size: 11px;">{label or hexv}</div>', txt(name, 12, weight=600), txt(note, 11.5, T["faint"]) if note else "", gap=4, extra="min-width: 0;")
    frames = col(sw("Frame", FRAME["native"], note="one gradient, always: ink at the top left, violet at the bottom right, 155°", label="#121220 → #2A1F50 → #4B2F8A" if DARK else None),
                 band("Traversing: you are inside someone’s view, timed", "warn", btn("Leave", "frame", size="sm")),
                 band("Occupied: Super User is inside your view", "danger", btn("Claim native session", "frame", size="sm")),
                 band("Assisted: helping a peer by consent", "assist", btn("End help", "frame", size="sm")), gap=8)
    meaning = f'<div style="display: grid; grid-template-columns: repeat(5, minmax(0, 1fr)); gap: 12px;">' + sw("Accent", T["accent"], note="selected, yours, primary action") + sw("Ok", T["ok"], note="free, done, synced, connected") + sw("Warn", T["warn"], note="deadline near, paused, consent pending, entered") + sw("Danger", T["danger"], note="blocked, violation, failed, Super User inside") + sw("Assist", T["assist"], note="assisted access, only that") + "</div>"
    neutrals = f'<div style="display: grid; grid-template-columns: repeat(6, minmax(0, 1fr)); gap: 12px;">' + sw("Ground", T["ground"], T["ink"]) + sw("Sidebar", T["side_native"], T["ink"], "a step below the pane") + sw("Pane", T["pane"], T["ink"]) + sw("Line", T["line"], T["ink"]) + sw("Dim text", T["dim"], T["ground"]) + sw("Ink", T["ink"], T["ground"]) + "</div>"
    type_ = col(
        row(txt("Display 28 / 600", 12, T["faint"], extra="width: 150px;"), txt("21:18 left at most", 28, weight=600, mono=True), gap=16, align="baseline"),
        row(txt("Page title 20 / 600", 12, T["faint"], extra="width: 150px;"), txt("Q3 supplier reconciliation", 20, weight=600), gap=16, align="baseline"),
        row(txt("Pane title 15 / 600", 12, T["faint"], extra="width: 150px;"), txt("Payroll to Archive", 15, weight=600), gap=16, align="baseline"),
        row(txt("Body 13 / 400", 12, T["faint"], extra="width: 150px;"), txt("Entering blocks Ama for the length of your session. She sees the overlay, not who is inside.", 13), gap=16, align="baseline"),
        row(txt("Small 12 and 11.5", 12, T["faint"], extra="width: 150px;"), txt("Only you see this", 12, T["dim"]), txt("since 08:14", 11.5, T["faint"]), gap=16, align="baseline"),
        row(txt("Mono, for data only", 12, T["faint"], extra="width: 150px;"), txt("WS-OPS-07   D:\\Archive\\payroll   4021   10:52", 13, mono=True), gap=16, align="baseline"),
        gap=10)
    shapes = row(
        col(f'<div style="width: 120px; height: 72px; border-radius: 10px; background: {T["pane"]}; border: 1px solid {T["line"]};"></div>', txt("Sheet and panes 10", 12, T["dim"]), gap=6),
        col(f'<div style="width: 120px; height: 36px; border-radius: 6px; background: {T["select"]};"></div>', txt("Selected row, controls 6", 12, T["dim"]), gap=6),
        col(row(chip("Chip", "accent", 11), chip("Status", "ok", 11, dot=True), gap=6), txt("Chips 999", 12, T["dim"]), gap=6),
        col(row(btn("Primary", "primary"), btn("Secondary", "secondary"), btn("Danger", "danger"), gap=6), txt("Buttons say what happens", 12, T["dim"]), gap=6),
        col(row(sess("free"), sess("native"), sess("traversed"), sess("assisted"), sess("su"), sess("you"), gap=8), txt("One session vocabulary", 12, T["dim"]), gap=6),
        gap=32, align="flex-start")
    reveal = col(pills([("Needs you", "4"), ("Client PCs", "7"), ("Routed", "2")], "Needs you", pad="0"),
                 acc("An open section", txt("reveals its content until you close it", 12.5, T["dim"]), open_=True, pad="0"),
                 acc("A closed section", open_=False, summary="one line says what is inside", pad="0"),
                 txt("Tabs choose one section of a body at a time. Accordions keep a stack short; only the item that needs you is open.", 12, T["faint"]),
                 gap=6)
    rules = col(*[row(dot(T["accent"], 6), txt(r, 12.5, T["dim"]), gap=10) for r in [
        "The frame is one gradient and never changes. Session state is one band under the top bar, the status line, and the session box in the inspector.",
        "Colour means one thing each. Amber is never decoration; red is never emphasis.",
        "Sentence case everywhere. No all-caps labels, no dividers made of dots, never a coloured edge on the left of a row or card.",
        "Mono is for identifiers, paths and times. Never for labels.",
        "Spacing scale 4, 8, 12, 16, 24, 32. Rows 32 in trees, 40 to 56 in lists.",
        "Nothing is dumped. A body shows one tab at a time; a stack is an accordion with one item open.",
        "One motion: the frame cross-fades when your state changes (600 ms). Indicators glow; nothing else moves on its own.",
    ]], gap=6)
    body = col(
        row(f'<span style="width: 10px; height: 26px; border-radius: 3px; background: #fff;"></span>', txt("Falcon Operator, the language", 22, "#fff", 700), gap=10),
        f'<div style="display: grid; grid-template-columns: 1fr 1fr; gap: 24px;">'
        + col(section("The frame, and the state band under it", frames, pad="0"), section("Meaning", meaning, pad="0"), section("Neutrals", neutrals, pad="0"), gap=20, extra=f"padding: 20px; border-radius: 10px; background: {T['pane']};")
        + col(section("Type: IBM Plex Sans, IBM Plex Mono", type_, pad="0"), section("Shapes", shapes, pad="0"), section("Revealing: tabs and accordions", reveal, pad="0"), section("Rules", rules, pad="0"), gap=16, extra=f"padding: 20px; border-radius: 10px; background: {T['pane']};")
        + "</div>",
        gap=20, extra=f"width: {W}px; height: {H}px; box-sizing: border-box; padding: 28px 32px; background: {FRAME['native']}; overflow: hidden;")
    return page("Tokens", "", "", body, "", "native")


# ------------------------------------------------------------------ the screens, by module
# Each module is plain Python executed in this namespace: they share the tokens and helpers above.
for _module in ("v2", "v3", "v4", "v5", "v6", "v7", "v8", "mood", "su_mood", "su_dash", "charts", "charts2", "layouts", "index_board", "interaction", "pages", "grid", "traverse", "dept_mood", "dept", "scale", "tasks_mood", "automation_mood", "work_pages", "actions_pages", "batch1_mood", "batch1_pages", "batch2_mood", "batch1b_pages", "batch2b_mood", "batch2_pages", "batch2d_pages"):
    exec(compile((Path(__file__).parent / (_module + ".py")).read_text(encoding="utf-8"), _module + ".py", "exec"))


# ------------------------------------------------------------------ write everything
for _n, _f in (("Lane-Filled.dc.html", screen_lane_filled), ("Lane-Empty.dc.html", screen_lane_empty)):
    (OUT / _n).write_text(_f(), encoding="utf-8")

SCREENS = INDEX + [
    # row 1: the shell and its states of authority
    ("Main.dc.html", "Admin at home", screen_admin_home),
    ("SuperUser.dc.html", "Super User at home", screen_su_home),
    ("Traversing.dc.html", "Super User inside a PC", screen_traversing),
    # row 2
    ("Occupied.dc.html", "Admin, occupied from above", screen_occupied),
    ("Assisted.dc.html", "Assisted access", screen_assisted),
    ("Tasks.dc.html", "Tasks: the guided review", screen_tasks),
    # row 3
    ("Flows.dc.html", "Flows: the graph", screen_flows),
    ("Automation.dc.html", "Automation: an event and its actions", screen_automation),
    ("Actions.dc.html", "Actions: Control, Monitoring, Custom", screen_actions),
    ("Automation-Live.dc.html", "Automation: live", screen_automation_live),
    ("SU-Departments.dc.html", "Super User: departments and Admins", screen_su_departments),
    ("SU-Views.dc.html", "Super User: Views, yours alone", screen_su_views),
    ("SU-Updates.dc.html", "Super User: rollout health", screen_su_updates),
    ("SU-Audit.dc.html", "Super User: who was where", screen_su_audit),
    ("Assistance.dc.html", "Assistance: pings, channels, listeners", screen_assistance),
    # row 4
    ("Resources.dc.html", "Resources: tiers and a violation", screen_resources),
    ("Reports.dc.html", "Reports, routing, alerts, updates", screen_reports),
    ("States.dc.html", "States and indicators", screen_states),
    # row 5
    ("Worker.dc.html", "Worker: Overlay and Dialog", screen_worker),
    ("Tokens.dc.html", "The language", screen_tokens),
    ("Dialogs.dc.html", "Dialogs and the plus menu", screen_dialogs),
] + MOOD + SU_MOOD + SU_DASH + CHART_MOOD + CHART_MOOD_2 + LAYOUTS + INTERACTION + PAGES_COMPOSED + GRID_TAKES + TRAVERSE + DEPT_MOOD + DEPT_PAGE + SCALE + TASKS_MOOD + AUTOMATION_MOOD + WORK_PAGES + ACTIONS_PAGES + BATCH1_MOOD + BATCH1_PAGES + BATCH2_MOOD + BATCH1B + BATCH2B + BATCH2_PAGES + BATCH2D
ROW_TITLES = ["The shell: one gradient frame, the state band says whose authority you are under", "Timed sessions, occupation, peer help", "Work: decide, wire, run", "Policy, reports, states", "Worker surfaces, the language, dialogs",
              "Mood board 1: cards, rows, status, decisions", "Mood board 2: sessions, titles, talk", "Mood board 3: the shell, bands, rails, sidebar, top bar, indicators, inspector", "Mood board 4: buttons, chips, inputs, avatars, feel", "Mood board 5: density, metrics, notices, logs, hierarchy shapes, creating"]

GAP_X, GAP_Y, TITLE_H = 80, 120, 260
boards, order, notes = {}, [], {}
for i, (name, title, fn) in enumerate(SCREENS):
    r, c = divmod(i, 3)
    x, y = c * (W + GAP_X), r * (H + GAP_Y + TITLE_H) + TITLE_H
    boards[name] = {"x": x, "y": y, "w": W, "h": H, "title": title, "radius": 12}
    order.append(name)
    (OUT / name).write_text(fn(), encoding="utf-8")
for r, t in enumerate(ROW_TITLES):
    notes[f"row{r}"] = {"x": 0, "y": r * (H + GAP_Y + TITLE_H) + 8, "text": t, "kind": "title1", "maxW": 3 * W + 2 * GAP_X}

canvas = {
    "v": 3,
    "createdOnFiles": {"v": 1, "at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")},
    "title": "Falcon Operator Design",
    "launch": {"view": "canvas"},
    "pages": [],
    "boards": boards,
    "order": order,
    "notes": notes,
    "designSystems": [],
}
(OUT / "canvas.json").write_text(json.dumps(canvas, indent=1), encoding="utf-8")
print("wrote", len(SCREENS), "artboards")
# The live canvas is arranged BY HAND. This index is a fallback for a canvas that does not exist yet
# and a source of board titles -- publishing it as-is would throw away the layout, the row notes and
# the boards the generator does not place. design/README.md has the merge.
print("NOTE: boards/canvas.json is generated, not publishable. Merge into the live index instead --")
print("      read the artifact's project/canvas.json, keep every x/y and note, append new boards.")
