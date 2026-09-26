# ================================================================== Batch 1 mood boards: HO01, FL01-FL02, AS01, RP01
# The user, 26 Sep 2026: "I want us to finish the design work to a good level ... anyplace you think this
# approach helps, don't hold back, it doesn't matter if it admin, department or super level."
#
# The Admin's remaining pages, each in the TK/AU format: one facet per section, four approaches at the
# same size, captioned so a pick can be named. Drawn from the combo documents:
#   Hierarchy home   the Admin's own department -- every machine is theirs to govern (with the others)
#   Flows            flow-natural-combo.md: source -> stages (branch / transform / categorize) ->
#                    destinations, one way only; consent, collision and cycle checks before saving;
#                    a failure pauses only its branch and offers a fix; an outside edit is kept as -modified
#   Assistance       resource-assistance-combo.md: the ping, the channel (one message per turn, only the
#                    superior closes it), listeners; and file search, scoped to what you may see
#   Reports          hierarchy-system-design.md, Report Routing: categories routed to a department, every
#                    Admin there sees them and marks them seen or addressed
# Nothing is typed as code on any of them.

B_CW, B_CH = 316, 240


def b_cell(name, html, note=""):
    return tk_cell(name, html, note)


def b_row(left, right="", tone=None, lead="", sub=""):
    return tk_line(left, right, tone, lead, sub)


def b_node(icon, label, sub="", tone="accent", w=None):
    width = f"width: {w}px;" if w else ""
    return col(row(au_icon(icon, tone, 22), txt(label, 11.5, T["ink"], 600), gap=7),
               txt(sub, 10, T["faint"]) if sub else "", gap=2,
               extra=f"{width} padding: 7px 9px; border-radius: 9px; background: {T['ground']}; box-sizing: border-box;")


def b_arrow(w=18):
    return row(ic("arrow", 13, T["faint"]), gap=0, extra=f"width: {w}px; justify-content: center; flex: none;")


def b_bubble(text, mine=False, meta=""):
    return col(txt(text, 11.5, T["ink"], extra="line-height: 1.4;"), txt(meta, 9.5, T["faint"]) if meta else "", gap=3,
               extra=f"max-width: 200px; padding: 7px 10px; border-radius: 11px; box-sizing: border-box; "
                     f"background: {T['accent_soft'] if mine else T['ground']}; align-self: {'flex-end' if mine else 'flex-start'};")


