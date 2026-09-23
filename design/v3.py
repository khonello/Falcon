# ================================================================== v3: states, worker, dialogs — same restraint

def mini(title, inner, w=452, h=300):
    return col(txt(title, 12, T["frame_dim"], 500), f'<div style="width: {w}px; height: {h}px; box-sizing: border-box; border-radius: 12px; background: {T["pane"]}; overflow: hidden; display: flex; flex-direction: column; box-shadow: 0 6px 24px rgba(0,0,0,0.45);">{inner}</div>', gap=8)


def centre(*c):
    return col(*c, gap=10, extra="flex: 1; align-items: center; justify-content: center; padding: 24px; text-align: center;")


def screen_states():
    connect = col(row(f'<span style="width: 8px; height: 22px; border-radius: 3px; background: {T["ink"]};"></span>', txt("Falcon", 20, weight=700), gap=8),
                  row(field("Engine", "127.0.0.1:7400", "190px", mono=True), field("Account", "4001", "110px", mono=True), gap=8),
                  row(btn("Connect", "primary"), chip("Certificate pinned", "ok", 10, dot=True), gap=10),
                  gap=16, extra="flex: 1; align-items: flex-start; justify-content: center; padding: 28px 32px;")
    sk = lambda w: f'<div style="height: 10px; width: {w}px; border-radius: 5px; background: {T["line"]};"></div>'
    loading = col(big_title("Operations"), group(*[row(dot(T["line"], 8), sk(w), '<span style="flex: 1;"></span>', sk(40), gap=12, extra=f"height: 46px; padding: 0 16px; {'border-bottom: 1px solid ' + T['line'] + ';' if i < 3 else ''}") for i, w in enumerate((120, 90, 140, 80))]), gap=0)
    empty = col(big_title("Tasks"), centre(ic("tasks", 30, T["line2"]), txt("No tasks yet", 16, weight=600), btn("New task", "primary", "plus")), gap=0)
    error = col(big_title("Flows"), centre(ic("warn", 30, T["danger"]), txt("Can’t create this flow", 16, weight=600), txt("It would loop through OPS-03.", 13, T["faint"]), row(btn("Change source", "primary"), btn("Back", "secondary"), gap=8)), gap=0)
    refused = col(row(avatar("EF", "worker", 36), col(txt("Efua", 16, weight=600), txt("OPS-02", 12, T["faint"], mono=True), gap=2), gap=12, extra="padding: 16px 16px 8px;"),
                  col(row(sess("traversed"), txt("A. Quaye is inside", 13.5, weight=600), '<span style="flex: 1;"></span>', txt("14:02 left", 12, T["faint"], mono=True), gap=8),
                      row(btn("Enter", "primary", "lock", extra="opacity: 0.4;"), btn("Ping Efua", "secondary", "ping"), gap=8),
                      note_line("A peer’s session ends on its own."),
                      gap=12, extra=f"margin: 8px 16px; padding: 14px; border-radius: 12px; background: {T['ground']};"), gap=0)
    disc = col(band("Connection lost. Reconnecting.", "danger", btn("Retry", "frame", size="sm")),
               col(big_title("Operations", "7 PCs, 2 Admins"), group(*[grow(dot(T["line2"], 8), n, "", last=(i == 2)) for i, n in enumerate(("Kojo", "Efua", "Yaw"))]), gap=0, extra="opacity: 0.45;"), gap=0)
    grid = f'<div style="display: grid; grid-template-columns: repeat(3, minmax(0, 1fr)); gap: 32px 24px; padding: 24px 32px;">' + "".join([
        mini("Connect", connect), mini("Loading", loading), mini("Empty", empty), mini("Error", error), mini("Refused: a peer’s session", refused), mini("Disconnected", disc)]) + "</div>"
    tray = row(txt("Indicators", 12, T["frame_dim"], 500), indicator("2 pings", "warn", "ping"), indicator("Deadline", "danger", "clock"), indicator("Task done", "ok", "check"),
               indicator("Flow failed", "danger", "flows"), indicator("Violation", "danger", "shield"), indicator("Help offered", "assist", "assistance"),
               txt("Lit until addressed.", 12, T["frame_faint"]), gap=10, extra="padding: 0 32px;")
    inner = col(tray, grid, gap=0, extra=f"width: {W}px; height: {H}px; box-sizing: border-box; padding-top: 28px; background: {FRAME['native']}; overflow: hidden;")
    return page("States", "", "", inner, "", "native")


