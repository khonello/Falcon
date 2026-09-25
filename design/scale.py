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
                         machine_marks(pcs, size, labels, per_row, gap), gap=5 if dense else 6)
                     for name, pcs in groups],
                   gap=9 if dense else 12, extra=f"width: {w}px;")

    shown = 1 if size == 0 else 2
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
