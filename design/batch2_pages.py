# ================================================================== Batch 2 pages: RC03, RO03, WK03, RS03, CP03
# The user, 27 Sep 2026: batch 2 "all work well" -- so every rethought facet (RC02-CP02) was open to use, and the
# picks were resolved here against design/PATTERNS.md. Each board's foot says what was chosen.
#
# Choices made, once:
#   * Record, Rollout, Work are the Super User's areas: the rail is the Super User's five, the area lit.
#   * Resources is Admin-only and the Admin rail has no Resources entry. It is reached from the Admin's home
#     (Hierarchy lit), crumb "Operations > Resources" -- a place inside their department, like a department is
#     inside Authority. No rail entry is added.
#   * Level 4 is drawn as an Admin inside a worker's machine (the common case); the lid is level 3's, one level
#     down. A Super User entering a PC directly gets the same page under the same lid.
#   * Rollout demonstrates PAGING (PATTERNS 3): machines stay at full size and the container's right edge
#     reveals the next ones, naming any that needs someone.

def area_page(title, active, crumbs, heading, phrase, tone, bands, note, brow):
    top = topbar2([IND["rollout"], IND["pings"]], "Go to, do, find")
    rail = held_rail(active, SU_AREAS)
    inner = col(brow, work_title(crumbs, heading, phrase, tone), *bands,
                row(txt(note, 11.5, T["frame_faint"]), gap=0, extra="flex: none;") if note else "",
                gap=12, extra="flex: 1; min-width: 0; display: flex; flex-direction: column; "
                              "padding: 6px 22px 8px 6px; box-sizing: border-box; overflow: hidden;")
    return page(title, top, rail, inner, statusbar("Connected, TLS pinned", "no session", "ok"), "native")


def paged_row(items, shown, size, more, needs="", w=None):
    """A row of machines at FULL size; the right edge is the pager (PATTERNS 3). items: (label, state, name, line, tone)."""
    cols = [col(calm_slot(n, st, size), txt(who, 12, T["ink"], 600, extra="text-align: center;"),
                txt(line, 10.5, tone_c(tone, T["faint"]), 500 if tone else 400, extra="text-align: center;"),
                gap=3, extra=f"align-items: center; width: {size + 34}px; flex: none;") for n, st, who, line, tone in items[:shown]]
    edge = col(ic("chev", 18, T["dim"]), txt(more, 11.5, T["dim"], 600), txt(needs, 10.5, T["warn"], 600) if needs else "",
               gap=4, extra="align-items: center; justify-content: center; width: 104px; flex: none; align-self: stretch; "
                             "border-radius: 12px; background: linear-gradient(90deg, rgba(255,255,255,0), rgba(255,255,255,0.06));")
    width = f"width: {w}px;" if w else ""
    return row(*cols, sp(), edge, gap=14, align="flex-start", extra=width)


def lanes_(rows_, w):
    grey = "rgba(255,255,255,0.18)"
    return col(*[row(txt(h, 11, T["dim"], mono=True, extra="width: 76px;"),
                     f'<div style="flex: 1; height: 10px; position: relative;">'
                     + "".join(f'<span style="position: absolute; left: {x}%; width: {ww}%; height: 10px; border-radius: 5px; '
                               f'background: {T[c_] if c_ else grey};"></span>' for x, ww, c_ in bl) + '</div>', gap=10,
                     extra="width: 100%;") for h, bl in rows_],
               row(txt("", 10, extra="width: 76px;"), *[txt(t, 10.5, T["faint"], mono=True, extra="flex: 1;") for t in ["08", "10", "12", "14", "16", "18"]],
                   gap=0, extra="width: 100%;"),
               row(txt("grey · at their own PC", 10.5, T["faint"]), txt("amber · an Admin entered", 10.5, T["warn"]),
                   txt("red · you entered", 10.5, T["danger"]), gap=18), gap=11, extra=f"width: {w}px;")


