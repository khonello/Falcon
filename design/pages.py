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


# ------------------------------------------------------------------ P03: page 2, an equal quartet
# A different signature from page 1 on purpose: four equal boxes, the density rising across the
# reading order. Pages that all share one shape stop telling you which page you are on.
def p03():
    QW, QH = 672, 350
    themap = ppanel("The hierarchy", "every department, Admin and PC", org_map(w=600, h=196),
                    density=2, w=QW, h=QH,
                    foot=legend([(d, c) for d, c in DEPT_COLOR.items()], "pick a department to descend"))
    assist = ppanel("Assistance", "across departments, today",
                    told(pair_rows(w=600), "No department has asked another for help today."),
                    density=3, w=QW, h=QH)
    routing_p = ppanel("Report routing", "additive, always",
                       told(routing_rows(w=600), "Three categories reach only you."),
                       density=3, w=QW, h=QH)
    thin = ppanel("Where authority is thin", "",
                  row(reading("Logistics has no Admin, so nobody below you governs it.",
                              [("Department", "Logistics", "danger"), ("Its client PCs", "3"),
                               ("Last traversal", "you, 4 days ago"), ("Open reports", "2 unaddressed", "warn")],
                              action="Assign an Admin", w=320),
                      col(f'<span style="display: block; width: 10px; height: 10px; border-radius: 5px; '
                          f'background: {DEPT_COLOR["Logistics"]};"></span>',
                          txt("Logistics", 12, T["dim"]), gap=8, extra="padding-top: 6px;"),
                      gap=20, align="flex-start"),
                  density=4, w=QW, h=QH)

    body = col(row(themap, assist, gap=16, align="stretch", extra="flex: none;"),
               row(routing_p, thin, gap=16, align="stretch", extra="flex: none;"),
               gap=16, extra="height: 716px; display: flex; flex-direction: column;")
    return pshell("Everything", "3 departments · 3 Admins · 14 client PCs", body,
                  "P03 · Page 2 as an equal quartet — four boxes the same size, density rising 2 → 3 → 3 → 4 "
                  "across the reading order. A different shape from page 1, so the page is recognisable.", 1,
                  brow=eyebrow("PAGE", "page 2 — The hierarchy, an equal quartet", "ready to build"))


# ------------------------------------------------------------------ P04: page 3, a lead and a column
# A third signature: one panel carries the day, and the column beside it hands over to words.
def p04():
    lanes = ppanel("Sessions today", "who held each PC, and for how long",
                   day_timeline(w=880, h=430, lane_h=44), density=2, grow=True,
                   foot=legend([("At the PC", T["line2"]), ("An Admin entered", T["warn"]),
                                ("You entered", T["danger"]), ("Assisted", T["accent"])],
                               "Efua and Kwame were never signed in"))
    vio = ppanel("Violations by tier", "", told(tier_bars(w=330), "One file is where it should not be."),
                 density=3, w=372, h=210)
    dev = ppanel("Deviations", "",
                 told(col(*[row(txt(t, 11.5, T["faint"], mono=True, extra="width: 42px;"),
                                txt(x, 12.5, extra="flex: 1;"), chip(s_, tone, 10), gap=10,
                                extra="padding: 5px 0; width: 100%;")
                            for t, x, s_, tone in
                            [("11:05", "Account from an unbound PC", "Addressed", "ok"),
                             ("09:12", "Hostname did not match", "Logged", "neutral")]], gap=0,
                          extra="width: 330px;"),
                      "One deviation is still unaddressed."),
                 density=3, w=372, h=190)
    day = ppanel("Today, in words", "",
                 reading("Four traversals today, one of them yours.",
                         [("You entered", "OPS-07, 24 minutes"), ("Still open", "1", "warn"),
                          ("Never signed in", "Efua, Kwame", "warn"),
                          ("Assisted", "Operations → Finance, once")],
                         action="Open the trail", w=300),
                 density=4, w=372, grow=True)

    body = row(lanes,
               col(vio, dev, day, gap=16,
                   extra="width: 372px; flex: none; display: flex; flex-direction: column;"),
               gap=16, align="stretch", extra="height: 716px;")
    return pshell("Everything", "Today, 08:00 to now", body,
                  "P04 · Page 3 as a lead and a column — the day is one large shape, and the column beside "
                  "it hands over 3 → 3 → 4. A third signature again.", 2,
                  brow=eyebrow("PAGE", "page 3 — The record, a lead and a column", "ready to build"))


