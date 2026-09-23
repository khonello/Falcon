# ================================================================== the mood board: every component, several ways
# Two sections per board; each section = one component in 3-4 approaches, same content, true size.

CW, CH = 316, 240


def cell(name, html, note="", h=None):
    box = f'<div style="width: {CW}px; height: {h or CH}px; box-sizing: border-box; border-radius: 12px; background: {T["pane"]}; padding: 16px; overflow: hidden; position: relative; display: flex; flex-direction: column; gap: 10px;">{html}</div>'
    return col(row(txt(name, 12.5, "#fff", 600), txt(note, 11.5, T["frame_faint"]) if note else "", gap=8), box, gap=6)


def msection(title, *cells):
    return col(txt(title, 14, T["frame_dim"], 600), row(*cells, gap=16, align="flex-start"), gap=8)


def board(title, s1, s2):
    inner = col(row(f'<span style="width: 8px; height: 22px; border-radius: 3px; background: #fff;"></span>', txt(title, 20, "#fff", 700), gap=10), s1, s2,
                gap=22, extra=f"width: {W}px; height: {H}px; box-sizing: border-box; padding: 26px 40px; background: {FRAME['native']}; overflow: hidden;")
    return page(title, "", "", inner, "", "native")


G = lambda *r, m="0": group(*r, m=m)
sp = lambda h=0: f'<span style="flex: {1 if not h else "none"}; height: {h}px;"></span>'
ring_svg = lambda pct, size=64, c=None, w=5: (f'<svg width="{size}" height="{size}" viewBox="0 0 {size} {size}" aria-hidden="true"><circle cx="{size/2}" cy="{size/2}" r="{size/2 - w}" fill="none" stroke="{T["line"]}" stroke-width="{w}"/>'
                                               f'<circle cx="{size/2}" cy="{size/2}" r="{size/2 - w}" fill="none" stroke="{c or T["warn"]}" stroke-width="{w}" stroke-linecap="round" stroke-dasharray="{3.1416 * (size - 2*w)}" stroke-dashoffset="{3.1416 * (size - 2*w) * (1 - pct)}" transform="rotate(-90 {size/2} {size/2})"/></svg>')
bar = lambda pct, c=None, h=4: f'<div style="height: {h}px; border-radius: {h}px; background: {T["line"]};"><div style="height: {h}px; border-radius: {h}px; background: {c or T["accent"]}; width: {int(pct*100)}%;"></div></div>'


# ------------------------------------------------------------------ 1 entity card / card strip
def m01():
    a = cell("Tile", col(row(card("Ama", "OPS-07", "Deadline reached", "danger", selected=True), card("Kojo", "OPS-01", "Needs help", "warn", w=110), gap=10), gap=0), "current")
    b = cell("Avatar-led", row(col(row(avatar("AM", "worker", 36), col(txt("Ama", 14, weight=600), txt("OPS-07", 11.5, T["faint"], mono=True), gap=1), gap=10), sp(), row(dot(T["danger"], 8), txt("Deadline reached", 12, T["danger"], 500), gap=6),
                                    gap=8, extra=f"width: 168px; height: 92px; box-sizing: border-box; padding: 12px 14px; border-radius: 12px; background: {T['ground']};"), gap=0))
    c = cell("Stat", row(col(txt("OPS-07", 18, weight=600, mono=True), txt("Ama", 12, T["faint"]), sp(), row(txt("2", 20, T["danger"], 600), txt("overdue", 12, T["faint"]), gap=6, align="baseline"),
                             gap=2, extra=f"width: 168px; height: 92px; box-sizing: border-box; padding: 12px 14px; border-radius: 12px; background: {T['ground']};"), gap=0))
    d = cell("Row card", col(row(avatar("AM", "worker", 30), col(txt("Ama", 13.5, weight=600), txt("OPS-07", 11.5, T["faint"], mono=True), gap=1, extra="flex: 1;"), txt("Deadline", 12, T["danger"], 500), gap=10,
                                 extra=f"width: 284px; height: 56px; padding: 0 14px; box-sizing: border-box; border-radius: 12px; background: {T['ground']};"),
                             row(avatar("KO", "worker", 30), col(txt("Kojo", 13.5, weight=600), txt("OPS-01", 11.5, T["faint"], mono=True), gap=1, extra="flex: 1;"), txt("Needs help", 12, T["warn"], 500), gap=10,
                                 extra=f"width: 284px; height: 56px; padding: 0 14px; box-sizing: border-box; border-radius: 12px; background: {T['ground']};"), gap=8))
    s1 = msection("Entity card", a, b, c, d)

    cards = lambda: [card("Ama", "OPS-07", "Deadline reached", "danger", selected=True, w=150), card("Kojo", "OPS-01", "Needs help", "warn", w=150), card("Efua", "OPS-02", "Free", None, "free", w=150)]
    e = cell("Fade", f'<div style="position: relative; overflow: hidden; width: 284px;"><div style="display: flex; gap: 8px; width: max-content;">{"".join(cards())}</div><div style="position: absolute; top: 0; right: 0; bottom: 0; width: 70px; background: linear-gradient(90deg, transparent, {T["pane"]});"></div></div>', "current")
    f = cell("Peek", col(f'<div style="overflow: hidden; width: 284px;"><div style="display: flex; gap: 8px; width: max-content;">{"".join(cards())}</div></div>', row(sp(), iconbtn("back", "Left", kind="pane", size=24), iconbtn("fwd", "Right", kind="pane", size=24), gap=2), gap=8), "cut edge, no fade")
    g = cell("Paged", col(row(*cards()[:2], gap=8), row(sp(), dot(T["ink"], 6), dot(T["line2"], 6), dot(T["line2"], 6), dot(T["line2"], 6), sp(), gap=6), gap=10), "dots")
    h = cell("Deck", f'<div style="position: relative; width: 284px; height: 120px;">'
             f'<div style="position: absolute; left: 16px; top: 16px; width: 150px; height: 92px; border-radius: 12px; background: {T["ground"]}; opacity: 0.4;"></div>'
             f'<div style="position: absolute; left: 8px; top: 8px; width: 150px; height: 92px; border-radius: 12px; background: {T["ground"]}; opacity: 0.7;"></div>'
             f'<div style="position: absolute; left: 0; top: 0;">{card("Ama", "OPS-07", "Deadline reached", "danger", selected=True, w=150)}</div>'
             f'<div style="position: absolute; left: 180px; top: 34px;">{txt("7 PCs", 13, T["dim"])}</div></div>', "stacked")
    s2 = msection("Card strip", e, f, g, h)
    return board("Cards and strips", s1, s2)


