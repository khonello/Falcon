# ================================================================== H01-H03: the watch
# The Overview is not an analytics dashboard, and designing it as one is why every attempt so far
# has looked like every other dashboard. A Super User is on WATCH: their job is to be told what
# needs them, in plain language, with the evidence available if they want it. The nearest thing in
# the world is a duty officer's log, and that is a typographic object, not a chart-led one.
#
# What follows from that:
#   * The page is a LIST, not a grid. One surface, five statements, hairlines between them. No
#     identical rounded cards -- that module is what made the earlier takes interchangeable.
#   * Size carries the hierarchy. The statement that needs you is set at display size; everything
#     else is quiet at one body size. Nothing is bold-for-emphasis and nothing is boxed to stand out.
#   * The page is almost monochrome. The only colour is the verdict word on the statements that are
#     not fine -- colour says state and nothing else, so it appears twice on a good day.
#   * Every statement says what it was worked out from, in prose. That line is what makes a
#     judgement checkable instead of something you have to take on trust.
#   * No tabs. The map belongs to Hierarchy and the rollout to Updates -- rail entries that already
#     exist -- so the Overview stops duplicating them and just says what it concluded.

WATCH = [
    ("danger", "Two things need you, and one has been waiting four days.",
     "worked out from the hierarchy, the rollout and the report trail"),
    ("warn", "The rollout is stalled, not slow.",
     "worked out from confirmations, escalation counts and who governs the failing PC"),
    ("ok", "Nobody was blocked from their own machine today.",
     "worked out from every session opened, ended or expired since 08:00"),
    ("ok", "The work is being done, apart from one department.",
     "worked out from every task deadline and every flow's sync state"),
    ("ok", "Nothing has moved anywhere it should not be.",
     "worked out from the file index, the resource tiers and the deviation log"),
]

VERDICT = {"ok": ("Fine", "dim"), "warn": ("Watch", "warn"), "danger": ("Needs you", "danger")}


def statement(tone, sentence, source, lead=False, opened=False, last=False):
    """One line of the watch. A statement, and underneath it the prose that says where it came
    from. No card, no pill, no icon -- the size says which one matters and the verdict word on the
    right says how it stands."""
    word, colour = VERDICT[tone]
    size = 34 if lead else 19
    weight = 600 if lead else 500
    verdict = txt(word, 13 if lead else 12.5, T[colour] if colour != "dim" else T["faint"],
                  600 if colour != "dim" else 400)
    chev = f'<span style="flex: none; opacity: {0.9 if opened else 0.45};">{ic("chevd" if opened else "chev", 15, T["faint"])}</span>'
    line = row(col(txt(sentence, size, T["ink"], weight,
                       extra=f"line-height: {1.18 if lead else 1.3}; max-width: {760 if lead else 820}px;"),
                   txt(source, 12.5, T["faint"], extra="line-height: 1.45;"),
                   gap=10 if lead else 7, extra="flex: 1; min-width: 0;"),
               col(verdict, gap=0, extra="flex: none; padding-top: 6px;"),
               chev, gap=26, align="flex-start",
               extra=f"width: 100%; padding: {30 if lead else 22}px 0 {26 if lead else 20}px;")
    rule = "" if last else f'<span style="display: block; height: 1px; background: {T["line"]}; width: 100%;"></span>'
    return col(line, rule, gap=0, extra="width: 100%;")


def watch_page(inner_rows, note, brow=""):
    head = row(txt("Everything", 15, T["frame_dim"], 500),
               f'<span style="flex: 1;"></span>',
               txt("Wednesday, 14:20", 12.5, T["frame_faint"]),
               gap=12, extra="width: 100%; flex: none;")
    # the surface ends where the watch ends. A page that stretches a list to fill a screen is how
    # dead space gets built in; below it there is only the frame, which is not empty, it is the app.
    foot = row(txt("Three departments, three Admins and fourteen client PCs, last read at 14:20.",
                   12.5, T["faint"]), gap=0, extra="width: 100%; padding: 22px 0 4px;")
    surface = col(*inner_rows, foot, gap=0,
                  extra=f"width: 100%; flex: none; padding: 8px 40px 18px; border-radius: 20px; "
                        f"background: {CHART_BG}; box-sizing: border-box; overflow: hidden;")
    inner = col(brow if brow else "", head, surface,
                row(txt(note, 11.5, T["frame_faint"]), gap=0, extra="flex: none;"),
                gap=16, extra=f"width: {W}px; height: {H}px; box-sizing: border-box; padding: 26px 40px 22px; "
                              f"background: {FRAME['native']}; overflow: hidden; display: flex; "
                              f"flex-direction: column;")
    return page("Everything", "", "", inner, "", "native")


# ------------------------------------------------------------------ H01: the watch, at rest
def h01():
    rows_ = [statement(t, s, src, lead=(i == 0), last=(i == len(WATCH) - 1))
             for i, (t, s, src) in enumerate(WATCH)]
    return watch_page(rows_,
                      "H01 · Five statements, one surface. No chart until you ask for one, and each line "
                      "says what it was worked out from so it can be checked.",
                      brow=eyebrow("PAGE", "Overview — one page, no tabs", "the whole system, on watch"))


# ------------------------------------------------------------------ H02: one statement, opened
# The evidence is four facts that had to be true TOGETHER -- not a sequence, so it is not numbered.
# Each is a short line with its own small mark beside it, on the same left edge as everything else.
def fact_line(line, mark, tone=None):
    return row(col(txt(line, 14, T["ink"], 500, extra="line-height: 1.4;"), gap=0,
                   extra="width: 300px; flex: none; padding-top: 2px;"),
               f'<div style="flex: 1; min-width: 0;">{mark}</div>',
               gap=28, align="center", extra="width: 100%; padding: 16px 0;")


