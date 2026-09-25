# ================================================================== DP10-DP11: scale, and maximising
# Two questions, and they turn out to be the same question.
#
# DP10 -- WHAT HAPPENS AT 10, 100, 240 MACHINES. Everything drawn so far assumed a department the size
# of Operations: seven machines, two Admins. That was the sample, not the design.
#
# NEVER HORIZONTAL SCROLLING. A chart you have to scroll has stopped answering "how many, how healthy"
# in one look -- it is a table wearing a chart's clothes, and it breaks the settled rule that a count
# is drawn against the largest. If the set does not fit, the DRAWING CHANGES KIND; it does not grow a
# scrollbar.
#
# The square shrinks until it stops being a square. Below about 14 px a slot cannot carry a state
# colour legibly beside its neighbours, and its hostname left long ago, so at that point the cell
# stops drawing one mark per machine and starts drawing the shape of the fleet instead.
#
#   n <= 8      46 px, the hostname inside the slot        -- you can read every machine
#   n <= 30     30 px, no labels, wrapped rows per Admin   -- you can count every machine
#   n <= 120    16 px, dense rows per Admin                -- you can see the proportion and the outliers
#   n > 120     one bar per Admin, and only the exceptions named
#
# In every case the cell answers the same three things: how many, how healthy, and whose. WHICH ONE
# and WHAT IS WRONG WITH IT is the maximised view's job -- which is DP11, and which is why the two
# questions are one question.

import math


def fleet_of(n_admins, n_each, bad_at=()):
    """A department of any size: admins, their machines, and a few in trouble."""
    out = []
    k = 0
    for a in range(n_admins):
        pcs = []
        for i in range(n_each):
            k += 1
            st = "confirmed"
            if k in bad_at:
                st = "behind" if k % 2 else "failing"
            pcs.append((f"OPS-{k:02d}", st))
        out.append((f"Admin {chr(65 + a)}", pcs))
    return out


def slot_size(total):
    if total <= 8:
        return 46, True
    if total <= 30:
        return 30, False
    if total <= 120:
        return 16, False
    return 0, False


def machine_marks(pcs, size, labels, per_row, gap=6):
    rows = []
    for i in range(0, len(pcs), per_row):
        chunk = pcs[i:i + per_row]
        marks = []
        for host, st in chunk:
            label = (f'<text x="{size / 2}" y="{size / 2 + 5}" text-anchor="middle" fill="{CHART_BG}" '
                     f'font-family="{T["mono"]}" font-size="14" font-weight="500">{host.split("-")[-1]}</text>'
                     if labels else "")
            marks.append(f'<svg width="{size}" height="{size}" style="display:block;flex:none;">'
                         f'<rect width="{size}" height="{size}" rx="{max(3, int(size / 3.5))}" fill="{ST[st]}" '
                         f'opacity="0.92"><title>{host}</title></rect>{label}</svg>')
        rows.append(row(*marks, gap=gap, extra="flex: none;"))
    return col(*rows, gap=gap, extra="flex: none;")


