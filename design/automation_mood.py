# ================================================================== The Automation & Actions mood board, AU01-AU03
# The user, 26 Sep 2026: "let take another visual pass on the automation and actions, automation uses
# events and actions, and actions categories by control, monitor and custom. do a proper design. note
# that it not programmers using it so it should intuitive visually using ux, not using things like k=".
#
# So nothing on these boards is typed as code: no `k=v`, no ids, no ISO timestamps, no path prefixes.
# A condition is chosen from things that can happen, its details are set with the control that fits
# the detail (a slider for a threshold, day chips for a schedule, a folder tier for a location), and an
# automation always reads back as a sentence: WHEN something happens, WHERE, DO these.
#
# The vocabulary is the Engine's own (engine/control/events.py EVENT_TYPES, actions.py BUILTIN):
# files, USB, programs, sign-ins, network, tasks & flows, time, system thresholds; Control actions
# (notify, lock the session, screenshot, kill/start a program, rename/restore a file, shut down, reboot),
# Monitoring actions (process list, system metrics, file activity, idle time, snapshot a file, USB
# contents), and Custom (an Admin's own script, validated twice, unsandboxed).

AU_CW, AU_CH = 316, 240

CAT = {"control": ("Control", "accent", "play"), "monitoring": ("Monitoring", "ok", "eye"),
       "custom": ("Custom", "warn", "terminal")}


def au_cell(name, html, note="", h=None):
    box = (f'<div style="width: {AU_CW}px; height: {h or AU_CH}px; box-sizing: border-box; border-radius: 12px; '
           f'background: {T["pane"]}; padding: 16px; overflow: hidden; position: relative; display: flex; '
           f'flex-direction: column; gap: 10px;">{html}</div>')
    return col(row(txt(name, 12.5, "#fff", 600), txt(note, 11.5, T["frame_faint"]) if note else "", gap=8), box, gap=6)


def au_slot(text, tone="accent"):
    """A blank in a sentence, filled with a choice -- it looks pressable, and it reads as a word."""
    return (f'<span style="display: inline-flex; align-items: center; gap: 4px; padding: 1px 7px; margin: 0 1px; '
            f'border-radius: 7px; background: {T[tone + "_soft"]}; color: {T[tone]}; font-weight: 600; '
            f'white-space: nowrap;">{text}<svg width="9" height="9" viewBox="0 0 24 24" fill="none" stroke="{T[tone]}" '
            f'stroke-width="2.5" stroke-linecap="round"><path d="M6 9l6 6 6-6"/></svg></span>')


def au_icon(name, tone="accent", size=30):
    return (f'<span style="width: {size}px; height: {size}px; border-radius: {int(size / 3)}px; background: {T[tone + "_soft"]}; '
            f'display: inline-flex; align-items: center; justify-content: center; flex: none;">{ic(name, int(size * 0.52), T[tone])}</span>')


def au_tile(icon, label, tone="accent", sel=False, w=86):
    ring = f"box-shadow: inset 0 0 0 1.5px {T[tone]};" if sel else ""
    return col(au_icon(icon, tone, 26), txt(label, 11, T["ink"] if sel else T["dim"], 600 if sel else 500,
                                           extra="text-align: center; line-height: 1.25;"),
               gap=6, extra=f"width: {w}px; box-sizing: border-box; padding: 9px 4px; border-radius: 10px; "
                            f"background: {T['ground']}; align-items: center; {ring}")


def au_sentence(*parts, size=12.5):
    return txt(" ".join(parts), size, T["dim"], extra="line-height: 2.0;")


def au_line(left, right="", tone=None, lead=""):
    return row(lead, txt(left, 12, T["dim"]), sp(), txt(right, 11.5, tone_c(tone, T["faint"]), 600) if right else "",
               gap=8, extra=f"width: 100%; padding: 6px 0; border-bottom: 1px solid {T['line']};")


def au_slider(pct, left, right, tone="warn"):
    return col(row(txt(left, 11, T["faint"]), sp(), txt(right, 11.5, T[tone], 700), gap=0, extra="width: 100%;"),
               (f'<div style="position: relative; height: 6px; border-radius: 3px; background: {T["line2"]};">'
                f'<div style="width: {pct}%; height: 6px; border-radius: 3px; background: {T[tone]};"></div>'
                f'<span style="position: absolute; left: calc({pct}% - 8px); top: -5px; width: 16px; height: 16px; '
                f'border-radius: 8px; background: #fff;"></span></div>'), gap=9, extra="width: 100%;")


