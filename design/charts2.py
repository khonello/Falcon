# ================================================================== Chart mood boards, C06-C10
# The second half: the relationship diagrams, the small counts, the work small multiple, and the
# figures themselves. Same rule as C01-C05 — one chart type per board, four real alternatives.

import math as _math

PAIRS = [("Operations", "Finance", 2), ("Finance", "Logistics", 1)]
DEPTS = ["Operations", "Finance", "Logistics"]


# ------------------------------------------------------------------ C06: assistance
def chord(w=340, h=280):
    """A circle of departments with the help drawn across it. Direction is the taper: thick where
    it left, thin where it arrived."""
    cx, cy, r = w / 2, h / 2 - 6, 96
    pos = {}
    out = []
    for i, d in enumerate(DEPTS):
        ang = _math.radians(-90 + i * (360 / len(DEPTS)))
        pos[d] = (cx + _math.cos(ang) * r, cy + _math.sin(ang) * r, ang)
    out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{T["line"]}" stroke-width="1"/>')
    for a, b, n in PAIRS:
        xa, ya, _ = pos[a]
        xb, yb, _ = pos[b]
        out.append(f'<path d="M{xa:.1f} {ya:.1f} Q {cx} {cy} {xb:.1f} {yb:.1f}" fill="none" '
                   f'stroke="{DEPT_COLOR[a]}" stroke-width="{1.5 + n * 2}" opacity="0.8" stroke-linecap="round"/>')
    for d, (x, y, ang) in pos.items():
        out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="8" fill="{DEPT_COLOR[d]}"/>')
        lx, ly = cx + _math.cos(ang) * (r + 26), cy + _math.sin(ang) * (r + 26)
        out.append(f'<text x="{lx:.1f}" y="{ly + 4:.1f}" text-anchor="middle" fill="{T["dim"]}" '
                   f'font-family="{T["sans"]}" font-size="12">{d}</text>')
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(out)}</svg>'


def ribbons(w=520, h=230):
    """Two columns: who gave help on the left, who received it on the right. Direction is the
    layout, so nothing has to carry an arrowhead."""
    lx, rx = 130, w - 160
    out = [f'<text x="{lx}" y="16" text-anchor="middle" fill="{T["faint"]}" font-family="{T["sans"]}" font-size="11.5">Helped</text>',
           f'<text x="{rx}" y="16" text-anchor="middle" fill="{T["faint"]}" font-family="{T["sans"]}" font-size="11.5">Was helped</text>']
    ys = {d: 56 + i * 62 for i, d in enumerate(DEPTS)}
    for a, b, n in PAIRS:
        ya, yb = ys[a], ys[b]
        out.append(f'<path d="M{lx + 10} {ya} C {(lx + rx) / 2} {ya}, {(lx + rx) / 2} {yb}, {rx - 10} {yb}" '
                   f'fill="none" stroke="{DEPT_COLOR[a]}" stroke-width="{2 + n * 3}" opacity="0.7" stroke-linecap="round"/>')
        out.append(f'<text x="{(lx + rx) / 2}" y="{(ya + yb) / 2 - 8}" text-anchor="middle" fill="{T["faint"]}" '
                   f'font-family="{T["mono"]}" font-size="11.5">{n}</text>')
    for d, y in ys.items():
        out.append(f'<circle cx="{lx}" cy="{y}" r="7" fill="{DEPT_COLOR[d]}"/>')
        out.append(f'<text x="{lx - 14}" y="{y + 4}" text-anchor="end" fill="{T["dim"]}" font-family="{T["sans"]}" font-size="12">{d}</text>')
        out.append(f'<circle cx="{rx}" cy="{y}" r="7" fill="{DEPT_COLOR[d]}" opacity="0.5"/>')
        out.append(f'<text x="{rx + 14}" y="{y + 4}" fill="{T["dim"]}" font-family="{T["sans"]}" font-size="12">{d}</text>')
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(out)}</svg>'


