# ================================================================== Batch 1, rethought: MK01, HO03, FL06-FL08, AS03, RP03
# The user, 27 Sep 2026, on HO02-RP02: "Rethink the entirety of the batch 1, I don't like the square with
# dots inside. Rethink it."
#
# Two things change, and both are system-wide:
#   1. THE MACHINE MARK. The calm-slot square (a tile with a dot in its corner) is gone. A machine is drawn
#      as what it is -- a small screen with its number on it. Quiet machines are a faint outline; one that
#      needs someone has its outline and number in the tone, and says why in a word. No dot, no square.
#      `calm_slot` is redefined here, so every board that used the square now draws the screen.
#      MK01 draws the alternatives, so the mark can still be swapped.
#   2. FEWER ICON TILES. Icons sitting in rounded squares read as the same shape family. On these pages an
#      icon stands bare unless it has a reason for a backing.
# And the compositions were reconsidered, not re-skinned: the machines and their one line are ONE thing
# now; lists that were rows are cards; the ping is a banner, not a dot in circles; the timeline is ticks.

def calm_slot(label, state="ok", size=52, sub=""):
    """One machine as a small screen with its number. Quiet unless it needs someone: then its outline and
    number take the exception's tone. 'free' is only fainter -- unused is not a problem."""
    tone = {"warn": T["warn"], "danger": T["danger"], "entered": T["warn"]}.get(state)
    stroke = tone or "rgba(255,255,255,0.30)"
    w, h = size, int(size * 0.66)
    op = 0.45 if state == "free" else 1
    svg = (f'<svg width="{w}" height="{h + 9}" viewBox="0 0 {w} {h + 9}" style="position: absolute; left: 0; top: 0;">'
           f'<rect x="1" y="1" width="{w - 2}" height="{h - 2}" rx="{max(3, int(size * 0.1))}" fill="rgba(255,255,255,0.03)" '
           f'stroke="{stroke}" stroke-width="1.5"/>'
           f'<path d="M{w / 2} {h} V{h + 5} M{w / 2 - size * 0.18} {h + 7} H{w / 2 + size * 0.18}" stroke="{stroke}" '
           f'stroke-width="1.5" stroke-linecap="round"/></svg>')
    num = (f'<span style="position: absolute; left: 0; top: 0; width: {w}px; height: {h}px; display: flex; align-items: center; '
           f'justify-content: center; font-family: {T["mono"]}; font-size: {max(9, int(size * 0.24))}px; font-weight: 600; '
           f'color: {tone or T["dim"]};">{label}</span>') if label else ""
    mark = (f'<span style="position: relative; width: {w}px; height: {h + 9}px; display: inline-block; opacity: {op};">'
            f'{svg}{num}</span>')
    return col(mark, txt(sub, 10.5, T["faint"], extra="text-align: center;") if sub else "", gap=5,
               extra="align-items: center; flex: none;")


def bare_node(x, y, icon, label, sub="", tone="accent", w=150, bad=False):
    """A flow stage as a card with its icon standing bare -- no tile behind it."""
    ring = f"box-shadow: inset 0 0 0 1.5px {T['danger']};" if bad else ""
    colour = T["danger"] if bad else T[tone]
    return (f'<div style="position: absolute; left: {x}px; top: {y}px; width: {w}px; box-sizing: border-box; '
            f'padding: 9px 12px; border-radius: 12px; background: {T["pane"]}; display: flex; align-items: center; gap: 10px; {ring}">'
            f'{ic(icon, 17, colour)}<div style="display: flex; flex-direction: column; gap: 1px; min-width: 0;">'
            f'<span style="font-family: {T["sans"]}; font-size: 12.5px; font-weight: 600; color: {T["ink"]}; white-space: nowrap;">{label}</span>'
            + (f'<span style="font-family: {T["sans"]}; font-size: 10.5px; color: {T["danger"] if bad else T["faint"]}; white-space: nowrap;">{sub}</span>' if sub else "")
            + '</div></div>')


