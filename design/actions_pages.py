# ================================================================== AU05-AU10: Actions, and making an automation, from the picks
# The picks off AU02 and AU03 (DECISIONS.md 3a), composed into pages:
#
#   AU05  the Actions page             AU03 "Grouped, with what it does" + "When it runs" + "Try it on one machine"
#   AU06  each action asks for what    the user: "each action can have it specify needs so it visuals or
#         it needs                     designs are not necessarily standard" -- one settings panel per action
#   AU07  a custom action              AU03 "A custom action" + "When it runs" + "Try it on one machine"
#   AU08  making an automation: When   AU02 "Three steps" + "Fill the sentence" + "Start from an example"
#   AU09  making an automation: Where  AU02 "A place is a tier, or a folder" + "Machines are picked" +
#                                      "A time is days and a clock"
#   AU10  making an automation: Do     the library again, "Grouped, with what it does", read back as a sentence
#
# The threshold slider was not picked -- "I don't have an issue with the slider, just the design". So it
# is REDRAWN (au_meter): the level is set against what is normal for these machines, not on a bare track.

LIBRARY = {
    "control": [("bell", "Notify", "shows a message on their screen"),
                ("lock", "Lock the screen", "for a set time, with a message"),
                ("camera", "Screenshot", "a still of their screen, now"),
                ("stop", "Close a program", "ends it, unsaved work is lost"),
                ("play", "Start a program", "opens one that is installed"),
                ("file", "Rename a file", "gives a file a new name"),
                ("power", "Restart", "the whole machine, after a warning")],
    "monitoring": [("cpu", "System load", "processor and memory, now"),
                   ("window", "Programs running", "what is open, and for how long"),
                   ("filewatch", "File activity", "what changed in a folder"),
                   ("clock", "Idle time", "how long since they touched it"),
                   ("file", "Snapshot a file", "keeps a copy as it is now"),
                   ("key", "USB contents", "what is on a plugged-in drive")],
    "custom": [("terminal", "Clear temp", "your script · PowerShell"),
               ("terminal", "Archive quarter", "your script · Python")],
}


def au_meter(value, normal=(20, 40), unit="%", label="The processor, across these machines", w=600):
    """A level, set against what is NORMAL. The bar runs calm -> careful -> alarming; the band these
    machines usually sit in is drawn on it, so '85 %' means something the moment it is chosen. The
    handle carries its own value; the duration is chips, not a second track."""
    lo, hi = normal
    bar = (f'<div style="position: relative; width: {w}px; height: 58px;">'
           # the value, on the handle
           f'<span style="position: absolute; left: calc({value}% - 26px); top: 0; width: 52px; text-align: center; '
           f'font-family: {T["mono"]}; font-size: 14px; font-weight: 700; color: {T["warn"]};">{value} {unit}</span>'
           # the track: calm, careful, alarming
           f'<div style="position: absolute; left: 0; right: 0; top: 26px; height: 12px; border-radius: 6px; '
           f'background: linear-gradient(90deg, {T["ok_soft"]} 0%, {T["ok_soft"]} 55%, {T["warn_soft"]} 70%, {T["danger_soft"]} 100%);"></div>'
           # what is normal
           f'<div style="position: absolute; left: {lo}%; width: {hi - lo}%; top: 26px; height: 12px; border-radius: 6px; '
           f'background: {T["ok"]}; opacity: 0.55;"></div>'
           # beyond the chosen level: what would fire
           f'<div style="position: absolute; left: {value}%; right: 0; top: 26px; height: 12px; border-radius: 0 6px 6px 0; '
           f'background: repeating-linear-gradient(135deg, {T["warn"]} 0 4px, transparent 4px 8px); opacity: 0.55;"></div>'
           # the handle
           f'<span style="position: absolute; left: calc({value}% - 3px); top: 20px; width: 6px; height: 24px; '
           f'border-radius: 3px; background: #fff; box-shadow: 0 0 0 3px rgba(0,0,0,0.35);"></span>'
           f'<span style="position: absolute; left: 0; top: 44px; font-family: {T["mono"]}; font-size: 10.5px; color: {T["faint"]};">0</span>'
           f'<span style="position: absolute; left: calc({lo}% ); top: 44px; font-family: {T["sans"]}; font-size: 10.5px; color: {T["ok"]};">usually {lo}-{hi} {unit}</span>'
           f'<span style="position: absolute; right: 0; top: 44px; font-family: {T["mono"]}; font-size: 10.5px; color: {T["faint"]};">100</span>'
           f'</div>')
    return col(txt(label, 12, T["faint"]), bar,
               row(txt("and stays there for", 12, T["faint"]), *[au_chip(x, x == "5 min", "warn") for x in ["1 min", "5 min", "15 min", "1 hour"]],
                   gap=6),
               txt("It fires only above the line, the striped part: well clear of a normal day.", 11.5, T["dim"]),
               gap=10, extra=f"width: {w}px;")


