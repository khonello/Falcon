# ================================================================== v7: Control, Events, Monitoring, Actions
# The docs (admin-reference §8) name four things: Events, Control, Monitoring, Custom, plus a Dashboard.
# Three pages carry them: Automation (an event and the actions attached to it), Actions (the library of
# Control / Monitoring / Custom, each enabled, run once, scheduled or attached) and Live (what is running).

NAV = [("home", "Hierarchy"), ("tasks", "Tasks"), ("flows", "Flows"), ("automation", "Automation"),
       ("play", "Actions"), ("assistance", "Assistance"), ("reports", "Reports")]


def switch(on=True):
    knob_x = "calc(100% - 15px)" if on else "3px"
    bg = T["accent"] if on else T["line2"]
    return (f'<span role="switch" aria-checked="{"true" if on else "false"}" style="position: relative; width: 34px; height: 20px; border-radius: 10px; background: {bg}; display: inline-block; flex: none;">'
            f'<span style="position: absolute; top: 3px; left: {knob_x}; width: 14px; height: 14px; border-radius: 7px; background: #fff;"></span></span>')


def kind_icon(kind):
    return {"Control": ("automation", T["dim"]), "Monitoring": ("camera", T["dim"]), "Custom": ("file", T["dim"]), "Event": ("automation", T["warn"])}[kind]


def act_row(kind, name, sub, on=True, sel=False, right=None):
    i, c = kind_icon(kind)
    return crow(ic(i, 16, c), name, right=(right if right is not None else row(switch(on), ic("chev", 14, T["faint"]), gap=10)), sub=sub, sel=sel)


def act_tile(icon, name, sel=False):
    """A small square with this action's own icon, the name under it."""
    bg = T["accent_soft"] if sel else T["pane"]
    ring = f"box-shadow: inset 0 0 0 1px {T['selectline']};" if sel else ""
    sq = (f'<span style="width: 54px; height: 54px; border-radius: 16px; background: {bg}; {ring} display: inline-flex; align-items: center; '
          f'justify-content: center;">{ic(icon, 22, T["accent"] if sel else T["dim"])}</span>')
    return col(sq, txt(name, 12.5, T["ink"] if sel else T["dim"], 600 if sel else 500, extra="text-align: center; line-height: 1.35;"),
               gap=10, extra="align-items: center; width: 100%;")


def tile_grid(*tiles, cols=4, h=420):
    """One big container holding the squares, with room around them. It scrolls; the fade says so."""
    inner = f'<div style="display: grid; grid-template-columns: repeat({cols}, minmax(0, 1fr)); gap: 32px 20px;">{"".join(tiles)}</div>'
    fade = f'<div style="position: absolute; left: 0; right: 0; bottom: 0; height: 48px; border-radius: 0 0 18px 18px; background: linear-gradient(180deg, transparent, {T["ground"]}); pointer-events: none;"></div>'
    return (f'<div style="position: relative; width: 100%; height: {h}px; box-sizing: border-box; padding: 26px 22px; border-radius: 18px; '
            f'background: {T["ground"]}; overflow: hidden; flex: none;">{inner}{fade}</div>')