def fleet_cell(groups, w=396, note=""):
    """Its machines, at whatever size the department turns out to be."""
    total = sum(len(pcs) for _, pcs in groups)
    size, labels = slot_size(total)
    bad = [(h, s) for _, pcs in groups for h, s in pcs if s != "confirmed"]

    dense = size == 0 or size <= 16
    packed = total > 60          # past this the exceptions line matters more than a second named row
    if size == 0:
        # Past the point where one mark per machine says anything: the shape of each Admin's fleet,
        # and only the machines that are wrong get named.
        bars = []
        for name, pcs in groups:
            parts = [("confirmed", sum(1 for _, s in pcs if s == "confirmed")),
                     ("behind", sum(1 for _, s in pcs if s == "behind")),
                     ("failing", sum(1 for _, s in pcs if s == "failing"))]
            # health_line already prints the total on the right; printing it twice is noise.
            bars.append(col(txt(name, 11.5, T["dim"]),
                            health_line("", [p for p in parts if p[1]], w=w), gap=4))
        body = col(*bars, gap=8, extra=f"width: {w}px;")
    else:
        gap = 6 if size > 20 else 3
        per_row = max(1, (w + gap) // (size + gap))
        # Dense fleets drop the per-Admin count -- the caption already carries the total, and at this
        # size the row of marks IS the count.
        body = col(*[col(row(txt(name, 11.5, T["faint"]), sp(),
                             ("" if dense else txt(f"{len(pcs)}", 11, T["faint"], mono=True)), gap=8,
                             extra=f"width: {w}px;"),
                         machine_marks(pcs, size, labels, per_row, gap if not packed else 2), gap=4 if packed else (5 if dense else 6))
                     for name, pcs in groups],
                   gap=7 if packed else (9 if dense else 12), extra=f"width: {w}px;")

    shown = 1 if (size == 0 or packed) else 2
    named = col(*[row(dot(ST[s], 7), txt(h, 12, T["ink"], 500, mono=True),
                      txt({"behind": "behind", "failing": "out of place"}[s], 11.5, T["faint"]), gap=8,
                      extra=f"width: {w}px;")
                  for h, s in bad[:shown]], gap=5, extra=f"width: {w}px;")
    more = (txt(f"and {len(bad) - shown} more — open it to name them", 11.5, T["faint"])
            if len(bad) > shown else "")
    return col(body, named, more, (txt(note, 11.5, T["faint"]) if note and not dense else ""),
               gap=10 if dense else 13, extra=f"width: {w}px;")


# ------------------------------------------------------------------ DP10: the same cell, four sizes
def dp10():
    seven = [("R. Mensah", [(f"OPS-0{i}", "confirmed") for i in (1, 2, 3)] + [("OPS-06", "behind")]),
             ("A. Quaye", [("OPS-04", "confirmed"), ("OPS-05", "confirmed"), ("OPS-07", "failing")])]
    cells = [
        variant("7 machines", "46 px — every hostname readable",
                fleet_cell(seven, 396, "the sample every board so far was drawn from"), 440, 380),
        variant("24 machines", "30 px — no labels, you can still count them",
                fleet_cell(fleet_of(2, 12, bad_at=(5, 17, 20)), 396,
                           "the slot keeps its shape; only the label goes"), 440, 380),
        variant("96 machines", "16 px — proportion and outliers, not names",
                fleet_cell(fleet_of(4, 24, bad_at=(9, 31, 60, 77, 88)), 396,
                           "still one mark per machine, still grouped by Admin"), 440, 380),
        variant("240 machines", "the drawing changes kind",
                fleet_cell(fleet_of(4, 60, bad_at=(11, 44, 90, 120, 150, 200, 233)), 396,
                           "one bar per Admin; only what is wrong is named"), 440, 380),
        variant("What it never does", "the rejected answer",
                col(txt("Horizontal scrolling.", 13.5, T["ink"], 600),
                    txt("A chart you have to scroll has stopped answering “how many, how healthy” in "
                        "one look — it is a table wearing a chart’s clothes. It also breaks the settled "
                        "rule that a count is drawn against the largest, because you can no longer see "
                        "the largest.", 12, T["dim"], extra="line-height: 1.55;"),
                    txt("So the mark shrinks while shrinking still says something, and past that the cell "
                        "draws the shape of the fleet instead. The cell always answers the same three "
                        "things: how many, how healthy, whose.", 12, T["dim"],
                        extra="line-height: 1.55;"),
                    gap=11, extra="width: 396px;"), 440, 380),
        variant("Where the names went", "and why this is one question, not two",
                col(txt("Which machine, and what is wrong with it.", 13.5, T["ink"], 600),
                    txt("At every size above eight, the cell stops naming machines — and that is exactly "
                        "what maximising is for. The cell answers the shape; the maximised chart answers "
                        "the detail, at whatever size the department happens to be.", 12, T["dim"],
                        extra="line-height: 1.55;"),
                    txt("DP11 →", 12.5, T["accent"], 600),
                    gap=11, extra="width: 396px;"), 440, 380),
    ]
    return mood("Its machines, at 7, 24, 96 and 240",
                "the department was never going to stay the size of the sample",
                cells, brow=eyebrow("BEHAVIOUR", "one cell, any department", "the mark shrinks, then changes kind"))


# ------------------------------------------------------------------ DP11: the chart, maximised
# THE USER'S PROPOSAL, AND IT IS GOOD: double-clicking a chart gives you THAT CHART, FULL SIZE, with
# the context it needs -- and NOT a page of four more charts.
#
# It does not need a new rule. DECISIONS.md already says the composition belongs to the cell and no
# two cells share a shape. A maximised chart is simply a composition of one panel: what explains a
# chart is MORE OF THAT CHART, not more charts. K03-K06 keep their compositions because their
# subjects are AREAS -- authority, a rollout, a day -- and an area is explained by several things.
#
#   A container that stands for an AREA   -> opens into a composition (K03-K06)
#   A container that stands for ONE CHART -> opens into itself, bigger, with its words beside it
#
# Same gesture, same Escape, still one level. The difference is what the container is about.
def dp11():
    """Maximised, the marks go back UP to 46 px and the hostname returns inside the slot. That is the
    whole argument for maximising rather than recomposing: the cell had to drop the names to fit, and
    this is where they come back -- for ninety-six machines or for seven."""
    groups = fleet_of(4, 24, bad_at=(9, 31, 60, 77, 88))
    plate_w, size, gap, per_row = 940, 46, 10, 16
    plate = col(*[col(row(txt(name, 12.5, T["dim"], 500), sp(),
                          txt(f"{len(pcs)} machines", 11.5, T["faint"], mono=True), gap=8,
                          extra=f"width: {plate_w}px;"),
                      machine_marks(pcs, size, True, per_row, gap), gap=7)
                  for name, pcs in groups],
                gap=14, extra=f"width: {plate_w}px; flex: none;")
    reading = col(txt("Ninety-six machines, five of them wrong.", 15, T["ink"], 600,
                      extra="line-height: 1.35;"),
                  col(*[row(dot(ST[st], 8), txt(h, 12.5, T["ink"], 500, mono=True), sp(),
                            txt(w_, 12, tone_c(t, T["faint"]), 500), gap=9,
                            extra=f"width: 296px; padding: 8px 0; border-bottom: 1px solid {T['line']};")
                        for h, st, w_, t in [("OPS-09", "behind", "six attempts", "warn"),
                                             ("OPS-31", "failing", "restricted file", "danger"),
                                             ("OPS-60", "behind", "two attempts", "warn"),
                                             ("OPS-77", "failing", "restricted file", "danger"),
                                             ("OPS-88", "behind", "one attempt", "warn")]],
                      gap=0, extra="width: 296px;"),
                  txt("Single click a square to put its machine here. Double click it to enter that "
                      "machine.", 11.5, T["faint"], extra="line-height: 1.5;"),
                  row(tbtn("Open the two files", "accent", "file", "sm"), gap=0,
                      extra="width: 296px; padding-top: 2px;"),
                  gap=13, extra="width: 296px; flex: none;")
    one = kcell("Its machines", "ninety-six, five wrong", "warn",
                row(plate, reading, gap=40, align="flex-start", extra="width: 1276px;"),
                w=1320, h=640, top=True)
    return dept_page("Operations", ["Authority", "Operations", "Its machines"], "Operations",
                     "one chart, nothing else", "accent", [one],
                     "DP11 · The chart maximised: THAT chart at full size with its own words beside it, and no "
                     "other chart on the page. The marks go back up to 46 px and the hostnames return — the cell "
                     "dropped them to fit, and this is where they come back. Escape restores the four cells exactly. "
                     "K03–K06 keep their compositions because their subjects are areas; an area is explained by "
                     "several things, a chart is explained by itself.",
                     eyebrow("BEHAVIOUR", "double-click a chart", "it maximises, it does not recompose"))


SCALE = [("DP10-Scale.dc.html", "Its machines at 7, 24, 96, 240", dp10),
         ("DP11-Maximised.dc.html", "A chart, maximised", dp11)]


# ================================================================== DP12-DP13: the gesture, at scale
# The maximise only earns its place when the cell has had to drop something. So these are drawn on a
# BIG Operations -- four Admins, ninety-six machines -- where the cell is at 16 px and the hostnames
# are gone. DP12 is that page at rest, DP13 is the same page with the pointer over the cell, and DP11
# is what the double click gives you. Escape puts DP12 back exactly.
#
# The day cell has to scale too: ninety-six lanes is not a drawing. It draws the machines that were
# actually used and says how many were quiet -- the same principle as the fleet, applied to time.

BIG = fleet_of(4, 24, bad_at=(9, 31, 60, 77, 88))

BIG_ADMINS = [dict(a) for a in ADMINS] + [
    {"initials": "KB", "name": "K. Boateng", "host": "WS-OPS-A3", "state": "native", "when": "since 07:55",
     "phrase": ("at their workstation", "dim"), "pcs": [], "tasks": [], "flows": [], "told": ""},
    {"initials": "EO", "name": "E. Owusu", "host": "WS-OPS-A4", "state": "free", "when": "not signed in",
     "phrase": ("free", "dim"), "pcs": [], "tasks": [], "flows": [], "told": ""},
]
# each Admin here answers for one of the four groups above, so "answers for N" is the truth
for _a, (_name, _pcs) in zip(BIG_ADMINS, BIG):
    _a["pcs"] = _pcs
BIG = [(a["name"], a["pcs"]) for a in BIG_ADMINS]


def big_day(w=816, lane_h=21, gap_y=9):
    """At scale the day draws what happened, not every machine that exists: the lanes that have
    something on them, and a count of the ones that have nothing."""
    lanes = [("OPS-03", [("native", 8.2, 12.0), ("native", 13.0, 17.4)]),
             ("OPS-09", [("native", 9.0, 10.3), ("su", 10.3, 11.0), ("native", 11.0, 17.0)]),
             ("OPS-22", [("native", 8.0, 16.2)]),
             ("OPS-31", [("native", 8.5, 17.5)]),
             ("OPS-48", [("native", 8.0, 10.3), ("traversed", 10.3, 11.0), ("native", 11.0, 16.0)]),
             ("OPS-60", [("native", 10.0, 15.4)]),
             ("OPS-77", [("native", 8.2, 17.6)])]
    kind = {"native": T["line2"], "traversed": T["warn"], "su": T["danger"]}
    t0, t1, label_w = 8.0, 18.0, 62
    plot = w - label_w - 12
    out = []
    for hour in range(8, 19, 2):
        x = label_w + ((hour - t0) / (t1 - t0)) * plot
        out.append(f'<line x1="{x:.1f}" y1="2" x2="{x:.1f}" y2="{len(lanes) * (lane_h + gap_y) - gap_y + 2}" '
                   f'stroke="{T["line"]}" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{len(lanes) * (lane_h + gap_y) + 15}" text-anchor="middle" '
                   f'fill="{T["faint"]}" font-family="{T["mono"]}" font-size="11">{hour:02d}</text>')
    for i, (name, blocks) in enumerate(lanes):
        y = 2 + i * (lane_h + gap_y)
        out.append(f'<text x="0" y="{y + lane_h / 2 + 4}" fill="{T["dim"]}" font-family="{T["mono"]}" '
                   f'font-size="11.5">{name}</text>')
        out.append(f'<rect x="{label_w}" y="{y}" width="{plot}" height="{lane_h}" rx="6" '
                   f'fill="{T["pane"]}" opacity="0.5"/>')
        for state, a, b in blocks:
            bx = label_w + ((a - t0) / (t1 - t0)) * plot
            bw = max(5, ((b - a) / (t1 - t0)) * plot - 2)
            out.append(f'<rect x="{bx:.1f}" y="{y}" width="{bw:.1f}" height="{lane_h}" rx="6" fill="{kind[state]}"/>')
    h = len(lanes) * (lane_h + gap_y) + 20
    return col(f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(out)}</svg>',
               legend([("At the PC", T["line2"]), ("An Admin entered", T["warn"]), ("You entered", T["danger"])],
                      "the other 89 machines were never signed in today"),
               gap=14, extra=f"width: {w}px;")


