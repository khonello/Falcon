# ================================================================== ST01-ST03, DG01, WR01: the states, the dialogs, the Worker's windows
# The last undesigned surfaces, composed straight from design/PATTERNS.md (the patterns are settled, so no mood board
# first; a surface that doesn't land gets one). Every one checked against its worst case before drawing:
#   * connect: a wrong key, an unreachable Engine, a certificate that doesn't match, a hostname deviation
#   * disconnected: mid-traversal -- the Engine keeps the deadline running whether you are connected or not
#   * dialogs: the ones with a cost say it first; the key shown ONCE is said to be shown once
#   * the Worker's windows: plain words, no alarm, never an Operator's vocabulary

DESK = "linear-gradient(135deg, #1b2a3a 0%, #243b53 55%, #2f4f6b 100%)"


def sheet_board(title, sub, content, note, kind="SURFACE"):
    inner = col(eyebrow(kind, title, sub), row(txt(title, 22, "#fff", 700), gap=0, extra="flex: none;"), content,
                txt(note, 11.5, T["frame_faint"]), gap=14,
                extra=f"width: {W}px; height: {H}px; box-sizing: border-box; padding: 24px 40px; background: {FRAME['native']};")
    return page(title, "", "", inner, "", "native")


def inp(label, value, hint="", mono=False, bad=False, w=372):
    ring = T["danger"] if bad else T["line2"]
    return col(txt(label, 11.5, T["faint"], 600),
               (f'<div style="width: {w}px; box-sizing: border-box; padding: 9px 12px; border-radius: 10px; background: {T["ground"]}; '
                f'box-shadow: inset 0 0 0 1px {ring}; font-family: {T["mono"] if mono else T["sans"]}; font-size: 13px; color: {T["ink"]};">{value}</div>'),
               txt(hint, 10.5, T["danger"] if bad else T["faint"]) if hint else "", gap=5)


def modal(title, body, actions, w=440, tone=None):
    ring = f"box-shadow: 0 24px 60px rgba(0,0,0,0.55), inset 0 0 0 1px {T[tone]};" if tone else "box-shadow: 0 24px 60px rgba(0,0,0,0.55);"
    return col(txt(title, 16, T["ink"], 700), *body, row(sp(), *actions, gap=8, extra="width: 100%; padding-top: 6px;"),
               gap=12, extra=f"width: {w}px; box-sizing: border-box; padding: 22px 24px; border-radius: 16px; background: {T['pane']}; {ring}")


# ------------------------------------------------------------------ ST01: connecting, first run and failures
def st01():
    first = modal("Connect to the Engine", [
        txt("The Engine is the machine that runs Falcon for your organisation. Your administrator gave you these.", 12, T["dim"],
            extra="line-height: 1.45;"),
        inp("Engine address", "falcon.internal : 7400"),
        inp("Who you are", "SU-PC", "the name this machine was registered with"),
        inp("Your key", "•••••••• •••••••• ••••", "paste it; it is kept on this machine only", mono=True),
        row(ic("shield", 14, T["ok"]), txt("engine.crt · the Engine's certificate", 12, T["dim"]), sp(), gbtn("Choose…", size="sm"), gap=8,
            extra="width: 100%;"),
        row(ic("check", 15, T["accent"]), txt("Remember on this machine", 12, T["dim"]), gap=8)],
        [tbtn("Connect", "accent", "fwd")], w=440)

    def state(icon, tone, head, body, act=""):
        return col(row(ic(icon, 18, T[tone]), txt(head, 13.5, T["ink"], 600), gap=9), txt(body, 12, T["dim"], extra="line-height: 1.45;"),
                   act, gap=8, extra=f"width: 400px; box-sizing: border-box; padding: 16px; border-radius: 14px; background: {T['pane']};")
    states = col(
        state("clock", "accent", "Connecting to falcon.internal…", "Checking the certificate, then who you are. This takes a moment."),
        state("x", "danger", "The key doesn't match SU-PC.", "Check you pasted the whole key. If it was re-issued, ask for the new one.",
              row(gbtn("Try again", size="sm"), gap=0)),
        state("globe", "danger", "The Engine can't be reached.", "falcon.internal didn't answer on port 7400. It may be off, or the address is wrong.",
              row(gbtn("Retry in 10 s", size="sm"), gbtn("Change the address", size="sm"), gap=4)),
        state("warn", "warn", "Connected — but this machine's name has changed.", "You were registered as SU-PC; this machine now says SU-PC-2. "
              "It has been noted for your administrator; you can carry on.", row(gbtn("Understood", size="sm"), gap=0)),
        gap=12)
    content = row(col(first, gap=0, extra="flex: 1; align-items: center; justify-content: center;"),
                  states, gap=40, align="center",
                  extra=f"flex: 1; padding: 0 30px; border-radius: 14px;")
    return sheet_board("Connecting", "first run, then what can go wrong", content,
                       "ST01 · First run in plain words (no certificate jargon beyond naming the file). Four outcomes, each said once with what "
                       "to do: connecting, a wrong key, unreachable, and a name that changed — a deviation noted, never a refusal.")


