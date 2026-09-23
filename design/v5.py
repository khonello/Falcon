# ================================================================== v5: the screens, built from the chosen kit
IND = {
    "pings": indicator("2 pings", "warn", "ping"),
    "deadline": indicator("Deadline", "danger", "clock"),
    "flow": indicator("Flow failed", "danger", "flows"),
    "done": indicator("Task done", "ok", "check"),
    "violation": indicator("Violation", "danger", "shield"),
    "offer": indicator("Help offered", "assist", "assistance"),
    "rollout": indicator("Rollout stalled", "danger", "warn"),
}


def screen_admin_home():
    top = topbar2([IND["pings"], IND["deadline"], IND["flow"], IND["done"]], "Go to, do, find")
    rail = icon_rail("home", "admin")
    strip_ = paged([pc_card_av("Ama", "OPS-07", "Deadline reached", "danger", sel=True),
                    pc_card_av("Kojo", "OPS-01", "Needs help", "warn"),
                    pc_card_av("Efua", "OPS-02", "Free", None, "free"),
                    pc_card_av("Yaw", "OPS-03", "Flow failing", "danger")], 0, 2)
    needs = cgroup(
        crow(ic("ping", 16, T["warn"]), "Kojo needs help", "4 min", "warn", right=tbtn("Answer", "warn", size="sm"), sub="OPS-01, twice"),
        crow(ic("clock", 16, T["danger"]), "Quarterly report overdue", "17:00", "danger", right=tbtn("Verify", "accent", size="sm"), sub="Ama, OPS-07", hover=True),
        crow(ic("flows", 16, T["danger"]), "Payroll flow failed", "10:52", "danger", sub="OPS-03 unreachable"),
        crow(ic("shield", 16, T["danger"]), "Restricted file on OPS-07", "10:41", "danger", sub="budget-2026.xlsx"))
    pop = popover("Ama", "OPS-07",
                  col(row(sicon("native", 16), txt("At the PC", 13.5, weight=600), '<span style="flex: 1;"></span>', txt("since 08:14", 12, T["faint"]), gap=8),
                      row(tbtn("Enter", "accent", "lock"), gbtn("End session"), gap=8),
                      note_line("Entering blocks Ama until you leave. 30 min."),
                      gap=10, extra=f"padding: 12px; border-radius: 12px; background: {T['ground']};"),
                  cgroup(crow(dot(T["warn"], 8), "Quarterly report", "Due 17:00", "warn", sub="Task"),
                         crow(dot(T["ok"], 8), "Payroll to Archive", "Syncing", sub="Flow"),
                         crow(dot(T["danger"], 8), "Restricted file", "Open", "danger", sub="Violation"), gap=6),
                  acard("Names", cgroup(crow(txt("", 1), "You call her", "Ama", right=""), crow(txt("", 1), "She sees you as", "R. Mensah", right=""), gap=6), summary="private to you"),
                  lead=av("AM", "worker", 36, "native"),
                  actions=row(tbtn("Ping", "accent", "ping", "sm"), gbtn("Assign task", "tasks", "sm"), gbtn("Run action", "automation", "sm"), gap=6))
    body = bodywrap(drill(("Operations", True)),
                    title_av(f'<span style="width: 40px; height: 40px; border-radius: 12px; background: {T["ground"]}; display: inline-flex; align-items: center; justify-content: center; flex: none;">{ic("dept", 20, T["dim"])}</span>',
                             "Operations", "7 PCs, 2 Admins", right=row(gbtn("Department action", "automation", "sm"), gap=6)),
                    strip_, f'<span style="height: 18px;"></span>',
                    pills2([("Needs you", "4"), ("Quiet", "3"), ("Reports", "2")], "Needs you"),
                    row(col(needs, gap=0, extra=f"width: {BODY_W}px; flex: none;"), lane(pop), gap=22, align="flex-start"))
    sh = sheet(sidebar_ops("OPS-07"), body)
    return page("Admin, at home", top, rail, sh, statusbar("Connected, TLS pinned", "native   1.4.2"), "native")


