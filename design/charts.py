# ================================================================== Chart mood boards, C01-C05
# One chart type per board, four treatments of it. The point is not to be exhaustive but to put
# genuinely different approaches side by side at the same size, so one can be picked the way the
# component mood boards (M01-M15) were picked.
#
# Every treatment keeps the settled language: identity is the categorical ramp, state is the four
# reserved colours and always carries a word, nothing is a table, and each chart sits in a panel.

ROLLOUT = [("Operations", 6, 1, 0), ("Finance", 4, 0, 0), ("Logistics", 2, 0, 1)]
TONE_ORDER = [("confirmed", "Confirmed"), ("behind", "Behind"), ("failing", "Failing")]


def variant(caption, note, body, w, h=None, foot=""):
    """One treatment, in the panel language, captioned so it can be named when it is picked."""
    head = row(txt(caption, 12.5, T["ink"], 600), txt(note, 11.5, T["faint"]), gap=9, extra="flex: none;")
    middle = (f'<div style="flex: 1; min-height: 0; display: flex; align-items: center; '
              f'justify-content: flex-start; overflow: hidden;">{body}</div>')
    parts = [head, middle] + ([foot] if foot else [])
    size = f"height: {h}px; " if h else ""
    return col(*parts, gap=12,
               extra=f"width: {w}px; {size}padding: 16px 18px; border-radius: 16px; "
                     f"background: {CHART_BG}; box-sizing: border-box; flex: none;")


def eyebrow(kind, phrase, where):
    """The line that stops a board being a mystery: what it is, what it is for, which page."""
    tag = (f'<span style="display: inline-flex; align-items: center; height: 20px; padding: 0 9px; '
           f'border-radius: 6px; background: rgba(255,255,255,0.14); color: #fff; font-family: {T["mono"]}; '
           f'font-size: 11px; font-weight: 500; flex: none;">{kind}</span>')
    return row(tag, txt(phrase, 12, T["frame_dim"]),
               txt("·", 12, T["frame_faint"]), txt(where, 12, T["frame_dim"]), gap=8, extra="flex: none;")


def mood(title, sub, cells, gap=16, brow=""):
    inner = col(brow if brow else "",
                row(f'<span style="width: 10px; height: 26px; border-radius: 3px; background: #fff;"></span>',
                    txt(title, 22, "#fff", 700), txt(sub, 13, T["frame_dim"]), gap=12, extra="flex: none;"),
                row(*cells, gap=gap, align="flex-start", extra="flex-wrap: wrap;"),
                gap=12, extra=f"width: {W}px; height: {H}px; box-sizing: border-box; padding: 22px 40px; "
                              f"background: {FRAME['native']}; overflow: hidden;")
    return page(title, "", "", inner, "", "native")


CW, CH = 672, 372          # a 2 x 2 grid of treatments


# ------------------------------------------------------------------ C01: the rollout
def grouped_bars(rows_, w=560, bar=9, gap=3, group_gap=22):
    """Three thin bars per department instead of one stacked one: each state is read on its own
    baseline, at the cost of the total no longer being a single length."""
    label_w = 92
    m = max(max(r[1:]) for r in rows_) or 1
    plot = w - label_w - 40
    out, y = [], 2
    for name, *vals in rows_:
        out.append(f'<text x="0" y="{y + bar + 6}" fill="{T["dim"]}" font-family="{T["sans"]}" font-size="12.5">{name}</text>')
        for i, v in enumerate(vals):
            bw = max(3, (v / m) * plot) if v else 3
            tone = TONE_ORDER[i][0]
            out.append(f'<rect x="{label_w}" y="{y + i * (bar + gap)}" width="{bw:.1f}" height="{bar}" rx="{bar / 2}" '
                       f'fill="{ST[tone]}" opacity="{1 if v else 0.25}"/>')
            out.append(f'<text x="{label_w + bw + 7:.1f}" y="{y + i * (bar + gap) + bar - 1}" fill="{T["faint"]}" '
                       f'font-family="{T["mono"]}" font-size="10.5">{v}</text>')
        y += 3 * (bar + gap) + group_gap
    return f'<svg width="{w}" height="{y}" viewBox="0 0 {w} {y}">{"".join(out)}</svg>'


