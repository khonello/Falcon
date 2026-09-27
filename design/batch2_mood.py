# ================================================================== Batch 2 mood boards: RC01, RO01, WK01, RS01, CP01
# The Super User's three undesigned areas (TABS.md): Record, Rollout, Work -- plus the Admin's Resources
# (tiering is Admin-only, TABS.md issue 5) and level 4, a client PC entered (LEVELS.md, not started).
#
# Same format as every mood board. Drawn from the documents:
#   Record    audit, sessions ("who was where"), all reports and their Views (who addressed what, Super
#             User only), deviations, violations -- past AND present (TABS.md issue 3)
#   Rollout   implementation-spec 9: N+1 cannot be approved until every PC is on N; Admins carry the
#             rollout; failures retry quietly and escalate to the PC's Admin past a threshold; the Super
#             User sees it grouped by department and holds one lever -- prompting a stalled Admin
#   Work      tasks, flows, and assistance WATCHED, never started (TABS.md issue 6); one Closed filter
#             that hands off to Record
#   Resources resource-assistance-combo: admin / restricted / workers / common tiers, restricted files
#             tracked by content, violations surfaced to the user, never auto-deleted
#   Client PC level 4, holding: the machine's live state (no screen streaming exists), what you can run
#             on it, its files, its tasks -- under the same banner as level 3
# NOT DRAWN, on purpose: the report-routing CONFIGURATION screen. implementation-spec 10 lists it as
# deferred and CLAUDE.md says not to decide it unilaterally.

def m_slots(states, size=30):
    return row(*[calm_slot("", s_, size) for s_ in states], gap=5)


# ------------------------------------------------------------------ RC01: Record
def rc01():
    a = b_cell("Four cells", dp_wire(dp_box(28, 10, 160, 62, label="who was where"), dp_box(196, 10, 76, 62, label="reports"),
                                     dp_box(28, 80, 76, 58, label="out of place"), dp_box(112, 80, 160, 58, label="the trail")),
               "the Overview's language")
    b = b_cell("A ledger by time", col(
        *[row(txt(t, 10.5, T["faint"], mono=True, extra="width: 38px; flex: none;"), ic(i, 13, T["dim"]), txt(w, 11.5, T["dim"]), gap=8,
              extra=f"width: 100%; padding: 6px 0; border-bottom: 1px solid {T['line']};")
          for t, i, w in [("14:20", "lock", "You entered WS-OPS-A1"), ("11:41", "shield", "A restricted file on OPS-07"),
                          ("10:40", "assistance", "A. Quaye began helping Finance"), ("09:11", "warn", "A hostname did not match")]], gap=0),
        "everything, newest first")
    c = b_cell("By person", col(
        person_card("RM", "R. Mensah", "entered OPS-04 twice today", w=284),
        person_card("AQ", "A. Quaye", "assisting Finance since 10:40", "accent", w=284), gap=8), "who did what")
    d = b_cell("By kind", col(
        *[row(ic(i, 14, T["dim"]), txt(k, 12, T["dim"]), sp(), txt(n, 12, T["ink"], 600, mono=True), gap=8,
              extra=f"width: 100%; padding: 6px 0; border-bottom: 1px solid {T['line']};")
          for i, k, n in [("lock", "Sessions", "14"), ("reports", "Reports", "6"), ("shield", "Out of place", "2"), ("warn", "Deviations", "1")]],
        gap=0), "the trail, sorted")
    s1 = msection("The shape of Record — what happened, and what is still true", a, b, c, d)

    e = b_cell("Who was where, today", col(
        *[row(txt(h, 10.5, T["dim"], mono=True, extra="width: 60px;"),
              f'<div style="flex: 1; height: 10px; position: relative;">'
              + "".join(f'<span style="position: absolute; left: {x}%; width: {w}%; height: 10px; border-radius: 3px; background: {c_};"></span>'
                        for x, w, c_ in bl) + '</div>', gap=8, extra="width: 100%;")
          for h, bl in [("OPS-01", [(5, 40, T["line2"]), (55, 40, T["line2"])]), ("OPS-04", [(0, 30, T["line2"]), (32, 8, T["warn"]), (42, 50, T["line2"])]),
                        ("WS-FIN-A1", [(20, 60, T["line2"])]), ("OPS-07", [(8, 30, T["line2"]), (40, 6, T["danger"])])]],
        txt("grey · at the PC   amber · an Admin entered   red · you", 10, T["faint"]), gap=9), "a lane per machine")
    f = b_cell("A report and its View", col(
        txt("Listener report, channel 14", 12.5, T["ink"], 600),
        tk_line("Routed to", "HR"), tk_line("Addressed", "by M. Osei, Monday 09:12", "ok"),
        row(ic("eye", 12, T["faint"]), txt("This View is yours alone; it is never routed.", 10.5, T["faint"]), gap=6), gap=6),
        "who addressed it, and when")
    g = b_cell("A deviation", col(
        txt("A hostname did not match its certificate.", 12.5, T["ink"], 600, extra="line-height: 1.35;"),
        tk_line("Machine", "OPS-05"), tk_line("When", "today 09:11"), tk_line("State", "logged, not addressed", "warn"), gap=5),
        "surfaced, never guessed at")
    h = b_cell("A person's trail", col(
        row(av("RM", "admin", 26), txt("R. Mensah, today", 12.5, T["ink"], 600), gap=8),
        *[txt(s_, 11.5, T["dim"], extra=f"padding: 5px 0; border-bottom: 1px solid {T['line']};")
          for s_ in ["08:14 signed in at WS-OPS-A1", "10:02 entered OPS-04 for 20 minutes", "11:45 marked a violation addressed"]],
        txt("Reviewing someone's trail is itself recorded.", 10.5, T["faint"]), gap=4), "their day, in their order")
    s2 = msection("Reading the record", e, f, g, h)
    return board("Record: what happened, and who was where", s1, s2)