def screen_su_home():
    """Governance, not operation: what waits on your authority, then the departments, then the trail."""
    rail = su_rail("home")
    top = topbar2([IND["rollout"], IND["offer"], IND["pings"]], "Go to, do, find")

    def dept_card(name, meta, note="", tone=None, sel=False):
        ring_ = f"box-shadow: inset 0 0 0 1px {T['selectline']};" if sel else ""
        return col(row(dept_glyph(tone if tone in ("warn", "danger") else None, "dept", 32),
                       col(txt(name, 14, weight=600), txt(meta, 11.5, T["faint"]), gap=0, extra="flex: 1; min-width: 0;"), gap=10),
                   '<span style="flex: 1;"></span>',
                   txt(note, 12, tone_c(tone, T["dim"]), 500 if tone else 400) if note else "",
                   gap=8, extra=f"width: 206px; height: 104px; box-sizing: border-box; padding: 13px 14px; border-radius: 14px; background: {T['ground']}; {ring_} flex: none;")

    strip_ = paged([dept_card("Operations", "2 Admins, 7 PCs", "", None, True),
                    dept_card("Finance", "1 Admin, 4 PCs"),
                    dept_card("Logistics", "3 PCs", "No Admin", "danger"),
                    f'<a href="#new" style="display: flex; flex-direction: column; align-items: center; justify-content: center; gap: 6px; width: 128px; height: 104px; box-sizing: border-box; border: 1px dashed {T["line2"]}; border-radius: 14px; color: {T["dim"]}; font-size: 12px; text-decoration: none; flex: none;">{ic("plus", 17)}New</a>'], 0, 1)

    waiting = cgroup(
        crow(ic("shield", 16, T["warn"]), "1.4.3 waits on your approval", "12 of 14", "warn", right=tbtn("Open", "accent", size="sm"), sub="two PCs still on 1.4.1"),
        crow(ic("dept", 16, T["danger"]), "Logistics has no Admin", "since Friday", "danger", right=tbtn("Assign", "accent", size="sm"), sub="3 PCs with nobody accountable"),
        crow(ic("eye", 16, T["dim"]), "A routed report is unaddressed", "09:40", right="", sub="Listener report, Operations, seen not addressed"),
        crow(ic("assistance", 16, T["dim"]), "Cross-department assistance", "29 min", right="", sub="A. Quaye helped Finance, reported to you", sel=True))

    pop = popover("A. Quaye helped Finance", "Cross-department assistance",
                  cgroup(crow(av("AQ", "admin", 24), "Helper", "A. Quaye, Operations", right=""),
                         crow(av("KB", "admin", 24), "Asked for help", "K. Boateng, Finance", right=""),
                         crow(txt("", 1), "Lasted", "29 min", right=""),
                         crow(txt("", 1), "Ceiling", "files and screen", right=""), gap=6),
                  note_line("By consent between peers. You see it, you do not gate it."),
                  acard("Every assistance today", cgroup(crow(av("AQ", "admin", 24), "Operations to Finance", "09:31", right=""),
                                                         crow(av("KB", "admin", 24), "Finance to Operations", "Mon", right=""), gap=6), summary="2 sessions"),
                  lead=dept_glyph(None, "assistance", 36))

    body = bodywrap(drill(("Everything", True)),
                    title_av(dept_glyph(icon="shield"), "Everything", "3 departments, 3 Admins, 14 Client PCs",
                             right=row(gbtn("New department", "plus", "sm"), gap=6)),
                    strip_, f'<span style="height: 18px;"></span>',
                    pills2([("Waiting on you", "2"), ("Watching", "2"), ("Trail", "")], "Waiting on you"),
                    row(col(waiting, gap=0, extra=f"width: {BODY_W}px; flex: none;"), lane(pop), gap=22, align="flex-start"))
    sh = sheet(sidebar_all(), body)
    return page("Super User, at home", top, rail, sh, statusbar("Connected, TLS pinned", "native   1.4.2"), "native")


def screen_traversing():
    top = topbar2([IND["pings"]], "Go to, do, find")
    rail = icon_rail("home", "su")
    pill = float_pill("inside OPS-07, through R. Mensah", "warn", tbtn("Extend", "warn", "clock", "sm").replace(T["warn_soft"], "rgba(255,255,255,0.18)").replace(f"color: {T['warn']}", "color: #fff"),
                      gbtn("Leave", size="sm").replace(f"color: {T['dim']}", "color: rgba(255,255,255,0.85)"), timer="21:18")
    metrics = row(tile("CPU", "23 %"), tile("Memory", "6.1 GB", "of 16"), tile("Idle", "0 s"), tile("Window", "EXCEL", "since 10:40"), gap=10)
    sparks = col(sparkrow("CPU", "23 %", "0,22 18,18 36,24 54,10 72,16 90,8 108,18 126,12 140,16"),
                 sparkrow("Memory", "6.1 GB", "0,24 20,23 40,22 60,20 80,19 100,18 120,17 140,17"),
                 sparkrow("Input", "now", "0,26 18,26 36,6 54,26 72,26 90,8 108,26 126,26 140,20", T["ok"]), gap=12,
                 extra=f"padding: 14px; border-radius: 12px; background: {T['ground']};")
    files = cgroup(crow(ic("folder", 15, T["dim"]), "Documents/Reports", "Task target", "accent"),
                   crow(ic("folder", 15, T["dim"]), "resources", "Workers"),
                   crow(ic("lock", 15, T["warn"]), "Personal", "Restricted", "warn"),
                   crow(ic("lock", 15, T["warn"]), "HR-Notes", "Restricted", "warn"))
    pop = popover("Your session", "Nobody can evict you",
                  row(ring(0.71, 56, T["warn"], 5, "21:18"), col(txt("You hold this session", 13.5, weight=600), txt("Ama sees the overlay", 12, T["faint"]), gap=3, extra="flex: 1;"), gap=12,
                      ),
                  row(tbtn("Extend 30 min", "warn", "clock"), gbtn("Leave"), gap=8),
                  acard("How you got here", cgroup(crow(ic("dept", 14, T["faint"]), "Operations", "10:20", right=""), crow(av("RM", "admin", 24, "su"), "R. Mensah", "blocked", "warn", right=""), crow(av("AM", "worker", 24, "su"), "OPS-07", "10:22", right=""), gap=6), open_=True),
                  lead=av("AM", "worker", 36, "su"))
    body = bodywrap(pill, drill(("Operations", False), ("R. Mensah", False), ("Ama", True)),
                    title_av(av("AM", "worker", 40, "su"), "Ama", "OPS-07, restricted folders open for you", trail=time_chip("21:18")),
                    pills2([("Live", ""), ("Files", "6"), ("Task", "1")], "Live"),
                    row(col(metrics, f'<span style="height: 10px;"></span>', sparks, f'<span style="height: 10px;"></span>', files, gap=0, extra=f"width: {BODY_W}px; flex: none;"), lane(pop), gap=22, align="flex-start"),
                    pad="14px 28px 22px")
    sh = sheet(sidebar_all(inside=True, sel="OPS-07"), body, state="traversing")
    return page("Super User, inside a PC", top, rail, sh, statusbar("Connected, TLS pinned", "traversing OPS-07   21:18 left", "warn"), "traversing")