def thing_card(icon, tone, title, sub, right="", rtone=None, sel=False, w=None):
    """Anything that is not a person, as a card: a bare icon, its words, a state word -- no tile."""
    width = f"width: {w}px;" if w else "width: 100%;"
    fill = T["select"] if sel else T["pane"]
    return row(ic(icon, 18, T[tone]), col(txt(title, 12.5, "#fff" if sel else T["ink"], 600),
                                          txt(sub, 11, T["select_sub"] if sel else T["faint"]), gap=2, extra="min-width: 0;"),
               sp(), txt(right, 11.5, tone_c(rtone, T["faint"]), 600) if right else "", gap=12,
               extra=f"{width} box-sizing: border-box; padding: 12px 14px; border-radius: 14px; background: {fill};")


# ------------------------------------------------------------------ MK01: marking a machine, without squares
def mk01():
    pcs = [("01", "ok"), ("02", "free"), ("03", "ok"), ("04", "entered"), ("05", "ok"), ("06", "warn"), ("07", "danger")]
    a = b_cell("A small screen", col(row(*[calm_slot(n, s_, 34) for n, s_ in pcs], gap=6),
                                     txt("the machine as itself; the outline takes the tone", 10.5, T["faint"]), gap=10), "the new default")
    b = b_cell("Numbers only", col(
        row(*[txt(n, 17, tone_c({"entered": "warn", "warn": "warn", "danger": "danger"}.get(s_), T["dim"] if s_ != "free" else T["faint"]),
                  700 if s_ in ("warn", "danger", "entered") else 400, mono=True,
                  extra=(f"border-bottom: 2px solid {T['warn'] if s_ in ('warn', 'entered') else T['danger']}; padding-bottom: 2px;"
                         if s_ in ("warn", "danger", "entered") else "padding-bottom: 4px;")) for n, s_ in pcs], gap=12),
        txt("typographic: the number, underlined when it matters", 10.5, T["faint"]), gap=10), "the quietest")
    c = b_cell("Their people", col(
        row(*[col(f'<span style="width: 30px; height: 30px; border-radius: 15px; display: inline-flex; align-items: center; justify-content: center; '
                  f'font-family: {T["sans"]}; font-size: 11px; font-weight: 700; background: rgba(255,255,255,0.08); color: {T["dim"]}; '
                  + (f'box-shadow: 0 0 0 2px {T["warn"] if s_ in ("warn", "entered") else T["danger"]};' if s_ in ("warn", "danger", "entered") else "")
                  + f'">{i}</span>', gap=0) for i, s_ in zip(["KO", "EF", "YA", "AD", "NA", "KW", "AM"], [p[1] for p in pcs])], gap=7),
        txt("the person at each machine; a coloured circle round the one to look at", 10.5, T["faint"]), gap=10), "people first")
    d = b_cell("One bar, marked", col(
        (f'<div style="position: relative; width: 280px; height: 36px;"><div style="position: absolute; left: 0; right: 0; top: 18px; height: 6px; '
         f'border-radius: 3px; background: rgba(255,255,255,0.10);"></div>'
         + "".join(f'<span style="position: absolute; left: {i * 40 + 14}px; top: {6 if s_ in ("warn", "danger", "entered") else 14}px; width: 2px; '
                   f'height: {18 if s_ in ("warn", "danger", "entered") else 14}px; border-radius: 1px; background: '
                   f'{T["danger"] if s_ == "danger" else T["warn"] if s_ in ("warn", "entered") else "rgba(255,255,255,0.35)"};"></span>'
                   for i, (n, s_) in enumerate(pcs)) + '</div>'),
        txt("the department as one line; the exceptions stand taller", 10.5, T["faint"]), gap=10), "for many machines")
    s1 = msection("Marking a machine — calm, and no square with a dot", a, b, c, d)

    e = b_cell("Screen, with its line", col(
        *[row(calm_slot(n, s_, 30), txt(f"OPS-{n}", 11.5, T["dim"], mono=True), sp(), txt(w_, 11, tone_c(t, T["faint"]), 500), gap=10,
              extra="width: 100%; padding: 2px 0;")
          for n, s_, w_, t in [("04", "entered", "you entered it", "warn"), ("06", "warn", "a version behind", "warn"),
                               ("07", "danger", "a file out of place", "danger")]], gap=4), "the mark and its reason")
    f = b_cell("Only what needs you", col(
        txt("5 machines are fine.", 13, T["dim"]),
        *[row(calm_slot(n, s_, 30), txt(w_, 12, tone_c(t, T["faint"]), 600), gap=10) for n, s_, w_, t in
          [("06", "warn", "OPS-06 is a version behind", "warn"), ("07", "danger", "OPS-07 has a file out of place", "danger")]], gap=8),
        "the fine ones folded into a sentence")
    g = b_cell("At scale", col(row(*[calm_slot("", s_, 16) for s_ in (["ok"] * 18 + ["warn"] + ["ok"] * 9 + ["danger"] + ["ok"] * 7)], gap=3,
                                   extra="flex-wrap: wrap;"),
                               txt("36 machines: the screens shrink, the tone still finds the two", 10.5, T["faint"]), gap=10), "a hundred still reads")
    h = b_cell("Maximised", col(row(*[calm_slot(n, s_, 58, sub) for n, s_, sub in [("06", "warn", "Kwame"), ("07", "danger", "Ama")]], gap=14),
                                txt("large enough for the name beneath", 10.5, T["faint"]), gap=10), "when a chart opens")
    s2 = msection("The screen mark, in use", e, f, g, h)
    return board("Marking a machine: without squares", s1, s2)