# ------------------------------------------------------------------ RO01: Rollout
def ro01():
    a = b_cell("The fleet by department", col(
        *[col(row(txt(d, 11.5, T["ink"], 600), sp(), txt(n, 10.5, T["faint"]), gap=0), m_slots(st, 24), gap=5)
          for d, n, st in [("Operations", "6 of 7 on 1.4.2", ["ok"] * 5 + ["warn", "ok"]),
                           ("Finance", "2 of 2", ["ok", "ok"]), ("Logistics", "1 of 2", ["ok", "danger"])]], gap=10),
        "calm slots; a ring on what lags")
    b = b_cell("One bar per department", col(
        *[col(row(txt(d, 11.5, T["dim"]), sp(), txt(f"{a_} of {b_}", 11, T["faint"]), gap=0),
              f'<div style="height: 8px; border-radius: 4px; background: {T["line2"]};"><div style="height: 8px; border-radius: 4px; '
              f'width: {int(100 * a_ / b_)}%; background: {T["dim"]};"></div></div>', gap=5)
          for d, a_, b_ in [("Operations", 6, 7), ("Finance", 2, 2), ("Logistics", 1, 2)]], gap=12), "how far each has come")
    c = b_cell("The gate", col(
        row(tk_tag("1.4.2", "accent"), txt("current", 11.5, T["faint"]), ic("arrow", 13, T["faint"]), tk_tag("1.4.3", "accent"), txt("waiting", 11.5, T["faint"]), gap=7),
        txt("1.4.3 can be approved once every machine is on 1.4.2.", 12.5, T["ink"], 600, extra="line-height: 1.35;"),
        tk_line("Still on 1.4.1", "2 machines", "warn"), gap=10), "never three versions at once")
    d = b_cell("Four cells", dp_wire(dp_box(28, 10, 160, 62, label="the fleet"), dp_box(196, 10, 76, 62, label="the gate"),
                                     dp_box(28, 80, 76, 58, label="stalled"), dp_box(112, 80, 160, 58, label="attempts, this week")),
               "the Overview's language")
    s1 = msection("The shape of Rollout — what version is where, and what is stuck", a, b, c, d)

    e = b_cell("Approve, when you may", col(
        txt("Approve 1.4.3", 13, T["ink"], 600), txt("Blocked: 2 machines are still on 1.4.1.", 11.5, T["warn"]),
        row(tbtn("Approve 1.4.3", "accent", "check", disabled=True), gap=0),
        txt("The button explains itself instead of hiding.", 10.5, T["faint"]), gap=9), "a gate said in words")
    f = b_cell("The lever: prompt an Admin", col(
        row(av("RM", "admin", 26), txt("Prompt R. Mensah", 12.5, T["ink"], 600), gap=8),
        txt("OPS-06 has failed six times since Friday.", 11.5, T["dim"]),
        tk_input("OPS-06 is holding up 1.4.3 — could you look today?", 40),
        row(tbtn("Send the prompt", "warn", size="sm"), gap=0), gap=8), "your one direct act")
    g = b_cell("A stalled department", col(
        row(au_icon("dept", "warn", 26), col(txt("Logistics has not moved since Monday", 12, T["ink"], 600),
                                             txt("no Admin governs it", 11, T["danger"]), gap=1), gap=9),
        txt("With nobody to prompt, it needs an Admin first.", 11, T["faint"]),
        row(gbtn("Assign an Admin", size="sm"), gap=0), gap=9), "nobody to prompt")
    h = b_cell("Attempts, quietly", col(
        txt("Retries happen when a machine is idle.", 12, T["ink"], 600),
        *[row(txt(m, 11, T["dim"], mono=True, extra="width: 60px;"), m_slots(st, 14), sp(), txt(r, 10.5, tone_c(t, T["faint"])), gap=6,
              extra="width: 100%;")
          for m, st, r, t in [("OPS-06", ["ok"] * 0 + ["warn"] * 6, "past the threshold", "warn"), ("LOG-02", ["danger", "danger"], "offline", "danger"),
                              ("OPS-02", ["ok"], "confirmed", None)]], gap=8), "silent below the threshold")
    s2 = msection("The two acts — approving, and prompting", e, f, g, h)
    return board("Rollout: versions, the gate, the lever", s1, s2)