def lib_row(icon, name, promise, tone, sel=False, check=None):
    fill = (f"background: {T['select']}; border-radius: 10px; padding: 5px 10px; margin: 0 -10px;"
            if sel else f"padding: 5px 0; border-bottom: 1px solid {T['line']};")
    box = ""
    if check is not None:
        box = (f'<span style="width: 18px; height: 18px; border-radius: 6px; flex: none; display: inline-flex; '
               f'align-items: center; justify-content: center; background: {T["accent"] if check else T["ground"]}; '
               f'box-shadow: inset 0 0 0 1px {T["line2"]};">{ic("check", 11, "#0d1018", 2.6) if check else ""}</span>')
    return row(box, au_icon(icon, tone, 24), txt(name, 12.5, "#fff" if sel else T["ink"], 600 if sel else 500), sp(),
               txt(promise, 11.5, T["select_sub"] if sel else T["faint"]), gap=10, extra=f"width: 100%; {fill}")


def library(w, selected=None, checks=None, compact=False):
    out = []
    for k in ("control", "monitoring", "custom"):
        label, tone, _ = CAT[k]
        out.append(row(txt(label.upper(), 11, T[tone], 700), sp(), txt(str(len(LIBRARY[k])), 11, T["faint"]), gap=0,
                       extra="width: 100%; padding-top: 8px;"))
        items = LIBRARY[k][:4] if compact else LIBRARY[k]
        for icon, name, promise in items:
            out.append(lib_row(icon, name, promise, tone, sel=(name == selected),
                               check=(None if checks is None else name in checks)))
        if compact and len(LIBRARY[k]) > 4:
            out.append(txt(f"+ {len(LIBRARY[k]) - 4} more", 11, T["faint"], extra="padding: 5px 0;"))
    return col(*out, gap=0, extra=f"width: {w}px;")


def when_it_runs(w, pick="now", wait="5 min"):
    opts = [("now", "Right away", "as soon as it is started"), ("wait", "After a wait", "then it runs once"),
            ("sched", "On a schedule", "every day, or on the days you pick")]
    rows_ = [row(au_chip("●" if k == pick else "○", k == pick),
                 col(txt(n, 12.5, T["ink"] if k == pick else T["dim"], 600 if k == pick else 400),
                     txt(s_, 11, T["faint"]), gap=1), gap=10, extra="padding: 5px 0;") for k, n, s_ in opts]
    extra = ""
    if pick == "wait":
        extra = row(txt("Wait", 11.5, T["faint"]), *[au_chip(x, x == wait) for x in ["1 min", "5 min", "15 min", "1 hour"]], gap=5,
                    extra="padding-left: 34px;")
    give_up = row(txt("Give up after", 11.5, T["faint"]), *[au_chip(x, x == "1 min") for x in ["30 s", "1 min", "5 min"]],
                  gap=5, extra="padding-top: 8px;")
    return col(*rows_, extra, rule(), give_up,
               txt("Giving up is reported as timed out, not as failed.", 11, T["faint"]), gap=6, extra=f"width: {w}px;")


