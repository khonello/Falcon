# ================================================================== P01-P04: the pages, composed
# The user's move: instead of a page of mute charts that only speak when clicked, let the LAYOUT
# carry the explanation. A page runs from shape to words across its reading order -- the first
# panel is almost all picture, the last is almost all sentence, and the ones between hand over
# gradually. Less navigation, and the text and the charts explain the system together.
#
# To make that a system rather than one nice arrangement, a panel has a DENSITY. A layout is a
# sequence of densities, so a new page is composed rather than invented.
#
#   1  Figure        a number and a word.            no chart, no sentence
#   2  Chart         a shape and its legend.         no sentence
#   3  Chart, told   a shape and ONE sentence under it
#   4  Reading       a sentence, facts one line each, and one small mark
#
# Clicking is not gone: the page answers the page-level question without it, and a click still
# answers the item-level one (X02) -- "why is LOG-02 failing" cannot be pre-written for every bar.

DENSITY_NAMES = {1: "Figure", 2: "Chart", 3: "Chart, told", 4: "Reading"}


def dtag(n):
    return (f'<span style="display: inline-flex; align-items: center; justify-content: center; width: 18px; '
            f'height: 18px; border-radius: 6px; background: {T["pane"]}; color: {T["faint"]}; '
            f'font-family: {T["mono"]}; font-size: 10.5px; flex: none;">{n}</span>')


def ppanel(title, note, *children, density=None, w=None, grow=False, h=None, foot="", show_density=False):
    head = row(txt(title, 13.5, T["ink"], 600), txt(note, 11.5, T["faint"]) if note else "",
               f'<span style="flex: 1;"></span>',
               dtag(density) if (show_density and density) else "", gap=10, extra="flex: none; width: 100%;")
    body = (f'<div style="flex: 1; min-height: 0; display: flex; align-items: flex-start; overflow: hidden;">'
            f'{"".join(children)}</div>')
    parts = [head, body] + ([foot] if foot else [])
    size = (f"width: {w}px; " if w else "") + (f"height: {h}px; " if h else "")
    return col(*parts, gap=12,
               extra=f"{size}padding: 16px 18px; border-radius: 16px; background: {CHART_BG}; "
                     f"box-sizing: border-box; {'flex: 1; min-width: 0;' if grow else 'flex: none;'}")


def told(chart, sentence, w=None):
    """Density 3: the shape, and under it the one sentence it is making. The sentence is generated
    from a condition, never written -- and when no condition matches it states the plain fact
    instead of manufacturing an insight."""
    return col(chart, txt(sentence, 13, T["ink"], 500, extra="line-height: 1.4;"),
               gap=14, extra=f"{'width: %dpx; ' % w if w else ''}flex: none;")


def pshell(title, sub, structure, note, pill=0, brow=""):
    pills = row(*[f'<span style="display: inline-flex; align-items: center; height: 30px; padding: 0 15px; '
                  f'border-radius: 999px; background: {T["select"] if i == pill else T["ground"]}; '
                  f'color: {"#fff" if i == pill else T["dim"]}; font-family: {T["sans"]}; font-size: 13px; '
                  f'font-weight: 600;">{p}</span>'
                  for i, p in enumerate(["At a glance", "The hierarchy", "The record"])], gap=7, extra="flex: none;")
    header = col(brow if brow else "",
                 row(f'<span style="width: 10px; height: 26px; border-radius: 3px; background: #fff;"></span>',
                     txt(title, 22, "#fff", 700), txt(sub, 13, T["frame_dim"]), gap=12),
                 pills, gap=12, extra="flex: none;")
    inner = col(header, structure, row(txt(note, 11.5, T["frame_faint"]), gap=0, extra="flex: none;"),
                gap=14, extra=f"width: {W}px; height: {H}px; box-sizing: border-box; padding: 22px 40px; "
                              f"background: {FRAME['native']}; overflow: hidden;")
    return page(title, "", "", inner, "", "native")


# ------------------------------------------------------------------ P01: the four densities
SENTENCE_RULES = [
    ("A sentence is generated, never written", "one template per condition, filled from the same data the chart drew"),
    ("No condition matched?", "state the plain fact — “All 14 PCs are on 1.4.2.” — and never manufacture an insight"),
    ("Twelve words or fewer", "if it needs more, it is a fact for the row below, not the sentence"),
    ("It says what the chart says", "not what someone should feel about it"),
]