# ------------------------------------------------------------------ RC03: Record
def rc03():
    who = lanes_([("OPS-01", [(3, 38, None), (50, 45, None)]), ("OPS-04", [(0, 28, None), (30, 9, "warn"), (41, 50, None)]),
                  ("OPS-07", [(6, 30, None), (38, 6, "danger"), (46, 40, None)]), ("WS-OPS-A1", [(2, 90, None)]),
                  ("WS-FIN-A1", [(18, 22, None), (42, 40, "accent")]), ("FIN-02", [(12, 70, None)]),
                  ("LOG-01", [(30, 20, None)])], 856)
    trail = col(*[row(txt(t, 11, T["faint"], mono=True, extra="width: 44px; flex: none;"), ic(i, 15, T[tn] if tn else T["dim"]),
                      txt(w_, 12.5, T["ink"] if tn else T["dim"], 500 if tn else 400), sp(), txt(who_, 11, T["faint"]), gap=10,
                      extra=f"width: 100%; padding: 8px 0; border-bottom: 1px solid {T['line']};")
                  for t, i, w_, who_, tn in [("14:20", "lock", "You entered WS-OPS-A1", "you", "danger"),
                                             ("11:45", "check", "A violation was marked addressed", "R. Mensah", None),
                                             ("11:41", "shield", "A restricted file turned up on OPS-07", "system", "danger"),
                                             ("10:40", "assistance", "A. Quaye began helping Finance", "A. Quaye", "accent"),
                                             ("10:02", "lock", "R. Mensah entered OPS-04 for 20 minutes", "R. Mensah", None),
                                             ("09:11", "warn", "A hostname did not match on OPS-05", "system", "warn")]],
                gap=0, extra="width: 856px;")
    views = col(txt("Reports, and who answered them", 11.5, T["faint"], 600),
                thing_card("eye", "ok", "Listener report, channel 14", "HR · addressed by M. Osei, Mon 09:12", "addressed"),
                thing_card("shield", "danger", "A restricted file on OPS-07", "Operations · seen, not addressed", "open", "danger"),
                row(ic("eye", 12, T["faint"]), txt("Who addressed what is yours alone; it is never routed.", 10.5, T["faint"]), gap=6),
                gap=9, extra="width: 396px;")
    place = col(txt("Two things are out of place right now.", 14, T["ink"], 600, extra="line-height: 1.35;"),
                thing_card("file", "danger", "budget-2026.xlsx", "Restricted · on OPS-07, among Workers files"),
                thing_card("warn", "warn", "A hostname did not match", "OPS-05 · logged, not addressed"),
                gap=10, extra="width: 396px;")
    return area_page(
        "Record", "record", ["Record"], "Record", "past and present · two things still out of place", "warn",
        [row(col(kcell("Who was where, today", "you entered one machine", "danger", who, w=900, h=300, top=True),
                 kcell("The trail", "newest first", "dim", trail, w=900, h=356, top=True), gap=20, extra="flex: none;"),
             col(kcell("Reports and their Views", "one still open", "warn", views, w=440, h=300, top=True),
                 kcell("Out of place", "two", "danger", place, w=440, h=356, top=True), gap=20, extra="flex: none;"),
             gap=20, align="stretch", extra="flex: none;")],
        "RC03 · Four cells (RC02): Who was where as lanes, The trail as a ledger with bare icons, a report beside its "
        "Super-User-only View, and what is out of place now. Closed work from Work lands in the trail.",
        eyebrow("PAGE", "Record — the Super User's", "a wide left column"))