# ------------------------------------------------------------------ HO03: the Admin's home, rethought
# SIGNATURE: A ROOM OVER THREE. The machines are the room -- each a screen with its person and its one
# line beneath it, the mark and the reason together -- and three cells of cards sit under it.
def ho03():
    pcs = [("01", "Kojo", "ok", "at the PC", None), ("02", "Efua", "free", "free", None),
           ("03", "Yaw", "ok", "at the PC", None), ("04", "Adjoa", "entered", "you entered it", "warn"),
           ("05", "Nana", "ok", "at the PC", None), ("06", "Kwame", "warn", "a version behind", "warn"),
           ("07", "Ama", "danger", "a file out of place", "danger")]
    room = row(*[col(calm_slot(n, st, 84), txt(who, 12.5, T["ink"], 600, extra="text-align: center;"),
                     txt(line, 11, tone_c(tone, T["faint"]), 500 if tone else 400, extra="text-align: center;"),
                     gap=4, extra="align-items: center; width: 150px;") for n, who, st, line, tone in pcs],
               gap=30, justify="center", extra="width: 1316px; padding-top: 6px;")
    room_col = col(room, txt("Quiet means fine. A machine in colour says why, beneath it.", 11.5, T["faint"],
                             extra="text-align: center;"), gap=18, extra="width: 1316px; align-items: center;")
    needs = col(thing_card("ping", "warn", "Kojo pinged you twice", "OPS-01 · since 09:40", "answer", "warn"),
                thing_card("shield", "danger", "A restricted file on OPS-07", "budget-2026.xlsx · 11:41", "new", "danger"),
                thing_card("clock", "danger", "Ama's report is overdue", "final deadline was yesterday"),
                gap=9, extra="width: 476px;")
    today = dept_day(w=376, lane_h=13, gap_y=6)
    people = col(person_card("AQ", "A. Quaye", "helping Finance since 10:40", "accent"),
                 person_card("SU", "Super User", "last entered your workstation Tuesday"),
                 txt("You and A. Quaye govern all seven machines together.", 11.5, T["faint"]), gap=10, extra="width: 336px;")
    return work_page(
        "Home", "hierarchy", ["Operations"], "Operations", "seven machines · three need you", "warn",
        [row(kcell("The machines", "three need looking at", "warn", room_col, w=1360, h=300, top=True), gap=0, extra="flex: none;"),
         row(kcell("Needs you", "three things", "warn", needs, w=520, h=356, top=True),
             kcell("Today", "you entered one machine", "warn", today, w=420, h=356, top=True),
             kcell("Governing with you", "one other Admin", "dim", people, w=380, h=356, top=True),
             gap=20, align="stretch", extra="flex: none;")],
        "HO03 · Rethought. Slots + One line each became ONE thing: each machine a small screen, its person and its line beneath. "
        "No squares, no dots. What needs you is cards with bare icons.",
        eyebrow("PAGE", "Admin home — rethought", "a room over three"))