def screen_occupied():
    top = topbar2([IND["pings"], IND["deadline"]], "Go to, do, find")
    rail = icon_rail("home", "admin")
    pill = float_pill("Super User is in charge of your view", "danger", tbtn("Claim", "danger", "lock", "sm").replace(T["danger_soft"], "rgba(255,255,255,0.18)").replace(f"color: {T['danger']}", "color: #fff"), timer="21:18")
    locked = col(ring(0.71, 72, T["danger"], 5, "21:18"), txt("Read only", 20, weight=600), txt("Until Super User leaves.", 13, T["faint"]),
                 row(tbtn("Claim native session", "danger", "lock"), gap=6),
                 gap=12, extra="align-items: center; justify-content: center; padding: 36px 0; flex: none;")
    waiting = cgroup(crow(ic("ping", 16, T["warn"]), "Kojo needs help", "4 min", "warn"), crow(ic("clock", 16, T["danger"]), "Quarterly report overdue", "17:00", "danger"))
    body = bodywrap(pill, drill(("Operations", True)),
                    title_av(f'<span style="width: 40px; height: 40px; border-radius: 12px; background: {T["ground"]}; display: inline-flex; align-items: center; justify-content: center; flex: none;">{ic("dept", 20, T["dim"])}</span>', "Operations", "7 PCs, 2 Admins"),
                    col(locked, f'<span style="height: 8px;"></span>', txt("Waiting for you", 12, T["faint"], 600, extra="padding: 0 4px 8px;"), waiting, gap=0, extra="max-width: 620px;"),
                    pad="14px 28px 22px")
    sh = sheet(sidebar_ops("OPS-07", "occupied"), body, state="occupied")
    return page("Admin, occupied from above", top, rail, sh, statusbar("Connected, TLS pinned", "held by Super User   21:18 left", "danger"), "occupied")


def screen_assisted():
    top = topbar2([IND["pings"]], "Go to, do, find")
    rail = icon_rail("assistance", "admin")
    pill = float_pill("helping K. Boateng, files and screen only", "assist", gbtn("End help", size="sm").replace(f"color: {T['dim']}", "color: rgba(255,255,255,0.85)"))
    side = col(sb_head("Assistance", False), sb_section("Helping", "1"), sb_person("K. Boateng", "FIN-02", "assisted", "KB", "admin", sel=True),
               sb_section("You can reach", ""),
               *[row(ic("check" if ok else "x", 14, T["accent"] if ok else T["faint"]), txt(t, 12.5, None if ok else T["faint"]), gap=9, extra="padding: 5px 16px;")
                 for t, ok in [("Screen, read only", True), ("Workers and common files", True), ("Control and actions", False), ("Restricted files", False)]],
               sb_legend(), gap=2, extra="flex: 1;")
    screen = f'<div style="height: 300px; border-radius: 14px; background: linear-gradient(135deg, #2b3542, #1b2430); display: flex; align-items: center; justify-content: center; color: {T["frame_dim"]}; font-size: 13px;">FIN-02, live</div>'
    talk = col(*[row(av(w[:2].upper(), "admin", 28, "assisted" if w != "You" else "native"), col(row(txt(w, 12.5, weight=600), txt(t, 11, T["faint"]), gap=7), txt(x, 12.5, extra="line-height: 1.45;"), gap=2, extra="flex: 1;"), gap=10, align="flex-start", extra="padding: 8px 0;")
                 for w, t, x in [("K. Boateng", "11:02", "Payroll export hangs at 40 % since the update."), ("You", "11:05", "There is a lock file from Monday. Delete it and retry.")]], gap=0)
    composer = row(f'<input type="text" placeholder="Message" aria-label="Message" style="flex: 1; height: 38px; padding: 0 13px; border: 0; border-radius: 10px; background: {T["ground"]}; font-family: {T["sans"]}; font-size: 13.5px; color: {T["ink"]};">', tbtn("Send", "accent"), gap=8)
    body = bodywrap(pill, drill(("Finance", False), ("K. Boateng", True)),
                    title_av(av("KB", "admin", 40, "assisted"), "K. Boateng", "Finance, by consent", trail=chip("Read only", "accent", 11, dot=True)),
                    row(col(screen, gap=0, extra="flex: 1; min-width: 0;"), col(talk, f'<span style="height: 8px;"></span>', composer, gap=0, extra="width: 380px; flex: none;"), gap=20, align="flex-start"),
                    pad="14px 28px 22px")
    sh = sheet(side, body, state="assisted")
    return page("Assisted access", top, rail, sh, statusbar("Connected, TLS pinned", "assisting FIN-02", "ok"), "assisted")