def hover_cell(name, state, tone, chart, w, h, hint):
    """The same cell, with the pointer on it. An enterable container advertises itself: it lifts, the
    pointer changes, and the hover names where it goes. Nothing invisible is load-bearing."""
    surface = col(f'<div style="flex: 1; min-height: 0; display: flex; align-items: flex-start; '
                  f'justify-content: flex-start; overflow: hidden;">{chart}</div>',
                  gap=0, extra=f"flex: 1; min-height: 0; padding: 22px; border-radius: 18px; "
                               f"background: {CHART_BG}; box-sizing: border-box; cursor: zoom-in; "
                               f"box-shadow: inset 0 0 0 1px {T['selectline']}, 0 14px 34px rgba(0,0,0,0.42); "
                               f"transform: translateY(-2px);")
    title = row(txt(name, 15, "#fff", 600),
                txt(hint, 12.5, T["accent"], 600),
                f'<span style="flex: 1;"></span>',
                txt(state, 12.5, tone_c(tone, T["frame_faint"]), 500),
                gap=10, extra="width: 100%; flex: none; padding: 0 4px 9px;")
    return col(title, surface, gap=0,
               extra=f"width: {w}px; height: {h}px; box-sizing: border-box; flex: none; "
                     f"display: flex; flex-direction: column;")