# ------------------------------------------------------------------ FL06: the Flows page, rethought
def fl06():
    W_, H_ = 856, 252
    red, ok = T["danger"], "rgba(255,255,255,0.22)"
    svg = "".join([svg_curve(150, 21, 330, 21, ok), svg_curve(480, 21, 660, 21, ok), svg_curve(480, 21, 660, 73, ok),
                   svg_curve(150, 115, 660, 121, ok), svg_curve(150, 173, 330, 173, red, True), svg_curve(480, 173, 660, 173, red, True),
                   svg_curve(150, 229, 660, 229, ok)])
    nodes = [bare_node(0, 0, "folder", "OPS-02", "Raw submissions", w=150), bare_node(330, 0, "file", "Make PDF", "then by type", "warn", w=150),
             bare_node(660, 0, "monitor", "Archive", "remote", "ok", w=150), bare_node(660, 52, "monitor", "Backup", "remote", "ok", w=150),
             bare_node(0, 94, "folder", "OPS-05", "Invoices", w=150), bare_node(660, 100, "dept", "Finance share", "waiting for a yes", "accent", w=170),
             bare_node(0, 152, "folder", "OPS-03", "Payroll", w=150), bare_node(330, 152, "file", "Make PDF", "failed 11:20", w=150, bad=True),
             bare_node(660, 152, "monitor", "WS-OPS-A1", "paused", "ok", w=150, bad=True),
             bare_node(0, 208, "folder", "WS-OPS-A1", "Handbook", w=150), bare_node(660, 208, "user", "Every worker", "7 machines", "ok", w=150)]
    the_map = canvas_(W_, H_, svg, nodes)

    def flow_card(src, dst, stage, state, tone):
        return col(row(txt(src, 12.5, T["ink"], 600, mono=True), ic("arrow", 13, T["faint"]), txt(dst, 12.5, T["dim"]), gap=8),
                   row(txt(stage, 11.5, T["warn"], 500) if stage else txt("copied as they are", 11, T["faint"]), sp(),
                       txt(state, 11.5, tone_c(tone, T["faint"]), 600), gap=8, extra="width: 100%;"),
                   gap=8, extra=f"width: 408px; box-sizing: border-box; padding: 12px 14px; border-radius: 14px; background: {T['pane']};")
    cards = col(row(flow_card("OPS-02", "Archive, Backup", "made into PDF", "syncing", None),
                    flow_card("OPS-05", "Finance share", "", "waiting for a yes", "accent"), gap=16),
                row(flow_card("OPS-03", "WS-OPS-A1", "made into PDF", "paused", "danger"),
                    flow_card("WS-OPS-A1", "Every worker", "", "syncing", None), gap=16), gap=14, extra="width: 856px;")
    broken = col(txt("One branch is paused; everything else still runs.", 14, T["ink"], 600, extra="line-height: 1.35;"),
                 thing_card("flows", "danger", "OPS-03 → WS-OPS-A1", "Make PDF failed at 11:20", "paused", "danger"),
                 row(tbtn("See the fix", "accent", size="sm"), gap=0), gap=12, extra="width: 396px;")
    waiting = col(txt("One flow waits on another department.", 14, T["ink"], 600, extra="line-height: 1.35;"),
                  person_card("KB", "K. Boateng", "must agree: OPS-05 → Finance share", "accent"),
                  row(gbtn("Remind them", size="sm"), gap=0), gap=12, extra="width: 396px;")
    return work_page(
        "Flows", "flows", ["Flows"], "Flows", "four flows · one paused", "warn",
        [row(col(kcell("Broken", "one branch paused", "danger", broken, w=440, h=346, top=True),
                 kcell("Waiting for a yes", "one", "accent", waiting, w=440, h=310, top=True), gap=20, extra="flex: none;"),
             col(kcell("Where files go", "every flow, drawn", "dim", the_map, w=900, h=346, top=True),
                 kcell("Your flows", "from → to", "dim", cards, w=900, h=310, top=True), gap=20, extra="flex: none;"),
             gap=20, align="stretch", extra="flex: none;")],
        "FL06 · Rethought. The map's stages carry bare icons, no tiles; the paths are quieter; the stage is said in words "
        "on each flow card instead of a coloured tag.",
        eyebrow("PAGE", "Flows — rethought", "a wide right column"))


