# ================================================================== OV01, DP18: the Overview and the department, brought to PATTERNS.md
# Levels 1 and 2 were designed and BUILT before the patterns that now work were found (K01, DP05). Both still draw
# machines as coloured squares, shrink them to fit, and read some things as shapes that should be words. This is
# the same two pages, brought to design/PATTERNS.md:
#   * machines are small screens at full size, paged sideways, the one that needs someone named at the edge
#   * card stacks page vertically by their bottom edge; the trail scrolls (PATTERNS 3)
#   * anything read to act on is written, with its act on the card (PATTERNS 0)
#   * the day keeps its timeline, with axis and legend
# The Overview keeps its approved shape (K01, the perfect 2 x 2) and its four names; the department keeps its
# pinwheel and its four names (Who governs, Its machines, Today, Waiting on you). What is drawn inside them changes.

def v_edge(more, needs="", w=396):
    """The bottom edge of a card stack as its pager (PATTERNS 3, vertical)."""
    return row(sp(), ic("chevd", 15, T["dim"]), txt(more, 11.5, T["dim"], 600), txt(needs, 11, T["warn"], 600) if needs else "", sp(),
               gap=8, extra=f"width: {w}px; box-sizing: border-box; padding: 9px 0 7px; border-radius: 0 0 12px 12px; "
                             f"background: linear-gradient(180deg, rgba(255,255,255,0), rgba(255,255,255,0.06));")


def dept_card(name, stamp, admins, machines, state, tone=None, act=""):
    faces = row(*[av(i, "admin", 26) for i in admins], gap=-6) if admins else txt("nobody", 12, T["danger"], 600)
    return row(f'<span style="width: 9px; height: 9px; border-radius: 3px; background: {stamp}; flex: none;"></span>',
               col(txt(name, 13.5, T["ink"], 600), txt(f"{machines} machines", 11, T["faint"]), gap=1), faces, sp(),
               txt(state, 11.5, tone_c(tone, T["faint"]), 600) if state else "", act, gap=12,
               extra=f"width: 100%; box-sizing: border-box; padding: 12px 14px; border-radius: 14px; background: {T['pane']};")


# ------------------------------------------------------------------ OV01: the Overview (level 1), to the patterns
def ov01():
    authority = col(
        dept_card(("Operations"), DEPT_COLOR["Operations"], ["RM", "AQ"], 14, "A. Quaye helping Finance", "accent"),
        dept_card("Finance", DEPT_COLOR["Finance"], ["KB"], 2, ""),
        dept_card("Logistics", DEPT_COLOR["Logistics"], [], 2, "", act=gbtn("Assign an Admin", size="sm")),
        txt("Every machine belongs to a department; every Admin there governs all of them.", 11, T["faint"]),
        gap=9, extra="width: 626px;")
    # the stable order, by hostname -- paging never re-sorts; what lags off-screen is named at the edge
    ops = [("01", "ok", "Kojo", "on 1.4.2", None), ("02", "ok", "Efua", "on 1.4.2", None), ("03", "ok", "Yaw", "on 1.4.2", None),
           ("04", "ok", "Adjoa", "on 1.4.2", None)]
    rollout = col(
        row(txt("1.4.2", 22, T["ink"], 700, mono=True), txt("on 16 of 18 machines", 13, T["dim"]), gap=10, extra="align-items: baseline;"),
        paged_row(ops, 4, 44, "14 more", "OPS-06, LOG-02 behind", w=626),
        row(ic("warn", 14, T["warn"]), txt("1.4.3 waits for OPS-06 and LOG-02.", 12.5, T["ink"], 500), sp(),
            txt("Open Rollout", 12, T["accent"], 500), ic("chev", 12, T["accent"]), gap=7, extra="width: 626px;"),
        gap=14, extra="width: 626px;")
    today = col(dept_day(w=626, lane_h=12, gap_y=6), gap=0, extra="width: 626px;")
    place = col(
        thing_card("file", "danger", "budget-2026.xlsx is out of place", "Restricted · on OPS-07, Operations", "new", "danger"),
        thing_card("warn", "warn", "A hostname did not match", "OPS-05 · logged, not addressed"),
        thing_card("reports", "warn", "Two reports wait on you", "a listener report, a flow failure", "open", "warn"),
        v_edge("1 more", "", 626),
        gap=9, extra="width: 626px;")
    brow = eyebrow("PAGE", "Must see — to the patterns", "the perfect grid, kept")
    head = row(sp(), txt("Wednesday, 14:20", 12.5, T["frame_faint"]), gap=0, extra="width: 100%; flex: none;")
    inner = col(brow, head,
                row(kcell("Authority", "one department ungoverned", "danger", authority, w=670, h=330, top=True),
                    kcell("Rollout", "two machines behind", "warn", rollout, w=670, h=330), gap=20, extra="flex: none;"),
                row(kcell("Today", "you entered one machine", "danger", today, w=670, h=330, top=True),
                    kcell("Out of place", "three things", "danger", place, w=670, h=330, top=True), gap=20, extra="flex: none;"),
                row(txt("OV01 · K01's grid and names kept. Inside: departments as cards, the fleet as screens paged with what lags "
                        "named at the edge, the day's timeline with its legend, what is out of place as cards paging down.", 11.5,
                        T["frame_faint"]), gap=0, extra="flex: none;"),
                gap=12, extra="flex: 1; min-width: 0; display: flex; flex-direction: column; padding: 6px 22px 8px 6px; "
                              "box-sizing: border-box; overflow: hidden;")
    return page("Must see", topbar2([IND["rollout"], IND["pings"]], "Go to, do, find"), held_rail("mustsee", SU_AREAS), inner,
                statusbar("Connected, TLS pinned", "no session", "ok"), "native")