# ------------------------------------------------------------------ 2 segmented / list row
def m02():
    items = [("Needs you", "4"), ("Reports", "2"), ("Activity", "")]
    a = cell("Filled", segmented(items, "Needs you", m="0"), "current")
    under = row(*[col(txt(l + (f" {c}" if c else ""), 13, T["ink"] if l == "Needs you" else T["dim"], 600 if l == "Needs you" else 500), f'<div style="height: 2px; border-radius: 1px; background: {T["accent"] if l == "Needs you" else "transparent"};"></div>', gap=8) for l, c in items], gap=20)
    b = cell("Underline", col(under, hr(), gap=0))
    badge = lambda c: ('<span style="padding: 0 6px; border-radius: 999px; background: rgba(255,255,255,0.2); font-size: 11px;">' + c + '</span>') if c else ""
    pillrow = row(*[f'<span style="display: inline-flex; align-items: center; gap: 6px; padding: 5px 11px; border-radius: 999px; background: {T["select"] if l == "Needs you" else T["ground"]}; color: {"#fff" if l == "Needs you" else T["dim"]}; font-size: 12.5px; font-weight: 600;">{l}{badge(c)}</span>' for l, c in items], gap=6)
    c = cell("Pills with badges", pillrow)
    icons = row(*[col(ic(i, 18, T["ink"] if l == "Needs you" else T["dim"]), txt(l, 11.5, T["ink"] if l == "Needs you" else T["dim"], 600 if l == "Needs you" else 500), gap=4, extra=f"align-items: center; padding: 8px 14px; border-radius: 10px; background: {T['ground'] if l == 'Needs you' else 'transparent'};") for (l, _), i in zip(items, ("bell", "reports", "clock"))], gap=4)
    d = cell("Icon tabs", icons)
    s1 = msection("Segmented control", a, b, c, d)

    rows = lambda last_sep=True: [grow(dot(T["warn"], 8), "Kojo needs help", "4 min", "warn"), grow(dot(T["danger"], 8), "Report overdue", "17:00", "danger"), grow(dot(T["danger"], 8), "Flow failed", "10:52", last=True)]
    e = cell("Inset group", G(*rows()), "current")
    f = cell("Flat", col(*[r.replace(f"border-bottom: 1px solid {T['line']};", f"border-bottom: 1px solid {T['line']};").replace("padding: 0 14px 0 16px", "padding: 0 4px 0 0") for r in rows()], gap=0))
    g = cell("Cards", col(*[f'<div style="border-radius: 12px; background: {T["ground"]};">{r.replace("border-bottom: 1px solid " + T["line"] + ";", "")}</div>' for r in rows()], gap=8))
    dense = lambda l, v, t: row(dot(tone_c(t), 6), txt(l, 12.5, extra="flex: 1;"), txt(v, 11.5, tone_c(t)), gap=10, extra=f"height: 34px; padding: 0 12px; border-bottom: 1px solid {T['line']};")
    h = cell("Dense", G(dense("Kojo needs help", "4 min", "warn"), dense("Report overdue", "17:00", "danger"), dense("Flow failed", "10:52", "danger"), dense("Restricted file", "10:41", "danger"), dense("Update pending", "OPS-06", None)), "34 px rows")
    s2 = msection("List row", e, f, g, h)
    return board("Segments and rows", s1, s2)


# ------------------------------------------------------------------ 3 row status / accordion
def m03():
    a = cell("Dot and word", G(grow(row(dot(T["accent"], 8), txt("Running", 12, T["accent"], 500), gap=8, extra="width: 76px;"), "USB inserted", "OPS-02"), grow(row(dot(T["ok"], 8), txt("Done", 12, T["ok"], 500), gap=8, extra="width: 76px;"), "Login", "OPS-04", last=True)), "current")
    b = cell("Value only", G(grow(txt("", 1), "USB inserted", "Running", "accent"), grow(txt("", 1), "Login", "Done", "ok"), grow(txt("", 1), "Logout", "Error", "danger", last=True)))
    c = cell("Trailing chip", G(grow(txt("", 1), "USB inserted", right=chip("Running", "accent", 10)), grow(txt("", 1), "Login", right=chip("Done", "ok", 10)), grow(txt("", 1), "Logout", right=chip("Error", "danger", 10, dot=True), last=True)))
    d = cell("Icon tint", G(grow(ic("play", 15, T["accent"]), "USB inserted", "OPS-02"), grow(ic("check", 15, T["ok"]), "Login", "OPS-04"), grow(ic("warn", 15, T["danger"]), "Logout", "OPS-01", last=True)))
    s1 = msection("Status on a row", a, b, c, d)

    e = cell("Chevron rows", h=290, html=G(grow(num(1, done=True), "Targets", "2 found"), grow(num(2, "warn"), "Name collision", right=ic("chevd", 14, T["faint"]), strong=True), col(txt("reconciliation-q3.docx exists on OPS-05.", 12.5), row(btn("Overwrite", "secondary", size="sm"), btn("Rename", "secondary", size="sm"), gap=6), gap=8, extra=f"padding: 0 16px 14px 50px; border-bottom: 1px solid {T['line']};"), grow(num(3, "warn"), "Deadline", "Mon or Wed", "warn", last=True)), note="current")
    step = lambda n, t, v, tone=None, done=False, open_=False, last=False: row(col(num(n, tone, done), f'<div style="width: 2px; flex: 1; background: {T["line"]}; margin: 4px 0;"></div>' if not last else "", gap=0, extra="align-items: center; align-self: stretch;"),
                                                                              col(row(txt(t, 13.5, weight=600 if open_ else 400, extra="flex: 1;"), txt(v, 12, tone_c(tone)), gap=8), (col(txt("reconciliation-q3.docx exists on OPS-05.", 12.5, T["dim"]), row(btn("Overwrite", "secondary", size="sm"), btn("Rename", "secondary", size="sm"), gap=6), gap=8, extra="padding: 6px 0 12px;") if open_ else ""), gap=2, extra="flex: 1; padding: 2px 0 14px;"), gap=12, align="flex-start")
    f = cell("Stepper", h=290, html=col(step(1, "Targets", "2 found", done=True), step(2, "Name collision", "", "warn", open_=True), step(3, "Deadline", "Mon or Wed", "warn"), step(4, "Two tasks?", "", last=True), gap=0))
    g = cell("Focus", h=290, html=col(row(num(1, done=True), txt("Targets", 12, T["faint"]), sp(), txt("2 found", 11.5, T["faint"]), gap=10),
                          col(row(num(2, "warn"), txt("Name collision", 15, weight=600), gap=10), txt("reconciliation-q3.docx exists on OPS-05.", 13, T["dim"]), row(btn("Overwrite", "primary", size="sm"), btn("Use existing", "secondary", size="sm"), btn("Rename", "secondary", size="sm"), gap=6),
                              gap=10, extra=f"padding: 14px; border-radius: 12px; background: {T['ground']};"),
                          row(num(3, "warn"), txt("Deadline", 12, T["faint"]), sp(), txt("Mon or Wed", 11.5, T["warn"]), gap=10), row(num(4), txt("Two tasks?", 12, T["faint"]), gap=10), gap=10), note="the open one is the page")
    h = cell("Cards", h=290, html=col(*[f'<div style="border-radius: 12px; background: {T["ground"]}; {"box-shadow: 0 0 0 1px " + T["warn"] + ";" if o else ""}">{grow(num(n, t, d), l, v, t, right=ic("chevd" if o else "chev", 14, T["faint"]), last=True)}</div>' for n, l, v, t, d, o in [(1, "Targets", "2 found", None, True, False), (2, "Name collision", "", "warn", False, True), (3, "Deadline", "Mon or Wed", "warn", False, False)]], gap=8))
    s2 = msection("Accordion and decisions", e, f, g, h)
    return board("Status and decisions", s1, s2)