# ------------------------------------------------------------------ FL07: one flow as a tree, rethought
def fl07():
    W_, H_ = 820, 470
    ok, red = "rgba(255,255,255,0.22)", T["danger"]
    svg = "".join([svg_curve(190, 235, 260, 110, ok, w=2.5), svg_curve(190, 235, 260, 360, red, True, 2.5),
                   svg_curve(430, 110, 470, 110, ok, w=2.5), svg_curve(640, 110, 660, 70, ok, w=2.5), svg_curve(640, 110, 660, 150, ok, w=2.5),
                   svg_curve(430, 360, 660, 360, red, True, 2.5)])
    nodes = [bare_node(0, 213, "folder", "OPS-02", "Raw submissions · source", w=190),
             bare_node(260, 88, "file", "Make PDF", "transform", "warn", w=170), bare_node(470, 88, "folder", "Sort by type", "categorize", "warn", w=170),
             bare_node(660, 48, "monitor", "Archive", "synced 11:40", "ok", w=160), bare_node(660, 128, "monitor", "Backup", "synced 11:40", "ok", w=160),
             bare_node(260, 338, "file", "Make PDF", "failed at 11:20", w=170, bad=True),
             bare_node(660, 338, "monitor", "WS-OPS-A1", "paused, not stale", "ok", w=160, bad=True)]
    tree = col(plain_tabs(["Tree", "Sentence", "Card"], "Tree"), canvas_(W_, H_, svg, nodes),
               txt("Tree is the default. Sentence and Card show the same flow another way.", 11.5, T["faint"]), gap=16, extra="width: 856px;")
    fix = col(txt("Make PDF could not convert payroll.xlsm.", 14, T["ink"], 600, extra="line-height: 1.35;"),
              txt("Suggested, safest first", 11.5, T["faint"], 600),
              row(tbtn("Skip files it cannot convert", "accent", size="sm"), gap=0),
              row(gbtn("Remove the PDF stage", size="sm"), gbtn("Retry", size="sm"), gap=4),
              txt("Only this branch waits. It resumes by itself once fixed.", 11.5, T["faint"]), gap=11, extra="width: 396px;")
    kept = col(txt("Someone changed a copy at the destination.", 13.5, T["ink"], 600, extra="line-height: 1.35;"),
               thing_card("file", "accent", "report.xlsx", "fresh from the source"),
               thing_card("file", "warn", "report-modified.xlsx", "Nana's edit, kept beside it", "kept", "warn"),
               txt("Nothing is overwritten. Both are in Archive.", 11.5, T["faint"]), gap=10, extra="width: 396px;")
    return work_page(
        "Flows — one flow", "flows", ["Flows", "Raw submissions"], "Raw submissions", "from OPS-02 · one branch paused", "warn",
        [row(kcell("The flow", "two branches", "dim", tree, w=900, h=676, top=True),
             col(kcell("The fix, offered", "for the paused branch", "danger", fix, w=440, h=316, top=True),
                 kcell("Kept, not overwritten", "once today", "warn", kept, w=440, h=340, top=True), gap=20, extra="flex: none;"),
             gap=20, align="stretch", extra="flex: none;")],
        "FL07 · Rethought. The tree's stages stand on bare icons; the kept edit is two file cards, not a row of glyphs.",
        eyebrow("PAGE", "Flows — one flow, rethought", "a hero and a column"))