def try_it(w, name="Lock the screen", result=("Locked OPS-07 for 15 minutes", "Ama saw the message at 14:21.")):
    return col(txt("See it work before an automation relies on it.", 12, T["dim"]),
               row(txt("On", 12, T["faint"]),
                   row(txt("OPS-07", 12, T["ink"], 600, mono=True), txt("Ama", 11.5, T["faint"]), ic("chevd", 12, T["faint"]),
                       gap=7, extra=f"padding: 6px 10px; border-radius: 9px; background: {T['pane']};"), gap=8),
               row(tbtn(f"Run {name.lower()} now", "accent", "play", "sm"), gap=0),
               rule(),
               row(ic("check", 14, T["ok"]), txt(result[0], 12.5, T["ok"], 600), gap=7),
               txt(result[1], 11.5, T["faint"]),
               gap=10, extra=f"width: {w}px;")


# ------------------------------------------------------------------ AU05: the Actions page
# SIGNATURE: A LIBRARY AND A WORKBENCH. The library down the left, grouped with what each does; the
# chosen action on the right, its own settings on top, when it runs and a trial run beneath.
def au05():
    settings = col(
        row(au_icon("lock", "accent", 34), col(txt("Lock the screen", 16, T["ink"], 600),
                                               txt("Control · used in 1 automation", 11.5, T["faint"]), gap=2), sp(),
            gbtn("Archive", size="sm"), gap=11, extra="width: 100%;"),
        au_slider(25, "Lock it for", "15 minutes", "accent"),
        col(txt("The message they see", 11.5, T["faint"]),
            (f'<div style="padding: 9px 12px; border-radius: 9px; background: {T["pane"]}; font-size: 12.5px; '
             f'color: {T["ink"]}; font-family: {T["sans"]};">Locked by your Admin for maintenance.</div>'), gap=6),
        gap=16, extra="width: 676px;")
    return work_page(
        "Actions", "actions", ["Actions"], "Actions", "fifteen in the library", "dim",
        [row(kcell("The library", "grouped, with what each does", "dim", library(576, selected="Lock the screen"),
                   w=620, h=676, top=True),
             col(kcell("Its settings", "only what this action needs", "accent", settings, w=720, h=316, top=True),
                 row(kcell("When it runs", "right away", "dim", when_it_runs(306), w=350, h=340, top=True),
                     kcell("Try it on one machine", "last tried 14:21", "ok", try_it(306), w=350, h=340, top=True),
                     gap=20, extra="flex: none;"),
                 gap=20, extra="flex: none;"),
             gap=20, align="stretch", extra="flex: none;")],
        "AU05 · Grouped, with what it does (AU03) down the left. The chosen action asks only for what it needs "
        "(AU06), then When it runs and Try it on one machine (AU03). Nothing typed as code.",
        eyebrow("PAGE", "Actions — an Admin's", "a library and a workbench"))