def pair_rows(w=520):
    """One line per pair, read as a sentence: who helped whom, how often, and when it last was."""
    out, y = [], 18
    for a, b, n in PAIRS + [("Logistics", "Operations", 0)]:
        dim = n == 0
        out.append(f'<circle cx="8" cy="{y - 4}" r="6" fill="{DEPT_COLOR[a]}" opacity="{0.3 if dim else 1}"/>')
        out.append(f'<text x="22" y="{y}" fill="{T["faint"] if dim else T["ink"]}" font-family="{T["sans"]}" font-size="12.5">{a}</text>')
        out.append(f'<path d="M{118} {y - 4} h28 m-6 -4 l6 4 l-6 4" fill="none" stroke="{T["line2"]}" stroke-width="1.5"/>')
        out.append(f'<circle cx="{160}" cy="{y - 4}" r="6" fill="{DEPT_COLOR[b]}" opacity="{0.3 if dim else 1}"/>')
        out.append(f'<text x="{174}" y="{y}" fill="{T["faint"] if dim else T["ink"]}" font-family="{T["sans"]}" font-size="12.5">{b}</text>')
        for k in range(max(n, 1)):
            out.append(f'<rect x="{290 + k * 16}" y="{y - 13}" width="11" height="11" rx="3" '
                       f'fill="{DEPT_COLOR[a] if n else T["line"]}" opacity="{1 if n else 0.6}"/>')
        out.append(f'<text x="{356}" y="{y}" fill="{T["faint"]}" font-family="{T["sans"]}" font-size="11.5">'
                   f'{"never" if not n else str(n) + (" session" if n == 1 else " sessions")}</text>')
        y += 34
    return f'<svg width="{w}" height="{y}" viewBox="0 0 {w} {y}">{"".join(out)}</svg>'


def c06():
    note = txt("You see every session and gate none of them.", 11.5, T["faint"])
    return mood("Assistance, four ways", "cross-department help today — by consent, never gated", [
        variant("A · Arcs", "a baseline of peers, help drawn over it", arcs(w=540, h=200), CW, CH, note),
        variant("B · Chord", "a circle of peers; thickness is the count", chord(w=540, h=270), CW, CH, note),
        variant("C · Ribbons", "direction is the layout, not an arrowhead", ribbons(w=540), CW, CH, note),
        variant("D · One line per pair", "reads as a sentence; says 'never' out loud", pair_rows(w=540), CW, CH, note),
    ])


# ------------------------------------------------------------------ C07: report routing
CATS = [("Listener reports", ["Operations"], 12), ("Violations", ["Operations", "Finance"], 7),
        ("Flow failures", [], 4), ("Assistance", [], 3), ("Deviations", [], 2)]


def sankey(w=520, h=250):
    """Thickness is how many reports that category carried, so the diagram says what is loud as
    well as where it goes."""
    total = sum(n for _, _, n in CATS)
    lx, rx = 132, w - 130
    out, y = [], 12
    dest_y = {"Operations": 54, "Finance": 112}
    you_y = h - 46
    for cat, to, n in CATS:
        th = max(3, (n / total) * 90)
        out.append(f'<text x="0" y="{y + th / 2 + 4:.1f}" fill="{T["dim"]}" font-family="{T["sans"]}" font-size="12.5">{cat}</text>')
        out.append(f'<rect x="{lx - 12}" y="{y}" width="8" height="{th:.1f}" rx="4" fill="{T["line2"]}"/>')
        out.append(f'<path d="M{lx} {y + th / 2:.1f} C {lx + 90} {y + th / 2:.1f}, {rx - 90} {you_y}, {rx} {you_y}" '
                   f'fill="none" stroke="{T["line2"]}" stroke-width="{th:.1f}" opacity="0.35" stroke-linecap="round"/>')
        for d in to:
            out.append(f'<path d="M{lx} {y + th / 2:.1f} C {lx + 90} {y + th / 2:.1f}, {rx - 90} {dest_y[d]}, {rx} {dest_y[d]}" '
                       f'fill="none" stroke="{DEPT_COLOR[d]}" stroke-width="{th * 0.7:.1f}" opacity="0.8" stroke-linecap="round"/>')
        y += th + 26
    for d, dy in dest_y.items():
        out.append(f'<circle cx="{rx}" cy="{dy}" r="7" fill="{DEPT_COLOR[d]}"/>')
        out.append(f'<text x="{rx + 13}" y="{dy + 4}" fill="{T["ink"]}" font-family="{T["sans"]}" font-size="12.5">{d}</text>')
    out.append(f'<circle cx="{rx}" cy="{you_y}" r="8" fill="{T["ink"]}"/>')
    out.append(f'<text x="{rx + 13}" y="{you_y + 4}" fill="{T["ink"]}" font-family="{T["sans"]}" font-size="12.5">You, always</text>')
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(out)}</svg>'


