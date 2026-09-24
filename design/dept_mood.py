# ================================================================== The department mood board, DP01-DP04
# Super User got S01-S04, the Admin console got M01-M15. The department never got one -- which is why
# the first attempts at it went straight to finished pages and mixed a level below into them.
#
# Same format as the others: one facet per board, two sections, four approaches side by side at the
# same size, captioned so a pick can be named. Nothing here is a finished screen.
#
# DEPARTMENT LEVEL ONLY. A department is a place you look at: its Admins, its client PCs, its day,
# and what waits on you. Choosing whom to enter happens here; being inside does not. No lid, no
# countdown, no rail of someone else's -- that is the level below and it has its own screens already.

DP_CW, DP_CH = 316, 240          # mood-board cell, as M01-M15 and S01-S04 use it (charts.py rebinds CW/CH)


def dp_cell(name, html, note="", h=None):
    box = (f'<div style="width: {DP_CW}px; height: {h or DP_CH}px; box-sizing: border-box; border-radius: 12px; '
           f'background: {T["pane"]}; padding: 16px; overflow: hidden; position: relative; display: flex; '
           f'flex-direction: column; gap: 10px;">{html}</div>')
    return col(row(txt(name, 12.5, "#fff", 600), txt(note, 11.5, T["frame_faint"]) if note else "", gap=8), box, gap=6)


DP_FRAME = "#171528"          # the gradient, standing in, so a wireframe reads as a window
DP_W, DP_H = 284, 150


def dp_box(x, y, w, h, fill=None, label="", lc=None, ring=None):
    t = (f'<span style="position: absolute; left: 7px; top: 5px; font-family: {T["sans"]}; font-size: 9.5px; '
         f'font-weight: 500; color: {lc or T["faint"]};">{label}</span>') if label else ""
    r = f"box-shadow: inset 0 0 0 1px {ring};" if ring else ""
    return (f'<div style="position: absolute; left: {x}px; top: {y}px; width: {w}px; height: {h}px; '
            f'border-radius: 7px; background: {fill or T["ground"]}; {r}">{t}</div>')


def dp_wire(*boxes, w=DP_W, h=DP_H, rail=True):
    """A page, sketched. The rail is drawn only so the proportions read as a real window."""
    inner = "".join(boxes)
    r = (f'<div style="position: absolute; left: 0; top: 0; width: 20px; height: {h}px; border-radius: 7px 0 0 7px; '
         f'background: rgba(255,255,255,0.06);"></div>') if rail else ""
    return (f'<div style="position: relative; width: {w}px; height: {h}px; border-radius: 9px; '
            f'background: {DP_FRAME}; overflow: hidden;">{r}{inner}</div>')


def dp_slots(states, size=26, gap=5, faded=0):
    """Client PCs as slots, the department's own unit of counting."""
    out = []
    for i, st in enumerate(states):
        out.append(f'<span style="width: {size}px; height: {size}px; border-radius: {int(size / 3)}px; '
                   f'background: {ST[st] if st else T["line"]}; opacity: {0.45 if st is None else 0.9}; '
                   f'display: inline-block;"></span>')
    for _ in range(faded):
        out.append(f'<span style="width: {size}px; height: {size}px; border-radius: {int(size / 3)}px; '
                   f'background: {T["line"]}; opacity: 0.4; display: inline-block;"></span>')
    return row(*out, gap=gap, extra="flex: none;")


def dp_line(label, right, tone=None, lead=""):
    return row(lead, txt(label, 12, T["dim"]), sp(), txt(right, 11.5, tone_c(tone, T["faint"]), 600),
               gap=8, extra=f"width: 100%; padding: 7px 0; border-bottom: 1px solid {T['line']};")