def screen_worker():
    overlay = (f'<div style="width: 800px; height: 500px; box-sizing: border-box; border-radius: 12px; background: linear-gradient(135deg, #2b3542, #1b2430); position: relative; overflow: hidden;">'
               f'<div style="position: absolute; inset: 0; background: rgba(18,17,32,0.78); backdrop-filter: blur(8px);"></div>'
               + col(ic("lock", 28, "#fff"),
                     txt("Your Admin is using this PC", 24, "#fff", 600),
                     txt("It comes back on its own.", 14, "rgba(255,255,255,0.7)"),
                     txt("21:18", 40, "#fff", 600, mono=True, extra="margin-top: 12px;"),
                     gap=10, extra="position: absolute; inset: 0; align-items: center; justify-content: center; text-align: center; padding: 40px;")
               + "</div>")

    def dialog(tone, when, title, line, *actions):
        return (f'<div style="width: 400px; box-sizing: border-box; border-radius: 14px; background: {T["pane"]}; box-shadow: 0 12px 40px rgba(0,0,0,0.5); overflow: hidden;">'
                + row(f'<span style="width: 6px; height: 18px; border-radius: 3px; background: {tone_c(tone)};"></span>', txt("Falcon", 12.5, T["dim"], 600), '<span style="flex: 1;"></span>', txt(when, 11.5, T["faint"]), gap=8, extra="padding: 14px 16px 0;")
                + col(txt(title, 16, weight=600), txt(line, 13, T["dim"]), row(*actions, gap=8, extra="margin-top: 4px;"), gap=8, extra="padding: 8px 16px 16px;")
                + "</div>")
    d1 = dialog("warn", "now", "Quarterly report due 17:00", "summary.pdf hasn’t appeared yet.", btn("Open task", "primary"), btn("Ping R. Mensah", "secondary", "ping"))
    d2 = dialog("danger", "10:41", "A restricted file is in your resources", "budget-2026.xlsx was ignored. Delete your copy.", btn("Show file", "secondary", "folder"), btn("Dismiss", "ghost"))
    left = col(txt("Overlay: the whole screen while the PC is entered", 12, T["frame_dim"], 500), overlay, gap=8)
    right = col(txt("Dialog: one notification, bottom right", 12, T["frame_dim"], 500), d1, d2, gap=16)
    inner = row(left, right, gap=40, align="flex-start", extra=f"width: {W}px; height: {H}px; box-sizing: border-box; padding: 40px; background: {FRAME['native']}; overflow: hidden;")
    return page("Worker: Overlay and Dialog", "", "", inner, "", "native")