def orbit(w=460, h=250):
    """You are the centre and cannot be routed away from; a category that is also routed puts a
    coloured arc on the ring around you."""
    cx, cy = w / 2 - 40, h / 2
    out = [f'<circle cx="{cx}" cy="{cy}" r="13" fill="{T["ink"]}"/>',
           f'<text x="{cx}" y="{cy + 34}" text-anchor="middle" fill="{T["dim"]}" font-family="{T["sans"]}" font-size="12">you</text>']
    for i, (cat, to, n) in enumerate(CATS):
        r = 34 + i * 17
        out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{T["line"]}" stroke-width="6" opacity="0.7"/>')
        for k, d in enumerate(to):
            c = 2 * _math.pi * r
            seg = c * 0.26
            off = -c * (0.06 + k * 0.30)
            out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{DEPT_COLOR[d]}" stroke-width="6" '
                       f'stroke-linecap="round" stroke-dasharray="{seg:.1f} {c:.1f}" stroke-dashoffset="{off:.1f}"/>')
        out.append(f'<text x="{w - 150}" y="{28 + i * 26}" fill="{T["dim"]}" font-family="{T["sans"]}" font-size="12">{cat}</text>')
        out.append(f'<circle cx="{w - 162}" cy="{24 + i * 26}" r="4" fill="{DEPT_COLOR[to[0]] if to else T["line2"]}"/>')
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(out)}</svg>'


def routing_rows(w=540):
    """No diagram at all: a line per category, the departments it also reaches as chips. The
    plainest thing that still says 'additive'."""
    cells = []
    for cat, to, n in CATS:
        chips = row(*[chip(d, "neutral", 11) for d in to], gap=6) if to else txt("you alone", 11.5, T["faint"])
        cells.append(row(txt(cat, 12.5, T["ink"], extra="width: 150px;"),
                         f'<span style="flex: 1;"></span>', chips,
                         txt(f"{n}", 11.5, T["faint"], mono=True, extra="width: 26px; text-align: right;"),
                         gap=10, extra="padding: 9px 0; width: 100%;"))
    return col(*cells, gap=0, extra=f"width: {w}px;")


def c07():
    note = txt("Additive: routing never takes your copy away.", 11.5, T["faint"])
    return mood("Report routing, four ways", "five categories; two of them also reach a department", [
        variant("A · Flow lines", "every category reaches you, some reach further",
                routing(w=540, h=210), CW, CH, note),
        variant("B · Sankey", "thickness is how loud the category is", sankey(w=540, h=250), CW, CH, note),
        variant("C · Orbit", "you are the centre and cannot be routed away", orbit(w=540, h=250), CW, CH, note),
        variant("D · Lines, no diagram", "the plainest thing that still says additive",
                routing_rows(), CW, CH, note),
    ])


