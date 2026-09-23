# ================================================================== Super User: the system, seen
# The Super User can see every department, Admin, PC, session, rollout, report and violation. That is a
# lot of data, and it should be drawn rather than listed. Three boards: the system at a glance, the
# hierarchy itself, and the record of one day.
#
# Colour: identity (which department) uses a validated categorical ramp; state (confirmed, behind,
# failing) uses the product's reserved status colours and always carries a word as well as a hue.
# Checked with the dataviz validator against the dark chart surface #12151C -- lightness band, chroma
# floor, CVD separation (worst adjacent dE 8.4), normal-vision floor (19.3) and contrast all PASS.

CAT = ["#3987e5", "#d95926", "#199e70", "#c98500", "#d55181"]      # identity, in fixed order
DEPT_COLOR = {"Operations": CAT[0], "Finance": CAT[1], "Logistics": CAT[2]}
ST = {"confirmed": T["ok"], "behind": T["warn"], "failing": T["danger"], "quiet": T["line2"]}
CHART_BG = T["ground"]


def panel(title, note, *children, w=None, h=None):
    head = row(txt(title, 13.5, weight=600), txt(note, 12, T["faint"]) if note else "", gap=10, extra="flex: none;")
    size = (f"width: {w}px; " if w else "") + (f"height: {h}px; " if h else "")
    return col(head, *children, gap=14,
               extra=f"padding: 16px 18px; border-radius: 16px; background: {CHART_BG}; {size}box-sizing: border-box; flex: none;")


def swatch(colour, shape="square"):
    r = "5px" if shape == "square" else "999px"
    return f'<span style="width: 10px; height: 10px; border-radius: {r}; background: {colour}; display: inline-block; flex: none;"></span>'


def legend(items, note=""):
    out = [row(swatch(c), txt(l, 11.5, T["dim"]), gap=6) for l, c in items]
    if note:
        out.append(txt(note, 11.5, T["faint"]))
    return row(*out, gap=16, extra="flex-wrap: wrap;")


def hero(value, label, sub="", tone=None):
    return col(txt(value, 44, tone_c(tone, T["ink"]), 600, mono=True, extra="line-height: 1;"),
               txt(label, 12.5, T["dim"], 500), txt(sub, 11.5, T["faint"]) if sub else "", gap=6)


# ------------------------------------------------------------------ charts
def stacked_bars(rows, w=440, bar_h=18, gap_y=26):
    """One row per department: confirmed / behind / failing, to a common scale. 2 px surface gaps,
    4 px rounded ends on the data ends only, the total direct-labelled."""
    total_max = max(sum(v for _, v in r[1]) for r in rows)
    label_w, pad = 92, 54
    plot = w - label_w - pad
    out, y = [], 4
    for name, parts in rows:
        total = sum(v for _, v in parts)
        x = label_w
        segs = []
        for i, (state, v) in enumerate(parts):
            if v <= 0:
                continue
            seg_w = max(3, (v / total_max) * plot - (2 if i < len(parts) - 1 else 0))
            first, last = i == 0, i == len(parts) - 1
            rx = 4
            segs.append(f'<rect x="{x:.1f}" y="{y}" width="{seg_w:.1f}" height="{bar_h}" rx="{rx}" fill="{ST[state]}"/>')
            if not (first and last):
                # square off the inner edge so only the data ends are rounded
                if not first:
                    segs.append(f'<rect x="{x:.1f}" y="{y}" width="{min(rx, seg_w):.1f}" height="{bar_h}" fill="{ST[state]}"/>')
                if not last:
                    segs.append(f'<rect x="{x + seg_w - rx:.1f}" y="{y}" width="{rx}" height="{bar_h}" fill="{ST[state]}"/>')
            x += seg_w + 2
        out.append(f'<text x="0" y="{y + bar_h - 4}" fill="{T["dim"]}" font-family="{T["sans"]}" font-size="12.5">{name}</text>'
                   + "".join(segs)
                   + f'<text x="{x + 8:.1f}" y="{y + bar_h - 4}" fill="{T["faint"]}" font-family="{T["mono"]}" font-size="12">{total}</text>')
        y += gap_y
    return f'<svg width="{w}" height="{y}" viewBox="0 0 {w} {y}" aria-label="Rollout by department">{"".join(out)}</svg>'