# ------------------------------------------------------------------ ST02: loading, and the empty system
def st02():
    skeleton = lambda w, h: f'<div style="width: {w}px; height: {h}px; border-radius: 10px; background: rgba(255,255,255,0.05);"></div>'
    loading = col(txt("Loading", 13, T["dim"], 600),
                  row(col(skeleton(560, 20), skeleton(560, 190), gap=10), col(skeleton(560, 20), skeleton(560, 190), gap=10), gap=24),
                  txt("The shapes of the four cells hold still while their contents arrive — nothing jumps into place.", 11.5, T["faint"]),
                  gap=12, extra="width: 1150px;")
    empty = col(txt("A new system, the first time you open it", 13, T["dim"], 600),
                row(col(txt("Authority", 14, "#fff", 600), txt("No departments yet.", 13, T["ink"], 600),
                        txt("Create the first one, then give it an Admin.", 12, T["dim"]), row(tbtn("Create a department", "accent", "plus", "sm"), gap=0),
                        gap=8, extra=f"width: 560px; box-sizing: border-box; padding: 18px; border-radius: 14px; background: {T['pane']};"),
                    col(txt("Rollout", 14, "#fff", 600), txt("Nothing to roll out.", 13, T["ink"], 600),
                        txt("Machines appear here once they are registered.", 12, T["dim"]),
                        gap=8, extra=f"width: 560px; box-sizing: border-box; padding: 18px; border-radius: 14px; background: {T['pane']};"),
                    gap=24, align="stretch"),
                txt("An empty cell says what is missing and the one next step; it is never blank.", 11.5, T["faint"]), gap=12, extra="width: 1150px;")
    content = col(loading, empty, gap=34, extra="flex: 1; padding: 20px 30px; box-sizing: border-box;")
    return sheet_board("Loading and empty", "while it arrives, and before there is anything", content,
                       "ST02 · Loading keeps each cell's shape (no spinners over blank space). An empty system tells you the first step in each cell.")


