# ================================================================== TK04-TK07, AU04: Tasks and Automation, composed from the picks
# The picks off TK01-TK03 and AU01 (DECISIONS.md 3a), composed into whole pages the way DP05 was
# composed off DP01-DP04. Where a section got more than one pick they are COMBINED here, not chosen
# between, and every cell says which pick it carries.
#
#   TK04  the Tasks page         TK01 "Four cells" + "By person"
#   TK05  describing a task      TK02 "Side by side" + "Decisions, one at a time" + "Asked where it
#                                stands" + "The split, drafted"
#   TK06  one task, running      TK03 "A checklist" + "The file itself" + "Review, then decide"
#   TK07  what the assignee sees TK03 "What the assignee sees"
#   AU04  the Automation page    AU01 "When | then" + "A recipe card" + "What it did"
#
# These are the Admin's own pages (the rail is theirs -- LEVELS.md, level 3), drawn in the Overview's
# language because "Four cells" was the pick. Nothing is typed as code anywhere on them.

ADMIN_AREAS = [("hierarchy", "Hierarchy", "home"), ("tasks", "Tasks", "tasks"), ("flows", "Flows", "flows"),
               ("automation", "Automation", "automation"), ("actions", "Actions", "play"),
               ("assistance", "Assistance", "assistance"), ("reports", "Reports", "reports")]


def work_title(crumbs, heading, phrase, tone, right="Wednesday, 14:20"):
    trail = []
    for i, step in enumerate(crumbs):
        if i:
            trail.append(ic("chev", 12, T["frame_faint"]))
        trail.append(txt(step, 12.5, "#fff" if i == len(crumbs) - 1 else T["frame_faint"],
                         600 if i == len(crumbs) - 1 else 400))
    return col(row(*trail, gap=6, extra="flex: none;"),
               row(txt(heading, 24, "#fff", 700, extra="letter-spacing: -0.3px;"),
                   txt(phrase, 13, tone_c(tone, T["frame_dim"]), 500), sp(),
                   txt(right, 12.5, T["frame_faint"]), gap=12, extra="width: 100%; flex: none;"),
               gap=5, extra="flex: none;")


def work_page(title, active, crumbs, heading, phrase, tone, bands, note, brow):
    top = topbar2([IND["pings"], IND["deadline"]], "Go to, do, find")
    rail = held_rail(active, ADMIN_AREAS, foot=("RM", "Admin"))
    inner = col(brow, work_title(crumbs, heading, phrase, tone), *bands,
                row(txt(note, 11.5, T["frame_faint"]), gap=0, extra="flex: none;") if note else "",
                gap=12, extra="flex: 1; min-width: 0; display: flex; flex-direction: column; "
                              "padding: 6px 22px 8px 6px; box-sizing: border-box; overflow: hidden;")
    return page(title, top, rail, inner, statusbar("Connected, TLS pinned", "native   1.4.2", "ok"), "native")


def w_line(left, right="", tone=None, lead="", sub="", strong=False):
    body = col(txt(left, 12.5, T["ink"] if strong else T["dim"], 600 if strong else 400),
               txt(sub, 11, T["faint"]) if sub else "", gap=1, extra="min-width: 0;")
    return row(lead, body, sp(), txt(right, 12, tone_c(tone, T["faint"]), 600) if right else "",
               gap=10, extra=f"width: 100%; padding: 8px 0; border-bottom: 1px solid {T['line']};")


def person_head(initials, name, count, host=""):
    return row(av(initials, "worker", 26), txt(name, 13, T["ink"], 600),
               txt(host, 11, T["faint"], mono=True) if host else "", sp(), txt(count, 11.5, T["faint"]), gap=9,
               extra="width: 100%;")