# ------------------------------------------------------------------ FL08: making a flow, rethought
def fl08():
    chain = col(
        au_sentence(f"Copy {au_slot('Raw submissions')}", f"from {au_slot('OPS-02')}", f"to {au_slot('Archive', 'ok')}", size=17),
        row(txt("then", 13, T["faint"]), au_slot("make PDF", "warn"), txt("then", 13, T["faint"]), au_slot("sort by type", "warn"),
            (f'<span style="padding: 4px 10px; border-radius: 8px; border: 1.5px dashed {T["line2"]}; font-size: 12px; '
             f'color: {T["faint"]}; font-family: {T["sans"]};">+ then…</span>'),
            txt("·", 13, T["faint"]), txt("+ another destination", 12, T["accent"], 500), gap=10),
        gap=14, extra="width: 1316px;")
    W_, H_ = 800, 250
    ok = "rgba(255,255,255,0.22)"
    svg = "".join([svg_curve(190, 125, 250, 125, ok, w=2.5), svg_curve(420, 125, 460, 125, ok, w=2.5), svg_curve(630, 125, 650, 125, ok, w=2.5)])
    nodes = [bare_node(0, 103, "folder", "OPS-02", "Raw submissions", w=190), bare_node(250, 103, "file", "Make PDF", "transform", "warn", w=170),
             bare_node(460, 103, "folder", "Sort by type", "categorize", "warn", w=170), bare_node(650, 103, "monitor", "Archive", "destination", "ok", w=150)]
    preview = col(canvas_(W_, H_, svg, nodes), txt("The tree grows as you write the sentence.", 11.5, T["faint"]), gap=10, extra="width: 856px;")
    checks = col(
        row(ic("check", 15, T["ok"]), txt("No loop: nothing flows back to OPS-02", 12.5, T["ok"]), gap=8),
        row(ic("warn", 15, T["warn"]), txt("Archive already has 12 files in that folder", 12.5, T["warn"]), gap=8),
        row(gbtn("Use another folder", size="sm"), gbtn("Replace them, it is meant", size="sm"), gap=4, extra="padding-left: 22px;"),
        row(ic("check", 15, T["ok"]), txt("Archive is yours: no one else must agree", 12.5, T["ok"]), gap=8),
        sp(),
        row(gbtn("Cancel"), sp(), tbtn("Save the flow", "accent", "check", disabled=True), gap=8, extra="width: 100%;"),
        txt("Saved only once the folder question is answered.", 11, T["faint"]), gap=10, extra="width: 396px; height: 100%;")
    return work_page(
        "Flows — new", "flows", ["Flows", "New flow"], "New flow", "write it as a sentence", "accent",
        [row(kcell("Fill the sentence", "then… adds a step", "accent", chain, w=1360, h=190, top=True), gap=0, extra="flex: none;"),
         row(kcell("What it makes", "a preview", "dim", preview, w=900, h=466, top=True),
             kcell("Checked before saving", "one question left", "warn", checks, w=440, h=466, top=True),
             gap=20, align="stretch", extra="flex: none;")],
        "FL08 · Rethought: the preview's stages on bare icons, 'then' chained without arrows, 'another destination' as words.",
        eyebrow("PAGE", "Flows — making one, rethought", "a sentence over a preview"))


