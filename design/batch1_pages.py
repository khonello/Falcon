# ================================================================== Batch 1 pages: HO02, FL03-FL05, AS02, RP02
# Composed from the user's picks off HO01, FL01-FL02, AS01, RP01 (27 Sep 2026), with their standing
# direction (memory: visual-direction): resolve conflicts here rather than asking.
#
# THE SLOT RULE, NEW AND SYSTEM-WIDE. "The only issues I have ever had with slots is the color ranging,
# not just here but everywhere." A set of marks is CALM: every slot the same quiet fill, and colour only
# on the exceptions that need someone -- a thin ring and a dot. A machine that is fine is not green; it is
# simply quiet. (`calm_slot` below. The built FleetGrid gets the same treatment when it is next touched.)
#
# Choices made where the picks left a gap, each said once:
#   * Flows "From -> to" was picked for the listing but not its look: the flows are CARDS, not rows.
#   * "Map of every flow" -- "I don't see how this will look": it is drawn for real on FL03.
#   * One flow: the TREE is the default view; Sentence and Card are the viewer's other choices (FL04).
#   * Assistance "By person": avatar-led rectangles, anchored left -- not a list.
#   * Listening gets its small spice: an eye with a soft halo, and the words "only you see this".

def calm_slot(label, state="ok", size=52, sub=""):
    """One machine as a slot. Quiet unless something needs a person: then a thin ring and a dot in the
    exception's tone. 'free' is only fainter -- being unused is not a problem."""
    ring = {"warn": T["warn"], "danger": T["danger"], "entered": T["warn"]}.get(state)
    dim = state == "free"
    shadow = f"box-shadow: inset 0 0 0 1.5px {ring};" if ring else ""
    dot_ = (f'<span style="position: absolute; top: 5px; right: 5px; width: 7px; height: 7px; border-radius: 4px; '
            f'background: {ring};"></span>') if ring else ""
    box = (f'<span style="position: relative; width: {size}px; height: {size}px; border-radius: {int(size * 0.28)}px; '
           f'background: {T["pane"]}; display: inline-flex; align-items: center; justify-content: center; '
           f'font-family: {T["mono"]}; font-size: {int(size * 0.25)}px; font-weight: 600; '
           f'color: {T["ink"] if ring else T["dim"]}; opacity: {0.5 if dim else 1}; {shadow}">{label}{dot_}</span>')
    return col(box, txt(sub, 10.5, T["faint"], extra="text-align: center;") if sub else "", gap=5,
               extra="align-items: center; flex: none;")


def person_card(initials, name, line, tone=None, right="", w=None, spice="", lead=None):
    """A person as a rectangle, avatar-led and anchored left -- never a list row."""
    width = f"width: {w}px;" if w else "width: 100%;"
    return row(lead or av(initials, "worker", 34), col(txt(name, 13, T["ink"], 600), txt(line, 11.5, tone_c(tone, T["faint"])), gap=2,
                                              extra="min-width: 0;"),
               sp(), spice, txt(right, 12, tone_c(tone, T["faint"]), 600) if right else "", gap=12,
               extra=f"{width} box-sizing: border-box; padding: 12px 14px; border-radius: 14px; background: {T['pane']};")


def svg_curve(x1, y1, x2, y2, color, dashed=False, w=2):
    mx = (x1 + x2) / 2
    dash = 'stroke-dasharray="5 5"' if dashed else ""
    return (f'<path d="M{x1},{y1} C{mx},{y1} {mx},{y2} {x2},{y2}" fill="none" stroke="{color}" stroke-width="{w}" '
            f'stroke-linecap="round" {dash}/>')


