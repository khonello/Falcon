# ================================================================== Super User: a different instrument
# The Admin console is for operating. This is for governing: scale, authority, descent, record.
# Four boards, each one component-and-idea in several approaches.

SEAL = "#B92828"          # the one colour only Super User's own acts wear
SEAL_SOFT = "rgba(185,40,40,0.16)"


def rule(w="100%", c=None, h=1):
    return f'<div style="width: {w}; height: {h}px; background: {c or T["line"]};"></div>'


def figure(n, label, sub="", size=54, tone=None):
    return col(txt(n, size, tone_c(tone, T["ink"]), 600, mono=True, extra="line-height: 1;"),
               txt(label, 12.5, T["dim"], 500), txt(sub, 11.5, T["faint"]) if sub else "",
               gap=6)


def ledger(name, meta, value, tone=None, seal=False):
    dots = f'<div style="flex: 1; border-bottom: 1px dotted {T["line2"]}; margin: 0 10px 5px;"></div>'
    mark = f'<span style="display: inline-flex; align-items: center; gap: 5px; padding: 2px 8px; border-radius: 999px; background: {SEAL_SOFT}; color: {SEAL}; font-size: 11px; font-weight: 600;">{ic("shield", 11, SEAL)}yours</span>' if seal else ""
    return row(col(txt(name, 13.5, weight=500), txt(meta, 11.5, T["faint"]) if meta else "", gap=1),
               dots, mark, txt(value, 13, tone_c(tone, T["dim"]), 500, mono=True),
               gap=0, align="flex-end", extra="padding: 9px 0;")


# ------------------------------------------------------------------ S01: the shape of the screen
def s01():
    # A. the console we have
    console = col(row(f'<div style="width: 64px; height: 150px; border-radius: 8px; background: {T["side_native"]};"></div>',
                      col(row(f'<div style="height: 14px; width: 90px; border-radius: 4px; background: {T["line"]};"></div>', gap=0),
                          row(*[f'<div style="width: 54px; height: 34px; border-radius: 8px; background: {T["ground"]};"></div>' for _ in range(3)], gap=6),
                          *[f'<div style="height: 20px; border-radius: 6px; background: {T["ground"]};"></div>' for _ in range(3)],
                          gap=7, extra="flex: 1;"),
                      f'<div style="width: 74px; height: 150px; border-radius: 10px; background: {T["pane"]}; box-shadow: 0 0 0 1px {T["line"]};"></div>',
                      gap=8, align="flex-start"), gap=0)
    a = cell("Console", console, "what we have: the Admin shape")

    # B. the ledger: no sidebar, editorial, figures do the talking
    led = col(txt("Everything", 26, weight=700, extra="letter-spacing: -0.4px;"),
              txt("3 departments  ·  3 Admins  ·  14 client PCs", 12, T["faint"]),
              rule(c=T["line2"]),
              col(ledger("Operations", "R. Mensah, A. Quaye", "7 PCs"),
                  ledger("Finance", "K. Boateng", "4 PCs"),
                  ledger("Logistics", "no Admin", "3 PCs", "danger", seal=True), gap=0),
              gap=10)
    b = cell("Ledger", led, "editorial, figure-led")

    # C. the situation board: wide bands, authority inline
    band = lambda name, meta, act, tone=None: row(col(txt(name, 14, weight=600), txt(meta, 11.5, T["faint"]), gap=2, extra="flex: 1;"),
                                                  (f'<span style="padding: 4px 11px; border-radius: 999px; background: {SEAL_SOFT}; color: {SEAL}; font-size: 11.5px; font-weight: 600;">{act}</span>' if act else ""),
                                                  gap=8, extra=f"padding: 12px 14px; border-radius: 12px; background: {T['ground']}; box-shadow: inset 0 0 0 1px {SEAL if tone else 'transparent'};")
    c = cell("Situation", col(band("Operations", "86 % on 1.4.2", ""), band("Finance", "all confirmed", ""),
                              band("Logistics", "no Admin since Friday", "assign", True), gap=8))

    # D. planes: descent is the interface
    plane = lambda x, y, w, o, label: (f'<div style="position: absolute; left: {x}px; top: {y}px; width: {w}px; height: 96px; border-radius: 12px; '
                                       f'background: {T["ground"]}; box-shadow: 0 8px 20px rgba(0,0,0,0.45), inset 0 0 0 1px {T["line"]}; opacity: {o}; '
                                       f'display: flex; align-items: flex-start; padding: 10px 12px; box-sizing: border-box;">{txt(label, 12.5, T["dim"], 600)}</div>')
    d = cell("Planes", f'<div style="position: relative; width: 284px; height: 150px;">'
             + plane(0, 0, 220, 0.45, "Everything") + plane(24, 22, 230, 0.7, "Operations") + plane(48, 44, 236, 1, "R. Mensah")
             + "</div>", "entering pushes a plane")
    s1 = msection("The shape of a Super User screen", a, b, c, d)

    # navigation
    rail = f'<div style="width: 56px; height: 132px; border-radius: 10px; background: {FRAME["native"]};"></div>'
    e = cell("Icon rail", row(rail, col(txt("same as Admin", 12, T["faint"]), gap=0), gap=12), "what we have")
    ladder = col(*[row(txt(t, 13 if on else 12.5, T["ink"] if on else T["faint"], 700 if on else 400), gap=6,
                       extra=f"padding: 7px 0; border-bottom: 1px solid {T['line']};") for t, on in
                   [("Everything", True), ("Departments", False), ("Views", False), ("Updates", False), ("The record", False)]], gap=0)
    f = cell("Index", ladder, "a text index, no icons")
    top = col(row(*[txt(t, 12.5, T["ink"] if i == 0 else T["faint"], 600 if i == 0 else 400, extra=f"padding: 6px 12px; border-radius: 999px; background: {T['ground'] if i == 0 else 'transparent'};")
                    for i, t in enumerate(["Everything", "Views", "Updates", "Record"])], gap=6), gap=10)
    g = cell("Top ladder", col(top, rule(), gap=10), "one line, then the page")
    h = cell("Palette only", col(row(ic("search", 15, T["faint"]), txt("Go anywhere", 13, T["dim"]), sp(), txt("Ctrl K", 11, T["faint"], mono=True), gap=8,
                                     extra=f"padding: 10px 12px; border-radius: 10px; background: {T['ground']};"),
                                 txt("Navigation is typing. The page is only the thing you asked for.", 12, T["faint"], extra="line-height: 1.5;"), gap=10))
    s2 = msection("Navigation", e, f, g, h)
    return board("Super User: the shape", s1, s2)