# ------------------------------------------------------------------ WK01: Work, for the Super User
def wk01():
    a = b_cell("Four cells", dp_wire(dp_box(28, 10, 160, 62, label="tasks you set"), dp_box(196, 10, 76, 62, label="flows"),
                                     dp_box(28, 80, 76, 58, label="help, live"), dp_box(112, 80, 160, 58, label="by department")),
               "the Overview's language")
    b = b_cell("By department", col(
        *[row(txt(d, 12, T["ink"], 600, extra="width: 90px;"), txt(f"{t} tasks", 11, T["dim"]), txt(f"{f} flows", 11, T["dim"]), sp(),
              txt(s_, 11, tone_c(tone, T["faint"]), 600), gap=10, extra=f"width: 100%; padding: 7px 0; border-bottom: 1px solid {T['line']};")
          for d, t, f, s_, tone in [("Operations", 8, 4, "one overdue", "danger"), ("Finance", 3, 2, "on track", None),
                                    ("Logistics", 2, 0, "no Admin", "danger")]], gap=0), "where work sits")
    c = b_cell("Work, in lanes", col(
        *[row(txt(k, 11, T["faint"], 600, extra="width: 64px;"), *[f'<span style="width: 18px; height: 18px; border-radius: 5px; background: rgba(255,255,255,0.08); '
                                                                     + (f'box-shadow: inset 0 0 0 1.5px {c_};' if c_ else "") + '"></span>' for c_ in cs], gap=5)
          for k, cs in [("Tasks", [None, None, T["danger"], None, None]), ("Flows", [None, T["warn"], None]), ("Help", [T["accent"]])]],
        txt("calm marks; a ring where something needs a person", 10.5, T["faint"]), gap=10), "three kinds, one glance")
    d = b_cell("Your own, first", col(
        txt("Given by you", 11, T["faint"], 600), tk_line("Department audit", "Operations · Fri"),
        tk_line("Year-end archive", "Finance · done?", "ok"),
        txt("Everyone else's", 11, T["faint"], 600), tk_line("8 tasks across 3 departments", "see all"), gap=4), "what you set, then the rest")
    s1 = msection("The shape of Work — what is moving through the organisation", a, b, c, d)

    e = b_cell("Help, watched", col(
        row(ic("eye", 14, T["accent"]), txt("Watching, not taking part", 12, T["accent"], 600), gap=7),
        tk_line("Kojo ↔ R. Mensah", "Kojo's turn"), tk_line("A. Quaye helping Finance", "assisting"),
        txt("A Super User watches assistance; it never starts it.", 10.5, T["faint"]), gap=6), "read-only, and says so")
    f = b_cell("Closed hands off", col(
        row(txt("Open", 12.5, T["ink"], 600), txt("Closed", 12.5, T["faint"]), gap=18),
        txt("Verified tasks and finished flows live in Record.", 11.5, T["dim"]),
        row(txt("Open Closed in Record", 12, T["accent"], 500), ic("chev", 12, T["accent"]), gap=4), gap=10), "one filter, one hand-off")
    g = b_cell("A task, from above", col(
        txt("Department audit", 13, T["ink"], 600), tk_line("Given to", "Operations · both Admins"),
        tk_line("Started", "by R. Mensah, Wed"), row(tbtn("Verify", "ok", size="sm"), gap=0),
        txt("You set it, so only you close it.", 10.5, T["faint"]), gap=6), "the assigner's view, one level up")
    h = b_cell("A flow across departments", col(
        row(b_node("folder", "Finance", w=90), b_arrow(), b_node("monitor", "Archive", tone="ok", w=90), gap=0),
        txt("Set up by you; Finance agreed on Monday.", 11, T["faint"]), gap=10), "the only flows a Super User makes")
    s2 = msection("Watching and setting — a Super User's part in work", e, f, g, h)
    return board("Work: what is moving, seen from above", s1, s2)