def pos_node(x, y, icon, label, sub="", tone="accent", w=150, bad=False):
    ring = f"box-shadow: inset 0 0 0 1.5px {T['danger']};" if bad else ""
    return (f'<div style="position: absolute; left: {x}px; top: {y}px; width: {w}px; box-sizing: border-box; '
            f'padding: 8px 10px; border-radius: 11px; background: {T["pane"]}; display: flex; align-items: center; gap: 9px; {ring}">'
            f'{au_icon(icon, "danger" if bad else tone, 26)}<div style="display: flex; flex-direction: column; gap: 1px; min-width: 0;">'
            f'<span style="font-family: {T["sans"]}; font-size: 12px; font-weight: 600; color: {T["ink"]}; white-space: nowrap;">{label}</span>'
            + (f'<span style="font-family: {T["sans"]}; font-size: 10.5px; color: {T["danger"] if bad else T["faint"]}; white-space: nowrap;">{sub}</span>' if sub else "")
            + '</div></div>')


def canvas_(w, h, svg, nodes):
    return (f'<div style="position: relative; width: {w}px; height: {h}px;">'
            f'<svg width="{w}" height="{h}" style="position: absolute; left: 0; top: 0;">{svg}</svg>{"".join(nodes)}</div>')


def plain_tabs(items, current):
    return row(*[txt(t, 13, T["ink"] if t == current else T["faint"], 600 if t == current else 400) for t in items], gap=20)


# ------------------------------------------------------------------ HO02: the Admin's home
# SIGNATURE: A BAND OVER THREE. The machines run the full width -- calm slots, and one line each beside
# them -- and three narrow cells sit beneath: what needs you, today, and who governs with you.
def ho02():
    pcs = [("01", "Kojo", "ok", "at the PC", None), ("02", "Efua", "free", "free", None),
           ("03", "Yaw", "ok", "at the PC", None), ("04", "Adjoa", "entered", "you entered it, 12 min", "warn"),
           ("05", "Nana", "ok", "at the PC", None), ("06", "Kwame", "warn", "a version behind since Friday", "warn"),
           ("07", "Ama", "danger", "a restricted file is on it", "danger")]
    slots = row(*[calm_slot(n, st, 56, who) for n, who, st, _, _ in pcs], gap=12)
    lines = col(*[row(txt(f"OPS-{n}", 12, T["ink"] if tone else T["dim"], 600 if tone else 400, mono=True, extra="width: 64px;"),
                      txt(who, 12, T["dim"], extra="width: 60px;"), txt(w_, 12, tone_c(tone, T["faint"]), 500 if tone else 400),
                      gap=10, extra=f"width: 100%; padding: 6px 0; border-bottom: 1px solid {T['line']};")
                  for n, who, st, w_, tone in pcs], gap=0, extra="width: 560px;")
    machines = row(col(slots, txt("Quiet means fine. A ring means someone should look.", 11.5, T["faint"]), gap=16,
                       extra="width: 600px;"), lines, gap=60, align="flex-start", extra="width: 1316px;")

    needs = col(*[row(ic(i, 15, T[t]), col(txt(a, 12.5, T["ink"], 600), txt(b, 11, T["faint"]), gap=1), gap=10,
                      extra=f"width: 100%; padding: 8px 0; border-bottom: 1px solid {T['line']};")
                  for i, t, a, b in [("ping", "warn", "Kojo pinged you twice", "OPS-01 · since 09:40"),
                                     ("shield", "danger", "A restricted file on OPS-07", "budget-2026.xlsx · 11:41"),
                                     ("clock", "danger", "Ama's report is overdue", "final deadline was yesterday"),
                                     ("flows", "warn", "A flow's PDF stage failed", "OPS-03 · the backup still runs")]],
                gap=0, extra="width: 476px;")
    today = dept_day(w=376, lane_h=13, gap_y=6)
    people = col(person_card("AQ", "A. Quaye", "helping Finance since 10:40", "accent"),
                 person_card("SU", "Super User", "last entered your workstation Tuesday"),
                 txt("You and A. Quaye govern all seven machines together.", 11.5, T["faint"]), gap=10, extra="width: 336px;")
    return work_page(
        "Home", "hierarchy", ["Operations"], "Operations", "seven machines · four need you", "warn",
        [row(kcell("The machines", "two need looking at", "warn", machines, w=1360, h=300, top=True), gap=0, extra="flex: none;"),
         row(kcell("Needs you", "four things", "warn", needs, w=520, h=356, top=True),
             kcell("Today", "you entered one machine", "warn", today, w=420, h=356, top=True),
             kcell("Governing with you", "one other Admin", "dim", people, w=380, h=356, top=True),
             gap=20, align="stretch", extra="flex: none;")],
        "HO02 · Four cells (HO01) with Slots + One line each (HO01). Slots are CALM: one quiet fill, colour only as a "
        "ring on what needs someone. People are avatar-led cards, not rows.",
        eyebrow("PAGE", "Admin home — their department", "a band over three"))