def screen_tasks():
    top = topbar2([IND["pings"], IND["deadline"]], "Go to, do, find")
    rail = icon_rail("tasks", "admin")
    side = col(sb_head("Tasks"), sb_section("To review", "1"), sb_item("tasks", "Q3 supplier reconciliation", "Nana", sel=True),
               sb_section("In progress", "3"), sb_item("tasks", "Quarterly report", "Ama", right=chip("Overdue", "danger", 10)), sb_item("tasks", "Onboarding pack", "Kojo"), sb_item("tasks", "Invoice batch", "Nana", right=txt("Fri", 11, T["faint"])),
               sb_section("To verify", "1"), sb_item("tasks", "Fleet inventory", "Yaw", right=chip("Done?", "ok", 10)),
               sb_section("Closed", "12", False), gap=2, extra="flex: 1;")
    quote = (f'<div style="padding: 13px 16px; border-radius: 12px; background: {T["ground"]}; font-size: 13.5px; line-height: 1.55; color: {T["dim"]}; max-width: 620px;">'
             f'Reconcile the Q3 supplier invoices against <b style="color: {T["ink"]}; font-weight: 500;">suppliers-q3.xlsx</b> and produce '
             f'<b style="color: {T["ink"]}; font-weight: 500;">reconciliation-q3.docx</b> by <b style="color: {T["warn"]}; font-weight: 500;">Monday or Wednesday</b>. Also archive last quarter\u2019s folder.</div>')
    decisions = cgroup(
        crow(num(1, done=True), "Targets", "2 found", right=""),
        crow(num(2, "warn"), "Name collision", "Deciding", "warn", sel=True),
        crow(num(3, "warn"), "Deadline", "Monday or Wednesday", "warn"),
        crow(num(4), "Two tasks?", "Archive folder"))
    pop = popover("Name collision", "Decision 2 of 4",
                  txt("reconciliation-q3.docx already exists on OPS-05, in Documents/Finance, changed 12 Aug.", 13.5, extra="line-height: 1.5;"),
                  col(tbtn("Overwrite, it is intended", "warn"), gbtn("Mean the existing file"), gbtn("Rename the new one"), gap=8),
                  acard("Where it lives", cgroup(crow(ic("file", 15, T["dim"]), "reconciliation-q3.docx", "12 Aug", right=""),
                                                 crow(ic("folder", 15, T["dim"]), "Documents/Finance", "OPS-05", right=""), gap=6), summary="OPS-05"),
                  acard("Other decisions", cgroup(crow(num(1, done=True), "Targets", "2 found", right=""),
                                                  crow(num(3, "warn"), "Deadline", "Mon or Wed", "warn", right=""),
                                                  crow(num(4), "Two tasks?", "Archive folder", right=""), gap=6), summary="3 left"),
                  lead=num(2, "warn"))
    foot = row('<span style="flex: 1;"></span>', gbtn("Discard"), tbtn("Confirm and assign", "accent", "check", disabled=True), txt("after 3 decisions", 12, T["faint"]), gap=10, extra="padding-top: 14px; flex: none;")
    body = bodywrap(drill(("Tasks", False), ("Q3 supplier reconciliation", True)),
                    title_av(av("NA", "worker", 40, "native"), "Q3 supplier reconciliation", "Proposed for Nana, OPS-05", trail=chip("Draft", "accent", 11)),
                    pills2([("Review", "3"), ("Targets", "2"), ("Deadline", ""), ("Assignee", "")], "Review"),
                    row(col(quote, f'<span style="height: 14px;"></span>', decisions, foot, gap=0, extra=f"width: {BODY_W}px; flex: none;"), lane(pop), gap=22, align="flex-start"))
    sh = sheet(side, body)
    return page("Tasks", top, rail, sh, statusbar("Connected, TLS pinned", "native   1.4.2"), "native")