# ------------------------------------------------------------------ HO01: the Admin's home
def ho01():
    a = b_cell("Four cells", dp_wire(dp_box(28, 10, 160, 62, label="needs you"), dp_box(196, 10, 76, 62, label="today"),
                                     dp_box(28, 80, 76, 58, label="people"), dp_box(112, 80, 160, 58, label="the machines")),
               "the department page's own language")
    b = b_cell("Machines first", dp_wire(dp_box(28, 10, 244, 78, label="every machine, as it is now"),
                                         dp_box(28, 96, 118, 42, label="needs you"), dp_box(154, 96, 118, 42, label="today")),
               "the fleet is the subject")
    c = b_cell("The day as the spine", dp_wire(dp_box(28, 10, 244, 34, label="needs you, one line"),
                                               dp_box(28, 52, 244, 86, label="today: who was where, hour by hour")),
               "read by what happened")
    d = b_cell("A queue first", dp_wire(dp_box(28, 10, 150, 128, label="what waits on you"),
                                        dp_box(186, 10, 86, 62, label="machines"), dp_box(186, 80, 86, 58, label="today")),
               "work you must do, first")
    s1 = msection("The shape of the Admin's home — their department, from inside", a, b, c, d)

    e = b_cell("A tile each", col(
        row(*[col(row(av(i, "worker", 22), txt(n, 11.5, T["ink"], 600), gap=6), txt(h, 10, T["faint"], mono=True),
                  row(sicon(st, 11), txt(w, 10.5, T["faint"]), gap=4), gap=4,
                  extra=f"width: 86px; padding: 8px; border-radius: 10px; background: {T['ground']}; box-sizing: border-box;")
              for i, n, h, st, w in [("KO", "Kojo", "OPS-01", "native", "at the PC"), ("EF", "Efua", "OPS-02", "free", "free"),
                                     ("AD", "Adjoa", "OPS-04", "traversed", "entered")]], gap=6),
        gap=0), "person, machine, state")
    f = b_cell("Slots", col(
        row(*[f'<span style="width: 34px; height: 34px; border-radius: 10px; background: {c_}; display: inline-flex; '
              f'align-items: center; justify-content: center; font-family: {T["mono"]}; font-size: 10.5px; color: #0d1018; '
              f'font-weight: 700;">{n}</span>' for n, c_ in [("01", T["ok"]), ("02", T["line2"]), ("03", T["ok"]), ("04", T["warn"]),
                                                             ("05", T["ok"]), ("06", T["line2"]), ("07", T["danger"])]], gap=5),
        txt("at the PC · free · entered · out of place", 10.5, T["faint"]), gap=10), "seven at a glance")
    g = b_cell("One line each", col(
        b_row("Kojo · OPS-01", "at the PC", lead=sicon("native", 13)), b_row("Efua · OPS-02", "free", lead=sicon("free", 13)),
        b_row("Adjoa · OPS-04", "you entered", "warn", lead=sicon("traversed", 13)),
        b_row("Ama · OPS-07", "file out of place", "danger", lead=sicon("native", 13)), gap=0), "a quiet list")
    h = b_cell("A reading", col(
        txt("Five of seven machines are in use; Ama's has a file out of place.", 12.5, T["ink"], 600, extra="line-height: 1.35;"),
        b_row("At the PC", "5"), b_row("Free", "2"), b_row("Out of place", "OPS-07", "danger"), gap=6), "a sentence and its facts")
    s2 = msection("One machine, drawn — the Admin governs all of them", e, f, g, h)
    return board("Admin home: their department", s1, s2)