def big_page(machines_cell, note, brow):
    govern = kcell("Who governs", "R. Mensah, of four", "accent",
                   one_admin(BIG_ADMINS[0], BIG_ADMINS[1:], 856), w=900, h=396, top=True)
    waits = kcell("Waiting on you", "five things", "warn",
                  reading_block("Five of the ninety-six need a decision.",
                                [("Behind", "three", "warn"), ("Out of place", "two", "danger"),
                                 ("Reports unaddressed", "2", "warn")],
                                "Open the two reports", w=396),
                  w=440, h=284, top=True)
    today = kcell("Today", "seven machines were used", "warn",
                  big_day(w=816, lane_h=17, gap_y=6), w=900, h=284, top=True)
    return dept_page("Operations", ["Authority", "Operations"], "Operations",
                     "ninety-six machines, four Admins", "dim",
                     [row(govern, machines_cell, gap=20, align="stretch", extra="flex: none;"),
                      row(waits, today, gap=20, align="stretch", extra="flex: none;")],
                     note, brow)


def dp12():
    cell = kcell("Its machines", "three behind, two out of place", "warn",
                 fleet_cell(BIG, 396), w=440, h=396, top=True)
    return big_page(cell,
                    "DP12 · The same page, eight times the department. Its machines is at 16 px, the hostnames "
                    "are gone, and the cell says “open it to name them”. The day draws what happened, not "
                    "every machine that exists.",
                    eyebrow("PAGE", "A department at 96 machines", "the page does not change shape"))