def au_chip(text, on=False, tone="accent"):
    return (f'<span style="display: inline-flex; padding: 4px 9px; border-radius: 8px; font-size: 11px; font-weight: 600; '
            f'font-family: {T["sans"]}; background: {T[tone + "_soft"] if on else T["ground"]}; '
            f'color: {T[tone] if on else T["faint"]};">{text}</span>')


# ------------------------------------------------------------------ AU01: the Automation page, and one automation read
def au01():
    # the shape of the page
    a = au_cell("A list of sentences", col(
        *[col(au_sentence(f"When {au_slot(w, 'accent')}", f"do {au_slot(d, 'ok')}", size=11.5),
              txt(m, 10.5, T["faint"]), gap=0, extra=f"width: 100%; padding: 4px 0; border-bottom: 1px solid {T['line']};")
          for w, d, m in [("a restricted file is opened", "Notify me", "fired 3 times today"),
                          ("the disk is nearly full", "Clear temp", "never fired"),
                          ("it is 18:00 on a weekday", "Lock screens", "fired yesterday")]], gap=2),
        "every automation, said in words")
    b = au_cell("When | then", col(
        *[row(row(au_icon(i1, "accent", 24), txt(w, 11, T["dim"]), gap=7, extra="width: 118px; flex: none;"),
              ic("arrow", 14, T["faint"]),
              row(au_icon(i2, "ok", 24), txt(d, 11, T["dim"]), gap=7), gap=8, extra="width: 100%; padding: 6px 0;")
          for i1, w, i2, d in [("file", "Restricted file opened", "bell", "Notify me"),
                               ("cpu", "Disk nearly full", "play", "Clear temp"),
                               ("clock", "Weekdays 18:00", "lock", "Lock screens")]], gap=0),
        "two columns, joined")
    c = au_cell("By what triggers it", col(
        row(au_icon("file", "accent", 20), txt("Files", 12, T["ink"], 600), sp(), txt("2", 11, T["faint"]), gap=8),
        row(au_icon("clock", "accent", 20), txt("Time", 12, T["ink"], 600), sp(), txt("1", 11, T["faint"]), gap=8),
        row(au_icon("cpu", "accent", 20), txt("The machine", 12, T["ink"], 600), sp(), txt("1", 11, T["faint"]), gap=8),
        row(au_icon("user", "accent", 20), txt("People", 12, T["dim"]), sp(), txt("0", 11, T["faint"]), gap=8),
        row(au_icon("key", "accent", 20), txt("USB drives", 12, T["dim"]), sp(), txt("0", 11, T["faint"]), gap=8),
        gap=9), "grouped, so you find it")
    d = au_cell("Four cells", dp_wire(dp_box(28, 10, 160, 62, label="your automations"),
                                      dp_box(196, 10, 76, 62, label="running now"),
                                      dp_box(28, 80, 76, 58, label="failed"),
                                      dp_box(112, 80, 160, 58, label="fired today")),
                "the Overview's language")
    s1 = msection("The Automation page — what you have set up, and what it did", a, b, c, d)

    # one automation, read at a glance
    e = au_cell("One sentence", col(
        au_sentence(f"When {au_slot('a file is opened')}", f"in {au_slot('Restricted')}",
                    f"on {au_slot('any Operations machine')}", f"do {au_slot('Notify me', 'ok')}",
                    f"then {au_slot('Lock the folder', 'ok')}", size=12.5),
        row(txt("Last fired 11:41, both ran clean", 10.5, T["ok"]), gap=0),
        gap=8), "every blank is a choice")
    f = au_cell("A recipe card", col(
        row(txt("WHEN", 10.5, T["faint"], 700), gap=0),
        row(au_icon("file", "accent", 26), col(txt("A restricted file is opened", 12, T["ink"], 600),
                                               txt("any Operations machine", 10.5, T["faint"]), gap=1), gap=9),
        row(txt("DO, IN ORDER", 10.5, T["faint"], 700), gap=0, extra="padding-top: 4px;"),
        row(au_icon("bell", "ok", 26), txt("Notify me", 12, T["dim"]), gap=9),
        row(au_icon("lock", "ok", 26), txt("Lock the folder", 12, T["dim"]), gap=9),
        gap=7), "blocks you read down")
    g = au_cell("Picture first", col(
        row(au_icon("file", "accent", 44), ic("arrow", 18, T["faint"]), au_icon("bell", "ok", 44),
            ic("arrow", 18, T["faint"]), au_icon("lock", "ok", 44), gap=10, justify="center",
            extra="width: 100%; padding: 14px 0 6px;"),
        row(txt("file opened", 10.5, T["faint"], extra="width: 60px; text-align: center;"), sp(),
            txt("notify", 10.5, T["faint"], extra="width: 60px; text-align: center;"), sp(),
            txt("lock", 10.5, T["faint"], extra="width: 60px; text-align: center;"), gap=0, extra="width: 100%;"),
        txt("Restricted files, any Operations machine", 11, T["dim"], extra="text-align: center;"),
        gap=8), "icons carry it, words confirm")
    h = au_cell("What it did", col(
        row(au_icon("file", "accent", 22), txt("Restricted file opened", 12, T["ink"], 600), gap=8),
        *[row(txt(t, 10.5, T["faint"], mono=True, extra="width: 38px; flex: none;"), txt(w, 11.5, T["dim"]), sp(),
              txt(r, 11, tone_c(tone, T["faint"]), 600), gap=8, extra=f"width: 100%; padding: 5px 0; border-bottom: 1px solid {T['line']};")
          for t, w, r, tone in [("11:41", "OPS-07 · notify, lock", "clean", "ok"),
                                ("10:02", "OPS-03 · notify, lock", "lock timed out", "warn"),
                                ("08:55", "OPS-07 · notify, lock", "clean", "ok")]],
        gap=4), "its record, under it")
    s2 = msection("One automation, read at a glance", e, f, g, h)
    return board("Automation: the page", s1, s2)


