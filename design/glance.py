# ================================================================== G01-G03: At a glance, again
# The first composition of page 1 was four boxes with air in them: small charts parked in large
# containers, and no organising idea beyond "a band and two columns". These three each commit to
# one idea instead, and each fills the space it takes.
#
# All three keep the settled rules: the density never falls along the reading order, a zero is a
# result, the four toned meanings, no tables.

GLANCE_FIGURES = [("14", "client PCs", "across 3 departments", None),
                  ("12", "on 1.4.2", "2 still behind", "warn"),
                  ("2", "waiting on you", "approval, and an empty department", "danger"),
                  ("4", "traversals today", "1 still open", None)]


def gpanel(title, note, *children, w=None, h=None, grow=False, foot="", pad=18, bg=None):
    head = (row(txt(title, 13.5, T["ink"], 600), txt(note, 11.5, T["faint"]) if note else "", gap=10,
                extra="flex: none; width: 100%;") if title else "")
    body = (f'<div style="flex: 1; min-height: 0; display: flex; flex-direction: column; '
            f'justify-content: flex-start; overflow: hidden;">{"".join(children)}</div>')
    parts = ([head] if head else []) + [body] + ([foot] if foot else [])
    size = (f"width: {w}px; " if w else "") + (f"height: {h}px; " if h else "")
    return col(*parts, gap=12,
               extra=f"{size}padding: {pad}px; border-radius: 16px; background: {bg or CHART_BG}; "
                     f"box-sizing: border-box; {'flex: 1; min-width: 0;' if grow else 'flex: none;'}")