# ------------------------------------------------------------------ ST03: disconnected, while holding a session
def st03():
    banner = row(ic("globe", 16, T["warn"]), txt("Lost the connection to the Engine.", 13, T["ink"], 600),
                 txt("Retrying — next try in 4 s.", 12, T["dim"]), sp(),
                 txt("Your session on OPS-03 keeps running until 14:50 either way.", 12, T["warn"], 500), gbtn("Retry now", size="sm"), gap=12,
                 extra=f"width: 1150px; box-sizing: border-box; padding: 11px 16px; border-radius: 12px; background: rgba(255,255,255,0.03); "
                       f"box-shadow: inset 0 0 0 1px rgba(210,164,104,0.45);")
    faded = col(row(col(txt("Its machines", 14, "#fff", 600), row(*[calm_slot(f"{n:02d}", "ok", 58) for n in range(1, 7)], gap=24),
                        gap=12, extra=f"width: 560px; box-sizing: border-box; padding: 18px; border-radius: 14px; background: {T['pane']};"),
                    col(txt("Waiting on you", 14, "#fff", 600), txt("As of 14:31 — may be out of date", 12, T["warn"]),
                        thing_card("shield", "danger", "A restricted file on OPS-07", "11:41"), gap=10,
                        extra=f"width: 560px; box-sizing: border-box; padding: 18px; border-radius: 14px; background: {T['pane']};"),
                    gap=24), gap=0, extra="opacity: 0.55;")
    what = col(txt("What still works", 13, T["dim"], 600),
               tk_line("Reading what is on screen", "yes — marked 'as of 14:31'"),
               tk_line("Anything that changes something", "waits; buttons say so", "warn"),
               tk_line("A session you hold", "keeps its deadline on the Engine", "warn"),
               tk_line("When it reconnects", "every cell refreshes by itself"), gap=0, extra="width: 560px;")
    content = col(banner, faded, what, gap=20, extra="flex: 1; padding: 20px 30px; box-sizing: border-box;")
    return sheet_board("Disconnected", "mid-session, the worst case", content,
                       "ST03 · The worst case: disconnected while holding someone's machine. The line says the session keeps running on the "
                       "Engine; what's on screen stays readable but dated; acts wait. No red alarm — it's usually a blip.")


# ------------------------------------------------------------------ DG01: the dialogs
def dg01():
    key_once = modal("OPS-15 is registered", [
        txt("Give this key to whoever sets up OPS-15. It is shown once — Falcon can't show it again.", 12, T["dim"], extra="line-height: 1.45;"),
        (f'<div style="padding: 12px; border-radius: 10px; background: {T["ground"]}; font-family: {T["mono"]}; font-size: 14px; '
         f'letter-spacing: 1px; color: {T["ink"]}; text-align: center;">7f3a 91c2 e04b 5d18 aa6e</div>'),
        row(gbtn("Copy", size="sm"), sp(), txt("If it's lost, issue a new key from the machine's page.", 11, T["faint"]), gap=8, extra="width: 100%;")],
        [tbtn("I've saved it", "accent", "check")], w=420, tone="warn")
    end_theirs = modal("End R. Mensah's session and enter?", [
        txt("R. Mensah is working at WS-OPS-A1 now.", 12.5, T["ink"], 600),
        tk_line("Their session", "ends now", "danger"), tk_line("They see", "who took it"), tk_line("They get it back", "when you leave"),
        ], [gbtn("Cancel"), tbtn("End theirs and enter", "danger")], w=420)
    offboard = modal("Offboard Kojo?", [
        txt("Kojo's account stops working. Nothing is deleted.", 12.5, T["ink"], 600),
        tk_line("OPS-01", "paused until someone new is set up"), tk_line("2 open tasks", "stay open, for you to reassign", "warn"),
        tk_line("Their files and history", "kept in Record"),
        ], [gbtn("Cancel"), tbtn("Offboard Kojo", "danger")], w=420)
    assign = modal("Assign an Admin to Logistics", [
        txt("Logistics has nobody governing it.", 12, T["dim"]),
        person_card("AQ", "A. Quaye", "Operations · already governs 14 machines"),
        person_card("MA", "M. Addo", "Harbour · already governs 48 machines"),
        row(txt("Or create a new Admin account", 12, T["accent"], 500), gap=0)], [gbtn("Cancel"), tbtn("Assign", "accent")], w=420)
    extend = modal("Extend your session on WS-OPS-A1?", [
        txt("12 minutes left. Extending adds 15 minutes.", 12.5, T["ink"], 600),
        txt("R. Mensah stays blocked for that time too.", 12, T["dim"])], [gbtn("Not now"), tbtn("Extend 15 min", "accent", "clock")], w=420)
    rekey = modal("Issue a new key for OPS-07?", [
        txt("The old key stops working at once. OPS-07 disconnects until the new key is entered there.", 12, T["dim"], extra="line-height: 1.45;")],
        [gbtn("Cancel"), tbtn("Issue a new key", "warn")], w=420)
    grid_ = col(row(key_once, end_theirs, offboard, gap=24, align="flex-start"), row(assign, extend, rekey, gap=24, align="flex-start"),
                gap=24, extra="flex: 1; padding: 6px 20px; box-sizing: border-box;")
    return sheet_board("Dialogs", "the few that interrupt", grid_,
                       "DG01 · Only acts with a cost interrupt. Each states the cost before its button, the button names the act ('Offboard Kojo', "
                       "not 'OK'), and the one-time key says it is shown once. The destructive act is tonal red, Cancel always beside it.", kind="DIALOGS")


