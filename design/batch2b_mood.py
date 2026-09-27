# ================================================================== Batch 2, rethought: RC02, RO02, WK02, RS02, CP02
# The user, 27 Sep 2026: "Rethink the whole batch, 1 and 2" -- and, on RS01's Tag by dropping: "I hate the
# lineup of 4 buttons, I hate the button design there too."
#
# What changes across all five, beyond the new machine mark (calm_slot is now a small screen):
#   * no square marks anywhere -- lanes of squares became ticks on a line, attempts became tick runs
#   * no icons sitting in rounded-square tiles -- icons stand bare
#   * no lineups of tinted pill buttons -- a choice among several is the things themselves (shelves you drop
#     onto, folders), one picker, or plain words; version numbers are words, not tags
# The same facets as RC01-CP01, so a pick still names a cell.

def ticks(states, gap=7, h=16):
    """A run of events as ticks on a line: quiet ones short and grey, the ones that need someone taller in tone."""
    out = []
    for s_ in states:
        tall = s_ in ("warn", "danger")
        out.append(f'<span style="width: 3px; height: {h if tall else int(h * 0.55)}px; border-radius: 2px; align-self: flex-end; '
                   f'background: {T[s_] if tall else "rgba(255,255,255,0.35)"};"></span>')
    return row(*out, gap=gap, align="flex-end", extra=f"height: {h}px; flex: none;")


def shelf(name, who, count, tone, target=False, w=132):
    """A tier as a shelf you can drop a file onto: a folder outline with its name and who may have it."""
    stroke = T[tone] if target else "rgba(255,255,255,0.22)"
    fill = T[tone + "_soft"] if target else "rgba(255,255,255,0.02)"
    dash = 'stroke-dasharray="5 4"' if target else ""
    return col(
        f'<svg width="{w}" height="70" viewBox="0 0 {w} 70"><path d="M2 12 a6 6 0 0 1 6-6 h30 l8 8 h{w - 56} a6 6 0 0 1 6 6 v42 '
        f'a6 6 0 0 1 -6 6 H8 a6 6 0 0 1 -6-6z" fill="{fill}" stroke="{stroke}" stroke-width="{2 if target else 1.4}" '
        f'{dash}/></svg>',
        txt(name, 12.5, T[tone] if target else T["ink"], 600), txt(who, 10.5, T["faint"]), txt(f"{count} files", 10.5, T["faint"]),
        gap=3, extra=f"width: {w}px; align-items: flex-start;")


