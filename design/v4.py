# ================================================================== v4: the chosen kit, applied
# Picks: pills segments · card rows · card decisions · avatar-led + row cards · paged strip · icons for
# session state · avatars with a session dot · tonal + ghost buttons · soft chips · filled inputs ·
# chrome-pill indicators · minimal top bar with a command palette · floating-pill band · icons+labels rail ·
# accordion sidebar of avatar rows · titles with an avatar · pill/terminal graph nodes, all one size ·
# box + inline session control · ring + in-title countdown · rows for talk · toasts · list and grouped logs ·
# comfortable density · tiles, bars, sparklines and rings for metrics · breadcrumb drill + split by state ·
# menu + command for creating · popover inspector (no permanent right panel).

SESSION_ICON = {"free": ("monitor", "faint"), "native": ("user", "dim"), "traversed": ("lock", "warn"),
                "assisted": ("assistance", "accent"), "su": ("shield", "danger"), "you": ("user", "accent")}


def sicon(state, size=15):
    name, tone = SESSION_ICON[state]
    return ic(name, size, T[tone])


def av(initials, tone="worker", size=34, state="native"):
    """One neutral avatar. State is said by the row's icon, never by a dot on the person."""
    return avatar(initials, tone, size)


# ------------------------------------------------------------------ buttons: tonal and ghost only
def tbtn(label, tone="accent", icon=None, size="md", disabled=False):
    pad, fs = ("7px 14px", 13.5) if size == "md" else ("5px 11px", 12.5)
    return (f'<button type="button" style="display: inline-flex; align-items: center; gap: 7px; padding: {pad}; border-radius: 9px; border: 0; '
            f'background: {T[tone + "_soft"]}; color: {T[tone]}; font-family: {T["sans"]}; font-size: {fs}px; font-weight: 600; cursor: pointer; white-space: nowrap; {"opacity: 0.45;" if disabled else ""}">'
            f'{ic(icon, 15) if icon else ""}{label}</button>')


def gbtn(label, icon=None, size="md"):
    pad, fs = ("7px 12px", 13.5) if size == "md" else ("5px 9px", 12.5)
    return (f'<button type="button" style="display: inline-flex; align-items: center; gap: 7px; padding: {pad}; border-radius: 9px; border: 0; background: transparent; '
            f'color: {T["dim"]}; font-family: {T["sans"]}; font-size: {fs}px; font-weight: 500; cursor: pointer; white-space: nowrap;">{ic(icon, 15) if icon else ""}{label}</button>')


# ------------------------------------------------------------------ segments: pills with badges
def pills2(items, active, pad="0 0 14px"):
    out = []
    for label, count in items:
        on = label == active
        badge = (f'<span style="padding: 0 6px; border-radius: 999px; background: {"rgba(255,255,255,0.22)" if on else T["line"]}; font-size: 11px; font-weight: 600;">{count}</span>') if count else ""
        out.append(f'<a href="#{label.lower().replace(" ", "-")}" style="display: inline-flex; align-items: center; gap: 7px; padding: 6px 13px; border-radius: 999px; '
                   f'background: {T["select"] if on else T["ground"]}; color: {"#fff" if on else T["dim"]}; font-family: {T["sans"]}; font-size: 13px; font-weight: 600; text-decoration: none;">{label}{badge}</a>')
    return row(*out, gap=7, extra=f"padding: {pad}; flex: none; flex-wrap: wrap;")


# ------------------------------------------------------------------ rows: each its own card
def crow(lead, title, value="", tone=None, right=None, sub="", hover=False, sel=False):
    v = txt(value, 12.5, tone_c(tone, T["dim"]), 500 if tone else 400) if value else ""
    r = right if right is not None else ic("chev", 14, T["faint"])
    bg = T["line"] if hover else T["ground"]
    ring = f"box-shadow: inset 0 0 0 1px {T['selectline']};" if sel else ""
    body = col(txt(title, 13.5, weight=500), txt(sub, 12, T["faint"]) if sub else "", gap=2, extra="flex: 1; min-width: 0;")
    return row(lead, body, v, r, gap=12, extra=f"min-height: 52px; padding: 8px 14px 8px 14px; box-sizing: border-box; border-radius: 12px; background: {bg}; {ring}")


def cgroup(*rows, gap=8):
    return col(*rows, gap=gap, extra="flex: none;")


