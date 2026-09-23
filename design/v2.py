# ================================================================== v2 bodies: one focus, one line per row, no sentences
# Inserted into gen.py before the write section; these definitions replace the earlier screens.

TONE = {None: None, "warn": None, "danger": None, "ok": None, "accent": None, "assist": None}


def tone_c(tone, fallback=None):
    return {"warn": T["warn"], "danger": T["danger"], "ok": T["ok"], "accent": T["accent"], "assist": T["assist"]}.get(tone, fallback or T["faint"])


def big_title(title, sub="", right=""):
    """The body's one large title. Everything under it is quiet."""
    return row(col(txt(title, 24, weight=600, extra="letter-spacing: -0.3px; line-height: 1.2;"), txt(sub, 13, T["faint"]) if sub else "", gap=3, extra="flex: 1; min-width: 0;"),
               right, gap=12, align="flex-end", extra="padding: 24px 24px 16px; flex: none;")


def segmented(items, active, m="0 24px 16px"):
    """A segmented control: the body shows one segment at a time."""
    segs = []
    for label, count in items:
        on = label == active
        bg = T["line"] if on else "transparent"
        c = f' <span style="opacity: 0.6; font-weight: 500;">{count}</span>' if count else ""
        segs.append(f'<a href="#{label.lower()}" style="flex: 1; text-align: center; padding: 6px 0; border-radius: 7px; background: {bg}; color: {T["ink"] if on else T["dim"]}; '
                    f'font-family: {T["sans"]}; font-size: 12.5px; font-weight: 600; text-decoration: none; white-space: nowrap;">{label}{c}</a>')
    return row(*segs, gap=2, extra=f"padding: 3px; border-radius: 10px; background: {T['ground']}; margin: {m}; flex: none;")


def group(*rows, m="0 24px 16px"):
    """An inset grouped list."""
    return f'<div style="margin: {m}; border-radius: 12px; background: {T["ground"]}; overflow: hidden; flex: none;">{"".join(rows)}</div>'


def grow(lead, title, value="", tone=None, right=None, last=False, sub="", strong=False):
    """One row, one line: lead, title, a value, a chevron."""
    v = txt(value, 12.5, tone_c(tone)) if value else ""
    r = right if right is not None else ic("chev", 14, T["faint"])
    sep_ = "" if last else f"border-bottom: 1px solid {T['line']};"
    h = 56 if sub else 46
    body = col(txt(title, 13.5, weight=600 if strong else 400), txt(sub, 12, T["faint"]) if sub else "", gap=2, extra="flex: 1; min-width: 0;")
    return row(lead, body, v, r, gap=12, extra=f"height: {h}px; padding: 0 14px 0 16px; box-sizing: border-box; {sep_}")


def num(n, tone=None, done=False):
    bg = T["ok_soft"] if done else (T["warn_soft"] if tone == "warn" else T["line"])
    fg = T["ok"] if done else (T["warn"] if tone == "warn" else T["dim"])
    return f'<span style="width: 22px; height: 22px; border-radius: 11px; display: inline-flex; align-items: center; justify-content: center; font-size: 11.5px; font-weight: 600; flex: none; background: {bg}; color: {fg};">{ic("check", 12) if done else n}</span>'


def strip(cards, m="0 0 16px"):
    """One row of landscape cards that scrolls sideways; the cut edge says there is more."""
    return (f'<div style="position: relative; overflow: hidden; margin: {m}; flex: none;">'
            f'<div style="display: flex; gap: 10px; padding: 2px 24px; width: max-content;">{"".join(cards)}</div>'
            f'<div style="position: absolute; top: 0; right: 0; bottom: 0; width: 80px; background: linear-gradient(90deg, transparent, {T["pane"]});"></div></div>')


def card(name, host, status, tone=None, session="native", selected=False, w=168):
    ring = f"box-shadow: 0 0 0 2px {T['select']};" if selected else ""
    return col(row(sess(session), txt(name, 14, weight=600, extra="flex: 1; white-space: nowrap;"), gap=7),
               txt(host, 11.5, T["faint"], mono=True),
               '<span style="flex: 1;"></span>',
               txt(status, 12, tone_c(tone, T["dim"]), 500 if tone else 400, extra="white-space: nowrap;"),
               gap=3, extra=f"width: {w}px; height: 92px; box-sizing: border-box; padding: 12px 14px; border-radius: 12px; background: {T['ground']}; {ring} flex: none;")


def add_card(label, w=112):
    return (f'<a href="#add" style="display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; width: {w}px; height: 92px; box-sizing: border-box; '
            f'border: 1px dashed {T["line2"]}; border-radius: 12px; color: {T["dim"]}; font-size: 12px; text-decoration: none; flex: none;">{ic("plus", 16)}{label}</a>')


def insp_title(title, sub="", right=""):
    return row(col(txt(title, 15, weight=600), txt(sub, 12, T["faint"]) if sub else "", gap=2, extra="flex: 1;"), right, gap=8, extra=f"padding: 16px 16px 12px; flex: none;")


def note_line(text):
    return txt(text, 12, T["faint"], extra="line-height: 1.45;")