# ------------------------------------------------------------------ FL03: the Flows page
# SIGNATURE: A WIDE RIGHT COLUMN, Tasks' mirror. The map and the flows as cards take the wide side; what
# is broken and what waits for a yes are the narrow column on the left.
def fl03():
    W_, H_ = 856, 252
    red, ok = T["danger"], T["line2"]
    svg = "".join([svg_curve(150, 31, 330, 31, ok), svg_curve(480, 31, 660, 23, ok), svg_curve(480, 31, 660, 75, ok),
                   svg_curve(150, 115, 660, 121, ok), svg_curve(150, 173, 330, 173, red, True), svg_curve(480, 173, 660, 173, red, True),
                   svg_curve(150, 229, 660, 229, ok)])
    nodes = [pos_node(0, 8, "folder", "OPS-02", "Raw submissions", w=150), pos_node(330, 8, "file", "Make PDF", "then by type", "warn", w=150),
             pos_node(660, 0, "monitor", "Archive", "remote", "ok", w=150), pos_node(660, 52, "monitor", "Backup", "remote", "ok", w=150),
             pos_node(0, 92, "folder", "OPS-05", "Invoices", w=150), pos_node(660, 98, "dept", "Finance share", "waiting for a yes", "accent", w=170),
             pos_node(0, 150, "folder", "OPS-03", "Payroll", w=150), pos_node(330, 150, "file", "Make PDF", "failed 11:20", w=150, bad=True),
             pos_node(660, 150, "monitor", "WS-OPS-A1", "paused", "ok", w=150, bad=True),
             pos_node(0, 206, "folder", "WS-OPS-A1", "Handbook", w=150), pos_node(660, 206, "user", "Every worker", "7 machines", "ok", w=150)]
    the_map = canvas_(W_, H_, svg, nodes)

    def flow_card(src, dst, stage, state, tone):
        return col(row(txt(src, 12.5, T["ink"], 600, mono=True), ic("arrow", 13, T["faint"]), txt(dst, 12.5, T["dim"]), gap=8),
                   row(tk_tag(stage, "warn") if stage else txt("as they are", 11, T["faint"]), sp(), txt(state, 11.5, tone_c(tone, T["faint"]), 600), gap=8,
                       extra="width: 100%;"),
                   gap=9, extra=f"width: 408px; box-sizing: border-box; padding: 12px 14px; border-radius: 14px; background: {T['pane']};")
    cards = col(row(flow_card("OPS-02", "Archive, Backup", "Make PDF", "syncing", None),
                    flow_card("OPS-05", "Finance share", "", "waiting", "accent"), gap=16),
                row(flow_card("OPS-03", "WS-OPS-A1", "Make PDF", "paused", "danger"),
                    flow_card("WS-OPS-A1", "Every worker", "", "syncing", None), gap=16),
                gap=14, extra="width: 856px;")
    broken = col(txt("One branch is paused; everything else still runs.", 14, T["ink"], 600, extra="line-height: 1.35;"),
                 person_card("", "OPS-03 → WS-OPS-A1", "Make PDF failed at 11:20", "danger", lead=au_icon("flows", "danger", 34)),
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
        "FL03 · Four cells (FL01). The map of every flow, drawn for real: sources left, stages between, destinations right; "
        "the paused branch dashed. From → to kept as cards, not rows.",
        eyebrow("PAGE", "Flows — an Admin's", "a wide right column"))