def screen_flows():
    top = topbar2([IND["flow"]], "Go to, do, find")
    rail = icon_rail("flows", "admin")
    side = col(sb_head("Flows"), sb_section("Yours", "4"),
               sb_item("flows", "Payroll to Archive", "2 destinations", sel=True, right=chip("Failing", "danger", 10, dot=True)),
               sb_item("flows", "Worker resources", "7 PCs", right=chip("Syncing", "ok", 10)),
               sb_item("flows", "Common resources", "Everyone", right=chip("Syncing", "ok", 10)),
               sb_item("flows", "Photos to shared", "OPS-02", right=chip("Paused", "warn", 10)),
               sb_section("Awaiting consent", "1"), sb_item("flows", "Finance handover", "A. Quaye", right=chip("Consent", "accent", 10)), gap=2, extra="flex: 1;")
    gw, gh = 612, 290
    edges = (f'<svg width="{gw}" height="{gh}" viewBox="0 0 {gw} {gh}" style="position: absolute; left: 0; top: 0;" aria-hidden="true">'
             f'<defs><marker id="ah" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8z" fill="{T["line2"]}"/></marker>'
             f'<marker id="ahd" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto"><path d="M0 0L8 4L0 8z" fill="{T["danger"]}"/></marker></defs>'
             f'<path d="M190 144 L 210 144" stroke="{T["line2"]}" stroke-width="1.75" fill="none" marker-end="url(#ah)"/>'
             f'<path d="M392 144 C 404 144, 404 71, 414 71" stroke="{T["line2"]}" stroke-width="1.75" fill="none" marker-end="url(#ah)"/>'
             f'<path d="M392 144 C 404 144, 404 217, 414 217" stroke="{T["danger"]}" stroke-width="1.75" fill="none" stroke-dasharray="5 4" marker-end="url(#ahd)"/></svg>')
    nodes = "".join([place(14, 105, gnode("Source", "C:\\Payroll\\out", "accent", "monitor")),
                     place(214, 105, gnode("Branch", "Categorize by type", None, "branch")),
                     place(414, 32, gnode("OPS-05", "D:\\Archive\\payroll", "ok")),
                     place(414, 178, gnode("OPS-03", "D:\\Archive\\payroll", "danger"))])
    graph = (f'<div style="position: relative; width: {gw}px; height: {gh}px; border-radius: 14px; background: {T["ground"]}; overflow: hidden; flex: none;">{edges}{nodes}'
             f'<div style="position: absolute; left: 16px; top: 14px; display: flex; gap: 6px;">{chip("No cycles", "ok", 10)}{chip("1 collision resolved", "neutral", 10)}</div></div>')
    failing = crow(dot(T["danger"], 8), "OPS-03 unreachable", "since 10:52", "danger", right=tbtn("Fix", "danger", size="sm"))
    pop = popover("History", "Newest first",
                  col(log_group("Today",
                                crow(dot(T["danger"], 8), "Sync failed, OPS-03", "10:52", right=""),
                                crow(dot(T["ok"], 8), "14 files to OPS-05", "10:50", right=""),
                                crow(dot(T["warn"], 8), "Conflict kept as -modified", "10:12", right="")),
                      f'<span style="height: 12px;"></span>',
                      log_group("Monday", crow(dot(T["line2"], 8), "Collision confirmed", "14:02", right="")), gap=0),
                  acard("Consent", cgroup(crow(av("NA", "worker", 24), "OPS-05", "Yours", "ok", right=""), crow(av("YA", "worker", 24), "OPS-03", "Yours", "ok", right=""), gap=6), summary="none needed"),
                  lead=f'<span style="width: 36px; height: 36px; border-radius: 12px; background: {T["ground"]}; display: inline-flex; align-items: center; justify-content: center; flex: none;">{ic("flows", 18, T["dim"])}</span>')
    body = bodywrap(drill(("Flows", False), ("Payroll to Archive", True)),
                    title_av(f'<span style="width: 40px; height: 40px; border-radius: 12px; background: {T["ground"]}; display: inline-flex; align-items: center; justify-content: center; flex: none;">{ic("flows", 20, T["dim"])}</span>',
                             "Payroll to Archive", "You to OPS-05 and OPS-03", trail=chip("Failing", "danger", 11, dot=True), right=row(gbtn("Pause", "pause", "sm"), gbtn("Sync now", "play", "sm"), gap=4)),
                    pills2([("Graph", ""), ("Log", "5"), ("Stages", "2")], "Graph"),
                    row(col(graph, f'<span style="height: 12px;"></span>', failing, gap=0, extra="flex: none; width: 612px;"), lane(pop), gap=22, align="flex-start"))
    sh = sheet(side, body)
    return page("Flows", top, rail, sh, statusbar("Connected, TLS pinned", "native   1.4.2"), "native")