def dp13():
    cell = hover_cell("Its machines", "three behind, two out of place", "warn",
                      fleet_cell(BIG, 396), 440, 396, "— maximise ›")
    return big_page(cell,
                    "DP13 · The pointer is on the cell. It lifts, takes a 1 px accent line, the cursor becomes "
                    "zoom-in and the title says where the gesture goes. A container with nothing behind it does "
                    "none of this and does not respond — nothing invisible is load-bearing.",
                    eyebrow("BEHAVIOUR", "hover, before the double click", "the container advertises itself"))


SCALE += [("DP12-Big.dc.html", "A department at 96 machines", dp12),
          ("DP13-Hover.dc.html", "The cell, advertising itself", dp13)]


# ------------------------------------------------------------------ DP14: an Admin opened, at scale
# DP06 is this same state at the sample size. Drawn again on the big department so the whole path can
# be shown on one organisation: an Admin who answers for twenty-four machines rather than four. The
# composition is unchanged -- the reading still leads -- which is the point: scale changes what a cell
# draws, never what the page is.
def big_chosen_station(a, w=876):
    head = row(av(a["initials"], "admin", 44, "native"),
               col(txt(a["name"], 16, T["ink"], 600),
                   row(txt(a["host"], 12, T["faint"], mono=True), sicon(a["state"], 13),
                       txt(SESSION_WORD[a["state"]] + " · " + a["when"], 12, T["faint"]), gap=7),
                   gap=3, extra="flex: 1; min-width: 0;"),
               sp(), txt("Esc to go back", 12, T["faint"]),
               gap=13, extra=f"width: {w}px;")
    figs = row(figure("8", "tasks", "one overdue", 34), figure("4", "flows", "one failing", 34),
               figure("2", "pings", "unanswered", 34, "warn"),
               figure("24", "machines", "one behind", 34), gap=48, extra="flex: none;")
    return col(head, rule(), figs,
               txt("Twenty-four machines, and OPS-09 has been behind since Friday.", 13, T["ink"], 500,
                   extra="line-height: 1.4;"),
               gap=17, extra=f"width: {w}px;")