# ------------------------------------------------------------------ FL04: one flow, as a tree -- and when it needs you
# SIGNATURE: A HERO AND A COLUMN. The tree is the page; the column beside it is what the flow needs from you.
def fl04():
    W_, H_ = 820, 470
    ok, red = T["line2"], T["danger"]
    svg = "".join([svg_curve(190, 235, 260, 110, ok, w=2.5), svg_curve(190, 235, 260, 360, red, True, 2.5),
                   svg_curve(430, 110, 470, 110, ok, w=2.5), svg_curve(640, 110, 660, 70, ok, w=2.5), svg_curve(640, 110, 660, 150, ok, w=2.5),
                   svg_curve(430, 360, 660, 360, red, True, 2.5)])
    nodes = [pos_node(0, 212, "folder", "OPS-02", "Raw submissions · source", w=190),
             pos_node(260, 87, "file", "Make PDF", "transform", "warn", w=170), pos_node(470, 87, "folder", "Sort by type", "categorize", "warn", w=170),
             pos_node(660, 47, "monitor", "Archive", "synced 11:40", "ok", w=160), pos_node(660, 127, "monitor", "Backup", "synced 11:40", "ok", w=160),
             pos_node(260, 337, "file", "Make PDF", "failed at 11:20", w=170, bad=True),
             pos_node(660, 337, "monitor", "WS-OPS-A1", "paused, not stale", "ok", w=160, bad=True)]
    tree = col(plain_tabs(["Tree", "Sentence", "Card"], "Tree"), canvas_(W_, H_, svg, nodes),
               row(txt("Tree is the default. Sentence and Card show the same flow another way.", 11.5, T["faint"]), gap=0),
               gap=16, extra="width: 856px;")
    fix = col(txt("Make PDF could not convert payroll.xlsm.", 14, T["ink"], 600, extra="line-height: 1.35;"),
              txt("Suggested, safest first", 11.5, T["faint"], 600),
              row(tbtn("Skip files it cannot convert", "accent", size="sm"), gap=0),
              row(gbtn("Remove the PDF stage", size="sm"), gbtn("Retry", size="sm"), gap=4),
              txt("Only this branch waits. It resumes by itself once fixed.", 11.5, T["faint"]), gap=11, extra="width: 396px;")
    kept = col(txt("Someone changed a copy at the destination.", 13.5, T["ink"], 600, extra="line-height: 1.35;"),
               row(ic("file", 16, T["accent"]), txt("report.xlsx", 12.5, T["ink"], 600, mono=True), sp(), txt("fresh from the source", 11, T["faint"]), gap=8),
               row(ic("file", 16, T["warn"]), txt("report-modified.xlsx", 12.5, T["ink"], 600, mono=True), sp(), txt("Nana's edit, kept", 11, T["warn"]), gap=8),
               txt("Nothing is overwritten. Both are in Archive.", 11.5, T["faint"]), gap=10, extra="width: 396px;")
    return work_page(
        "Flows — one flow", "flows", ["Flows", "Raw submissions"], "Raw submissions", "from OPS-02 · one branch paused", "warn",
        [row(kcell("The flow", "two branches", "dim", tree, w=900, h=676, top=True),
             col(kcell("The fix, offered", "for the paused branch", "danger", fix, w=440, h=316, top=True),
                 kcell("Kept, not overwritten", "once today", "warn", kept, w=440, h=340, top=True), gap=20, extra="flex: none;"),
             gap=20, align="stretch", extra="flex: none;")],
        "FL04 · A tree (FL01), the default view, with Sentence and Card as the viewer's other choices. When a flow needs you "
        "(FL02): the broken branch is dashed in the tree, the fix is offered beside it, and a kept edit is shown, not hidden.",
        eyebrow("PAGE", "Flows — one flow", "a hero and a column"))