def screen_automation():
    top = topbar2([IND["pings"]], "Go to, do, find")
    rail = icon_rail("automation", "admin")
    modes = row(*[f'<a href="#{l.lower()}" style="flex: 1; text-align: center; padding: 6px 0; border-radius: 8px; background: {T["pane"] if l == "Dashboard" else "transparent"}; color: {T["ink"] if l == "Dashboard" else T["dim"]}; font-size: 12.5px; font-weight: 600; text-decoration: none;">{l}</a>' for l in ("Dashboard", "Editing")],
                gap=2, extra=f"padding: 3px; border-radius: 10px; background: {T['line']}; margin: 6px 12px 4px;")
    side = col(sb_head("Automation", False), modes, sb_section("Running", "2"), sb_item("automation", "USB inserted", "OPS-02", sel=True), sb_item("automation", "Idle 20 min", "OPS-06"),
               sb_section("Armed", "5"), sb_item("automation", "Login"), sb_item("automation", "File change"), sb_item("automation", "Every day 17:30"), sb_item("automation", "CPU over 90 %"), sb_item("automation", "Logout"), gap=2, extra="flex: 1;")
    st = lambda tone, word: row(dot(tone_c(tone, T["accent"]), 8), txt(word, 12, tone_c(tone, T["accent"]), 600, extra="width: 58px;"), gap=8)
    runs = cgroup(
        crow(st("accent", "Running"), "USB inserted", "OPS-02, 12 s", right=tbtn("Stop", "danger", "stop", "sm")),
        crow(st("accent", "Running"), "Idle 20 min", "OPS-06, 3 min", right=tbtn("Stop", "danger", "stop", "sm")),
        crow(st("ok", "Done"), "USB inserted", "OPS-02, 10:58"),
        crow(st("ok", "Done"), "Login", "OPS-04, 10:20"),
        crow(st("warn", "Timeout"), "CPU over 90 %", "OPS-03, 60 s"),
        crow(st("danger", "Error"), "Logout", "OPS-01, Mon 17:31", sel=True))
    pop = popover("Logout", "clear temp on OPS-01",
                  row(chip("Error", "danger", 11, dot=True), txt("exit code 1", 12.5, T["faint"], mono=True), gap=8),
                  f'<pre style="margin: 0; padding: 12px 13px; border-radius: 12px; background: {T["ground"]}; color: {T["ink"]}; font-family: {T["mono"]}; font-size: 11.5px; line-height: 1.55; white-space: pre-wrap; word-break: break-word; overflow: hidden;">Remove-Item : Access to the path &#39;C:\Temp\lock&#39; is denied.</pre>',
                  cgroup(crow(txt("", 1), "Started", "Mon 17:31", right=""), crow(txt("", 1), "Timeout", "60 s", right=""), gap=6),
                  acard("The event", cgroup(crow(ic("camera", 15, T["dim"]), "Screenshot", "30 s", right=""), crow(ic("file", 15, T["dim"]), "Log event", "10 s", right=""),
                                            crow(ic("automation", 15, T["dim"]), "clear temp", "60 s", right=""), gap=6), summary="Logout, 3 actions"),
                  acard("Custom script", f'<pre style="margin: 0; padding: 11px 13px; border-radius: 10px; background: {T["ground"]}; color: {T["ink"]}; font-family: {T["mono"]}; font-size: 11.5px; line-height: 1.5; white-space: pre-wrap; word-break: break-word; overflow: hidden;">Get-ChildItem C:\Temp -Recurse | Remove-Item -Force</pre>', summary="validated"),
                  lead=f'<span style="width: 36px; height: 36px; border-radius: 12px; background: {T["danger_soft"]}; display: inline-flex; align-items: center; justify-content: center; flex: none;">{ic("automation", 18, T["danger"])}</span>',
                  actions=row(tbtn("Run again", "accent", "play", "sm"), gbtn("Open event", size="sm"), gap=6))
    body = bodywrap(drill(("Automation", False), ("Dashboard", True)),
                    title_av(f'<span style="width: 40px; height: 40px; border-radius: 12px; background: {T["ground"]}; display: inline-flex; align-items: center; justify-content: center; flex: none;">{ic("automation", 20, T["dim"])}</span>', "Dashboard", "Live, this department"),
                    pills2([("All", "6"), ("Running", "2"), ("Done", "2"), ("Timeout", "1"), ("Error", "1")], "All"),
                    row(col(runs, gap=0, extra=f"width: {BODY_W}px; flex: none;"), lane(pop), gap=22, align="flex-start"))
    sh = sheet(side, body)
    return page("Automation", top, rail, sh, statusbar("Connected, TLS pinned", "native   1.4.2"), "native")