# ------------------------------------------------------------------ 4 session control / countdown
def m04():
    a = cell("Box", col(row(sess("native"), txt("At the PC", 13.5, weight=600), sp(), txt("since 08:14", 12, T["faint"]), gap=8), row(btn("Enter", "primary", "lock"), btn("End session", "secondary"), gap=8), note_line("Entering blocks Ama until you leave."),
                        gap=12, extra=f"padding: 14px; border-radius: 12px; background: {T['ground']};"), "current")
    b = cell("Hero", col(txt("At the PC", 22, weight=600), txt("since 08:14", 12.5, T["faint"]), sp(14), row(btn("Enter", "primary", "lock"), btn("End session", "ghost"), gap=8), gap=2))
    c = cell("Inline", G(grow(sess("native"), "At the PC", "since 08:14", right=btn("Enter", "primary", size="sm"), last=True)))
    d = cell("Ring", row(f'<div style="position: relative; width: 72px; height: 72px;">{ring_svg(0.71, 72)}<div style="position: absolute; inset: 0; display: flex; align-items: center; justify-content: center;">{txt("21:18", 13, weight=600, mono=True)}</div></div>',
                         col(txt("You hold this session", 13.5, weight=600), txt("Ama sees the overlay", 12, T["faint"]), row(btn("Extend", "warn", size="sm"), btn("Leave", "secondary", size="sm"), gap=6), gap=6), gap=14), "traversing")
    s1 = msection("Session control", a, b, c, d)

    e = cell("Ring", f'<div style="position: relative; width: 96px; height: 96px;">{ring_svg(0.71, 96, T["warn"], 6)}<div style="position: absolute; inset: 0; display: flex; flex-direction: column; align-items: center; justify-content: center;">{txt("21:18", 18, weight=600, mono=True)}{txt("left", 11, T["faint"])}</div></div>')
    f = cell("Digits", col(txt("21:18", 40, weight=600, mono=True, extra="line-height: 1;"), txt("of 30:00", 12, T["faint"]), gap=4))
    g = cell("Bar", col(row(txt("21:18 left", 13, weight=600), sp(), txt("30 min", 12, T["faint"]), gap=8), bar(0.71, T["warn"], 6), gap=8))
    h = cell("In the title", col(row(txt("Ama", 24, weight=600), f'<span style="display: inline-flex; align-items: center; gap: 6px; padding: 3px 10px; border-radius: 999px; background: {T["warn_soft"]}; color: {T["warn"]}; font-family: {T["mono"]}; font-size: 13px; font-weight: 600;">{ic("clock", 13)}21:18</span>', gap=10, align="center"), txt("OPS-07, through R. Mensah", 13, T["faint"]), gap=3))
    s2 = msection("Countdown", e, f, g, h)
    return board("Sessions and time", s1, s2)


# ------------------------------------------------------------------ 5 big title / graph node
def m05():
    a = cell("Title and subtitle", col(txt("Operations", 24, weight=600), txt("7 PCs, 2 Admins", 13, T["faint"]), gap=3), "current")
    b = cell("Title and chips", col(txt("Operations", 24, weight=600), row(chip("7 PCs", "neutral", 10), chip("2 Admins", "neutral", 10), chip("4 need you", "warn", 10, dot=True), gap=6), gap=8))
    c = cell("With avatar", row(avatar("AM", "worker", 44), col(txt("Ama", 24, weight=600), txt("OPS-07", 13, T["faint"], mono=True), gap=2), gap=14))
    d = cell("Title and actions", col(txt("Operations", 24, weight=600), row(btn("Department action", "secondary", "automation", "sm"), btn("Register", "ghost", "plus", "sm"), gap=6), gap=10))
    s1 = msection("Big title", a, b, c, d)

    nodebox = lambda inner, edge=None, w=170: f'<div style="width: {w}px; box-sizing: border-box; padding: 12px 14px; border: 1px solid {edge or T["line2"]}; border-radius: 12px; background: {T["ground"]}; display: flex; flex-direction: column; gap: 4px;">{inner}</div>'
    e = cell("Card", nodebox(row(ic("monitor", 15, T["dim"]), txt("OPS-05", 13.5, weight=600), gap=8) + txt("D:\\Archive\\payroll", 11.5, T["faint"], mono=True) + txt("Synced 10:50", 12, T["ok"], 500), T["ok"]), "current")
    f = cell("Pill", col(row(dot(T["ok"], 8), txt("OPS-05", 13, weight=600), txt("Synced", 12, T["ok"]), gap=8, extra=f"padding: 8px 14px; border-radius: 999px; background: {T['ground']}; width: max-content;"),
                         row(dot(T["danger"], 8), txt("OPS-03", 13, weight=600), txt("Unreachable", 12, T["danger"]), gap=8, extra=f"padding: 8px 14px; border-radius: 999px; background: {T['ground']}; width: max-content;"), gap=8))
    g = cell("Terminal", col(f'<div style="padding: 10px 12px; border-radius: 10px; background: {T["ground"]}; font-family: {T["mono"]}; font-size: 12px; color: {T["ink"]};"><span style="color: {T["faint"]};">OPS-05</span>  D:\\Archive\\payroll</div>',
                             f'<div style="padding: 10px 12px; border-radius: 10px; background: {T["ground"]}; font-family: {T["mono"]}; font-size: 12px; color: {T["danger"]}; box-shadow: 0 0 0 1px {T["danger"]};"><span style="opacity: 0.7;">OPS-03</span>  D:\\Archive\\payroll</div>', gap=8), "path is the node")
    h = cell("Dot and label", col(row(dot(T["ok"], 12), col(txt("OPS-05", 13, weight=600), txt("Synced 10:50", 11.5, T["faint"]), gap=1), gap=10), f'<div style="width: 2px; height: 28px; background: {T["line2"]}; margin-left: 5px;"></div>', row(dot(T["danger"], 12), col(txt("OPS-03", 13, weight=600), txt("Unreachable", 11.5, T["danger"]), gap=1), gap=10), gap=6))
    s2 = msection("Graph node", e, f, g, h)
    return board("Titles and nodes", s1, s2)


# ------------------------------------------------------------------ 6 conversation / empty & error
def m06():
    m = lambda who, tone, t, text: row(avatar(who[:2].upper(), tone, 26), col(row(txt(who, 12.5, weight=600), txt(t, 11, T["faint"]), gap=6), txt(text, 12.5, extra="line-height: 1.45;"), gap=2, extra="flex: 1;"), gap=8, align="flex-start")
    a = cell("Rows", col(m("Ama", "worker", "10:05", "The sheet asks for a password."), m("You", "admin", "10:07", "It is restricted. Sending a copy."), gap=12), "current")
    bub = lambda text, mine: row(f'<div style="max-width: 200px; padding: 8px 12px; border-radius: 14px; border-bottom-{"right" if mine else "left"}-radius: 4px; background: {T["select"] if mine else T["ground"]}; color: {"#fff" if mine else T["ink"]}; font-size: 12.5px; line-height: 1.45;">{text}</div>', justify="flex-end" if mine else "flex-start")
    b = cell("Bubbles", col(bub("The sheet asks for a password.", False), bub("It is restricted. Sending a copy.", True), bub("Thanks, before 17:00.", False), gap=8))
    c = cell("Thread gutter", col(row(f'<div style="width: 28px; display: flex; flex-direction: column; align-items: center; gap: 4px;">{avatar("AM", "worker", 24)}<div style="width: 2px; flex: 1; background: {T["line"]};"></div></div>', col(txt("Ama", 12, T["faint"]), txt("The sheet asks for a password.", 12.5), gap=2, extra="padding-bottom: 12px;"), gap=8, align="flex-start"),
                                  row(f'<div style="width: 28px; display: flex; justify-content: center;">{avatar("RM", "admin", 24)}</div>', col(txt("You", 12, T["faint"]), txt("It is restricted. Sending a copy.", 12.5), gap=2), gap=8, align="flex-start"), gap=0))
    d = cell("Timeline", col(*[row(txt(t, 11, T["faint"], mono=True, extra="width: 38px;"), txt(w, 12, T["dim"], 600, extra="width: 34px;"), txt(x, 12.5, extra="flex: 1;"), gap=8, align="flex-start") for t, w, x in [("10:02", "Ama", "pinged"), ("10:05", "Ama", "The sheet asks for a password."), ("10:07", "You", "It is restricted. Sending a copy."), ("10:10", "", "A. Quaye is listening")]], gap=10))
    s1 = msection("Conversation", a, b, c, d)

    e = cell("Centred", centre(ic("tasks", 28, T["line2"]), txt("No tasks yet", 15, weight=600), btn("New task", "primary", "plus", "sm")), "current")
    f = cell("Glyph tile", col(f'<div style="width: 64px; height: 64px; border-radius: 16px; background: {T["ground"]}; display: flex; align-items: center; justify-content: center;">{ic("tasks", 26, T["dim"])}</div>', txt("No tasks yet", 15, weight=600), btn("New task", "secondary", "plus", "sm"), gap=12))
    g = cell("Inline row", G(grow(ic("plus", 14, T["dim"]), "No tasks yet", "New task", "accent", last=True)), "where content would be")
    h = cell("Toast", col(sp(), row(ic("warn", 16, T["danger"]), txt("Can\u2019t create this flow", 13, weight=600), sp(), btn("Fix", "frame", size="sm"), gap=10, extra=f"padding: 12px 14px; border-radius: 12px; background: {T['ground']}; box-shadow: 0 8px 24px rgba(0,0,0,0.4);"), gap=0, extra="flex: 1;"), "error as toast")
    s2 = msection("Empty and error", e, f, g, h)
    return board("Talk and emptiness", s1, s2)


