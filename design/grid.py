# ================================================================== K01-K02: must see
# Four cells, because four things are worth a Super User's attention before anything else, and the
# page is only those four. The title of each cell sits ABOVE it, on the frame, so the cell itself is
# a clean surface holding nothing but the drawing.
#
# K01 is a perfect grid -- four equal cells, nothing claiming to matter more.
# K02 varies the cells, so the ranking is in the geometry: authority biggest, then the rollout, then
# the day, then what is out of place.
#
# There is no "three departments, three Admins, fourteen client PCs" line. That is a description of
# the organisation, and a Super User already knows it. The page says what they must see.

MUST_SEE = [
    ("Authority", "Logistics has no Admin", "danger"),
    ("Rollout 1.4.2", "two PCs behind, 1.4.3 blocked", "warn"),
    ("Today", "you entered one machine", "dim"),
    ("Out of place", "one file, one deviation", "warn"),
]


def cell_title(name, state, tone):
    colour = {"danger": T["danger"], "warn": T["warn"], "ok": T["ok"], "dim": T["frame_faint"]}[tone]
    return row(txt(name, 15, "#fff", 600),
               f'<span style="flex: 1;"></span>',
               txt(state, 12.5, colour, 500),
               gap=12, extra="width: 100%; flex: none; padding: 0 4px 9px;")


def kcell(name, state, tone, chart, w=None, h=None, grow=False, pad=22):
    surface = col(f'<div style="flex: 1; min-height: 0; display: flex; align-items: center; '
                  f'justify-content: center; overflow: hidden;">{chart}</div>',
                  gap=0, extra=f"flex: 1; min-height: 0; padding: {pad}px; border-radius: 18px; "
                               f"background: {CHART_BG}; box-sizing: border-box;")
    size = (f"width: {w}px; " if w else "") + (f"height: {h}px; " if h else "")
    return col(cell_title(name, state, tone), surface, gap=0,
               extra=f"{size}box-sizing: border-box; {'flex: 1; min-width: 0;' if grow else 'flex: none;'} "
                     f"display: flex; flex-direction: column;")


def kshell(structure, note, brow=""):
    head = row(txt("Must see", 24, "#fff", 700),
               f'<span style="flex: 1;"></span>',
               txt("Wednesday, 14:20", 12.5, T["frame_faint"]), gap=14,
               extra="width: 100%; flex: none;")
    inner = col(brow if brow else "", head, structure,
                row(txt(note, 11.5, T["frame_faint"]), gap=0, extra="flex: none;"),
                gap=16, extra=f"width: {W}px; height: {H}px; box-sizing: border-box; padding: 24px 40px 18px; "
                              f"background: {FRAME['native']}; overflow: hidden; display: flex; "
                              f"flex-direction: column;")
    return page("Must see", "", "", inner, "", "native")


# ------------------------------------------------------------------ the four drawings
def authority(w=600, h=260):
    """Who governs what, and where nobody does. The department with no Admin is the only thing
    coloured against its own department hue."""
    depts = [("Operations", 2, 7), ("Finance", 1, 4), ("Logistics", 0, 3)]
    rx, dx, px = 26, w * 0.40, w * 0.62
    ys = [h * 0.17, h * 0.5, h * 0.83]
    links, nodes, labels = [], [], []
    for i, (name, admins, pcs) in enumerate(depts):
        c = DEPT_COLOR[name]
        dy = ys[i]
        links.append(f'<path d="M{rx + 12} {h * 0.5} C {(rx + dx) / 2} {h * 0.5}, {(rx + dx) / 2} {dy}, '
                     f'{dx - 13} {dy}" fill="none" stroke="{c}" stroke-width="1.8" opacity="0.5"/>')
        for k in range(pcs):
            ox = px + (k % 4) * 38
            oy = dy - 22 + (k // 4) * 34
            bad = (name == "Logistics" and k == 2)
            links.append(f'<path d="M{dx + 12} {dy} C {(dx + px) / 2} {dy}, {(dx + px) / 2} {oy}, {ox - 9} {oy}" '
                         f'fill="none" stroke="{c}" stroke-width="1" opacity="0.2"/>')
            nodes.append(f'<circle cx="{ox}" cy="{oy}" r="{9 if bad else 7}" '
                         f'fill="{ST["failing"] if bad else c}" opacity="{1 if bad else 0.8}"/>')
        nodes.append(f'<circle cx="{dx}" cy="{dy}" r="12" fill="{c}"/>')
        labels.append(f'<text x="{dx - 20}" y="{dy + 1}" text-anchor="end" fill="{T["ink"]}" '
                      f'font-family="{T["sans"]}" font-size="14" font-weight="500">{name}</text>')
        labels.append(f'<text x="{dx - 20}" y="{dy + 18}" text-anchor="end" '
                      f'fill="{T["danger"] if admins == 0 else T["faint"]}" font-family="{T["sans"]}" '
                      f'font-size="12">{"no Admin" if admins == 0 else str(admins) + " Admin" + ("s" if admins > 1 else "")}</text>')
    nodes.append(f'<circle cx="{rx}" cy="{h * 0.5}" r="14" fill="{T["ink"]}"/>')
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(links + nodes + labels)}</svg>'


