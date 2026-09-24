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


def kcell(name, state, tone, chart, w=None, h=None, grow=False, pad=22, top=False):
    surface = col(f'<div style="flex: 1; min-height: 0; display: flex; align-items: '
                  f'{"flex-start" if top else "center"}; '
                  f'justify-content: {"flex-start" if top else "center"}; overflow: hidden;">{chart}</div>',
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



# ------------------------------------------------------------------ K03-K04: a cell, opened in place
# When a chart is clicked the page does not navigate -- it RECOMPOSES around it. The clicked cell
# grows where it already is, and the panels around it become the gradient that explains it: shapes
# first, then a shape with its sentence, then the words.
#
# THE COMPOSITION IS PER CELL. Authority opens into the shape below -- the one that was drawn on
# board P03 and that the user picked out: a big chart, two told panels beneath it, and one tall
# reading panel down the right. Rollout does not want that shape at all; its subject is a fleet, so
# it opens wide (K04). Every cell declares the composition its own subject needs.
#
# Four rules keep it from becoming a maze:
#   1. The clicked cell GROWS WHERE IT IS. It never jumps to first position -- if everything moves
#      at once you lose your place, and the anchor is the whole point.
#   2. One level only. Inside an opened cell a click selects or filters; it never opens again.
#   3. Back is the same gesture, or Escape, and the grid returns exactly as it was.
#   4. A cell with nothing to explain does not open.
def opened_head(subject):
    return row(txt("Must see", 15, T["frame_faint"], 500),
               ic("chev", 14, T["frame_faint"]),
               txt(subject, 15, "#fff", 600),
               f'<span style="flex: 1;"></span>',
               txt("Esc to go back", 12, T["frame_faint"]),
               gap=9, extra="width: 100%; flex: none; padding: 0 0 12px;")


def tall_shape(hero, told_a, told_b, reading_, hero_h=352, told_h=236, right_w=372):
    """The P03 shape: a big chart, two told panels beneath it, one tall reading panel down the
    right. It suits a subject whose shape is the point and whose meaning needs saying at length."""
    left_w = 1360 - right_w - 20
    bottom_w = (left_w - 20) // 2
    return row(col(kcell(*hero[:3], hero[3], w=left_w, h=hero_h + 33),
                   row(kcell(*told_a[:3], told_a[3], w=bottom_w, h=told_h + 33),
                       kcell(*told_b[:3], told_b[3], w=bottom_w, h=told_h + 33),
                       gap=20, align="stretch", extra="flex: none;"),
                   gap=20, extra="flex: none; display: flex; flex-direction: column;"),
               kcell(*reading_[:3], reading_[3], w=right_w, h=hero_h + told_h + 53, top=True),
               gap=20, align="flex-start", extra="flex: 1; min-height: 0;")


def wide_shape(hero, told_a, told_b, reading_, hero_h=300):
    """A different shape for a different subject: the hero runs the full width, and the three
    panels that explain it sit in a row beneath. A fleet is wide, so its page is."""
    third = (1360 - 40) // 3
    rest_h = 720 - hero_h - 33 - 20 - 33
    return col(kcell(*hero[:3], hero[3], w=1360, h=hero_h + 33),
               row(kcell(*told_a[:3], told_a[3], w=third, h=rest_h + 33),
                   kcell(*told_b[:3], told_b[3], w=third, h=rest_h + 33),
                   kcell(*reading_[:3], reading_[3], w=third, h=rest_h + 33, top=True),
                   gap=20, align="stretch", extra="flex: none;"),
               gap=20, extra="flex: 1; min-height: 0; display: flex; flex-direction: column;")


def opened_page(subject, shape, note, brow_phrase):
    inner = col(eyebrow("BEHAVIOUR", brow_phrase, "the composition is per cell"),
                row(txt("Must see", 24, "#fff", 700),
                    f'<span style="flex: 1;"></span>',
                    txt("Wednesday, 14:20", 12.5, T["frame_faint"]), gap=14,
                    extra="width: 100%; flex: none;"),
                opened_head(subject), shape,
                row(txt(note, 11.5, T["frame_faint"]), gap=0, extra="flex: none;"),
                gap=14, extra=f"width: {W}px; height: {H}px; box-sizing: border-box; padding: 24px 40px 18px; "
                              f"background: {FRAME['native']}; overflow: hidden; display: flex; "
                              f"flex-direction: column;")
    return page("Must see", "", "", inner, "", "native")


# --- the panels Authority opens into -----------------------------------------------------------
def logistics_pcs(w=420):
    marks = []
    for i, (host, st, note) in enumerate([("LOG-01", "confirmed", "on 1.4.2"),
                                          ("LOG-03", "confirmed", "on 1.4.2"),
                                          ("LOG-02", "failing", "failed 6 times")]):
        x = i * 128
        marks.append(f'<rect x="{x}" y="0" width="112" height="58" rx="14" fill="{ST[st]}" opacity="0.9"/>')
        marks.append(f'<text x="{x + 56}" y="35" text-anchor="middle" fill="{CHART_BG}" '
                     f'font-family="{T["mono"]}" font-size="14" font-weight="500">{host}</text>')
        marks.append(f'<text x="{x + 56}" y="78" text-anchor="middle" fill="{T["faint"]}" '
                     f'font-family="{T["sans"]}" font-size="11.5">{note}</text>')
    return f'<svg width="{w}" height="86" viewBox="0 0 {3 * 128 - 16} 86">{"".join(marks)}</svg>'


def scoped_day(names, used, w=400):
    t0, t1 = 8.0, 18.0
    label_w, lane_h, gap_y = 62, 18, 9
    plot = w - label_w - 10
    out = []
    for i, name in enumerate(names):
        y = 2 + i * (lane_h + gap_y)
        out.append(f'<text x="0" y="{y + lane_h / 2 + 4}" fill="{T["dim"]}" font-family="{T["sans"]}" '
                   f'font-size="12">{name}</text>')
        out.append(f'<rect x="{label_w}" y="{y}" width="{plot}" height="{lane_h}" rx="6" '
                   f'fill="{T["pane"]}" opacity="0.5"/>')
        if name in used:
            a, b = used[name]
            bx = label_w + ((a - t0) / (t1 - t0)) * plot
            bw = max(5, ((b - a) / (t1 - t0)) * plot - 2)
            out.append(f'<rect x="{bx:.1f}" y="{y}" width="{bw:.1f}" height="{lane_h}" rx="6" fill="{T["line2"]}"/>')
    h = len(names) * (lane_h + gap_y)
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(out)}</svg>'