# ------------------------------------------------------------------ FL01: the Flows page, and one flow
def fl01():
    a = b_cell("A map of every flow", dp_wire(
        dp_box(30, 20, 52, 26, label="OPS-02"), dp_box(118, 12, 60, 22, label="PDF"), dp_box(214, 8, 58, 22, label="Archive"),
        dp_box(214, 40, 58, 22, label="Backup"), dp_box(30, 90, 52, 26, label="OPS-05"), dp_box(214, 92, 58, 22, label="Finance")),
        "where files go, drawn")
    b = b_cell("From → to, a list", col(
        *[row(txt(s, 11.5, T["ink"], 600, mono=True), ic("arrow", 12, T["faint"]), txt(d, 11.5, T["dim"]), sp(),
              txt(st, 11, tone_c(t, T["faint"]), 600), gap=7, extra=f"width: 100%; padding: 7px 0; border-bottom: 1px solid {T['line']};")
          for s, d, st, t in [("OPS-02", "Archive, Backup", "syncing", "ok"), ("OPS-05", "Finance share", "paused", "warn"),
                              ("OPS-03", "WS-OPS-A1", "failed", "danger"), ("WS-OPS-A1", "every worker", "syncing", "ok")]], gap=0),
        "one line per flow")
    c = b_cell("By machine", col(
        row(txt("OPS-02", 12, T["ink"], 600, mono=True), sp(), txt("sends 1 · receives 1", 10.5, T["faint"]), gap=0),
        row(txt("OPS-05", 12, T["ink"], 600, mono=True), sp(), txt("sends 1", 10.5, T["faint"]), gap=0),
        row(txt("WS-OPS-A1", 12, T["ink"], 600, mono=True), sp(), txt("sends 1 · receives 2", 10.5, T["faint"]), gap=0),
        txt("A machine is where you look for what moves through it.", 10.5, T["faint"]), gap=10), "what moves through each PC")
    d = b_cell("Four cells", dp_wire(dp_box(28, 10, 160, 62, label="your flows"), dp_box(196, 10, 76, 62, label="broken"),
                                     dp_box(28, 80, 76, 58, label="waiting consent"), dp_box(112, 80, 160, 58, label="synced today")),
               "the Overview's language")
    s1 = msection("The Flows page — what moves where", a, b, c, d)

    e = b_cell("A pipeline", col(
        row(b_node("folder", "Source", "OPS-02, Raw submissions", w=86), b_arrow(), b_node("file", "Make PDF", "transform", "warn", w=80),
            b_arrow(), b_node("monitor", "Archive", "remote", "ok", w=74), gap=0),
        txt("Left to right, the way the files travel. One way only.", 10.5, T["faint"]), gap=12), "stages in a row")
    f = b_cell("A tree", col(
        b_node("folder", "OPS-02 · Raw submissions", w=200),
        row(txt("├─", 12, T["faint"], mono=True), b_node("file", "Make PDF → by type → Archive", tone="warn", w=200), gap=6),
        row(txt("└─", 12, T["faint"], mono=True), b_node("monitor", "As they are → Backup", tone="ok", w=200), gap=6),
        gap=6), "branches you can see")
    g = b_cell("A sentence", col(
        au_sentence(f"Copy {au_slot('Raw submissions')}", f"from {au_slot('OPS-02')}", f"to {au_slot('Archive', 'ok')}",
                    f"as {au_slot('PDF', 'warn')}", f"and to {au_slot('Backup', 'ok')}", "as they are", size=12),
        txt("syncing · last change 11:20", 10.5, T["ok"]), gap=8), "every blank a choice")
    h = b_cell("A recipe card", col(
        txt("FROM", 10, T["faint"], 700), row(au_icon("folder", "accent", 22), txt("OPS-02 · Raw submissions", 11.5, T["ink"], 600), gap=8),
        txt("THROUGH", 10, T["faint"], 700), row(au_icon("file", "warn", 22), txt("Make PDF, then sort by type", 11.5, T["dim"]), gap=8),
        txt("TO", 10, T["faint"], 700), row(au_icon("monitor", "ok", 22), txt("Archive · Backup", 11.5, T["dim"]), gap=8),
        gap=5), "like the automations")
    s2 = msection("One flow, drawn", e, f, g, h)
    return board("Flows: the page", s1, s2)