# ------------------------------------------------------------------ the PC inspector, quiet
def inspector_pc(name="Ama", host="OPS-07"):
    head = row(avatar("AM", "worker", 36), col(txt(name, 16, weight=600), txt(host, 12, T["faint"], mono=True), gap=2), gap=12, extra="padding: 16px 16px 8px; flex: none;")
    session_box = col(
        row(sess("native"), txt("At the PC", 13.5, weight=600), '<span style="flex: 1;"></span>', txt("since 08:14", 12, T["faint"]), gap=8),
        row(btn("Enter", "primary", "lock"), btn("End session", "secondary"), gap=8),
        note_line("Entering blocks Ama until you leave. 30 min, extendable."),
        gap=12, extra=f"margin: 8px 16px 16px; padding: 14px; border-radius: 12px; background: {T['ground']};")
    on_pc = group(grow(dot(T["warn"], 8), "Quarterly report", "Due 17:00", "warn"), grow(dot(T["ok"], 8), "Payroll to Archive", "Syncing"), grow(dot(T["danger"], 8), "Restricted file", "Open", "danger", last=True), m="0 16px 4px")
    name_rows = group(grow(ic("eye", 14, T["faint"]), "Display name", "Ama"), grow(ic("user", 14, T["faint"]), "She sees you as", "R. Mensah", last=True), m="0 16px 4px")
    details = group(grow(txt("", 1), "Account", "4021", right=""), grow(txt("", 1), "PC", "17", right=""), grow(txt("", 1), "Version", "1.4.2", right="", last=True), m="0 16px 4px")
    body = col(session_box,
               acc("On this PC", on_pc, open_=True, count="3"),
               acc("Names", name_rows, open_=False, summary="Ama, only you"),
               acc("Details", details, open_=False, summary="4021, PC 17"),
               gap=0, extra="overflow: hidden;")
    actions = row(btn("Ping", "secondary", "ping", "sm"), btn("Assign task", "secondary", "tasks", "sm"), btn("Run action", "secondary", "automation", "sm"), gap=6)
    return col(head, body, row(actions, extra=f"padding: 10px 16px; border-top: 1px solid {T['line']}; margin-top: auto; flex: none;"), gap=0, extra="flex: 1; min-height: 0;")


# ================================================================== screens, v2
def screen_admin_home():
    crumbs = [crumb("Operations", "box", "dept"), sep(), crumb("You", "you")]
    inds = [indicator("2 pings", "warn", "ping"), indicator("Deadline", "danger", "clock"), indicator("Flow failed", "danger", "flows"), indicator("Task done", "ok", "check")]
    top = topbar(crumbs, "Search files", inds)
    rail = icon_rail("home", "admin")

    cards = strip([
        card("Ama", "OPS-07", "Deadline reached", "danger", selected=True),
        card("Kojo", "OPS-01", "Needs help", "warn"),
        card("Efua", "OPS-02", "Free", None, "free"),
        card("Yaw", "OPS-03", "Flow failing", "danger"),
        card("Adjoa", "OPS-04", "You are inside", "warn", "traversed"),
        card("Nana", "OPS-05", "Working"),
        card("Kwame", "OPS-06", "Free", None, "free"),
        add_card("Register"),
    ])
    seg = segmented([("Needs you", "4"), ("Reports", "2"), ("Activity", "")], "Needs you")
    needs = group(
        grow(dot(T["warn"], 8), "Kojo needs help", "4 min", "warn"),
        grow(dot(T["danger"], 8), "Quarterly report overdue", "17:00", "danger"),
        grow(dot(T["danger"], 8), "Payroll flow failed", "10:52"),
        grow(dot(T["danger"], 8), "Restricted file on OPS-07", "10:41", last=True),
    )
    pg = col(big_title("Operations", "7 PCs, 2 Admins", btn("Department action", "secondary", "automation", "sm")), cards, seg, needs, gap=0, extra="flex: 1; min-height: 0; overflow: hidden;")
    sh = sheet(sidebar_admin("OPS-07"), pg, inspector_pc())
    status = statusbar("Connected, TLS pinned", "native   1.4.2")
    return page("Admin, at home", top, rail, sh, status, "native")


def screen_su_home():
    crumbs = [crumb("Everything", "you", "shield")]
    inds = [indicator("Ping", "warn", "ping"), indicator("Rollout stalled", "danger", "warn"), indicator("Assistance report", "assist", "reports")]
    top = topbar(crumbs, "Search every file", inds)
    rail = icon_rail("home", "su")

    def dept(name, meta, pct, tone, selected=False):
        ring = f"box-shadow: 0 0 0 2px {T['select']};" if selected else ""
        bar = f'<div style="height: 4px; border-radius: 2px; background: {T["line"]};"><div style="height: 4px; border-radius: 2px; background: {tone_c(tone)}; width: {pct}%;"></div></div>'
        return col(txt(name, 14, weight=600), txt(meta, 12, T["faint"]), '<span style="flex: 1;"></span>', row(bar, gap=0, extra="flex-direction: column;"), txt(f"{pct} % on 1.4.2", 11.5, T["faint"]),
                   gap=4, extra=f"width: 200px; height: 92px; box-sizing: border-box; padding: 12px 14px; border-radius: 12px; background: {T['ground']}; {ring} flex: none;")
    cards = strip([dept("Operations", "2 Admins, 7 PCs", 86, "ok", True), dept("Finance", "1 Admin, 4 PCs", 50, "warn"), dept("Logistics", "No Admin, 3 PCs", 0, "danger"), add_card("New")])
    seg = segmented([("Activity", ""), ("Rollout", "12 of 14"), ("Deviations", "0")], "Activity")
    activity = group(
        grow(avatar("SU", "su", 24), "You entered OPS-04", "21 min"),
        grow(avatar("RM", "admin", 24), "R. Mensah entered OPS-04", "now", "warn"),
        grow(avatar("AQ", "admin", 24), "A. Quaye helped Finance", "29 min", "assist", last=True),
    )
    pg = col(big_title("Everything", "3 departments, 14 PCs", btn("New department", "secondary", "plus", "sm")), cards, seg, activity, gap=0, extra="flex: 1; min-height: 0; overflow: hidden;")

    def route(cat, to):
        return grow(ic("reports", 14, T["faint"]), cat, right=row(*(chip(d, "accent", 10) for d in to), iconbtn("plus", "Add", kind="pane", size=22), gap=4))
    routing = group(route("Listener reports", ["Operations"]), route("Violations", ["Operations", "Finance"]), route("Flow failures", []), route("Assistance", []), grow(ic("reports", 14, T["faint"]), "Deviations", right=row(iconbtn("plus", "Add", kind="pane", size=22)), last=True), m="0 16px 8px")
    addressed = group(grow(avatar("RM", "admin", 22), "Violation, OPS-07", "Addressed 10:55", "ok"), grow(avatar("AQ", "admin", 22), "Listener report", "Seen 09:40", last=True), m="0 16px 8px")
    insp = col(insp_title("Routing", "Reports always reach you"), routing, acc("Who addressed what", addressed, open_=False, summary="2 today"), gap=0, extra="flex: 1; min-height: 0;")
    sh = sheet(sidebar_su(), pg, insp)
    status = statusbar("Connected, TLS pinned", "native   1.4.2")
    return page("Super User, at home", top, rail, sh, status, "native")