# ------------------------------------------------------------------ TK04: the Tasks page
# SIGNATURE: A WIDE LEFT COLUMN. The two wide cells stack on the left -- what needs you, and who is
# carrying what -- with the two narrow ones down the right. The department is a pinwheel and the
# Overview a perfect grid; this is neither.
def tk04():
    def needs_row(initials, who, task, state, tone, act=""):
        return row(av(initials, "worker", 26), col(txt(task, 12.5, T["ink"], 600), txt(who, 11, T["faint"]), gap=1),
                   sp(), txt(state, 12, tone_c(tone, T["faint"]), 600), act, gap=10,
                   extra=f"width: 100%; padding: 8px 0; border-bottom: 1px solid {T['line']};")

    needs = row(
        col(txt("To review — the model has proposed, you decide", 11.5, T["faint"], 600),
            needs_row("NA", "Nana · OPS-05", "Q3 reconciliation", "2 decisions left", "accent"),
            needs_row("KO", "Kojo · OPS-01", "Onboarding pack", "ready to assign", "accent"),
            gap=2, extra="flex: 1; min-width: 0;"),
        col(txt("To verify — the work is in", 11.5, T["faint"], 600),
            needs_row("YA", "Yaw · OPS-03", "Fleet inventory", "2 of 2 checks", "ok"),
            txt("Given to you", 11.5, T["faint"], 600, extra="padding-top: 12px;"),
            row(av("SU", "admin", 26), col(txt("Department audit", 12.5, T["ink"], 600),
                                           txt("from the Super User · by Friday", 11, T["faint"]), gap=1),
                sp(), tbtn("Start", "accent", "play", "sm"), gap=10,
                extra=f"width: 100%; padding: 8px 0; border-bottom: 1px solid {T['line']};"),
            gap=2, extra="flex: 1; min-width: 0;"),
        gap=36, align="flex-start", extra="width: 856px;")

    def person(initials, name, host, tasks):
        return col(person_head(initials, name, f"{len(tasks)} task{'s' if len(tasks) != 1 else ''}", host),
                   col(*[w_line(t, d, tone) for t, d, tone in tasks], gap=0, extra="padding-left: 35px;"),
                   gap=4, extra="flex: 1; min-width: 0;")

    people = row(person("NA", "Nana", "OPS-05", [("Q3 reconciliation", "Wed", "warn"), ("Invoice batch", "Fri", None)]),
                 person("AM", "Ama", "OPS-07", [("Quarterly report", "overdue", "danger")]),
                 person("YA", "Yaw", "OPS-03", [("Fleet inventory", "to verify", "ok")]),
                 gap=28, align="flex-start", extra="width: 856px;")

    deadlines = reading_block("Ama is a day past the final deadline.",
                              [("Quarterly report", "overdue", "danger"), ("Q3 reconciliation", "Wednesday", "warn"),
                               ("Invoice batch", "Friday", "")], "", w=396)
    closed = col(txt("Six closed this week; one was sent back.", 15, T["ink"], 600, extra="line-height: 1.35;"),
                 row(txt("Verified", 12.5, T["ink"], 600), txt("Sent back", 12.5, T["faint"]), gap=18),
                 w_line("Printer audit", "verified", "ok", sub="Kojo · Tuesday"),
                 w_line("Leave forms", "sent back", "warn", sub="Efua · Monday"),
                 row(txt("All of them are in Record", 12, T["accent"], 500), ic("chev", 12, T["accent"]), gap=4,
                     extra="padding-top: 4px;"),
                 gap=10, extra="width: 396px;")

    return work_page(
        "Tasks", "tasks", ["Tasks"], "Tasks", "four waiting on you", "accent",
        [row(kcell("Needs you", "4 things", "accent", needs, w=900, h=316, top=True),
             kcell("Deadlines", "one overdue", "danger", deadlines, w=440, h=316, top=True),
             gap=20, align="stretch", extra="flex: none;"),
         row(kcell("By person", "who is carrying what", "dim", people, w=900, h=340, top=True),
             kcell("Closed", "hands off to Record", "dim", closed, w=440, h=340, top=True),
             gap=20, align="stretch", extra="flex: none;")],
        "TK04 · Four cells (TK01) with the list By person (TK01). No assigner anywhere: on your own page it is "
        "always you. A task given TO you names who gave it and carries Start. Closed hands off to Record.",
        eyebrow("PAGE", "Tasks — an Admin's", "a wide left column"))


