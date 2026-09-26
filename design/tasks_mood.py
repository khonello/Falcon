# ================================================================== The Tasks mood board, TK01-TK03
# The user, 26 Sep 2026, on the pre-kit Tasks screen: "the task structure being table doesn't sit right
# and doesn't reflect what we discuss for task creation at all, LLM, etc. input and structure that is
# populated" -- and, of its columns, "why is assigner necessary since the user is assigner".
#
# Same format as DP01-DP04: one facet per board, two sections, four approaches side by side at the same
# size, captioned so a pick can be named. Nothing here is a finished screen. Everything is drawn from
# task-natural-combo.md: describe it in plain language -> the local LLM populates the structure
# (targets + intent, deadline, a split) -> anything uncertain comes back as a question, never a silent
# guess -> the assigner confirms, or says "None" explicitly -> the assignee starts it -> expectations
# show work happening -> ONLY the assigner verifies, as a whole.
#
# One sample throughout, so the cells compare: Nana on OPS-05, "Reconcile the Q3 supplier invoices
# against suppliers-q3.xlsx and produce reconciliation-q3.docx by Monday or Wednesday. Also archive
# last quarter's folder."

TK_CW, TK_CH = 316, 240


def tk_cell(name, html, note="", h=None):
    box = (f'<div style="width: {TK_CW}px; height: {h or TK_CH}px; box-sizing: border-box; border-radius: 12px; '
           f'background: {T["pane"]}; padding: 16px; overflow: hidden; position: relative; display: flex; '
           f'flex-direction: column; gap: 10px;">{html}</div>')
    return col(row(txt(name, 12.5, "#fff", 600), txt(note, 11.5, T["frame_faint"]) if note else "", gap=8), box, gap=6)


def tk_tag(text, tone="accent"):
    """An intent or a state, as a word on a soft fill of its tone -- a word, never only a colour."""
    return (f'<span style="display: inline-flex; align-items: center; padding: 2px 8px; border-radius: 999px; '
            f'background: {T[tone + "_soft"]}; color: {T[tone]}; font-family: {T["sans"]}; font-size: 10.5px; '
            f'font-weight: 600; white-space: nowrap;">{text}</span>')


def tk_mark(text, tone="accent"):
    """A span of the description the model read something from: underlined in the tone of what it is."""
    return (f'<span style="color: {T["ink"]}; font-weight: 600; border-bottom: 2px solid {T[tone]}; '
            f'padding-bottom: 1px;">{text}</span>')


def tk_line(left, right="", tone=None, lead="", sub=""):
    body = col(txt(left, 12, T["dim"]), txt(sub, 10.5, T["faint"]) if sub else "", gap=1)
    return row(lead, body, sp(), txt(right, 11.5, tone_c(tone, T["faint"]), 600) if right else "",
               gap=8, extra=f"width: 100%; padding: 6px 0; border-bottom: 1px solid {T['line']};")


def tk_check(state):
    """One verification item's state: passed, failed, or not yet -- the stack's own vocabulary."""
    c = {"pass": T["ok"], "fail": T["danger"], "wait": T["line2"]}[state]
    icon = {"pass": ic("check", 11, "#10131a", 2.4), "fail": ic("x", 11, "#10131a", 2.4), "wait": ""}[state]
    return (f'<span style="width: 18px; height: 18px; border-radius: 6px; background: {c}; display: inline-flex; '
            f'align-items: center; justify-content: center; flex: none;">{icon}</span>')


def tk_dots(*states, size=9, gap=4):
    c = {"pass": T["ok"], "fail": T["danger"], "wait": T["line2"]}
    return row(*[f'<span style="width: {size}px; height: {size}px; border-radius: 3px; background: {c[s]}; '
                 f'display: inline-block;"></span>' for s in states], gap=gap, extra="flex: none;")


def tk_wire(*boxes):
    return dp_wire(*boxes)