# ------------------------------------------------------------------ AU06: each action asks for what it needs
# A reference, not a choice: the settings panel of eight actions side by side, each drawn with the
# control its need calls for. "Its settings" on AU05 is whichever of these the chosen action is.
def au06():
    def head(icon, name, tone="accent"):
        return row(au_icon(icon, tone, 26), txt(name, 13, T["ink"], 600), gap=9)

    def box(text, faint=False):
        return (f'<div style="padding: 7px 10px; border-radius: 8px; background: {T["ground"]}; font-size: 11.5px; '
                f'color: {T["faint"] if faint else T["ink"]}; font-family: {T["sans"]};">{text}</div>')

    def pick(text, sub=""):
        return row(txt(text, 12, T["ink"], 600), txt(sub, 10.5, T["faint"]) if sub else "", sp(),
                   ic("chevd", 12, T["faint"]), gap=7,
                   extra=f"width: 100%; padding: 7px 10px; border-radius: 8px; background: {T['ground']}; box-sizing: border-box;")

    a = au_cell("Notify", col(head("bell", "Notify"), txt("What it says", 11, T["faint"]),
                              box("Please save your work; the network restarts at 18:00."),
                              row(txt("Stays up", 11, T["faint"]), au_chip("until closed", True), au_chip("10 s"), gap=5),
                              gap=8), "a message, and how long")
    b = au_cell("Lock the screen", col(head("lock", "Lock the screen"), au_slider(25, "for", "15 minutes", "accent"),
                                       txt("Message", 11, T["faint"]), box("Locked by your Admin for maintenance."),
                                       gap=9), "how long, and why")
    c = au_cell("Rename a file", col(head("file", "Rename a file"), txt("Which file", 11, T["faint"]),
                                     pick("budget-2026.xlsx", "found on 2 machines"), txt("New name", 11, T["faint"]),
                                     box("budget-2026 (locked).xlsx"), gap=7), "a file from the index, a name")
    d = au_cell("Close a program", col(head("stop", "Close a program"), txt("Which program", 11, T["faint"]),
                                       pick("Excel", "open on 5 machines"),
                                       row(ic("warn", 13, T["warn"]), txt("Unsaved work in it is lost.", 11.5, T["warn"]), gap=6),
                                       gap=8), "picked from what runs")
    s1 = msection("Control — the control follows the need", a, b, c, d)

    e = au_cell("Start a program", col(head("play", "Start a program"), txt("Which program", 11, T["faint"]),
                                       pick("Calculator", "installed on every machine"),
                                       txt("Only programs installed on that machine are offered.", 11, T["faint"],
                                           extra="line-height: 1.4;"), gap=8), "picked from what is installed")
    f = au_cell("Restart", col(head("power", "Restart"),
                               row(txt("Warn them first", 11.5, T["faint"]), au_chip("1 min"), au_chip("5 min", True), gap=5),
                               row(ic("warn", 13, T["danger"]), txt("Everyone on the machine loses unsaved work.", 11.5, T["danger"]),
                                   gap=6), gap=10), "a warning, stated plainly")
    g = au_cell("Snapshot a file", col(head("file", "Snapshot a file", "ok"), txt("Which file", 11, T["faint"]),
                                       pick("payroll.xlsx", "OPS-03"),
                                       txt("A copy as it is right now, kept for the record.", 11, T["faint"]), gap=8),
                "monitoring: a file")
    h = au_cell("Screenshot", col(head("camera", "Screenshot"),
                                  txt("Nothing to set.", 13, T["dim"], 600),
                                  txt("It takes a still of their screen, now. The only question is when it runs.", 11.5,
                                      T["faint"], extra="line-height: 1.45;"), gap=10), "some ask for nothing")
    s2 = msection("More control, and monitoring — and the ones that need nothing", e, f, g, h)
    return board("Actions: each asks for what it needs", s1, s2)


# ------------------------------------------------------------------ AU07: a custom action
# SIGNATURE: THE SAME WORKBENCH, with the script where the library was -- a custom action is made, not
# chosen. The file is dropped, the check speaks in words, and it is tried before anything relies on it.
def au07():
    script = col(
        (f'<div style="width: 100%; height: 190px; box-sizing: border-box; border-radius: 14px; '
         f'border: 1.5px dashed {T["line2"]}; display: flex; flex-direction: column; align-items: center; '
         f'justify-content: center; gap: 10px; font-family: {T["sans"]};">'
         f'{au_icon("terminal", "warn", 44)}'
         f'<span style="font-size: 14px; color: {T["ink"]}; font-weight: 600;">clear_temp.ps1</span>'
         f'<span style="font-size: 11.5px; color: {T["faint"]};">PowerShell · 40 lines · drop another to replace it</span></div>'),
        txt("Checked before it is saved", 11.5, T["faint"], 600),
        row(ic("check", 14, T["ok"]), txt("Uses only parts of Windows that are allowed", 12.5, T["ok"]), gap=8),
        row(ic("check", 14, T["ok"]), txt("Reads cleanly; nothing in it is broken", 12.5, T["ok"]), gap=8),
        row(ic("check", 14, T["ok"]), txt("Checked again on each machine when it arrives", 12.5, T["dim"]), gap=8),
        (f'<div style="padding: 11px 13px; border-radius: 10px; background: {T["warn_soft"]}; font-size: 12px; '
         f'line-height: 1.45; color: {T["warn"]}; font-family: {T["sans"]};">It runs on the machine with no fence '
         f'around it. Only add scripts you trust, and try it on one machine first.</div>'),
        gap=11, extra="width: 576px;")
    about = col(
        txt("Name", 11.5, T["faint"]),
        (f'<div style="padding: 9px 12px; border-radius: 9px; background: {T["pane"]}; font-size: 13px; '
         f'color: {T["ink"]}; font-family: {T["sans"]};">Clear temp</div>'),
        txt("What it does, in a line", 11.5, T["faint"]),
        (f'<div style="padding: 9px 12px; border-radius: 9px; background: {T["pane"]}; font-size: 13px; '
         f'color: {T["ink"]}; font-family: {T["sans"]};">Empties the temp folders to free disk space.</div>'),
        row(txt("It goes in", 11.5, T["faint"]), tk_tag("Custom", "warn"), gap=8),
        gap=8, extra="width: 676px;")
    return work_page(
        "Actions — a custom action", "actions", ["Actions", "New custom action"], "New custom action",
        "your own script", "warn",
        [row(kcell("Your script", "checked, passed", "ok", script, w=620, h=676, top=True),
             col(kcell("About it", "how it shows in the library", "dim", about, w=720, h=316, top=True),
                 row(kcell("When it runs", "right away", "dim", when_it_runs(306), w=350, h=340, top=True),
                     kcell("Try it on one machine", "not tried yet", "warn",
                           try_it(306, "Clear temp", ("Freed 1.2 GB on OPS-07", "Ran in 4 s, clean.")), w=350, h=340, top=True),
                     gap=20, extra="flex: none;"),
                 gap=20, extra="flex: none;"),
             gap=20, align="stretch", extra="flex: none;")],
        "AU07 · A custom action (AU03): a file dropped, never code typed into a box; the check said in words; "
        "then When it runs and Try it on one machine, as for every action.",
        eyebrow("PAGE", "Actions — a custom one", "the workbench, with the script in place of the library"))


