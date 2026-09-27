# ================================================================== RO05, RO06, OV02: a fleet that scales -- departments, then maximise
# The user, 27 Sep 2026, on RO04: "what if the departments are many, what if the pcs are many ... We decide on
# maximize approach for those pc design so how are you going to make that work ... this multi department in one
# container not really cutting it, if it one department then yep. Maybe we need to rethink the design."
#
# THE RULE (PATTERNS.md 3a): a container never holds more than one department's machines.
#   * A page about many departments shows DEPARTMENTS: one card each, a count and a thin progress line, and only
#     the machines that need someone, as small screens with their reason. A department with nothing wrong is one
#     quiet line. Many departments page down by the stack's bottom edge, naming any hidden one that needs you.
#   * Double-click a department to MAXIMISE it (DP11): that one department fills the page, its machines at full size
#     in a grid, its words beside them.
#   * Inside one department the set's size picks the drawing: one row in a cell pages sideways; a maximised grid
#     fills the area and pages DOWN by rows, with plain-text filters (All · Behind · Offline). The order is stable.

PREFIX = {"Operations": "OPS", "Logistics": "LOG", "Finance": "FIN", "Harbour": "HAR", "Customs": "CUS", "Records": "REC",
          "Procurement": "PRO", "Legal": "LEG", "Payroll": "PAY", "Fleet": "FLT"}
ROLLOUT_DEPTS = [("Operations", "#6C8EEF", 14, 13, [("06", "warn", "failed 6×")]),
         ("Logistics", "#3FB68B", 2, 1, [("02", "danger", "offline")]),
         ("Finance", "#E07A4F", 22, 22, []),
         ("Harbour", "#C58AF0", 48, 46, [("17", "warn", "failed 3×"), ("31", "warn", "failed 2×")]),
         ("Customs", "#E5C15D", 31, 31, []),
         ("Records", "#5CC4D6", 9, 9, []),
         ("Procurement", "#EF8FB0", 17, 17, []),
         ("Legal", "#9AA7B8", 6, 6, []),
         ("Payroll", "#8FD16A", 12, 12, []),
         ("Fleet", "#D98B5F", 64, 63, [("41", "danger", "offline")])]


def rollout_card(name, stamp, total, on, behind, w=856, compact=False):
    """One department's rollout. Fine: one quiet line. Not fine: the lagging machines as small screens with reasons."""
    pct = on / total
    bar = (f'<div style="width: {140 if compact else 200}px; height: 4px; border-radius: 2px; background: rgba(255,255,255,0.10); flex: none;">'
           f'<div style="width: {int(pct * 100)}%; height: 4px; border-radius: 2px; background: {T["dim"]};"></div></div>')
    head = row(f'<span style="width: 9px; height: 9px; border-radius: 3px; background: {stamp}; flex: none;"></span>',
               txt(name, 13, T["ink"], 600, extra=f"width: {100 if compact else 130}px; flex: none;"), bar,
               txt(f"{on} of {total}", 12, T["dim"], extra="width: 64px; flex: none;"), sp(),
               *([row(*[row(calm_slot(n, st, 30), col(txt(f"{PREFIX[name]}-{n}", 11, T[st], 600, mono=True), txt(why, 10.5, T["faint"], extra="white-space: nowrap;"), gap=0),
                            gap=7) for n, st, why in behind], gap=16)] if behind else [txt("all current", 11.5, T["faint"])]),
               ic("chev", 13, T["faint"]), gap=14, extra="width: 100%;")
    pad = "10px 14px" if not behind else "8px 14px"
    return row(head, gap=0, extra=f"width: {w}px; box-sizing: border-box; padding: {pad}; border-radius: 14px; background: {T['pane']};")