# ------------------------------------------------------------------ S02: figures and the record
def s02():
    a = cell("Display figures", row(figure("14", "client PCs", "across 3 departments"), figure("12", "on 1.4.2", "2 behind", "warn"), gap=28))
    b = cell("Ledger", col(ledger("Operations", "", "7"), ledger("Finance", "", "4"), ledger("Logistics", "", "3", "danger"), gap=0))
    c = cell("Stat band", col(rule(), row(figure("3", "departments", size=30), figure("14", "PCs", size=30), figure("2", "waiting on you", size=30, tone="danger"), gap=26, extra="padding: 14px 0;"), rule(), gap=0))
    d = cell("Figure and trend", col(row(figure("86", "% on 1.4.2", size=38), sp(),
                                         f'<svg width="120" height="40" viewBox="0 0 120 40"><polyline points="0,34 20,30 40,26 60,18 80,14 100,9 120,6" fill="none" stroke="{T["ok"]}" stroke-width="1.75"/></svg>', gap=10, align="flex-end"),
                                     txt("since Monday", 11.5, T["faint"]), gap=8))
    s1 = msection("Scale, said with figures", a, b, c, d)

    e = cell("Audit lines", col(*[row(txt(t, 11.5, T["faint"], mono=True, extra="width: 46px;"), txt(w, 12, T["dim"], 600, mono=True, extra="width: 34px;"), txt(x, 12.5, extra="flex: 1;"), gap=8)
                                 for t, w, x in [("10:41", "SU", "entered OPS-04 via R. Mensah"), ("10:20", "RM", "entered OPS-04"), ("09:31", "AQ", "assisted Finance"), ("08:00", "SU", "approved 1.4.2")]], gap=9), "log-like, mono")
    f = cell("Ledger record", col(ledger("You entered OPS-04", "through R. Mensah", "21 min", seal=True), ledger("R. Mensah entered OPS-04", "still inside", "21:18", "warn"), ledger("A. Quaye assisted Finance", "by consent", "29 min"), gap=0))
    g = cell("Hairline timeline", col(*[row(txt(t, 11, T["faint"], mono=True, extra="width: 42px; text-align: right;"),
                                            col(dot(tone_c(tone, T["line2"]), 8), f'<div style="width: 1px; flex: 1; background: {T["line"]}; margin: 2px 0;"></div>' if i < 2 else "", gap=0, extra="align-items: center; align-self: stretch;"),
                                            col(txt(x, 12.5), txt(s_, 11.5, T["faint"]), gap=1, extra="padding-bottom: 14px;"), gap=10, align="flex-start")
                                        for i, (t, x, s_, tone) in enumerate([("10:41", "You entered OPS-04", "21 min", None), ("10:20", "R. Mensah entered", "still inside", "warn"), ("08:00", "You approved 1.4.2", "14 PCs", None)])], gap=0))
    h = cell("Day ledger", col(txt("Today", 11.5, T["faint"], 600), rule(), ledger("Traversals", "", "4"), ledger("Assisted sessions", "", "2"), ledger("Deviations", "", "1", "warn"), gap=6))
    s2 = msection("The record", e, f, g, h)
    return board("Super User: figures and the record", s1, s2)