# ------------------------------------------------------------------ TK01: the page, and one task listed
def tk01():
    # A. by stage: the lifecycle IS the layout
    a = tk_cell("By stage", tk_wire(dp_box(28, 10, 78, 128, label="to review"),
                                    dp_box(111, 10, 78, 128, label="moving"),
                                    dp_box(194, 10, 78, 128, label="to verify")),
                "where each task stands")
    # B. a lead and a column: the list narrow, the chosen task wide
    b = tk_cell("Lead and column", tk_wire(dp_box(28, 10, 76, 128, label="tasks"),
                                           dp_box(112, 10, 160, 128, label="the chosen task")),
                "one task at a time")
    # C. four cells, the Overview's language: what needs you is the wide one
    c = tk_cell("Four cells", tk_wire(dp_box(28, 10, 160, 62, label="needs you"),
                                      dp_box(196, 10, 76, 62, label="moving"),
                                      dp_box(28, 80, 76, 58, label="deadlines"),
                                      dp_box(112, 80, 160, 58, label="the week")),
                "the Overview's language")
    # D. a timeline: every task a bar, read against its deadline
    d = tk_cell("By deadline", tk_wire(dp_box(28, 10, 244, 18, label="Mon · Tue · Wed · Thu · Fri"),
                                       *[dp_box(28 + x, 36 + i * 22, w, 14, fill=f)
                                         for i, (x, w, f) in enumerate([(0, 150, T["accent_soft"]),
                                                                        (40, 120, T["warn_soft"]),
                                                                        (90, 154, T["accent_soft"]),
                                                                        (10, 70, T["danger_soft"]),
                                                                        (120, 100, T["accent_soft"])])]),
                "read against the clock")
    s1 = msection("The shape of the Tasks page", a, b, c, d)

    # One task, listed. Never the assigner: on your own page it is always you, so the line names
    # only who it is FOR. (An Admin's task FROM the Super User says "from Super User" instead.)
    e = tk_cell("Name and person", col(
        *[row(col(txt(n, 12.5, T["ink"], 600), txt(p, 11, T["faint"]), gap=1), sp(), txt(r, 11.5, tone_c(t, T["faint"]), 600),
              gap=8, extra=f"width: 100%; padding: 7px 0; border-bottom: 1px solid {T['line']};")
          for n, p, r, t in [("Q3 reconciliation", "Nana · OPS-05", "to review", "accent"),
                             ("Quarterly report", "Ama · OPS-07", "overdue", "danger"),
                             ("Fleet inventory", "Yaw · OPS-03", "to verify", "ok")]], gap=0),
        "the quietest; no assigner")
    f = tk_cell("A sentence", col(
        *[col(txt(s_, 12.5, T["ink"], 500, extra="line-height: 1.35;"), txt(m, 11, T["faint"]), gap=2,
              extra=f"width: 100%; padding: 7px 0; border-bottom: 1px solid {T['line']};")
          for s_, m in [("Nana has 1 of 3 files; due Wednesday.", "Q3 reconciliation"),
                        ("Ama is a day past the final deadline.", "Quarterly report"),
                        ("Yaw's 2 checks passed; yours to verify.", "Fleet inventory")]], gap=0),
        "generated, twelve words")
    g = tk_cell("The stack as marks", col(
        *[row(col(txt(n, 12.5, T["ink"], 600), txt(p, 11, T["faint"]), gap=1), sp(), tk_dots(*ds), txt(r, 11, T["faint"]),
              gap=10, extra=f"width: 100%; padding: 7px 0; border-bottom: 1px solid {T['line']};")
          for n, p, ds, r in [("Q3 reconciliation", "Nana", ("pass", "wait", "wait"), "Wed"),
                              ("Quarterly report", "Ama", ("pass", "fail"), "late"),
                              ("Fleet inventory", "Yaw", ("pass", "pass"), "Fri")]], gap=0),
        "each check a square")
    h = tk_cell("By person", col(
        row(av("NA", "worker", 24), txt("Nana", 12.5, T["ink"], 600), sp(), txt("2 tasks", 11, T["faint"]), gap=8),
        col(tk_line("Q3 reconciliation", "Wed"), tk_line("Invoice batch", "Fri"), gap=0, extra="padding-left: 32px;"),
        row(av("AM", "worker", 24), txt("Ama", 12.5, T["ink"], 600), sp(), txt("1 task", 11, T["faint"]), gap=8),
        col(tk_line("Quarterly report", "overdue", "danger"), gap=0, extra="padding-left: 32px;"),
        gap=6), "who is carrying what")
    s2 = msection("One task, listed — who it is for, never who set it", e, f, g, h)
    return board("Tasks: the page", s1, s2)