# ------------------------------------------------------------------ FL02: making a flow, and when it breaks
def fl02():
    a = b_cell("Three steps", col(
        row(*[row(f'<span style="width: 20px; height: 20px; border-radius: 10px; background: {T["accent"] if i == 1 else T["ground"]}; '
                  f'color: {"#0d1018" if i == 1 else T["faint"]}; font-size: 11px; font-weight: 700; display: inline-flex; '
                  f'align-items: center; justify-content: center; font-family: {T["sans"]};">{i}</span>',
                  txt(n, 11.5, T["ink"] if i == 1 else T["faint"], 600 if i == 1 else 400), gap=6)
              for i, n in [(1, "From"), (2, "Through"), (3, "To")]], gap=16),
        rule(), txt("Which folder should it copy from?", 12.5, T["ink"], 600),
        row(ic("folder", 15, T["dim"]), txt("OPS-02 · Documents / raw-submissions", 11.5, T["dim"]), sp(), gbtn("Browse", size="sm"), gap=7,
            extra=f"width: 100%; padding: 6px 9px; border-radius: 9px; background: {T['ground']}; box-sizing: border-box;"),
        gap=9), "from, through, to")
    b = b_cell("Fill the sentence", col(
        au_sentence(f"Copy {au_slot('a folder')}", f"from {au_slot('a machine')}", f"to {au_slot('somewhere', 'ok')}", size=12.5),
        txt("then, if you like", 10.5, T["faint"]),
        row(au_chip("+ make PDF"), au_chip("+ sort into folders"), au_chip("+ another destination"), gap=5,
            extra="flex-wrap: wrap;"), gap=8), "the automation's way")
    c = b_cell("Draw it", col(
        row(b_node("folder", "OPS-02", w=84), b_arrow(), f'<span style="width: 70px; height: 38px; border-radius: 9px; border: 1.5px dashed {T["line2"]}; '
            f'display: inline-flex; align-items: center; justify-content: center; font-size: 10.5px; color: {T["faint"]}; '
            f'font-family: {T["sans"]};">+ stage</span>', b_arrow(), b_node("monitor", "?", "drop a place", "ok", w=74), gap=0),
        txt("Drag a place onto the end; drop a stage in between.", 10.5, T["faint"]), gap=12), "build the pipeline")
    d = b_cell("Checked before saving", col(
        row(ic("check", 13, T["ok"]), txt("No loop: nothing flows back to OPS-02", 11.5, T["ok"]), gap=6),
        row(ic("warn", 13, T["warn"]), txt("Archive already has 12 files there", 11.5, T["warn"]), gap=6),
        row(gbtn("Use another folder", size="sm"), gbtn("Replace them, it is meant", size="sm"), gap=4),
        row(ic("clock", 13, T["accent"]), txt("Finance share needs its owner's yes", 11.5, T["accent"]), gap=6),
        gap=8), "the three checks, said plainly")
    s1 = msection("Making a flow — no paths typed, nothing saved unchecked", a, b, c, d)

    e = b_cell("The broken branch", col(
        b_node("folder", "OPS-02 · Raw submissions", w=200),
        row(txt("├─", 12, T["faint"], mono=True), b_node("file", "Make PDF · failed at 11:20", tone="danger", w=200), gap=6),
        row(txt("└─", 12, T["faint"], mono=True), b_node("monitor", "Backup · still syncing", tone="ok", w=200), gap=6),
        txt("Only the broken branch waits.", 10.5, T["faint"]), gap=6), "only it pauses")
    f = b_cell("The fix, offered", col(
        txt("Make PDF could not convert payroll.xlsm.", 12.5, T["ink"], 600, extra="line-height: 1.35;"),
        txt("Suggested", 10.5, T["faint"], 600),
        row(tbtn("Skip files it cannot convert", "accent", size="sm"), gap=0),
        row(gbtn("Remove the PDF stage", size="sm"), gbtn("Retry", size="sm"), gap=4),
        txt("It resumes by itself once fixed.", 10.5, T["faint"]), gap=8), "reactive, never set up in advance")
    g = b_cell("Kept, not overwritten", col(
        row(ic("file", 15, T["accent"]), txt("report.xlsx", 12, T["ink"], 600, mono=True), sp(), txt("from the source", 10.5, T["faint"]), gap=7),
        row(ic("file", 15, T["warn"]), txt("report-modified.xlsx", 12, T["ink"], 600, mono=True), sp(), txt("Nana's edit, kept", 10.5, T["warn"]), gap=7),
        txt("Someone changed the copy at the destination. Their version is kept beside the fresh one.", 11, T["faint"],
            extra="line-height: 1.4;"), gap=9), "an outside edit")
    h = b_cell("Waiting for a yes", col(
        row(au_icon("clock", "accent", 24), txt("Waiting for K. Boateng", 12, T["ink"], 600), gap=8),
        txt("Finance share belongs to another department's Admin, so they must agree first.", 11, T["faint"],
            extra="line-height: 1.4;"),
        row(gbtn("Remind them", size="sm"), gbtn("Pick another place", size="sm"), gap=4), gap=9), "consent, said plainly")
    s2 = msection("When a flow needs you — broken, conflicted, or waiting", e, f, g, h)
    return board("Flows: making one, and when it breaks", s1, s2)