# ------------------------------------------------------------------ 1. Automation: one event, its actions
def screen_automation():
    top = topbar2([IND["pings"]], "Go to, do, find")
    rail = icon_rail("automation", "admin")
    modes = row(*[f'<a href="#{l.lower()}" style="flex: 1; text-align: center; padding: 6px 0; border-radius: 8px; background: {T["pane"] if l == "Editing" else "transparent"}; color: {T["ink"] if l == "Editing" else T["dim"]}; font-size: 12.5px; font-weight: 600; text-decoration: none;">{l}</a>' for l in ("Live", "Editing")],
                gap=2, extra=f"padding: 3px; border-radius: 10px; background: {T['line']}; margin: 6px 12px 4px;")
    side = col(sb_head("Events"), modes,
               sb_section("Native, pushed by the PC", "4"),
               sb_item("automation", "USB inserted", "7 PCs", sel=True), sb_item("automation", "Login"), sb_item("automation", "Logout"), sb_item("automation", "File change in Documents"),
               sb_section("Polled, evaluated here", "3"),
               sb_item("automation", "Idle over 20 min"), sb_item("automation", "CPU over 90 % for 5 min"), sb_item("automation", "Every day 17:30"),
               gap=2, extra="flex: 1;")

    trigger = col(row(ic("automation", 16, T["warn"]), txt("When a USB device is inserted", 13.5, weight=600), '<span style="flex: 1;"></span>', chip("Native", "neutral", 10), gap=9),
                  note_line("Pushed by the PC, no polling. Armed on 7 PCs in Operations."),
                  gap=8, extra=f"padding: 13px 14px; border-radius: 12px; background: {T['ground']};")
    attached = cgroup(
        act_row("Monitoring", "Screenshot", "Monitoring, timeout 30 s", sel=True),
        act_row("Control", "Log event", "Control, timeout 10 s"),
        act_row("Custom", "clear temp", "Custom PowerShell, timeout 60 s", on=False))
    add = row(gbtn("Attach an action", "plus", "sm"), txt("each runs on its own, order is display only", 12, T["faint"]), gap=10)

    pop = popover("Screenshot", "Monitoring action",
                  cgroup(crow(txt("", 1), "Timeout", "30 s", right=""), crow(txt("", 1), "Terminable", "yes", right=""), crow(txt("", 1), "Output", "image, to Live", right=""), gap=6),
                  row(tbtn("Run now", "accent", "play", "sm"), gbtn("Detach", size="sm"), gap=6),
                  acard("Armed on", cgroup(crow(av("KO", "worker", 24), "Kojo", "OPS-01", right=""), crow(av("EF", "worker", 24), "Efua", "OPS-02", right=""),
                                           crow(txt("", 1), "and 5 more", "", right=""), gap=6), summary="7 PCs"),
                  acard("Last runs", cgroup(crow(dot(T["ok"], 8), "OPS-02", "10:58", "ok", right=""), crow(dot(T["ok"], 8), "OPS-04", "10:20", "ok", right=""), gap=6), summary="2 today"),
                  lead=f'<span style="width: 36px; height: 36px; border-radius: 12px; background: {T["ground"]}; display: inline-flex; align-items: center; justify-content: center; flex: none;">{ic("camera", 18, T["dim"])}</span>')

    body = bodywrap(drill(("Automation", False), ("USB inserted", True)),
                    title_av(f'<span style="width: 40px; height: 40px; border-radius: 12px; background: {T["warn_soft"]}; display: inline-flex; align-items: center; justify-content: center; flex: none;">{ic("automation", 20, T["warn"])}</span>',
                             "USB inserted", "Native event, armed on 7 PCs", trail=chip("Armed", "ok", 11)),
                    pills2([("Actions", "3"), ("Where it is armed", "7"), ("History", "12")], "Actions"),
                    row(col(trigger, f'<span style="height: 12px;"></span>', attached, f'<span style="height: 12px;"></span>', add, gap=0, extra=f"width: {BODY_W}px; flex: none;"),
                        lane(pop), gap=22, align="flex-start"))
    sh = sheet(side, body)
    return page("Automation", top, rail, sh, statusbar("Connected, TLS pinned", "native   1.4.2"), "native")


# ------------------------------------------------------------------ 2. Actions: the library, as a grid
def screen_actions():
    top = topbar2([IND["pings"]], "Go to, do, find")
    rail = icon_rail("play", "admin")
    side = col(sb_head("Actions"),
               sb_section("Kinds", ""),
               sb_item("play", "All", right=txt("14", 11, T["faint"])),
               sb_item("automation", "Control", right=txt("6", 11, T["faint"])),
               sb_item("camera", "Monitoring", sel=True, right=txt("6", 11, T["select_sub"])),
               sb_item("file", "Custom", right=txt("2", 11, T["faint"])),
               sb_section("Running on a clock", ""),
               sb_item("clock", "Scheduled", right=txt("3", 11, T["faint"])),
               row(txt("A Custom action is PowerShell or Python, validated before it is sent.", 11.5, T["faint"], extra="line-height: 1.5;"),
                   extra="padding: 10px 16px; margin-top: auto;"),
               gap=2, extra="flex: 1;")

    grid = tile_grid(
        act_tile("camera", "Screenshot", sel=True),
        act_tile("pulse", "System metrics"),
        act_tile("filewatch", "Watch a file"),
        act_tile("window", "Watch a program"),
        act_tile("keyboard", "Keylogging"),
        act_tile("globe", "Network activity"),
        act_tile("cpu", "Process monitoring"),
        act_tile("monitor", "Open windows"),
        act_tile("key", "Logon history"))

    pop = popover("Screenshot", "Monitoring action",
                  cgroup(crow(txt("", 1), "Every", "30 s", right=""), crow(txt("", 1), "Timeout", "30 s", right=""),
                         crow(txt("", 1), "Enabled", "on 7 PCs", "ok", right=""), gap=6),
                  col(tbtn("Run once, now", "accent", "play"), gbtn("Schedule it", "clock"), gbtn("Attach to an event", "automation"), gap=8),
                  acard("Run on", cgroup(crow(av("KO", "worker", 24), "Kojo", "OPS-01", right=switch(True)),
                                         crow(av("EF", "worker", 24), "Efua", "OPS-02", right=switch(True)),
                                         crow(av("AM", "worker", 24), "Ama", "OPS-07", right=switch(False)), gap=6), summary="7 of 7"),
                  acard("Scheduled", cgroup(crow(ic("clock", 15, T["dim"]), "Every day 17:30", "armed", "ok", right=""), gap=6), summary="1 schedule"),
                  lead=f'<span style="width: 36px; height: 36px; border-radius: 12px; background: {T["ground"]}; display: inline-flex; align-items: center; justify-content: center; flex: none;">{ic("camera", 18, T["dim"])}</span>',
                  actions=row(chip("Terminable", "neutral", 10), txt("independent of every other action", 12, T["faint"]), gap=8))

    body = bodywrap(drill(("Actions", False), ("Monitoring", True)),
                    title_av(f'<span style="width: 40px; height: 40px; border-radius: 12px; background: {T["ground"]}; display: inline-flex; align-items: center; justify-content: center; flex: none;">{ic("camera", 20, T["dim"])}</span>',
                             "Monitoring", "What the system watches and records", right=row(gbtn("New custom action", "plus", "sm"), gap=6)),
                    pills2([("All", "6"), ("In use", "4"), ("Unused", "2")], "All"),
                    row(col(grid, gap=0, extra=f"width: {BODY_W}px; flex: none;"), lane(pop), gap=22, align="flex-start"))
    sh = sheet(side, body)
    return page("Actions", top, rail, sh, statusbar("Connected, TLS pinned", "native   1.4.2"), "native")