def acard(title, *children, open_=False, lead="", summary="", tone=None):
    """A decision or section as its own card."""
    chev = ic("chevd" if open_ else "chev", 14, T["faint"])
    sm = txt(summary, 12.5, tone_c(tone, T["faint"])) if summary else ""
    head = (f'<button type="button" style="display: flex; align-items: center; gap: 12px; width: 100%; min-height: 52px; padding: 0; border: 0; background: transparent; '
            f'color: {T["ink"]}; font-family: {T["sans"]}; text-align: left; cursor: pointer;">{lead}{txt(title, 13.5, weight=600)}'
            f'<span style="flex: 1; min-width: 0; display: flex; justify-content: flex-end;">{sm}</span>{chev}</button>')
    inner = col(*children, gap=10, extra="padding: 2px 0 14px;") if open_ else ""
    ring = f"box-shadow: inset 0 0 0 1px {tone_c(tone)}66;" if (open_ and tone) else ""
    return col(head, inner, gap=0, extra=f"padding: 0 14px; border-radius: 12px; background: {T['ground']}; {ring} flex: none;")


# ------------------------------------------------------------------ title with avatar, and the breadcrumb drill
def drill(*steps):
    out = []
    for i, (label, cur) in enumerate(steps):
        if i:
            out.append(ic("chev", 12, T["faint"]))
        out.append(txt(label, 12.5, T["ink"] if cur else T["faint"], 600 if cur else 400))
    return row(*out, gap=6, extra="flex: none; padding-bottom: 10px;")


def title_av(lead, title, sub="", right="", trail=""):
    return row(lead, col(row(txt(title, 24, weight=600, extra="letter-spacing: -0.3px;"), trail, gap=10), txt(sub, 13, T["faint"]) if sub else "", gap=3, extra="flex: 1; min-width: 0;"),
               right, gap=14, extra="padding-bottom: 16px; flex: none;")


def bodywrap(*children, pad="22px 28px"):
    return col(*children, gap=0, extra=f"padding: {pad}; flex: 1; min-height: 0; overflow: hidden;")


# ------------------------------------------------------------------ countdown: ring, and in the title
def ring(pct, size=44, c=None, w=4, label=""):
    circ = 3.1416 * (size - 2 * w)
    inner = f'<div style="position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;">{txt(label, 11.5, weight=600, mono=True)}</div>' if label else ""
    return (f'<div style="position: relative; width: {size}px; height: {size}px; flex: none;"><svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" aria-hidden="true">'
            f'<circle cx="{size/2}" cy="{size/2}" r="{size/2 - w}" fill="none" stroke="{T["line"]}" stroke-width="{w}"/>'
            f'<circle cx="{size/2}" cy="{size/2}" r="{size/2 - w}" fill="none" stroke="{c or T["warn"]}" stroke-width="{w}" stroke-linecap="round" '
            f'stroke-dasharray="{circ}" stroke-dashoffset="{circ * (1 - pct)}" transform="rotate(-90 {size/2} {size/2})"/></svg>{inner}</div>')


def time_chip(t, tone="warn"):
    return (f'<span style="display: inline-flex; align-items: center; gap: 6px; padding: 4px 11px; border-radius: 999px; background: {T[tone + "_soft"]}; color: {T[tone]}; '
            f'font-family: {T["mono"]}; font-size: 13px; font-weight: 600;">{ic("clock", 13)}{t}</span>')


# ------------------------------------------------------------------ shell: minimal top bar with a command palette
def topbar2(inds, palette="Go to, do, find"):
    left = row(iconbtn("back", "Back"), iconbtn("fwd", "Forward"), gap=2, extra="flex: none;")
    cmd = (f'<button type="button" style="display: flex; align-items: center; gap: 9px; width: 420px; height: 30px; padding: 0 12px; border-radius: 9px; background: {T["frame_wash"]}; '
           f'border: 1px solid rgba(255,255,255,0.12); color: {T["frame_dim"]}; font-family: {T["sans"]}; font-size: 13px; cursor: pointer;">{ic("search", 15)}{palette}'
           f'<span style="flex: 1;"></span><span style="font-family: {T["mono"]}; font-size: 11px; opacity: 0.7;">Ctrl K</span></button>')
    win = row(iconbtn("min", "Minimize"), iconbtn("close", "Close"), gap=0)
    return row(left, '<span style="flex: 1;"></span>', cmd, '<span style="flex: 1;"></span>', row(*inds, gap=6), f'<span style="width: 1px; height: 18px; background: rgba(255,255,255,0.18); margin: 0 8px;"></span>', win,
               gap=10, extra="height: 44px; padding: 0 6px 0 6px; box-sizing: border-box; flex: none;")