# ------------------------------------------------------------------ RO03: Rollout
def ro03():
    ops = [(f"{i:02d}", st, who, line, tone) for i, (st, who, line, tone) in enumerate([
        ("ok", "Kojo", "on 1.4.2", None), ("ok", "Efua", "on 1.4.2", None), ("ok", "Yaw", "on 1.4.2", None),
        ("ok", "Adjoa", "on 1.4.2", None), ("ok", "Nana", "on 1.4.2", None), ("warn", "Kwame", "failed 6 times", "warn"),
        ("ok", "Ama", "on 1.4.2", None), ("ok", "Kofi", "on 1.4.2", None)], start=1)]
    fleet = col(
        row(txt("Operations", 13, T["ink"], 600), txt("13 of 14 on 1.4.2", 11.5, T["faint"]), gap=12),
        paged_row(ops, 8, 58, "6 more", "", w=1316),
        row(txt("Logistics", 13, T["ink"], 600), txt("1 of 2 · no Admin governs it", 11.5, T["danger"]), gap=12, extra="padding-top: 6px;"),
        row(*[col(calm_slot(n, st, 58), txt(who, 12, T["ink"], 600), txt(line, 10.5, tone_c(tone, T["faint"]), 500 if tone else 400),
                  gap=3, extra="align-items: center; width: 92px;") for n, st, who, line, tone in
              [("01", "ok", "Esi", "on 1.4.2", None), ("02", "danger", "Abena", "offline, on 1.4.1", "danger")]], gap=14),
        txt("Finance: 2 of 2, every machine current — folded away.", 11.5, T["faint"]),
        gap=10, extra="width: 1316px;")
    gate = col(txt("1.4.3 waits for two machines.", 15, T["ink"], 600, extra="line-height: 1.35;"),
               txt("A new version can be approved only once every machine is on the current one.", 11.5, T["dim"], extra="line-height: 1.4;"),
               row(tbtn("Approve 1.4.3", "accent", "check", disabled=True), gap=0),
               txt("Blocked by OPS-06 and LOG-02.", 11.5, T["warn"]), gap=10, extra="width: 396px;")
    lever = col(person_card("RM", "R. Mensah", "OPS-06 has failed six times since Friday", "warn"),
                tk_input("OPS-06 is holding up 1.4.3 — could you look today?", 44),
                row(tbtn("Prompt R. Mensah", "warn", size="sm"), sp(), txt("your one direct act", 11, T["faint"]), gap=8, extra="width: 100%;"),
                rule(),
                row(ic("dept", 16, T["danger"]), txt("Logistics has nobody to prompt.", 12, T["ink"], 500), sp(), gbtn("Assign an Admin", size="sm"), gap=8,
                    extra="width: 100%;"), gap=10, extra="width: 436px;")
    attempts = col(txt("Retries run quietly when a machine is idle.", 12.5, T["ink"], 600, extra="line-height: 1.35;"),
                   *[row(txt(m, 11.5, T["dim"], mono=True, extra="width: 64px;"), ticks(st, 6, 18), sp(), txt(r, 11, tone_c(t, T["faint"]), 500), gap=8,
                         extra="width: 100%; padding: 4px 0;")
                     for m, st, r, t in [("OPS-06", ["ok", "ok", "ok", "warn", "warn", "warn"], "past the threshold", "warn"),
                                         ("LOG-02", ["danger", "danger"], "offline", "danger"), ("OPS-02", ["ok"], "confirmed", None),
                                         ("FIN-01", ["ok", "ok"], "confirmed", None)]],
                   gap=8, extra="width: 356px;")
    return area_page(
        "Rollout", "rollout", ["Rollout"], "Rollout", "1.4.2 on 16 of 18 machines", "warn",
        [row(kcell("The fleet", "two machines behind", "warn", fleet, w=1360, h=356, top=True), gap=0, extra="flex: none;"),
         row(kcell("The gate", "1.4.3 blocked", "warn", gate, w=440, h=300, top=True),
             kcell("The lever", "prompt an Admin", "warn", lever, w=480, h=300, top=True),
             kcell("Attempts", "silent below the threshold", "dim", attempts, w=400, h=300, top=True),
             gap=20, align="stretch", extra="flex: none;")],
        "RO03 · The fleet as screens at full size, PAGED: the right edge shows '6 more' and slides the next ones in — no shrinking "
        "(PATTERNS 3). A department with every machine current folds into a line. The gate in words, the lever, attempts as ticks.",
        eyebrow("PAGE", "Rollout — the Super User's", "a band over three"))