def dot_plot(rows_, w=560, row_h=34):
    """A rule per department from nothing to its fleet size, with a mark where confirmation
    reached. Position carries the number; the rule carries the target."""
    label_w, pad = 92, 44
    m = max(sum(r[1:]) for r in rows_) or 1
    plot = w - label_w - pad
    out, y = [], 14
    for name, ok_, behind, failing in rows_:
        total = ok_ + behind + failing
        x_end = label_w + (total / m) * plot
        x_ok = label_w + (ok_ / m) * plot
        out.append(f'<text x="0" y="{y + 4}" fill="{T["dim"]}" font-family="{T["sans"]}" font-size="12.5">{name}</text>')
        out.append(f'<line x1="{label_w}" y1="{y}" x2="{x_end:.1f}" y2="{y}" stroke="{T["line2"]}" stroke-width="2" stroke-linecap="round" opacity="0.5"/>')
        out.append(f'<line x1="{label_w}" y1="{y}" x2="{x_ok:.1f}" y2="{y}" stroke="{ST["confirmed"]}" stroke-width="2" stroke-linecap="round"/>')
        out.append(f'<circle cx="{x_ok:.1f}" cy="{y}" r="6" fill="{ST["confirmed"]}"/>')
        if failing:
            out.append(f'<circle cx="{x_end:.1f}" cy="{y}" r="5" fill="none" stroke="{ST["failing"]}" stroke-width="2"/>')
        elif behind:
            out.append(f'<circle cx="{x_end:.1f}" cy="{y}" r="5" fill="none" stroke="{ST["behind"]}" stroke-width="2"/>')
        out.append(f'<text x="{x_end + 12:.1f}" y="{y + 4}" fill="{T["faint"]}" font-family="{T["mono"]}" font-size="12">{ok_}/{total}</text>')
        y += row_h
    return f'<svg width="{w}" height="{y}" viewBox="0 0 {w} {y}">{"".join(out)}</svg>'


def donut(value, total, colour, size=88, stroke=9, label=""):
    r = (size - stroke) / 2
    c = 2 * 3.14159 * r
    frac = (value / total) if total else 0
    return (f'<svg width="{size}" height="{size + 22}" viewBox="0 0 {size} {size + 22}">'
            f'<circle cx="{size / 2}" cy="{size / 2}" r="{r}" fill="none" stroke="{T["line"]}" stroke-width="{stroke}"/>'
            f'<circle cx="{size / 2}" cy="{size / 2}" r="{r}" fill="none" stroke="{colour}" stroke-width="{stroke}" '
            f'stroke-linecap="round" stroke-dasharray="{c * frac:.1f} {c:.1f}" transform="rotate(-90 {size / 2} {size / 2})"/>'
            f'<text x="{size / 2}" y="{size / 2 + 6}" text-anchor="middle" fill="{T["ink"]}" font-family="{T["mono"]}" '
            f'font-size="17" font-weight="500">{value}</text>'
            f'<text x="{size / 2}" y="{size + 16}" text-anchor="middle" fill="{T["dim"]}" font-family="{T["sans"]}" '
            f'font-size="12">{label}</text></svg>')


def donuts_row(rows_):
    return row(*[donut(ok_, ok_ + b + f, ST["failing"] if f else ST["behind"] if b else ST["confirmed"], label=name)
                 for name, ok_, b, f in rows_], gap=30)


def one_bar(rows_, w=560):
    """The whole fleet as a single bar, departments segmented inside it and named underneath. The
    rollout as one object rather than three comparable ones."""
    total = sum(sum(r[1:]) for r in rows_) or 1
    h, y = 30, 6
    x, segs, labels = 0, [], []
    for i, (name, ok_, b, f) in enumerate(rows_):
        n = ok_ + b + f
        sw = (n / total) * w - (2 if i < len(rows_) - 1 else 0)
        # inside the department's share, how much has confirmed
        segs.append(f'<rect x="{x:.1f}" y="{y}" width="{sw:.1f}" height="{h}" rx="6" fill="{T["line"]}"/>')
        segs.append(f'<rect x="{x:.1f}" y="{y}" width="{max(4, (ok_ / n) * sw):.1f}" height="{h}" rx="6" fill="{DEPT_COLOR[name]}"/>')
        labels.append(f'<text x="{x:.1f}" y="{y + h + 18}" fill="{T["dim"]}" font-family="{T["sans"]}" font-size="12">{name}</text>')
        labels.append(f'<text x="{x:.1f}" y="{y + h + 34}" fill="{T["faint"]}" font-family="{T["mono"]}" font-size="11.5">{ok_} of {n}</text>')
        x += sw + 2
    return f'<svg width="{w}" height="{y + h + 42}" viewBox="0 0 {w} {y + h + 42}">{"".join(segs + labels)}</svg>'


