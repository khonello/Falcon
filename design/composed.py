# ================================================================== J01-J02: one page, three charts
# The brief, exactly: no tabs, one big chart, one medium chart, one small one tucked into the
# bottom right, and the text sitting on and around the charts rather than in blocks of its own.
#
# The difference from everything before it is that the charts are SIZED AGAINST EACH OTHER. A big
# one, a medium one and a small one make a composition; four equal ones make a grid, which is what
# every previous attempt was. Text is annotation here -- it lands on the chart, next to the thing
# it is about.

def anno(x, y, lines, anchor="start", lead=None, lead_to=None, tone=None):
    """Text placed ON the chart, next to what it is about. Optionally with a leader line to it."""
    out = []
    if lead and lead_to:
        out.append(f'<path d="M{lead[0]} {lead[1]} L{lead_to[0]} {lead_to[1]}" stroke="{T["line2"]}" '
                   f'stroke-width="1" fill="none"/>')
        out.append(f'<circle cx="{lead_to[0]}" cy="{lead_to[1]}" r="2.5" fill="{T["line2"]}"/>')
    for i, (text, size, colour, weight) in enumerate(lines):
        out.append(f'<text x="{x}" y="{y + i * (size + 5)}" text-anchor="{anchor}" fill="{colour}" '
                   f'font-family="{T["sans"]}" font-size="{size}" font-weight="{weight}">{text}</text>')
    return "".join(out)


# ------------------------------------------------------------------ the big one: the system, drawn
def system_map(w=800, h=470, hero=True):
    """Every department, Admin and PC, drawn large enough to be the subject of the page. The labels
    are part of the drawing -- department names sit on their nodes, and the one thing that is wrong
    is called out where it is."""
    depts = [("Operations", 2, 7, 0), ("Finance", 1, 4, 1), ("Logistics", 0, 3, 2)]
    rx, dx, px = 54, w * 0.38, w * 0.60
    links, nodes, labels = [], [], []
    ys = [h * 0.20, h * 0.52, h * 0.84]
    root_y = h * 0.52

    for name, admins, pcs, idx in depts:
        c = DEPT_COLOR[name]
        dy = ys[idx]
        links.append(f'<path d="M{rx + 17} {root_y} C {(rx + dx) / 2} {root_y}, {(rx + dx) / 2} {dy}, {dx - 17} {dy}" '
                     f'fill="none" stroke="{c}" stroke-width="2" opacity="0.5"/>')
        per_row = 4
        for k in range(pcs):
            ox = px + (k % per_row) * 48
            oy = dy - 34 + (k // per_row) * 46
            failing = name == "Logistics" and k == 2
            behind = name == "Operations" and k == 6
            fill = ST["failing"] if failing else ST["behind"] if behind else c
            op = 1 if (failing or behind) else 0.8
            links.append(f'<path d="M{dx + 16} {dy} C {(dx + px) / 2} {dy}, {(dx + px) / 2} {oy}, {ox - 12} {oy}" '
                         f'fill="none" stroke="{c}" stroke-width="1.2" opacity="0.22"/>')
            nodes.append(f'<circle cx="{ox}" cy="{oy}" r="{13 if (failing or behind) else 10}" fill="{fill}" opacity="{op}"/>')
            if failing:
                labels.append(anno(ox + 38, oy - 3,
                                   [("LOG-02", 14, T["ink"], 500),
                                    ("failed six times", 12.5, ST["failing"], 400)],
                                   lead=(ox + 33, oy - 8), lead_to=(ox + 15, oy)))
        nodes.append(f'<circle cx="{dx}" cy="{dy}" r="16" fill="{c}"/>')
        labels.append(anno(dx - 28, dy + 1,
                           [(name, 17, T["ink"], 500),
                            ("no Admin" if admins == 0 else f'{admins} Admin{"s" if admins > 1 else ""}, '
                             f'{pcs} PCs', 13, T["danger"] if admins == 0 else T["faint"], 400)],
                           anchor="end"))
    nodes.append(f'<circle cx="{rx}" cy="{root_y}" r="19" fill="{T["ink"]}"/>')
    labels.append(anno(rx, root_y + 42, [("you", 13, T["dim"], 400)], anchor="middle"))
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(links + nodes + labels)}</svg>'