# ------------------------------------------------------------------ RS01: Resources (Admin)
def rs01():
    tiers = [("Admin", "danger", "Admins only", 3), ("Restricted", "warn", "your machine only", 5),
             ("Workers", "accent", "your department's workers", 24), ("Common", "ok", "everyone", 40)]
    a = b_cell("Four shelves", col(
        *[row(au_icon("folder", t, 26), col(txt(n, 12, T["ink"], 600), txt(w, 10.5, T["faint"]), gap=1), sp(), txt(str(c_), 12, T["dim"], 600, mono=True),
              gap=9, extra=f"width: 100%; padding: 5px 0; border-bottom: 1px solid {T['line']};") for n, t, w, c_ in tiers], gap=0),
        "a tier is who may have it")
    b = b_cell("Who may have what", col(
        row(txt("", 11, extra="width: 76px;"), *[txt(h, 10.5, T["faint"], 600, extra="width: 52px; text-align: center;") for h in ["You", "Admins", "Workers"]], gap=0),
        *[row(txt(n, 11.5, T["dim"], extra="width: 76px;"), *[row(ic("check", 12, T["ok"]) if ok_ else ic("x", 12, T["line2"]), gap=0,
                                                                    extra="width: 52px; justify-content: center;") for ok_ in marks], gap=0)
          for n, marks in [("Admin", [True, True, False]), ("Restricted", [True, False, False]), ("Workers", [True, True, True]), ("Common", [True, True, True])]],
        gap=6), "the rule, drawn once")
    c = b_cell("Tag by dropping", col(
        row(ic("file", 16, T["accent"]), txt("pay-scales-2026.xlsx", 12, T["ink"], 600), gap=8,
            extra=f"padding: 8px 10px; border-radius: 9px; background: {T['ground']}; box-shadow: 0 8px 18px rgba(0,0,0,0.4);"),
        row(ic("arrow", 14, T["faint"]), gap=0, extra="padding-left: 20px;"),
        row(*[f'<span style="padding: 8px 10px; border-radius: 9px; font-size: 11px; font-weight: 600; font-family: {T["sans"]}; '
              f'background: {T[t + "_soft"]}; color: {T[t]}; {"box-shadow: inset 0 0 0 1.5px " + T[t] + ";" if n == "Restricted" else ""}">{n}</span>'
              for n, t, _, _ in tiers], gap=5), gap=6), "a file onto a shelf")
    d = b_cell("Everything in place", col(
        txt("Every machine holds what it should, and nothing more.", 12.5, T["ink"], 600, extra="line-height: 1.35;"),
        tk_line("Checked", "as files move, not on a timer"), tk_line("Out of place", "1 file", "danger"), gap=6), "compliance, as a sentence")
    s1 = msection("The tiers — the folders are the access policy", a, b, c, d)

    e = b_cell("A file out of place", col(
        row(ic("file", 16, T["danger"]), txt("budget-2026.xlsx", 12.5, T["ink"], 600), sp(), tk_tag("Restricted", "warn"), gap=8),
        tk_line("Found on", "OPS-07, among Workers files"), tk_line("Recognised by", "its content, not its name"),
        txt("Not deleted. Ignored until moved; Ama has been told.", 10.5, T["faint"]), gap=5), "surfaced, never deleted")
    f = b_cell("Where it should be", col(
        txt("pay-scales-2026.xlsx · Workers", 12, T["ink"], 600),
        row(*[calm_slot(n, s_, 28) for n, s_ in [("01", "ok"), ("02", "ok"), ("03", "warn"), ("04", "ok"), ("05", "ok")]], gap=5),
        txt("Missing on OPS-03. A ring shows the one that lacks it.", 10.5, T["faint"]), gap=9), "present where it must be")
    g = b_cell("Retag, and what changes", col(
        row(tk_tag("Workers", "accent"), ic("arrow", 13, T["faint"]), tk_tag("Restricted", "warn"), gap=7),
        txt("It will leave 7 worker machines and stay only on yours.", 11.5, T["dim"], extra="line-height: 1.4;"),
        row(tbtn("Retag it", "warn", size="sm"), gbtn("Cancel", size="sm"), gap=4), gap=9), "the cost, first")
    h = b_cell("A file's journey", col(
        *[row(txt(t, 10.5, T["faint"], mono=True, extra="width: 40px;"), txt(w, 11.5, T["dim"]), gap=8, extra="padding: 4px 0;")
          for t, w in [("Mon", "tagged Restricted by you"), ("Tue", "copied to OPS-07 by Ama"), ("11:41", "flagged out of place")]],
        txt("Followed by its content, through renames and copies.", 10.5, T["faint"]), gap=4), "tracked by content")
    s2 = msection("One file — tagged, tracked, surfaced", e, f, g, h)
    return board("Resources: the tiers, and a file out of place", s1, s2)