# ------------------------------------------------------------------ FL05: making a flow
# SIGNATURE: A SENTENCE OVER A PREVIEW. The sentence is written across the top; the tree it makes grows
# underneath as it is written, and the checks sit beside it, said plainly, before anything is saved.
def fl05():
    chain = col(
        au_sentence(f"Copy {au_slot('Raw submissions')}", f"from {au_slot('OPS-02')}", f"to {au_slot('Archive', 'ok')}", size=17),
        row(txt("then", 13, T["faint"]), au_slot("make PDF", "warn"), ic("arrow", 13, T["faint"]), txt("then", 13, T["faint"]),
            au_slot("sort by type", "warn"), ic("arrow", 13, T["faint"]),
            (f'<span style="padding: 4px 10px; border-radius: 8px; border: 1.5px dashed {T["line2"]}; font-size: 12px; '
             f'color: {T["faint"]}; font-family: {T["sans"]};">+ then…</span>'),
            txt("·", 13, T["faint"]), au_chip("+ another destination"), gap=9),
        gap=14, extra="width: 1316px;")
    W_, H_ = 800, 250
    svg = "".join([svg_curve(190, 125, 250, 125, T["line2"], w=2.5), svg_curve(420, 125, 460, 125, T["line2"], w=2.5),
                   svg_curve(630, 125, 650, 125, T["line2"], w=2.5)])
    nodes = [pos_node(0, 102, "folder", "OPS-02", "Raw submissions", w=190), pos_node(250, 102, "file", "Make PDF", "transform", "warn", w=170),
             pos_node(460, 102, "folder", "Sort by type", "categorize", "warn", w=170), pos_node(650, 102, "monitor", "Archive", "destination", "ok", w=150)]
    preview = col(canvas_(W_, H_, svg, nodes), txt("The tree grows as you write the sentence.", 11.5, T["faint"]), gap=10, extra="width: 856px;")
    checks = col(
        row(ic("check", 15, T["ok"]), txt("No loop: nothing flows back to OPS-02", 12.5, T["ok"]), gap=8),
        row(ic("warn", 15, T["warn"]), txt("Archive already has 12 files in that folder", 12.5, T["warn"]), gap=8),
        row(gbtn("Use another folder", size="sm"), gbtn("Replace them, it is meant", size="sm"), gap=4, extra="padding-left: 22px;"),
        row(ic("check", 15, T["ok"]), txt("Archive is yours: no one else must agree", 12.5, T["ok"]), gap=8),
        sp(),
        row(gbtn("Cancel"), sp(), tbtn("Save the flow", "accent", "check", disabled=True), gap=8, extra="width: 100%;"),
        txt("Saved only once the folder question is answered.", 11, T["faint"]),
        gap=10, extra="width: 396px; height: 100%;")
    return work_page(
        "Flows — new", "flows", ["Flows", "New flow"], "New flow", "write it as a sentence", "accent",
        [row(kcell("Fill the sentence", "then… adds a step", "accent", chain, w=1360, h=190, top=True), gap=0, extra="flex: none;"),
         row(kcell("What it makes", "a preview", "dim", preview, w=900, h=466, top=True),
             kcell("Checked before saving", "one question left", "warn", checks, w=440, h=466, top=True),
             gap=20, align="stretch", extra="flex: none;")],
        "FL05 · Fill the sentence (FL02) with its chained 'then…' steps, the tree drawn underneath as it is written, and "
        "Checked before saving (FL02): the loop, the collision and the consent, in words.",
        eyebrow("PAGE", "Flows — making one", "a sentence over a preview"))