# ------------------------------------------------------------------ the big one, alternative: the day
def day_big(w=800, h=470):
    """The same page with the day as its subject instead of the shape of the organisation."""
    lanes = [("Kojo", [("native", 8.2, 12.0), ("native", 13.0, 17.4)]),
             ("Efua", []),
             ("Yaw", [("native", 9.0, 12.5), ("traversed", 12.5, 13.2), ("native", 13.2, 17.0)]),
             ("Adjoa", [("native", 8.0, 10.3), ("traversed", 10.3, 11.0), ("native", 11.0, 16.0)]),
             ("Nana", [("native", 8.5, 17.5)]),
             ("Kwame", []),
             ("Ama", [("native", 8.2, 10.7), ("su", 10.7, 11.1), ("native", 11.1, 17.6)])]
    kind = {"native": T["line2"], "traversed": T["warn"], "su": T["danger"]}
    t0, t1 = 8.0, 18.0
    label_w, lane_h, gap = 76, 40, 14
    plot = w - label_w - 30
    out = []
    for hour in range(8, 19, 2):
        x = label_w + ((hour - t0) / (t1 - t0)) * plot
        out.append(f'<line x1="{x:.1f}" y1="6" x2="{x:.1f}" y2="{len(lanes) * (lane_h + gap) - gap + 6}" '
                   f'stroke="{T["line"]}" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{len(lanes) * (lane_h + gap) + 20}" text-anchor="middle" '
                   f'fill="{T["faint"]}" font-family="{T["mono"]}" font-size="11.5">{hour:02d}</text>')
    for i, (name, blocks) in enumerate(lanes):
        y = 6 + i * (lane_h + gap)
        out.append(f'<text x="0" y="{y + lane_h / 2 + 5}" fill="{T["dim"]}" font-family="{T["sans"]}" '
                   f'font-size="14">{name}</text>')
        out.append(f'<rect x="{label_w}" y="{y}" width="{plot}" height="{lane_h}" rx="10" '
                   f'fill="{T["pane"]}" opacity="0.5"/>')
        if not blocks:
            out.append(f'<text x="{label_w + 16}" y="{y + lane_h / 2 + 5}" fill="{T["faint"]}" '
                       f'font-family="{T["sans"]}" font-size="12.5">never signed in</text>')
        for state, a, b in blocks:
            bx = label_w + ((a - t0) / (t1 - t0)) * plot
            bw = max(6, ((b - a) / (t1 - t0)) * plot - 3)
            out.append(f'<rect x="{bx:.1f}" y="{y}" width="{bw:.1f}" height="{lane_h}" rx="10" fill="{kind[state]}"/>')
            if state == "su":
                out.append(anno(bx + bw / 2, y - 12,
                                [("you, 24 minutes", 12, ST["failing"], 500)], anchor="middle"))
    return f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(out)}</svg>'


# ------------------------------------------------------------------ the pieces
def big(title, over, chart, w=822, note=""):
    """The hero. Its headline sits ON the chart's own surface, top left, not in a bar above it."""
    head = col(txt(title, 13, T["faint"]),
               txt(over, 26, T["ink"], 600, extra="line-height: 1.25; max-width: 470px;"),
               txt(note, 12.5, T["faint"]) if note else "",
               gap=9, extra="flex: none;")
    return col(head, f'<div style="flex: 1; min-height: 0; display: flex; align-items: center;">{chart}</div>',
               gap=6, extra=f"width: {w}px; height: 100%; padding: 28px 30px 20px; border-radius: 20px; "
                            f"background: {CHART_BG}; box-sizing: border-box; flex: none; "
                            f"display: flex; flex-direction: column;")


def medium(over, chart, foot, w=506):
    """Second in the ranking, and sized to its content -- a panel stretched to fill a column is how
    the air gets in."""
    return col(txt(over, 19, T["ink"], 600, extra="line-height: 1.3; max-width: 420px;"),
               chart, foot, gap=20,
               extra=f"width: {w}px; padding: 26px 28px 22px; border-radius: 20px; background: {CHART_BG}; "
                     f"box-sizing: border-box; flex: none;")