# ------------------------------------------------------------------ AS03: Assistance, rethought
# The ping was a dot in rings -- the same family the user rejected. It is a BANNER now: warm, wide, the
# count said in words, the answer button on it.
def as03():
    ping = col(
        col(row(ic("ping", 20, T["warn"]), txt("Kojo is asking for you", 15, T["ink"], 600), gap=10),
            txt("Pinged twice — 09:40, again at 10:15 · OPS-01", 12, T["warn"]),
            row(tbtn("Answer Kojo", "warn", size="sm"), sp(), txt("stays lit until you answer", 11, T["faint"]), gap=8, extra="width: 100%;"),
            gap=10, extra=f"width: 100%; box-sizing: border-box; padding: 16px; border-radius: 14px; background: {T['warn_soft']};"),
        gap=0, extra="width: 356px;")
    people = col(person_card("AM", "Ama", "OPS-07 · your turn to reply", "accent", "your turn"),
                 person_card("YA", "Yaw", "OPS-03 · waiting for Yaw"),
                 person_card("EF", "Efua", "OPS-02 · closed this morning"), gap=10, extra="width: 356px;")
    listening = (f'<span style="display: inline-flex; align-items: center; gap: 8px; padding: 5px 12px 5px 10px; border-radius: 999px; '
                 f'background: linear-gradient(90deg, rgba(122,162,247,0.22), rgba(122,162,247,0.06));">'
                 f'{ic("eye", 14, T["accent"])}<span style="font-family: {T["sans"]}; font-size: 11.5px; font-weight: 600; color: {T["accent"]};">'
                 f'HR is listening</span></span>')
    channel = col(
        row(av("AM", "worker", 30), col(txt("Ama", 13.5, T["ink"], 600), txt("OPS-07 · opened 11:02", 11, T["faint"]), gap=1), sp(), listening, gap=10,
            extra="width: 100%;"),
        txt("Only you see who you added. Ama is not told; the audit trail records it.", 10.5, T["faint"], extra="padding-left: 40px;"),
        rule(),
        b_bubble("I can't open the budget file any more.", False, "Ama · 11:02"),
        b_bubble("It is restricted; it should not be on your machine. Move it to Documents.", True, "you · 11:05"),
        b_bubble("Done — it says moved. Is that all?", False, "Ama · 11:09"),
        sp(),
        (f'<div style="padding: 10px 12px; border-radius: 11px; background: {T["pane"]}; font-size: 12.5px; color: {T["faint"]}; '
         f'font-family: {T["sans"]};">Your turn — one reply, then Ama\'s</div>'),
        row(gbtn("Close the channel", size="sm"), sp(), txt("only you can close it", 11, T["faint"]), gap=8, extra="width: 100%;"),
        gap=10, extra="width: 476px; height: 100%;")
    search = col(
        tk_input("budget template", 38),
        txt("Common — everyone", 11.5, T["ok"], 600),
        thing_card("file", "ok", "budget-template-2026.xlsx", "in your Resources folder"),
        txt("Operations — your department", 11.5, T["accent"], 600, extra="padding-top: 4px;"),
        thing_card("file", "accent", "budget-q3-draft.xlsx", "on the department share"),
        txt("Only what you may see is ever shown.", 11, T["faint"], extra="padding-top: 6px;"),
        gap=8, extra="width: 356px;")
    return work_page(
        "Assistance", "assistance", ["Assistance"], "Assistance", "one person asking for you", "warn",
        [row(col(kcell("Asking for you", "a ping", "warn", ping, w=400, h=226, top=True),
                 kcell("By person", "three channels", "dim", people, w=400, h=430, top=True), gap=20, extra="flex: none;"),
             kcell("Ama", "your turn", "accent", channel, w=520, h=676, top=True),
             kcell("Find a file", "grouped by where", "dim", search, w=400, h=676, top=True),
             gap=20, align="stretch", extra="flex: none;")],
        "AS03 · Rethought. The ping is a warm banner, not a dot in rings. Search results are file cards under plain headings. "
        "The listener keeps its small spice: an eye on a soft gradient pill.",
        eyebrow("PAGE", "Assistance — rethought", "three columns"))