# ------------------------------------------------------------------ P05: a panel is never blank
# The rule: the visual stays. An empty panel keeps its own structure -- the rows, the lanes, the
# tiers, the track -- drawn quiet and at zero, with a short notice laid over it. What never happens
# is a panel that is simply empty space, or one whose chart is replaced by a line of text.
#
# A ZERO IS NOT EMPTY. It is a result, and it is drawn normally with no notice at all: "all 14
# confirmed" and "no violations in /workers/" are answers, not absences.
def ghost(svg, note, sub=""):
    """A chart's own structure, quietened, with the notice over it."""
    return (f'<div style="position: relative;">'
            f'<div style="opacity: 0.28; filter: grayscale(1);">{svg}</div>'
            f'<div style="position: absolute; inset: 0; display: flex; flex-direction: column; '
            f'align-items: center; justify-content: center; gap: 4px;">'
            f'{txt(note, 12.5, T["dim"], 600)}{txt(sub, 11.5, T["faint"]) if sub else ""}</div></div>')


def skeleton_rows(labels, w=440, bar=18, gap_y=26):
    """A chart's bones: its rows at full width, no values. What an empty panel keeps."""
    out, y = [], 4
    for name in labels:
        out.append(f'<text x="0" y="{y + bar - 4}" fill="{T["faint"]}" font-family="{T["sans"]}" font-size="12.5">{name}</text>')
        out.append(f'<rect x="96" y="{y}" width="{w - 140}" height="{bar}" rx="4" fill="{T["line"]}"/>')
        y += gap_y
    return f'<svg width="{w}" height="{y}" viewBox="0 0 {w} {y}">{"".join(out)}</svg>'


def p05():
    PH = 248
    zero_rollout = stacked_bars([("Operations", [("confirmed", 7), ("behind", 0), ("failing", 0)]),
                                 ("Finance", [("confirmed", 4), ("behind", 0), ("failing", 0)]),
                                 ("Logistics", [("confirmed", 3), ("behind", 0), ("failing", 0)])], w=440)
    struct_rollout = skeleton_rows(["Operations", "Finance", "Logistics"], w=440)

    a = ppanel("Rollout 1.4.2", "by department", zero_rollout, density=2, w=CW, h=PH,
               foot=col(txt("Every PC is on 1.4.2.", 13, T["ink"], 500),
                        txt("A ZERO IS A RESULT. Drawn normally, no notice — the chart is answering.",
                            11.5, T["faint"]), gap=8))
    b = ppanel("Rollout 1.4.2", "by department",
               col(ghost(struct_rollout, "Nothing recorded yet", "no version has been approved"),
                   gap=0, extra="padding-top: 10px;"),
               density=2, w=CW, h=PH,
               foot=txt("NOTHING YET. The rows stay so the panel keeps its shape and its size.",
                        11.5, T["faint"]))
    c = ppanel("Confirmations", "since Monday",
               ghost(trend([0, 1], w=440, h=96), "Not enough to draw yet", "one day of attempts so far"),
               density=3, w=CW, h=PH,
               foot=txt("NOT ENOUGH. There is data, but less than this shape needs.", 11.5, T["faint"]))
    d = ppanel("What needs you", "",
               row(reading("Nothing is waiting on you.",
                           [("Behind", "0"), ("Empty departments", "0"), ("Violations", "0")], w=290),
                   col(mini_bar([("confirmed", 14)], w=140), gap=0, extra="width: 140px; padding-top: 8px;"),
                   gap=20, align="flex-start"),
               density=4, w=CW, h=PH,
               foot=txt("A reading panel with nothing to report still reports it, in the same shape.",
                        11.5, T["faint"]))

    rules = col(row(txt("A panel is never blank", 13.5, T["ink"], 600),
                    txt("three cases, and only two of them get a notice", 11.5, T["faint"]), gap=10),
                row(*[row(f'<span style="width: 6px; height: 6px; border-radius: 3px; background: {c_}; '
                          f'flex: none;"></span>',
                          col(txt(k, 12.5, T["ink"], 600), txt(v, 11.5, T["faint"]), gap=2, extra="flex: 1;"),
                          gap=10, extra="width: 420px;")
                      for k, v, c_ in
                      [("A zero", "drawn normally, no notice — it is an answer", T["ok"]),
                       ("Nothing yet", "structure stays, quietened, notice over it", T["warn"]),
                       ("Not enough", "the shape's frame, and what is missing", T["accent"])]],
                    gap=16, align="flex-start", extra="flex-wrap: wrap;"),
                gap=14, extra=f"width: {CW * 2 + 16}px; padding: 16px 18px; border-radius: 16px; "
                              f"background: {CHART_BG}; box-sizing: border-box; flex: none;")

    return mood("A panel is never blank", "the visual stays; the notice is laid over it, not put in place of it",
                [a, b, c, d, rules],
                brow=eyebrow("SYSTEM", "applies to every panel on every page", "all three pages"))


PAGES_COMPOSED = [("P01-Density.dc.html", "The four panel densities", p01),
                  ("P02-Glance.dc.html", "Page 1 composed: At a glance", p02),
                  ("P03-Hierarchy.dc.html", "Page 2 composed: The hierarchy", p03),
                  ("P04-Record.dc.html", "Page 3 composed: The record", p04),
                  ("P05-Empty.dc.html", "A panel is never blank", p05)]