# ------------------------------------------------------------------ making an automation: the three steps
def steps(now):
    names = [(1, "When", "what happens"), (2, "Where", "which machines, which files"), (3, "Do", "which actions")]
    out = []
    for n, name, sub in names:
        state = "now" if n == now else "done" if n < now else "next"
        disc = (f'<span style="width: 26px; height: 26px; border-radius: 13px; display: inline-flex; align-items: center; '
                f'justify-content: center; font-family: {T["sans"]}; font-size: 12px; font-weight: 700; '
                f'background: {T["accent"] if state == "now" else T["ok_soft"] if state == "done" else "rgba(255,255,255,0.08)"}; '
                f'color: {"#0d1018" if state == "now" else T["ok"] if state == "done" else T["frame_faint"]};">'
                f'{ic("check", 13, T["ok"], 2.4) if state == "done" else n}</span>')
        out.append(row(disc, col(txt(name, 13.5, "#fff" if state != "next" else T["frame_faint"], 600),
                                 txt(sub, 11.5, T["frame_faint"]), gap=0), gap=10))
        if n < 3:
            out.append(f'<span style="width: 60px; height: 1px; background: rgba(255,255,255,0.18);"></span>')
    return row(*out, gap=16, extra="flex: none;")


def so_far(parts):
    return col(txt("It reads", 11.5, T["faint"], 600), au_sentence(*parts, size=15), gap=6)