# ------------------------------------------------------------------ RP03: Reports, rethought
# The timeline was squares. It is ticks on a line now -- a week read left to right, the ones still waiting
# standing taller in their tone.
def rp03():
    queue = col(txt("To address", 11.5, T["faint"], 600),
                thing_card("shield", "danger", "A restricted file on OPS-07", "Resource violation · 11:41", "new", "danger", sel=True),
                thing_card("flows", "warn", "The PDF stage failed", "Flow failure · OPS-03 · 11:20", "seen", "warn"),
                thing_card("dept", "warn", "Two folders disagree", "Directory conflict · OPS-05 · Mon", "seen", "warn"),
                txt("Addressed this week", 11.5, T["faint"], 600, extra="padding-top: 8px;"),
                thing_card("eye", "ok", "Listener report, channel 14", "HR · addressed Monday", "addressed"),
                thing_card("shield", "ok", "A worker's file among Admin files", "addressed Tuesday", "addressed"),
                gap=9, extra="width: 576px;")
    reading = col(txt("budget-2026.xlsx, restricted, is on Ama's machine.", 16, T["ink"], 600, extra="line-height: 1.35;"),
                  tk_line("Where", "OPS-07 · in Workers"), tk_line("Found", "today, 11:41"), tk_line("Ama", "has been told", "ok"),
                  row(tbtn("Mark addressed", "ok", "check", size="sm"), gbtn("Seen", size="sm"), sp(),
                      txt("the Super User keeps their own copy", 11, T["faint"]), gap=6, extra="width: 100%;"),
                  gap=8, extra="width: 676px;")
    days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    ticks = {"Mon": [None, None], "Tue": [None], "Wed": [], "Thu": ["warn", "warn"], "Fri": ["danger"]}
    line = (f'<div style="position: relative; width: 376px; height: 120px;">'
            f'<div style="position: absolute; left: 0; right: 0; top: 80px; height: 2px; border-radius: 1px; background: rgba(255,255,255,0.12);"></div>'
            + "".join(f'<span style="position: absolute; left: {d_i * 80 + 16 + k * 10}px; top: {80 - (40 if t else 18)}px; width: 3px; '
                      f'height: {40 if t else 18}px; border-radius: 2px; background: {T[t] if t else "rgba(255,255,255,0.35)"};"></span>'
                      for d_i, d in enumerate(days) for k, t in enumerate(ticks[d]))
            + "".join(f'<span style="position: absolute; left: {d_i * 80 + 8}px; top: 92px; font-family: {T["sans"]}; font-size: 11px; '
                      f'color: {T["faint"]};">{d}</span>' for d_i, d in enumerate(days)) + '</div>')
    timeline = col(line, txt("Every report is a tick. The ones still waiting stand taller, in their tone.", 11, T["faint"]),
                   gap=6, extra="width: 376px;")
    kinds = col(*[row(txt(k, 12, T["dim"]), sp(), txt(n, 12.5, T["ink"], 600, mono=True), gap=8,
                      extra=f"width: 100%; padding: 7px 0; border-bottom: 1px solid {T['line']};")
                  for k, n in [("Violations", "2"), ("Flow failures", "1"), ("Conflicts", "1"), ("Listener", "1")]],
                gap=0, extra="width: 196px;")
    return work_page(
        "Reports", "reports", ["Reports"], "Reports", "three to address", "warn",
        [row(kcell("To address", "three waiting", "warn", queue, w=620, h=676, top=True),
             col(kcell("A restricted file on OPS-07", "new", "danger", reading, w=720, h=316, top=True),
                 row(kcell("This week", "a timeline", "dim", timeline, w=440, h=340, top=True),
                     kcell("By kind", "routed here", "dim", kinds, w=260, h=340, top=True), gap=20, extra="flex: none;"),
                 gap=20, extra="flex: none;"),
             gap=20, align="stretch", extra="flex: none;")],
        "RP03 · Rethought. Report cards carry bare icons, no tiles. The week is ticks on a line — the ones still waiting "
        "stand taller in their tone — instead of squares.",
        eyebrow("PAGE", "Reports — rethought", "a tall queue and three"))


BATCH1B = [("MK01-Marks.dc.html", "Marking a machine: without squares", mk01),
           ("HO03-Home.dc.html", "Admin home: rethought", ho03),
           ("FL06-Flows.dc.html", "Flows: the page, rethought", fl06),
           ("FL07-Flow.dc.html", "Flows: one flow, rethought", fl07),
           ("FL08-New.dc.html", "Flows: making one, rethought", fl08),
           ("AS03-Assistance.dc.html", "Assistance: rethought", as03),
           ("RP03-Reports.dc.html", "Reports: rethought", rp03)]