def waffle(cells, cols=7, size=20, gap=6, w=440):
    """One square per client PC, coloured by where it is in the rollout. The fleet, countable."""
    out = []
    for i, (state, label) in enumerate(cells):
        cx, cy = (i % cols) * (size + gap), (i // cols) * (size + gap)
        out.append(f'<rect x="{cx}" y="{cy}" width="{size}" height="{size}" rx="6" fill="{ST[state]}" opacity="{1 if state != "quiet" else 0.5}">'
                   f'<title>{label}</title></rect>')
    rows_n = (len(cells) + cols - 1) // cols
    h = rows_n * (size + gap) - gap
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {cols * (size + gap) - gap} {h}" aria-label="Client PCs by rollout state">{"".join(out)}</svg>'


def trend(points, w=440, h=96, colour=None, label=""):
    """One series, so no legend: the title names it. Last point carries the only marker and label."""
    colour = colour or T["ok"]
    lo, hi = min(points), max(points)
    span = max(1, hi - lo)
    step = (w - 40) / (len(points) - 1)
    pts = [(8 + i * step, h - 20 - ((v - lo) / span) * (h - 44)) for i, v in enumerate(points)]
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    lx, ly = pts[-1]
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" aria-label="{label}">'
            f'<line x1="0" y1="{h - 14}" x2="{w}" y2="{h - 14}" stroke="{T["line"]}" stroke-width="1"/>'
            f'<polyline points="{poly}" fill="none" stroke="{colour}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/>'
            f'<circle cx="{lx:.1f}" cy="{ly:.1f}" r="4.5" fill="{colour}" stroke="{CHART_BG}" stroke-width="2"/>'
            f'<text x="{lx - 6:.1f}" y="{ly - 12:.1f}" text-anchor="end" fill="{T["ink"]}" font-family="{T["mono"]}" font-size="12">{points[-1]}</text>'
            f'</svg>')