def rollout_cell(w=560, bars=True):
    parts = [stacked_bars([(n, [("confirmed", a), ("behind", b), ("failing", f)])
                           for n, a, b, f in ROLLOUT], w=w, bar_h=22, gap_y=38)]
    parts.append(col(txt("the fleet, one square each", 11.5, T["faint"]),
                     waffle(FLEET, cols=14, size=24, gap=7, w=min(w, 14 * 31)), gap=10))
    parts.append(legend([("Confirmed", ST["confirmed"]), ("Behind", ST["behind"]), ("Failing", ST["failing"])]))
    return col(*parts, gap=22, extra=f"width: {w}px;")


def rollout_tall(w=420):
    """The same information in a narrow cell: the bars stack and the fleet sits under them."""
    return col(stacked_bars([(n, [("confirmed", a), ("behind", b), ("failing", f)])
                             for n, a, b, f in ROLLOUT], w=w, bar_h=20, gap_y=34),
               col(txt("the fleet, one square each", 11.5, T["faint"]),
                   waffle(FLEET, cols=7, size=26, gap=8, w=7 * 34), gap=10),
               legend([("Confirmed", ST["confirmed"]), ("Behind", ST["behind"]), ("Failing", ST["failing"])]),
               gap=22, extra=f"width: {w}px;")


def day_cell(w=600, lane_h=22, gap_y=9):
    lanes = [("Kojo", [("native", 8.2, 12.0), ("native", 13.0, 17.4)]),
             ("Efua", []),
             ("Yaw", [("native", 9.0, 12.5), ("traversed", 12.5, 13.2), ("native", 13.2, 17.0)]),
             ("Adjoa", [("native", 8.0, 10.3), ("traversed", 10.3, 11.0), ("native", 11.0, 16.0)]),
             ("Nana", [("native", 8.5, 17.5)]),
             ("Kwame", []),
             ("Ama", [("native", 8.2, 10.7), ("su", 10.7, 11.1), ("native", 11.1, 17.6)])]
    kind = {"native": T["line2"], "traversed": T["warn"], "su": T["danger"]}
    t0, t1 = 8.0, 18.0
    label_w = 58
    plot = w - label_w - 12
    out = []
    for hour in range(8, 19, 2):
        x = label_w + ((hour - t0) / (t1 - t0)) * plot
        out.append(f'<line x1="{x:.1f}" y1="2" x2="{x:.1f}" y2="{len(lanes) * (lane_h + gap_y) - gap_y + 2}" '
                   f'stroke="{T["line"]}" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{len(lanes) * (lane_h + gap_y) + 16}" text-anchor="middle" '
                   f'fill="{T["faint"]}" font-family="{T["mono"]}" font-size="11">{hour:02d}</text>')
    for i, (name, blocks) in enumerate(lanes):
        y = 2 + i * (lane_h + gap_y)
        out.append(f'<text x="0" y="{y + lane_h / 2 + 4}" fill="{T["dim"]}" font-family="{T["sans"]}" '
                   f'font-size="12.5">{name}</text>')
        out.append(f'<rect x="{label_w}" y="{y}" width="{plot}" height="{lane_h}" rx="7" '
                   f'fill="{T["pane"]}" opacity="0.5"/>')
        for state, a, b in blocks:
            bx = label_w + ((a - t0) / (t1 - t0)) * plot
            bw = max(5, ((b - a) / (t1 - t0)) * plot - 2)
            out.append(f'<rect x="{bx:.1f}" y="{y}" width="{bw:.1f}" height="{lane_h}" rx="7" fill="{kind[state]}"/>')
    h = len(lanes) * (lane_h + gap_y) + 22
    return col(f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(out)}</svg>',
               legend([("At the PC", T["line2"]), ("An Admin entered", T["warn"]), ("You entered", T["danger"])],
                      "Efua and Kwame were never signed in"),
               gap=16, extra=f"width: {w}px;")