# ------------------------------------------------------------------ TK05: describing a task
# SIGNATURE: SIDE BY SIDE. Your words on the left, the structure they filled on the right. The
# questions the model could not settle are ASKED WHERE THEY STAND in the structure, worked down ONE
# AT A TIME (the strip at the top of the structure says which), and a detected split is DRAFTED at
# the foot as a concrete choice. Confirm is last, and waits for the decisions.
def tk05():
    step = lambda n, label, state: row(
        f'<span style="width: 22px; height: 22px; border-radius: 11px; display: inline-flex; align-items: center; '
        f'justify-content: center; font-family: {T["sans"]}; font-size: 11px; font-weight: 700; '
        f'background: {T["warn"] if state == "now" else T["ok_soft"] if state == "done" else T["ground"]}; '
        f'color: {"#0d1018" if state == "now" else T["ok"] if state == "done" else T["faint"]};">'
        f'{ic("check", 12, T["ok"], 2.4) if state == "done" else n}</span>',
        txt(label, 12, T["ink"] if state == "now" else T["faint"], 600 if state == "now" else 400), gap=7)

    you_write = col(
        row(txt("For", 12, T["faint"]),
            row(av("NA", "worker", 22), txt("Nana", 12.5, T["ink"], 600), txt("OPS-05", 11, T["faint"], mono=True),
                ic("chevd", 12, T["faint"]), gap=7,
                extra=f"padding: 5px 10px; border-radius: 9px; background: {T['pane']};"), gap=10),
        (f'<div style="width: 100%; height: 250px; box-sizing: border-box; padding: 14px 16px; border-radius: 12px; '
         f'background: {T["pane"]}; box-shadow: inset 0 0 0 1px {T["line2"]}; font-family: {T["sans"]}; font-size: 14px; '
         f'line-height: 1.6; color: {T["ink"]};">Reconcile the Q3 supplier invoices against suppliers-q3.xlsx and '
         f'produce reconciliation-q3.docx by Monday or Wednesday. Also archive last quarter&#8217;s folder.</div>'),
        row(tbtn("Propose again", "accent", "pulse", "sm"), sp(),
            txt("Read by the local model. Nothing is assigned until you confirm.", 11.5, T["faint"]), gap=10,
            extra="width: 100%;"),
        gap=14, extra="width: 396px;")

    it_fills = col(
        row(step(1, "Which deadline", "now"), step(2, "A name that exists", "next"), step(3, "Two tasks", "next"),
            sp(), txt("3 decisions before you can assign", 11.5, T["faint"]), gap=18, extra="width: 100%;"),
        rule(),
        w_line("suppliers-q3.xlsx", "found in the index, OPS-05", lead=tk_tag("Update", "accent"), strong=True),
        col(row(tk_tag("Create", "ok"), txt("reconciliation-q3.docx", 12.5, T["ink"], 600), sp(),
                txt("already exists on OPS-05", 12, T["danger"], 600), gap=10, extra="width: 100%;"),
            row(gbtn("Rename the new one", size="sm"), gbtn("It means the existing file", size="sm"),
                gbtn("Give a folder", size="sm"), gap=4, extra="padding-left: 60px;"),
            gap=6, extra=f"width: 100%; padding: 8px 0; border-bottom: 1px solid {T['line']};"),
        col(row(txt("Deadline", 12.5, T["ink"], 600), sp(), txt("you wrote both — which applies?", 12, T["warn"], 600),
                gap=10, extra="width: 100%;"),
            row(tbtn("Monday 17:00", "warn", size="sm"), tbtn("Wednesday 17:00", "warn", size="sm"),
                txt("a soft reminder the day before", 11.5, T["faint"]), gap=8),
            gap=8, extra=f"width: 100%; padding: 10px 12px; margin: 4px 0; border-radius: 10px; "
                         f"background: {T['warn_soft']}; box-sizing: border-box;"),
        row(col(txt("This reads as two tasks.", 13, T["ink"], 600),
                txt("Everything else is shared: Nana, the same deadline.", 11.5, T["faint"]), gap=2),
            sp(),
            col(txt("1 · Reconcile Q3", 12, T["dim"], 600), txt("2 files", 11, T["faint"]), gap=1,
                extra=f"padding: 7px 11px; border-radius: 9px; background: {T['pane']};"),
            col(txt("2 · Archive Q2 folder", 12, T["dim"], 600), txt("1 folder", 11, T["faint"]), gap=1,
                extra=f"padding: 7px 11px; border-radius: 9px; background: {T['pane']};"),
            tbtn("Split as shown", "accent", size="sm"), gbtn("Keep as one", size="sm"),
            gap=10, extra="width: 100%; padding-top: 8px;"),
        sp(),
        row(gbtn("No verification applies", size="sm"), sp(),
            txt("after 3 decisions", 11.5, T["faint"]), tbtn("Confirm and assign", "accent", "check", disabled=True),
            gap=10, extra="width: 100%;"),
        gap=8, extra="width: 796px; height: 100%;")

    return work_page(
        "Tasks — describing one", "tasks", ["Tasks", "New task"], "New task", "the model has proposed; you decide",
        "accent",
        [row(kcell("You write", "plain language", "dim", you_write, w=440, h=676, top=True),
             kcell("It fills", "3 decisions left", "warn", it_fills, w=900, h=676, top=True),
             gap=20, align="stretch", extra="flex: none;")],
        "TK05 · Side by side (TK02). Decisions one at a time: the strip names the current one. Asked where it "
        "stands: each question sits on the line it is about. The split, drafted. Confirm waits for all three.",
        eyebrow("PAGE", "Tasks — describing one", "side by side"))