# ------------------------------------------------------------------ AU08: step 1, When
def au08():
    fill = col(
        au_sentence(f"When {au_slot('a file')}", f"is {au_slot('opened')}", size=17),
        (f'<div style="width: 330px; margin-left: 138px; border-radius: 12px; background: {T["pane"]}; padding: 7px; '
         f'box-sizing: border-box; box-shadow: 0 14px 30px rgba(0,0,0,0.5);">'
         + "".join(f'<div style="padding: 8px 10px; border-radius: 8px; font-size: 13px; font-family: {T["sans"]}; '
                   f'color: {T["ink"] if on else T["dim"]}; background: {T["select"] if on else "transparent"};">{o}</div>'
                   for o, on in [("is created", False), ("is changed", False), ("is opened", True),
                                 ("is moved or copied", False), ("is deleted", False)])
         + '</div>'),
        rule(),
        txt("A file · a USB drive · a program · someone signing in · the network · a time · the machine itself · "
            "a task or a flow", 12, T["faint"], extra="line-height: 1.5;"),
        txt("The first blank chooses what kind of thing happens; the rest follow from it.", 11.5, T["faint"]),
        sp(),
        row(gbtn("Cancel"), sp(), tbtn("Next: where", "accent", "fwd"), gap=8, extra="width: 100%;"),
        gap=14, extra="width: 856px; height: 100%;")
    examples = col(
        txt("Or start from one of these, and change what you need.", 12, T["dim"], extra="line-height: 1.4;"),
        *[row(au_icon(i, "accent", 26), col(txt(n, 12.5, T["ink"], 500), txt(s_, 11, T["faint"]), gap=1), sp(),
              ic("plus", 14, T["faint"]), gap=10, extra=f"width: 100%; padding: 9px 0; border-bottom: 1px solid {T['line']};")
          for i, n, s_ in [("file", "Warn me when a restricted file is opened", "files"),
                           ("key", "Snapshot a USB drive when it is plugged in", "USB drives"),
                           ("clock", "Lock every screen at 18:00 on weekdays", "a time"),
                           ("user", "Tell me when someone signs in after 20:00", "people"),
                           ("cpu", "Clear temp when the disk is nearly full", "the machine"),
                           ("tasks", "Notify me when a task's final deadline passes", "tasks")]],
        gap=0, extra="width: 396px;")
    return work_page(
        "Automation — new, step 1", "automation", ["Automation", "New automation"], "New automation",
        "step 1 of 3", "accent",
        [steps(1),
         row(kcell("When", "fill the sentence", "accent", fill, w=900, h=610, top=True),
             kcell("Start from an example", "six common ones", "dim", examples, w=440, h=610, top=True),
             gap=20, align="stretch", extra="flex: none;")],
        "AU08 · Three steps (AU02); the first is Fill the sentence, and every blank opens its own choices. "
        "Start from an example (AU02) sits beside it: a template to edit, never a blank page.",
        eyebrow("PAGE", "Automation — making one, step 1", "a sentence and its examples"))


# ------------------------------------------------------------------ AU09: step 2, Where
def au09():
    place = col(
        txt("Where the file is", 12, T["faint"]),
        row(au_chip("Restricted", True, "danger"), au_chip("Admin"), au_chip("Workers"), au_chip("Common"), gap=6),
        txt("or a folder", 11.5, T["faint"]),
        row(ic("folder", 16, T["dim"]), txt("Documents / Finance", 13, T["dim"]), sp(), gbtn("Browse", size="sm"),
            gap=9, extra=f"width: 100%; padding: 8px 11px; border-radius: 10px; background: {T['pane']}; box-sizing: border-box;"),
        gap=10, extra="width: 616px;")
    slots = [("01", True), ("02", False), ("03", True), ("04", False), ("05", False), ("06", True), ("07", True)]
    machines = col(
        row(*[col(f'<span style="width: 52px; height: 52px; border-radius: 14px; display: inline-flex; align-items: center; '
                  f'justify-content: center; font-family: {T["mono"]}; font-size: 13px; font-weight: 600; '
                  f'background: {T["accent_soft"] if on else T["pane"]}; color: {T["accent"] if on else T["faint"]}; '
                  f'{"box-shadow: inset 0 0 0 2px " + T["accent"] + ";" if on else ""}">{n}</span>',
                  txt(who, 10.5, T["faint"], extra="text-align: center;"), gap=4, extra="align-items: center;")
              for (n, on), who in zip(slots, ["Kojo", "Efua", "Yaw", "Adjoa", "Nana", "Kwame", "Ama"])], gap=10),
        txt("4 of 7 machines. Click one to add or take it away.", 12, T["dim"]),
        row(gbtn("Every machine here", size="sm"), gbtn("None", size="sm"), gap=4),
        gap=12, extra="width: 616px;")
    right_now = col(
        so_far([f"When {au_slot('a file')}", f"is {au_slot('opened')}", f"in {au_slot('Restricted', 'danger')}",
                f"on {au_slot('4 machines')}"]),
        sp(),
        row(gbtn("Back"), sp(), tbtn("Next: do", "accent", "fwd"), gap=8, extra="width: 100%;"),
        gap=10, extra="width: 636px; height: 100%;")
    time_ = col(
        txt("If the trigger were a time, this step asks this instead", 11.5, T["faint"], 600),
        row(*[au_chip(d, d not in ("Sat", "Sun")) for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]], gap=5),
        row(txt("at", 12, T["faint"]),
            f'<span style="padding: 7px 14px; border-radius: 10px; background: {T["pane"]}; font-family: {T["mono"]}; '
            f'font-size: 18px; color: {T["ink"]}; font-weight: 600;">18:00</span>', gap=9),
        rule(),
        row(txt("REDRAWN", 10.5, T["warn"], 700), txt("a level, for the machine's own triggers", 11.5, T["faint"]), gap=8),
        au_meter(85, w=600),
        gap=10, extra="width: 636px;")
    return work_page(
        "Automation — new, step 2", "automation", ["Automation", "New automation"], "New automation",
        "step 2 of 3", "accent",
        [steps(2),
         row(col(kcell("Where the file is", "a tier, or a folder", "danger", place, w=660, h=250, top=True),
                 kcell("Which machines", "picked, never typed", "accent", machines, w=660, h=340, top=True),
                 gap=20, extra="flex: none;"),
             col(kcell("So far", "", "dim", right_now, w=680, h=190, top=True),
                 kcell("Other kinds of trigger", "", "dim", time_, w=680, h=400, top=True),
                 gap=20, extra="flex: none;"),
             gap=20, align="stretch", extra="flex: none;")],
        "AU09 · A place is a tier, or a folder; Machines are picked; A time is days and a clock (AU02). The level, "
        "bottom right, is the slider REDRAWN: set against what is normal, the part that would fire striped.",
        eyebrow("PAGE", "Automation — making one, step 2", "the details, each with its own control"))