# ------------------------------------------------------------------ AU02: making an automation, without code
def au02():
    a = au_cell("Pick what happens", col(
        row(au_tile("file", "A file", sel=True, w=62), au_tile("key", "A USB drive", w=62),
            au_tile("window", "A program", w=62), au_tile("user", "Sign-in", w=62), gap=6),
        row(au_tile("globe", "Network", w=62), au_tile("clock", "A time", w=62),
            au_tile("cpu", "The machine", w=62), au_tile("tasks", "Tasks, flows", w=62), gap=6),
        gap=6), "big targets, one per family")
    b = au_cell("Fill the sentence", col(
        au_sentence(f"When {au_slot('a file')}", f"is {au_slot('opened')}", f"in {au_slot('Restricted')}"),
        (f'<div style="width: 100%; border-radius: 10px; background: {T["ground"]}; padding: 6px; box-sizing: border-box; '
         f'box-shadow: 0 10px 24px rgba(0,0,0,0.45);">'
         + "".join(f'<div style="padding: 6px 8px; border-radius: 7px; font-size: 11.5px; font-family: {T["sans"]}; '
                   f'color: {T["ink"] if on else T["dim"]}; background: {T["select"] if on else "transparent"};">{o}</div>'
                   for o, on in [("created", False), ("changed", False), ("opened", True), ("moved or copied", False),
                                 ("deleted", False)])
         + '</div>'),
        gap=4), "a blank opens its choices")
    c = au_cell("Three steps", col(
        row(*[row(f'<span style="width: 20px; height: 20px; border-radius: 10px; background: {T["accent"] if i == 2 else T["ground"]}; '
                  f'color: {"#0d1018" if i == 2 else T["faint"]}; font-size: 11px; font-weight: 700; display: inline-flex; '
                  f'align-items: center; justify-content: center; font-family: {T["sans"]};">{i}</span>',
                  txt(n, 11.5, T["ink"] if i == 2 else T["faint"], 600 if i == 2 else 400), gap=6)
              for i, n in [(1, "When"), (2, "Where"), (3, "Do")]], gap=16),
        rule(),
        txt("Which machines should watch for it?", 12.5, T["ink"], 600),
        au_line("Every Operations machine", "", lead=au_chip("●", True)),
        au_line("Only some", "", lead=au_chip("○")),
        gap=9), "one question per step")
    d = au_cell("Start from an example", col(
        txt("Common ones", 11, T["faint"], 600),
        *[row(au_icon(i, "accent", 22), txt(n, 11.5, T["dim"]), sp(), ic("plus", 13, T["faint"]), gap=8,
              extra=f"width: 100%; padding: 5px 0; border-bottom: 1px solid {T['line']};")
          for i, n in [("file", "Warn me when a restricted file is opened"), ("key", "Snapshot a USB drive when plugged in"),
                       ("clock", "Lock every screen at 18:00"), ("cpu", "Clear temp when the disk is nearly full")]],
        gap=2), "edit a template, not a blank")
    s1 = msection("Choosing what triggers it", a, b, c, d)

    e = au_cell("A threshold is a slider", col(
        txt("When the processor stays busy", 12.5, T["ink"], 600),
        au_slider(85, "above", "85 %"), au_slider(33, "for at least", "5 minutes", "accent"),
        gap=14), "never 'threshold.cpu, 85'")
    f = au_cell("A time is days and a clock", col(
        txt("Every", 11.5, T["faint"]),
        row(*[au_chip(d, d not in ("Sat", "Sun")) for d in ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]], gap=4),
        row(txt("at", 11.5, T["faint"]),
            f'<span style="padding: 6px 12px; border-radius: 9px; background: {T["ground"]}; font-family: {T["mono"]}; '
            f'font-size: 16px; color: {T["ink"]}; font-weight: 600;">18:00</span>', gap=8),
        txt("Weekdays at six in the evening.", 11, T["dim"]),
        gap=10), "never an ISO timestamp")
    g = au_cell("A place is a tier, or a folder", col(
        txt("Where the file is", 11.5, T["faint"]),
        row(au_chip("Restricted", True, "danger"), au_chip("Admin"), au_chip("Workers"), au_chip("Common"), gap=5),
        txt("or", 10.5, T["faint"]),
        row(ic("folder", 15, T["dim"]), txt("Documents / Finance", 12, T["dim"]), sp(), gbtn("Browse", size="sm"),
            gap=8, extra=f"width: 100%; padding: 6px 9px; border-radius: 9px; background: {T['ground']}; box-sizing: border-box;"),
        gap=8), "never 'path_prefix='")
    h = au_cell("Machines are picked, not typed", col(
        txt("Which machines", 11.5, T["faint"]),
        row(*[f'<span style="width: 30px; height: 30px; border-radius: 9px; display: inline-flex; align-items: center; '
              f'justify-content: center; font-family: {T["mono"]}; font-size: 10.5px; font-weight: 600; '
              f'background: {T["accent_soft"] if on else T["ground"]}; color: {T["accent"] if on else T["faint"]}; '
              f'{"box-shadow: inset 0 0 0 1.5px " + T["accent"] + ";" if on else ""}">{n}</span>'
              for n, on in [("01", True), ("02", False), ("03", True), ("04", False), ("05", False), ("06", True),
                            ("07", True)]], gap=5),
        txt("4 of 7 machines · click to add or remove", 10.5, T["faint"]),
        row(gbtn("All of them", size="sm"), gbtn("None", size="sm"), gap=4),
        gap=9), "never 'pc ids 1,2'")
    s2 = msection("Saying the details — the control that fits, never typed code", e, f, g, h)
    return board("Automation: making one", s1, s2)