# ------------------------------------------------------------------ S03: authority, and where red belongs
def s03():
    seal_mark = (f'<span style="width: 58px; height: 58px; border-radius: 29px; box-shadow: inset 0 0 0 2px {SEAL}; background: {SEAL_SOFT}; '
                 f'display: inline-flex; align-items: center; justify-content: center;">{ic("shield", 24, SEAL)}</span>')
    a = cell("The seal", col(row(seal_mark, col(txt("Approved by you", 13.5, weight=600), txt("1.4.2, Monday 08:00", 12, T["faint"]), gap=3), gap=14),
                             txt("Only your own acts wear this.", 12, T["faint"]), gap=12))
    b = cell("Approval bar", col(row(col(txt("1.4.3 waits for you", 13.5, weight=600), txt("12 of 14 PCs confirmed 1.4.2", 12, T["faint"]), gap=2, extra="flex: 1;"),
                                     f'<span style="padding: 6px 13px; border-radius: 9px; background: {SEAL_SOFT}; color: {SEAL}; font-size: 12.5px; font-weight: 600;">Approve</span>', gap=10,
                                     extra=f"padding: 13px 14px; border-radius: 12px; background: {T['ground']}; box-shadow: inset 0 0 0 1px {SEAL};"), gap=0))
    c = cell("Gate", col(row(ic("lock", 15, SEAL), txt("Blocked until all 14 confirm", 12.5, T["dim"]), gap=9,
                             extra=f"padding: 11px 13px; border-radius: 10px; background: {T['ground']};"),
                         row(txt("Approve 1.4.3", 13, T["faint"], 600, extra=f"padding: 7px 13px; border-radius: 9px; background: {T['line']}; opacity: 0.6;"), gap=6), gap=10), "the refusal states the rule")
    d = cell("Signature", col(rule(c=SEAL, h=2), row(txt("Approved", 13, weight=700), txt("Super User, Monday 08:00", 12, T["faint"]), gap=10, extra="padding-top: 8px;"),
                              txt("An act of authority reads like a signed line.", 11.5, T["faint"]), gap=6))
    s1 = msection("Authority", a, b, c, d)

    e = cell("Red dot", col(*[row(txt(t, 12.5, extra="flex: 1;"), (dot(SEAL, 7) if r else ""), gap=8, extra="padding: 7px 0;") for t, r in
                              [("Departments", False), ("Views", True), ("Updates", True), ("The record", False)]], gap=0), "where you are needed")
    f = cell("Red count", col(*[row(txt(t, 12.5, extra="flex: 1;"), (f'<span style="padding: 1px 8px; border-radius: 999px; background: {SEAL}; color: #fff; font-size: 11px; font-weight: 700;">{n}</span>' if n else ""), gap=8, extra="padding: 7px 0;")
                                for t, n in [("Departments", ""), ("Views", "2"), ("Updates", "1"), ("The record", "")]], gap=0))
    g = cell("Red heading", col(col(txt("Waiting on you", 12, SEAL, 700), rule(c=SEAL, h=2), gap=6), col(txt("Watching", 12, T["faint"], 600), rule(), gap=6), gap=16), "the section, not the row")
    h = cell("Red figure", col(row(figure("2", "waiting on you", size=42, tone="danger"), sp(), figure("12", "quiet", size=42), gap=10),
                               txt("Only the number that needs you is red.", 11.5, T["faint"]), gap=12))
    s2 = msection("Where red belongs", e, f, g, h)
    return board("Super User: authority and red", s1, s2)