def reading_block(sentence, facts, action, w=330):
    return col(txt(sentence, 15, T["ink"], 600, extra="line-height: 1.35;"),
               col(*[row(txt(k, 12.5, T["dim"]), f'<span style="flex: 1;"></span>',
                         txt(v, 12.5, tone_c(tone, T["ink"]) if tone else T["ink"], 500), gap=10,
                         extra=f"width: 100%; padding: 8px 0; border-bottom: 1px solid {T['line']};")
                     for k, v, tone in facts], gap=0, extra="width: 100%;"),
               row(f'<span style="display: inline-flex; align-items: center; height: 32px; padding: 0 14px; '
                   f'border-radius: 9px; background: {T["accent_soft"]}; color: {T["accent"]}; '
                   f'font-family: {T["sans"]}; font-size: 12.5px; font-weight: 500;">{action}</span>',
                   gap=0, extra="padding-top: 6px;") if action else "",
               gap=16, extra=f"width: {w}px;")


def k03():
    shape = tall_shape(
        ("The hierarchy", "Logistics has no Admin", "danger", authority(w=850, h=356)),
        ("Its client PCs", "one failing", "danger", logistics_pcs(w=420)),
        ("Sessions there", "one machine used", "dim",
         col(scoped_day(["Esi", "Abena", "LOG-02"], {"Esi": (9.0, 16.2)}, w=400),
             txt("Only one of the three was used today.", 12.5, T["ink"], 500), gap=14)),
        ("What the gap means", "four days", "danger",
         reading_block("Nobody below you has governed Logistics for four days.",
                       [("Ungoverned PCs", "3", "danger"), ("Last traversal", "you, 4 days ago", ""),
                        ("Unaddressed reports", "2", "warn"), ("Its Admins", "none", "danger")],
                       "Assign an Admin")))
    return opened_page("Authority", shape,
                       "K03 · Authority opened, in the shape from board P03: a big chart, two told panels "
                       "beneath it, one tall reading panel down the right.",
                       "Authority, opened")


def k04():
    shape = wide_shape(
        ("The fleet", "2 of 14 behind", "warn",
         col(waffle(FLEET, cols=14, size=48, gap=12, w=14 * 60), gap=0)),
        ("By department", "Logistics failing", "danger",
         col(stacked_bars([(n, [("confirmed", a), ("behind", b), ("failing", f)])
                           for n, a, b, f in ROLLOUT], w=380, bar_h=16, gap_y=28),
             txt("Logistics is the only one failing.", 12.5, T["ink"], 500), gap=14)),
        ("Since Monday", "stalled since Friday", "warn",
         col(trend(SERIES, w=380, h=120),
             txt("Nothing has confirmed for three days.", 12.5, T["ink"], 500), gap=14)),
        ("What is blocking", "1.4.3 held", "warn",
         reading_block("Approving 1.4.3 stays blocked until both confirm.",
                       [("Retrying", "OPS-06", "warn"), ("Failing", "LOG-02, 6 attempts", "danger"),
                        ("Threshold", "3 attempts", "")],
                       "Prompt their Admins", w=330)))
    return opened_page("Rollout 1.4.2", shape,
                       "K04 · Rollout opened, and it does NOT take Authority's shape. Its subject is a "
                       "fleet, so the hero runs the full width and the three that explain it sit beneath.",
                       "Rollout, opened")


GRID_TAKES = [("K01-Perfect.dc.html", "Must see: a perfect grid", k01),
              ("K02-Ranked.dc.html", "Must see: ranked by size", k02),
              ("K03-Opened.dc.html", "Must see: Authority opened", k03),
              ("K04-Opened-Wide.dc.html", "Must see: Rollout opened, a different shape", k04)]