# ------------------------------------------------------------------ TK02: describing it, and what comes back
DESC = ("Reconcile the Q3 supplier invoices against suppliers-q3.xlsx and produce reconciliation-q3.docx "
        "by Monday or Wednesday. Also archive last quarter's folder.")


def tk_desc_marked(size=12):
    return txt(f'Reconcile the Q3 supplier invoices against {tk_mark("suppliers-q3.xlsx", "accent")} and produce '
               f'{tk_mark("reconciliation-q3.docx", "accent")} by {tk_mark("Monday or Wednesday", "warn")}. '
               f'{tk_mark("Also archive last quarter&#8217;s folder.", "danger")}', size, T["dim"],
               extra="line-height: 1.55;")


def tk_input(text, h=64, placeholder=False):
    return (f'<div style="width: 100%; height: {h}px; box-sizing: border-box; padding: 9px 11px; border-radius: 9px; '
            f'background: {T["ground"]}; box-shadow: inset 0 0 0 1px {T["line2"]}; font-family: {T["sans"]}; '
            f'font-size: 11.5px; line-height: 1.45; color: {T["faint"] if placeholder else T["dim"]}; overflow: hidden;">{text}</div>')


def tk02():
    # Where you describe it: natural language is the INPUT; the structure is what it populates
    a = tk_cell("One box, then the proposal", col(
        row(txt("For", 11.5, T["faint"]), av("NA", "worker", 20), txt("Nana · OPS-05", 12, T["dim"]), gap=7),
        tk_input(DESC, 84),
        row(sp(), tbtn("Propose", "accent", "pulse", "sm"), gap=0, extra="width: 100%;"),
        txt("The model reads it; nothing is committed.", 10.5, T["faint"]),
        gap=9), "describe, then ask")
    b = tk_cell("Side by side", row(
        col(txt("You write", 10.5, T["faint"], 600), tk_input(DESC, 150), gap=5, extra="width: 128px; flex: none;"),
        col(txt("It fills", 10.5, T["faint"], 600),
            tk_line("suppliers-q3.xlsx", "", lead=tk_tag("Update", "accent")),
            tk_line("reconciliation-q3.docx", "", lead=tk_tag("Create", "ok")),
            tk_line("Deadline", "?", "warn"), gap=0, extra="flex: 1; min-width: 0;"),
        gap=12, align="flex-start"), "the structure beside the words")
    c = tk_cell("The words, marked", col(
        tk_desc_marked(12),
        row(row(dot(T["accent"], 7), txt("a target", 10.5, T["faint"]), gap=4),
            row(dot(T["warn"], 7), txt("unclear", 10.5, T["faint"]), gap=4),
            row(dot(T["danger"], 7), txt("another task?", 10.5, T["faint"]), gap=4), gap=12),
        gap=12), "what was read, where it was read")
    d = tk_cell("A single line", col(
        tk_input("Have Nana reconcile Q3 invoices against suppliers-q3.xlsx…", 36),
        txt("Enter to propose", 10.5, T["faint"]),
        rule(),
        txt("Proposed for Nana", 11, T["faint"], 600),
        tk_line("suppliers-q3.xlsx", "Update"), tk_line("reconciliation-q3.docx", "Create"),
        gap=7), "like a command")
    s1 = msection("Describing it — plain language is the input", a, b, c, d)

    # What comes back: the model PROPOSES; whatever it could not settle is asked, one question at a time
    e = tk_cell("The structure, proposed", col(
        tk_line("suppliers-q3.xlsx", "proposed", lead=tk_tag("Update", "accent"), sub="in the index, OPS-05"),
        tk_line("reconciliation-q3.docx", "proposed", lead=tk_tag("Create", "ok"), sub="name only; no path given"),
        tk_line("Excel, on that file", "proposed", lead=tk_tag("Used with", "accent")),
        tk_line("Deadline", "Mon or Wed?", "warn"),
        gap=0), "every line marked as the model's")
    f = tk_cell("Decisions, one at a time", col(
        row(txt("3 decisions before you can assign", 11.5, T["faint"]), gap=0),
        *[row(f'<span style="width: 20px; height: 20px; border-radius: 10px; background: {T["ground"]}; display: inline-flex; '
              f'align-items: center; justify-content: center; font-size: 10.5px; color: {T["dim"]}; font-family: {T["sans"]};">{i}</span>',
              txt(q, 12, T["ink"] if i == 1 else T["dim"], 600 if i == 1 else 400), sp(), txt(v, 11, tone_c(t, T["faint"]), 600),
              gap=9, extra=f"width: 100%; padding: 8px 0; border-bottom: 1px solid {T['line']};")
          for i, q, v, t in [(1, "Which deadline?", "Mon · Wed", "warn"),
                             (2, "reconciliation-q3.docx exists", "rename?", "danger"),
                             (3, "Two tasks?", "archive", None)]],
        gap=2), "a queue you work down")
    g = tk_cell("Asked where it stands", col(
        tk_line("suppliers-q3.xlsx", "", lead=tk_tag("Update", "accent")),
        col(row(txt("Deadline", 12, T["dim"]), sp(), gap=0),
            row(tbtn("Monday", "warn", size="sm"), tbtn("Wednesday", "warn", size="sm"), gap=6),
            txt("You wrote both; which applies?", 10.5, T["faint"]), gap=6,
            extra=f"width: 100%; padding: 8px 0; border-bottom: 1px solid {T['line']};"),
        tk_line("reconciliation-q3.docx", "", lead=tk_tag("Create", "ok")),
        gap=0), "the question inside the structure")
    h = tk_cell("The split, drafted", col(
        txt("This reads as two tasks.", 12.5, T["ink"], 600),
        row(col(txt("1 · Reconcile Q3", 11.5, T["dim"], 600), txt("2 files · Wed", 10.5, T["faint"]), gap=2,
                extra=f"flex: 1; padding: 9px; border-radius: 9px; background: {T['ground']};"),
            col(txt("2 · Archive Q2", 11.5, T["dim"], 600), txt("1 folder · Wed", 10.5, T["faint"]), gap=2,
                extra=f"flex: 1; padding: 9px; border-radius: 9px; background: {T['ground']};"), gap=8),
        row(tbtn("Split as shown", "accent", size="sm"), gbtn("Keep as one", size="sm"), gap=6),
        gap=10), "a concrete choice, not a question")
    s2 = msection("What comes back — proposed, never settled for you", e, f, g, h)
    return board("Tasks: describing one", s1, s2)