# ------------------------------------------------------------------ WK03: Work, from above
def wk03():
    def dept_card(name, tasks, flows, state, tone):
        return col(row(txt(name, 13.5, T["ink"], 600), sp(), txt(state, 11.5, tone_c(tone, T["faint"]), 600), gap=8, extra="width: 100%;"),
                   row(txt("Tasks", 11, T["faint"], extra="width: 44px;"), ticks(tasks, 6, 16), gap=8),
                   row(txt("Flows", 11, T["faint"], extra="width: 44px;"), ticks(flows, 6, 16), gap=8),
                   gap=9, extra=f"width: 100%; box-sizing: border-box; padding: 13px 14px; border-radius: 14px; background: {T['pane']};")
    depts = col(plain_tabs(["Open", "Closed"], "Open"),
                dept_card("Operations", ["ok", "ok", "danger", "ok", "ok", "ok", "ok", "ok"], ["ok", "warn", "ok", "ok"], "one overdue", "danger"),
                dept_card("Finance", ["ok", "ok", "ok"], ["ok", "ok"], "on track", None),
                dept_card("Logistics", ["ok", "ok"], [], "no Admin", "danger"),
                txt("Closed hands off to Record.", 11, T["faint"]), gap=10, extra="width: 396px;")
    mine = col(txt("Given by you", 11.5, T["faint"], 600),
               thing_card("tasks", "accent", "Department audit", "Operations · both Admins · started Wed", "Fri"),
               thing_card("tasks", "ok", "Year-end archive", "Finance · both checks passed", "verify", "ok"),
               row(tbtn("Verify the archive", "ok", "check", size="sm"), sp(), txt("you set it, so only you close it", 11, T["faint"]), gap=8,
                   extra="width: 100%;"),
               txt("A flow you set", 11.5, T["faint"], 600, extra="padding-top: 8px;"),
               au_sentence(f"Copy {au_slot('Year-end')}", f"from {au_slot('Finance')}", f"to {au_slot('Archive', 'ok')}", size=13),
               txt("Finance agreed on Monday.", 11, T["faint"]), gap=9, extra="width: 396px;")
    watch = col(row(ic("eye", 15, T["accent"]), txt("Watching, never taking part", 12.5, T["accent"], 600), gap=8),
                person_card("KO", "Kojo ↔ R. Mensah", "Operations · Kojo's turn"),
                person_card("AM", "Ama ↔ R. Mensah", "Operations · HR is listening", "accent"),
                person_card("AQ", "A. Quaye → Finance", "assisting by consent since 10:40", "accent"),
                txt("A Super User watches assistance; it never starts it.", 11, T["faint"]), gap=9, extra="width: 396px;")
    return area_page(
        "Work", "work", ["Work"], "Work", "13 tasks · 6 flows · one overdue", "danger",
        [row(kcell("By department", "one overdue", "danger", depts, w=440, h=676, top=True),
             kcell("Yours", "two tasks, one flow", "accent", mine, w=440, h=676, top=True),
             kcell("Help, watched", "three live", "accent", watch, w=440, h=676, top=True),
             gap=20, align="stretch", extra="flex: none;")],
        "WK03 · Three columns: departments as cards with their work as ticks and the one Closed filter; what you set, with the "
        "flow as a sentence; assistance watched as avatar-led cards (WK02).",
        eyebrow("PAGE", "Work — the Super User's", "three equal columns"))