# ------------------------------------------------------------------ DP01: the shape of a department screen
def dp01():
    # A. the colonnade: one column per Admin over a shared floor
    a = dp_cell("Colonnade", dp_wire(dp_box(28, 10, 118, 62, label="Admin"), dp_box(154, 10, 118, 62, label="Admin"),
                                  dp_box(28, 80, 166, 58, label="the day"), dp_box(202, 80, 70, 58, label="waits")),
             "people first")
    # B. floor first: the day is the spine, people hang off it
    b = dp_cell("Floor first", dp_wire(dp_box(28, 10, 244, 66, label="the day, every machine"),
                                    dp_box(28, 84, 78, 54, label="Admin"), dp_box(112, 84, 78, 54, label="Admin"),
                                    dp_box(196, 84, 76, 54, label="waits")),
             "what happened, first")
    # C. the roster: the machines are the subject, the Admins a header
    c = dp_cell("Roster", dp_wire(dp_box(28, 10, 244, 26, label="2 Admins"),
                               *[dp_box(28, 44 + i * 18, 244, 14) for i in range(5)]),
             "machines are the subject")
    # D. split: governance on one side, machines on the other
    d = dp_cell("Split", dp_wire(dp_box(28, 10, 116, 128, label="who governs"),
                              dp_box(152, 10, 120, 62, label="machines"),
                              dp_box(152, 80, 120, 58, label="waits")),
             "authority | machines")
    s1 = msection("The shape of a department screen", a, b, c, d)

    # where the Admins sit
    e = dp_cell("Columns", col(row(col(av("RM", "admin", 26), txt("R. Mensah", 11.5, T["dim"]), gap=6,
                                    extra=f"width: 128px; padding: 12px; border-radius: 10px; background: {T['ground']}; align-items: center;"),
                                col(av("AQ", "admin", 26), txt("A. Quaye", 11.5, T["dim"]), gap=6,
                                    extra=f"width: 128px; padding: 12px; border-radius: 10px; background: {T['ground']}; align-items: center;"),
                                gap=12), gap=0), "side by side, equal")
    f = dp_cell("Header band", col(row(av("RM", "admin", 24), txt("R. Mensah", 12, T["ink"], 600), sp(),
                                    txt("4 PCs", 11.5, T["faint"]), gap=8,
                                    extra=f"width: 100%; padding: 9px 11px; border-radius: 9px; background: {T['ground']}; box-sizing: border-box;"),
                                row(av("AQ", "admin", 24), txt("A. Quaye", 12, T["ink"], 600), sp(),
                                    txt("3 PCs", 11.5, T["faint"]), gap=8,
                                    extra=f"width: 100%; padding: 9px 11px; border-radius: 9px; background: {T['ground']}; box-sizing: border-box;"),
                                gap=8), "one line each, over the page")
    g = dp_cell("Ledger", col(ledger("R. Mensah", "WS-OPS-A1", "4 PCs"), ledger("A. Quaye", "helping Finance", "3 PCs"),
                           gap=0), "editorial, no cards")
    h = dp_cell("On the machines", col(*[row(dp_slots([s]), txt(host, 11.5, T["dim"], mono=True), sp(),
                                          txt(who, 11, T["faint"]), gap=8, extra="width: 100%; padding: 4px 0;")
                                      for host, s, who in [("OPS-01", "confirmed", "R. Mensah"),
                                                           ("OPS-04", "confirmed", "A. Quaye"),
                                                           ("OPS-06", "behind", "R. Mensah")]], gap=2),
             "the Admin is a property of the PC")
    s2 = msection("Where the Admins sit", e, f, g, h)
    return board("A department: the shape", s1, s2)