# ------------------------------------------------------------------ AS01: Assistance
def as01():
    a = b_cell("The ping, unmissable", col(
        row(f'<span style="width: 12px; height: 12px; border-radius: 6px; background: {T["warn"]}; box-shadow: 0 0 0 6px {T["warn_soft"]};"></span>',
            txt("Kojo pinged you twice", 13, T["ink"], 600), gap=12, extra="padding: 6px 4px;"),
        txt("OPS-01 · first at 09:40, again at 10:15", 11, T["faint"]),
        row(tbtn("Answer", "warn", size="sm"), gap=0),
        txt("It stays lit until you answer; it never times out.", 10.5, T["faint"]), gap=9), "a signal, not a message")
    b = b_cell("A channel of turns", col(
        b_bubble("The printer on floor 2 won't take my login.", meta="Kojo · 10:16"),
        b_bubble("Try the badge reader, then your PIN.", mine=True, meta="you · 10:18"),
        row(ic("lock", 12, T["faint"]), txt("Kojo's turn — you can reply once he has", 10.5, T["faint"]), gap=6),
        gap=6), "one message each, in turn")
    c = b_cell("By person", col(
        b_row("Kojo · OPS-01", "2 pings", "warn", lead=av("KO", "worker", 22)),
        b_row("Ama · OPS-07", "your turn", "accent", lead=av("AM", "worker", 22)),
        b_row("Yaw · OPS-03", "their turn", None, lead=av("YA", "worker", 22)), gap=0), "who is waiting on whom")
    d = b_cell("Listening in", col(
        row(ic("eye", 14, T["accent"]), txt("HR is listening", 12, T["ink"], 600), gap=7),
        txt("You added them. Kojo is not told — the audit trail records it.", 11, T["faint"], extra="line-height: 1.4;"),
        row(gbtn("+ another listener", size="sm"), gap=0), gap=9), "a quiet third party")
    s1 = msection("Pings and channels — structured, never a chat", a, b, c, d)

    e = b_cell("One search box", col(
        tk_input("quarterly budget template", 34),
        b_row("budget-template-2026.xlsx", "Common", lead=ic("file", 14, T["accent"])),
        b_row("budget-q3-draft.xlsx", "Workers · Operations", lead=ic("file", 14, T["accent"])), gap=6),
        "only what you may see")
    f = b_cell("Grouped by where", col(
        txt("COMMON", 10, T["ok"], 700), b_row("budget-template-2026.xlsx", "everyone"),
        txt("YOUR DEPARTMENT", 10, T["accent"], 700), b_row("budget-q3-draft.xlsx", "Operations"), gap=4),
        "the tier is the heading")
    g = b_cell("With where to get it", col(
        row(ic("file", 16, T["accent"]), txt("budget-template-2026.xlsx", 12, T["ink"], 600), gap=8),
        txt("In your Resources folder already · Common", 11, T["ok"]),
        row(gbtn("Open its folder", size="sm"), gap=0), gap=9), "found means reachable")
    h = b_cell("Not found — then ask", col(
        txt("Nothing named 'Q4 forecast' is yours to see.", 12, T["ink"], 600, extra="line-height: 1.35;"),
        row(tbtn("Ping R. Mensah about it", "warn", size="sm"), gap=0),
        txt("Search first; asking is the next step, not the first.", 10.5, T["faint"]), gap=9), "the hand-off to a ping")
    s2 = msection("Finding a file — search before asking", e, f, g, h)
    return board("Assistance: pings, channels, search", s1, s2)