def c01():
    lg = legend([(l, ST[t]) for t, l in TONE_ORDER])
    return mood("Rollout, four ways", "one version across three departments — 12 of 14 confirmed",
                brow=eyebrow("CHART", "fills the Rollout slot", "page 1, At a glance"), cells=[
        variant("A · Stacked, one scale", "totals comparable at a glance",
             stacked_bars([(n, [("confirmed", a), ("behind", b), ("failing", f)]) for n, a, b, f in ROLLOUT], w=580),
             CW, CH, lg),
        variant("B · Grouped, own baselines", "each state read on its own",
             grouped_bars(ROLLOUT, w=580), CW, CH, lg),
        variant("C · Progress to target", "the rule is the fleet, the mark is where it got to",
             dot_plot(ROLLOUT, w=580), CW, CH,
             legend([("Confirmed", ST["confirmed"]), ("Not yet", T["line2"])], "the hollow ring is the state it stalled in")),
        variant("D · One bar, departments inside", "the rollout as a single object",
             col(one_bar(ROLLOUT, w=580), donuts_row(ROLLOUT), gap=26), CW, CH,
             legend([(d, c) for d, c in DEPT_COLOR.items()], "colour is the department; fill is what confirmed")),
    ])


# ------------------------------------------------------------------ C02: the fleet
FLEET = ([("confirmed", "OPS")] * 6 + [("behind", "OPS-06 retrying")] + [("confirmed", "FIN")] * 4
         + [("confirmed", "LOG")] * 2 + [("failing", "LOG-02, 6 failures")])
FLEET_GROUPS = [("Operations", [("confirmed", "")] * 6 + [("behind", "OPS-06")]),
                ("Finance", [("confirmed", "")] * 4),
                ("Logistics", [("confirmed", "")] * 2 + [("failing", "LOG-02")])]


def dot_fleet(cells, cols=14, size=14, gap=9):
    out = []
    for i, (state, label) in enumerate(cells):
        cx, cy = (i % cols) * (size + gap) + size / 2, (i // cols) * (size + gap) + size / 2
        out.append(f'<circle cx="{cx}" cy="{cy}" r="{size / 2}" fill="{ST[state]}"><title>{label}</title></circle>')
    rows_n = (len(cells) + cols - 1) // cols
    w, h = cols * (size + gap) - gap, rows_n * (size + gap) - gap
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(out)}</svg>'


def grouped_waffle(groups, size=26, gap=7, per_row=7):
    """The fleet split by department, each group under its own name and colour rule. The counts
    stay comparable because every square is the same size."""
    cols = []
    for name, cells in groups:
        out = []
        for i, (state, label) in enumerate(cells):
            cx, cy = (i % per_row) * (size + gap), (i // per_row) * (size + gap)
            out.append(f'<rect x="{cx}" y="{cy}" width="{size}" height="{size}" rx="7" fill="{ST[state]}"><title>{label}</title></rect>')
        rows_n = (len(cells) + per_row - 1) // per_row
        w, h = min(per_row, len(cells)) * (size + gap) - gap, rows_n * (size + gap) - gap
        rule = f'<span style="display: block; width: 26px; height: 3px; border-radius: 2px; background: {DEPT_COLOR[name]};"></span>'
        cols.append(col(rule, txt(name, 12, T["dim"]),
                        f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(out)}</svg>',
                        gap=8, extra="flex: none;"))
    return row(*cols, gap=30, align="flex-start")