# ------------------------------------------------------------------ 7 band / icon rail
def m07():
    a = cell("Solid band", band("Inside OPS-07 as Super User. 21:18 left.", "warn", btn("Leave", "frame", size="sm")).replace("height: 40px", "height: 40px; width: 284px").replace("border-radius: 10px 10px 0 0", "border-radius: 10px"), "current")
    b = cell("Tinted strip", row(dot(T["warn"], 8), txt("Inside OPS-07", 13, weight=600), txt("21:18 left", 12, T["warn"], mono=True), sp(), btn("Leave", "secondary", size="sm"), gap=10, extra=f"height: 40px; padding: 0 14px; border-radius: 10px; background: {T['warn_soft']};"))
    c = cell("Floating pill", row(sp(), row(ic("clock", 14, "#fff"), txt("21:18", 13, "#fff", 600, mono=True), txt("inside OPS-07", 12, "rgba(255,255,255,0.8)"), btn("Leave", "frame", size="sm"), gap=8, extra=f"padding: 6px 8px 6px 14px; border-radius: 999px; background: #B4650A; box-shadow: 0 8px 24px rgba(0,0,0,0.4);"), sp(), gap=0))
    minishell = lambda fc: (f'<div style="width: 284px; height: 150px; border-radius: 10px; background: {fc}; padding: 6px; box-sizing: border-box; display: flex; gap: 6px;">'
                            f'<div style="width: 22px; border-radius: 6px; background: rgba(255,255,255,0.08);"></div><div style="flex: 1; border-radius: 8px; background: {T["pane"]}; display: flex;"><div style="width: 70px; background: {T["side_native"]};"></div></div></div>')
    d = cell("Frame recolours", minishell("linear-gradient(155deg, #3A2A05, #7A4A08)"), "the earlier idea, for the record")
    s1 = msection("State band", a, b, c, d)

    railcell = lambda inner, w=64: f'<div style="width: {w}px; height: 280px; border-radius: 10px; background: {FRAME["native"]}; padding: 8px 0; box-sizing: border-box; display: flex; flex-direction: column; align-items: center; gap: 6px;">{inner}</div>'
    labspan = lambda l, lab: ("<span>" + l + "</span>") if lab else ""
    it = lambda i, l, on=False, w=56, lab=True: f'<div style="display: flex; flex-direction: column; align-items: center; gap: 3px; width: {w}px; padding: 7px 0 6px; border-radius: 10px; background: {T["frame_wash2"] if on else "transparent"}; color: {"#fff" if on else T["frame_dim"]}; font-size: 10.5px; font-weight: 500;">{ic(i, 20, sw=1.6)}{labspan(l, lab)}</div>'
    e = cell("Icons and labels", h=320, html=row(railcell(it("home", "Hierarchy", True) + it("tasks", "Tasks") + it("flows", "Flows") + it("automation", "Automation")), gap=0), note="current")
    f = cell("Icons only", h=320, html=row(railcell(it("home", "", True, 40, False) + it("tasks", "", False, 40, False) + it("flows", "", False, 40, False) + it("automation", "", False, 40, False), 52), col(txt("tooltip on hover", 12, T["faint"]), gap=0), gap=14))
    wide = lambda i, l, on=False: row(ic(i, 16, "#fff" if on else T["frame_dim"]), txt(l, 12.5, "#fff" if on else T["frame_dim"], 600 if on else 500), gap=10, extra=f"width: 140px; padding: 8px 12px; box-sizing: border-box; border-radius: 8px; background: {T['frame_wash2'] if on else 'transparent'};")
    g = cell("Wide rail", h=320, html=f'<div style="width: 156px; height: 280px; border-radius: 10px; background: {FRAME["native"]}; padding: 8px; box-sizing: border-box; display: flex; flex-direction: column; gap: 2px;">{wide("home", "Hierarchy", True)}{wide("tasks", "Tasks")}{wide("flows", "Flows")}{wide("automation", "Automation")}{wide("assistance", "Assistance")}</div>')
    tabs = row(*[txt(l, 12.5, "#fff" if l == "Hierarchy" else T["frame_dim"], 600 if l == "Hierarchy" else 500, extra=f"padding: 6px 10px; border-radius: 7px; background: {T['frame_wash2'] if l == 'Hierarchy' else 'transparent'};") for l in ("Hierarchy", "Tasks", "Flows", "Automation")], gap=2)
    h = cell("Top tabs", h=320, html=f'<div style="width: 284px; border-radius: 10px; background: {FRAME["native"]}; padding: 8px; box-sizing: border-box;">{tabs}</div>', note="no rail; the sheet gets 64 px back")
    s2 = msection("Icon rail", e, f, g, h)
    return board("Bands and rails", s1, s2)