# ------------------------------------------------------------------ AU10: step 3, Do
def au10():
    chosen = col(
        *[row(txt(str(n), 13, T["faint"], 600, mono=True), au_icon(i, "ok", 30),
              col(txt(nm, 13, T["ink"], 600), txt(s_, 11.5, T["faint"]), gap=1), sp(),
              gbtn("Settings", size="sm"), ic("x", 13, T["faint"]), gap=11,
              extra=f"width: 100%; padding: 9px 0; border-bottom: 1px solid {T['line']};")
          for n, i, nm, s_ in [(1, "bell", "Notify me", "right away"),
                               (2, "lock", "Lock the screen", "right away · gives up after 1 min")]],
        txt("They run in this order, each on its own. One failing does not stop the next.", 11.5, T["faint"],
            extra="padding-top: 4px;"),
        gap=0, extra="width: 676px;")
    reads = col(
        so_far([f"When {au_slot('a file')}", f"is {au_slot('opened')}", f"in {au_slot('Restricted', 'danger')}",
                f"on {au_slot('4 machines')}", f"do {au_slot('Notify me', 'ok')}", f"then {au_slot('Lock the screen', 'ok')}"]),
        sp(),
        row(gbtn("Back"), sp(), gbtn("Save, switched off"), tbtn("Save and switch on", "accent", "check"), gap=8,
            extra="width: 100%;"),
        gap=10, extra="width: 676px; height: 100%;")
    return work_page(
        "Automation — new, step 3", "automation", ["Automation", "New automation"], "New automation",
        "step 3 of 3", "accent",
        [steps(3),
         row(kcell("Pick what it does", "grouped, with what each does", "dim",
                   library(576, checks={"Notify", "Lock the screen"}, compact=True), w=620, h=610, top=True),
             col(kcell("In order", "two actions", "ok", chosen, w=720, h=250, top=True),
                 kcell("It reads", "the whole automation", "accent", reads, w=720, h=340, top=True),
                 gap=20, extra="flex: none;"),
             gap=20, align="stretch", extra="flex: none;")],
        "AU10 · The library again, Grouped with what it does (AU03), ticked instead of opened. The chosen actions "
        "keep their order; the whole automation reads back as one sentence before it is saved.",
        eyebrow("PAGE", "Automation — making one, step 3", "the library, ticked"))


ACTIONS_PAGES = [("AU05-Actions.dc.html", "Actions: the page, from the picks", au05),
                 ("AU06-Needs.dc.html", "Actions: each asks for what it needs", au06),
                 ("AU07-Custom.dc.html", "Actions: a custom action", au07),
                 ("AU08-When.dc.html", "Automation: making one, step 1", au08),
                 ("AU09-Where.dc.html", "Automation: making one, step 2", au09),
                 ("AU10-Do.dc.html", "Automation: making one, step 3", au10)]