def float_pill(text, tone="warn", *actions, timer=""):
    bg = {"warn": "#B4650A", "danger": "#B92828", "assist": "#0E6E77"}[tone]
    t = f'<span style="font-family: {T["mono"]}; font-size: 13px; font-weight: 700; color: #fff;">{timer}</span>' if timer else ""
    return row('<span style="flex: 1;"></span>',
               row(ic({"warn": "lock", "danger": "shield", "assist": "assistance"}[tone], 15, "#fff"), t, txt(text, 12.5, "#fff", 500), *actions,
                   gap=9, extra=f"padding: 6px 8px 6px 14px; border-radius: 999px; background: {bg}; box-shadow: 0 10px 30px rgba(0,0,0,0.45);"),
               '<span style="flex: 1;"></span>', gap=0, extra="padding: 10px 0 2px; flex: none;")


def toast(text, tone="ok", action=""):
    return row('<span style="flex: 1;"></span>',
               row(ic({"ok": "check", "danger": "warn", "warn": "clock"}[tone], 16, T[tone]), txt(text, 13, weight=600), action,
                   gap=10, extra=f"padding: 11px 13px; border-radius: 12px; background: {T['ground']}; box-shadow: 0 10px 30px rgba(0,0,0,0.5);"),
               '<span style="flex: 1;"></span>', gap=0, extra="flex: none;")


# ------------------------------------------------------------------ sidebar: accordion of avatar rows
def sb_head(title, plus=True):
    return row(txt(title, 15, weight=700, extra="flex: 1;"), (iconbtn("plus", "Create", kind="pane", size=26) if plus else ""), gap=6,
               extra="height: 48px; padding: 0 10px 0 16px; box-sizing: border-box; flex: none;")


def sb_section(title, count="", open_=True):
    return row(ic("chevd" if open_ else "chev", 13, T["faint"]), txt(title, 12, T["dim"], 600, extra="flex: 1;"), txt(count, 11, T["faint"]),
               gap=7, extra="height: 30px; padding: 0 14px 0 12px; box-sizing: border-box; margin-top: 6px;")


def sb_person(name, host, state, initials=None, tone="worker", sel=False, right=""):
    return row(av(initials or name[:2].upper(), tone, 28, state),
               col(txt(name, 13, "#fff" if sel else None, 500), txt(host, 11, T["select_sub"] if sel else T["faint"], mono=True) if host else "", gap=0, extra="flex: 1; min-width: 0;"),
               right, gap=10, extra=f"height: 44px; padding: 0 10px; box-sizing: border-box; margin: 0 6px; border-radius: 9px; background: {T['select'] if sel else 'transparent'};")


def sb_item(icon, name, sub="", sel=False, right=""):
    return row(ic(icon, 15, "#fff" if sel else T["dim"]), col(txt(name, 13, "#fff" if sel else None, 500), txt(sub, 11, T["select_sub"] if sel else T["faint"]) if sub else "", gap=0, extra="flex: 1; min-width: 0;"), right,
               gap=10, extra=f"height: 40px; padding: 0 10px; box-sizing: border-box; margin: 0 6px; border-radius: 9px; background: {T['select'] if sel else 'transparent'};")


def sb_legend():
    pairs = [("free", "Free"), ("native", "At the PC"), ("traversed", "Entered"), ("assisted", "Assisted"), ("su", "Super User")]
    return row(*[row(sicon(k, 13), txt(l, 11, T["faint"]), gap=5) for k, l in pairs], gap=10,
               extra=f"padding: 10px 14px 12px; border-top: 1px solid {T['line']}; margin-top: auto; flex-wrap: wrap;")