# ------------------------------------------------------------------ TK06: one task, running -- and closing it
# SIGNATURE: TWO BANDS AND A TALL LANE. The checks and the files stack on the left; the verdict runs
# the full height on the right, because closing is the one thing on this page only the assigner does.
def tk06():
    checks = col(
        *[row(tk_check(st), col(txt(n, 13, T["ink"], 600), txt(m, 11.5, T["faint"]), gap=1), sp(),
              tk_tag(i, tone), gap=12, extra=f"width: 100%; padding: 10px 0; border-bottom: 1px solid {T['line']};")
          for st, n, m, i, tone in [("pass", "suppliers-q3.xlsx", "changed at 10:42, after the task began", "Update", "accent"),
                                    ("pass", "reconciliation-q3.docx", "created at 13:05", "Create", "ok"),
                                    ("fail", "Excel, on that file", "Excel ran 25 minutes, never on this file", "Used with", "accent")]],
        txt("Signs of work, never proof of it. The checks inform; the verdict is yours.", 11.5, T["faint"],
            extra="padding-top: 4px;"),
        gap=0, extra="width: 856px;")

    def file_card(name, where, lines, on=True):
        return col(row(ic("file", 18, T["accent"] if on else T["faint"]),
                       txt(name, 14, T["ink"] if on else T["dim"], 600, mono=True), gap=9),
                   txt(where, 11.5, T["faint"]),
                   *[row(dot(T["accent"] if on else T["line2"], 6), txt(l_, 12, T["dim"]), gap=8) for l_ in lines],
                   gap=8, extra=f"flex: 1; min-width: 0; padding: 14px; border-radius: 12px; background: {T['pane']};")

    files = row(file_card("suppliers-q3.xlsx", "D:/Finance/Q3 on OPS-05",
                          ["changed 3 times today", "last at 10:42", "open in Excel for 25 min"]),
                file_card("reconciliation-q3.docx", "C:/Users/nana/Documents on OPS-05",
                          ["created at 13:05", "changed once since", "found by name, wherever it was saved"]),
                gap=14, align="stretch", extra="width: 856px;")

    verdict = col(
        txt("Two of three checks passed. Excel was never used on the file.", 15, T["ink"], 600,
            extra="line-height: 1.35;"),
        txt("Look at the work first", 11.5, T["faint"], 600),
        w_line("suppliers-q3.xlsx", "Open", "accent", lead=tk_check("pass")),
        w_line("reconciliation-q3.docx", "Open", "accent", lead=tk_check("pass")),
        w_line("Excel, on that file", "", lead=tk_check("fail")),
        sp(),
        col(txt("Only you can close this task, and only as a whole.", 12, T["dim"], extra="line-height: 1.4;"),
            row(tbtn("Complete", "ok", "check"), tbtn("Send back", "warn"), gap=8),
            gap=10),
        gap=10, extra="width: 356px; height: 100%;")

    return work_page(
        "Tasks — one task", "tasks", ["Tasks", "Q3 reconciliation"], "Q3 reconciliation", "Nana · OPS-05 · due Wednesday",
        "dim",
        [row(col(kcell("The checks", "two of three passed", "warn", checks, w=900, h=316, top=True),
                 kcell("The files", "tracked by name, not by folder", "dim", files, w=900, h=340, top=True),
                 gap=20, extra="flex: none;"),
             kcell("Review, then decide", "yours alone", "accent", verdict, w=440, h=676, top=True),
             gap=20, align="stretch", extra="flex: none;")],
        "TK06 · A checklist + The file itself (TK03, while it runs) and Review, then decide (TK03, closing). "
        "The verdict runs the full height: it is the one act on this page that belongs to the assigner.",
        eyebrow("PAGE", "Tasks — one task, running and closing", "two bands and a tall lane"))