# ------------------------------------------------------------------ RO05: Rollout with ten departments
def ro05():
    cards = [rollout_card(*d, w=856) for d in ROLLOUT_DEPTS[:7]]
    fleet = col(plain_tabs(["Every department", "Behind only"], "Every department"), *cards,
                v_edge("3 more departments", "Fleet has one offline", 856),
                txt("Double-click a department to open its machines.", 11, T["faint"]), gap=8, extra="width: 856px;")
    gate = col(txt("1.4.3 can't be approved yet.", 15, T["ink"], 600, extra="line-height: 1.35;"),
               txt("Five machines in four departments are still on 1.4.1.", 12, T["dim"], extra="line-height: 1.45;"),
               row(tbtn("Approve 1.4.3", "accent", "check", disabled=True), gap=0),
               txt("This unlocks by itself when they catch up.", 11.5, T["faint"]), gap=11, extra="width: 396px;")
    holding = col(
        stall_card(calm_slot("06", "warn", 36), "OPS-06 won't update", "Operations · 6 tries since Friday",
                   tbtn("Ask R. Mensah", "warn", size="sm")),
        stall_card(calm_slot("02", "danger", 36), "LOG-02 is offline", "Logistics · nobody governs it", gbtn("Assign", size="sm")),
        v_edge("3 more", "", 396), gap=9, extra="width: 396px;")
    return area_page(
        "Rollout", "rollout", ["Rollout"], "Rollout", "1.4.2 on 220 of 225 machines · 10 departments", "warn",
        [row(kcell("By department", "four with machines behind", "warn", fleet, w=900, h=676, top=True),
             col(kcell("The gate", "1.4.3 waits", "warn", gate, w=440, h=300, top=True),
                 kcell("Holding it up", "five machines", "warn", holding, w=440, h=356, top=True), gap=20, extra="flex: none;"),
             gap=20, align="stretch", extra="flex: none;")],
        "RO05 · Ten departments, 225 machines: one card per department, only the machines behind drawn (small screens with their "
        "reason), the rest one quiet line. The stack pages down and names what it hides. Double-click opens one department.",
        eyebrow("PAGE", "Rollout — at scale", "departments, then maximise"))


# ------------------------------------------------------------------ RO06: one department maximised
def ro06():
    states = {17: ("warn", "failed 3×"), 31: ("warn", "failed 2×")}
    grid_rows = []
    for r in range(4):
        cells = []
        for c in range(8):
            n = r * 8 + c + 1
            st, why = states.get(n, ("ok", "on 1.4.2"))
            cells.append(col(calm_slot(f"{n:02d}", st, 58), txt(f"HAR-{n:02d}", 11, T["ink"] if st != "ok" else T["dim"], 600 if st != "ok" else 400, mono=True),
                             txt(why, 10, T[st] if st != "ok" else T["faint"], 500 if st != "ok" else 400), gap=2,
                             extra="align-items: center; width: 92px;"))
        grid_rows.append(row(*cells, gap=10, justify="center", extra="width: 856px;"))
    grid = col(row(plain_tabs(["All 48", "Behind 2", "Offline 0"], "All 48"), sp(), txt("1–32 of 48", 11.5, T["faint"], mono=True), gap=0,
                   extra="width: 856px;"),
               *grid_rows, v_edge("16 more", "", 856), gap=12, extra="width: 856px;")
    words = col(txt("46 of Harbour's 48 machines are on 1.4.2.", 15, T["ink"], 600, extra="line-height: 1.35;"),
                stall_card(calm_slot("17", "warn", 36), "HAR-17 won't update", "3 tries since Monday", tbtn("Ask M. Addo", "warn", size="sm")),
                stall_card(calm_slot("31", "warn", 36), "HAR-31 won't update", "2 tries since Tuesday", tbtn("Ask M. Addo", "warn", size="sm")),
                tk_line("Governed by", "M. Addo, J. Tetteh"), tk_line("Retries", "run by themselves when idle"),
                gap=10, extra="width: 396px;")
    brow = eyebrow("PAGE", "Rollout — one department, maximised", "a grid and its words")
    title = col(row(txt("Rollout", 12.5, T["frame_faint"]), ic("chev", 12, T["frame_faint"]), txt("Harbour", 12.5, "#fff", 600), gap=6),
                row(txt("Harbour", 24, "#fff", 700), f'<span style="width: 9px; height: 9px; border-radius: 3px; background: #C58AF0;"></span>',
                    txt("48 machines · two behind", 13, T["warn"], 500), sp(), txt("Esc to go back", 12.5, T["frame_faint"]), gap=12,
                    extra="width: 100%;"), gap=5, extra="flex: none;")
    inner = col(brow, title,
                row(kcell("Its machines", "two behind", "warn", grid, w=900, h=676, top=True),
                    kcell("What it says", "two to chase", "warn", words, w=440, h=676, top=True), gap=20, extra="flex: none;"),
                row(txt("RO06 · Maximised (DP11): one department fills the page. Its machines at 58 in a grid that pages DOWN by rows "
                        "(32 at a time, so 200 machines is seven pages, not fifty), plain-text filters to see only what's behind, "
                        "and its words beside it.", 11.5, T["frame_faint"]), gap=0, extra="flex: none;"),
                gap=12, extra="flex: 1; min-width: 0; display: flex; flex-direction: column; padding: 6px 22px 8px 6px; "
                              "box-sizing: border-box; overflow: hidden;")
    return page("Harbour", topbar2([IND["rollout"], IND["pings"]], "Go to, do, find"), held_rail("rollout", SU_AREAS), inner,
                statusbar("Connected, TLS pinned", "no session", "ok"), "native")