# ------------------------------------------------------------------ RS03: Resources (Admin)
def rs03():
    tiers = [("Admin", "you and other Admins", 3, "danger"), ("Restricted", "you alone, on this machine", 5, "warn"),
             ("Workers", "you and Operations' workers", 24, "accent"), ("Common", "everyone", 40, "ok")]
    dragging = row(ic("file", 18, T["accent"]), txt("pay-scales-2026.xlsx", 13, T["ink"], 600), gap=9,
                   extra=f"padding: 10px 14px; border-radius: 12px; background: {T['pane']}; box-shadow: 0 14px 30px rgba(0,0,0,0.55); "
                         f"transform: rotate(-2deg); margin-left: 420px; align-self: flex-start;")
    shelves = col(dragging,
                  row(*[shelf(n, w_, c_, t, target=(n == "Restricted"), w=260) for n, w_, c_, t in tiers], gap=58),
                  txt("Drop a file on a shelf to tag it. The shelf you hover opens; the tier is who may have it.", 11.5, T["faint"]),
                  gap=12, extra="width: 1316px;")
    out = col(txt("budget-2026.xlsx is out of place.", 14, T["ink"], 600, extra="line-height: 1.35;"),
              tk_line("Tier", "Restricted", "warn"), tk_line("Found on", "OPS-07, among Workers files"),
              tk_line("Recognised by", "its content, not its name"),
              row(gbtn("Ping Ama", size="sm"), gbtn("Enter OPS-07", size="sm"), gap=4),
              txt("Not deleted. Ignored until moved; Ama has been told.", 11, T["faint"]), gap=8, extra="width: 476px;")
    present = col(txt("pay-scales-2026.xlsx belongs on every worker machine.", 12.5, T["ink"], 600, extra="line-height: 1.35;"),
                  row(*[col(calm_slot(n, s_, 44), txt(w_, 10.5, tone_c(t, T["faint"]), 500 if t else 400), gap=3, extra="align-items: center; width: 60px;")
                        for n, s_, w_, t in [("01", "ok", "has it", None), ("02", "ok", "has it", None), ("03", "warn", "missing", "warn"),
                                             ("04", "ok", "has it", None), ("05", "ok", "has it", None)]], gap=6),
                  txt("OPS-03 lacks it; the next sweep will offer it again.", 11, T["faint"]), gap=10, extra="width: 376px;")
    journey = col(*[row(txt(t, 11, T["faint"], mono=True, extra="width: 44px;"), txt(w_, 12, T["dim"]), gap=8,
                        extra=f"width: 100%; padding: 6px 0; border-bottom: 1px solid {T['line']};")
                    for t, w_ in [("Mon", "put on the Restricted shelf by you"), ("Tue", "copied to OPS-07 by Ama"),
                                  ("11:41", "flagged out of place"), ("11:45", "Ama was told")]],
                  txt("Followed by its content, through renames and copies.", 11, T["faint"], extra="padding-top: 4px;"),
                  gap=0, extra="width: 336px;")
    return work_page(
        "Resources", "hierarchy", ["Operations", "Resources"], "Resources", "the folders are the access policy · one file out of place",
        "warn",
        [row(kcell("The shelves", "four tiers", "dim", shelves, w=1360, h=300, top=True), gap=0, extra="flex: none;"),
         row(kcell("Out of place", "one file", "danger", out, w=520, h=356, top=True),
             kcell("Where it should be", "one machine lacks it", "warn", present, w=420, h=356, top=True),
             kcell("A file's journey", "budget-2026.xlsx", "dim", journey, w=380, h=356, top=True),
             gap=20, align="stretch", extra="flex: none;")],
        "RS03 · The tiers are shelves you drop a file onto — the things themselves as the targets (RS02, PATTERNS 10). "
        "Reached from the Admin's home: no rail entry is added. Below: out of place, present where it must be, its journey.",
        eyebrow("PAGE", "Resources — an Admin's", "a band over three"))