def sidebar_ops(sel="OPS-07", state="native"):
    held = state == "occupied"
    # stable order, always by hostname: the list never resorts itself under the cursor
    people = [("Kojo", "OPS-01", "native"), ("Efua", "OPS-02", "free"), ("Yaw", "OPS-03", "native"), ("Adjoa", "OPS-04", "traversed"),
              ("Nana", "OPS-05", "native"), ("Kwame", "OPS-06", "free"), ("Ama", "OPS-07", "su" if held else "native")]
    return col(sb_head("Operations"),
               sb_section("Admins", "2"),
               sb_person("You", "WS-OPS-A1", "su" if held else "you", "RM", "admin", right=chip("Admin", "admin", 10)),
               sb_person("A. Quaye", "WS-OPS-A2", "native", "AQ", "admin"),
               sb_section("Client PCs", "7"),
               *[sb_person(n, h, s, sel=(h == sel)) for n, h, s in people],
               sb_legend(), gap=2, extra="flex: 1; min-height: 0;")


def sidebar_all(inside=False, sel=None):
    out = [sb_head("Everything"), sb_section("Operations", "2 Admins, 7 PCs"),
           sb_person("R. Mensah", "WS-OPS-A1", "su" if inside else "native", "RM", "admin", sel=(sel == "A1")),
           sb_person("A. Quaye", "WS-OPS-A2", "native", "AQ", "admin")]
    if inside:
        out += [sb_person("Ama", "OPS-07", "su", sel=(sel == "OPS-07")), sb_person("Kojo", "OPS-01", "native"),
                row(txt("4 more", 11.5, T["faint"]), extra="padding: 2px 16px 4px 54px;")]
    else:
        out += [row(ic("lock", 12, T["faint"]), txt("PCs show once inside an Admin", 11.5, T["faint"]), gap=6, extra="padding: 2px 14px 6px 42px;")]
    out += [sb_section("Finance", "1 Admin, 4 PCs", False), sb_section("Logistics", "3 PCs", False)]
    out += [row(ic("warn", 13, T["warn"]), txt("Logistics has no Admin", 11.5, T["warn"]), gap=6, extra="padding: 4px 16px;")]
    out += [sb_legend()]
    return col(*out, gap=2, extra="flex: 1; min-height: 0;")


# ------------------------------------------------------------------ the detail card (always in the lane)
def popover(title, sub, *children, lead="", w=340, actions=""):
    """The detail card. Not a popover: it is always in the lane, it never closes, only its contents change."""
    head = row(lead, col(txt(title, 15.5, weight=600), txt(sub, 12, T["faint"]) if sub else "", gap=2, extra="flex: 1;"), gap=10, extra="padding: 16px 16px 10px;")
    body = col(*children, gap=10, extra="padding: 0 16px 16px;")
    foot = row(actions, gap=8, extra=f"padding: 10px 16px; border-top: 1px solid {T['line']};") if actions else ""
    return (f'<div style="width: {w}px; box-sizing: border-box; border-radius: 16px; background: {T["pane"]}; box-shadow: 0 18px 50px rgba(0,0,0,0.6), 0 0 0 1px {T["line"]}; overflow: hidden; flex: none;">'
            f'{head}{body}{foot}</div>')


def anchored(anchor_html, pop_html, gap_px=12):
    return row(anchor_html, f'<span style="width: {gap_px}px;"></span>', pop_html, gap=0, align="flex-start")


# ------------------------------------------------------------------ cards for entities
def pc_card_av(name, host, status, tone=None, state="native", sel=False, w=206):
    ring_ = f"box-shadow: inset 0 0 0 1px {T['selectline']};" if sel else ""
    return col(row(av(name[:2].upper(), "worker", 34, state), col(txt(name, 14, weight=600), txt(host, 11.5, T["faint"], mono=True), gap=0, extra="flex: 1; min-width: 0;"), gap=10),
               '<span style="flex: 1;"></span>',
               row(txt(status, 12.5, tone_c(tone, T["dim"]), 500 if tone else 400), gap=6),
               gap=8, extra=f"width: {w}px; height: 104px; box-sizing: border-box; padding: 13px 14px; border-radius: 14px; background: {T['ground']}; {ring_} flex: none;")


def paged(cards, page_i=0, pages=2):
    dots = row(*[dot(T["ink"] if i == page_i else T["line2"], 6) for i in range(pages)], gap=6)
    return col(row(*cards, gap=10, extra="flex: none;"), row('<span style="flex: 1;"></span>', dots, '<span style="flex: 1;"></span>', gap=0), gap=10, extra="flex: none;")