# ------------------------------------------------------------------ AU03: the Actions library, and setting one up
def au03():
    lib = {"control": [("bell", "Notify"), ("lock", "Lock the screen"), ("camera", "Screenshot"), ("stop", "Close a program"),
                       ("play", "Start a program"), ("file", "Rename a file"), ("power", "Restart")],
           "monitoring": [("cpu", "System load"), ("window", "Programs running"), ("filewatch", "File activity"),
                          ("clock", "Idle time"), ("file", "Snapshot a file"), ("key", "USB contents")],
           "custom": [("terminal", "Clear temp"), ("terminal", "Archive quarter")]}

    a = au_cell("Three shelves", col(
        *[col(row(txt(CAT[k][0], 11.5, T[CAT[k][1]], 700), sp(), txt(str(len(lib[k])), 10.5, T["faint"]), gap=0),
              row(*[au_icon(i, CAT[k][1], 28) for i, _ in lib[k][:6]], gap=6), gap=6)
          for k in ("control", "monitoring", "custom")], gap=12), "the three categories, icons only")
    b = au_cell("Grouped, with what it does", col(
        txt("CONTROL", 10.5, T["accent"], 700),
        au_line("Notify", "shows a message", lead=au_icon("bell", "accent", 20)),
        au_line("Lock the screen", "for a set time", lead=au_icon("lock", "accent", 20)),
        txt("MONITORING", 10.5, T["ok"], 700, extra="padding-top: 4px;"),
        au_line("System load", "reports CPU, memory", lead=au_icon("cpu", "ok", 20)),
        txt("CUSTOM", 10.5, T["warn"], 700, extra="padding-top: 4px;"),
        au_line("Clear temp", "your script", lead=au_icon("terminal", "warn", 20)),
        gap=2), "a one-line promise each")
    c = au_cell("Tiles", col(
        row(au_tile("bell", "Notify", w=64), au_tile("lock", "Lock screen", w=64), au_tile("camera", "Screenshot", w=64),
            au_tile("stop", "Close program", w=64), gap=6),
        row(au_tile("cpu", "System load", "ok", w=64), au_tile("filewatch", "File activity", "ok", w=64),
            au_tile("terminal", "Clear temp", "warn", w=64), au_tile("plus", "New", "warn", w=64), gap=6),
        gap=6), "colour says the category")
    d = au_cell("With how it last went", col(
        *[row(au_icon(i, CAT[k][1], 22), col(txt(n, 12, T["ink"], 500), txt(u, 10.5, T["faint"]), gap=1), sp(),
              txt(r, 11, tone_c(t, T["faint"]), 600), gap=8, extra=f"width: 100%; padding: 5px 0; border-bottom: 1px solid {T['line']};")
          for i, k, n, u, r, t in [("bell", "control", "Notify", "in 3 automations", "clean", "ok"),
                                   ("lock", "control", "Lock the screen", "in 1 automation", "timed out", "warn"),
                                   ("terminal", "custom", "Clear temp", "not used yet", "never run", None)]],
        gap=2), "is it used, does it work")
    s1 = msection("The library — Control, Monitoring, Custom", a, b, c, d)

    e = au_cell("Its settings, in words", col(
        row(au_icon("lock", "accent", 26), txt("Lock the screen", 13, T["ink"], 600), gap=9),
        au_slider(25, "for", "15 minutes", "accent"),
        col(txt("Message they see", 11, T["faint"]),
            (f'<div style="padding: 7px 10px; border-radius: 9px; background: {T["ground"]}; font-size: 11.5px; '
             f'color: {T["dim"]}; font-family: {T["sans"]};">Locked by your Admin for maintenance.</div>'), gap=5),
        gap=12), "never 'duration_s=900'")
    f = au_cell("When it runs", col(
        *[row(au_chip("●" if on else "○", on), col(txt(n, 12, T["ink"] if on else T["dim"], 600 if on else 400),
                                                  txt(s_, 10.5, T["faint"]), gap=1), gap=9, extra="padding: 4px 0;")
          for n, s_, on in [("Right away", "as soon as it is triggered", False),
                            ("After a wait", "e.g. 5 minutes later", True),
                            ("On a schedule", "hourly, daily, weekly", False)]],
        row(txt("Wait", 11, T["faint"]), au_chip("1 min"), au_chip("5 min", True), au_chip("15 min"), au_chip("1 hour"), gap=5),
        gap=6), "timing as three plain choices")
    g = au_cell("A custom action", col(
        row(au_icon("terminal", "warn", 26), txt("Your own script", 13, T["ink"], 600), gap=9),
        (f'<div style="width: 100%; height: 62px; box-sizing: border-box; border-radius: 10px; border: 1.5px dashed {T["line2"]}; '
         f'display: flex; align-items: center; justify-content: center; gap: 8px; color: {T["dim"]}; font-size: 11.5px; '
         f'font-family: {T["sans"]};">{ic("file", 15, T["dim"])}clear_temp.ps1</div>'),
        row(ic("check", 13, T["ok"]), txt("Checked: uses only allowed parts of Windows", 11, T["ok"]), gap=6),
        txt("It runs unprotected on the machine. Only add scripts you trust.", 10.5, T["warn"],
            extra="line-height: 1.4;"),
        gap=8), "a file, not code")
    h = au_cell("Try it on one machine", col(
        row(au_icon("bell", "accent", 26), txt("Notify", 13, T["ink"], 600), gap=9),
        row(txt("on", 11.5, T["faint"]),
            (f'<span style="padding: 5px 10px; border-radius: 8px; background: {T["ground"]}; font-family: {T["mono"]}; '
             f'font-size: 11.5px; color: {T["ink"]};">OPS-07 ▾</span>'), tbtn("Run now", "accent", "play", "sm"), gap=8),
        rule(),
        row(ic("check", 13, T["ok"]), txt("Delivered to OPS-07 in 2 s", 11.5, T["ok"], 600), gap=6),
        txt("Ama saw it at 14:21.", 10.5, T["faint"]),
        gap=9), "see it work before you rely on it")
    s2 = msection("Setting an action up — plain settings, never code", e, f, g, h)
    return board("Actions: the library", s1, s2)


AUTOMATION_MOOD = [("AU01-Automation.dc.html", "Automation: the page", au01),
                   ("AU02-Making.dc.html", "Automation: making one", au02),
                   ("AU03-Actions.dc.html", "Actions: the library", au03)]