def p01():
    PH = 248
    fig = ppanel("The figures", "", row(hero("14", "client PCs", "across 3 departments"),
                                        hero("12", "on 1.4.2", "2 still behind", "warn"), gap=48),
                 density=1, w=CW, h=PH, show_density=True,
                 foot=txt("A number and a word. No chart and no sentence — the figure is the statement.",
                          11.5, T["faint"]))
    cha = ppanel("Rollout 1.4.2", "by department",
                 stacked_bars([(n, [("confirmed", a), ("behind", b), ("failing", f)]) for n, a, b, f in ROLLOUT], w=460),
                 density=2, w=CW, h=PH, show_density=True,
                 foot=txt("A shape and its legend. What the boards have carried so far.", 11.5, T["faint"]))
    tol = ppanel("Confirmations", "since Monday",
                 told(trend(SERIES, w=460, h=92),
                      "Confirmations have not moved since Friday."),
                 density=3, w=CW, h=PH, show_density=True,
                 foot=txt("A shape, and the one sentence it is making. The handover begins here.", 11.5, T["faint"]))
    rea = ppanel("What needs you", "",
                 row(reading("Two PCs are not on 1.4.2, and 1.4.3 is blocked until they are.",
                             [("Retrying", "OPS-06", "warn"), ("Failing", "LOG-02, 6 attempts", "danger")],
                             action="Nudge both Admins", w=290),
                     col(mini_bar([("confirmed", 12), ("behind", 1), ("failing", 1)], w=140), gap=0,
                         extra="width: 140px; padding-top: 8px;"),
                     gap=20, align="flex-start"),
                 density=4, w=CW, h=PH, show_density=True,
                 foot=txt("A sentence, facts one line each, and one small mark so it still belongs.",
                          11.5, T["faint"]))

    rules = col(row(txt("Where the sentences come from", 13.5, T["ink"], 600),
                    txt("the part of this idea that can go wrong", 11.5, T["faint"]), gap=10),
                row(*[row(f'<span style="width: 6px; height: 6px; border-radius: 3px; background: {T["accent"]}; '
                          f'flex: none;"></span>',
                          col(txt(k, 12.5, T["ink"], 600), txt(v, 11.5, T["faint"]), gap=2, extra="flex: 1;"),
                          gap=10, extra="width: 310px;")
                      for k, v in SENTENCE_RULES], gap=16, align="flex-start", extra="flex-wrap: wrap;"),
                gap=14, extra=f"width: {CW * 2 + 16}px; padding: 16px 18px; border-radius: 16px; "
                              f"background: {CHART_BG}; box-sizing: border-box; flex: none;")

    return mood("Four panel densities", "a layout is a sequence of these, running shape → words",
                [fig, cha, tol, rea, rules],
                brow=eyebrow("SYSTEM", "the vocabulary every page is composed from", "all three pages"))


# ------------------------------------------------------------------ P02: page 1, composed
def p02():
    band = col(row(hero("14", "client PCs", "across 3 departments"),
                   hero("12", "on 1.4.2", "2 still behind", "warn"),
                   hero("2", "waiting on you", "an empty department, a violation", "danger"),
                   hero("4", "traversals today", "1 still open"), gap=64, extra="flex: none;"),
               gap=0, extra=f"padding: 18px 24px; border-radius: 16px; background: {CHART_BG}; "
                            f"height: 104px; box-sizing: border-box; flex: none;")

    rollout = ppanel("Rollout 1.4.2", "by department", density=2, grow=True,
                     *[stacked_bars([(n, [("confirmed", a), ("behind", b), ("failing", f)])
                                     for n, a, b, f in ROLLOUT], w=600)],
                     foot=legend([("Confirmed", ST["confirmed"]), ("Behind", ST["behind"]), ("Failing", ST["failing"])]))
    conf = ppanel("Confirmations", "since Monday",
                  told(trend(SERIES, w=600, h=120), "Nothing has confirmed since Friday."),
                  density=3, grow=True)
    fleet = ppanel("The fleet", "one square per PC", waffle(FLEET, cols=7, size=28, gap=8, w=260),
                   density=2, h=196,
                   foot=legend([("Confirmed", ST["confirmed"]), ("Behind", ST["behind"]), ("Failing", ST["failing"])]))
    needs = ppanel("What needs you", "",
                   reading("Two PCs are not on 1.4.2, and 1.4.3 is blocked until they are.",
                           [("Retrying", "OPS-06", "warn"), ("Failing", "LOG-02, 6 attempts", "danger"),
                            ("No Admin", "Logistics", "danger"), ("Violation", "budget-2026.xlsx, OPS-07", "danger")],
                           action="Nudge both Admins", w=300),
                   density=4, grow=True)

    # the gradient runs diagonally: shape at the top left, words at the bottom right
    body = col(band,
               row(col(rollout, conf, gap=16,
                       extra="flex: 1; min-width: 0; display: flex; flex-direction: column;"),
                   col(fleet, needs, gap=16,
                       extra="width: 372px; flex: none; display: flex; flex-direction: column;"),
                   gap=16, align="stretch", extra="flex: 1; min-height: 0;"),
               gap=16, extra="height: 716px; display: flex; flex-direction: column;")
    return pshell("Everything", "3 departments · 3 Admins · 14 client PCs", body,
                  "P02 · Page 1 composed 1 → 2 → 3 → 4. Figures, then shapes, then a shape with its sentence, "
                  "then the words. Nothing has to be clicked for the page to answer.",
                  brow=eyebrow("PAGE", "page 1 — At a glance, composed from the densities", "ready to build"))