# ------------------------------------------------------------------ metrics
def tile(k, v, sub=""):
    return col(txt(k, 11.5, T["faint"]), txt(v, 20, weight=600, mono=True), txt(sub, 11, T["faint"]) if sub else "", gap=2,
               extra=f"padding: 12px 14px; border-radius: 12px; background: {T['ground']}; flex: 1; min-width: 0;")


def barline(k, v, pct, c=None):
    return col(row(txt(k, 12.5), '<span style="flex: 1;"></span>', txt(v, 12, T["dim"], mono=True), gap=6),
               f'<div style="height: 5px; border-radius: 3px; background: {T["line"]};"><div style="height: 5px; border-radius: 3px; background: {c or T["accent"]}; width: {int(pct*100)}%;"></div></div>', gap=6)


def sparkline(pts, c=None, w=140, h=30):
    return f'<svg width="{w}" height="{h}" viewBox="0 0 140 30" preserveAspectRatio="none" aria-hidden="true"><polyline points="{pts}" fill="none" stroke="{c or T["accent"]}" stroke-width="1.75" stroke-linejoin="round" stroke-linecap="round"/></svg>'


def sparkrow(k, v, pts, c=None):
    return row(txt(k, 12.5, extra="width: 74px;"), sparkline(pts, c), txt(v, 12, T["dim"], mono=True, extra="margin-left: auto;"), gap=10)


# ------------------------------------------------------------------ logs: list, and grouped by day
def logrow(title, when, tone=None, sub=""):
    return crow(dot(tone_c(tone, T["line2"]), 8), title, when, None, right="", sub=sub)


def log_group(day, *rows):
    return col(txt(day, 11.5, T["faint"], 600, extra="padding: 0 4px 2px;"), cgroup(*rows, gap=6), gap=8)


# ------------------------------------------------------------------ graph: one node size, pill head + terminal path
NODE_W, NODE_H = 176, 78


def gnode(title, path, tone=None, icon="monitor", status=""):
    head = row(ic(icon, 14, tone_c(tone, T["dim"])), txt(title, 13, weight=600, extra="white-space: nowrap;"), '<span style="flex: 1;"></span>', (dot(tone_c(tone), 7) if tone else ""), gap=7,
               extra=f"height: 26px; padding: 0 11px; border-radius: 999px; background: {T['pane']}; box-sizing: border-box;")
    return (f'<div style="position: absolute; width: {NODE_W}px; height: {NODE_H}px; box-sizing: border-box; padding: 9px; border-radius: 14px; background: {T["ground"]}; '
            f'box-shadow: 0 0 0 1px {tone_c(tone, T["line"])}; display: flex; flex-direction: column; gap: 6px;">{head}'
            f'<div style="font-family: {T["mono"]}; font-size: 11px; color: {T["faint"]}; padding: 0 4px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">{path}</div></div>')


def place(x, y, html):
    return html.replace("position: absolute;", f"position: absolute; left: {x}px; top: {y}px;", 1)


# ------------------------------------------------------------------ the lane: reserved space, no chrome
LANE_W, BODY_W = 372, 620


def lane(*children):
    """A constant region on the right. The popover always appears here, so the body never reflows.
    The lane itself is nothing: no border, no background, no title."""
    return col(*children, gap=12, extra=f"width: {LANE_W}px; flex: none;")


def popover_empty(icon="monitor", line="Nothing selected", hint="Pick a PC, a row or a card and it opens here.", h=250):
    """The same card, holding its empty state. The container never leaves the lane; only its contents change."""
    inner = col(f'<span style="width: 52px; height: 52px; border-radius: 16px; background: {T["ground"]}; display: inline-flex; align-items: center; justify-content: center;">{ic(icon, 23, T["faint"])}</span>',
                txt(line, 14, T["dim"], 600), txt(hint, 12.5, T["faint"], extra="text-align: center; max-width: 230px; line-height: 1.5;"),
                gap=12, extra=f"min-height: {h}px; align-items: center; justify-content: center; padding: 24px;")
    return (f'<div style="width: 100%; box-sizing: border-box; border-radius: 16px; background: {T["pane"]}; '
            f'box-shadow: 0 18px 50px rgba(0,0,0,0.6), 0 0 0 1px {T["line"]}; overflow: hidden; flex: none;">{inner}</div>')


def lane_hint(line="Nothing selected"):
    return popover_empty(line=line)