# ------------------------------------------------------------------ 3. Live: what is running now
def screen_automation_live():
    top = topbar2([IND["pings"]], "Go to, do, find")
    rail = icon_rail("automation", "admin")
    modes = row(*[f'<a href="#{l.lower()}" style="flex: 1; text-align: center; padding: 6px 0; border-radius: 8px; background: {T["pane"] if l == "Live" else "transparent"}; color: {T["ink"] if l == "Live" else T["dim"]}; font-size: 12.5px; font-weight: 600; text-decoration: none;">{l}</a>' for l in ("Live", "Editing")],
                gap=2, extra=f"padding: 3px; border-radius: 10px; background: {T['line']}; margin: 6px 12px 4px;")
    side = col(sb_head("Events"), modes, sb_section("Running", "2"), sb_item("automation", "USB inserted", "OPS-02", sel=True), sb_item("automation", "Idle 20 min", "OPS-06"),
               sb_section("Armed", "5"), sb_item("automation", "Login"), sb_item("automation", "File change"), sb_item("automation", "Every day 17:30"),
               sb_item("automation", "CPU over 90 %"), sb_item("automation", "Logout"), gap=2, extra="flex: 1;")
    st = lambda tone, word: row(dot(tone_c(tone, T["accent"]), 8), txt(word, 12, tone_c(tone, T["accent"]), 600, extra="width: 58px;"), gap=8)
    runs = cgroup(
        crow(st("accent", "Running"), "Screenshot", "USB inserted, OPS-02, 12 s", right=tbtn("Stop", "danger", "stop", "sm")),
        crow(st("accent", "Running"), "System metrics", "Idle 20 min, OPS-06, 3 min", right=tbtn("Stop", "danger", "stop", "sm")),
        crow(st("ok", "Done"), "Log event", "USB inserted, OPS-02, 10:58"),
        crow(st("ok", "Done"), "Screenshot", "Login, OPS-04, 10:20"),
        crow(st("warn", "Timeout"), "Process list", "CPU over 90 %, OPS-03, 60 s"),
        crow(st("danger", "Error"), "clear temp", "Logout, OPS-01, Mon 17:31", sel=True))
    pop = popover("clear temp", "Custom action on OPS-01",
                  row(chip("Error", "danger", 11, dot=True), txt("exit code 1", 12.5, T["faint"], mono=True), gap=8),
                  f'<pre style="margin: 0; padding: 12px 13px; border-radius: 12px; background: {T["ground"]}; color: {T["ink"]}; font-family: {T["mono"]}; font-size: 11.5px; line-height: 1.55; white-space: pre-wrap; word-break: break-word; overflow: hidden;">Remove-Item : Access to the path &#39;C:\\Temp\\lock&#39; is denied.</pre>',
                  cgroup(crow(txt("", 1), "Started", "Mon 17:31", right=""), crow(txt("", 1), "Timeout", "60 s", right=""), crow(txt("", 1), "From event", "Logout", right=""), gap=6),
                  lead=f'<span style="width: 36px; height: 36px; border-radius: 12px; background: {T["danger_soft"]}; display: inline-flex; align-items: center; justify-content: center; flex: none;">{ic("file", 18, T["danger"])}</span>',
                  actions=row(tbtn("Run again", "accent", "play", "sm"), gbtn("Open the action", size="sm"), gap=6))
    body = bodywrap(drill(("Automation", False), ("Live", True)),
                    title_av(f'<span style="width: 40px; height: 40px; border-radius: 12px; background: {T["ground"]}; display: inline-flex; align-items: center; justify-content: center; flex: none;">{ic("automation", 20, T["dim"])}</span>',
                             "Live", "Every action running in this department"),
                    pills2([("All", "6"), ("Running", "2"), ("Done", "2"), ("Timeout", "1"), ("Error", "1")], "All"),
                    row(col(runs, gap=0, extra=f"width: {BODY_W}px; flex: none;"), lane(pop), gap=22, align="flex-start"))
    sh = sheet(side, body)
    return page("Automation, live", top, rail, sh, statusbar("Connected, TLS pinned", "native   1.4.2"), "native")