# ------------------------------------------------------------------ C08: violations by tier
TIERS = [("/restricted/", 1), ("/admin/", 0), ("/workers/", 0), ("/common/", 0)]


def lollipop(w=520, row_h=30):
    out, y = [], 16
    m = max(n for _, n in TIERS) or 1
    for name, n in TIERS:
        x = 120 + (n / m) * 150
        out.append(f'<text x="0" y="{y + 4}" fill="{T["dim"]}" font-family="{T["mono"]}" font-size="12.5">{name}</text>')
        out.append(f'<line x1="120" y1="{y}" x2="{x:.1f}" y2="{y}" stroke="{T["line"]}" stroke-width="2"/>')
        out.append(f'<circle cx="{x:.1f}" cy="{y}" r="{7 if n else 5}" fill="{ST["failing"] if n else T["line2"]}"/>')
        out.append(f'<text x="{x + 14:.1f}" y="{y + 4}" fill="{T["faint"]}" font-family="{T["mono"]}" font-size="12">{n}</text>')
        y += row_h
    return f'<svg width="{w}" height="{y}" viewBox="0 0 {w} {y}">{"".join(out)}</svg>'


def tier_tiles(w=520):
    cells = []
    for name, n in TIERS:
        cells.append(col(txt(str(n), 30, ST["failing"] if n else T["faint"], 600, mono=True, extra="line-height: 1;"),
                         txt(name, 11.5, T["dim"], mono=True), gap=8,
                         extra=f"width: 118px; height: 96px; padding: 16px; border-radius: 14px; box-sizing: border-box; "
                               f"background: {T['pane']}; {'box-shadow: inset 0 0 0 1px ' + T['danger_soft'] + ';' if n else ''}"))
    return row(*cells, gap=12)


def tier_single(w=520, h=34):
    """One bar for the whole estate, the offending tier picked out of it. Says 'almost nothing is
    wrong' better than four bars of zero do."""
    total = 14
    bad = sum(n for _, n in TIERS)
    bw = max(10, (bad / total) * w)
    return (f'<svg width="{w}" height="{h + 30}" viewBox="0 0 {w} {h + 30}">'
            f'<rect x="0" y="0" width="{w}" height="{h}" rx="8" fill="{T["line"]}"/>'
            f'<rect x="0" y="0" width="{bw:.1f}" height="{h}" rx="8" fill="{ST["failing"]}"/>'
            f'<text x="0" y="{h + 20}" fill="{T["faint"]}" font-family="{T["sans"]}" font-size="11.5">'
            f'{bad} file out of place, in /restricted/, across 14 PCs</text></svg>')


def c08():
    note = txt("budget-2026.xlsx, found in /workers/ on OPS-07 at 10:41.", 11.5, T["faint"])
    return mood("Violations, four ways", "a tier is a policy, so a zero keeps its row", [
        variant("A · Bars", "the one on the boards now", tier_bars(w=540), CW, CH, note),
        variant("B · Lollipops", "the count is a position, not an area", lollipop(w=540), CW, CH, note),
        variant("C · Tiles", "each tier is an object you can act on", tier_tiles(), CW, CH, note),
        variant("D · One bar", "says 'almost nothing is wrong' in one shape",
                col(tier_single(w=500), txt("The tiers with nothing in them are not drawn; they are named in the card.",
                                            11.5, T["faint"]), gap=18), CW, CH, note),
    ])


# ------------------------------------------------------------------ C09: work, by department
WORK = {"Operations": ([5, 2, 1], [3, 1, 0]), "Finance": ([3, 0, 0], [2, 1, 0]), "Logistics": ([1, 1, 2], [0, 0, 0])}
WORK_TONES = ["confirmed", "behind", "failing"]