def screen_assistance():
    top = topbar2([IND["pings"], IND["offer"]], "Go to, do, find")
    rail = icon_rail("assistance", "admin")
    offer = col(row(sicon("assisted", 15), txt("K. Boateng offers help", 12.5, weight=500), gap=8), row(tbtn("Accept", "accent", size="sm"), gbtn("Decline", size="sm"), gap=6),
                gap=9, extra=f"margin: 2px 12px; padding: 11px 12px; border-radius: 12px; background: {T['accent_soft']};")
    side = col(sb_head("Assistance", False), sb_section("Pings", "2"), sb_person("Kojo", "4 min", "native", right=chip("2", "warn", 10)), sb_person("Nana", "12 min", "native", right=chip("1", "warn", 10)),
               sb_section("Channels", "2"), sb_person("Ama", "Your turn", "native", sel=True), sb_person("Yaw", "Waiting", "native", right=txt("10:31", 11, T["faint"])),
               sb_section("Listening", "1"), sb_person("A. Quaye and Efua", "", "native", "AQ", "admin", right=ic("eye", 14, T["faint"])),
               sb_section("Finance", ""), offer, gap=2, extra="flex: 1;")
    msg = lambda who, tone, t, x, state="native": row(av(who[:2].upper(), tone, 30, state), col(row(txt(who, 13, weight=600), txt(t, 11.5, T["faint"]), gap=8), txt(x, 13.5, extra="line-height: 1.5;"), gap=3, extra="flex: 1;"), gap=11, align="flex-start", extra="padding: 9px 0;")
    sysline = lambda t: row('<span style="flex: 1;"></span>', txt(t, 11.5, T["faint"]), '<span style="flex: 1;"></span>', gap=8, extra="padding: 8px 0;")
    talk = col(sysline("Pinged 10:02, answered 10:05"),
               msg("Ama", "worker", "10:05", "The figures sheet asks for a password from Documents/Reports."),
               msg("You", "admin", "10:07", "It is restricted and synced there by mistake. I\u2019ll send an unlocked copy."),
               msg("Ama", "worker", "10:09", "Thanks. I need it before 17:00."),
               sysline("A. Quaye is listening"), gap=0, extra="flex: 1;")
    composer = col(row(chip("Your turn", "accent", 10, dot=True), txt("Ama is locked until you send", 12, T["faint"]), gap=8),
                   row(f'<input type="text" placeholder="Reply" aria-label="Reply" style="flex: 1; height: 40px; padding: 0 14px; border: 0; border-radius: 12px; background: {T["ground"]}; font-family: {T["sans"]}; font-size: 13.5px; color: {T["ink"]};">', tbtn("Send", "accent"), gap=8), gap=9)
    pop = popover("Files", "Yours, workers, common",
                  f'<label style="display: flex; align-items: center; gap: 9px; height: 38px; padding: 0 12px; border-radius: 11px; background: {T["ground"]}; color: {T["faint"]};">{ic("search", 15)}<input type="search" value="q3 figures" aria-label="Search files" style="flex: 1; border: 0; outline: 0; background: transparent; font-family: {T["sans"]}; font-size: 13.5px; color: {T["ink"]};"></label>',
                  cgroup(crow(ic("file", 15, T["dim"]), "q3-figures.xlsx", "OPS-07", "accent", right=""),
                         crow(ic("lock", 15, T["danger"]), "q3-figures-locked.xlsx", "Restricted", "danger", right=""),
                         crow(ic("file", 15, T["dim"]), "figures-template.xlsx", "Common", right=""), gap=6),
                  lead=f'<span style="width: 36px; height: 36px; border-radius: 12px; background: {T["ground"]}; display: inline-flex; align-items: center; justify-content: center; flex: none;">{ic("search", 18, T["dim"])}</span>')
    body = bodywrap(drill(("Assistance", False), ("Ama", True)),
                    title_av(av("AM", "worker", 40, "native"), "Ama", "Your turn", right=row(gbtn("Add listener", "eye", "sm"), gbtn("Close", "x", "sm"), gap=4)),
                    row(col(talk, composer, gap=0, extra=f"width: {BODY_W}px; flex: none;"), lane(pop), gap=22, align="flex-start"))
    sh = sheet(side, body)
    return page("Assistance", top, rail, sh, statusbar("Connected, TLS pinned", "native   1.4.2"), "native")