# ------------------------------------------------------------------ RC02: Record
def rc02():
    a = b_cell("Four cells", dp_wire(dp_box(28, 10, 160, 62, label="who was where"), dp_box(196, 10, 76, 62, label="reports"),
                                     dp_box(28, 80, 76, 58, label="out of place"), dp_box(112, 80, 160, 58, label="the trail")),
               "the Overview's language")
    b = b_cell("A ledger by time", col(
        *[row(txt(t, 10.5, T["faint"], mono=True, extra="width: 38px; flex: none;"), ic(i, 13, T["dim"]), txt(w, 11.5, T["dim"]), gap=8,
              extra=f"width: 100%; padding: 6px 0; border-bottom: 1px solid {T['line']};")
          for t, i, w in [("14:20", "lock", "You entered WS-OPS-A1"), ("11:41", "shield", "A restricted file on OPS-07"),
                          ("10:40", "assistance", "A. Quaye began helping Finance"), ("09:11", "warn", "A hostname did not match")]], gap=0),
        "everything, newest first")
    c = b_cell("By person", col(person_card("RM", "R. Mensah", "entered OPS-04 twice today", w=284),
                                person_card("AQ", "A. Quaye", "assisting Finance since 10:40", "accent", w=284), gap=8), "who did what")
    d = b_cell("By kind, as ticks", col(
        *[row(txt(k, 11.5, T["dim"], extra="width: 92px;"), ticks(st), sp(), txt(str(len(st)), 11.5, T["ink"], 600, mono=True), gap=8,
              extra="width: 100%; padding: 5px 0;")
          for k, st in [("Sessions", ["ok"] * 12 + ["warn", "danger"]), ("Reports", ["ok"] * 4 + ["warn", "danger"]),
                        ("Out of place", ["danger", "ok"]), ("Deviations", ["warn"])]], gap=4), "each thing a tick")
    s1 = msection("The shape of Record — what happened, and what is still true", a, b, c, d)

    e = b_cell("Who was where, today", col(
        *[row(txt(h, 10.5, T["dim"], mono=True, extra="width: 60px;"),
              f'<div style="flex: 1; height: 8px; position: relative;">'
              + "".join(f'<span style="position: absolute; left: {x}%; width: {w}%; height: 8px; border-radius: 4px; background: {c_};"></span>'
                        for x, w, c_ in bl) + '</div>', gap=8, extra="width: 100%;")
          for h, bl in [("OPS-01", [(5, 40, "rgba(255,255,255,0.18)"), (55, 40, "rgba(255,255,255,0.18)")]),
                        ("OPS-04", [(0, 30, "rgba(255,255,255,0.18)"), (32, 8, T["warn"]), (42, 50, "rgba(255,255,255,0.18)")]),
                        ("WS-FIN-A1", [(20, 60, "rgba(255,255,255,0.18)")]), ("OPS-07", [(8, 30, "rgba(255,255,255,0.18)"), (40, 6, T["danger"])])]],
        txt("grey · at the PC   amber · an Admin entered   red · you", 10, T["faint"]), gap=10), "a lane per machine")
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
    return board("Record: rethought", s1, s2)


# ------------------------------------------------------------------ RO02: Rollout
def ro02():
    a = b_cell("The fleet, as screens", col(
        *[col(row(txt(d, 11.5, T["ink"], 600), sp(), txt(n, 10.5, T["faint"]), gap=0),
              row(*[calm_slot("", s_, 24) for s_ in st], gap=5), gap=5)
          for d, n, st in [("Operations", "6 of 7 on 1.4.2", ["ok"] * 5 + ["warn", "ok"]),
                           ("Finance", "2 of 2", ["ok", "ok"]), ("Logistics", "1 of 2", ["ok", "danger"])]], gap=10),
        "quiet screens; the lagging one in tone")
    b = b_cell("One line per department", col(
        *[col(row(txt(d, 11.5, T["dim"]), sp(), txt(f"{a_} of {b_}", 11, T["faint"]), gap=0),
              f'<div style="height: 4px; border-radius: 2px; background: rgba(255,255,255,0.10);"><div style="height: 4px; border-radius: 2px; '
              f'width: {int(100 * a_ / b_)}%; background: {T["dim"]};"></div></div>', gap=6)
          for d, a_, b_ in [("Operations", 6, 7), ("Finance", 2, 2), ("Logistics", 1, 2)]], gap=14), "how far each has come")
    c = b_cell("The gate, in words", col(
        txt("Everyone is on 1.4.2 except two machines.", 13, T["ink"], 600, extra="line-height: 1.35;"),
        txt("1.4.3 can be approved once those two catch up.", 11.5, T["dim"]),
        tk_line("Still on 1.4.1", "OPS-06, LOG-02", "warn"), gap=9), "never three versions at once")
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
        row(ic("dept", 18, T["warn"]), col(txt("Logistics has not moved since Monday", 12, T["ink"], 600),
                                           txt("no Admin governs it", 11, T["danger"]), gap=1), gap=10),
        txt("With nobody to prompt, it needs an Admin first.", 11, T["faint"]),
        row(gbtn("Assign an Admin", size="sm"), gap=0), gap=9), "nobody to prompt")
    h = b_cell("Attempts, as ticks", col(
        txt("Retries happen when a machine is idle.", 12, T["ink"], 600),
        *[row(txt(m, 11, T["dim"], mono=True, extra="width: 60px;"), ticks(st, 5, 14), sp(), txt(r, 10.5, tone_c(t, T["faint"])), gap=8,
              extra="width: 100%;")
          for m, st, r, t in [("OPS-06", ["ok", "ok", "ok", "warn", "warn", "warn"], "past the threshold", "warn"),
                              ("LOG-02", ["danger", "danger"], "offline", "danger"), ("OPS-02", ["ok"], "confirmed", None)]], gap=9),
        "silent below the threshold")
    s2 = msection("The two acts — approving, and prompting", e, f, g, h)
    return board("Rollout: rethought", s1, s2)