def work_rings(size=64):
    cells = []
    for name, (tasks, flows) in WORK.items():
        tt, ft = sum(tasks), sum(flows)
        cells.append(col(row(swatch(DEPT_COLOR[name], "dot"), txt(name, 12.5, T["ink"], 600), gap=7),
                         row(donut(tasks[0], max(1, tt), ST["confirmed"], size=size, stroke=8, label="Tasks"),
                             donut(flows[0], max(1, ft), ST["confirmed"], size=size, stroke=8, label="Flows"), gap=14),
                         gap=12, extra=f"width: 168px; padding: 14px; border-radius: 12px; background: {T['pane']}; box-sizing: border-box;"))
    return row(*cells, gap=14)


def bullet(w=520):
    """A bullet bar per measure: the fill is what is fine, the tick is the whole, and anything
    past the tick is what needs a person."""
    out, y = [], 14
    for name, (tasks, flows) in WORK.items():
        out.append(f'<text x="0" y="{y + 4}" fill="{T["ink"]}" font-family="{T["sans"]}" font-size="12.5" font-weight="600">{name}</text>')
        y += 16
        for label, parts in (("Tasks", tasks), ("Flows", flows)):
            total = max(1, sum(parts))
            plot = 250
            out.append(f'<text x="10" y="{y + 9}" fill="{T["dim"]}" font-family="{T["sans"]}" font-size="11.5">{label}</text>')
            out.append(f'<rect x="60" y="{y}" width="{plot}" height="12" rx="6" fill="{T["line"]}"/>')
            out.append(f'<rect x="60" y="{y}" width="{(parts[0] / total) * plot:.1f}" height="12" rx="6" fill="{ST["confirmed"]}"/>')
            bad = parts[1] + parts[2]
            if bad:
                out.append(f'<rect x="{60 + plot - (bad / total) * plot:.1f}" y="{y}" width="{(bad / total) * plot:.1f}" '
                           f'height="12" rx="6" fill="{ST["failing"] if parts[2] else ST["behind"]}"/>')
            out.append(f'<text x="{60 + plot + 12}" y="{y + 10}" fill="{T["faint"]}" font-family="{T["mono"]}" font-size="11.5">{sum(parts)}</text>')
            y += 19
        y += 12
    return f'<svg width="{w}" height="{y}" viewBox="0 0 {w} {y}">{"".join(out)}</svg>'


def work_columns(w=520, h=190):
    """Stacked columns, one pair per department, all to one scale: the departments become
    comparable instead of each being read on its own."""
    m = max(max(sum(t), sum(f)) for t, f in WORK.values()) or 1
    out, x = [], 46
    for name, (tasks, flows) in WORK.items():
        for k, parts in enumerate((tasks, flows)):
            y = h - 34
            for i, v in enumerate(parts):
                if not v:
                    continue
                bh = (v / m) * (h - 60)
                y -= bh
                out.append(f'<rect x="{x + k * 30}" y="{y:.1f}" width="22" height="{bh:.1f}" rx="4" fill="{ST[WORK_TONES[i]]}"/>')
            out.append(f'<text x="{x + k * 30 + 11}" y="{h - 20}" text-anchor="middle" fill="{T["faint"]}" '
                       f'font-family="{T["sans"]}" font-size="10.5">{"T" if k == 0 else "F"}</text>')
        out.append(f'<text x="{x + 26}" y="{h - 4}" text-anchor="middle" fill="{T["dim"]}" font-family="{T["sans"]}" font-size="12">{name}</text>')
        x += 152
    out.append(f'<line x1="0" y1="{h - 34}" x2="{w}" y2="{h - 34}" stroke="{T["line"]}" stroke-width="1"/>')
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(out)}</svg>'


def c09():
    lg = legend([("On track", ST["confirmed"]), ("Needs attention", ST["behind"]), ("Overdue", ST["failing"])])
    return mood("Work by department, four ways", "tasks and flows, the same two measures each time", [
        variant("A · Two bars in a card", "the one on the boards now",
                row(*[health_card(n, DEPT_COLOR[n], list(zip(WORK_TONES, t)), list(zip(WORK_TONES, f)), w=168)
                      for n, (t, f) in WORK.items()], gap=14), CW, CH, lg),
        variant("B · Rings", "share, not amount", work_rings(), CW, CH, lg),
        variant("C · Bullets", "what is fine fills from the left, what is not sits at the end",
                bullet(w=540), CW, CH, lg),
        variant("D · Columns, one scale", "departments become comparable", work_columns(w=540), CW, CH, lg),
    ])