def screen_traversing():
    crumbs = [crumb("Operations", "box", "dept"), sep(), crumb("R. Mensah", "box", "user"), sep(), crumb("Ama", "you", "monitor")]
    top = topbar(crumbs, "Search every file", [indicator("Ping", "warn", "ping")])
    rail = icon_rail("home", "su")
    seg = segmented([("Files", ""), ("Screen", ""), ("Task", "1")], "Files")
    files = group(
        grow(ic("folder", 15, T["dim"]), "Documents/Reports", "Task target", "accent"),
        grow(ic("folder", 15, T["dim"]), "resources", "Workers"),
        grow(ic("lock", 15, T["warn"]), "Personal", "Restricted", "warn"),
        grow(ic("folder", 15, T["dim"]), "Projects/Q3", "Common"),
        grow(ic("folder", 15, T["dim"]), "Downloads", "18 files"),
        grow(ic("lock", 15, T["warn"]), "HR-Notes", "Restricted", "warn", last=True),
    )
    pg = col(big_title("Ama", "OPS-07, through R. Mensah", chip("You are inside", "warn", 11, dot=True)), seg, files, note_line("Restricted folders open for you, not for R. Mensah.").replace("<span", '<span style="padding: 0 24px;"', 1) if False else row(note_line("Restricted folders open for you, not for R. Mensah."), extra="padding: 0 24px;"), gap=0, extra="flex: 1; min-height: 0; overflow: hidden;")
    bnd = band("Inside OPS-07 as Super User. 21:18 left.", "warn", btn("Extend", "frame", size="sm"), btn("Leave", "frame", size="sm"))

    head = row(avatar("AM", "worker", 36), col(txt("Ama", 16, weight=600), txt("OPS-07", 12, T["faint"], mono=True), gap=2), gap=12, extra="padding: 16px 16px 8px; flex: none;")
    hold = col(row(sess("su"), txt("You hold this session", 13.5, weight=600), '<span style="flex: 1;"></span>', txt("21:18", 13, T["warn"], 600, mono=True), gap=8),
               row(btn("Extend 30 min", "warn", "clock"), btn("Leave", "secondary"), gap=8),
               note_line("Nobody can evict you. Ama sees the overlay."),
               gap=12, extra=f"margin: 8px 16px 16px; padding: 14px; border-radius: 12px; background: {T['warn_soft']};")
    path = group(grow(ic("dept", 14, T["faint"]), "Operations", "10:20"), grow(ic("user", 14, T["faint"]), "R. Mensah", "blocked"), grow(ic("monitor", 14, T["faint"]), "OPS-07", "10:22", last=True), m="0 16px 4px")
    names = group(grow(txt("", 1), "R. Mensah calls her", "Ama", right=""), grow(txt("", 1), "You call him", "Mensah (Ops)", right="", last=True), m="0 16px 4px")
    insp = col(head, hold, acc("How you got here", path, open_=True), acc("Names", names, open_=False, summary="private to each side"), gap=0, extra="flex: 1; min-height: 0;")
    sh = sheet(sidebar_su(inside=True, selected="OPS-07"), pg, insp, state="traversing", band_html=bnd)
    status = statusbar("Connected, TLS pinned", "traversing OPS-07   21:18 left", "warn")
    return page("Super User, inside a PC", top, rail, sh, status, "traversing")


def screen_occupied():
    crumbs = [crumb("Operations", "box", "dept"), sep(), crumb("You", "you")]
    top = topbar(crumbs, "Search files", [indicator("2 pings", "warn", "ping"), indicator("Deadline", "danger", "clock")])
    rail = icon_rail("home", "admin")
    bnd = band("Super User in charge. 21:18 left.", "danger", btn("Claim native session", "frame", size="sm"))
    centre = col(ic("lock", 32, T["danger"]), txt("Read only", 20, weight=600), txt("Until Super User leaves.", 13, T["faint"]),
                 gap=10, extra="flex: 1; align-items: center; justify-content: center; padding: 40px;")
    pg = col(big_title("Operations", "7 PCs, 2 Admins"), centre, gap=0, extra="flex: 1; min-height: 0;")
    held = col(row(sess("su"), txt("Super User is inside", 13.5, weight=600), '<span style="flex: 1;"></span>', txt("21:18", 13, T["danger"], 600, mono=True), gap=8),
               row(btn("Claim native session", "secondary", "lock"), gap=8),
               note_line("Works once the session is free."),
               gap=12, extra=f"margin: 8px 16px 16px; padding: 14px; border-radius: 12px; background: {T['danger_soft']};")
    waiting = group(grow(dot(T["warn"], 8), "Kojo needs help", "4 min", "warn"), grow(dot(T["danger"], 8), "Quarterly report overdue", "17:00", "danger", last=True), m="0 16px 4px")
    insp = col(insp_title("Your session", "Held from above"), held, acc("Waiting for you", waiting, open_=True, count="2"), gap=0, extra="flex: 1; min-height: 0;")
    sh = sheet(sidebar_admin("OPS-07", "occupied"), pg, insp, state="occupied", band_html=bnd)
    status = statusbar("Connected, TLS pinned", "held by Super User   21:18 left", "danger")
    return page("Admin, occupied from above", top, rail, sh, status, "occupied")


