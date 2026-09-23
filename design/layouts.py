# ================================================================== Layout structure boards, L01-L06
# The same Super User content, arranged six ways. These are about STRUCTURE, not about which chart:
# how many panels a page carries, how they are weighted, and what that does to what gets read first.
#
# Every board keeps the shell's header (breadcrumb, title, pills) so the structures are comparable
# as screens rather than as abstract grids. Content area: 1360 x 720 under a 100 px header.

LW, LH = 1360, 716          # the content area every structure divides up
LGAP = 16


def lpanel(title, note, *children, w=None, h=None, grow=False, foot=""):
    head = row(txt(title, 13.5, T["ink"], 600), txt(note, 11.5, T["faint"]) if note else "", gap=10, extra="flex: none;")
    body = (f'<div style="flex: 1; min-height: 0; display: flex; align-items: center; overflow: hidden;">'
            f'{"".join(children)}</div>')
    parts = [head, body] + ([foot] if foot else [])
    size = (f"width: {w}px; " if w else "") + (f"height: {h}px; " if h else "")
    return col(*parts, gap=12,
               extra=f"{size}padding: 16px 18px; border-radius: 16px; background: {CHART_BG}; "
                     f"box-sizing: border-box; {'flex: 1; min-width: 0;' if grow else 'flex: none;'}")


def figure_band(h=104):
    """The band every structure may or may not lead with: four numbers, nothing drawn."""
    return col(row(hero("14", "client PCs", "across 3 departments"),
                   hero("12", "on 1.4.2", "2 still behind", "warn"),
                   hero("2", "waiting on you", "an empty department", "danger"),
                   hero("4", "traversals today", "1 still open"), gap=64, extra="flex: none;"),
               gap=0, extra=f"padding: 18px 24px; border-radius: 16px; background: {CHART_BG}; "
                            f"height: {h}px; box-sizing: border-box; flex: none;")


def lshell(title, sub, structure, note, pill=0):
    pills = row(*[f'<span style="display: inline-flex; align-items: center; height: 30px; padding: 0 15px; '
                  f'border-radius: 999px; background: {T["select"] if i == pill else T["ground"]}; '
                  f'color: {"#fff" if i == pill else T["dim"]}; font-family: {T["sans"]}; font-size: 13px; '
                  f'font-weight: 600;">{p}</span>'
                  for i, p in enumerate(["At a glance", "The hierarchy", "The record"])], gap=7, extra="flex: none;")
    header = col(txt("Everything", 13, T["frame_dim"], 600),
                 row(f'<span style="width: 10px; height: 26px; border-radius: 3px; background: #fff;"></span>',
                     txt(title, 22, "#fff", 700), txt(sub, 13, T["frame_dim"]), gap=12),
                 pills, gap=12, extra="flex: none;")
    inner = col(header, structure,
                row(txt(note, 11.5, T["frame_faint"]), gap=0, extra="flex: none;"),
                gap=14, extra=f"width: {W}px; height: {H}px; box-sizing: border-box; padding: 22px 40px; "
                              f"background: {FRAME['native']}; overflow: hidden;")
    return page(title, "", "", inner, "", "native")


# --- the pieces each structure draws from ---------------------------------------------------------
def p_rollout(w=None, grow=False, h=None, plot=520):
    return lpanel("Rollout 1.4.2", "by department, to the same scale",
                  stacked_bars([(n, [("confirmed", a), ("behind", b), ("failing", f)]) for n, a, b, f in ROLLOUT], w=plot),
                  w=w, h=h, grow=grow,
                  foot=legend([("Confirmed", ST["confirmed"]), ("Behind", ST["behind"]), ("Failing", ST["failing"])]))


def p_fleet(w=None, grow=False, h=None, cols=7, size=30):
    return lpanel("The fleet", "one square per PC", waffle(FLEET, cols=cols, size=size, gap=8, w=cols * (size + 8)),
                  w=w, h=h, grow=grow,
                  foot=legend([("Confirmed", ST["confirmed"]), ("Behind", ST["behind"]), ("Failing", ST["failing"])]))