# ------------------------------------------------------------------ WK02: Work, from above
def wk02():
    a = b_cell("Four cells", dp_wire(dp_box(28, 10, 160, 62, label="tasks you set"), dp_box(196, 10, 76, 62, label="flows"),
                                     dp_box(28, 80, 76, 58, label="help, live"), dp_box(112, 80, 160, 58, label="by department")),
               "the Overview's language")
    b = b_cell("By department", col(
        *[row(txt(d, 12, T["ink"], 600, extra="width: 90px;"), txt(f"{t} tasks", 11, T["dim"]), txt(f"{f} flows", 11, T["dim"]), sp(),
              txt(s_, 11, tone_c(tone, T["faint"]), 600), gap=10, extra=f"width: 100%; padding: 7px 0; border-bottom: 1px solid {T['line']};")
          for d, t, f, s_, tone in [("Operations", 8, 4, "one overdue", "danger"), ("Finance", 3, 2, "on track", None),
                                    ("Logistics", 2, 0, "no Admin", "danger")]], gap=0), "where work sits")
    c = b_cell("Work, as ticks", col(
        *[row(txt(k, 11, T["faint"], 600, extra="width: 60px;"), ticks(st, 8, 18), gap=8, extra="padding: 4px 0;")
          for k, st in [("Tasks", ["ok", "ok", "danger", "ok", "ok", "ok"]), ("Flows", ["ok", "warn", "ok"]), ("Help", ["ok"])]],
        txt("each item a tick; the ones needing a person stand taller", 10.5, T["faint"]), gap=8), "three kinds, one glance")
    d = b_cell("Your own, first", col(
        txt("Given by you", 11, T["faint"], 600), tk_line("Department audit", "Operations · Fri"),
        tk_line("Year-end archive", "Finance · done?", "ok"),
        txt("Everyone else's", 11, T["faint"], 600), tk_line("8 tasks across 3 departments", "see all"), gap=4), "what you set, then the rest")
    s1 = msection("The shape of Work — what is moving through the organisation", a, b, c, d)

    e = b_cell("Help, watched", col(
        row(ic("eye", 14, T["accent"]), txt("Watching, not taking part", 12, T["accent"], 600), gap=7),
        person_card("KO", "Kojo ↔ R. Mensah", "Kojo's turn", w=284), person_card("AQ", "A. Quaye", "helping Finance", "accent", w=284),
        gap=8), "read-only, and says so")
    f = b_cell("Closed hands off", col(
        row(txt("Open", 12.5, T["ink"], 600), txt("Closed", 12.5, T["faint"]), gap=18),
        txt("Verified tasks and finished flows live in Record.", 11.5, T["dim"]),
        row(txt("Open Closed in Record", 12, T["accent"], 500), ic("chev", 12, T["accent"]), gap=4), gap=10), "one filter, one hand-off")
    g = b_cell("A task, from above", col(
        txt("Department audit", 13, T["ink"], 600), tk_line("Given to", "Operations · both Admins"),
        tk_line("Started", "by R. Mensah, Wed"), row(tbtn("Verify", "ok", size="sm"), gap=0),
        txt("You set it, so only you close it.", 10.5, T["faint"]), gap=6), "the assigner's view, one level up")
    h = b_cell("A flow across departments", col(
        au_sentence(f"Copy {au_slot('Year-end')}", f"from {au_slot('Finance')}", f"to {au_slot('Archive', 'ok')}", size=12.5),
        txt("Set up by you; Finance agreed on Monday.", 11, T["faint"]), gap=10), "as a sentence, like every flow")
    s2 = msection("Watching and setting — a Super User's part in work", e, f, g, h)
    return board("Work: rethought", s1, s2)