def screen_assisted():
    crumbs = [crumb("Finance", "box", "dept"), sep(), crumb("K. Boateng", "you", "assistance")]
    top = topbar(crumbs, "Search files", [indicator("2 pings", "warn", "ping")])
    rail = icon_rail("assistance", "admin")
    head = row(txt("Helping", 15, weight=700, extra="flex: 1;"), gap=6, extra="height: 44px; padding: 0 10px 0 16px; box-sizing: border-box; flex: none;")
    who = col(row(sess("assisted"), txt("K. Boateng", 13.5, weight=600), '<span style="flex: 1;"></span>', txt("11:03", 12, T["faint"]), gap=8),
              row(btn("End help", "secondary", "x", "sm"), gap=6),
              gap=10, extra=f"margin: 4px 12px 8px; padding: 12px; border-radius: 12px; background: {T['pane']};")
    reach = col(dept_head("You can reach", ""),
                row(ic("check", 14, T["assist"]), txt("Screen, read only", 12.5), gap=8, extra="padding: 5px 16px;"),
                row(ic("check", 14, T["assist"]), txt("Workers and common files", 12.5), gap=8, extra="padding: 5px 16px;"),
                row(ic("x", 14, T["faint"]), txt("Control and actions", 12.5, T["faint"]), gap=8, extra="padding: 5px 16px;"),
                row(ic("x", 14, T["faint"]), txt("Restricted files", 12.5, T["faint"]), gap=8, extra="padding: 5px 16px;"), gap=2)
    side = col(head, who, reach, gap=2, extra="flex: 1;")
    screen = f'<div style="flex: 1; margin: 0 24px 24px; border-radius: 12px; background: linear-gradient(135deg, #2b3542, #1b2430); display: flex; align-items: center; justify-content: center; color: {T["frame_dim"]}; font-size: 13px;">FIN-02, live</div>'
    pg = col(big_title("K. Boateng", "Finance, read only", chip("Assisted", "assist", 11, dot=True)), screen, gap=0, extra="flex: 1; min-height: 0;")
    bnd = band("Helping K. Boateng by consent. Files and screen only.", "assist", btn("End help", "frame", size="sm"))
    m = lambda who_, tone, t, text: row(avatar(who_[:2].upper(), tone, 26), col(row(txt(who_, 12.5, weight=600), txt(t, 11, T["faint"]), gap=6), txt(text, 12.5, extra="line-height: 1.45;"), gap=2, extra="flex: 1;"), gap=8, align="flex-start", extra="padding: 8px 16px;")
    convo = col(m("K. Boateng", "admin", "11:02", "Payroll export hangs at 40 % since the update."), m("You", "admin", "11:05", "There is a lock file from Monday in the export folder. Delete it and retry."), gap=0, extra="flex: 1;")
    composer = row(f'<input type="text" placeholder="Message" aria-label="Message" style="flex: 1; height: 34px; padding: 0 12px; border: 1px solid {T["line2"]}; border-radius: 8px; font-family: {T["sans"]}; font-size: 13px;">', btn("Send", "primary", size="sm"), gap=8, extra=f"padding: 12px 16px; border-top: 1px solid {T['line']};")
    insp = col(insp_title("Channel", "Opened by the request"), convo, composer, gap=0, extra="flex: 1; min-height: 0;")
    sh = sheet(side, pg, insp, state="assisted", band_html=bnd)
    status = statusbar("Connected, TLS pinned", "assisting FIN-02", "ok")
    return page("Assisted access", top, rail, sh, status, "assisted")


def screen_tasks():
    crumbs = [crumb("Operations", "box", "dept"), sep(), crumb("You", "you")]
    top = topbar(crumbs, "Search files", [indicator("2 pings", "warn", "ping"), indicator("Deadline", "danger", "clock")])
    rail = icon_rail("tasks", "admin")
    head = row(txt("Tasks", 15, weight=700, extra="flex: 1;"), btn("New", "primary", "plus", "sm"), gap=6, extra="height: 44px; padding: 0 10px 0 16px; box-sizing: border-box; flex: none;")

    def trow(name, who, state="", tone="neutral", selected=False):
        bg = T["select"] if selected else "transparent"
        return row(col(txt(name, 13, "#fff" if selected else None, 500 if selected else 400), txt(who, 11.5, T["select_sub"] if selected else T["faint"]), gap=1, extra="flex: 1; min-width: 0;"), chip(state, tone, 10) if state else "", gap=8,
                   extra=f"padding: 7px 10px 7px 14px; margin: 0 6px; border-radius: 6px; background: {bg};")
    side = col(head,
        dept_head("To review", "1"), trow("Q3 supplier reconciliation", "Nana", selected=True),
        dept_head("In progress", "3"), trow("Quarterly report", "Ama", "Overdue", "danger"), trow("Onboarding pack", "Kojo"), trow("Invoice batch", "Nana", "Fri"),
        dept_head("To verify", "1"), trow("Fleet inventory", "Yaw", "Done?", "ok"),
        dept_head("Closed", "12", False),
        gap=2, extra="flex: 1;")

    quote = (f'<div style="margin: 0 24px 16px; padding: 12px 16px; border-radius: 12px; background: {T["ground"]}; font-size: 13px; line-height: 1.5; color: {T["dim"]};">'
             f'Reconcile the Q3 supplier invoices against <b style="color: {T["ink"]}; font-weight: 500;">suppliers-q3.xlsx</b> and produce <b style="color: {T["ink"]}; font-weight: 500;">reconciliation-q3.docx</b> by <b style="color: {T["warn"]}; font-weight: 500;">Monday or Wednesday</b>. Also archive last quarter\u2019s folder.</div>')
    seg = segmented([("Review", "3"), ("Targets", "2"), ("Deadline", ""), ("Assignee", "")], "Review")
    open_body = col(txt("reconciliation-q3.docx already exists on OPS-05.", 13),
                    row(btn("Overwrite", "secondary", size="sm"), btn("Use existing", "secondary", size="sm"), btn("Rename", "secondary", size="sm"), gap=6),
                    gap=10, extra=f"padding: 0 16px 16px 50px; border-bottom: 1px solid {T['line']};")
    decisions = group(
        grow(num(1, done=True), "Targets", "2 found"),
        grow(num(2, "warn"), "Name collision", right=ic("chevd", 14, T["faint"]), strong=True),
        open_body,
        grow(num(3, "warn"), "Deadline", "Monday or Wednesday", "warn"),
        grow(num(4), "Two tasks?", "Archive folder", last=True),
    )
    foot = row('<span style="flex: 1;"></span>', btn("Discard", "ghost"), btn("Confirm and assign", "primary", "check", extra="opacity: 0.5;"), gap=8, extra=f"padding: 12px 24px; border-top: 1px solid {T['line']}; flex: none;")
    pg = col(big_title("Q3 supplier reconciliation", "Proposed for Nana, OPS-05", chip("Draft", "accent", 11)), quote, seg, decisions, '<span style="flex: 1;"></span>', foot, gap=0, extra="flex: 1; min-height: 0;")

    exp = group(grow(dot(T["ok"], 8), "q3-report.docx", "Modified", "ok"), grow(dot(T["ok"], 8), "q3-figures.xlsx", "Modified", "ok"), grow(dot(T["warn"], 8), "summary.pdf", "Not created", "warn", last=True), m="0 16px 8px")
    verify = col(txt("Only you can close this", 13.5, weight=600), row(btn("Complete", "primary", "check"), btn("Incomplete", "secondary"), gap=8), row(btn("Open targets", "ghost", "folder", "sm"), gap=6),
                 gap=10, extra=f"margin: 4px 16px 16px; padding: 14px; border-radius: 12px; background: {T['ground']};")
    dl = group(grow(txt("", 1), "Final", "17:00, reached", "danger", right=""), grow(txt("", 1), "Soft", "15:00, nudged", right=""), grow(txt("", 1), "Started", "09:02", right="", last=True), m="0 16px 8px")
    insp = col(insp_title("Quarterly report", "Ama, OPS-07", chip("Overdue", "danger", 10, dot=True)), acc("Expectations", exp, open_=True, count="3"), verify, acc("Deadlines", dl, open_=False, summary="final 17:00"), gap=0, extra="flex: 1; min-height: 0;")
    sh = sheet(side, pg, insp)
    status = statusbar("Connected, TLS pinned", "native   1.4.2")
    return page("Tasks", top, rail, sh, status, "native")