# ------------------------------------------------------------------ 8 sidebar tree / top bar
def m08():
    a = cell("Accordion", col(dept_head("Client PCs", "7"), tree_row("Ama", "OPS-07", "native", selected=True), tree_row("Kojo", "OPS-01", "native"), tree_row("Efua", "OPS-02", "free"), gap=2, extra=f"background: {T['side_native']}; border-radius: 10px; padding: 4px 0 8px; margin: 0 -4px;"), "current")
    av = lambda n, h, s, on=False: row(avatar(n[:2].upper(), "worker", 26), col(txt(n, 13, "#fff" if on else None, 500), txt(h, 11, T["select_sub"] if on else T["faint"], mono=True), gap=0, extra="flex: 1;"), sess(s), gap=10, extra=f"height: 40px; padding: 0 10px; border-radius: 8px; background: {T['select'] if on else 'transparent'}; margin: 0 6px;")
    b = cell("Avatar list", col(av("Ama", "OPS-07", "native", True), av("Kojo", "OPS-01", "native"), av("Efua", "OPS-02", "free"), gap=2, extra=f"background: {T['side_native']}; border-radius: 10px; padding: 8px 0; margin: 0 -4px;"))
    guide = lambda n, h, s, depth, on=False: row(f'<span style="width: {depth * 14}px; height: 32px; border-right: 1px solid {T["line2"]}; margin-right: 10px; flex: none;"></span>' if depth else "", sess(s), txt(n, 13, "#fff" if on else None, extra="flex: 1;"), txt(h, 11, T["select_sub"] if on else T["faint"], mono=True), gap=8, extra=f"height: 32px; padding: 0 10px 0 14px; border-radius: 6px; background: {T['select'] if on else 'transparent'}; margin: 0 6px;")
    c = cell("Tree with guides", col(guide("Operations", "", "you", 0), guide("R. Mensah", "A1", "native", 1), guide("Ama", "OPS-07", "native", 2, True), guide("Kojo", "OPS-01", "native", 2), gap=0, extra=f"background: {T['side_native']}; border-radius: 10px; padding: 8px 0; margin: 0 -4px;"))
    d = cell("Miller columns", row(*[col(txt(t, 11.5, T["faint"], 600, extra="padding: 0 8px 4px;"), *[row(txt(x, 12.5, "#fff" if x == on else None), sp(), ic("chev", 12, "#fff" if x == on else T["faint"]) if col_i < 2 else "", gap=4, extra=f"height: 30px; padding: 0 8px; border-radius: 6px; background: {T['select'] if x == on else 'transparent'};") for x in xs], gap=1, extra=f"width: 88px; background: {T['side_native']}; border-radius: 8px; padding: 6px 4px;") for col_i, (t, xs, on) in enumerate([("Departments", ["Operations", "Finance", "Logistics"], "Operations"), ("Admins", ["R. Mensah", "A. Quaye"], "R. Mensah"), ("PCs", ["Ama", "Kojo", "Efua"], "Ama")])], gap=6, align="flex-start"), "drill down, left to right")
    s1 = msection("Hierarchy sidebar", a, b, c, d)

    tb = lambda inner: f'<div style="width: 284px; height: 44px; border-radius: 10px; background: {FRAME["native"]}; padding: 0 8px; box-sizing: border-box; display: flex; align-items: center; gap: 8px;">{inner}</div>'
    e = cell("Crumbs and search", tb(crumb("Operations", "box", "dept") + sep() + crumb("You", "you") + sp() + f'<span style="display: flex; align-items: center; gap: 6px; height: 28px; padding: 0 10px; border-radius: 7px; background: {T["frame_wash"]}; color: {T["frame_dim"]}; font-size: 12px;">{ic("search", 13)}Search</span>'), "current")
    f = cell("Search only", tb(sp() + f'<span style="display: flex; align-items: center; gap: 8px; width: 200px; height: 28px; padding: 0 10px; border-radius: 7px; background: {T["frame_wash"]}; color: {T["frame_dim"]}; font-size: 12px;">{ic("search", 13)}Search files</span>' + sp()), "the sheet carries the title")
    g = cell("Command palette", col(tb(sp() + f'<span style="display: flex; align-items: center; gap: 8px; width: 220px; height: 28px; padding: 0 10px; border-radius: 7px; background: {T["frame_wash"]}; color: {T["frame_dim"]}; font-size: 12px;">{ic("search", 13)}Go to, do, find<span style="flex: 1;"></span><span style="font-family: {T["mono"]}; font-size: 11px; opacity: 0.7;">Ctrl K</span></span>' + sp()),
                                    G(grow(ic("monitor", 14, T["dim"]), "Enter OPS-07", "Ctrl E", right=""), grow(ic("tasks", 14, T["dim"]), "New task", "", right=""), grow(ic("search", 14, T["dim"]), "q3 figures", "3 files", right="", last=True)), gap=8), "one box for everything")
    h = cell("Minimal", tb(iconbtn("back", "Back") + iconbtn("fwd", "Forward") + sp() + iconbtn("search", "Search") + iconbtn("bell", "Indicators")), "icons only")
    s2 = msection("Top bar", e, f, g, h)
    return board("Sidebar and top bar", s1, s2)


# ------------------------------------------------------------------ 9 indicators / inspector
def m09():
    fr = lambda inner, h=52: f'<div style="width: 284px; height: {h}px; border-radius: 10px; background: {FRAME["native"]}; padding: 0 10px; box-sizing: border-box; display: flex; align-items: center; gap: 6px;">{inner}</div>'
    a = cell("Chrome pills", fr(indicator("2 pings", "warn", "ping") + indicator("Deadline", "danger", "clock")), "current")
    b = cell("Bell with count", fr(sp() + f'<span style="position: relative; width: 32px; height: 32px; display: inline-flex; align-items: center; justify-content: center; color: #fff;">{ic("bell", 18)}<span style="position: absolute; top: 2px; right: 2px; min-width: 16px; height: 16px; padding: 0 4px; border-radius: 8px; background: {T["danger"]}; color: #fff; font-size: 10.5px; font-weight: 700; display: inline-flex; align-items: center; justify-content: center;">4</span></span>'))
    raildot = lambda t: ('<span style="position: absolute; top: 4px; right: 10px; width: 8px; height: 8px; border-radius: 4px; background: ' + tone_c(t) + '; box-shadow: 0 0 0 3px ' + tone_c(t) + '55;"></span>') if t else ""
    c = cell("Rail badges", row(f'<div style="width: 64px; height: 150px; border-radius: 10px; background: {FRAME["native"]}; padding: 8px 0; box-sizing: border-box; display: flex; flex-direction: column; align-items: center; gap: 6px;">'
                                + "".join(f'<div style="position: relative; display: flex; flex-direction: column; align-items: center; gap: 3px; width: 56px; padding: 7px 0 6px; color: {T["frame_dim"]}; font-size: 10.5px;">{ic(i, 20, sw=1.6)}<span>{l}</span>{raildot(t)}</div>' for i, l, t in [("tasks", "Tasks", "danger"), ("assistance", "Assist", "warn"), ("flows", "Flows", None)])
                                + "</div>", col(txt("the dot sits on the area it belongs to", 12, T["faint"]), gap=0), gap=14, align="flex-start"))
    d = cell("Ticker", col(fr(sp() + txt("Falcon", 12, "#fff", 700) + sp(), 36), row(dot(T["warn"], 7), txt("Kojo needs help", 12), txt("4 min", 11.5, T["faint"]), sp(), dot(T["danger"], 7), txt("Report overdue", 12), gap=8, extra=f"height: 30px; padding: 0 12px; background: {T['ground']}; border-radius: 0 0 10px 10px; margin-top: -8px;"), gap=0), "a strip under the top bar")
    s1 = msection("Indicators", a, b, c, d)

    insp_mini = lambda insp, extra="": f'<div style="width: 284px; height: 190px; border-radius: 10px; background: {T["ground"]}; position: relative; overflow: hidden; display: flex; {extra}"><div style="flex: 1;"></div>{insp}</div>'
    e = cell("Side panel", insp_mini(f'<div style="width: 110px; background: {T["pane"]}; border-left: 1px solid {T["line"]};"></div>'), "current")
    f = cell("Slide-over", insp_mini(f'<div style="position: absolute; top: 8px; right: 8px; bottom: 8px; width: 120px; border-radius: 10px; background: {T["pane"]}; box-shadow: 0 12px 32px rgba(0,0,0,0.5);"></div>'), "over the page, dismissable")
    g = cell("Popover", insp_mini(f'<div style="position: absolute; left: 20px; top: 20px; width: 90px; height: 50px; border-radius: 8px; background: {T["pane"]}; box-shadow: 0 0 0 2px {T["select"]};"></div><div style="position: absolute; left: 118px; top: 14px; width: 130px; height: 120px; border-radius: 10px; background: {T["pane"]}; box-shadow: 0 12px 32px rgba(0,0,0,0.5);"></div>'), "from the card")
    h = cell("Bottom drawer", insp_mini(f'<div style="position: absolute; left: 8px; right: 8px; bottom: 0; height: 90px; border-radius: 10px 10px 0 0; background: {T["pane"]}; box-shadow: 0 -8px 24px rgba(0,0,0,0.4);"><div style="width: 32px; height: 4px; border-radius: 2px; background: {T["line2"]}; margin: 8px auto 0;"></div></div>'))
    s2 = msection("Inspector", e, f, g, h)
    return board("Indicators and inspectors", s1, s2)