def h02():
    before = statement(*WATCH[0], lead=True)
    opened = statement(*WATCH[1], opened=True)

    evidence = col(
        txt("Four things are true at once.", 13, T["dim"], 500, extra="padding-bottom: 2px;"),
        fact_line("Two of fourteen PCs have not confirmed 1.4.2.",
                  stacked_bars([(n, [("confirmed", a), ("behind", b), ("failing", f)])
                                for n, a, b, f in ROLLOUT], w=460, bar_h=12, gap_y=20)),
        f'<span style="display: block; height: 1px; background: {T["line"]}; width: 100%; opacity: 0.6;"></span>',
        fact_line("None has confirmed since Friday.",
                  col(trend(SERIES, w=460, h=74), gap=0)),
        f'<span style="display: block; height: 1px; background: {T["line"]}; width: 100%; opacity: 0.6;"></span>',
        fact_line("LOG-02 has failed six times; the threshold is three.",
                  row(*[f'<span style="width: 22px; height: 22px; border-radius: 7px; background: '
                        f'{ST["failing"] if i < 6 else T["line"]}; display: inline-block;"></span>'
                        for i in range(9)], gap=5)),
        f'<span style="display: block; height: 1px; background: {T["line"]}; width: 100%; opacity: 0.6;"></span>',
        fact_line("Its department has nobody to chase it.",
                  row(f'<span style="width: 10px; height: 10px; border-radius: 5px; '
                      f'background: {DEPT_COLOR["Logistics"]};"></span>',
                      txt("Logistics", 13.5, T["ink"], 500),
                      txt("no Admin, three client PCs, two unaddressed reports", 12.5, T["danger"]),
                      gap=10)),
        row(txt("Approving 1.4.3 stays blocked until both confirm.", 13, T["dim"]),
            f'<span style="flex: 1;"></span>',
            f'<span style="display: inline-flex; align-items: center; height: 34px; padding: 0 16px; '
            f'border-radius: 10px; background: {T["accent_soft"]}; color: {T["accent"]}; '
            f'font-family: {T["sans"]}; font-size: 13px; font-weight: 500;">Prompt their Admins</span>',
            f'<span style="display: inline-flex; align-items: center; height: 34px; padding: 0 16px; '
            f'border-radius: 10px; color: {T["dim"]}; font-family: {T["sans"]}; font-size: 13px;">'
            f'Open Updates</span>', gap=12, extra="width: 100%; padding-top: 18px;"),
        gap=0, extra=f"width: 100%; padding: 4px 0 26px;")

    after = [statement(t, s, src, last=(i == len(WATCH[2:]) - 1))
             for i, (t, s, src) in enumerate(WATCH[2:])]
    return watch_page([before, opened, evidence, *after],
                      "H02 · The same page, one statement opened. The evidence unfolds in place and pushes "
                      "the rest down; nothing is covered and closing it restores the page exactly.",
                      brow=eyebrow("PAGE", "Overview — a statement opened", "why it concluded that"))


# ------------------------------------------------------------------ H03: what moves
MOTION = [
    ("The evidence unfolds", "height nothing to its own, 220ms, easing out. The statements below are "
                             "pushed down — never covered, so you keep your place on the page."),
    ("The chevron turns", "a quarter turn over 160ms. It is the only thing on the page that rotates."),
    ("The line lightens", "the statement you are pointing at lifts to the pane tone over 120ms. "
                          "Nothing else on the row moves."),
    ("A figure counts once", "on first paint, 400ms, and never again. A number that re-animates on "
                             "every refresh is a number nobody ends up trusting."),
    ("A verdict settles", "when a statement changes how it stands, its word crossfades over 300ms "
                          "where it already is. It never slides in from somewhere else."),
    ("Nothing else moves", "no shimmer, no pulse, no skeleton wave, no entrance on scroll. The page "
                           "is still until it is touched."),
]


def h03():
    principle = col(txt("Motion is for continuity, never for attention.", 26, T["ink"], 600,
                        extra="line-height: 1.25; max-width: 640px;"),
                    txt("Everything that moves is answering something the person just did. Nothing moves "
                        "to be noticed — a page that moves on its own is a page you cannot read while it "
                        "is moving.", 14, T["dim"], extra="line-height: 1.55; max-width: 640px;"),
                    gap=14, extra="width: 100%; padding: 26px 0 28px; flex: none;")
    rows_ = [col(row(col(txt(k, 15, T["ink"], 500), gap=0, extra="width: 260px; flex: none;"),
                     txt(v, 13, T["faint"], extra="line-height: 1.5; flex: 1; max-width: 640px;"),
                     gap=28, align="flex-start", extra="width: 100%; padding: 17px 0;"),
                 "" if i == len(MOTION) - 1 else
                 f'<span style="display: block; height: 1px; background: {T["line"]}; width: 100%;"></span>',
                 gap=0, extra="width: 100%;")
             for i, (k, v) in enumerate(MOTION)]
    return watch_page([principle, *rows_],
                      "H03 · The six things that move, and the one rule behind them.",
                      brow=eyebrow("SYSTEM", "micro-interaction, everywhere", "the Overview first"))


OVERVIEW_TAKES = [("H01-Watch.dc.html", "Overview: the watch", h01),
                  ("H02-Opened.dc.html", "Overview: a statement opened", h02),
                  ("H03-Motion.dc.html", "What moves, and why", h03)]