def strip_fleet(groups, w=560, h=22, gap_y=12):
    """One strip per department: length is its size, and the parts of it that are not confirmed
    are picked out. Reads as a fleet rather than as counted objects."""
    total = max(len(c) for _, c in groups) or 1
    unit = (w - 100) / total
    out, y = [], 4
    for name, cells in groups:
        out.append(f'<text x="0" y="{y + h - 6}" fill="{T["dim"]}" font-family="{T["sans"]}" font-size="12.5">{name}</text>')
        for i, (state, label) in enumerate(cells):
            out.append(f'<rect x="{100 + i * unit:.1f}" y="{y}" width="{unit - 3:.1f}" height="{h}" rx="5" '
                       f'fill="{ST[state]}"><title>{label}</title></rect>')
        y += h + gap_y
    return f'<svg width="{w}" height="{y}" viewBox="0 0 {w} {y}">{"".join(out)}</svg>'



def c02():
    lg = legend([(l, ST[t]) for t, l in TONE_ORDER])
    return mood("The fleet, four ways", "one mark per client PC — 14 of them",
                brow=eyebrow("CHART", "fills the The fleet slot", "page 1, At a glance"), cells=[
        variant("A · Squares", "countable, neutral", waffle(FLEET, cols=7, size=30, gap=8, w=260), CW, CH, lg),
        variant("B · Dots", "lighter; the fleet reads as a population", dot_fleet(FLEET), CW, CH, lg),
        variant("C · Grouped by department", "the split is structural, not a filter",
             grouped_waffle(FLEET_GROUPS), CW, CH, lg),
        variant("D · A strip per department", "length is the department's size; no counting needed",
                strip_fleet(FLEET_GROUPS, w=560, h=30, gap_y=16), CW, CH, lg),
    ])


# ------------------------------------------------------------------ C03: confirmations over time
SERIES = [0, 3, 6, 8, 10, 11, 12]
DAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Today"]
PER_DEPT = {"Operations": [0, 2, 3, 4, 5, 6, 6], "Finance": [0, 1, 2, 3, 4, 4, 4], "Logistics": [0, 0, 1, 1, 1, 1, 2]}


def _pts(points, w, h, pad_l=8, pad_r=34, pad_b=20, pad_t=18):
    lo, hi = min(points), max(points)
    span = max(1, hi - lo)
    step = (w - pad_l - pad_r) / max(1, len(points) - 1)
    return [(pad_l + i * step, h - pad_b - ((v - lo) / span) * (h - pad_b - pad_t)) for i, v in enumerate(points)]


def area(points, w=560, h=150, colour=None):
    colour = colour or ST["confirmed"]
    pts = _pts(points, w, h)
    poly = " ".join(f"{x:.1f},{y:.1f}" for x, y in pts)
    fill = f"{poly} {pts[-1][0]:.1f},{h - 20} {pts[0][0]:.1f},{h - 20}"
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<defs><linearGradient id="ag" x1="0" y1="0" x2="0" y2="1">'
            f'<stop offset="0%" stop-color="{colour}" stop-opacity="0.35"/>'
            f'<stop offset="100%" stop-color="{colour}" stop-opacity="0.02"/></linearGradient></defs>'
            f'<polygon points="{fill}" fill="url(#ag)"/>'
            f'<polyline points="{poly}" fill="none" stroke="{colour}" stroke-width="2" stroke-linejoin="round"/>'
            f'<line x1="0" y1="{h - 20}" x2="{w}" y2="{h - 20}" stroke="{T["line"]}" stroke-width="1"/>'
            f'<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="4.5" fill="{colour}" stroke="{CHART_BG}" stroke-width="2"/>'
            f'<text x="{pts[-1][0] + 10:.1f}" y="{pts[-1][1] + 4:.1f}" fill="{T["ink"]}" font-family="{T["mono"]}" '
            f'font-size="12">{points[-1]}</text></svg>')