def gshell(title, sub, structure, note, brow=""):
    pills = row(*[f'<span style="display: inline-flex; align-items: center; height: 30px; padding: 0 15px; '
                  f'border-radius: 999px; background: {T["select"] if i == 0 else T["ground"]}; '
                  f'color: {"#fff" if i == 0 else T["dim"]}; font-family: {T["sans"]}; font-size: 13px; '
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


# ------------------------------------------------------------------ G01: three concerns
# Each column is one complete thought, and the density runs DOWN it rather than across the page:
# a figure, then the shape behind the figure, then the sentence. Three columns, no dead space,
# and each answers one question a Super User actually has.
def column_head(figure, label, sub, tone=None):
    return col(txt(figure, 40, tone_c(tone, T["ink"]), 600, mono=True, extra="line-height: 1;"),
               txt(label, 13, T["ink"], 600), txt(sub, 11.5, T["faint"]), gap=6,
               extra="flex: none; padding-bottom: 4px;")


def concern(title, figure, label, sub, tone, *body, foot="", w=436):
    return col(txt(title.upper(), 11, T["faint"], 600, extra="letter-spacing: 0.08em;"),
               column_head(figure, label, sub, tone),
               f'<span style="display: block; height: 1px; background: {T["line"]}; flex: none;"></span>',
               *body,
               (f'<span style="flex: 1;"></span>' + foot) if foot else "",
               gap=14, extra=f"width: {w}px; height: 100%; padding: 20px; border-radius: 16px; "
                             f"background: {CHART_BG}; box-sizing: border-box; flex: none; "
                             f"display: flex; flex-direction: column;")


def g01():
    rollout = concern(
        "The rollout", "12", "of 14 on 1.4.2", "approved Monday", "warn",
        stacked_bars([(n, [("confirmed", a), ("behind", b), ("failing", f)]) for n, a, b, f in ROLLOUT], w=396),
        col(txt("The fleet", 11.5, T["faint"]), waffle(FLEET, cols=7, size=26, gap=7, w=232), gap=8),
        foot=col(txt("2 PCs are behind, so 1.4.3 stays blocked.", 12.5, T["ink"], 500),
                 legend([("Confirmed", ST["confirmed"]), ("Behind", ST["behind"]), ("Failing", ST["failing"])]),
                 gap=10))

    work = concern(
        "The work", "24", "tasks and flows", "across three departments", None,
        col(*[row(col(row(swatch(DEPT_COLOR[n], "dot"), txt(n, 12.5, T["ink"], 600), gap=7),
                      health_line("Tasks", list(zip(WORK_TONES, t)), w=380),
                      health_line("Flows", list(zip(WORK_TONES, f)), w=380), gap=9,
                      extra="width: 100%;"), gap=0, extra="width: 100%; padding: 10px 0;")
              for n, (t, f) in WORK.items()], gap=0, extra="width: 100%;"),
        foot=col(txt("Logistics has three tasks overdue and no flows.", 12.5, T["ink"], 500),
                 legend([("On track", ST["confirmed"]), ("Needs attention", ST["behind"]), ("Overdue", ST["failing"])]),
                 gap=10))

    attention = concern(
        "What needs you", "2", "waiting on you", "and nothing else is overdue", "danger",
        col(*[row(f'<span style="width: 8px; height: 8px; border-radius: 4px; background: {tone_c(tone, T["dim"])}; '
                  f'flex: none;"></span>',
                  col(txt(k, 12.5, T["ink"], 500), txt(v, 11.5, T["faint"]), gap=2, extra="flex: 1;"),
                  gap=11, extra="width: 100%; padding: 11px 0; border-bottom: 1px solid " + T["line"] + ";")
              for k, v, tone in
              [("Logistics has no Admin", "three client PCs answer to nobody below you", "danger"),
               ("LOG-02 has failed six times", "last attempt 09:12 today", "danger"),
               ("OPS-06 is retrying", "behind since Monday", "warn"),
               ("budget-2026.xlsx", "restricted, found in /workers/ on OPS-07", "warn")]],
            gap=0, extra="width: 100%;"),
        foot=row(f'<span style="display: inline-flex; align-items: center; height: 32px; padding: 0 14px; '
                 f'border-radius: 9px; background: {T["accent_soft"]}; color: {T["accent"]}; '
                 f'font-family: {T["sans"]}; font-size: 12.5px; font-weight: 500;">Assign an Admin</span>',
                 f'<span style="display: inline-flex; align-items: center; height: 32px; padding: 0 14px; '
                 f'border-radius: 9px; color: {T["dim"]}; font-family: {T["sans"]}; font-size: 12.5px;">'
                 f'Prompt their Admins</span>', gap=8))

    body = row(rollout, work, attention, gap=16, align="stretch", extra="height: 716px;")
    return gshell("Everything", "3 departments · 3 Admins · 14 client PCs", body,
                  "G01 · Three concerns. Each column is one complete thought and the density runs DOWN it — "
                  "figure, then the shape behind the figure, then the sentence.",
                  brow=eyebrow("PAGE", "page 1 — At a glance, take two", "three concerns"))


# ------------------------------------------------------------------ G02: one picture
# The fleet is the page. Every client PC is a mark, grouped under its department and coloured by
# where it is in the rollout, filling two thirds of the screen. The figures stack down the left as
# a spine, and the words sit under the picture. "The system, in one object."
def big_fleet(w=880, size=76, gap=16, per_row=7):
    groups = [("Operations", [("confirmed", f"OPS-0{i+1}") for i in range(6)] + [("behind", "OPS-06 retrying")]),
              ("Finance", [("confirmed", f"FIN-0{i+1}") for i in range(4)]),
              ("Logistics", [("confirmed", "LOG-01"), ("confirmed", "LOG-03"), ("failing", "LOG-02, 6 failures")])]
    blocks = []
    for name, cells in groups:
        marks = []
        for i, (state, label) in enumerate(cells):
            cx, cy = (i % per_row) * (size + gap), (i // per_row) * (size + gap)
            marks.append(f'<rect x="{cx}" y="{cy}" width="{size}" height="{size}" rx="14" fill="{ST[state]}">'
                         f'<title>{label}</title></rect>')
            host = label.split(",")[0].split(" ")[0]
            marks.append(f'<text x="{cx + size / 2}" y="{cy + size / 2 + 5}" text-anchor="middle" '
                         f'fill="{CHART_BG}" font-family="{T["mono"]}" font-size="14" font-weight="500">'
                         f'{host}</text>')
        rows_n = (len(cells) + per_row - 1) // per_row
        sw = min(per_row, len(cells)) * (size + gap) - gap
        sh = rows_n * (size + gap) - gap
        confirmed = sum(1 for st, _ in cells if st == "confirmed")
        head = row(f'<span style="width: 22px; height: 3px; border-radius: 2px; '
                   f'background: {DEPT_COLOR[name]};"></span>',
                   txt(name, 13, T["dim"]),
                   f'<span style="flex: 1;"></span>',
                   txt(f"{confirmed} of {len(cells)} confirmed", 11.5, T["faint"]),
                   gap=9, extra="width: 100%;")
        blocks.append(col(head,
                          f'<svg width="{sw}" height="{sh}" viewBox="0 0 {sw} {sh}">{"".join(marks)}</svg>',
                          gap=12, extra="flex: none; width: 100%;"))
    return col(*blocks, gap=26, extra="flex: none; width: 100%;")


def g02():
    spine = col(*[col(txt(v, 34, tone_c(tone, T["ink"]), 600, mono=True, extra="line-height: 1;"),
                      txt(label, 12.5, T["dim"], 500), txt(sub, 11, T["faint"]), gap=5,
                      extra="width: 100%; padding: 16px 0; border-bottom: 1px solid " + T["line"] + ";")
                  for v, label, sub, tone in GLANCE_FIGURES],
                gap=0, extra="width: 100%;")

    left = gpanel("", "", spine, w=268, grow=False,
                  foot=col(txt("Everything is one version behind approval.", 12, T["ink"], 500),
                           gap=0, extra="padding-top: 10px;"))
    left = col(left, gap=0, extra="height: 100%; display: flex; flex-direction: column;")

    picture = gpanel("The fleet", "every client PC, grouped by department, coloured by the rollout",
                     big_fleet(), grow=True,
                     foot=col(row(legend([("Confirmed", ST["confirmed"]), ("Behind", ST["behind"]),
                                          ("Failing", ST["failing"])]), gap=0),
                              txt("12 of 14 are on 1.4.2. LOG-02 has failed six times and sits in a "
                                  "department with no Admin.", 13, T["ink"], 500),
                              gap=12))

    body = row(left, picture, gap=16, align="stretch", extra="height: 716px;")
    return gshell("Everything", "3 departments · 3 Admins · 14 client PCs", body,
                  "G02 · One picture. The fleet is the page — every PC is a mark you could point at — "
                  "with the figures as a spine and the words under the picture.",
                  brow=eyebrow("PAGE", "page 1 — At a glance, take two", "one picture"))


# ------------------------------------------------------------------ G03: the finding first
# The page's title IS the finding, stated once and large. Under it a strip of four small charts,
# all the same size, each captioned with the one line it is making: the evidence for the title.
# Calmer and more editorial, and it puts the answer where the eye lands first.
def evidence(title, chart, line, w=316):
    return col(txt(title, 11.5, T["faint"], 600, extra="letter-spacing: 0.06em;"),
               f'<div style="flex: 1; min-height: 0; display: flex; align-items: center;">{chart}</div>',
               txt(line, 13, T["ink"], 500, extra="line-height: 1.35;"),
               gap=12, extra=f"width: {w}px; height: 100%; padding: 20px; border-radius: 16px; "
                             f"background: {CHART_BG}; box-sizing: border-box; flex: none; "
                             f"display: flex; flex-direction: column;")


def g03():
    finding = col(txt("Two PCs are behind, so 1.4.3 stays blocked.", 34, T["ink"], 600,
                      extra="line-height: 1.25;"),
                  txt("And Logistics has no Admin, so three client PCs answer to nobody below you.",
                      15, T["dim"], extra="line-height: 1.4;"),
                  row(f'<span style="display: inline-flex; align-items: center; height: 34px; padding: 0 16px; '
                      f'border-radius: 10px; background: {T["accent_soft"]}; color: {T["accent"]}; '
                      f'font-family: {T["sans"]}; font-size: 13px; font-weight: 500;">Assign an Admin</span>',
                      f'<span style="display: inline-flex; align-items: center; height: 34px; padding: 0 16px; '
                      f'border-radius: 10px; color: {T["dim"]}; font-family: {T["sans"]}; font-size: 13px;">'
                      f'Prompt their Admins</span>', gap=10, extra="padding-top: 6px;"),
                  gap=16, extra=f"width: 100%; padding: 30px 32px; border-radius: 16px; background: {CHART_BG}; "
                                f"box-sizing: border-box; flex: none;")

    strip = row(evidence("ROLLOUT",
                         stacked_bars([(n, [("confirmed", a), ("behind", b), ("failing", f)])
                                       for n, a, b, f in ROLLOUT], w=280, bar_h=14, gap_y=22),
                         "Logistics is the only one failing."),
                evidence("THE FLEET", waffle(FLEET, cols=5, size=34, gap=9, w=206),
                         "12 of 14 have confirmed."),
                evidence("CONFIRMATIONS", trend(SERIES, w=280, h=110),
                         "Nothing has confirmed since Friday."),
                evidence("WORK",
                         col(*[health_line(n, list(zip(WORK_TONES, t)), w=280) for n, (t, _f) in WORK.items()],
                             gap=10),
                         "Three tasks are overdue, all in Logistics."),
                gap=16, align="stretch", extra="flex: 1; min-height: 0;")

    quiet = row(*[row(f'<span style="width: 8px; height: 8px; border-radius: 4px; background: {T["line2"]}; '
                      f'flex: none;"></span>', txt(t, 12, T["faint"]), gap=9)
                  for t in ["4 traversals today, one still open", "No cross-department help today",
                            "One violation, on OPS-07", "One deviation still unaddressed"]],
                gap=34, extra=f"width: 100%; padding: 16px 22px; border-radius: 16px; background: {CHART_BG}; "
                              f"box-sizing: border-box; flex: none;")

    body = col(finding, strip, quiet, gap=16,
               extra="height: 716px; display: flex; flex-direction: column;")
    return gshell("Everything", "3 departments · 3 Admins · 14 client PCs", body,
                  "G03 · The finding first. The answer is stated once and large, the four small charts "
                  "under it are the evidence, and everything quiet is one line at the foot.",
                  brow=eyebrow("PAGE", "page 1 — At a glance, take two", "the finding first"))


GLANCE_TAKES = [("G01-Concerns.dc.html", "At a glance: three concerns", g01),
                ("G02-Picture.dc.html", "At a glance: one picture", g02),
                ("G03-Finding.dc.html", "At a glance: the finding first", g03)]
