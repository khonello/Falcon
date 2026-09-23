# ================================================================== INDEX: what every board is
# The canvas had grown past the point where a board's name told you what it was for. This board is
# the contents page: the three Super User pages, the slots each one has, and which chart board
# offers the alternatives for that slot.
#
# Read it as: a PAGE is a screen. A SLOT is one panel on that screen. A C-board is the set of ways
# that slot's chart could be drawn. An L-board is a way of arranging the slots.

PAGES = [
    ("1", "At a glance", "the system's condition, in figures and the charts behind them", [
        ("The figures", "C10", "four numbers, nothing drawn", "band"),
        ("Rollout", "C01", "one version across the departments", "wide"),
        ("The fleet", "C02", "one mark per client PC", "narrow"),
        ("Confirmations", "C03", "the rollout landing, over the week", "wide"),
        ("Work, by department", "C09", "tasks and flows, the same two measures", "narrow"),
    ]),
    ("2", "The hierarchy", "who governs what, and what crosses between them", [
        ("The hierarchy", "C04", "department → Admin → PC", "wide"),
        ("Assistance", "C06", "who helped whom, across departments", "narrow"),
        ("Report routing", "C07", "where each category of report goes", "narrow"),
        ("— descended into one department —", "", "", "rule"),
        ("Its Admins", "—", "a list, not a chart", "narrow"),
        ("Sessions here", "C05", "the same timeline, scoped", "wide"),
        ("In numbers", "C01 + C09", "its rollout and its work", "narrow"),
    ]),
    ("3", "The record", "what actually happened today", [
        ("Sessions today", "C05", "who held each PC, and for how long", "wide"),
        ("Violations by tier", "C08", "files where their tier does not allow them", "narrow"),
        ("Deviations", "—", "a list, not a chart", "narrow"),
    ]),
]

LAYOUT_NOTE = [
    ("L01", "Three — a band over two charts", "suits page 1: the figures are read first"),
    ("L02", "Three — one subject, two supporting", "suits page 2: the map is the subject"),
    ("L03", "Four, even", "a survey; nothing claims to matter more"),
    ("L04", "Four, weighted", "suits page 3: the timeline is the lead story"),
    ("L05", "Five", "the most a page carries before titles do the navigating"),
    ("L06", "Five, asymmetric", "a triage column, then the substance"),
]


def slot_row(name, board, note, kind):
    if kind == "rule":
        return row(f'<span style="flex: 1; height: 1px; background: {T["line"]};"></span>',
                   txt(name, 11, T["faint"]),
                   f'<span style="flex: 1; height: 1px; background: {T["line"]};"></span>',
                   gap=10, extra="width: 100%; padding: 6px 0;")
    tag = (f'<span style="display: inline-flex; align-items: center; height: 20px; padding: 0 8px; '
           f'border-radius: 6px; background: {T["pane"]}; color: {T["accent"] if board not in ("—", "") else T["faint"]}; '
           f'font-family: {T["mono"]}; font-size: 11px; font-weight: 500; flex: none;">{board}</span>')
    return row(f'<span style="width: 6px; height: 6px; border-radius: 3px; background: {T["line2"]}; flex: none;"></span>',
               col(txt(name, 12.5, T["ink"], 500), txt(note, 11, T["faint"]), gap=2, extra="flex: 1; min-width: 0;"),
               tag, gap=10, extra="width: 100%; padding: 7px 0;")


def page_card(num, name, sub, slots, w=416):
    head = col(row(f'<span style="display: inline-flex; align-items: center; justify-content: center; width: 22px; '
                   f'height: 22px; border-radius: 7px; background: {T["accent_soft"]}; color: {T["accent"]}; '
                   f'font-family: {T["mono"]}; font-size: 12px; font-weight: 600; flex: none;">{num}</span>',
                   txt(name, 15, T["ink"], 700), gap=10),
               txt(sub, 11.5, T["faint"]), gap=6, extra="flex: none;")
    return col(head, col(*[slot_row(*s) for s in slots], gap=0, extra="width: 100%;"),
               gap=14, extra=f"width: {w}px; padding: 18px 20px; border-radius: 16px; background: {CHART_BG}; "
                             f"box-sizing: border-box; flex: none;")


def legend_card(w=416):
    rows_ = [("PAGE", "a screen the Super User can be on", T["ink"]),
             ("SLOT", "one panel on that screen", T["dim"]),
             ("C01–C10", "the ways that slot's chart could be drawn — pick one per slot", T["accent"]),
             ("L01–L06", "the ways the slots could be arranged — pick one per page", T["accent"]),
             ("D01–D04", "the pages as they are built today", T["dim"])]
    return col(txt("How to read the canvas", 15, T["ink"], 700),
               col(*[row(f'<span style="width: 74px; font-family: {T["mono"]}; font-size: 11.5px; color: {c}; '
                         f'flex: none;">{k}</span>', txt(v, 12, T["dim"]), gap=12, extra="width: 100%; padding: 6px 0;")
                     for k, v, c in rows_], gap=0),
               txt("Everything on this row is Super User only. What carries over to Admin is decided afterwards.",
                   11.5, T["faint"]),
               gap=14, extra=f"width: {w}px; padding: 18px 20px; border-radius: 16px; background: {CHART_BG}; "
                             f"box-sizing: border-box; flex: none;")


def layouts_card(w=416):
    return col(txt("Layouts, and what each is for", 15, T["ink"], 700),
               col(*[row(f'<span style="width: 34px; font-family: {T["mono"]}; font-size: 11.5px; '
                         f'color: {T["accent"]}; flex: none;">{k}</span>',
                         col(txt(n, 12.5, T["ink"], 500), txt(note, 11, T["faint"]), gap=2, extra="flex: 1;"),
                         gap=10, extra="width: 100%; padding: 7px 0;")
                     for k, n, note in LAYOUT_NOTE], gap=0),
               gap=14, extra=f"width: {w}px; padding: 18px 20px; border-radius: 16px; background: {CHART_BG}; "
                             f"box-sizing: border-box; flex: none;")


def index_board():
    cards = [page_card(*p) for p in PAGES]
    inner = col(row(f'<span style="width: 10px; height: 26px; border-radius: 3px; background: #fff;"></span>',
                    txt("What every board is", 22, "#fff", 700),
                    txt("three Super User pages, their slots, and where each slot's alternatives live",
                        13, T["frame_dim"]), gap=12, extra="flex: none;"),
                row(*cards, gap=16, align="flex-start"),
                row(legend_card(), layouts_card(), gap=16, align="flex-start"),
                gap=16, extra=f"width: {W}px; height: {H}px; box-sizing: border-box; padding: 26px 40px; "
                              f"background: {FRAME['native']}; overflow: hidden;")
    return page("What every board is", "", "", inner, "", "native")


INDEX = [("INDEX.dc.html", "Start here: what every board is", index_board)]