def dp14():
    a = BIG_ADMINS[0]
    lane = kcell("Entering R. Mensah", "the cost, then the act", "danger", reading_lane(372),
                 w=416, h=660, top=True, pad=22)
    hero_ = kcell("R. Mensah", "chosen", "accent", big_chosen_station(a, 876), w=924, h=308, top=True)
    theirs = kcell("Their machines", "one behind", "warn",
                   fleet_cell([(a["name"], a["pcs"])], 396), w=452, h=332, top=True)
    theirday = kcell("Their day", "two were used", "warn",
                     col(scoped_day(["OPS-03", "OPS-09", "OPS-14", "OPS-22"],
                                    {"OPS-03": (8.2, 17.4), "OPS-22": (8.0, 16.2)}, w=396),
                         legend([("At the PC", T["line2"])], "twenty-two were quiet"),
                         txt("Two of their twenty-four machines were used today.", 12.5, T["ink"], 500,
                             extra="line-height: 1.4; max-width: 396px;"),
                         gap=13),
                     w=452, h=332, top=True)
    right = col(hero_, row(theirs, theirday, gap=20, align="stretch", extra="flex: none;"),
                gap=20, extra="flex: none; display: flex; flex-direction: column;")
    return dept_page("Operations", ["Authority", "Operations", "R. Mensah"], "Operations",
                     "choosing whether to enter", "accent",
                     [row(lane, right, gap=20, align="flex-start", extra="flex: none;")],
                     "DP14 · The same state as DP06, on the big department. The composition does not change "
                     "with scale — the reading still leads, the cost is still stated before the act — and "
                     "only the machines cell draws differently, because there are twenty-four of them.",
                     eyebrow("BEHAVIOUR", "Who governs, opened on an Admin", "the reading leads, at scale"))


SCALE += [("DP14-Chosen-Big.dc.html", "An Admin opened, at 96 machines", dp14)]