# ------------------------------------------------------------------ RP01: Reports
def rp01():
    a = b_cell("A queue to address", col(
        b_row("A restricted file on OPS-07", "new", "danger", lead=ic("shield", 14, T["danger"])),
        b_row("Flow failed: PDF stage", "seen", "warn", lead=ic("flows", 14, T["warn"])),
        b_row("Listener report, channel 14", "addressed", "ok", lead=ic("eye", 14, T["ok"])), gap=0), "work down it")
    b = b_cell("By category", col(
        *[row(txt(k, 11.5, T["dim"]), sp(), row(*[f'<span style="width: 10px; height: 10px; border-radius: 3px; background: {c_};"></span>'
                                                 for c_ in cs], gap=3), gap=8, extra="width: 100%; padding: 6px 0;")
          for k, cs in [("Resource violations", [T["danger"], T["danger"], T["ok"]]), ("Flow failures", [T["warn"], T["ok"]]),
                        ("Listener reports", [T["ok"]]), ("Directory conflicts", [])]],
        txt("new · seen · addressed", 10.5, T["faint"]), gap=2), "a row per kind")
    c = b_cell("A timeline", col(
        *[row(txt(t, 10.5, T["faint"], mono=True, extra="width: 38px;"), dot(c_, 8), txt(w, 11.5, T["dim"]), gap=8, extra="padding: 5px 0;")
          for t, c_, w in [("11:41", T["danger"], "Restricted file on OPS-07"), ("10:02", T["warn"], "Flow failed on OPS-03"),
                           ("Mon", T["ok"], "Listener report addressed")]], gap=0), "read in time")
    d = b_cell("Four cells", dp_wire(dp_box(28, 10, 160, 62, label="new to you"), dp_box(196, 10, 76, 62, label="routed here"),
                                     dp_box(28, 80, 76, 58, label="by kind"), dp_box(112, 80, 160, 58, label="addressed this week")),
               "the Overview's language")
    s1 = msection("The Reports page — what the department must answer", a, b, c, d)

    e = b_cell("A reading, then mark it", col(
        txt("budget-2026.xlsx, restricted, is on Ama's machine.", 12.5, T["ink"], 600, extra="line-height: 1.35;"),
        b_row("Where", "OPS-07 · /workers/"), b_row("Found", "11:41"),
        row(tbtn("Mark addressed", "ok", "check", size="sm"), gbtn("Seen", size="sm"), gap=4), gap=6), "facts, then the act")
    f = b_cell("With what to do", col(
        txt("A restricted file is out of place.", 12.5, T["ink"], 600),
        txt("Ama has been told. It is ignored by the system until moved.", 11, T["faint"], extra="line-height: 1.4;"),
        row(gbtn("Ping Ama", size="sm"), gbtn("Enter OPS-07", size="sm"), gap=4), gap=8), "the next step, offered")
    g = b_cell("Who else sees it", col(
        row(ic("shield", 13, T["danger"]), txt("The Super User always has it", 11.5, T["dim"]), gap=7),
        row(ic("dept", 13, T["accent"]), txt("Routed to Operations: all 2 Admins", 11.5, T["dim"]), gap=7),
        txt("Marking it addressed here does not touch the Super User's copy.", 10.5, T["faint"], extra="line-height: 1.4;"),
        gap=8), "routing, made visible")
    h = b_cell("A sentence per report", col(
        *[txt(s_, 11.5, T["dim"], extra=f"padding: 6px 0; border-bottom: 1px solid {T['line']}; line-height: 1.35;")
          for s_ in ["A restricted file turned up on Ama's machine at 11:41.", "The PDF stage failed on OPS-03; the backup still runs.",
                     "HR addressed the listener report on Monday."]], gap=0), "generated, twelve words")
    s2 = msection("One report — read it, act, mark it", e, f, g, h)
    return board("Reports: what the department must answer", s1, s2)


BATCH1_MOOD = [("HO01-Home.dc.html", "Admin home: their department", ho01),
               ("FL01-Flows.dc.html", "Flows: the page", fl01),
               ("FL02-Making.dc.html", "Flows: making one, and when it breaks", fl02),
               ("AS01-Assistance.dc.html", "Assistance: pings, channels, search", as01),
               ("RP01-Reports.dc.html", "Reports: what the department must answer", rp01)]