# ------------------------------------------------------------------ DP02: one Admin, drawn
def dp02():
    a = dp_cell("Station", col(row(av("RM", "admin", 30), col(txt("R. Mensah", 12.5, T["ink"], 600),
                                                           txt("WS-OPS-A1", 11, T["faint"], mono=True), gap=1), gap=9),
                            dp_slots(["confirmed", "confirmed", "confirmed", "behind"], 30, 6),
                            txt("Four machines, one behind.", 11.5, T["dim"]), gap=12), "person, then their machines")
    b = dp_cell("Ledger line", col(ledger("R. Mensah", "at their workstation", "4 PCs"),
                                ledger("A. Quaye", "helping Finance", "3 PCs"), gap=0), "quietest")
    c = dp_cell("Figures", col(row(figure("4", "machines", size=30), figure("8", "tasks", size=30),
                                figure("2", "pings", size=30, tone="warn"), gap=18),
                            txt("R. Mensah · WS-OPS-A1", 11.5, T["faint"]), gap=14), "numbers first")
    d = dp_cell("Portrait", col(row(av("RM", "admin", 40), col(txt("R. Mensah", 13, T["ink"], 600),
                                                            row(sicon("native", 12), txt("At their workstation", 11, T["faint"]), gap=5),
                                                            gap=3), gap=11),
                             rule(), row(txt("Operations", 11.5, T["faint"]), sp(),
                                         txt("since 08:14", 11, T["faint"], mono=True), gap=6, extra="width: 100%;"),
                             gap=11), "who, before what")
    s1 = msection("One Admin, drawn four ways", a, b, c, d)

    e = dp_cell("Their machines", col(txt("Governs", 11, T["faint"]),
                                   dp_slots(["confirmed", "confirmed", "confirmed", "behind"], 32, 7),
                                   txt("against the largest here", 11, T["faint"]), gap=9), "slots, sized to the biggest")
    f = dp_cell("Their work", col(health_line("Tasks", [("confirmed", 5), ("behind", 2), ("failing", 1)], w=252),
                               health_line("Flows", [("confirmed", 3), ("failing", 1)], w=252), gap=14), "two bars")
    g = dp_cell("One sentence", col(txt("OPS-06 has been behind since Friday.", 13, T["ink"], 600,
                                     extra="line-height: 1.4;"),
                                 txt("generated, never written", 11, T["faint"]), gap=10), "words only")
    h = dp_cell("State word", col(row(sicon("native", 14), txt("At their workstation", 12, T["dim"]), gap=7),
                               row(sicon("assisted", 14), txt("Helping Finance", 12, T["dim"]), gap=7),
                               row(sicon("free", 14), txt("Free", 12, T["faint"]), gap=7), gap=11),
             "an icon and a word, no colour on the person")
    s2 = msection("What is said about them", e, f, g, h)
    return board("A department: its people", s1, s2)


# ------------------------------------------------------------------ DP03: its machines
def dp03():
    seven = ["confirmed", "confirmed", "confirmed", "behind", "confirmed", "confirmed", "failing"]
    a = dp_cell("Grouped by Admin", col(txt("R. Mensah", 11, T["faint"]),
                                     dp_slots(seven[:4], 28, 6),
                                     txt("A. Quaye", 11, T["faint"]),
                                     dp_slots(seven[4:], 28, 6), gap=7), "who answers for which")
    b = dp_cell("One waffle", col(dp_slots(seven, 30, 7),
                               txt("the department, one square each", 11, T["faint"]), gap=12), "the department as one set")
    c = dp_cell("Day lanes", col(*[row(txt(h_, 10.5, T["faint"], mono=True, extra="width: 46px;"),
                                    f'<div style="flex: 1; height: 9px; border-radius: 5px; background: {T["line"]}; '
                                    f'position: relative;"><div style="position: absolute; left: {l}%; width: {w_}%; '
                                    f'height: 9px; border-radius: 5px; background: {c_};"></div></div>', gap=7,
                                    extra="width: 100%; padding: 3px 0;")
                                for h_, l, w_, c_ in [("OPS-01", 6, 62, T["line2"]), ("OPS-03", 18, 44, T["line2"]),
                                                      ("OPS-04", 10, 70, T["line2"]), ("OPS-06", 0, 0, T["line2"]),
                                                      ("OPS-07", 22, 50, T["line2"])]], gap=1),
             "when, not just what")
    d = dp_cell("Roster", col(*[dp_line(h_, w_, tone) for h_, w_, tone in
                             [("OPS-01", "confirmed", "ok"), ("OPS-06", "behind", "warn"),
                              ("OPS-07", "restricted file", "danger")]], gap=0), "a list, state in words")
    s1 = msection("The seven client PCs", a, b, c, d)

    e = dp_cell("Slot", col(dp_slots(["behind"], 44, 0),
                         txt("OPS-06", 12, T["ink"], 600, mono=True),
                         txt("behind since Friday", 11, T["faint"]), gap=9), "the unit everywhere else")
    f = dp_cell("With its Admin", col(row(dp_slots(["behind"], 32, 0),
                                       col(txt("OPS-06", 12, T["ink"], 600, mono=True),
                                           txt("R. Mensah answers for it", 11, T["faint"]), gap=2), gap=10),
                                   rule(), txt("Retrying 1.4.2, six attempts", 11.5, T["dim"]), gap=11),
             "never orphaned")
    g = dp_cell("Its day", col(txt("OPS-06", 12, T["ink"], 600, mono=True),
                            f'<div style="width: 100%; height: 12px; border-radius: 6px; background: {T["line"]};"></div>',
                            txt("never signed in today", 11.5, T["faint"]), gap=10), "one lane, read across")
    h = dp_cell("Figure", col(figure("6", "attempts", "OPS-06, 1.4.2", 34, "warn"), gap=8), "when one number is the point")
    s2 = msection("One machine", e, f, g, h)
    return board("A department: its machines", s1, s2)