def screen_flows():
    crumbs = [crumb("Operations", "box", "dept"), sep(), crumb("You", "you")]
    top = topbar(crumbs, "Search files", [indicator("Flow failed", "danger", "flows")])
    rail = icon_rail("flows", "admin")
    head = row(txt("Flows", 15, weight=700, extra="flex: 1;"), btn("New", "primary", "plus", "sm"), gap=6, extra="height: 44px; padding: 0 10px 0 16px; box-sizing: border-box; flex: none;")

    def frow(name, sub, state, tone, selected=False):
        bg = T["select"] if selected else "transparent"
        return row(col(txt(name, 13, "#fff" if selected else None, 500 if selected else 400), txt(sub, 11.5, T["select_sub"] if selected else T["faint"]), gap=1, extra="flex: 1; min-width: 0;"), chip(state, tone, 10, dot=(tone == "danger")), gap=8,
                   extra=f"padding: 7px 10px 7px 14px; margin: 0 6px; border-radius: 6px; background: {bg};")
    side = col(head, dept_head("Yours", "4"),
        frow("Payroll to Archive", "2 destinations", "Failing", "danger", True), frow("Worker resources", "7 PCs", "Syncing", "ok"),
        frow("Common resources", "Everyone", "Syncing", "ok"), frow("Photos to shared", "OPS-02", "Paused", "warn"),
        dept_head("Awaiting consent", "1"), frow("Finance handover", "A. Quaye", "Consent", "accent"),
        gap=2, extra="flex: 1;")

    def node(title, sub, icon, tone="neutral", w=190, status=""):
        edge_c = {"neutral": T["line2"], "danger": T["danger"], "ok": T["ok"], "accent": T["accent"]}[tone]
        return (f'<div style="position: absolute; width: {w}px; box-sizing: border-box; padding: 12px 14px; border: 1px solid {edge_c}; border-radius: 12px; background: {T["ground"]}; display: flex; flex-direction: column; gap: 4px;">'
                + row(ic(icon, 15, T["dim"]), txt(title, 13.5, weight=600, extra="white-space: nowrap;"), gap=8) + txt(sub, 11.5, T["faint"], mono=True)
                + (txt(status, 12, tone_c(tone), 500, extra="margin-top: 4px;") if status else "") + "</div>")

    def at(x, y, html):
        return html.replace("position: absolute;", f"position: absolute; left: {x}px; top: {y}px;", 1)
    gw, gh = 700, 330
    edges = f'''<svg width="{gw}" height="{gh}" viewBox="0 0 {gw} {gh}" style="position: absolute; left: 0; top: 0;" aria-hidden="true">
<defs><marker id="ah" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8z" fill="{T['line2']}"/></marker>
<marker id="ahd" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8z" fill="{T['danger']}"/></marker></defs>
<path d="M214 165 C 240 165, 240 165, 262 165" stroke="{T['line2']}" stroke-width="1.75" fill="none" marker-end="url(#ah)"/>
<path d="M452 165 C 480 165, 480 80, 502 80" stroke="{T['line2']}" stroke-width="1.75" fill="none" marker-end="url(#ah)"/>
<path d="M452 165 C 480 165, 480 250, 502 250" stroke="{T['danger']}" stroke-width="1.75" fill="none" stroke-dasharray="5 4" marker-end="url(#ahd)"/>
</svg>'''
    nodes = [at(24, 128, node("Source", "C:\\Payroll\\out", "monitor", "accent")),
             at(262, 128, node("Branch", "Categorize by type", "branch")),
             at(502, 40, node("OPS-05", "D:\\Archive\\payroll", "monitor", "ok", status="Synced 10:50")),
             at(502, 210, node("OPS-03", "D:\\Archive\\payroll", "monitor", "danger", status="Unreachable")),
             f'<div style="position: absolute; left: 24px; top: 16px; display: flex; gap: 6px;">{chip("No cycles", "ok", 10)}{chip("1 collision resolved", "neutral", 10)}</div>']
    graph = f'<div style="position: relative; width: {gw}px; height: {gh}px; margin: 0 24px 16px; border-radius: 12px; background: {T["ground"]}; overflow: hidden; flex: none;">{edges}{"".join(nodes)}</div>'
    seg = segmented([("Graph", ""), ("Log", "5"), ("Stages", "2")], "Graph")
    failing = group(grow(dot(T["danger"], 8), "OPS-03 unreachable", "since 10:52", "danger", right=btn("Fix", "secondary", size="sm"), last=True))
    pg = col(big_title("Payroll to Archive", "You to OPS-05 and OPS-03", row(btn("Pause", "secondary", "pause", "sm"), btn("Sync now", "secondary", "play", "sm"), gap=6)), seg, graph, failing, gap=0, extra="flex: 1; min-height: 0; overflow: hidden;")

    hist = group(grow(dot(T["danger"], 8), "Sync failed, OPS-03", "10:52", right=""), grow(dot(T["ok"], 8), "14 files to OPS-05", "10:50", right=""), grow(dot(T["warn"], 8), "Conflict kept as -modified", "10:12", right=""), grow(dot(T["ok"], 8), "3 files to both", "09:30", right=""), grow(dot(T["line2"], 8), "Collision confirmed", "Mon", right="", last=True), m="0 16px 8px")
    consent = group(grow(avatar("NA", "worker", 22), "OPS-05", "Yours", "ok", right=""), grow(avatar("YA", "worker", 22), "OPS-03", "Yours", "ok", right="", last=True), m="0 16px 8px")
    insp = col(insp_title("This flow"), acc("History", hist, open_=True, count="5"), acc("Consent", consent, open_=False, summary="none needed"), gap=0, extra="flex: 1; min-height: 0;")
    sh = sheet(side, pg, insp)
    status = statusbar("Connected, TLS pinned", "native   1.4.2")
    return page("Flows", top, rail, sh, status, "native")