def step(points, w=560, h=150, colour=None):
    """A confirmation is a discrete event, and a step says so: the line holds until the next one."""
    colour = colour or ST["confirmed"]
    pts = _pts(points, w, h)
    d = [f"M{pts[0][0]:.1f} {pts[0][1]:.1f}"]
    for i in range(1, len(pts)):
        d.append(f"H{pts[i][0]:.1f}")
        d.append(f"V{pts[i][1]:.1f}")
    marks = "".join(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="3" fill="{colour}" opacity="0.6"/>' for x, y in pts[:-1])
    return (f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">'
            f'<line x1="0" y1="{h - 20}" x2="{w}" y2="{h - 20}" stroke="{T["line"]}" stroke-width="1"/>'
            f'<path d="{" ".join(d)}" fill="none" stroke="{colour}" stroke-width="2" stroke-linejoin="round"/>'
            f'{marks}<circle cx="{pts[-1][0]:.1f}" cy="{pts[-1][1]:.1f}" r="4.5" fill="{colour}" stroke="{CHART_BG}" stroke-width="2"/>'
            f'<text x="{pts[-1][0] + 10:.1f}" y="{pts[-1][1] + 4:.1f}" fill="{T["ink"]}" font-family="{T["mono"]}" '
            f'font-size="12">{points[-1]}</text></svg>')


def spark_rows(series_map, w=560, h=34):
    """One sparkline per department, same scale, stacked: the shape of each rollout, separately."""
    out = []
    m = max(max(v) for v in series_map.values()) or 1
    for i, (name, vals) in enumerate(series_map.items()):
        step_x = (w - 200) / max(1, len(vals) - 1)
        pts = " ".join(f"{110 + k * step_x:.1f},{i * (h + 8) + h - 6 - (v / m) * (h - 12):.1f}" for k, v in enumerate(vals))
        out.append(f'<text x="0" y="{i * (h + 8) + h - 10}" fill="{T["dim"]}" font-family="{T["sans"]}" font-size="12.5">{name}</text>')
        out.append(f'<polyline points="{pts}" fill="none" stroke="{DEPT_COLOR[name]}" stroke-width="2" stroke-linejoin="round"/>')
        out.append(f'<text x="{w - 70}" y="{i * (h + 8) + h - 10}" fill="{T["faint"]}" font-family="{T["mono"]}" font-size="12">{vals[-1]} of {max(vals)}</text>')
    total_h = len(series_map) * (h + 8)
    return f'<svg width="{w}" height="{total_h}" viewBox="0 0 {w} {total_h}">{"".join(out)}</svg>'



def days_row(w=560):
    return row(*[txt(d, 11.5, T["faint"], extra=f"width: {w // 7}px; text-align: center;") for d in DAYS], gap=0)


def c03():
    return mood("Confirmations, four ways", "PCs confirmed on 1.4.2 since the rollout was approved",
                brow=eyebrow("CHART", "fills the Confirmations slot", "page 1, At a glance"), cells=[
        variant("A · Line", "one series, the last point labelled",
             col(trend(SERIES, w=560, h=150), days_row(), gap=4), CW, CH),
        variant("B · Area", "the same line, with weight under it",
             col(area(SERIES), days_row(), gap=4), CW, CH),
        variant("C · Step", "a confirmation is an event, not a slope",
             col(step(SERIES), days_row(), gap=4), CW, CH),
        variant("D · One line each", "the shape of each department's rollout, and where it got to",
                spark_rows(PER_DEPT, h=48), CW, CH,
                legend([(d, c) for d, c in DEPT_COLOR.items()])),
    ])


# ------------------------------------------------------------------ C04: the hierarchy
TREE = [("Operations", 2, 7), ("Finance", 1, 4), ("Logistics", 0, 3)]


def indented_tree(w=560):
    """The plainest possible reading: you, then departments, then their PCs as a count bar. No
    curves to follow, and it survives twenty departments."""
    out, y = [], 16
    out.append(f'<circle cx="10" cy="{y - 4}" r="7" fill="{T["ink"]}"/>')
    out.append(f'<text x="26" y="{y}" fill="{T["ink"]}" font-family="{T["sans"]}" font-size="13" font-weight="600">Everything</text>')
    y += 16
    for name, admins, pcs in TREE:
        top = y
        y += 22
        c = DEPT_COLOR[name]
        out.append(f'<path d="M10 {top} V{y - 4} H30" fill="none" stroke="{T["line2"]}" stroke-width="1.5"/>')
        out.append(f'<circle cx="38" cy="{y - 4}" r="6" fill="{c}"/>')
        out.append(f'<text x="52" y="{y}" fill="{T["ink"]}" font-family="{T["sans"]}" font-size="12.5">{name}</text>')
        out.append(f'<text x="160" y="{y}" fill="{T["danger"] if admins == 0 else T["faint"]}" font-family="{T["sans"]}" '
                   f'font-size="11.5">{"no Admin" if admins == 0 else str(admins) + " Admin" + ("s" if admins > 1 else "")}</text>')
        for k in range(pcs):
            out.append(f'<rect x="{250 + k * 16}" y="{y - 12}" width="11" height="11" rx="3" fill="{c}" opacity="0.8"/>')
        out.append(f'<text x="{250 + pcs * 16 + 8}" y="{y}" fill="{T["faint"]}" font-family="{T["mono"]}" font-size="11.5">{pcs} PCs</text>')
        y += 8
    return f'<svg width="{w}" height="{y + 6}" viewBox="0 0 {w} {y + 6}">{"".join(out)}</svg>'


def radial(w=420, h=300):
    """You at the centre, departments on a ring, their PCs outside it. Says 'everything reports to
    one place' more directly than a left-to-right tree does."""
    import math

    cx, cy = w / 2, h / 2
    out = []
    for i, (name, admins, pcs) in enumerate(TREE):
        ang = math.radians(-90 + i * (360 / len(TREE)))
        dx, dy = cx + math.cos(ang) * 78, cy + math.sin(ang) * 78
        c = DEPT_COLOR[name]
        out.append(f'<line x1="{cx}" y1="{cy}" x2="{dx:.1f}" y2="{dy:.1f}" stroke="{c}" stroke-width="1.5" opacity="0.55"/>')
        for k in range(pcs):
            spread = math.radians(-26 + (52 / max(1, pcs - 1)) * k) if pcs > 1 else 0
            px = cx + math.cos(ang + spread) * 124
            py = cy + math.sin(ang + spread) * 124
            out.append(f'<line x1="{dx:.1f}" y1="{dy:.1f}" x2="{px:.1f}" y2="{py:.1f}" stroke="{c}" stroke-width="1" opacity="0.25"/>')
            out.append(f'<circle cx="{px:.1f}" cy="{py:.1f}" r="4.5" fill="{c}" opacity="0.85"/>')
        out.append(f'<circle cx="{dx:.1f}" cy="{dy:.1f}" r="8" fill="{c}"/>')
        anchor = "middle"
        out.append(f'<text x="{dx:.1f}" y="{dy - 14:.1f}" text-anchor="{anchor}" fill="{T["ink"]}" '
                   f'font-family="{T["sans"]}" font-size="12">{name}</text>')
    out.append(f'<circle cx="{cx}" cy="{cy}" r="11" fill="{T["ink"]}"/>')
    out.append(f'<text x="{cx}" y="{cy + 28}" text-anchor="middle" fill="{T["dim"]}" font-family="{T["sans"]}" font-size="12">you</text>')
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(out)}</svg>'