# ------------------------------------------------------------------ CP03: level 4, inside a worker's machine
def cp03():
    lid = (f'<div style="width: 1360px; height: 38px; border-radius: 12px; box-sizing: border-box; padding: 0 14px; display: flex; '
           f'align-items: center; gap: 10px; box-shadow: inset 0 0 0 1px rgba(221,138,138,0.45); background: rgba(255,255,255,0.03); flex: none;">'
           f'{ring_svg(0.8, 16, T["danger"], 2)}<span style="font-family: {T["sans"]}; font-size: 13px; color: {T["ink"]}; font-weight: 600;">'
           f'You are inside Ama\'s machine</span><span style="font-family: {T["mono"]}; font-size: 12px; color: {T["faint"]};">OPS-07</span>'
           f'<span style="font-family: {T["mono"]}; font-size: 13px; color: {T["danger"]}; font-weight: 700;">24:10 left</span>'
           f'<span style="flex: 1;"></span><span style="font-family: {T["sans"]}; font-size: 12px; color: {T["faint"]};">Esc steps out</span>'
           f'<span style="font-family: {T["sans"]}; font-size: 13px; color: {T["dim"]}; font-weight: 600;">Extend</span>'
           f'{tbtn("Leave", "danger", "back", "sm")}</div>')
    live = col(row(calm_slot("07", "danger", 84), col(txt("OPS-07", 18, T["ink"], 700, mono=True), txt("Ama · Operations", 12.5, T["dim"]),
                                                      txt("a file out of place", 12, T["danger"], 600), gap=3), gap=18),
               tk_line("In front", "Excel · budget-2026.xlsx", "accent"), tk_line("Idle for", "3 minutes"),
               tk_line("Processor", "22 %"), tk_line("Memory", "61 %"),
               (f'<div style="width: 100%; height: 150px; border-radius: 12px; background: rgba(255,255,255,0.03); box-shadow: inset 0 0 0 1px {T["line2"]}; '
                f'display: flex; flex-direction: column; gap: 6px; align-items: center; justify-content: center; font-family: {T["sans"]};">'
                f'{ic("camera", 18, T["faint"])}<span style="font-size: 11.5px; color: {T["faint"]};">Their screen is not carried yet</span></div>'),
               txt("A live state, not a viewport: nothing streams their screen.", 11, T["faint"]), gap=9, extra="width: 396px;")
    run = col(*[row(ic(i, 16, T[t]), col(txt(n, 12.5, T["ink"], 500), txt(s_, 11, T["faint"]), gap=1), sp(), txt("Run", 12, T["accent"], 600), gap=11,
                    extra=f"width: 100%; padding: 8px 0; border-bottom: 1px solid {T['line']};")
                for i, t, n, s_ in [("bell", "accent", "Notify Ama", "a message on her screen"), ("lock", "accent", "Lock the screen", "for a set time"),
                                    ("stop", "accent", "Close Excel", "unsaved work is lost"), ("eye", "ok", "Programs running", "what is open, and how long")]],
              txt("The Actions library, aimed at this one machine.", 11, T["faint"], extra="padding-top: 4px;"), gap=0, extra="width: 396px;")
    files = col(thing_card("file", "danger", "budget-2026.xlsx", "Restricted · out of place here", "out of place", "danger"),
                thing_card("file", "accent", "reconciliation-q3.docx", "a task's target · created 13:05"),
                thing_card("folder", "ok", "Resources", "every file this machine should have", "all present", "ok"),
                gap=9, extra="width: 396px;")
    work = col(thing_card("tasks", "danger", "Quarterly report", "final deadline was yesterday", "overdue", "danger"),
               thing_card("flows", "accent", "Handbook → this machine", "from WS-OPS-A1", "syncing"),
               txt("What Ama sees now", 11.5, T["faint"], 600, extra="padding-top: 6px;"),
               (f'<div style="padding: 11px 13px; border-radius: 12px; box-shadow: inset 0 0 0 1px rgba(221,138,138,0.45); font-size: 12px; '
                f'color: {T["ink"]}; font-family: {T["sans"]}; line-height: 1.45;">Your Admin, R. Mensah, is in charge of this machine for now. '
                f'You can use it again when they leave.</div>'), gap=9, extra="width: 396px;")
    return work_page(
        "Inside OPS-07", "hierarchy", ["Operations", "OPS-07"], "OPS-07", "Ama's machine · you are holding it", "danger",
        [lid,
         row(kcell("The machine, live", "a file out of place", "danger", live, w=440, h=620, top=True),
             col(kcell("Run here", "the library, aimed", "accent", run, w=440, h=300, top=True),
                 kcell("Its files", "one out of place", "danger", files, w=440, h=300, top=True), gap=20, extra="flex: none;"),
             kcell("Its work", "one overdue", "danger", work, w=440, h=620, top=True),
             gap=20, align="stretch", extra="flex: none;")],
        "CP03 · Level 4 under level 3's lid, one level down. The machine as its screen mark at 84 with its live facts; the Actions "
        "library aimed at it; its files and work as cards; what Ama sees (CP02).",
        eyebrow("PAGE", "A client PC — level 4, holding", "a lid over three columns"))


BATCH2_PAGES = [("RC03-Record.dc.html", "Record: from the picks", rc03),
                ("RO03-Rollout.dc.html", "Rollout: from the picks, paged", ro03),
                ("WK03-Work.dc.html", "Work: from the picks", wk03),
                ("RS03-Resources.dc.html", "Resources: from the picks", rs03),
                ("CP03-ClientPC.dc.html", "Client PC: level 4, from the picks", cp03)]