def p_trend(w=None, grow=False, h=None, plot=520):
    return lpanel("Confirmations", "since Monday", trend(SERIES, w=plot, h=110), w=w, h=h, grow=grow)


def p_work(w=None, grow=False, h=None, cw=160):
    return lpanel("Work, by department", "the same two bars, once each",
                  row(*[health_card(n, DEPT_COLOR[n], list(zip(WORK_TONES, t)), list(zip(WORK_TONES, f)), w=cw)
                        for n, (t, f) in WORK.items()], gap=12),
                  w=w, h=h, grow=grow,
                  foot=legend([("On track", ST["confirmed"]), ("Needs attention", ST["behind"]), ("Overdue", ST["failing"])]))


def p_work_stacked(w=None, grow=False, h=None, cw=284):
    """The same small multiple in a narrow column: the three cards stack instead of sitting in a
    row. Same component, different shelf."""
    return lpanel("Work, by department", "",
                  col(*[health_card(n, DEPT_COLOR[n], list(zip(WORK_TONES, t)), list(zip(WORK_TONES, f)), w=cw)
                        for n, (t, f) in WORK.items()], gap=10),
                  w=w, h=h, grow=grow,
                  foot=legend([("On track", ST["confirmed"]), ("Needs attention", ST["behind"]), ("Overdue", ST["failing"])]))


def p_map(w=None, grow=False, h=None, mw=520, mh=230):
    return lpanel("The hierarchy", "every department, Admin and PC", org_map(w=mw, h=mh), w=w, h=h, grow=grow,
                  foot=legend([(d, c) for d, c in DEPT_COLOR.items()]))


def p_sessions(w=None, grow=False, h=None, tw=520, th=210, lane_h=22):
    return lpanel("Sessions today", "who held each PC", day_timeline(w=tw, h=th, lane_h=lane_h), w=w, h=h, grow=grow,
                  foot=legend([("At the PC", T["line2"]), ("An Admin entered", T["warn"]), ("You entered", T["danger"])]))


def p_violations(w=None, grow=False, h=None):
    return lpanel("Violations by tier", "", tier_bars(w=380), w=w, h=h, grow=grow,
                  foot=txt("budget-2026.xlsx, found in /workers/ on OPS-07.", 11.5, T["faint"]))


def p_assist(w=None, grow=False, h=None):
    return lpanel("Assistance", "peer help, by consent", arcs(w=380, h=150), w=w, h=h, grow=grow)


# --------------------------------------------------------------------------------------------------
def l01():
    """Three: a band of figures, then two panels. The numbers are read first and the charts
    explain them — the shape the boards use now."""
    body = col(figure_band(),
               row(p_rollout(grow=True, plot=520), p_fleet(w=430), gap=LGAP, align="stretch",
                   extra="flex: 1; min-height: 0;"),
               gap=LGAP, extra=f"height: {LH}px; display: flex; flex-direction: column;")
    return lshell("Everything", "3 departments · 3 Admins · 14 client PCs", body,
                  "L01 · Three panels — a band of figures over two charts. Numbers first, charts explain.")


def l02():
    """Three: one tall panel and two stacked beside it. One chart is the subject of the page and
    the other two are context, which is what a drill-down wants."""
    body = row(p_map(w=780, mw=700, mh=380),
               col(p_rollout(grow=True, plot=420), p_violations(grow=True), gap=LGAP,
                   extra="flex: 1; min-width: 0; display: flex; flex-direction: column;"),
               gap=LGAP, align="stretch", extra=f"height: {LH}px;")
    return lshell("Everything", "3 departments · 3 Admins · 14 client PCs", body,
                  "L02 · Three panels — one subject, two supporting. The shape for a page that is about one thing.", 1)