# ------------------------------------------------------------------ DP18: the department (level 2), to the patterns
def dp18():
    pcs = [("01", "ok", "Kojo", "at the PC", None), ("02", "free", "Efua", "free", None), ("03", "ok", "Yaw", "at the PC", None),
           ("04", "entered", "Adjoa", "R. Mensah entered", "warn"), ("05", "ok", "Nana", "at the PC", None),
           ("06", "warn", "Kwame", "a version behind", "warn"), ("07", "danger", "Ama", "a file out of place", "danger")]
    machines = col(paged_row(pcs, 6, 70, "1 more", "OPS-07 needs you", w=856),
                   txt("Quiet means fine. A machine in colour says why beneath it.", 11.5, T["faint"], extra="text-align: center;"),
                   gap=10, extra="width: 856px;")
    waiting = col(
        thing_card("shield", "danger", "A restricted file on OPS-07", "budget-2026.xlsx · 11:41", "new", "danger"),
        thing_card("clock", "danger", "Ama's report is overdue", "final deadline was yesterday"),
        v_edge("3 more", "", 396),
        gap=9, extra="width: 396px;")
    govern = col(
        person_card("RM", "R. Mensah", "at their workstation since 08:14 · 8 tasks", None, "selected"),
        person_card("AQ", "A. Quaye", "helping Finance since 10:40 · 4 tasks", "accent"),
        txt("Both govern all seven machines. Double-click one to open them.", 11, T["faint"]),
        gap=9, extra="width: 396px;")
    today = dept_day(w=856, lane_h=16, gap_y=7)
    brow = eyebrow("PAGE", "A department — to the patterns", "the pinwheel, kept")
    title = col(row(txt("Authority", 12.5, T["frame_faint"]), ic("chev", 12, T["frame_faint"]), txt("Operations", 12.5, "#fff", 600), gap=6),
                row(txt("Operations", 24, "#fff", 700), f'<span style="width: 9px; height: 9px; border-radius: 3px; background: {DEPT_COLOR["Operations"]};"></span>',
                    txt("seven machines · two Admins", 13, T["frame_dim"]), sp(), txt("Wednesday, 14:20", 12.5, T["frame_faint"]),
                    gap=12, extra="width: 100%;"), gap=5, extra="flex: none;")
    inner = col(brow, title,
                row(kcell("Its machines", "three need looking at", "warn", machines, w=900, h=300),
                    kcell("Waiting on you", "five things", "danger", waiting, w=440, h=300, top=True), gap=20, extra="flex: none;"),
                row(kcell("Who governs", "two Admins", "dim", govern, w=440, h=356, top=True),
                    kcell("Today", "an Admin entered one machine", "warn", today, w=900, h=356, top=True), gap=20, extra="flex: none;"),
                row(txt("DP18 · DP05's pinwheel and names kept, its machines moved to the wide cell: screens at full size, paged, the "
                        "hidden one that needs you named at the edge. Waiting on you pages down. Who governs as cards.", 11.5,
                        T["frame_faint"]), gap=0, extra="flex: none;"),
                gap=12, extra="flex: 1; min-width: 0; display: flex; flex-direction: column; padding: 6px 22px 8px 6px; "
                              "box-sizing: border-box; overflow: hidden;")
    return page("Operations", topbar2([IND["rollout"], IND["pings"]], "Go to, do, find"), held_rail("authority", SU_AREAS), inner,
                statusbar("Connected, TLS pinned", "no session", "ok"), "native")


BATCH3 = [("OV01-Overview.dc.html", "Must see: to the patterns", ov01),
          ("DP18-Department.dc.html", "A department: to the patterns", dp18)]