def org_map(w=600, h=300, focus=None):
    """Department -> Admin -> PC, drawn. Colour is the department; the shape is the level.
    With `focus`, the same drawing quietens every other department: descent is a change of
    attention, not a different picture."""
    root = (46, h / 2)
    depts = [("Operations", 2, 7), ("Finance", 1, 4), ("Logistics", 0, 3)]
    dx, px = 210, 400
    links, nodes, labels = [], [], []
    spread = [h * 0.22, h * 0.5, h * 0.78]
    for i, (name, admins, pcs) in enumerate(depts):
        c = DEPT_COLOR[name]
        on = focus is None or focus == name
        fade = "" if on else ' opacity="0.22"'
        dy = spread[i]
        links.append(f'<path d="M{root[0] + 10} {root[1]} C {(root[0] + dx) / 2} {root[1]}, {(root[0] + dx) / 2} {dy}, {dx - 9} {dy}" '
                     f'fill="none" stroke="{c}" stroke-width="1.5" opacity="{0.55 if on else 0.14}"/>')
        nodes.append(f'<circle cx="{dx}" cy="{dy}" r="{10 if focus == name else 8}" fill="{c}"{fade}/>')
        if focus == name:
            nodes.append(f'<circle cx="{dx}" cy="{dy}" r="15" fill="none" stroke="{c}" stroke-width="1.5" opacity="0.45"/>')
        lx = dx - (22 if focus == name else 14)
        labels.append(f'<text x="{lx}" y="{dy + 4}" text-anchor="end" fill="{T["ink"] if on else T["faint"]}" '
                      f'font-family="{T["sans"]}" font-size="12.5" font-weight="{600 if focus == name else 400}">{name}</text>')
        # the PCs of this department, as a small constellation
        per_row = 4
        for k in range(pcs):
            ox = px + (k % per_row) * 22
            oy = dy - 18 + (k // per_row) * 20
            links.append(f'<path d="M{dx + 9} {dy} C {(dx + px) / 2} {dy}, {(dx + px) / 2} {oy}, {ox - 5} {oy}" fill="none" '
                         f'stroke="{c}" stroke-width="1" opacity="{0.28 if on else 0.08}"/>')
            nodes.append(f'<circle cx="{ox}" cy="{oy}" r="5" fill="{c}" opacity="{0.85 if on else 0.2}"/>')
        if admins == 0:
            labels.append(f'<text x="{lx}" y="{dy + 21}" text-anchor="end" fill="{T["danger"] if on else T["faint"]}" font-family="{T["sans"]}" font-size="11.5">no Admin</text>')
        else:
            labels.append(f'<text x="{lx}" y="{dy + 21}" text-anchor="end" fill="{T["faint"]}" font-family="{T["sans"]}" font-size="11.5">{admins} Admin{"s" if admins > 1 else ""}</text>')
    nodes.append(f'<circle cx="{root[0]}" cy="{root[1]}" r="10" fill="{T["ink"]}"/>')
    labels.append(f'<text x="{root[0]}" y="{root[1] + 26}" text-anchor="middle" fill="{T["dim"]}" font-family="{T["sans"]}" font-size="12">you</text>')
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" aria-label="The hierarchy">{"".join(links + nodes + labels)}</svg>'


def arcs(w=440, h=150):
    """Cross-department assistance: who helped whom, and how often. Thickness is the count."""
    names = ["Operations", "Finance", "Logistics"]
    xs = {n: (w * (i + 1)) / (len(names) + 1) for i, n in enumerate(names)}
    base = h - 34
    out = []
    for a, b, n in [("Operations", "Finance", 2), ("Finance", "Logistics", 1)]:
        x1, x2 = xs[a], xs[b]
        r = abs(x2 - x1) / 2
        out.append(f'<path d="M{x1} {base} A {r} {r * 0.72} 0 0 1 {x2} {base}" fill="none" stroke="{DEPT_COLOR[a]}" '
                   f'stroke-width="{1 + n * 1.6}" opacity="0.8" stroke-linecap="round"/>')
        out.append(f'<text x="{(x1 + x2) / 2}" y="{base - r * 0.72 - 8}" text-anchor="middle" fill="{T["faint"]}" '
                   f'font-family="{T["mono"]}" font-size="11.5">{n}</text>')
    for name, x in xs.items():
        out.append(f'<circle cx="{x}" cy="{base}" r="7" fill="{DEPT_COLOR[name]}"/>')
        out.append(f'<text x="{x}" y="{base + 22}" text-anchor="middle" fill="{T["dim"]}" font-family="{T["sans"]}" font-size="12">{name}</text>')
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" aria-label="Assistance between departments">{"".join(out)}</svg>'


def routing(w=440, h=190):
    """Report routing: a category always reaches you, and additively reaches the departments you chose."""
    cats = [("Listener reports", ["Operations"]), ("Violations", ["Operations", "Finance"]),
            ("Flow failures", []), ("Assistance", []), ("Deviations", [])]
    dests = {"Operations": 40, "Finance": 90}
    lx, rx = 4, w - 120
    out = []
    for i, (cat, to) in enumerate(cats):
        y = 16 + i * 34
        out.append(f'<text x="{lx}" y="{y + 4}" fill="{T["dim"]}" font-family="{T["sans"]}" font-size="12.5">{cat}</text>')
        out.append(f'<path d="M{lx + 118} {y} C {lx + 190} {y}, {rx - 70} 150, {rx} 150" fill="none" stroke="{T["line2"]}" stroke-width="1.5" opacity="0.6"/>')
        for d in to:
            out.append(f'<path d="M{lx + 118} {y} C {lx + 190} {y}, {rx - 70} {dests[d]}, {rx} {dests[d]}" fill="none" '
                       f'stroke="{DEPT_COLOR[d]}" stroke-width="2.5" opacity="0.85"/>')
    for d, y in dests.items():
        out.append(f'<circle cx="{rx}" cy="{y}" r="6" fill="{DEPT_COLOR[d]}"/>')
        out.append(f'<text x="{rx + 12}" y="{y + 4}" fill="{T["ink"]}" font-family="{T["sans"]}" font-size="12.5">{d}</text>')
    out.append(f'<circle cx="{rx}" cy="150" r="7" fill="{T["ink"]}"/>')
    out.append(f'<text x="{rx + 12}" y="154" fill="{T["ink"]}" font-family="{T["sans"]}" font-size="12.5">You, always</text>')
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" aria-label="Report routing">{"".join(out)}</svg>'


def day_timeline(w=600, h=250, lane_h=22):
    """A day on every PC: who held each session, and for how long. One lane per PC, 08:00 to 18:00."""
    lanes = [("Kojo", [("native", 8.2, 12.0), ("native", 13.0, 17.4)]),
             ("Efua", [("quiet", 8.0, 18.0)]),
             ("Yaw", [("native", 9.0, 12.5), ("traversed", 12.5, 13.2), ("native", 13.2, 17.0)]),
             ("Adjoa", [("native", 8.0, 10.3), ("traversed", 10.3, 11.0), ("native", 11.0, 16.0)]),
             ("Nana", [("native", 8.5, 17.5)]),
             ("Kwame", [("quiet", 8.0, 18.0)]),
             ("Ama", [("native", 8.2, 10.7), ("su", 10.7, 11.1), ("native", 11.1, 17.6)])]
    kind = {"native": T["line2"], "traversed": T["warn"], "su": T["danger"], "quiet": "transparent"}
    t0, t1 = 8.0, 18.0
    label_w = 62
    plot = w - label_w - 8
    gap = 10
    out = []
    for hour in range(8, 19, 2):
        x = label_w + ((hour - t0) / (t1 - t0)) * plot
        out.append(f'<line x1="{x:.1f}" y1="4" x2="{x:.1f}" y2="{len(lanes) * (lane_h + gap)}" stroke="{T["line"]}" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{len(lanes) * (lane_h + gap) + 16}" text-anchor="middle" fill="{T["faint"]}" '
                   f'font-family="{T["mono"]}" font-size="11">{hour:02d}</text>')
    for i, (name, blocks) in enumerate(lanes):
        y = 6 + i * (lane_h + gap)
        out.append(f'<text x="0" y="{y + 15}" fill="{T["dim"]}" font-family="{T["sans"]}" font-size="12.5">{name}</text>')
        out.append(f'<rect x="{label_w}" y="{y}" width="{plot}" height="{lane_h}" rx="6" fill="{T["pane"]}" opacity="0.5"/>')
        for state, a, b in blocks:
            if state == "quiet":
                continue
            bx = label_w + ((a - t0) / (t1 - t0)) * plot
            bw = max(4, ((b - a) / (t1 - t0)) * plot - 2)
            out.append(f'<rect x="{bx:.1f}" y="{y}" width="{bw:.1f}" height="{lane_h}" rx="6" fill="{kind[state]}"><title>{name} {a:.1f}-{b:.1f}</title></rect>')
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}" aria-label="Sessions today">{"".join(out)}</svg>'