def columns(w=560, h=260):
    """Three columns and straight links: level is a column, so depth is read left to right and
    nothing has to be traced around a curve."""
    out = []
    xs = [40, 230, 430]
    out.append(f'<text x="{xs[0]}" y="14" fill="{T["faint"]}" font-family="{T["sans"]}" font-size="11.5">You</text>')
    out.append(f'<text x="{xs[1]}" y="14" fill="{T["faint"]}" font-family="{T["sans"]}" font-size="11.5">Departments</text>')
    out.append(f'<text x="{xs[2]}" y="14" fill="{T["faint"]}" font-family="{T["sans"]}" font-size="11.5">Client PCs</text>')
    for i, (name, admins, pcs) in enumerate(TREE):
        dy = 56 + i * 64
        c = DEPT_COLOR[name]
        out.append(f'<line x1="{xs[0] + 12}" y1="{h / 2 + 6}" x2="{xs[1] - 6}" y2="{dy}" stroke="{c}" stroke-width="1.5" opacity="0.5"/>')
        out.append(f'<rect x="{xs[1] - 6}" y="{dy - 11}" width="{130}" height="22" rx="11" fill="{c}" opacity="0.18"/>')
        out.append(f'<circle cx="{xs[1] + 6}" cy="{dy}" r="5" fill="{c}"/>')
        out.append(f'<text x="{xs[1] + 18}" y="{dy + 4}" fill="{T["ink"]}" font-family="{T["sans"]}" font-size="12">{name}</text>')
        for k in range(pcs):
            px, py = xs[2] + (k % 4) * 22, dy - 10 + (k // 4) * 20
            out.append(f'<line x1="{xs[1] + 128}" y1="{dy}" x2="{px - 5}" y2="{py}" stroke="{c}" stroke-width="1" opacity="0.22"/>')
            out.append(f'<circle cx="{px}" cy="{py}" r="4.5" fill="{c}" opacity="0.85"/>')
    out.append(f'<circle cx="{xs[0] + 12}" cy="{h / 2 + 6}" r="9" fill="{T["ink"]}"/>')
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(out)}</svg>'