# ------------------------------------------------------------------ RS02: Resources
def rs02():
    tiers = [("Admin", "Admins only", 3, "danger"), ("Restricted", "your machine only", 5, "warn"),
             ("Workers", "your department's workers", 24, "accent"), ("Common", "everyone", 40, "ok")]
    a = b_cell("Four shelves", row(*[shelf(n, "", c_, t, w=58) for n, w, c_, t in tiers], gap=12), "a tier is a folder you can see")
    b = b_cell("Who may have what", col(
        *[row(txt(n, 12, T["ink"], 600, extra="width: 84px;"), txt(w, 11.5, T["dim"]), gap=8,
              extra=f"width: 100%; padding: 8px 0; border-bottom: 1px solid {T['line']};")
          for n, w in [("Admin", "you and other Admins"), ("Restricted", "you alone, on this machine"),
                       ("Workers", "you, and Operations' workers"), ("Common", "everyone")]], gap=0), "the rule, said in a line each")
    c = b_cell("Drop it on a shelf", col(
        row(ic("file", 16, T["accent"]), txt("pay-scales-2026.xlsx", 12, T["ink"], 600), gap=8,
            extra=f"padding: 8px 12px; border-radius: 10px; background: {T['pane']}; box-shadow: 0 10px 22px rgba(0,0,0,0.5); "
                  f"margin-left: 70px; transform: rotate(-3deg);"),
        row(*[shelf(n, "", c_, t, target=(n == "Restricted"), w=58) for n, _, c_, t in tiers], gap=10),
        txt("The shelf you hover opens; let go to tag it.", 10.5, T["faint"]), gap=6), "the shelves are the targets")
    d = b_cell("Everything in place", col(
        txt("Every machine holds what it should, and nothing more.", 12.5, T["ink"], 600, extra="line-height: 1.35;"),
        tk_line("Checked", "as files move, not on a timer"), tk_line("Out of place", "1 file", "danger"), gap=6), "compliance, as a sentence")
    s1 = msection("The tiers — the folders are the access policy", a, b, c, d)

    e = b_cell("A file out of place", col(
        row(ic("file", 16, T["danger"]), txt("budget-2026.xlsx", 12.5, T["ink"], 600), sp(), txt("Restricted", 11.5, T["warn"], 600), gap=8),
        tk_line("Found on", "OPS-07, among Workers files"), tk_line("Recognised by", "its content, not its name"),
        txt("Not deleted. Ignored until moved; Ama has been told.", 10.5, T["faint"]), gap=5), "surfaced, never deleted")
    f = b_cell("Where it should be", col(
        txt("pay-scales-2026.xlsx · Workers", 12, T["ink"], 600),
        row(*[calm_slot(n, s_, 34) for n, s_ in [("01", "ok"), ("02", "ok"), ("03", "warn"), ("04", "ok"), ("05", "ok")]], gap=8),
        txt("Missing on OPS-03: the one screen in tone.", 10.5, T["faint"]), gap=9), "present where it must be")
    g = b_cell("Move it, and what changes", col(
        au_sentence(f"Move {au_slot('pay-scales-2026.xlsx')}", f"from Workers to {au_slot('Restricted', 'warn')}", size=12),
        txt("It will leave 7 worker machines and stay only on yours.", 11.5, T["dim"], extra="line-height: 1.4;"),
        row(tbtn("Move it", "warn", size="sm"), gbtn("Cancel", size="sm"), gap=4), gap=9), "the cost, first")
    h = b_cell("A file's journey", col(
        *[row(txt(t, 10.5, T["faint"], mono=True, extra="width: 40px;"), txt(w, 11.5, T["dim"]), gap=8, extra="padding: 4px 0;")
          for t, w in [("Mon", "put on the Restricted shelf by you"), ("Tue", "copied to OPS-07 by Ama"), ("11:41", "flagged out of place")]],
        txt("Followed by its content, through renames and copies.", 10.5, T["faint"]), gap=4), "tracked by content")
    s2 = msection("One file — tagged, tracked, surfaced", e, f, g, h)
    return board("Resources: rethought", s1, s2)