def screen_automation():
    crumbs = [crumb("Operations", "box", "dept"), sep(), crumb("You", "you")]
    top = topbar(crumbs, "Search files", [indicator("2 pings", "warn", "ping")])
    rail = icon_rail("automation", "admin")
    modes = row(f'<a href="#dash" style="flex: 1; text-align: center; padding: 5px 0; border-radius: 6px; background: {T["pane"]}; color: {T["ink"]}; font-size: 12.5px; font-weight: 600; text-decoration: none;">Dashboard</a>',
                f'<a href="#edit" style="flex: 1; text-align: center; padding: 5px 0; border-radius: 6px; color: {T["dim"]}; font-size: 12.5px; font-weight: 500; text-decoration: none;">Editing</a>',
                gap=2, extra=f"padding: 3px; border-radius: 8px; background: {T['line']}; margin: 8px 12px 4px;")
    head = row(txt("Automation", 15, weight=700, extra="flex: 1;"), gap=6, extra="height: 44px; padding: 0 10px 0 16px; box-sizing: border-box; flex: none;")

    def erow(name, sub="", selected=False):
        bg = T["select"] if selected else "transparent"
        return row(ic("automation", 14, "#fff" if selected else T["dim"]), col(txt(name, 13, "#fff" if selected else None, 500 if selected else 400), txt(sub, 11.5, T["select_sub"] if selected else T["faint"]) if sub else "", gap=1, extra="flex: 1; min-width: 0;"), gap=8,
                   extra=f"padding: 7px 10px 7px 14px; margin: 0 6px; border-radius: 6px; background: {bg};")
    side = col(head, modes, dept_head("Running", "2"), erow("USB inserted", "OPS-02", True), erow("Idle 20 min", "OPS-06"),
               dept_head("Armed", "5"), erow("Login"), erow("File change"), erow("Every day 17:30"), erow("CPU over 90 %"), erow("Logout"),
               gap=2, extra="flex: 1;")

    seg = segmented([("All", "6"), ("Running", "2"), ("Done", "2"), ("Timeout", "1"), ("Error", "1")], "All")
    st = lambda tone, word: row(dot(tone_c(tone, T["accent"]), 8), txt(word, 12, tone_c(tone, T["accent"]), 500, extra="width: 56px;"), gap=8)
    out = col(f'<pre style="margin: 0; padding: 10px 12px; border-radius: 8px; background: {T["pane"]}; color: {T["ink"]}; font-family: {T["mono"]}; font-size: 11.5px; line-height: 1.5; overflow: hidden;">Remove-Item : Access to the path &#39;C:\\Temp\\lock&#39; is denied.\nexit code 1</pre>',
              row(btn("Run again", "secondary", "play", "sm"), btn("Open event", "ghost", size="sm"), gap=6),
              gap=10, extra=f"padding: 0 16px 16px 92px; border-bottom: 1px solid {T['line']};")
    runs = group(
        grow(st("accent", "Running"), "USB inserted", "OPS-02, 12 s", right=btn("Stop", "secondary", "stop", "sm")),
        grow(st("accent", "Running"), "Idle 20 min", "OPS-06, 3 min", right=btn("Stop", "secondary", "stop", "sm")),
        grow(st("ok", "Done"), "USB inserted", "OPS-02, 10:58"),
        grow(st("ok", "Done"), "Login", "OPS-04, 10:20"),
        grow(st("warn", "Timeout"), "CPU over 90 %", "OPS-03, 60 s"),
        grow(st("danger", "Error"), "Logout", "OPS-01, Mon", right=ic("chevd", 14, T["faint"]), strong=True),
        out.replace(f"border-bottom: 1px solid {T['line']};", ""),
    )
    pg = col(big_title("Dashboard", "Live, this department"), seg, runs, gap=0, extra="flex: 1; min-height: 0; overflow: hidden;")

    acts = group(grow(ic("camera", 14, T["dim"]), "Screenshot", "30 s", right=iconbtn("x", "Detach", kind="pane", size=22)), grow(ic("file", 14, T["dim"]), "Log event", "10 s", right=iconbtn("x", "Detach", kind="pane", size=22)), grow(ic("automation", 14, T["dim"]), "clear temp", "60 s", right=iconbtn("x", "Detach", kind="pane", size=22), last=True), m="0 16px 8px")
    script = col(row(txt("clear temp", 13.5, weight=600), chip("Validated", "ok", 10), gap=8),
                 f'<pre style="margin: 0; padding: 10px 12px; border-radius: 8px; background: {T["ground"]}; color: {T["ink"]}; font-family: {T["mono"]}; font-size: 11.5px; line-height: 1.5; overflow: hidden;">Get-ChildItem C:\\Temp -Recurse |\n  Remove-Item -Force -ErrorAction Stop</pre>',
                 gap=8, extra="padding: 0 16px 16px;")
    insp = col(insp_title("USB inserted", "Native event, 7 PCs"), acc("Actions", col(acts, row(btn("Attach", "secondary", "plus", "sm"), extra="padding: 0 16px 8px;"), gap=0), open_=True, count="3"), acc("Custom script", script, open_=False, summary="PowerShell, validated"), gap=0, extra="flex: 1; min-height: 0;")
    sh = sheet(side, pg, insp)
    status = statusbar("Connected, TLS pinned", "native   1.4.2")
    return page("Automation", top, rail, sh, status, "native")