# ------------------------------------------------------------------ 10 buttons / chips
def m10():
    a = cell("Filled and outline", col(row(btn("Enter", "primary", "lock"), btn("End session", "secondary"), gap=8), row(btn("End session", "danger"), btn("Cancel", "ghost"), gap=8), gap=10), "current")
    tonal = lambda t, tone="accent", i=None: f'<button type="button" style="display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 8px; border: 0; background: {T[tone + "_soft"]}; color: {T[tone]}; font-family: {T["sans"]}; font-size: 13px; font-weight: 600;">{ic(i, 14) if i else ""}{t}</button>'
    b = cell("Tonal", col(row(tonal("Enter", "accent", "lock"), tonal("End session", "danger"), gap=8), row(tonal("Extend", "warn", "clock"), tonal("Accept", "assist"), gap=8), gap=10))
    c = cell("Ghost with icon", col(row(btn("Ping", "ghost", "ping"), btn("Assign", "ghost", "tasks"), btn("Run", "ghost", "automation"), gap=4), gap=0))
    big = lambda t, bg, i=None: f'<button type="button" style="display: inline-flex; align-items: center; justify-content: center; gap: 8px; width: 100%; height: 44px; border-radius: 12px; border: 0; background: {bg}; color: #fff; font-family: {T["sans"]}; font-size: 14px; font-weight: 600;">{ic(i, 16) if i else ""}{t}</button>'
    d = cell("Large", col(big("Enter this PC", "#3B6FE0", "lock"), big("End session", T["ground"]).replace("color: #fff", f"color: {T['ink']}"), gap=8), "one per surface")
    s1 = msection("Buttons", a, b, c, d)

    e = cell("Soft", row(chip("Overdue", "danger", 11, dot=True), chip("Syncing", "ok", 11), chip("Draft", "accent", 11), chip("Worker", "worker", 11), gap=6, extra="flex-wrap: wrap;"), "current")
    out = lambda t, tone: f'<span style="padding: 2px 8px; border-radius: 999px; border: 1px solid {tone_c(tone, T["line2"])}; color: {tone_c(tone, T["dim"])}; font-size: 11px; font-weight: 500;">{t}</span>'
    f = cell("Outline", row(out("Overdue", "danger"), out("Syncing", "ok"), out("Draft", "accent"), out("Worker", None), gap=6, extra="flex-wrap: wrap;"))
    sol = lambda t, tone: f'<span style="padding: 2px 8px; border-radius: 6px; background: {tone_c(tone, T["line2"])}; color: #fff; font-size: 11px; font-weight: 600;">{t}</span>'
    g = cell("Solid", row(sol("Overdue", "danger"), sol("Syncing", "ok"), sol("Draft", "accent"), sol("Worker", None), gap=6, extra="flex-wrap: wrap;"))
    h = cell("Text only", row(txt("Overdue", 12, T["danger"], 600), txt("Syncing", 12, T["ok"], 600), txt("Draft", 12, T["accent"], 600), txt("Worker", 12, T["dim"], 600), gap=14))
    s2 = msection("Chips", e, f, g, h)
    return board("Buttons and chips", s1, s2)


# ------------------------------------------------------------------ 11 inputs / avatars
def m11():
    lab = lambda t: f'<label style="font-size: 12px; color: {T["dim"]}; font-weight: 500;">{t}</label>'
    a = cell("Filled", col(lab("Hostname"), f'<input type="text" value="WS-OPS-08" style="height: 38px; padding: 0 12px; border: 0; border-radius: 10px; background: {T["ground"]}; font-family: {T["mono"]}; font-size: 13.5px; color: {T["ink"]}; width: 100%; box-sizing: border-box;">', gap=6), "current")
    b = cell("Outline", col(lab("Hostname"), f'<input type="text" value="WS-OPS-08" style="height: 38px; padding: 0 12px; border: 1px solid {T["line2"]}; border-radius: 10px; background: transparent; font-family: {T["mono"]}; font-size: 13.5px; color: {T["ink"]}; width: 100%; box-sizing: border-box;">', gap=6))
    c = cell("Underline", col(lab("Hostname"), f'<input type="text" value="WS-OPS-08" style="height: 34px; padding: 0 2px; border: 0; border-bottom: 1px solid {T["line2"]}; border-radius: 0; background: transparent; font-family: {T["mono"]}; font-size: 14px; color: {T["ink"]}; width: 100%; box-sizing: border-box;">', gap=4))
    d = cell("Floating label", f'<div style="position: relative; height: 46px; border-radius: 10px; background: {T["ground"]}; padding: 20px 12px 0; box-sizing: border-box;"><span style="position: absolute; top: 7px; left: 12px; font-size: 10.5px; color: {T["faint"]};">Hostname</span><input type="text" value="WS-OPS-08" style="border: 0; background: transparent; font-family: {T["mono"]}; font-size: 13.5px; color: {T["ink"]}; width: 100%; padding: 0;"></div>')
    s1 = msection("Inputs", a, b, c, d)

    e = cell("Square initials", row(avatar("SU", "su", 36), avatar("RM", "admin", 36), avatar("AM", "worker", 36), gap=10), "current")
    rnd = lambda i, tone, s=36: avatar(i, tone, s).replace("border-radius: 8px", f"border-radius: {s}px")
    f = cell("Round", row(rnd("SU", "su"), rnd("RM", "admin"), rnd("AM", "worker"), gap=10))
    ringed = lambda i, tone, c: f'<span style="padding: 2px; border-radius: 12px; box-shadow: 0 0 0 2px {c};">{avatar(i, tone, 32)}</span>'
    g = cell("Role ring", row(ringed("SU", "su", T["su"]), ringed("RM", "admin", T["admin"]), ringed("AM", "worker", T["line2"]), gap=14), "colour is the role")
    st = lambda i, tone, c: f'<span style="position: relative; display: inline-block;">{avatar(i, tone, 36)}<span style="position: absolute; right: -2px; bottom: -2px; width: 12px; height: 12px; border-radius: 6px; background: {c}; box-shadow: 0 0 0 2px {T["pane"]};"></span></span>'
    h = cell("With session dot", row(st("AM", "worker", T["worker"]), st("KO", "worker", T["warn"]), st("EF", "worker", T["pane"]).replace(f"background: {T['pane']}; box-shadow", f"background: {T['pane']}; border: 2px solid {T['line2']}; box-sizing: border-box; box-shadow"), gap=14), "session state on the person")
    s2 = msection("Avatars", e, f, g, h)
    return board("Inputs and avatars", s1, s2)