def tier_bars(w=440):
    """Violations by tier: few enough to be a bar chart, serious enough to name each one."""
    data = [("/restricted/", 1, "failing"), ("/workers/", 0, "quiet"), ("/common/", 0, "quiet")]
    out, y = [], 6
    for name, n, tone in data:
        bw = max(6, n * 120)
        out.append(f'<text x="0" y="{y + 13}" fill="{T["dim"]}" font-family="{T["sans"]}" font-size="12.5">{name}</text>')
        out.append(f'<rect x="96" y="{y}" width="{bw}" height="16" rx="4" fill="{ST[tone]}" opacity="{1 if n else 0.35}"/>')
        out.append(f'<text x="{96 + bw + 8}" y="{y + 13}" fill="{T["faint"]}" font-family="{T["mono"]}" font-size="12">{n}</text>')
        y += 26
    return f'<svg width="{w}" height="{y}" viewBox="0 0 {w} {y}" aria-label="Violations by tier">{"".join(out)}</svg>'



# ------------------------------------------------------------------ per-department health
# A small multiple: the same two bars, drawn once per department, to one scale. Identity is the
# swatch; state is the reserved colours, and the legend carries the words.
WORDS = {"tasks": [("On track", "confirmed"), ("Due soon", "behind"), ("Overdue", "failing")],
         "flows": [("Syncing", "confirmed"), ("Paused", "behind"), ("Failing", "failing")]}