def screen_assistance():
    crumbs = [crumb("Operations", "box", "dept"), sep(), crumb("You", "you")]
    top = topbar(crumbs, "Search files", [indicator("2 pings", "warn", "ping"), indicator("Help offered", "assist", "assistance")])
    rail = icon_rail("assistance", "admin")
    head = row(txt("Assistance", 15, weight=700, extra="flex: 1;"), gap=6, extra="height: 44px; padding: 0 10px 0 16px; box-sizing: border-box; flex: none;")

    def crow(name, sub, right="", selected=False, tone="worker"):
        bg = T["select"] if selected else "transparent"
        return row(avatar(name[:2].upper(), tone, 24), col(txt(name, 13, "#fff" if selected else None, 500 if selected else 400), txt(sub, 11.5, T["select_sub"] if selected else T["faint"]), gap=1, extra="flex: 1; min-width: 0;"), right, gap=8,
                   extra=f"padding: 6px 10px 6px 14px; margin: 0 6px; border-radius: 6px; background: {bg};")
    offer = col(row(sess("assisted"), txt("K. Boateng offers help", 12.5, weight=500), gap=6), row(btn("Accept", "secondary", size="sm", extra=f"border-color: {T['assist']}; color: {T['assist']};"), btn("Decline", "ghost", size="sm"), gap=6),
                gap=8, extra=f"margin: 2px 12px; padding: 10px 12px; border-radius: 10px; background: {T['assist_soft']};")
    side = col(head,
        dept_head("Pings", "2"), crow("Kojo", "4 min", chip("2", "warn", 10)), crow("Nana", "12 min", chip("1", "warn", 10)),
        dept_head("Channels", "2"), crow("Ama", "Your turn", "", True), crow("Yaw", "Waiting", txt("10:31", 11, T["faint"])),
        dept_head("Listening", "1", False),
        dept_head("Finance", ""), offer,
        row(chip("Reachable", "assist", 10), extra="padding: 8px 16px; margin-top: auto;"),
        gap=2, extra="flex: 1;")

    def msg(who, tone, t, text, mine=False):
        return row(avatar(who[:2].upper(), tone, 30), col(row(txt(who, 13, weight=600), txt(t, 11.5, T["faint"]), gap=8), txt(text, 13.5, extra="line-height: 1.5;"), gap=3, extra="flex: 1;"),
                   gap=10, align="flex-start", extra=f"padding: 10px 24px; {'background: ' + T['ground'] + ';' if mine else ''}")
    sysline = lambda t: row(txt(t, 11.5, T["faint"]), gap=10, justify="center", extra="padding: 8px 24px;")
    convo = col(sysline("Pinged 10:02, answered 10:05"),
                msg("Ama", "worker", "10:05", "The figures sheet asks for a password from Documents/Reports."),
                msg("You", "admin", "10:07", "It is restricted and synced there by mistake. I\u2019ll send an unlocked copy.", mine=True),
                msg("Ama", "worker", "10:09", "Thanks. I need it before 17:00."),
                sysline("A. Quaye is listening"),
                gap=0, extra="flex: 1; overflow: hidden;")
    composer = row(f'<input type="text" placeholder="Reply" aria-label="Reply" style="flex: 1; height: 38px; padding: 0 14px; border: 1px solid {T["line2"]}; border-radius: 10px; font-family: {T["sans"]}; font-size: 13px;">', btn("Send", "primary"), gap=8, extra=f"padding: 12px 24px 20px; flex: none;")
    pg = col(big_title("Ama", "Your turn", row(btn("Add listener", "secondary", "eye", "sm"), btn("Close", "secondary", "x", "sm"), gap=6)), convo, composer, gap=0, extra="flex: 1; min-height: 0;")

    q = f'<label style="display: flex; align-items: center; gap: 8px; height: 36px; padding: 0 12px; border-radius: 10px; background: {T["ground"]}; margin: 0 16px 8px; color: {T["faint"]};">{ic("search", 15)}<input type="search" value="q3 figures" aria-label="Search files" style="flex: 1; border: 0; outline: 0; background: transparent; font-family: {T["sans"]}; font-size: 13px; color: {T["ink"]};"></label>'
    results = group(grow(ic("file", 14, T["dim"]), "q3-figures.xlsx", "OPS-07", "accent"), grow(ic("lock", 14, T["danger"]), "q3-figures-locked.xlsx", "Restricted", "danger"), grow(ic("file", 14, T["dim"]), "figures-template.xlsx", "Common"), grow(ic("file", 14, T["dim"]), "q3-figures.xlsx", "A. Quaye", last=True), m="0 16px 8px")
    insp = col(insp_title("Files", "Yours, workers, common"), q, results, gap=0, extra="flex: 1; min-height: 0;")
    sh = sheet(side, pg, insp)
    status = statusbar("Connected, TLS pinned", "native   1.4.2")
    return page("Assistance", top, rail, sh, status, "native")