# ------------------------------------------------------------------ AS02: Assistance
# SIGNATURE: THREE COLUMNS. Who is waiting on you, the conversation you are in, and finding a file --
# the three things Assistance is, side by side.
def as02():
    ping = col(
        row(f'<span style="width: 14px; height: 14px; border-radius: 7px; background: {T["warn"]}; box-shadow: 0 0 0 7px {T["warn_soft"]}, 0 0 0 14px rgba(210,164,104,0.07);"></span>',
            col(txt("Kojo pinged you twice", 14, T["ink"], 600), txt("OPS-01 · 09:40, again 10:15", 11.5, T["faint"]), gap=2), gap=16,
            extra=f"width: 100%; padding: 14px; border-radius: 14px; background: {T['warn_soft']}; box-sizing: border-box;"),
        row(tbtn("Answer Kojo", "warn", size="sm"), sp(), txt("stays lit until answered", 11, T["faint"]), gap=8, extra="width: 100%;"),
        gap=10, extra="width: 356px;")
    people = col(person_card("AM", "Ama", "OPS-07 · your turn to reply", "accent", "your turn"),
                 person_card("YA", "Yaw", "OPS-03 · waiting for Yaw"),
                 person_card("EF", "Efua", "OPS-02 · closed this morning"), gap=10, extra="width: 356px;")

    def bubble(text, mine, meta):
        return b_bubble(text, mine, meta)
    halo = (f'<span style="display: inline-flex; align-items: center; gap: 7px; padding: 4px 10px 4px 5px; border-radius: 999px; '
            f'background: {T["accent_soft"]};"><span style="width: 22px; height: 22px; border-radius: 11px; display: inline-flex; '
            f'align-items: center; justify-content: center; background: {T["pane"]}; box-shadow: 0 0 0 3px rgba(122,162,247,0.25);">'
            f'{ic("eye", 12, T["accent"])}</span><span style="font-family: {T["sans"]}; font-size: 11.5px; font-weight: 600; '
            f'color: {T["accent"]};">HR is listening</span></span>')
    channel = col(
        row(av("AM", "worker", 30), col(txt("Ama", 13.5, T["ink"], 600), txt("OPS-07 · opened 11:02", 11, T["faint"]), gap=1), sp(), halo, gap=10,
            extra="width: 100%;"),
        txt("Only you see who you added. Ama is not told; the audit trail records it.", 10.5, T["faint"], extra="padding-left: 40px;"),
        rule(),
        bubble("I can't open the budget file any more.", False, "Ama · 11:02"),
        bubble("It is restricted; it should not be on your machine. Move it to Documents.", True, "you · 11:05"),
        bubble("Done — it says moved. Is that all?", False, "Ama · 11:09"),
        sp(),
        (f'<div style="padding: 10px 12px; border-radius: 11px; background: {T["pane"]}; font-size: 12.5px; color: {T["faint"]}; '
         f'font-family: {T["sans"]};">Your turn — one reply, then Ama\'s</div>'),
        row(gbtn("Close the channel", size="sm"), sp(), txt("only you can close it", 11, T["faint"]), gap=8, extra="width: 100%;"),
        gap=10, extra="width: 476px; height: 100%;")
    search = col(
        tk_input("budget template", 38),
        txt("COMMON", 10.5, T["ok"], 700), tk_line("budget-template-2026.xlsx", "everyone", lead=ic("file", 14, T["accent"])),
        txt("OPERATIONS", 10.5, T["accent"], 700), tk_line("budget-q3-draft.xlsx", "your department", lead=ic("file", 14, T["accent"])),
        txt("RESTRICTED — YOURS", 10.5, T["danger"], 700), tk_line("budget-2026.xlsx", "your machine only", lead=ic("file", 14, T["danger"])),
        txt("Only what you may see is ever shown.", 11, T["faint"], extra="padding-top: 6px;"),
        gap=7, extra="width: 356px;")
    return work_page(
        "Assistance", "assistance", ["Assistance"], "Assistance", "one ping waiting", "warn",
        [row(col(kcell("Waiting on you", "a ping", "warn", ping, w=400, h=226, top=True),
                 kcell("By person", "three channels", "dim", people, w=400, h=430, top=True), gap=20, extra="flex: none;"),
             kcell("Ama", "your turn", "accent", channel, w=520, h=676, top=True),
             kcell("Find a file", "grouped by where", "dim", search, w=400, h=676, top=True),
             gap=20, align="stretch", extra="flex: none;")],
        "AS02 · The ping, unmissable; By person as avatar-led cards; the listener with its small spice (AS01). One search box, "
        "grouped by where (AS01). The channel keeps its one-reply-each turns.",
        eyebrow("PAGE", "Assistance — an Admin's", "three columns"))