def c04():
    lg = legend([(d, c) for d, c in DEPT_COLOR.items()], "colour is the department, everywhere")
    return mood("The hierarchy, four ways", "three departments, three Admins, fourteen client PCs",
                brow=eyebrow("CHART", "fills the The hierarchy slot", "page 2, The hierarchy"), cells=[
        variant("A · Curves", "organic; the one on the boards now", org_map(w=560, h=250), CW, CH, lg),
        variant("B · Indented", "plainest; survives twenty departments", indented_tree(), CW, CH, lg),
        variant("C · Radial", "everything reports to one place", radial(w=560, h=270), CW, CH, lg),
        variant("D · Columns", "a level is a column; depth reads left to right", columns(), CW, CH, lg),
    ])


# ------------------------------------------------------------------ C05: sessions today
LANES = [("Kojo", [("native", 8.2, 12.0), ("native", 13.0, 17.4)]),
         ("Efua", []),
         ("Yaw", [("native", 9.0, 12.5), ("traversed", 12.5, 13.2), ("native", 13.2, 17.0)]),
         ("Adjoa", [("native", 8.0, 10.3), ("traversed", 10.3, 11.0), ("native", 11.0, 16.0)]),
         ("Nana", [("native", 8.5, 17.5)]),
         ("Kwame", []),
         ("Ama", [("native", 8.2, 10.7), ("su", 10.7, 11.1), ("native", 11.1, 17.6)])]
KIND = {"native": T["line2"], "traversed": T["warn"], "su": T["danger"], "assisted": T["accent"]}
T0, T1 = 8.0, 18.0


def heat_grid(w=560, cell_w=None, cell_h=20, gap=3):
    """One cell per PC per hour, shaded by who held it. Ten hours, so the whole day is one block
    the eye can scan down a column as well as along a row."""
    hours = int(T1 - T0)
    label_w = 62
    cell_w = cell_w or (w - label_w - 8) / hours - gap
    out = []
    for h in range(hours):
        out.append(f'<text x="{label_w + h * (cell_w + gap) + cell_w / 2:.1f}" y="10" text-anchor="middle" '
                   f'fill="{T["faint"]}" font-family="{T["mono"]}" font-size="10">{T0 + h:02.0f}</text>')
    for i, (name, blocks) in enumerate(LANES):
        y = 18 + i * (cell_h + gap)
        out.append(f'<text x="0" y="{y + cell_h - 5}" fill="{T["dim"]}" font-family="{T["sans"]}" font-size="12.5">{name}</text>')
        for h in range(hours):
            lo, hi = T0 + h, T0 + h + 1
            state = None
            for st, a, b in blocks:
                if a < hi and b > lo:
                    state = st if state in (None, "native") else state
            fill = KIND[state] if state else T["pane"]
            out.append(f'<rect x="{label_w + h * (cell_w + gap):.1f}" y="{y}" width="{cell_w:.1f}" height="{cell_h}" '
                       f'rx="5" fill="{fill}" opacity="{1 if state else 0.45}"/>')
    total_h = 18 + len(LANES) * (cell_h + gap)
    return f'<svg width="{w}" height="{total_h}" viewBox="0 0 {w} {total_h}">{"".join(out)}</svg>'