def small(over, chart, w=506):
    """Tucked: it sits in the corner of its space rather than filling it, and says one thing."""
    return row(col(txt(over, 13, T["ink"], 500, extra="line-height: 1.35; max-width: 160px;"),
                   gap=0, extra="flex: none; padding-top: 4px;"),
               f'<span style="flex: 1;"></span>',
               f'<div style="flex: none;">{chart}</div>',
               gap=18, align="center",
               extra=f"width: {w}px; padding: 18px 26px; border-radius: 20px; background: {CHART_BG}; "
                     f"box-sizing: border-box; flex: none;")


def jshell(structure, note, brow=""):
    head = row(txt("Everything", 22, "#fff", 700),
               txt("three departments, three Admins, fourteen client PCs", 13, T["frame_dim"]),
               f'<span style="flex: 1;"></span>',
               txt("Wednesday, 14:20", 12.5, T["frame_faint"]), gap=14,
               extra="width: 100%; flex: none;")
    inner = col(brow if brow else "", head, structure,
                row(txt(note, 11.5, T["frame_faint"]), gap=0, extra="flex: none;"),
                gap=16, extra=f"width: {W}px; height: {H}px; box-sizing: border-box; padding: 24px 40px 20px; "
                              f"background: {FRAME['native']}; overflow: hidden; display: flex; "
                              f"flex-direction: column;")
    return page("Everything", "", "", inner, "", "native")


# ------------------------------------------------------------------ J01: the system is the subject
def j01():
    hero = big("The system", "Logistics has no Admin, and its failing PC has nobody to chase it.",
               system_map(w=760, h=500),
               note="every department, Admin and client PC you govern")

    med = medium("Two PCs are behind, so 1.4.3 stays blocked.",
                 stacked_bars([(n, [("confirmed", a), ("behind", b), ("failing", f)])
                               for n, a, b, f in ROLLOUT], w=440, bar_h=20, gap_y=32),
                 legend([("Confirmed", ST["confirmed"]), ("Behind", ST["behind"]), ("Failing", ST["failing"])]))

    sm = small("Nothing has confirmed since Friday.",
               col(trend(SERIES, w=250, h=62), gap=0))

    body = row(hero, col(med, f'<span style="flex: 1;"></span>', sm, gap=16,
                         extra="flex: 1; min-width: 0; display: flex; flex-direction: column;"),
               gap=16, align="stretch", extra="flex: 1; min-height: 0;")
    return jshell(body,
                  "J01 · One big, one medium, one small tucked into the corner. The headline sits on the "
                  "hero's own surface and the callout sits on the PC it is about.",
                  brow=eyebrow("PAGE", "Overview — one page, no tabs", "the system is the subject"))


# ------------------------------------------------------------------ J02: the day is the subject
def j02():
    hero = big("Today", "You entered Ama's machine for twenty-four minutes. Two PCs were never signed into.",
               day_big(w=760, h=430),
               note="who held each client PC, from 08:00")

    med = medium("Logistics is the only department with work overdue.",
                 row(*[health_card(n, DEPT_COLOR[n], list(zip(WORK_TONES, t)), list(zip(WORK_TONES, f)), w=140)
                       for n, (t, f) in WORK.items()], gap=10),
                 legend([("On track", ST["confirmed"]), ("Needs attention", ST["behind"]), ("Overdue", ST["failing"])]))

    sm = small("One file sits where its tier does not allow.",
               tier_bars(w=250))

    body = row(hero, col(med, f'<span style="flex: 1;"></span>', sm, gap=16,
                         extra="flex: 1; min-width: 0; display: flex; flex-direction: column;"),
               gap=16, align="stretch", extra="flex: 1; min-height: 0;")
    return jshell(body,
                  "J02 · The same composition with the day as the hero instead of the organisation.",
                  brow=eyebrow("PAGE", "Overview — one page, no tabs", "the day is the subject"))


COMPOSED = [("J01-System.dc.html", "Overview: the system is the subject", j01),
            ("J02-Day.dc.html", "Overview: the day is the subject", j02)]