def mini_bar(parts, w=162, h=9):
    total = max(1, sum(v for _, v in parts))
    x, out = 0, []
    out.append(f'<rect x="0" y="0" width="{w}" height="{h}" rx="{h / 2}" fill="{T["line"]}" opacity="0.55"/>')
    for state, v in parts:
        if v <= 0:
            continue
        sw = max(4, (v / total) * w - 2)
        out.append(f'<rect x="{x:.1f}" y="0" width="{sw:.1f}" height="{h}" rx="{h / 2}" fill="{ST[state]}"/>')
        x += sw + 2
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(out)}</svg>'


def health_line(label, parts, w=162):
    total = sum(v for _, v in parts)
    head = row(txt(label, 11.5, T["dim"]), txt(str(total), 11.5, T["faint"], mono=True),
               gap=8, justify="space-between", extra="width: 100%;")
    return col(head, mini_bar(parts, w=w), gap=5, extra="width: 100%;")


def health_card(name, colour, tasks, flows, w=190):
    return col(row(swatch(colour, "dot"), txt(name, 12.5, T["ink"], 600), gap=7),
               health_line("Tasks", tasks, w=w - 28), health_line("Flows", flows, w=w - 28),
               gap=11, extra=f"width: {w}px; padding: 13px 14px; border-radius: 12px; background: {T['pane']}; "
                             "box-sizing: border-box; flex: none;")


def health_panel(w=650):
    cards = [health_card("Operations", DEPT_COLOR["Operations"], [("confirmed", 5), ("behind", 2), ("failing", 1)],
                         [("confirmed", 3), ("behind", 0), ("failing", 1)]),
             health_card("Finance", DEPT_COLOR["Finance"], [("confirmed", 3), ("behind", 0), ("failing", 0)],
                         [("confirmed", 2), ("behind", 1), ("failing", 0)]),
             health_card("Logistics", DEPT_COLOR["Logistics"], [("confirmed", 1), ("behind", 1), ("failing", 2)],
                         [("confirmed", 0), ("behind", 0), ("failing", 0)])]
    return panel("Work, by department", "the same two bars, three times",
                 row(*cards, gap=14, align="stretch"),
                 legend([("On track", ST["confirmed"]), ("Due soon", ST["behind"]), ("Overdue / failing", ST["failing"])],
                        "Logistics has no Admin, and no flows"), w=w)