def coverage(w=560, row_h=26, bar=15):
    """One bar per PC: how many of the day's hours it was in use, segmented by who held them. The
    question it answers -- 'is this machine being used, and by whom' -- needs no geometry explained."""
    span = T1 - T0
    label_w = 62
    plot = w - label_w - 56
    out, y = [], 6
    for name, blocks in LANES:
        held = sum(b - a for _, a, b in blocks)
        x = label_w
        out.append(f'<text x="0" y="{y + bar - 3}" fill="{T["dim"]}" font-family="{T["sans"]}" font-size="12.5">{name}</text>')
        out.append(f'<rect x="{label_w}" y="{y}" width="{plot}" height="{bar}" rx="{bar / 2}" fill="{T["pane"]}" opacity="0.6"/>')
        for st, a, b in blocks:
            bw = ((b - a) / span) * plot
            out.append(f'<rect x="{x:.1f}" y="{y}" width="{max(3, bw - 1):.1f}" height="{bar}" rx="{bar / 2}" fill="{KIND[st]}"/>')
            x += bw
        label = f"{held:.1f}h" if held else "not used"
        out.append(f'<text x="{label_w + plot + 10}" y="{y + bar - 3}" fill="{T["faint"]}" '
                   f'font-family="{T["mono"] if held else T["sans"]}" font-size="11.5">{label}</text>')
        y += row_h
    return f'<svg width="{w}" height="{y}" viewBox="0 0 {w} {y}">{"".join(out)}</svg>'


def event_marks(w=560, row_h=22):
    """Only what changed: a mark where someone entered and where they left. Quiet PCs are an
    empty line, which is the point."""
    label_w = 62
    plot = w - label_w - 16
    out = []
    for i, (name, blocks) in enumerate(LANES):
        y = 12 + i * row_h
        out.append(f'<text x="0" y="{y + 4}" fill="{T["dim"]}" font-family="{T["sans"]}" font-size="12.5">{name}</text>')
        out.append(f'<line x1="{label_w}" y1="{y}" x2="{label_w + plot}" y2="{y}" stroke="{T["line"]}" stroke-width="1"/>')
        for st, a, b in blocks:
            if st == "native":
                continue
            xa = label_w + plot * (a - T0) / (T1 - T0)
            xb = label_w + plot * (b - T0) / (T1 - T0)
            out.append(f'<line x1="{xa:.1f}" y1="{y}" x2="{xb:.1f}" y2="{y}" stroke="{KIND[st]}" stroke-width="3" stroke-linecap="round"/>')
            out.append(f'<circle cx="{xa:.1f}" cy="{y}" r="4" fill="{KIND[st]}"/>')
        if not blocks:
            out.append(f'<text x="{label_w + 8}" y="{y + 4}" fill="{T["faint"]}" font-family="{T["sans"]}" font-size="11">never signed in</text>')
    total_h = 12 + len(LANES) * row_h
    return f'<svg width="{w}" height="{total_h}" viewBox="0 0 {w} {total_h}">{"".join(out)}</svg>'


def c05():
    lg = legend([("At the PC", KIND["native"]), ("An Admin entered", KIND["traversed"]), ("You entered", KIND["su"])])
    return mood("Sessions today, four ways", "seven client PCs, 08:00 to 18:00",
                brow=eyebrow("CHART", "fills the Sessions today slot", "page 3, The record — and page 2 when descended"),
                cells=[
        variant("A · Lanes", "duration is length; the one on the boards now",
             day_timeline(w=560, h=230), CW, CH, lg),
        variant("B · Hour grid", "scan a column as well as a row", heat_grid(), CW, CH, lg),
        variant("C · Coverage", "how much of the day each PC was in use, and by whom",
                coverage(w=560), CW, CH, lg),
        variant("D · Only what changed", "native time is the quiet rule; entries are the marks",
             event_marks(), CW, CH, lg),
    ])


CHART_MOOD = [("C01-Rollout.dc.html", "Rollout, four ways", c01),
              ("C02-Fleet.dc.html", "The fleet, four ways", c02),
              ("C03-Confirmations.dc.html", "Confirmations, four ways", c03),
              ("C04-Hierarchy.dc.html", "The hierarchy, four ways", c04),
              ("C05-Sessions.dc.html", "Sessions today, four ways", c05)]