# ------------------------------------------------------------------ OV02: the Overview's Rollout cell, at scale
def ov02():
    authority = col(
        dept_card("Operations", DEPT_COLOR["Operations"], ["RM", "AQ"], 14, "A. Quaye helping Finance", "accent"),
        dept_card("Logistics", DEPT_COLOR["Logistics"], [], 2, "", act=gbtn("Assign an Admin", size="sm")),
        dept_card("Harbour", "#C58AF0", ["MA", "JT"], 48, ""),
        v_edge("7 more departments", "", 626), gap=9, extra="width: 626px;")
    rollout = col(
        row(txt("1.4.2", 22, T["ink"], 700, mono=True), txt("on 220 of 225 machines", 13, T["dim"]), gap=10, extra="align-items: baseline;"),
        *[rollout_card(*d, w=626, compact=True) for d in [ROLLOUT_DEPTS[0], ROLLOUT_DEPTS[1], ROLLOUT_DEPTS[3]]],
        v_edge("7 more · all current but Fleet", "", 626), gap=8, extra="width: 626px;")
    today = col(dept_day(w=626, lane_h=12, gap_y=6), gap=0, extra="width: 626px;")
    place = col(
        thing_card("file", "danger", "budget-2026.xlsx is out of place", "Restricted · on OPS-07, Operations", "new", "danger"),
        thing_card("warn", "warn", "A hostname did not match", "OPS-05 · logged, not addressed"),
        thing_card("reports", "warn", "Two reports wait on you", "a listener report, a flow failure", "open", "warn"),
        v_edge("1 more", "", 626), gap=9, extra="width: 626px;")
    head = row(sp(), txt("Wednesday, 14:20", 12.5, T["frame_faint"]), gap=0, extra="width: 100%; flex: none;")
    inner = col(eyebrow("PAGE", "Must see — at scale", "the perfect grid, kept"), head,
                row(kcell("Authority", "one department ungoverned", "danger", authority, w=670, h=330, top=True),
                    kcell("Rollout", "five machines behind", "warn", rollout, w=670, h=330, top=True), gap=20, extra="flex: none;"),
                row(kcell("Today", "you entered one machine", "danger", today, w=670, h=330, top=True),
                    kcell("Out of place", "three things", "danger", place, w=670, h=330, top=True), gap=20, extra="flex: none;"),
                row(txt("OV02 · The Overview at ten departments: Authority and Rollout are department cards that page down, only machines "
                        "behind are drawn. No cell holds more than one department's machines.", 11.5, T["frame_faint"]), gap=0, extra="flex: none;"),
                gap=12, extra="flex: 1; min-width: 0; display: flex; flex-direction: column; padding: 6px 22px 8px 6px; "
                              "box-sizing: border-box; overflow: hidden;")
    return page("Must see", topbar2([IND["rollout"], IND["pings"]], "Go to, do, find"), held_rail("mustsee", SU_AREAS), inner,
                statusbar("Connected, TLS pinned", "no session", "ok"), "native")


BATCH4 = [("RO05-Rollout.dc.html", "Rollout: at scale, by department", ro05),
          ("RO06-Harbour.dc.html", "Rollout: one department maximised", ro06),
          ("OV02-Overview.dc.html", "Must see: at scale", ov02)]