# ------------------------------------------------------------------ C10: the figures
FIGS = [("14", "client PCs", "across 3 departments", None, [0, 4, 8, 11, 14]),
        ("12", "on 1.4.2", "2 still behind", "warn", [0, 3, 6, 10, 12]),
        ("2", "waiting on you", "approval, and an empty department", "danger", [0, 1, 1, 2, 2]),
        ("4", "traversals today", "1 still open", None, [1, 2, 2, 3, 4])]


def micro_bar(frac, colour, w=96, h=5):
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<rect x="0" y="0" width="{w}" height="{h}" rx="{h / 2}" fill="{T["line"]}"/>'
            f'<rect x="0" y="0" width="{max(4, w * frac):.1f}" height="{h}" rx="{h / 2}" fill="{colour}"/></svg>')


def spark(points, colour, w=96, h=26):
    m = max(points) or 1
    step_x = w / max(1, len(points) - 1)
    pts = " ".join(f"{i * step_x:.1f},{h - 3 - (v / m) * (h - 8):.1f}" for i, v in enumerate(points))
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<polyline points="{pts}" fill="none" stroke="{colour}" stroke-width="2" stroke-linejoin="round" stroke-linecap="round"/></svg>')


def figures(kind):
    cells = []
    for value, label, sub, tone, series in FIGS:
        colour = tone_c(tone, T["ok"]) if tone else T["line2"]
        big = txt(value, 38, tone_c(tone, T["ink"]), 600, mono=True, extra="line-height: 1;")
        if kind == "plain":
            body = col(big, txt(label, 12.5, T["dim"], 500), txt(sub, 11.5, T["faint"]), gap=6)
        elif kind == "bar":
            body = col(big, txt(label, 12.5, T["dim"], 500), micro_bar(int(value) / 14, colour), gap=8)
        elif kind == "spark":
            body = col(row(big, spark(series, colour), gap=12, align="flex-end"),
                       txt(label, 12.5, T["dim"], 500), txt(sub, 11.5, T["faint"]), gap=6)
        else:
            body = col(row(donut(int(value), 14, colour, size=56, stroke=7),
                           col(txt(label, 12.5, T["ink"], 600), txt(sub, 11.5, T["faint"]), gap=4), gap=12),
                       gap=0)
        pad = "16px 18px" if kind == "tile" else "0"
        bg = T["pane"] if kind == "tile" else "transparent"
        cells.append(col(body, gap=0, extra=f"width: 148px; padding: {pad}; border-radius: 14px; background: {bg}; box-sizing: border-box;"))
    return row(*cells, gap=18, align="flex-start")


def c10():
    return mood("The figures, four ways", "the four numbers the Super User opens on", [
        variant("A · Numbers alone", "nothing competes with the figure", figures("plain"), CW, CH),
        variant("B · Number and share", "a rule under it says how big the whole is", figures("bar"), CW, CH),
        variant("C · Number and trend", "the figure plus where it came from", figures("spark"), CW, CH),
        variant("D · Tiles", "each figure an object, tinted only when it is not fine", figures("tile"), CW, CH),
    ])


CHART_MOOD_2 = [("C06-Assistance.dc.html", "Assistance, four ways", c06),
                ("C07-Routing.dc.html", "Report routing, four ways", c07),
                ("C08-Violations.dc.html", "Violations, four ways", c08),
                ("C09-Work.dc.html", "Work by department, four ways", c09),
                ("C10-Figures.dc.html", "The figures, four ways", c10)]