# ------------------------------------------------------------------ D01: the system at a glance
def d01():
    heroes = row(hero("14", "client PCs", "across 3 departments"),
                 hero("12", "on 1.4.2", "2 still behind", "warn"),
                 hero("2", "waiting on you", "approval, and an empty department", "danger"),
                 hero("4", "traversals today", "1 still open"),
                 gap=64, extra="flex: none;")

    roll = panel("Rollout 1.4.2", "by department, to the same scale",
                 stacked_bars([("Operations", [("confirmed", 6), ("behind", 1), ("failing", 0)]),
                               ("Finance", [("confirmed", 4), ("behind", 0), ("failing", 0)]),
                               ("Logistics", [("confirmed", 2), ("behind", 0), ("failing", 1)])], w=640),
                 legend([("Confirmed", ST["confirmed"]), ("Behind", ST["behind"]), ("Failing", ST["failing"])],
                        "1.4.3 stays blocked until all 14 confirm"), w=690)

    fleet = panel("The fleet", "one square per PC",
                  waffle([("confirmed", "OPS-01")] * 6 + [("behind", "OPS-06 retrying")] +
                         [("confirmed", "FIN")] * 4 + [("confirmed", "LOG")] * 2 + [("failing", "LOG-02, 6 failures")],
                         cols=14, size=30, gap=8, w=524),
                  legend([("Confirmed", ST["confirmed"]), ("Behind", ST["behind"]), ("Failing", ST["failing"])]), w=654)

    tr = panel("Confirmations", "since the rollout was approved, Monday",
               trend([0, 3, 6, 8, 10, 11, 12], w=640, h=118, label="PCs confirmed on 1.4.2"),
               row(*[txt(d, 11.5, T["faint"], extra="width: 88px; text-align: center;") for d in
                     ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Today"]], gap=0), w=690)

    inner = col(row(f'<span style="width: 10px; height: 26px; border-radius: 3px; background: #fff;"></span>',
                    txt("Everything", 22, "#fff", 700), txt("3 departments  ·  3 Admins  ·  14 client PCs", 13, T["frame_dim"]), gap=12),
                col(heroes, gap=0, extra=f"padding: 20px 24px; border-radius: 16px; background: {CHART_BG};"),
                row(roll, fleet, gap=16, align="stretch", extra="flex: 1; min-height: 0;"),
                row(tr, health_panel(w=654), gap=16, align="stretch", extra="flex: 1; min-height: 0;"),
                gap=16, extra=f"width: {W}px; height: {H}px; box-sizing: border-box; padding: 26px 40px; background: {FRAME['native']}; overflow: hidden;")
    return page("Super User: the system at a glance", "", "", inner, "", "native")


# ------------------------------------------------------------------ D02: the hierarchy, seen
def d02():
    themap = panel("The hierarchy", "every department, Admin and PC you govern", org_map(w=620, h=290),
                   legend([(d, c) for d, c in DEPT_COLOR.items()],
                          "colour is the department, everywhere  ·  pick one to descend into it"), w=660)
    arcp = panel("Assistance between departments", "peer help, by consent", arcs(w=420, h=150),
                 txt("You see every session and gate none of them.", 11.5, T["faint"]), w=460)
    rout = panel("Report routing", "additive: routing never takes your copy away", routing(w=420, h=190), w=460)

    inner = col(row(f'<span style="width: 10px; height: 26px; border-radius: 3px; background: #fff;"></span>',
                    txt("The hierarchy, seen", 22, "#fff", 700), gap=12),
                row(themap, col(arcp, rout, gap=16), gap=16, align="flex-start"),
                gap=16, extra=f"width: {W}px; height: {H}px; box-sizing: border-box; padding: 26px 40px; background: {FRAME['native']}; overflow: hidden;")
    return page("Super User: the hierarchy, seen", "", "", inner, "", "native")


# ------------------------------------------------------------------ D03: the record of a day
def d03():
    tl = panel("Sessions today", "who held each PC, and for how long", day_timeline(w=620, h=250),
               legend([("At the PC", T["line2"]), ("An Admin entered", T["warn"]), ("You entered", T["danger"])],
                      "Efua and Kwame were never signed in"), w=660)
    vio = panel("Violations by tier", "restricted files found where they should not be", tier_bars(w=420),
                txt("budget-2026.xlsx, found in /workers/ on OPS-07 at 10:41.", 11.5, T["faint"]), w=460)
    dev = panel("Deviations", "logged, surfaced, never silently corrected",
                col(*[row(txt(t, 11.5, T["faint"], mono=True, extra="width: 46px;"), txt(x, 12.5, extra="flex: 1;"),
                          chip(s, tone, 10), gap=10, extra="padding: 7px 0;")
                      for t, x, s, tone in [("11:05", "Account used from an unbound PC", "Addressed", "ok"),
                                            ("09:12", "Hostname did not match the certificate", "Logged", "neutral")]], gap=0), w=460)

    inner = col(row(f'<span style="width: 10px; height: 26px; border-radius: 3px; background: #fff;"></span>',
                    txt("The record", 22, "#fff", 700), txt("Today, 08:00 to now", 13, T["frame_dim"]), gap=12),
                row(tl, col(vio, dev, gap=16), gap=16, align="flex-start"),
                gap=16, extra=f"width: {W}px; height: {H}px; box-sizing: border-box; padding: 26px 40px; background: {FRAME['native']}; overflow: hidden;")
    return page("Super User: the record", "", "", inner, "", "native")



# ------------------------------------------------------------------ D04: descending into one department
# Descent is a change of attention, not a different picture: the same map, everything else quietened,
# and the right-hand column swaps from the system's relationships to this department's own numbers.
def d04():
    themap = panel("The hierarchy", "Operations, in place", org_map(w=620, h=250, focus="Operations"),
                   legend([(d, c) for d, c in DEPT_COLOR.items()], "back out by picking `Everything`"), w=690)

    people = panel("Its Admins", "who governs here",
                   col(*[row(f'<span style="width: 30px; height: 30px; border-radius: 9px; background: {T["line2"]}; '
                             f'display: inline-flex; align-items: center; justify-content: center; font-family: {T["sans"]}; '
                             f'font-size: 11.5px; font-weight: 600; color: {T["ink"]}; flex: none;">{ini}</span>',
                             col(txt(name, 13, T["ink"], 500), txt(host, 11.5, T["faint"], mono=True), gap=1),
                             f'<span style="flex: 1;"></span>', chip(state, tone, 11), gap=11,
                             extra="padding: 8px 0;")
                         for ini, name, host, state, tone in
                         [("RM", "R. Mensah", "WS-OPS-A1", "At the PC", "neutral"),
                          ("AQ", "A. Quaye", "WS-OPS-A2", "Helping Finance", "accent")]], gap=0), w=690)

    lanes = panel("Sessions today, here", "who held each PC, and for how long", day_timeline(w=610, h=250),
                  legend([("At the PC", T["line2"]), ("An Admin entered", T["warn"]), ("You entered", T["danger"])]), w=654)

    work = panel("Operations, in numbers", "its rollout, and its work",
                 stacked_bars([("Rollout", [("confirmed", 6), ("behind", 1), ("failing", 0)])], w=606),
                 row(health_card("Tasks and flows", DEPT_COLOR["Operations"],
                                 [("confirmed", 5), ("behind", 2), ("failing", 1)],
                                 [("confirmed", 3), ("behind", 0), ("failing", 1)], w=290),
                     col(hero("1", "PC behind", "OPS-06, retrying", "warn"),
                         hero("2", "waiting on you", "a ping, and a violation", "danger"), gap=18),
                     gap=20, align="flex-start"),
                 legend([("Confirmed / on track", ST["confirmed"]), ("Behind / due soon", ST["behind"]),
                         ("Failing / overdue", ST["failing"])]), w=654)

    inner = col(row(txt("Everything", 13, T["frame_faint"]), txt("›", 13, T["frame_faint"]),
                    txt("Operations", 13, T["frame_dim"], 600), gap=8),
                row(f'<span style="width: 10px; height: 26px; border-radius: 3px; background: {DEPT_COLOR["Operations"]};"></span>',
                    txt("Operations", 22, "#fff", 700),
                    txt("2 Admins  ·  7 client PCs  ·  6 on 1.4.2", 13, T["frame_dim"]), gap=12),
                row(col(themap, people, gap=16, extra="flex: none;"), col(lanes, work, gap=16, extra="flex: none;"),
                    gap=16, align="flex-start", extra="flex: 1; min-height: 0;"),
                gap=14, extra=f"width: {W}px; height: {H}px; box-sizing: border-box; padding: 26px 40px; background: {FRAME['native']}; overflow: hidden;")
    return page("Super User: descending into a department", "", "", inner, "", "native")


SU_DASH = [("D01-Glance.dc.html", "Super User: the system at a glance", d01),
           ("D02-Hierarchy.dc.html", "Super User: the hierarchy, seen", d02),
           ("D03-Record.dc.html", "Super User: the record of a day", d03),
           ("D04-Department.dc.html", "Super User: descending into a department", d04)]