# ------------------------------------------------------------------ CP01: level 4, a client PC entered
def cp01():
    lid = (f'<div style="width: 100%; height: 26px; border-radius: 8px; box-sizing: border-box; padding: 0 10px; display: flex; '
           f'align-items: center; gap: 8px; box-shadow: inset 0 0 0 1px {T["danger_soft"]}; background: rgba(255,255,255,0.03);">'
           f'{ring_svg(0.8, 14, T["danger"], 2)}<span style="font-family: {T["sans"]}; font-size: 10.5px; color: {T["ink"]}; '
           f'font-weight: 600;">You are inside Ama\'s machine</span><span style="flex: 1;"></span><span style="font-family: {T["mono"]}; '
           f'font-size: 10.5px; color: {T["danger"]}; font-weight: 700;">24:10 left</span></div>')
    a = b_cell("Four cells, under the banner", col(lid, dp_wire(dp_box(28, 10, 160, 62, label="the machine now"), dp_box(196, 10, 76, 62, label="run here"),
                                                                dp_box(28, 80, 76, 58, label="its tasks"), dp_box(112, 80, 160, 58, label="its files")),
                                                  gap=6), "level 3's banner")
    b = b_cell("The machine, live", col(
        tk_line("Processor", "22 %"), tk_line("Memory", "61 %"), tk_line("Idle for", "3 minutes"),
        tk_line("In front", "Excel · budget-2026.xlsx", "accent"),
        txt("A live state, not their screen: nothing streams it.", 10.5, T["faint"]), gap=3), "what is true, right now")
    c = b_cell("Their screen, as a still", col(
        (f'<div style="width: 100%; height: 110px; border-radius: 10px; background: {T["ground"]}; box-shadow: inset 0 0 0 1px {T["line2"]}; '
         f'display: flex; align-items: center; justify-content: center; color: {T["faint"]}; font-size: 11px; font-family: {T["sans"]};">'
         f'{ic("camera", 16, T["faint"])}&nbsp; a still, taken 12 s ago</div>'),
        row(gbtn("Take another", "camera", "sm"), gap=0), gap=8), "once it can be carried")
    d = b_cell("Their programs", col(
        *[row(ic("window", 13, T["dim"]), txt(p, 11.5, T["dim"]), sp(), txt(t, 10.5, T["faint"]), gap=8,
              extra=f"width: 100%; padding: 5px 0; border-bottom: 1px solid {T['line']};")
          for p, t in [("Excel", "open 40 min"), ("Outlook", "open all day"), ("Calculator", "idle")]],
        row(gbtn("Close one…", size="sm"), gap=0), gap=4), "what runs")
    s1 = msection("Inside a client PC — holding, level 4", a, b, c, d)

    e = b_cell("Run an action here", col(
        *[row(au_icon(i, t, 22), txt(n, 11.5, T["dim"]), sp(), ic("play", 12, T["faint"]), gap=8,
              extra=f"width: 100%; padding: 5px 0; border-bottom: 1px solid {T['line']};")
          for i, t, n in [("bell", "accent", "Notify Ama"), ("lock", "accent", "Lock the screen"), ("eye", "ok", "Programs running")]],
        txt("The library, aimed at this one machine.", 10.5, T["faint"]), gap=3), "the Actions page, aimed")
    f = b_cell("Its files", col(
        tk_line("budget-2026.xlsx", "out of place", "danger", lead=ic("file", 13, T["danger"])),
        tk_line("reconciliation-q3.docx", "a task's target", "accent", lead=ic("file", 13, T["accent"])),
        tk_line("Resources", "all present", "ok", lead=ic("folder", 13, T["ok"])), gap=0), "what matters on it")
    g = b_cell("Its tasks and flows", col(
        tk_line("Quarterly report", "overdue", "danger", lead=ic("tasks", 13, T["danger"])),
        tk_line("Handbook → this machine", "syncing", None, lead=ic("flows", 13, T["dim"])), gap=0), "the work tied to it")
    h = b_cell("What Ama sees", col(
        (f'<div style="padding: 10px 12px; border-radius: 10px; box-shadow: inset 0 0 0 1px {T["danger_soft"]}; font-size: 11.5px; '
         f'color: {T["ink"]}; font-family: {T["sans"]}; line-height: 1.4;">Your Admin, R. Mensah, is in charge of this machine for now. '
         f'You can use it again when they leave.</div>'),
        txt("The Worker overlay: said plainly, no alarm.", 10.5, T["faint"]), gap=8), "the other side of the banner")
    s2 = msection("What you can do inside", e, f, g, h)
    return board("Client PC: level 4, inside a worker's machine", s1, s2)


BATCH2_MOOD = [("RC01-Record.dc.html", "Record: what happened, and who was where", rc01),
               ("RO01-Rollout.dc.html", "Rollout: versions, the gate, the lever", ro01),
               ("WK01-Work.dc.html", "Work: what is moving, seen from above", wk01),
               ("RS01-Resources.dc.html", "Resources: the tiers, and a file out of place", rs01),
               ("CP01-ClientPC.dc.html", "Client PC: level 4, inside a worker's machine", cp01)]