def l03():
    """Four, evenly: nothing is more important than anything else. Honest when the page is a
    survey, dull when one thing actually matters."""
    body = col(row(p_rollout(grow=True, plot=430), p_fleet(grow=True, cols=5), gap=LGAP, align="stretch",
                   extra="flex: 1; min-height: 0;"),
               row(p_trend(grow=True, plot=430), p_work(grow=True, cw=140), gap=LGAP, align="stretch",
                   extra="flex: 1; min-height: 0;"),
               gap=LGAP, extra=f"height: {LH}px; display: flex; flex-direction: column;")
    return lshell("Everything", "3 departments · 3 Admins · 14 client PCs", body,
                  "L03 · Four panels, even — a survey. Nothing claims to matter more than anything else.")


def l04():
    """Four, weighted: one large panel and three narrow ones down the side. The page has a lead
    story, and the rest are glances."""
    body = row(p_sessions(grow=True, tw=760, th=520, lane_h=50),
               col(p_violations(w=372, grow=True), p_assist(w=372, grow=True), p_rollout(w=372, grow=True, plot=300),
                   gap=LGAP, extra="flex: none; display: flex; flex-direction: column;"),
               gap=LGAP, align="stretch", extra=f"height: {LH}px;")
    return lshell("Everything", "Today, 08:00 to now", body,
                  "L04 · Four panels, weighted — one lead story, three glances beside it.", 2)


def l05():
    """Five: a band, two wide, two narrow. Carries the most without crowding, and it is the first
    structure where the eye needs the panel titles to navigate."""
    body = col(figure_band(h=96),
               row(p_rollout(grow=True, plot=400), p_trend(grow=True, plot=400), gap=LGAP, align="stretch",
                   extra="flex: 1; min-height: 0;"),
               row(p_fleet(w=360, cols=5), p_work(grow=True, cw=150), p_violations(w=330), gap=LGAP, align="stretch",
                   extra="flex: 1; min-height: 0;"),
               gap=LGAP, extra=f"height: {LH}px; display: flex; flex-direction: column;")
    return lshell("Everything", "3 departments · 3 Admins · 14 client PCs", body,
                  "L05 · Five panels — the most a page carries before the titles start doing the navigating.")


def l06():
    """Five, asymmetric: a column of three small panels against two large ones. The small column
    is the triage strip — what needs you — and the large panels are where you then look."""
    body = row(col(lpanel("Waiting on you", "", col(txt("2", 34, T["danger"], 600, mono=True, extra="line-height: 1;"),
                                                    txt("an empty department, a violation", 11.5, T["faint"]), gap=8),
                          grow=True),
                   lpanel("Behind", "", col(txt("2", 34, T["warn"], 600, mono=True, extra="line-height: 1;"),
                                            txt("OPS-06 retrying, LOG-02 failing", 11.5, T["faint"]), gap=8), grow=True),
                   lpanel("Open sessions", "", col(txt("1", 34, T["ink"], 600, mono=True, extra="line-height: 1;"),
                                                   txt("you, inside OPS-07", 11.5, T["faint"]), gap=8), grow=True),
                   gap=LGAP, extra="width: 300px; flex: none; display: flex; flex-direction: column;"),
               col(p_map(grow=True, mw=620, mh=290), p_sessions(grow=True, tw=620, th=250), gap=LGAP,
                   extra="flex: 1; min-width: 0; display: flex; flex-direction: column;"),
               col(p_rollout(w=330, grow=True, plot=280), p_work_stacked(w=330, grow=True), gap=LGAP,
                   extra="flex: none; display: flex; flex-direction: column;"),
               gap=LGAP, align="stretch", extra=f"height: {LH}px;")
    return lshell("Everything", "3 departments · 3 Admins · 14 client PCs", body,
                  "L06 · Five panels, asymmetric — a triage column on the left, the substance beside it.")


LAYOUTS = [("L01-Three-Band.dc.html", "Three: a band and two charts", l01),
           ("L02-Three-Subject.dc.html", "Three: one subject, two supporting", l02),
           ("L03-Four-Even.dc.html", "Four, even: a survey", l03),
           ("L04-Four-Weighted.dc.html", "Four, weighted: a lead story", l04),
           ("L05-Five.dc.html", "Five: band, two wide, two narrow", l05),
           ("L06-Five-Triage.dc.html", "Five, asymmetric: a triage column", l06)]