# ------------------------------------------------------------------ RP02: Reports
# SIGNATURE: A TALL QUEUE AND THREE. The queue down the left is the work; the chosen report is read at the
# top right, with the week's timeline and the kinds beneath it.
def rp02():
    def q_card(icon, tone, title, sub, state, sel=False):
        fill = T["select"] if sel else T["pane"]
        return row(au_icon(icon, tone, 30), col(txt(title, 12.5, "#fff" if sel else T["ink"], 600), txt(sub, 11, T["select_sub"] if sel else T["faint"]), gap=2),
                   sp(), txt(state, 11.5, tone_c({"new": "danger", "seen": "warn"}.get(state), T["faint"]), 600), gap=11,
                   extra=f"width: 100%; box-sizing: border-box; padding: 11px 13px; border-radius: 13px; background: {fill};")
    queue = col(txt("To address", 11.5, T["faint"], 600),
                q_card("shield", "danger", "A restricted file on OPS-07", "Resource violation · 11:41", "new", True),
                q_card("flows", "warn", "The PDF stage failed", "Flow failure · OPS-03 · 11:20", "seen"),
                q_card("dept", "warn", "Two folders disagree", "Directory conflict · OPS-05 · Mon", "seen"),
                txt("Addressed this week", 11.5, T["faint"], 600, extra="padding-top: 8px;"),
                q_card("eye", "ok", "Listener report, channel 14", "HR · addressed Monday", "addressed"),
                q_card("shield", "ok", "A worker's file among Admin files", "addressed Tuesday", "addressed"),
                gap=9, extra="width: 576px;")
    reading = col(txt("budget-2026.xlsx, restricted, is on Ama's machine.", 16, T["ink"], 600, extra="line-height: 1.35;"),
                  tk_line("Where", "OPS-07 · in Workers"), tk_line("Found", "today, 11:41"), tk_line("Ama", "has been told", "ok"),
                  row(tbtn("Mark addressed", "ok", "check", size="sm"), gbtn("Seen", size="sm"), sp(),
                      txt("the Super User keeps their own copy", 11, T["faint"]), gap=6, extra="width: 100%;"),
                  gap=8, extra="width: 676px;")
    days = ["Mon", "Tue", "Wed", "Thu", "Fri"]
    marks = {"Mon": [None, None], "Tue": [None], "Wed": [], "Thu": [T["warn"], T["warn"]], "Fri": [T["danger"]]}
    sq = lambda c_: (f'<span style="width: 16px; height: 16px; border-radius: 5px; background: {T["pane"]}; '
                     + (f'box-shadow: inset 0 0 0 1.5px {c_};' if c_ else "") + '"></span>')
    timeline = col(row(*[col(col(*[sq(c_) for c_ in marks[d]],
                                 gap=5, extra="height: 110px; justify-content: flex-end; align-items: center;"),
                             txt(d, 11, T["faint"]), gap=8, extra="align-items: center; width: 52px;") for d in days], gap=10),
                   txt("Quiet squares are addressed; a ring of colour only on what still waits.", 11, T["faint"]),
                   gap=10, extra="width: 376px;")
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
        "RP02 · Four cells (RP01): A queue to address as cards, A reading then mark (RP01) for the chosen one, A timeline "
        "of the week — calm marks, colour only on what still waits — and the kinds routed here.",
        eyebrow("PAGE", "Reports — an Admin's", "a tall queue and three"))


BATCH1_PAGES = [("HO02-Home.dc.html", "Admin home: composed from the picks", ho02),
                ("FL03-Flows.dc.html", "Flows: the page, from the picks", fl03),
                ("FL04-Flow.dc.html", "Flows: one flow, as a tree", fl04),
                ("FL05-New.dc.html", "Flows: making one", fl05),
                ("AS02-Assistance.dc.html", "Assistance: from the picks", as02),
                ("RP02-Reports.dc.html", "Reports: from the picks", rp02)]