# ------------------------------------------------------------------ P03: page 2, composed
def p03():
    themap = ppanel("The hierarchy", "every department, Admin and PC", org_map(w=620, h=300),
                    density=2, grow=True,
                    foot=legend([(d, c) for d, c in DEPT_COLOR.items()], "pick a department to descend"))
    assist = ppanel("Assistance", "", told(pair_rows(w=330), "Logistics has asked no one for help."),
                    density=3, w=390)
    routing_p = ppanel("Report routing", "", told(routing_rows(w=330),
                                                  "Three categories reach only you."),
                       density=3, w=390)
    thin = ppanel("Where authority is thin", "",
                  reading("Logistics has no Admin, so nobody below you governs three PCs.",
                          [("Department", "Logistics", "danger"), ("Client PCs", "3"),
                           ("Last traversal", "you, 4 days ago"), ("Open reports", "2 unaddressed", "warn")],
                          action="Assign an Admin", w=300),
                  density=4, w=372)

    body = row(col(themap, row(assist, routing_p, gap=16, align="stretch", extra="flex: none; height: 250px;"),
                   gap=16, extra="flex: 1; min-width: 0; display: flex; flex-direction: column;"),
               thin, gap=16, align="stretch", extra="height: 716px;")
    return pshell("Everything", "3 departments · 3 Admins · 14 client PCs", body,
                  "P03 · Page 2. The map carries the shape; the two told panels each add one line; the "
                  "reading panel says the thing the map cannot: what the gap means.", 1,
                  brow=eyebrow("PAGE", "page 2 — The hierarchy, composed from the densities", "ready to build"))


# ------------------------------------------------------------------ P04: page 3, composed
def p04():
    lanes = ppanel("Sessions today", "who held each PC, and for how long", day_timeline(w=620, h=300, lane_h=30),
                   density=2, grow=True,
                   foot=legend([("At the PC", T["line2"]), ("An Admin entered", T["warn"]), ("You entered", T["danger"])]))
    vio = ppanel("Violations by tier", "", told(tier_bars(w=330), "One file is where it should not be."),
                 density=3, w=390)
    dev = ppanel("Deviations", "", told(col(*[row(txt(t, 11.5, T["faint"], mono=True, extra="width: 42px;"),
                                                  txt(x, 12.5, extra="flex: 1;"), chip(s_, tone, 10), gap=10,
                                                  extra="padding: 6px 0; width: 100%;")
                                              for t, x, s_, tone in
                                              [("11:05", "Account from an unbound PC", "Addressed", "ok"),
                                               ("09:12", "Hostname did not match", "Logged", "neutral")]], gap=0,
                                            extra="width: 330px;"),
                                        "One deviation is still unaddressed."),
                 density=3, w=390)
    day = ppanel("Today, in words", "",
                 reading("Two PCs were never signed into, and you entered one workstation yourself.",
                         [("Traversals", "4, one still open"), ("You entered", "OPS-07, 24 minutes"),
                          ("Never signed in", "Efua, Kwame", "warn"), ("Assisted", "Operations → Finance, once")],
                         action="Open the trail", w=300),
                 density=4, w=372)

    body = row(col(lanes, row(vio, dev, gap=16, align="stretch", extra="flex: none; height: 250px;"),
                   gap=16, extra="flex: 1; min-width: 0; display: flex; flex-direction: column;"),
               day, gap=16, align="stretch", extra="height: 716px;")
    return pshell("Everything", "Today, 08:00 to now", body,
                  "P04 · Page 3. The day as a shape, two told panels, and the day in words — which is the "
                  "panel a Super User would read first if they only had ten seconds.", 2,
                  brow=eyebrow("PAGE", "page 3 — The record, composed from the densities", "ready to build"))


PAGES_COMPOSED = [("P01-Density.dc.html", "The four panel densities", p01),
                  ("P02-Glance.dc.html", "Page 1 composed: At a glance", p02),
                  ("P03-Hierarchy.dc.html", "Page 2 composed: The hierarchy", p03),
                  ("P04-Record.dc.html", "Page 3 composed: The record", p04)]