# ------------------------------------------------------------------ DP04: the two doors
def dp04():
    """A department has exactly two doors: an Admin, and a client PC. This board is about getting to
    them and asking -- never about what is on the other side."""
    a = dp_cell("Opens in place", dp_wire(dp_box(28, 10, 174, 62, T["pane"], "Admin", T["ink"], ring=T["selectline"]),
                                       dp_box(210, 10, 62, 62), dp_box(28, 80, 244, 58)),
             "the cell grows where it stands")
    b = dp_cell("Detail lane", dp_wire(dp_box(28, 10, 158, 62, ring=T["selectline"]), dp_box(28, 80, 158, 58),
                                    dp_box(194, 10, 78, 128, T["pane"], "detail", T["ink"])),
             "selection explains itself on the right")
    c = dp_cell("Drill", dp_wire(dp_box(28, 8, 244, 16, T["ground"], "Everything › Operations › R. Mensah", T["dim"]),
                              dp_box(28, 32, 244, 106, T["pane"], "their page", T["ink"])),
             "a new page, a crumb back")
    d = dp_cell("Reveal", col(row(av("RM", "admin", 26), col(txt("R. Mensah", 12, T["ink"], 600),
                                                          txt("WS-OPS-A1", 10.5, T["faint"], mono=True), gap=1), sp(),
                               tbtn("Enter", "accent", "lock", "sm"), gap=9,
                               extra=f"width: 100%; padding: 10px; border-radius: 10px; background: {T['line']}; box-sizing: border-box;"),
                           txt("the act appears on hover, not before", 11, T["faint"]), gap=12),
             "quiet until you reach for it")
    s1 = msection("Choosing an Admin, or a client PC", a, b, c, d)

    e = dp_cell("In the cell", col(row(txt("R. Mensah", 12.5, T["ink"], 600), sp(), tbtn("Enter", "accent", "lock", "sm"), gap=8,
                                    extra="width: 100%;"),
                                txt("Blocks them for 30 minutes.", 11, T["faint"]), gap=10), "one press, said plainly")
    f = dp_cell("A confirm", col(col(txt("Enter WS-OPS-A1?", 12.5, T["ink"], 600),
                                  txt("R. Mensah is blocked until you leave.", 11, T["faint"], extra="line-height: 1.4;"),
                                  row(sp(), gbtn("Cancel", size="sm"), tbtn("Enter", "accent", size="sm"), gap=6,
                                      extra="width: 100%;"),
                                  gap=9, extra=f"width: 100%; padding: 12px; border-radius: 11px; background: {T['ground']}; "
                                               f"box-sizing: border-box; box-shadow: 0 8px 22px rgba(0,0,0,0.45);"), gap=0),
             "asked, then done")
    g = dp_cell("A reading", col(txt("Entering takes their workstation.", 12.5, T["ink"], 600, extra="line-height: 1.35;"),
                              dp_line("They get", "a red screen", "danger"), dp_line("Time", "30 minutes", "warn"),
                              row(sp(), tbtn("Enter", "accent", "lock", "sm"), gap=0, extra="width: 100%; padding-top: 6px;"),
                              gap=8), "the cost, then the act")
    h = dp_cell("Two doors, named", col(row(av("RM", "admin", 24), txt("Enter R. Mensah", 12, T["dim"]), sp(),
                                         ic("chev", 13, T["faint"]), gap=8, extra="width: 100%; padding: 7px 0;"),
                                     rule(),
                                     row(dp_slots(["behind"], 22, 0), txt("Enter OPS-06 directly", 12, T["dim"]), sp(),
                                         ic("chev", 13, T["faint"]), gap=8, extra="width: 100%; padding: 7px 0;"),
                                     txt("a Super User may do either", 11, T["faint"]), gap=6),
             "the PC is not only reachable through its Admin")
    s2 = msection("Asking to enter — the act, never what is behind it", e, f, g, h)
    return board("A department: the two doors", s1, s2)


DEPT_MOOD = [("DP01-Shape.dc.html", "Department: the shape", dp01),
             ("DP02-People.dc.html", "Department: its people", dp02),
             ("DP03-Machines.dc.html", "Department: its machines", dp03),
             ("DP04-Doors.dc.html", "Department: the two doors", dp04)]