# ------------------------------------------------------------------ 12 hover & press / session vocabulary
def m12():
    a = cell("Row hover", G(grow(dot(T["warn"], 8), "Kojo needs help", "4 min", "warn"), grow(dot(T["danger"], 8), "Report overdue", "17:00", "danger").replace(f"box-sizing: border-box;", f"box-sizing: border-box; background: {T['line']};"), grow(dot(T["danger"], 8), "Flow failed", "10:52", last=True)), "middle row hovered")
    b = cell("Card hover", row(card("Ama", "OPS-07", "Deadline reached", "danger", w=130), card("Kojo", "OPS-01", "Needs help", "warn", w=130).replace("flex: none;", f"flex: none; transform: translateY(-2px); box-shadow: 0 8px 20px rgba(0,0,0,0.45), 0 0 0 1px {T['line2']};"), gap=10), "right card hovered")
    c = cell("Pressed", row(btn("Enter", "primary", "lock"), btn("Enter", "primary", "lock", extra="filter: brightness(0.85); transform: scale(0.97);"), gap=12), "rest, pressed")
    d = cell("Selected and hover", col(tree_row("Ama", "OPS-07", "native", selected=True), tree_row("Kojo", "OPS-01", "native").replace("background: transparent", f"background: {T['line']}"), tree_row("Efua", "OPS-02", "free"), gap=2, extra=f"background: {T['side_native']}; border-radius: 10px; padding: 8px 0; margin: 0 -4px;"), "selected, hovered, rest")
    s1 = msection("Hover and press", a, b, c, d)

    vocab = [("free", "Free"), ("native", "At the PC"), ("traversed", "Entered"), ("assisted", "Assisted"), ("su", "Super User")]
    e = cell("Dots", col(*[row(sess(k), txt(l, 12.5), gap=10) for k, l in vocab], gap=8), "current")
    icons = {"free": ("monitor", T["line2"]), "native": ("user", T["worker"]), "traversed": ("lock", T["warn"]), "assisted": ("assistance", T["assist"]), "su": ("shield", T["su"])}
    f = cell("Icons", col(*[row(ic(icons[k][0], 15, icons[k][1]), txt(l, 12.5), gap=10) for k, l in vocab], gap=8))
    rg = lambda c, hollow=False: f'<span style="width: 12px; height: 12px; border-radius: 6px; border: 2px solid {c}; box-sizing: border-box; background: {"transparent" if hollow else c + "55"}; display: inline-block;"></span>'
    g = cell("Rings", col(*[row(rg({"free": T["line2"], "native": T["worker"], "traversed": T["warn"], "assisted": T["assist"], "su": T["su"]}[k], k == "free"), txt(l, 12.5), gap=10) for k, l in vocab], gap=8))
    h = cell("Name colour", col(*[row(txt("Ama", 13, {"free": T["faint"], "native": T["ink"], "traversed": T["warn"], "assisted": T["assist"], "su": T["su"]}[k], 500), txt(l, 11.5, T["faint"]), gap=10) for k, l in vocab], gap=8), "no dot at all")
    s2 = msection("Session vocabulary", e, f, g, h)
    return board("Feel and vocabulary", s1, s2)


# ------------------------------------------------------------------ 13 density / live metrics
def m13():
    dens = lambda h, fs: G(*[row(dot(tone_c(t), 8 if h > 36 else 6), txt(l, fs, extra="flex: 1;"), txt(v, fs - 1, tone_c(t)), ic("chev", 13, T["faint"]), gap=10, extra=f"height: {h}px; padding: 0 12px 0 14px; {'border-bottom: 1px solid ' + T['line'] + ';' if i < 3 else ''}") for i, (l, v, t) in enumerate([("Kojo needs help", "4 min", "warn"), ("Report overdue", "17:00", "danger"), ("Flow failed", "10:52", "danger"), ("Restricted file", "10:41", "danger")])])
    a = cell("Compact 36", dens(36, 12.5), h=270)
    b = cell("Comfortable 46", dens(46, 13.5), "current", h=270)
    c = cell("Spacious 56", dens(56, 14), h=270)
    d = cell("Auto", h=270, html=col(txt("Compact for lists over 20 rows, comfortable otherwise, spacious for touch.", 12.5, T["dim"]), gap=0), note="a rule, not a setting")
    s1 = msection("Density", a, b, c, d)

    tile = lambda k, v, sub="": col(txt(k, 11.5, T["faint"]), txt(v, 20, weight=600, mono=True), txt(sub, 11, T["faint"]) if sub else "", gap=2, extra=f"padding: 10px 12px; border-radius: 10px; background: {T['ground']}; flex: 1;")
    e = cell("Tiles", f'<div style="display: grid; grid-template-columns: repeat(2, minmax(0, 1fr)); gap: 8px;">{tile("CPU", "23 %")}{tile("Memory", "6.1 GB", "of 16")}{tile("Idle", "0 s")}{tile("Window", "EXCEL", "since 10:40")}</div>')
    f = cell("Rows", G(grow(txt("", 1), "CPU", "23 %", right=""), grow(txt("", 1), "Memory", "6.1 of 16 GB", right=""), grow(txt("", 1), "Idle", "0 s", right=""), grow(txt("", 1), "Window", "EXCEL.EXE", right="", last=True)), "current")
    g = cell("Bars", col(*[col(row(txt(k, 12), sp(), txt(v, 12, T["dim"], mono=True), gap=6), bar(p, c), gap=5) for k, v, p, c in [("CPU", "23 %", 0.23, T["accent"]), ("Memory", "6.1 / 16 GB", 0.38, T["accent"]), ("Disk", "71 %", 0.71, T["warn"])]], gap=12))
    spark = lambda pts, c: f'<svg width="120" height="28" viewBox="0 0 120 28" aria-hidden="true"><polyline points="{pts}" fill="none" stroke="{c}" stroke-width="1.75" stroke-linejoin="round"/></svg>'
    h = cell("Sparklines", col(*[row(txt(k, 12, extra="width: 60px;"), spark(p, c), txt(v, 12, T["dim"], mono=True, extra="margin-left: auto;"), gap=8) for k, v, p, c in [("CPU", "23 %", "0,20 15,18 30,22 45,10 60,14 75,8 90,16 105,12 120,15", T["accent"]), ("Memory", "6.1 GB", "0,22 20,21 40,20 60,18 80,17 100,16 120,15", T["accent"]), ("Input", "now", "0,24 20,24 40,6 60,24 80,24 100,8 120,24", T["ok"])]], gap=12), "the last minute")
    s2 = msection("Live metrics", e, f, g, h)
    return board("Density and metrics", s1, s2)


# ------------------------------------------------------------------ 14 notices / logs
def m14():
    a = cell("Toast", col(sp(), row(ic("check", 16, T["ok"]), txt("Session ended", 13, weight=600), sp(), btn("Undo", "ghost", size="sm"), gap=10, extra=f"padding: 12px 14px; border-radius: 12px; background: {T['ground']}; box-shadow: 0 8px 24px rgba(0,0,0,0.4);"), gap=0, extra="flex: 1;"), "bottom, 4 s")
    b = cell("Banner", col(row(ic("check", 16, T["ok"]), txt("Session ended", 13, weight=600), sp(), iconbtn("x", "Dismiss", kind="pane", size=22), gap=10, extra=f"padding: 10px 14px; border-radius: 10px; background: {T['ok_soft']};"), gap=0), "top of the sheet")
    c = cell("Inline", G(grow(ic("check", 14, T["ok"]), "Session ended", "just now", "ok", right="", last=True)), "as the first row")
    d = cell("Status line", col(sp(), row(dot(T["ok"], 7), txt("Session ended", 11.5, T["frame_dim"]), sp(), txt("native   1.4.2", 11.5, T["frame_faint"], mono=True), gap=8, extra=f"height: 24px; padding: 0 12px; border-radius: 6px; background: {FRAME['native']};"), gap=0, extra="flex: 1;"), "quietest")
    s1 = msection("Notices", a, b, c, d)

    logs = [("10:52", "Sync failed", "OPS-03", "danger"), ("10:50", "14 files", "OPS-05", "ok"), ("10:12", "Conflict kept", "OPS-05", "warn"), ("09:30", "3 files", "both", "ok")]
    e = cell("Table", col(row(*[txt(h, 11, T["faint"], 500, extra=f"width: {w}px;") for h, w in [("Time", 48), ("Event", 110), ("Where", 60)]], gap=8, extra=f"padding: 0 8px 6px; border-bottom: 1px solid {T['line']};"),
                          *[row(txt(t, 11.5, T["faint"], mono=True, extra="width: 48px;"), txt(e_, 12.5, extra="width: 110px;"), txt(w, 12, T["dim"], extra="width: 60px;"), gap=8, extra=f"height: 32px; padding: 0 8px; border-bottom: 1px solid {T['line']};") for t, e_, w, _ in logs], gap=0))
    f = cell("List", G(*[grow(dot(tone_c(t), 8), e_, t_, right="", last=(i == 3)) for i, (t_, e_, w, t) in enumerate(logs)]), "current")
    g = cell("Timeline", col(*[row(txt(t_, 11, T["faint"], mono=True, extra="width: 40px; text-align: right;"), col(dot(tone_c(t), 10), f'<div style="width: 2px; flex: 1; background: {T["line"]}; margin: 2px 0;"></div>' if i < 3 else "", gap=0, extra="align-items: center; align-self: stretch;"), col(txt(e_, 12.5), txt(w, 11.5, T["faint"]), gap=1, extra="padding-bottom: 12px;"), gap=10, align="flex-start") for i, (t_, e_, w, t) in enumerate(logs)], gap=0))
    h = cell("Grouped by day", col(txt("Today", 11.5, T["faint"], 600), G(*[grow(dot(tone_c(t), 8), e_, t_, right="", last=(i == 2)) for i, (t_, e_, w, t) in enumerate(logs[:3])]), txt("Monday", 11.5, T["faint"], 600), G(grow(dot(T["line2"], 8), "Collision confirmed", "14:02", right="", last=True)), gap=6))
    s2 = msection("Logs", e, f, g, h)
    return board("Notices and logs", s1, s2)