# ------------------------------------------------------------------ WR01: the Worker's windows
def wr01():
    def desk(child, w, h, label):
        return col(txt(label, 12, T["frame_dim"], 600),
                   row(child, gap=0, justify="center", extra=f"width: {w}px; height: {h}px; border-radius: 12px; background: {DESK}; align-items: center;"),
                   gap=8)
    overlay = col(ic("shield", 26, T["ink"]), txt("R. Mensah is using this machine", 18, T["ink"], 700, extra="text-align: center;"),
                  txt("You can use it again when they leave — about 20 minutes. You don't need to do anything.", 12.5, T["dim"],
                      extra="text-align: center; line-height: 1.5;"), gap=10,
                  extra=f"width: 360px; box-sizing: border-box; padding: 26px; border-radius: 18px; background: rgba(20,22,32,0.92); align-items: center; "
                        f"box-shadow: inset 0 0 0 1px rgba(221,138,138,0.45);")
    notify = col(row(ic("bell", 16, T["accent"]), txt("From your Admin, R. Mensah", 12, T["dim"], 600), sp(), ic("close", 13, T["faint"]), gap=8,
                     extra="width: 100%;"),
                 txt("Please save your work; the network restarts at 18:00.", 13.5, T["ink"], 600, extra="line-height: 1.4;"),
                 row(sp(), gbtn("OK", size="sm"), gap=0, extra="width: 100%;"), gap=10,
                 extra=f"width: 340px; box-sizing: border-box; padding: 16px; border-radius: 14px; background: {T['pane']}; box-shadow: 0 16px 40px rgba(0,0,0,0.5);")
    ping = col(row(ic("ping", 16, T["warn"]), txt("Ask R. Mensah for help", 13, T["ink"], 600), gap=8),
               tk_input("The printer on floor 2 won't take my login.", 60),
               row(txt("One message, then wait for their reply.", 11, T["faint"]), sp(), tbtn("Send", "warn", size="sm"), gap=8, extra="width: 100%;"),
               gap=10, extra=f"width: 340px; box-sizing: border-box; padding: 16px; border-radius: 14px; background: {T['pane']}; box-shadow: 0 16px 40px rgba(0,0,0,0.5);")
    lock = col(ic("lock", 26, T["ink"]), txt("Locked by your Admin", 18, T["ink"], 700),
               txt("Locked for maintenance. It unlocks by itself at 14:45.", 12.5, T["dim"], extra="text-align: center;"), gap=10,
               extra=f"width: 340px; box-sizing: border-box; padding: 24px; border-radius: 18px; background: rgba(20,22,32,0.92); align-items: center;")
    content = col(row(desk(overlay, 560, 300, "Someone is using your machine"), desk(notify, 560, 300, "A message from your Admin"), gap=30),
                  row(desk(ping, 560, 300, "Asking for help"), desk(lock, 560, 300, "The screen, locked"), gap=30),
                  gap=20, extra="flex: 1; padding: 0 20px; box-sizing: border-box;")
    return sheet_board("The Worker's windows", "small, calm, in plain words", content,
                       "WR01 · The Worker never sees the Operator's vocabulary. Being blocked is said as 'R. Mensah is using this machine', with how "
                       "long and 'you don't need to do anything'. A ping is one message then wait. (The task window is TK07.)")


STATES = [("ST01-Connect.dc.html", "Connecting: first run and failures", st01),
          ("ST02-Loading.dc.html", "Loading and empty", st02),
          ("ST03-Disconnected.dc.html", "Disconnected, mid-session", st03),
          ("DG01-Dialogs.dc.html", "Dialogs: the few that interrupt", dg01),
          ("WR01-Worker.dc.html", "The Worker's windows", wr01)]