# ------------------------------------------------------------------ S04: descent
def s04():
    step = lambda t, s_, on: row(col(dot(SEAL if on else T["line2"], 9), f'<div style="width: 1px; height: 26px; background: {T["line"]}; margin: 3px auto;"></div>', gap=0, extra="align-items: center;"),
                                 col(txt(t, 13, T["ink"] if on else T["faint"], 600 if on else 400), txt(s_, 11.5, T["faint"]) if s_ else "", gap=1), gap=12, align="flex-start")
    a = cell("The ladder", col(step("Everything", "3 departments", False), step("Operations", "2 Admins", False), step("R. Mensah", "you are here", True), gap=0), "how deep you are, always")
    b = cell("Threshold", col(txt("You are entering", 12, T["faint"]), txt("R. Mensah’s view", 20, weight=700),
                              txt("Everything you do is logged as you. 30 minutes.", 12.5, T["dim"], extra="line-height: 1.5;"),
                              row(f'<span style="padding: 7px 14px; border-radius: 9px; background: {SEAL_SOFT}; color: {SEAL}; font-size: 13px; font-weight: 600;">Enter</span>',
                                  txt("Cancel", 13, T["dim"], extra="padding: 7px 12px;"), gap=8), gap=10), "a deliberate crossing")
    c = cell("Zoom", f'<div style="position: relative; width: 284px; height: 150px;">'
             f'<div style="position: absolute; inset: 0; border-radius: 12px; background: {T["ground"]}; opacity: 0.4;"></div>'
             f'<div style="position: absolute; left: 30px; top: 18px; right: 30px; bottom: 18px; border-radius: 12px; background: {T["ground"]}; box-shadow: inset 0 0 0 1px {T["line"]};"></div>'
             f'<div style="position: absolute; left: 62px; top: 38px; right: 62px; bottom: 38px; border-radius: 10px; background: {T["pane"]}; box-shadow: 0 8px 20px rgba(0,0,0,0.5);">'
             f'<div style="padding: 10px 12px;">{txt("OPS-04", 12.5, weight=600)}</div></div></div>', "the level opens inside the last")
    d = cell("Takeover", col(row(txt("Everything", 12, T["faint"]), ic("chev", 12, T["faint"]), txt("Operations", 12, T["faint"]), ic("chev", 12, T["faint"]), txt("R. Mensah", 12.5, weight=600), gap=5),
                             f'<div style="height: 84px; border-radius: 12px; background: {T["ground"]}; box-shadow: inset 0 0 0 1px {SEAL}; display: flex; align-items: center; justify-content: center;">{txt("his interface, whole", 12.5, T["dim"])}</div>',
                             txt("Inside, the screen is his. Only the ladder stays yours.", 11.5, T["faint"]), gap=10))
    s1 = msection("Entering", a, b, c, d)

    e = cell("Quiet chrome", col(row(txt("Everything", 13, weight=700), sp(), dot(SEAL, 7), txt("2", 12, SEAL, 600), gap=8),
                                 txt("No indicators, no strip, no live feed. What waits on you is one figure.", 12, T["faint"], extra="line-height: 1.5;"), gap=12))
    f = cell("One question", col(txt("Two things wait on your authority.", 14, weight=600, extra="line-height: 1.4;"),
                                 col(ledger("Approve 1.4.3", "12 of 14 confirmed", "open", seal=True), ledger("Logistics has no Admin", "since Friday", "open", "danger", seal=True), gap=0), gap=12))
    g = cell("Everything else, folded", col(*[row(txt(t, 12.5, T["dim"], extra="flex: 1;"), txt(v, 12, T["faint"], mono=True), ic("chev", 13, T["faint"]), gap=8, extra=f"padding: 10px 0; border-bottom: 1px solid {T['line']};")
                                              for t, v in [("Departments", "3"), ("The record", "24 h"), ("Views", "12"), ("Assistance", "2")]], gap=0), "one line each, until you open it")
    h = cell("Stillness", col(txt("Governance is not a dashboard.", 13.5, weight=600),
                              txt("Nothing here moves on its own. The page changes when you decide something, and the record notes that you did.", 12.5, T["faint"], extra="line-height: 1.6;"), gap=10))
    s2 = msection("Fewer distractions", e, f, g, h)
    return board("Super User: descent and stillness", s1, s2)


SU_MOOD = [("S01-Shape.dc.html", "Super User: the shape", s01), ("S02-Figures.dc.html", "Super User: figures and the record", s02),
           ("S03-Authority.dc.html", "Super User: authority and red", s03), ("S04-Descent.dc.html", "Super User: descent and stillness", s04)]