def screen_resources():
    crumbs = [crumb("Operations", "box", "dept"), sep(), crumb("You", "you")]
    top = topbar(crumbs, "Search files", [indicator("Violation", "danger", "shield")])
    rail = icon_rail("home", "admin")
    head = row(txt("Resources", 15, weight=700, extra="flex: 1;"), btn("Add", "primary", "plus", "sm"), gap=6, extra="height: 44px; padding: 0 10px 0 16px; box-sizing: border-box; flex: none;")

    def tier(name, who, n, tone, selected=False):
        bg = T["select"] if selected else "transparent"
        return row(ic("folder", 15, "#fff" if selected else tone_c(tone, T["dim"])), col(txt(name, 13, "#fff" if selected else None, 600, mono=True), txt(who, 11.5, T["select_sub"] if selected else T["faint"]), gap=1, extra="flex: 1;"), txt(n, 11, T["select_sub"] if selected else T["faint"]), gap=8,
                   extra=f"padding: 8px 10px 8px 14px; margin: 0 6px; border-radius: 6px; background: {bg};")
    side = col(head, dept_head("Tiers", ""),
        tier("/restricted/", "Only you", "6", "danger", True), tier("/workers/", "Operations", "31", None), tier("/common/", "Everyone", "12", "ok"),
        dept_head("Violations", "1"), row(sess("su"), col(txt("budget-2026.xlsx", 12.5, mono=True), txt("OPS-07", 11.5, T["faint"]), gap=1), gap=8, extra="padding: 6px 16px;"),
        gap=2, extra="flex: 1;")
    seg = segmented([("Files", "6"), ("Copies", ""), ("Violations", "1")], "Files")
    f = lambda name, when, tone=None, value="", last=False: grow(ic("lock" if tone else "file", 14, tone_c(tone, T["dim"])), name, value or when, tone, last=last)
    files = group(f("budget-2026.xlsx", "Mon", "danger", "Found outside"), f("salaries-q3.xlsx", "Fri"), f("supplier-contracts.pdf", "Fri"), f("ops-review.docx", "Thu"), f("access-list.txt", "Aug"), f("q3-figures-locked.xlsx", "Aug", last=True))
    pg = col(big_title("/restricted/", "Only you, tracked everywhere", chip("Admin only", "danger", 11)), seg, files, gap=0, extra="flex: 1; min-height: 0; overflow: hidden;")

    where = group(grow(txt("", 1), "File", "budget-2026.xlsx", right=""), grow(txt("", 1), "Tier", "/restricted/", "danger", right=""), grow(txt("", 1), "Found in", "/workers/, OPS-07", right=""), grow(txt("", 1), "Matched by", "content", right="", last=True), m="0 16px 8px")
    resolve = col(row(btn("Mark addressed", "primary", "check"), btn("Ping Ama", "secondary", "ping"), gap=8), note_line("Logged. That copy is ignored. Ama was told."), gap=10, extra="padding: 4px 16px 16px;")
    insp = col(insp_title("Violation", "Since 10:41", chip("Open", "danger", 10, dot=True)), where, resolve, gap=0, extra="flex: 1; min-height: 0;")
    sh = sheet(side, pg, insp)
    status = statusbar("Connected, TLS pinned", "native   1.4.2")
    return page("Resources", top, rail, sh, status, "native")


def screen_reports():
    crumbs = [crumb("Operations", "box", "dept"), sep(), crumb("You", "you")]
    top = topbar(crumbs, "Search files", [indicator("2 pings", "warn", "ping")])
    rail = icon_rail("reports", "admin")
    head = row(txt("Reports", 15, weight=700, extra="flex: 1;"), gap=6, extra="height: 44px; padding: 0 10px 0 16px; box-sizing: border-box; flex: none;")

    def nrow(name, n, selected=False, icon="reports"):
        bg = T["select"] if selected else "transparent"
        return row(ic(icon, 14, "#fff" if selected else T["dim"]), txt(name, 13, "#fff" if selected else None, 500 if selected else 400, extra="flex: 1;"), txt(n, 11, T["select_sub"] if selected else T["faint"]), gap=8, extra=f"height: 32px; padding: 0 10px 0 14px; margin: 0 6px; border-radius: 6px; background: {bg};")
    side = col(head, dept_head("Routed to you", ""), nrow("Listener reports", "3", True), nrow("Violations", "1"),
               dept_head("Yours", ""), nrow("Alerts", "2", icon="bell"), nrow("Updates", "1", icon="shield"), nrow("Deviations", "0", icon="warn"),
               gap=2, extra="flex: 1;")
    seg = segmented([("All", "3"), ("Unseen", "1"), ("Seen", "1"), ("Addressed", "1")], "All")
    reps = group(
        grow(dot(T["warn"], 8), "Ama and you", "Unseen", "warn", sub="A. Quaye listening, today"),
        grow(dot(T["line2"], 8), "Kojo and you", "Seen", sub="A. Quaye listening, Mon"),
        grow(dot(T["ok"], 8), "Efua and A. Quaye", "Addressed", "ok", sub="You listening, Fri", last=True),
    )
    pg = col(big_title("Listener reports", "Routed to Operations"), seg, reps, gap=0, extra="flex: 1; min-height: 0; overflow: hidden;")
    about = group(grow(txt("", 1), "Channel", "Ama and you", right=""), grow(txt("", 1), "Listener", "A. Quaye", right=""), grow(txt("", 1), "Also to", "Super User", right="", last=True), m="0 16px 8px")
    marks = row(btn("Mark seen", "secondary", size="sm"), btn("Mark addressed", "primary", "check", "sm"), gap=6, extra="padding: 0 16px 16px;")
    alert = col(f'<textarea aria-label="Alert" placeholder="Tell Operations" style="height: 60px; padding: 8px 10px; border: 0; border-radius: 8px; font-family: {T["sans"]}; font-size: 13px; resize: none;"></textarea>',
                row(chip("Operations", "accent", 10), '<span style="flex: 1;"></span>', btn("Send", "secondary", "bell", "sm"), gap=6), gap=8, extra="padding: 0 16px 16px;")
    upd = col(row(txt("6 of 7 confirmed", 12.5), '<span style="flex: 1;"></span>', txt("OPS-06 retrying", 12, T["faint"]), gap=6), f'<div style="height: 5px; border-radius: 3px; background: {T["line"]};"><div style="height: 5px; border-radius: 3px; background: {T["ok"]}; width: 86%;"></div></div>', gap=8, extra="padding: 0 16px 16px;")
    insp = col(insp_title("Listener report", "Today 10:10"), about, marks, acc("Send an alert", alert, open_=False, summary="to Operations"), acc("Update 1.4.2", upd, open_=False, summary="6 of 7"), gap=0, extra="flex: 1; min-height: 0;")
    sh = sheet(side, pg, insp)
    status = statusbar("Connected, TLS pinned", "native   1.4.2")
    return page("Reports", top, rail, sh, status, "native")