def screen_dialogs():
    """The plus menu, three creation dialogs, one destructive confirm. Dialogs fade and scale in (200 ms)."""
    def dlg(title, sub, body, *actions, w=460):
        return (f'<div style="width: {w}px; box-sizing: border-box; border-radius: 14px; background: {T["pane"]}; box-shadow: 0 16px 48px rgba(0,0,0,0.55); overflow: hidden;">'
                + col(txt(title, 18, weight=600), txt(sub, 13, T["faint"]) if sub else "", gap=3, extra="padding: 20px 20px 12px;")
                + col(body, gap=12, extra="padding: 0 20px 8px;")
                + row('<span style="flex: 1;"></span>', *actions, gap=8, extra="padding: 12px 20px 20px;")
                + "</div>")

    def fld(label, value="", placeholder="", mono=False, rows=1):
        fam = T["mono"] if mono else T["sans"]
        if rows > 1:
            ctl = f'<textarea aria-label="{label}" placeholder="{placeholder}" style="height: {rows * 24 + 16}px; padding: 10px 12px; border: 0; border-radius: 10px; background: {T["ground"]}; font-family: {fam}; font-size: 13.5px; color: {T["ink"]}; resize: none; width: 100%; box-sizing: border-box; line-height: 1.5;">{value}</textarea>'
        else:
            ctl = f'<input type="text" value="{value}" placeholder="{placeholder}" aria-label="{label}" style="height: 38px; padding: 0 12px; border: 0; border-radius: 10px; background: {T["ground"]}; font-family: {fam}; font-size: 13.5px; color: {T["ink"]}; width: 100%; box-sizing: border-box;">'
        return col(f'<label style="font-family: {T["sans"]}; font-size: 12px; color: {T["dim"]}; font-weight: 500;">{label}</label>', ctl, gap=6)

    def pick(label, value, sub=""):
        return col(f'<label style="font-family: {T["sans"]}; font-size: 12px; color: {T["dim"]}; font-weight: 500;">{label}</label>',
                   row(txt(value, 13.5), txt(sub, 12, T["faint"]) if sub else "", '<span style="flex: 1;"></span>', ic("chevd", 14, T["faint"]), gap=8, extra=f"height: 38px; padding: 0 12px; border-radius: 10px; background: {T['ground']};"), gap=6)

    # the plus menu, anchored under the sidebar's +
    plus_btn = f'<span style="width: 28px; height: 28px; border-radius: 8px; background: {T["line"]}; display: inline-flex; align-items: center; justify-content: center; color: {T["ink"]};">{ic("x", 15)}</span>'
    item = lambda icon, label, last=False: row(ic(icon, 15, T["dim"]), txt(label, 13.5), gap=10, extra=f"height: 40px; padding: 0 14px; {'' if last else ''}")
    menu = (f'<div style="width: 220px; border-radius: 12px; background: {T["pane"]}; box-shadow: 0 12px 40px rgba(0,0,0,0.5); padding: 6px; box-sizing: border-box; display: flex; flex-direction: column; gap: 0;">'
            + item("monitor", "Register a PC") + item("tasks", "New task") + item("flows", "New flow") + item("bell", "Send an alert", True) + "</div>")
    anchored = col(row(txt("Operations", 15, weight=700, extra="flex: 1;"), plus_btn, gap=6, extra=f"width: 280px; height: 44px; padding: 0 10px 0 16px; box-sizing: border-box; background: {T['side_native']}; border-radius: 12px 12px 0 0;"),
                   row('<span style="flex: 1;"></span>', menu, gap=0, extra="width: 280px; padding: 4px 6px 0 0; box-sizing: border-box;"), gap=0)

    new_task = dlg("New task", "Describe it. The model drafts targets and a deadline; you confirm.",
                   col(pick("For", "Nana", "OPS-05"), fld("What should be done", "Reconcile the Q3 supplier invoices against suppliers-q3.xlsx and produce reconciliation-q3.docx by Wednesday.", rows=4), gap=12),
                   btn("Cancel", "ghost"), btn("Draft", "primary", "tasks"))
    confirm = dlg("End Ama’s session?", "She’ll see the overlay until you leave.", "", btn("Cancel", "ghost"), btn("End session", "danger", "lock"), w=380)
    register = dlg("Register a PC", "It binds to one account for its lifetime.",
                   col(fld("Hostname", "WS-OPS-08", mono=True), pick("Department", "Operations"), fld("Name, only you see it", "", "Optional"), gap=12),
                   btn("Cancel", "ghost"), btn("Register", "primary", "plus"))
    create_dept = dlg("New department", "Admins can be assigned later.",
                      col(fld("Name", "", "Logistics"), gap=12),
                      btn("Cancel", "ghost"), btn("Create", "primary", "plus"), w=380)
    key_note = (f'<div style="width: 460px; box-sizing: border-box; border-radius: 14px; background: {T["pane"]}; box-shadow: 0 16px 48px rgba(0,0,0,0.55); overflow: hidden;">'
                + col(txt("WS-OPS-08 registered", 18, weight=600), txt("This key is shown once.", 13, T["faint"]), gap=3, extra="padding: 20px 20px 12px;")
                + col(f'<div style="padding: 12px 14px; border-radius: 10px; background: {T["ground"]}; font-family: {T["mono"]}; font-size: 12.5px; color: {T["ink"]}; word-break: break-all;">4c1f9e2a7b0d…e83a</div>', gap=0, extra="padding: 0 20px 8px;")
                + row('<span style="flex: 1;"></span>', btn("Copy key", "secondary"), btn("Done", "primary", "check"), gap=8, extra="padding: 12px 20px 20px;")
                + "</div>")

    lab = lambda t: txt(t, 12, T["frame_dim"], 500)
    grid = row(col(lab("The plus menu"), anchored, gap=8, extra="width: 300px;"),
               col(lab("New task"), new_task, gap=8),
               col(lab("Confirm, destructive"), confirm, lab("New department"), create_dept, gap=8),
               gap=40, align="flex-start")
    grid2 = row(col(lab("Register a PC"), register, gap=8), col(lab("After registering: the key, once"), key_note, gap=8), gap=40, align="flex-start")
    inner = col(row(f'<span style="width: 8px; height: 22px; border-radius: 3px; background: #fff;"></span>', txt("Dialogs", 20, "#fff", 700), txt("fade and scale in, 200 ms; Esc or click outside closes", 12, T["frame_faint"]), gap=10),
                grid, grid2, gap=24, extra=f"width: {W}px; height: {H}px; box-sizing: border-box; padding: 28px 40px; background: {FRAME['native']}; overflow: hidden;")
    return page("Dialogs", "", "", inner, "", "native")