def out_of_place(w=420, tight=False):
    rows_ = [("11:05", "Account used from an unbound PC", "Addressed", "ok"),
             ("09:12", "Hostname did not match the certificate", "Logged", "neutral")]
    if tight:
        rows_ = rows_[:1] + [("09:12", "Hostname did not match", "Logged", "neutral")][:1]
    return col(tier_bars(w=w),
               f'<span style="display: block; height: 1px; background: {T["line"]}; width: 100%;"></span>',
               col(*[row(txt(t, 11.5, T["faint"], mono=True, extra="width: 44px;"),
                         txt(x, 12.5, T["ink"], extra="flex: 1;"), chip(s, tone, 10), gap=10,
                         extra="width: 100%; padding: 8px 0;")
                     for t, x, s, tone in rows_], gap=0, extra=f"width: {w}px;"),
               txt("budget-2026.xlsx, restricted, found in /workers/ on OPS-07.", 11.5, T["faint"]),
               gap=14 if tight else 18, extra=f"width: {w}px;")


# ------------------------------------------------------------------ K01: a perfect grid
def k01():
    CW_, CH_ = 662, 334
    a = kcell(*MUST_SEE[0], authority(w=600, h=268), w=CW_, h=CH_)
    b = kcell(*MUST_SEE[1], rollout_cell(w=560), w=CW_, h=CH_)
    c = kcell(*MUST_SEE[2], day_cell(w=590, lane_h=22, gap_y=8), w=CW_, h=CH_)
    d = kcell(*MUST_SEE[3], out_of_place(w=560), w=CW_, h=CH_)
    body = col(row(a, b, gap=20, align="stretch", extra="flex: none;"),
               row(c, d, gap=20, align="stretch", extra="flex: none;"),
               gap=20, extra="flex: 1; min-height: 0; display: flex; flex-direction: column;")
    return kshell(body,
                  "K01 · A perfect grid. Four equal cells, so nothing claims to matter more than "
                  "anything else — the titles sit above the cells, on the frame.",
                  brow=eyebrow("PAGE", "Overview — must see", "a perfect 2 × 2"))


# ------------------------------------------------------------------ K02: the ranking is the geometry
def k02():
    a = kcell(*MUST_SEE[0], authority(w=740, h=306), w=838, h=386)
    b = kcell(*MUST_SEE[1], rollout_tall(w=420), w=502, h=386)
    c = kcell(*MUST_SEE[2], day_cell(w=740, lane_h=16, gap_y=5), w=838, h=282)
    d = kcell(*MUST_SEE[3], out_of_place(w=420, tight=True), w=502, h=282)
    body = col(row(a, b, gap=20, align="stretch", extra="flex: none;"),
               row(c, d, gap=20, align="stretch", extra="flex: none;"),
               gap=20, extra="flex: 1; min-height: 0; display: flex; flex-direction: column;")
    return kshell(body,
                  "K02 · The same four, sized by how much they matter: authority is the largest cell, "
                  "then the rollout, then the day, then what is out of place.",
                  brow=eyebrow("PAGE", "Overview — must see", "a 2 × 2 with the ranking in the geometry"))


GRID_TAKES = [("K01-Perfect.dc.html", "Must see: a perfect grid", k01),
              ("K02-Ranked.dc.html", "Must see: ranked by size", k02)]