# ------------------------------------------------------------------ 15 hierarchy, other shapes / the plus
def m15():
    orgnode = lambda t, s, tone=None, w=90: f'<div style="width: {w}px; padding: 8px 10px; border-radius: 8px; background: {T["ground"]}; box-shadow: 0 0 0 1px {tone_c(tone, T["line"])}; text-align: center; box-sizing: border-box;">{txt(t, 12, weight=600)}<br>{txt(s, 10.5, T["faint"])}</div>'
    a = cell("Org chart", col(row(sp(), orgnode("Operations", "2 Admins"), sp(), gap=0), f'<div style="height: 14px; width: 2px; background: {T["line2"]}; margin: 0 auto;"></div>', row(orgnode("R. Mensah", "4 PCs", "accent"), orgnode("A. Quaye", "3 PCs"), gap=10, justify="center"), f'<div style="height: 14px; width: 2px; background: {T["line2"]}; margin: 0 auto;"></div>', row(orgnode("Ama", "OPS-07", "danger", 64), orgnode("Kojo", "OPS-01", "warn", 64), orgnode("Efua", "OPS-02", None, 64), gap=6, justify="center"), gap=0))
    b = cell("Grid map", f'<div style="display: grid; grid-template-columns: repeat(4, minmax(0, 1fr)); gap: 6px;">' + "".join(f'<div style="height: 44px; border-radius: 8px; background: {T["ground"]}; box-shadow: inset 0 0 0 1px {tone_c(t, T["line"])}; display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 2px;">{sess(s)}{txt(n, 11, weight=500)}</div>' for n, s, t in [("Ama", "native", "danger"), ("Kojo", "native", "warn"), ("Efua", "free", None), ("Yaw", "native", "danger"), ("Adjoa", "traversed", "warn"), ("Nana", "native", None), ("Kwame", "free", None), ("+", "free", None)]) + "</div>", "the whole department at a glance")
    c = cell("Breadcrumb drill", col(row(txt("Operations", 12.5, T["faint"]), ic("chev", 12, T["faint"]), txt("R. Mensah", 12.5, T["faint"]), ic("chev", 12, T["faint"]), txt("Ama", 12.5, weight=600), gap=4), G(grow(sess("native"), "Ama", "OPS-07", right=""), grow(sess("native"), "Kojo", "OPS-01", right=""), grow(sess("free"), "Efua", "OPS-02", right="", last=True)), gap=10), "one level at a time")
    d = cell("Split by state", col(txt("Need you", 11.5, T["faint"], 600), G(grow(sess("native"), "Ama", "Deadline", "danger", right=""), grow(sess("native"), "Kojo", "Needs help", "warn", right="", last=True)), txt("Quiet", 11.5, T["faint"], 600), G(grow(sess("native"), "Nana", "", right=""), grow(sess("free"), "Efua", "", right="", last=True)), gap=6), "state first, names second")
    s1 = msection("Hierarchy, other shapes", a, b, c, d)

    e = cell("Menu", col(row(sp(), f'<span style="width: 28px; height: 28px; border-radius: 8px; background: {T["line"]}; display: inline-flex; align-items: center; justify-content: center; color: {T["ink"]};">{ic("x", 15)}</span>', gap=0), f'<div style="width: 190px; margin-left: auto; border-radius: 12px; background: {T["ground"]}; padding: 6px; box-shadow: 0 12px 32px rgba(0,0,0,0.5);">' + "".join(row(ic(i, 15, T["dim"]), txt(l, 13), gap=10, extra="height: 36px; padding: 0 12px;") for i, l in [("monitor", "Register a PC"), ("tasks", "New task"), ("flows", "New flow"), ("bell", "Send an alert")]) + "</div>", gap=6), "current")
    f = cell("Speed dial", col(sp(), row(sp(), col(*[row(txt(l, 12, T["dim"]), f'<span style="width: 36px; height: 36px; border-radius: 18px; background: {T["ground"]}; display: inline-flex; align-items: center; justify-content: center; color: {T["ink"]};">{ic(i, 16)}</span>', gap=10, justify="flex-end") for i, l in [("monitor", "Register"), ("tasks", "Task"), ("flows", "Flow")]], f'<span style="width: 44px; height: 44px; border-radius: 22px; background: #3B6FE0; display: inline-flex; align-items: center; justify-content: center; color: #fff; margin-left: auto;">{ic("x", 18)}</span>', gap=10, extra="align-items: flex-end;"), gap=0), gap=0, extra="flex: 1;"), "floating, bottom right")
    g = cell("Per-area button", col(row(txt("Tasks", 15, weight=700, extra="flex: 1;"), btn("New", "primary", "plus", "sm"), gap=6), row(txt("Flows", 15, weight=700, extra="flex: 1;"), btn("New", "primary", "plus", "sm"), gap=6), gap=14), "no global plus")
    h = cell("Command", G(grow(ic("search", 14, T["dim"]), "new task for Nana", "", right=txt("Enter", 11, T["faint"], mono=True), last=True)), "type it")
    s2 = msection("Creating things", e, f, g, h)
    return board("Shapes of the hierarchy, and creating", s1, s2)


MOOD = [("M01-Cards.dc.html", "Cards and strips", m01), ("M02-Rows.dc.html", "Segments and rows", m02), ("M03-Status.dc.html", "Status and decisions", m03),
        ("M04-Sessions.dc.html", "Sessions and time", m04), ("M05-Titles.dc.html", "Titles and nodes", m05), ("M06-Talk.dc.html", "Talk and emptiness", m06),
        ("M07-Rails.dc.html", "Bands and rails", m07), ("M08-Sidebar.dc.html", "Sidebar and top bar", m08), ("M09-Indicators.dc.html", "Indicators and inspectors", m09),
        ("M10-Buttons.dc.html", "Buttons and chips", m10), ("M11-Inputs.dc.html", "Inputs and avatars", m11), ("M12-Feel.dc.html", "Feel and vocabulary", m12),
        ("M13-Density.dc.html", "Density and metrics", m13), ("M14-Notices.dc.html", "Notices and logs", m14), ("M15-Shapes.dc.html", "Hierarchy shapes, creating", m15)]