# ------------------------------------------------------------------ TK07: what the assignee sees
# A Worker has no Operator Client: they get the Worker Dialog, the small helper window (spec 5). It is
# drawn here on a stand-in desktop at its real size. Start, and the signs of work -- never verify.
def tk07():
    desk = "linear-gradient(135deg, #1b2a3a 0%, #243b53 55%, #2f4f6b 100%)"
    dialog = col(
        row(ic("tasks", 16, T["accent"]), txt("A task from R. Mensah", 12.5, T["dim"], 500), sp(),
            ic("close", 14, T["faint"]), gap=8, extra="width: 100%;"),
        txt("Q3 reconciliation", 20, T["ink"], 700),
        txt("Reconcile the Q3 supplier invoices against suppliers-q3.xlsx and produce reconciliation-q3.docx.",
            13, T["dim"], extra="line-height: 1.5;"),
        row(ic("clock", 14, T["warn"]), txt("Due Wednesday at 17:00", 12.5, T["warn"], 600), gap=7),
        rule(),
        txt("What will show the work is happening", 11.5, T["faint"], 600),
        w_line("suppliers-q3.xlsx", "changed 10:42", "ok", lead=ic("file", 15, T["accent"])),
        w_line("reconciliation-q3.docx", "not yet", None, lead=ic("file", 15, T["faint"]),
               sub="save it anywhere; it is found by name"),
        w_line("Excel, on that file", "not yet", None, lead=ic("window", 15, T["faint"])),
        sp(),
        row(txt("R. Mensah closes it when the work is checked.", 11.5, T["faint"]), sp(),
            tbtn("Start", "accent", "play"), gap=10, extra="width: 100%;"),
        gap=11, extra=f"width: 460px; height: 560px; box-sizing: border-box; padding: 20px 22px; border-radius: 16px; "
                      f"background: {T['pane']}; box-shadow: 0 24px 60px rgba(0,0,0,0.55);")
    inner = col(eyebrow("SURFACE", "The Worker Dialog — what the assignee sees", "a helper window, not the Operator Client"),
                row(txt("Tasks: what the assignee sees", 22, "#fff", 700), gap=0, extra="flex: none;"),
                row(dialog, gap=0, justify="center",
                    extra=f"flex: 1; align-items: center; border-radius: 14px; background: {desk};"),
                txt("TK07 · What the assignee sees (TK03). Start, and the signs of work being tracked. There is no "
                    "Complete here: only the assigner closes a task.", 11.5, T["frame_faint"]),
                gap=14, extra=f"width: {W}px; height: {H}px; box-sizing: border-box; padding: 24px 40px; "
                              f"background: {FRAME['native']};")
    return page("Tasks — the assignee", "", "", inner, "", "native")