# ------------------------------------------------------------------ TK03: while it runs, and closing it
def tk03():
    # The stack while the work happens: expectations say work is moving, never that it is done
    a = tk_cell("A checklist", col(
        *[row(tk_check(st), col(txt(n, 12, T["ink"], 500), txt(m, 10.5, T["faint"]), gap=1), sp(),
              txt(i, 10.5, T["faint"]), gap=9, extra=f"width: 100%; padding: 7px 0; border-bottom: 1px solid {T['line']};")
          for st, n, m, i in [("pass", "suppliers-q3.xlsx", "changed 10:42", "Update"),
                              ("wait", "reconciliation-q3.docx", "not created yet", "Create"),
                              ("wait", "Excel, on that file", "open 25 min, active", "Used with")]],
        gap=0), "the stack, as the doc draws it")
    b = tk_cell("Signals over time", col(
        txt("Work on Nana's files today", 11.5, T["faint"]),
        *[row(txt(n, 11, T["dim"], mono=True, extra="width: 92px; flex: none; overflow: hidden;"),
              (f'<div style="flex: 1; height: 12px; position: relative;">'
               + "".join(f'<span style="position: absolute; left: {x}%; width: 3px; height: 12px; border-radius: 2px; background: {c};"></span>'
                         for x in xs) + '</div>'), gap=8, extra="width: 100%;")
          for n, xs, c in [("suppliers…", [8, 12, 30, 34, 36, 61], T["accent"]),
                           ("reconcil…", [], T["accent"]),
                           ("Excel", [10, 11, 12, 13, 14, 30, 31, 32, 60, 61], T["ok"])]],
        row(txt("08", 10, T["faint"], mono=True), sp(), txt("12", 10, T["faint"], mono=True), sp(),
            txt("16", 10, T["faint"], mono=True), gap=0, extra="width: 100%; padding-left: 100px; box-sizing: border-box;"),
        gap=10), "is work happening")
    c = tk_cell("A reading", col(
        txt("One of three is done; the new file is not made yet.", 12.5, T["ink"], 600, extra="line-height: 1.35;"),
        tk_line("Started", "09:15"), tk_line("Last activity", "10:42"), tk_line("Due", "Wednesday", "warn"),
        gap=6), "a sentence and its facts")
    d = tk_cell("The file itself", col(
        row(ic("file", 16, T["accent"]), txt("suppliers-q3.xlsx", 12.5, T["ink"], 600, mono=True), gap=8),
        txt("D:/Finance/Q3 · changed 10:42 · 3 times today", 10.5, T["faint"]),
        rule(),
        row(ic("file", 16, T["faint"]), txt("reconciliation-q3.docx", 12.5, T["dim"], 600, mono=True), gap=8),
        txt("watched by name; appears when Nana saves it", 10.5, T["faint"]),
        gap=8), "targets by identity, not a folder")
    s1 = msection("While it runs — signs of work, never proof of it", a, b, c, d)

    # Closing it: ONLY the assigner, and only the whole task
    e = tk_cell("At the foot of the stack", col(
        row(tk_check("pass"), txt("suppliers-q3.xlsx", 12, T["dim"]), gap=9, extra="padding: 5px 0;"),
        row(tk_check("pass"), txt("reconciliation-q3.docx", 12, T["dim"]), gap=9, extra="padding: 5px 0;"),
        row(tk_check("fail"), txt("Excel, on that file", 12, T["dim"]), gap=9, extra="padding: 5px 0;"),
        rule(),
        row(tbtn("Complete", "ok", "check", "sm"), gbtn("Incomplete", size="sm"), sp(), txt("the task, whole", 10.5, T["faint"]),
            gap=6, extra="width: 100%;"),
        gap=4), "checks first, then the verdict")
    f = tk_cell("Review, then decide", col(
        txt("Look at the work first", 11.5, T["faint"]),
        tk_line("suppliers-q3.xlsx", "Open", "accent", lead=tk_check("pass")),
        tk_line("reconciliation-q3.docx", "Open", "accent", lead=tk_check("pass")),
        row(tbtn("Complete", "ok", size="sm"), tbtn("Send back", "warn", size="sm"), gap=6, extra="padding-top: 6px;"),
        gap=4), "the work, not only the checks")
    g = tk_cell("A verdict line", col(
        txt("Two of three checks passed. Excel was never used on the file.", 12.5, T["ink"], 600,
            extra="line-height: 1.35;"),
        row(tbtn("Complete anyway", "ok", size="sm"), tbtn("Incomplete", "danger", size="sm"), gap=6),
        txt("The checks inform; you decide.", 10.5, T["faint"]),
        gap=10), "said, then decided")
    h = tk_cell("What the assignee sees", col(
        row(av("NA", "worker", 24), txt("Nana's view", 12, T["ink"], 600), gap=8),
        tk_line("Q3 reconciliation", "started", "accent"),
        txt("Expectations tracked as you work. Only the person who set this can close it.", 11, T["faint"],
            extra="line-height: 1.4;"),
        row(gbtn("Start", "play", size="sm"), gap=0),
        gap=8), "start, never verify")
    s2 = msection("Closing it — only the assigner, and only the whole task", e, f, g, h)
    return board("Tasks: while it runs, and closing it", s1, s2)


TASKS_MOOD = [("TK01-Page.dc.html", "Tasks: the page", tk01),
              ("TK02-Describing.dc.html", "Tasks: describing one", tk02),
              ("TK03-Closing.dc.html", "Tasks: while it runs, and closing it", tk03)]