# ------------------------------------------------------------------ CP02: level 4, a client PC
def cp02():
    lid = (f'<div style="width: 100%; height: 26px; border-radius: 8px; box-sizing: border-box; padding: 0 10px; display: flex; '
           f'align-items: center; gap: 8px; box-shadow: inset 0 0 0 1px {T["danger_soft"]}; background: rgba(255,255,255,0.03);">'
           f'{ring_svg(0.8, 14, T["danger"], 2)}<span style="font-family: {T["sans"]}; font-size: 10.5px; color: {T["ink"]}; '
           f'font-weight: 600;">You are inside Ama\'s machine</span><span style="flex: 1;"></span><span style="font-family: {T["mono"]}; '
           f'font-size: 10.5px; color: {T["danger"]}; font-weight: 700;">24:10 left</span></div>')
    a = b_cell("Four cells, under the banner", col(lid, dp_wire(dp_box(28, 10, 160, 62, label="the machine now"), dp_box(196, 10, 76, 62, label="run here"),
                                                                dp_box(28, 80, 76, 58, label="its tasks"), dp_box(112, 80, 160, 58, label="its files")),
                                                  gap=6), "level 3's banner")
    b = b_cell("The machine, live", col(
        row(calm_slot("07", "danger", 56), col(txt("OPS-07 · Ama", 13, T["ink"], 600), txt("Excel · budget-2026.xlsx in front", 11, T["accent"]),
                                              txt("idle 3 min · processor 22 %", 11, T["faint"]), gap=2), gap=12),
        txt("A live state, not their screen: nothing streams it.", 10.5, T["faint"]), gap=10), "what is true, right now")
    c = b_cell("Their screen, as a still", col(
        (f'<div style="width: 100%; height: 110px; border-radius: 10px; background: rgba(255,255,255,0.03); box-shadow: inset 0 0 0 1px {T["line2"]}; '
         f'display: flex; align-items: center; justify-content: center; color: {T["faint"]}; font-size: 11px; font-family: {T["sans"]};">'
         f'{ic("camera", 16, T["faint"])}&nbsp; a still, taken 12 s ago</div>'),
        row(gbtn("Take another", "camera", "sm"), gap=0), gap=8), "once it can be carried")
    d = b_cell("Their programs", col(
        *[row(ic("window", 14, T["dim"]), txt(p, 11.5, T["dim"]), sp(), txt(t, 10.5, T["faint"]), gap=8,
              extra=f"width: 100%; padding: 5px 0; border-bottom: 1px solid {T['line']};")
          for p, t in [("Excel", "open 40 min"), ("Outlook", "open all day"), ("Calculator", "idle")]],
        row(gbtn("Close one…", size="sm"), gap=0), gap=4), "what runs")
    s1 = msection("Inside a client PC — holding, level 4", a, b, c, d)

    e = b_cell("Run an action here", col(
        *[row(ic(i, 15, T[t]), txt(n, 11.5, T["dim"]), sp(), txt("Run", 11.5, T["accent"], 500), gap=10,
              extra=f"width: 100%; padding: 6px 0; border-bottom: 1px solid {T['line']};")
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
    return board("Client PC: rethought", s1, s2)


BATCH2B = [("RC02-Record.dc.html", "Record: rethought", rc02),
           ("RO02-Rollout.dc.html", "Rollout: rethought", ro02),
           ("WK02-Work.dc.html", "Work: rethought", wk02),
           ("RS02-Resources.dc.html", "Resources: rethought", rs02),
           ("CP02-ClientPC.dc.html", "Client PC: rethought", cp02)]