# ------------------------------------------------------------------ AU04: the Automation page
# SIGNATURE: A TALL LIST AND A STACK. Every automation down the left as WHEN -> DO, joined; the one
# chosen is read on the right as a recipe card, and what it did sits under it. Single click chooses.
def au04():
    rows_ = [("file", "A restricted file is opened", "any Operations machine", [("bell", "Notify me"), ("lock", "Lock the folder")], True),
             ("cpu", "The disk is nearly full", "every machine", [("terminal", "Clear temp")], False),
             ("clock", "Weekdays at 18:00", "every machine", [("lock", "Lock the screen")], False),
             ("key", "A USB drive is plugged in", "OPS-03, OPS-07", [("eye", "USB contents"), ("bell", "Notify me")], False),
             ("user", "Someone signs in after 20:00", "every machine", [("bell", "Notify me")], False),
             ("cpu", "The processor stays busy", "above 85 % for 5 min", [("eye", "Programs running")], False)]

    def auto_row(i1, when, where, dos, sel):
        fill = (f"background: {T['select']}; border-radius: 11px; padding: 10px 12px; margin: 0 -12px;"
                if sel else f"padding: 10px 0; border-bottom: 1px solid {T['line']};")
        return row(row(au_icon(i1, "accent", 28), col(txt(when, 12.5, "#fff" if sel else T["ink"], 600),
                                                      txt(where, 11, T["select_sub"] if sel else T["faint"]), gap=1),
                       gap=10, extra="width: 270px; flex: none;"),
                   ic("arrow", 15, T["faint"]),
                   # the user, 26 Sep 2026: "actions are multiple, show first one with , ... or etc." --
                   # one line per automation; the recipe card on the right is where they are all listed
                   row(au_icon(dos[0][0], "ok", 22), txt(dos[0][1], 12, T["dim"]),
                       txt(f"+ {len(dos) - 1} more", 11.5, T["faint"]) if len(dos) > 1 else "", gap=8),
                   gap=14, extra=f"width: 100%; {fill}")

    listing = col(*[auto_row(*r) for r in rows_],
                  row(tbtn("New automation", "accent", "plus", "sm"), gap=0, extra="padding-top: 12px;"),
                  gap=0, extra="width: 576px;")

    recipe = col(
        txt("WHEN", 11, T["faint"], 700),
        row(au_icon("file", "accent", 34), col(txt("A restricted file is opened", 14, T["ink"], 600),
                                               txt("in Restricted files, on any Operations machine", 11.5, T["faint"]), gap=2), gap=11),
        txt("DO, IN ORDER", 11, T["faint"], 700, extra="padding-top: 6px;"),
        row(txt("1", 12, T["faint"], 600, mono=True), au_icon("bell", "ok", 30), col(txt("Notify me", 13, T["dim"], 600),
                                                                                    txt("right away", 11, T["faint"]), gap=1), gap=10),
        row(txt("2", 12, T["faint"], 600, mono=True), au_icon("lock", "ok", 30), col(txt("Lock the folder", 13, T["dim"], 600),
                                                                                    txt("right away · gives up after 1 min", 11, T["faint"]), gap=1), gap=10),
        row(sp(), gbtn("Pause it", "pause", "sm"), tbtn("Change", "accent", size="sm"), gap=6, extra="width: 100%;"),
        gap=9, extra="width: 656px;")

    did = col(
        row(dot(T["accent"], 7), txt("Running now: Lock the folder on OPS-03, 12 seconds in", 12.5, T["ink"], 500), sp(),
            gbtn("Stop", "stop", "sm"), gap=9, extra="width: 100%;"),
        *[row(txt(t, 11.5, T["faint"], mono=True, extra="width: 44px; flex: none;"),
              txt(w, 12.5, T["dim"]), sp(), txt(r, 12, tone_c(tone, T["faint"]), 600), gap=10,
              extra=f"width: 100%; padding: 8px 0; border-bottom: 1px solid {T['line']};")
          for t, w, r, tone in [("11:41", "OPS-07 · budget-2026.xlsx · notified, locked", "clean", "ok"),
                                ("10:02", "OPS-03 · payroll.xlsx · notified, lock gave up", "lock timed out", "warn"),
                                ("08:55", "OPS-07 · budget-2026.xlsx · notified, locked", "clean", "ok")]],
        gap=4, extra="width: 656px;")

    return work_page(
        "Automation", "automation", ["Automation"], "Automation", "six set up, one running", "dim",
        [row(kcell("When · then", "six automations", "dim", listing, w=620, h=676, top=True),
             col(kcell("Chosen", "fired 3 times today", "ok", recipe, w=720, h=316, top=True),
                 kcell("What it did", "one running now", "accent", did, w=720, h=340, top=True),
                 gap=20, extra="flex: none;"),
             gap=20, align="stretch", extra="flex: none;")],
        "AU04 · When | then (AU01) down the left; the chosen one as A recipe card (AU01), with What it did "
        "(AU01) beneath it. No tabs: Dashboard, Events and Executions are one page now.",
        eyebrow("PAGE", "Automation — an Admin's", "a tall list and a stack"))


WORK_PAGES = [("TK04-Tasks.dc.html", "Tasks: the page, from the picks", tk04),
              ("TK05-Describing.dc.html", "Tasks: describing one", tk05),
              ("TK06-Running.dc.html", "Tasks: one task, running and closing", tk06),
              ("TK07-Assignee.dc.html", "Tasks: what the assignee sees", tk07),
              ("AU04-Automation.dc.html", "Automation: the page, from the picks", au04)]
