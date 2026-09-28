# ================================================================== OV03, AS04: the two surfaces the build was missing
# Written 28 Sep 2026, after the page audit found that:
#
#   * the Super User's AUTHORITY area had no board at all and was still the pre-kit console screen --
#     a sidebar, a card strip and a detail card printing account and PC ids; and
#   * ASSISTED ACCESS had no page at all. Its only GUI was `HierarchyView.qml`, which nothing mounted,
#     so the whole combo was reachable from the TUI and nowhere else.
#
# Both are drawn here to the patterns, and both are built (`AuthorityView.qml`, the Assistance page's
# "Help from another department" cell).
#
# T06 stays as it is, and stays PARKED: it draws a richer future -- the helper watching the requester's
# screen -- which the Engine cannot supply (a screenshot Action returns a path, not an image, see
# design/ENGINE-WORK.md). AS04 is what exists.


# ------------------------------------------------------------------ OV03: the Authority area
# Its signature is THREE COLUMNS of unequal width, so it reads as neither Must see's quartet nor the
# department's pinwheel. Display names live here and nowhere else: a name is private to the namer and
# never propagates across relationship layers, so the page only ever says what YOU see and what others
# see of YOU -- never what one person calls another.
def ov03():
    depts = col(
        dept_card("Operations", DEPT_COLOR["Operations"], ["RM", "AQ"], 7, "A. Quaye assisting elsewhere", "accent"),
        dept_card("Finance", DEPT_COLOR["Finance"], ["KB"], 4, ""),
        dept_card("Logistics", DEPT_COLOR["Logistics"], [], 3, "", act=gbtn("Assign an Admin", size="sm")),
        v_edge("2 more departments", "Harbour has nobody", 356), gap=9, extra="width: 356px;")

    people = col(
        person_card("RM", "R. Mensah", "Operations · at their workstation"),
        person_card("AQ", "A. Quaye", "Operations · helping another department", "accent"),
        person_card("KB", "K. Boateng", "Finance · not signed in", "warn", right="selected"),
        person_card("MA", "M. Addo", "Harbour · at their workstation"),
        v_edge("3 more", "", 476), gap=9, extra="width: 476px;")

    gap_cell = col(
        thing_card("dept", "danger", "Logistics", "3 machines, unattended", "Assign an Admin", "danger"),
        thing_card("dept", "danger", "Harbour", "no machines yet", "Assign an Admin", "danger"),
        gap=9, extra="width: 356px;")

    naming = col(
        reading_block("K. Boateng is the name you see for them.",
                      [("You see them as", "K. Boateng", ""), ("They see you as", "the Super User", ""),
                       ("Department", "Finance", "")],
                      "Call them something else", w=356),
        row(txt("Everyone below you sees the name on your account.", 11, T["faint"]), gap=0,
            extra="width: 356px; padding-top: 4px;"),
        row(gbtn("What they call you", "user", size="sm"), gap=0, extra="width: 356px;"),
        gap=12, extra="width: 356px;")

    head = row(txt("Logistics has nobody governing it.", 12.5, T["danger"]), sp(),
               gbtn("New department", "plus", size="sm"),
               txt("Wednesday, 14:20", 12.5, T["frame_faint"]), gap=16, extra="width: 100%; flex: none;")

    body = row(kcell("The departments", "5 departments, one empty", "danger", depts, w=400, h=690, top=True),
               kcell("The people", "K. Boateng of 7", "dim", people, w=520, h=690, top=True),
               col(kcell("Where nobody governs", "Logistics unattended", "danger", gap_cell, w=400, h=300, top=True),
                   kcell("What you call them", "your names only", "accent", naming, w=400, h=370, top=True),
                   gap=20, extra="flex: none; display: flex; flex-direction: column;"),
               gap=20, align="flex-start", extra="flex: 1; min-height: 0;")

    inner = col(eyebrow("PAGE", "Authority — who governs what", "the last pre-kit screen, rebuilt"), head, body,
                row(txt("OV03 · Three columns, widths unequal — the page's own signature. Display names are set here "
                        "and nowhere else, and no account or PC id appears anywhere on it.", 11.5, T["frame_faint"]),
                    gap=0, extra="flex: none;"),
                gap=12, extra="flex: 1; min-width: 0; display: flex; flex-direction: column; padding: 6px 22px 8px 6px; "
                              "box-sizing: border-box; overflow: hidden;")
    return page("Authority", topbar2([IND["rollout"], IND["pings"]], "Go to, do, find"),
                held_rail("authority", SU_AREAS), inner,
                statusbar("Connected, TLS pinned", "no session", "ok"), "native")