def screen_resources():
    top = topbar2([IND["violation"]], "Go to, do, find")
    rail = icon_rail("home", "admin")
    side = col(sb_head("Resources"), sb_section("Tiers", ""),
               sb_item("lock", "/restricted/", "Only you", sel=True, right=txt("6", 11, T["select_sub"])),
               sb_item("folder", "/workers/", "Operations", right=txt("31", 11, T["faint"])),
               sb_item("folder", "/common/", "Everyone", right=txt("12", 11, T["faint"])),
               sb_section("Violations", "1"), sb_item("shield", "budget-2026.xlsx", "OPS-07", right=chip("Open", "danger", 10, dot=True)), gap=2, extra="flex: 1;")
    files = cgroup(crow(ic("lock", 15, T["danger"]), "budget-2026.xlsx", "Found outside", "danger", sub="412 KB, Monday"),
                   crow(ic("file", 15, T["dim"]), "salaries-q3.xlsx", "Friday", sub="88 KB"),
                   crow(ic("file", 15, T["dim"]), "supplier-contracts.pdf", "Friday", sub="2.1 MB"),
                   crow(ic("file", 15, T["dim"]), "ops-review.docx", "Thursday", sub="140 KB"))
    pop = popover("Violation", "Since 10:41",
                  cgroup(crow(txt("", 1), "File", "budget-2026.xlsx", right=""), crow(txt("", 1), "Tier", "/restricted/", "danger", right=""),
                         crow(av("AM", "worker", 24, "native"), "Found on", "OPS-07, /workers/", right=""), crow(txt("", 1), "Matched by", "content hash", right=""), gap=6),
                  note_line("Logged. That copy is ignored. Ama was told."),
                  lead=f'<span style="width: 36px; height: 36px; border-radius: 12px; background: {T["danger_soft"]}; display: inline-flex; align-items: center; justify-content: center; flex: none;">{ic("shield", 18, T["danger"])}</span>',
                  actions=row(tbtn("Mark addressed", "ok", "check", "sm"), gbtn("Ping Ama", "ping", "sm"), gap=6))
    body = bodywrap(drill(("Resources", False), ("/restricted/", True)),
                    title_av(f'<span style="width: 40px; height: 40px; border-radius: 12px; background: {T["danger_soft"]}; display: inline-flex; align-items: center; justify-content: center; flex: none;">{ic("lock", 20, T["danger"])}</span>',
                             "/restricted/", "Only you, tracked everywhere", trail=chip("Admin only", "danger", 11)),
                    pills2([("Files", "6"), ("Copies", ""), ("Violations", "1")], "Files"),
                    row(col(files, gap=0, extra=f"width: {BODY_W}px; flex: none;"), lane(pop), gap=22, align="flex-start"))
    sh = sheet(side, body)
    return page("Resources", top, rail, sh, statusbar("Connected, TLS pinned", "native   1.4.2"), "native")


def screen_reports():
    top = topbar2([IND["pings"]], "Go to, do, find")
    rail = icon_rail("reports", "admin")
    side = col(sb_head("Reports", False), sb_section("Routed to you", ""), sb_item("reports", "Listener reports", right=chip("3", "neutral", 10), sel=True), sb_item("shield", "Violations", right=chip("1", "neutral", 10)),
               sb_section("Yours", ""), sb_item("bell", "Alerts", right=txt("2", 11, T["faint"])), sb_item("shield", "Updates", right=chip("1", "warn", 10)), sb_item("warn", "Deviations", right=txt("0", 11, T["faint"])), gap=2, extra="flex: 1;")
    reps = col(log_group("Today",
                         crow(av("AM", "worker", 26, "native"), "Ama and you", "Unseen", "warn", sub="A. Quaye listening, 10:10", hover=True),
                         crow(av("KO", "worker", 26, "native"), "Kojo and you", "Seen", sub="A. Quaye listening, 09:30")),
               f'<span style="height: 12px;"></span>',
               log_group("Friday", crow(av("EF", "worker", 26, "native"), "Efua and A. Quaye", "Addressed", "ok", sub="You listening")), gap=0)
    pop = popover("Listener report", "Today 10:10",
                  cgroup(crow(txt("", 1), "Channel", "Ama and you", right=""), crow(av("AQ", "admin", 24), "Listener", "A. Quaye", right=""), crow(txt("", 1), "Also to", "Super User", right=""), gap=6),
                  acard("Update 1.4.2", col(barline("Operations", "6 of 7", 0.86, T["ok"]), note_line("OPS-06 retries when idle."), gap=8), summary="6 of 7"),
                  acard("Send an alert", col(f'<textarea aria-label="Alert" placeholder="Tell Operations" style="height: 62px; padding: 10px 12px; border: 0; border-radius: 10px; background: {T["ground"]}; font-family: {T["sans"]}; font-size: 13px; color: {T["ink"]}; resize: none; width: 100%; box-sizing: border-box;"></textarea>',
                                             row(chip("Operations", "accent", 10), '<span style="flex: 1;"></span>', tbtn("Send", "accent", "bell", "sm"), gap=6), gap=8), summary="to Operations"),
                  lead=f'<span style="width: 36px; height: 36px; border-radius: 12px; background: {T["ground"]}; display: inline-flex; align-items: center; justify-content: center; flex: none;">{ic("reports", 18, T["dim"])}</span>',
                  actions=row(tbtn("Mark addressed", "ok", "check", "sm"), gbtn("Mark seen", size="sm"), gap=6))
    body = bodywrap(drill(("Reports", False), ("Listener reports", True)),
                    title_av(f'<span style="width: 40px; height: 40px; border-radius: 12px; background: {T["ground"]}; display: inline-flex; align-items: center; justify-content: center; flex: none;">{ic("reports", 20, T["dim"])}</span>',
                             "Listener reports", "Routed to Operations"),
                    pills2([("All", "3"), ("Unseen", "1"), ("Seen", "1"), ("Addressed", "1")], "All"),
                    row(col(reps, f'<span style="height: 16px;"></span>', toast("Marked addressed", "ok", gbtn("Undo", size="sm")), gap=0, extra=f"width: {BODY_W}px; flex: none;"), lane(pop), gap=22, align="flex-start"))
    sh = sheet(side, body)
    return page("Reports", top, rail, sh, statusbar("Connected, TLS pinned", "native   1.4.2"), "native")