# ------------------------------------------------------------------ AS04: assisted access, as built
# CONSENT, NOT EVICTION, and the difference is carried by words rather than by a fifth colour: PATTERNS
# 9 allows four toned meanings, and T06's teal would have been a fifth. What the helper may do is said
# before either side agrees; there is no clock anywhere in it; either party ends it.
#
# It is an ADMIN's surface. Every assisted_access handler refuses anyone else -- a Super User traverses
# instead -- so for them the cell is simply not there.
def as04():
    def state_row(*words):
        return row(*words, gap=14, extra="width: 372px; padding-top: 6px;")

    offer = col(
        row(ic("assistance", 17, T["accent"]), txt("A. Quaye needs help", 14, T["ink"], 600), gap=10),
        txt("They would let you run control actions, monitoring checks on their machine.",
            11.5, T["accent"], extra="line-height: 1.4;"),
        row(tbtn("Help them", "accent", "assistance", size="sm"), gbtn("Not now", size="sm"), gap=8),
        gap=8, extra=f"width: 372px; box-sizing: border-box; padding: 14px; border-radius: 14px; "
                     f"background: {T['accent_soft']};")

    running = col(
        txt("Helping A. Quaye", 14, T["ink"], 600),
        txt("You may run control actions, monitoring checks. It ends when either of you closes it.",
            11, T["faint"], extra="line-height: 1.4;"),
        row(gbtn("End it", "stop", size="sm"), gap=0),
        gap=6, extra=f"width: 372px; box-sizing: border-box; padding: 14px; border-radius: 14px; background: {T['pane']};")

    asking = col(
        txt("You are not available, and nobody is being helped.", 14, T["ink"], 600),
        row(txt("Ask", 12.5, T["dim"]),
            f'<span style="display: inline-flex; align-items: center; gap: 6px; padding: 5px 10px; border-radius: 7px; '
            f'background: {T["accent_soft"]}; color: {T["accent"]}; font-family: {T["sans"]}; font-size: 12.5px; '
            f'font-weight: 600;">anyone free {ic("chevd", 12, T["accent"])}</span>',
            tbtn("Ask for help", "accent", "assistance", size="sm"), gap=8, extra="padding-top: 4px;"),
        f'<div style="width: 372px; height: 1px; background: {T["line"]};"></div>',
        state_row(txt("You are", 11, T["faint"]),
                  txt("available to help", 11, T["faint"]),
                  txt("not available", 11, T["ink"], 600)),
        gap=10, extra="width: 372px;")

    help_cell = col(offer, running, asking, gap=12, extra="width: 372px;")

    asking_for_you = col(
        col(row(ic("ping", 17, T["warn"]), txt("Kojo is asking for you", 14, T["ink"], 600), gap=10),
            txt("Pinged twice — 09:40, again at 10:15 · OPS-01", 11, T["warn"]),
            row(tbtn("Answer Kojo", "warn", size="sm"), sp(), txt("stays lit until you answer", 11, T["faint"]), gap=8,
                extra="width: 100%;"),
            gap=8, extra=f"width: 372px; box-sizing: border-box; padding: 16px; border-radius: 14px; background: {T['warn_soft']};"),
        gap=10, extra="width: 372px;")

    channel = col(
        row(av("AM", "worker", 34), col(txt("Ama", 13.5, T["ink"], 600), txt("OPS-07 · opened 11:01", 11, T["faint"]), gap=1),
            sp(), gap=10, extra="width: 100%;"),
        txt("I can't open the budget file any more.", 12.5, T["dim"]),
        txt("It is restricted; it should not be on your machine. Move it to Documents.", 12.5, T["ink"],
            extra=f"align-self: flex-end; max-width: 300px; padding: 10px 12px; border-radius: 12px; background: {T['pane']};"),
        gap=12, extra="width: 420px;")

    body = row(kcell("Asking for you", "a ping", "warn", asking_for_you, w=420, h=690, top=True),
               kcell("Ama", "your turn", "accent", channel, w=460, h=690, top=True),
               kcell("Help from another department", "1 asking", "warn", help_cell, w=420, h=690, top=True),
               gap=20, align="flex-start", extra="flex: 1; min-height: 0;")

    head = row(txt("Assistance", 24, "#fff", 700), txt("one person asking for you", 13, T["warn"]), sp(),
               txt("Wednesday, 14:20", 12.5, T["frame_faint"]), gap=12, extra="width: 100%; flex: none;")

    inner = col(eyebrow("PAGE", "Assisted access — as built", "consent, a ceiling in words, no clock"), head, body,
                row(txt("AS04 · The Admin's Assistance page. Asking, being asked, and the help running — all in the cell "
                        "that asked, no modal. The ceiling is the Engine's; the page may only narrow it, and says it in words.",
                        11.5, T["frame_faint"]), gap=0, extra="flex: none;"),
                gap=12, extra="flex: 1; min-width: 0; display: flex; flex-direction: column; padding: 6px 22px 8px 6px; "
                              "box-sizing: border-box; overflow: hidden;")
    return page("Assistance", topbar2([IND["pings"]], "Go to, do, find"),
                held_rail("assistance", ADMIN_AREAS, foot=("AD", "Admin")), inner,
                statusbar("Connected, TLS pinned", "no session", "ok"), "native")


AUTHORITY_PAGES = [("OV03-Authority.dc.html", "Authority: who governs what", ov03),
                   ("AS04-Assisted.dc.html", "Assisted access, as built", as04)]
