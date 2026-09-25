# ================================================================== DP05-DP06: the department, built from the picks
# T01 and T02 were drawn before the department had a mood board. DP01-DP04 gave it one, and this is
# the page rebuilt from what was picked off it, plus the four cell names settled in TABS.md issue 9.
#
# The picks, and where each one shows up here:
#   DP01 s2 "Columns"          -- the Admins sit side by side, equal, across the top
#   DP02 s1 "Station"          -- one Admin is an avatar, their workstation, their state, their slots
#   DP03 s1 "Grouped by Admin" -- the seven client PCs are grouped under whoever answers for them
#   DP04 s1 "Opens in place"   -- a cell grows where it stands; nothing navigates
#   DP04 s2 "A reading"        -- asking to enter states the COST first, and the act last
#
# THE FOUR CELLS ARE NAMED: Who governs, Its machines, Today, Waiting on you (TABS.md issue 9).
# They are cells, not tabs -- the department is one page. The widths do the ranking and TODAY IS THE
# WIDE ONE, because a department you have not entered is read by its day.
#
# ITS SIGNATURE IS AN EQUAL PAIR OVER A SPLIT: people and machines share the top because neither is
# chosen, then the day takes the wide cell with the queue narrow beside it. K01 is a perfect grid,
# K03-K06 are four other shapes, and this is a sixth -- you know which page you are on before
# reading a word.
#
# LEVEL 2 ONLY. No lid, no countdown, nobody else's rail: that is level 3, and it already has
# screens. What belongs here is choosing, asking, and the answer that comes back.
#
# The rail is drawn as the five settled areas -- Must see, Authority, Rollout, Record, Work -- with
# AUTHORITY lit, because a Super User looking at a department is deeper inside Authority rather than
# somewhere new. It is still eight entries in QML; drawing it as five is what the design says, and
# IconRail.qml has not been changed yet.

SU_AREAS = [("mustsee", "Must see", "pulse"), ("authority", "Authority", "home"),
            ("rollout", "Rollout", "shield"), ("record", "Record", "eye"), ("work", "Work", "tasks")]

STATION_LINE = {"RM": "Four machines; OPS-06 behind since Friday.",
                "AQ": "Three machines; OPS-07 keeps a restricted file."}

DEPT_TINT = DEPT_COLOR["Operations"]          # identity, from the categorical ramp, never a state colour


# ------------------------------------------------------------------ the place, and its identity
def dept_title(crumbs, heading, phrase, tone):
    """The crumb, the title, and the department's identity colour stamped small beside it. That is
    the whole of how depth is told -- nothing about the frame, the palette or the kit changes."""
    trail = []
    for i, step in enumerate(crumbs):
        if i:
            trail.append(ic("chev", 12, T["frame_faint"]))
        trail.append(txt(step, 12.5, "#fff" if i == len(crumbs) - 1 else T["frame_faint"],
                         600 if i == len(crumbs) - 1 else 400))
    stamp = (f'<span style="width: 9px; height: 9px; border-radius: 3px; background: {DEPT_TINT}; '
             f'display: inline-block; flex: none;"></span>')
    return col(row(*trail, gap=6, extra="flex: none;"),
               row(txt(heading, 24, "#fff", 700, extra="letter-spacing: -0.3px;"), stamp,
                   txt(phrase, 13, tone_c(tone, T["frame_dim"]), 500),
                   '<span style="flex: 1;"></span>',
                   txt("Wednesday, 14:20", 12.5, T["frame_faint"]),
                   gap=12, extra="width: 100%; flex: none;"),
               gap=5, extra="flex: none;")


def dept_page(title, crumbs, heading, phrase, tone, bands, note, brow, active="authority",
              status=("native   no session", "ok")):
    top = topbar2([IND["rollout"], IND["pings"]], "Go to, do, find")
    rail = held_rail(active, SU_AREAS)
    inner = col(brow if brow else "", dept_title(crumbs, heading, phrase, tone), *bands,
                (row(txt(note, 11.5, T["frame_faint"]), gap=0, extra="flex: none;") if note else ""),
                gap=12, extra="flex: 1; min-width: 0; display: flex; flex-direction: column; "
                              "padding: 6px 22px 8px 6px; box-sizing: border-box; overflow: hidden;")
    return page(title, top, rail, inner, statusbar("Connected, TLS pinned", status[0], status[1]), "native")


# ------------------------------------------------------------------ Who governs: ONE Admin at a time
# Two stations crammed into one cell was rejected ("the who governs is terrible"). The cell now draws
# ONE Admin at full width and names the others on a line at the foot. Single click on a name swaps
# which one is drawn; double click enters them. Nothing is compressed, because only one is there.
#
# Which one is drawn at rest follows the STABLE ORDER rule -- admins in their fixed order, never
# resorted by state -- so the cell does not rearrange itself under you when something goes wrong.
def other_line(a):
    return row(av(a["initials"], "admin", 22, "native"),
               txt(a["name"], 12.5, T["dim"], 500),
               sicon(a["state"], 12), txt(SESSION_WORD[a["state"]].lower(), 11.5, T["faint"]),
               sp(), txt(f'{len(a["pcs"])} machines', 11.5, T["faint"]), ic("chev", 13, T["faint"]),
               gap=8, extra=f"width: 100%; padding: 9px 0;")


def one_admin(a, others, w=856):
    head = row(av(a["initials"], "admin", 44, "native"),
               col(txt(a["name"], 16, T["ink"], 600),
                   row(txt(a["host"], 12, T["faint"], mono=True), sicon(a["state"], 13),
                       txt(SESSION_WORD[a["state"]] + " · " + a["when"], 12, T["faint"]), gap=7),
                   gap=3, extra="flex: 1; min-width: 0;"),
               sp(), txt(f'Answers for {len(a["pcs"])}', 12, T["faint"]),
               gap=13, extra=f"width: {w}px;")
    work = row(health_line("Tasks", a["tasks"], w=282), health_line("Flows", a["flows"], w=282),
               sp(), gap=44, extra=f"width: {w}px;")
    told = txt(a["told"], 13, T["ink"], 500, extra="line-height: 1.4;")
    foot = col(rule(), txt("Also here", 11.5, T["faint"]),
               col(*[other_line(o) for o in others], gap=0, extra=f"width: {w}px;"),
               gap=9, extra=f"width: {w}px;")
    return col(head, rule(), work, told, sp(), foot, gap=13, extra=f"width: {w}px; height: 100%;")


# ------------------------------------------------------------------ Its machines: grouped under their Admin
def machines_grouped(w=626, size=52, gap=9):
    """DP03's pick. The seven are never one anonymous waffle and never orphaned from whoever answers
    for them: each Admin's row is drawn to the largest row here, so who governs more is legible at
    the same time as what is wrong. This cell NAMES the machines; the stations above only count them."""
    groups = []
    for a in ADMINS:
        groups.append(col(row(txt(a["name"], 11.5, T["faint"]), sp(),
                              txt(f'{len(a["pcs"])} of {BIGGEST}', 11, T["faint"], mono=True), gap=8,
                              extra=f"width: {BIGGEST * (size + gap) - gap}px;"),
                          dept_pcs(a["pcs"], BIGGEST, size=size, gap=gap), gap=7))
    notes = col(*[row(dot(ST[st], 7), txt(line, 12, T["ink"], 500), gap=9, extra="width: 100%;")
                  for st, line in [("behind", "OPS-06 has been behind since Friday, six attempts."),
                                   ("failing", "OPS-07 keeps budget-2026.xlsx, restricted, in /workers/.")]],
                gap=7, extra=f"width: {w}px;")
    return col(col(*groups, gap=14), notes,
               legend([("Confirmed", ST["confirmed"]), ("Behind", ST["behind"]), ("Out of place", ST["failing"])],
                      "faded slots are machines this Admin does not have"),
               gap=15, extra=f"width: {w}px;")


# ------------------------------------------------------------------ Waiting on you: a reading, never a list
def waiting(w=396):
    return reading_block("Nothing here is ungoverned; two machines need a decision from you.",
                         [("Client PCs", "7", ""), ("Behind", "OPS-06", "warn"),
                          ("Out of place", "OPS-07", "danger"), ("Reports unaddressed", "2", "warn")],
                         "Open the two reports", w=w)


# ------------------------------------------------------------------ DP05: the department at rest
# THE SIGNATURE IS A PINWHEEL: the two big cells sit on a diagonal -- who governs at the top left,
# the day at the bottom right -- with the two narrow ones filling the other corners. No other page
# has it, and it keeps the day wide as settled.
def dp05():
    govern = kcell("Who governs", "R. Mensah, of two", "accent",
                   one_admin(ADMINS[0], ADMINS[1:], 856), w=900, h=316, top=True)
    machines = kcell("Its machines", "one behind, one out of place", "warn",
                     machines_grouped(396, size=46, gap=9), w=440, h=316, top=True)
    waits = kcell("Waiting on you", "two things", "warn", waiting(396), w=440, h=340, top=True)
    today = kcell("Today", "two machines were entered", "warn",
                  dept_day(w=816, lane_h=21, gap_y=9), w=900, h=340, top=True)
    return dept_page("Operations", ["Authority", "Operations"], "Operations",
                     "seven machines, two Admins", "dim",
                     [row(govern, machines, gap=20, align="stretch", extra="flex: none;"),
                      row(waits, today, gap=20, align="stretch", extra="flex: none;")],
                     "DP05 · The department at rest. Who governs draws ONE Admin at full width and names the "
                     "others below — single click swaps who is drawn, double click enters them. Its machines "
                     "names the seven. Nothing here offers to enter anybody; the act appears when you reach for it.",
                     eyebrow("PAGE", "A department — level 2, looking", "a pinwheel"))


# ------------------------------------------------------------------ DP06: Who governs, opened on one Admin
# The fifth structural signature, and it is deliberately inverted: THE READING LEADS, down the left,
# because what this state is about is not a picture of a person -- it is a decision with a price. The
# cost is stated before the act, which is DP04's pick, made structural rather than decorative.
def reading_lane(w=372):
    cost = col(txt("Entering takes their workstation.", 15, T["ink"], 600, extra="line-height: 1.35;"),
               col(*[row(txt(k, 12.5, T["dim"]), sp(), txt(v, 12.5, tone_c(tone, T["ink"]), 500), gap=10,
                         extra=f"width: 100%; padding: 8px 0; border-bottom: 1px solid {T['line']};")
                     for k, v, tone in [("R. Mensah gets", "a red screen", "danger"),
                                        ("They keep", "nothing open", "danger"),
                                        ("You hold it for", "30 minutes", "warn"),
                                        ("Extend", "once, by 15", "warn"),
                                        ("They are told", "it was you", "")]],
                   gap=0, extra=f"width: {w}px;"),
               gap=14, extra=f"width: {w}px;")
    act = col(row(tbtn("Enter WS-OPS-A1", "accent", "lock"), gap=0, extra=f"width: {w}px;"),
              gap=0, extra=f"width: {w}px;")
    # DP04's other pick: the two doors, named. A client PC is not only reachable through its Admin,
    # so the second door is offered here rather than hidden behind the person.
    doors = col(rule(),
                txt("Or go straight to a machine", 12, T["faint"]),
                col(*[row(dot(ST[st], 8), txt(host, 12.5, T["ink"], 500, mono=True),
                          txt(word, 12, T["faint"]), sp(), ic("chev", 13, T["faint"]), gap=9,
                          extra=f"width: {w}px; padding: 7px 0; border-bottom: 1px solid {T['line']};")
                      for host, st, word in [("OPS-01", "confirmed", "in use since 08:12"),
                                             ("OPS-02", "confirmed", "not signed in"),
                                             ("OPS-03", "confirmed", "in use since 09:00"),
                                             ("OPS-06", "behind", "behind, six attempts")]],
                    gap=0, extra=f"width: {w}px;"),
                txt("Entering a machine blocks its worker, not their Admin.", 11.5, T["faint"],
                    extra="line-height: 1.45;"),
                gap=12, extra=f"width: {w}px;")
    return col(cost, act, doors, gap=18, extra=f"width: {w}px;")


def chosen_station(a, w=920):
    head = row(av(a["initials"], "admin", 44, "native"),
               col(txt(a["name"], 16, T["ink"], 600),
                   row(txt(a["host"], 12, T["faint"], mono=True), sicon(a["state"], 13),
                       txt(SESSION_WORD[a["state"]] + " · " + a["when"], 12, T["faint"]), gap=7),
                   gap=3, extra="flex: 1; min-width: 0;"),
               sp(), txt("Esc to go back", 12, T["faint"]),
               gap=13, extra=f"width: {w}px;")
    figs = row(figure("8", "tasks", "one overdue", 34), figure("4", "flows", "one failing", 34),
               figure("2", "pings", "unanswered", 34, "warn"),
               figure("4", "machines", "one behind", 34), gap=48, extra="flex: none;")
    return col(head, rule(), figs, txt(a["told"], 13, T["ink"], 500, extra="line-height: 1.4;"),
               gap=17, extra=f"width: {w}px;")


def dp06():
    lane = kcell("Entering R. Mensah", "the cost, then the act", "danger",
                 reading_lane(372), w=416, h=660, top=True, pad=22)
    hero_ = kcell("R. Mensah", "chosen", "accent", chosen_station(ADMINS[0], 876), w=924, h=308, top=True)
    theirs = kcell("Their machines", "OPS-06 behind", "warn",
                   col(dept_pcs(ADMINS[0]["pcs"], BIGGEST, size=46, gap=9),
                       txt("Four of the seven here; OPS-06 has lost six attempts at 1.4.2.", 12.5,
                           T["ink"], 500, extra="line-height: 1.4; max-width: 400px;"),
                       col(*[row(txt(h_, 12, T["dim"], mono=True), sp(),
                                 txt(v, 11.5, tone_c(tone, T["faint"]), 500), gap=8,
                                 extra=f"width: 396px; padding: 6px 0; border-bottom: 1px solid {T['line']};")
                             for h_, v, tone in [("OPS-01", "1.4.2 confirmed", "ok"),
                                                 ("OPS-02", "1.4.2 confirmed", "ok"),
                                                 ("OPS-03", "1.4.2 confirmed", "ok"),
                                                 ("OPS-06", "retrying 1.4.2", "warn")]],
                           gap=0), gap=13),
                   w=452, h=332, top=True)
    theirday = kcell("Their day", "one was entered", "warn",
                     col(scoped_day(["OPS-01", "OPS-02", "OPS-03", "OPS-06"],
                                    {"OPS-01": (8.2, 17.4), "OPS-03": (9.0, 17.0)}, w=396),
                         legend([("At the PC", T["line2"])], "OPS-02 and OPS-06 not signed in"),
                         txt("Two of their four machines were used today, both all day. Nobody entered "
                             "them but you.", 12.5, T["ink"], 500, extra="line-height: 1.4; max-width: 396px;"),
                         gap=13),
                     w=452, h=332, top=True)
    right = col(hero_, row(theirs, theirday, gap=20, align="stretch", extra="flex: none;"),
                gap=20, extra="flex: none; display: flex; flex-direction: column;")
    return dept_page("Operations", ["Authority", "Operations", "R. Mensah"], "Operations",
                     "choosing whether to enter", "accent",
                     [row(lane, right, gap=20, align="flex-start", extra="flex: none;")],
                     "DP06 · The same page, one Admin opened in place. The reading LEADS this shape because the "
                     "subject is a decision, not a person: the cost is stated before the act. Escape restores "
                     "the four cells exactly. Still level 2 — no lid, no clock, nothing held.",
                     eyebrow("BEHAVIOUR", "Who governs, opened on an Admin", "the reading leads"))


DEPT_PAGE = [("DP05-Department.dc.html", "Department: the page, from the picks", dp05),
             ("DP06-Entering.dc.html", "Department: an Admin opened, the cost first", dp06)]


# ================================================================== DP07-DP08: the answer that comes back
# Pressing Enter does not move the window. It creates the SESSION, and the session appears as a small
# landscape container on the page where it was started -- here, in the cell where R. Mensah was
# standing. Double-clicking that container is what takes the window into level 3. Escape comes back
# out while the session is still held, and the container keeps counting.
#
# There is NO SCREEN STREAMING in the protocol, so the container is a live-state card and never a
# viewport: control.metrics (CPU, memory, idle), the active window, the machine, the countdown, and
# the screenshot Action for a still on demand. Drawing a fake preview would promise what the system
# cannot do.
#
# T04 drew the four answers as modal dialogs. DP04's pick replaced the confirm with a reading, so the
# answers arrive WHERE THE ASK WAS MADE -- the same lane that stated the cost now carries what came
# back. One place, before and after, and no modal anywhere in the level.

def screen_still(w=856, h=214):
    """A picture of what is on their monitor. The user asked for this instead of a metrics card.

    WHAT IT IS TODAY: a STILL, not a feed. `engine/control/actions.py` has a `screenshot` Action and
    `worker_client/executor.py` implements it -- but it saves the PNG on the worker's own disk and
    prints the path. Nothing carries the bytes back. So this drawing is ahead of the system by three
    specific pieces: the Action returning image data rather than a path, a protocol message able to
    carry it, and a refresh the Operator Client asks for. A live feed is a fourth, larger thing.
    The card says how old the picture is for exactly that reason -- an unlabelled image would read as
    live and promise what does not exist."""
    bar = (f'<div style="height: 22px; border-radius: 7px 7px 0 0; background: {T["line"]}; display: flex; '
           f'align-items: center; gap: 6px; padding: 0 9px;">'
           + "".join(f'<span style="width: 8px; height: 8px; border-radius: 999px; background: {c};"></span>'
                     for c in (T["danger"], T["warn"], T["ok"]))
           + f'<span style="font-family: {T["sans"]}; font-size: 10.5px; color: {T["faint"]}; margin-left: 6px;">'
             f'budget-2026.xlsx — Excel</span></div>')
    grid_rows = "".join(
        f'<div style="display: flex; gap: 4px; margin-bottom: 4px;">'
        + "".join(f'<span style="height: 9px; width: {wd}px; border-radius: 2px; background: '
                  f'{T["line2"] if (r == 0) else T["line"]}; opacity: {0.9 if r == 0 else 0.6};"></span>'
                  for wd in (58, 82, 64, 96, 72))
        + '</div>' for r in range(7))
    sheet = (f'<div style="flex: 1; min-width: 0; border-radius: 0 0 7px 7px; background: {T["pane"]}; '
             f'padding: 10px;">{grid_rows}</div>')
    window = (f'<div style="position: absolute; left: 26px; top: 18px; width: {int(w * 0.62)}px; '
              f'height: {h - 52}px; display: flex; flex-direction: column; border-radius: 8px; overflow: hidden; '
              f'box-shadow: 0 10px 26px rgba(0,0,0,0.5);">{bar}{sheet}</div>')
    side = (f'<div style="position: absolute; right: 22px; top: 34px; width: {int(w * 0.24)}px; '
            f'height: {h - 86}px; border-radius: 8px; background: {T["ground"]}; opacity: 0.75;"></div>')
    taskbar = (f'<div style="position: absolute; left: 0; right: 0; bottom: 0; height: 18px; '
               f'background: rgba(0,0,0,0.35); display: flex; align-items: center; gap: 6px; padding: 0 10px;">'
               + "".join(f'<span style="width: 10px; height: 10px; border-radius: 3px; background: {T["line2"]}; '
                         f'opacity: 0.7;"></span>' for _ in range(4)) + '</div>')
    return (f'<div style="position: relative; width: {w}px; height: {h}px; border-radius: 10px; overflow: hidden; '
            f'background: linear-gradient(150deg, #1d2b3a, #121a24); box-shadow: inset 0 0 0 1px {T["line"]};">'
            f'{window}{side}{taskbar}</div>')


def held_card(w=856):
    """The session, as a container: their screen at its own proportions, and beside it who is held,
    for how long, and the way in. No metrics card and no still-button — the picture is the subject."""
    shot_w = 396
    right = w - shot_w - 32
    head = row(av("RM", "admin", 32, "native"),
               col(txt("R. Mensah", 13.5, T["ink"], 600),
                   txt("WS-OPS-A1", 11.5, T["faint"], mono=True), gap=2, extra="flex: 1; min-width: 0;"),
               sp(), ring(0.96, 26, T["danger"], 3),
               txt("28:41 left", 12.5, T["danger"], 600, mono=True),
               gap=10, extra=f"width: {right}px;")
    facts = col(*[row(txt(k, 12, T["dim"]), sp(), txt(v, 12, tone_c(tone, T["ink"]), 500), gap=10,
                      extra=f"width: {right}px; padding: 7px 0; border-bottom: 1px solid {T['line']};")
                  for k, v, tone in [("Ends", "14:50", "warn"),
                                     ("They see", "a red screen", "danger"),
                                     ("The picture", "a still, 12s old", "")]],
                gap=0, extra=f"width: {right}px;")
    foot = row(txt("Double-click to go in", 11.5, T["faint"]), sp(),
               gbtn("Refresh", "arrow", "sm"), tbtn("Leave", "danger", "back", "sm"),
               gap=6, extra=f"width: {right}px;")
    return row(screen_still(shot_w, 214),
               col(head, rule(), facts, sp(), foot, gap=12, extra=f"width: {right}px; height: 214px;"),
               gap=32, align="flex-start", extra=f"width: {w}px;")


def dp07():
    govern = kcell("Who governs", "you hold R. Mensah's workstation", "danger",
                   held_card(856), w=900, h=316, top=True)
    machines = kcell("Its machines", "one behind, one out of place", "warn",
                     machines_grouped(396, size=46, gap=9), w=440, h=316, top=True)
    waits = kcell("Waiting on you", "two things", "warn", waiting(396), w=440, h=340, top=True)
    today = kcell("Today", "two machines were entered", "warn",
                  dept_day(w=816, lane_h=21, gap_y=9), w=900, h=340, top=True)
    return dept_page("Operations", ["Authority", "Operations"], "Operations",
                     "you are holding one workstation", "danger",
                     [row(govern, machines, gap=20, align="stretch", extra="flex: none;"),
                      row(waits, today, gap=20, align="stretch", extra="flex: none;")],
                     "DP07 · The session, held. The window did not move: the big cell becomes the session, "
                     "carrying their screen and the countdown, and double-clicking it is what takes you into "
                     "level 3. THE PICTURE IS A STILL AND SAYS ITS AGE — the screenshot Action writes a PNG on "
                     "the worker and returns a path, so carrying the image back is not built yet, and a live "
                     "feed is a separate Engine capability.",
                     eyebrow("STATE", "A session is a container, not a navigation", "level 2, holding"),
                     status=("holding WS-OPS-A1   28:41 left", "danger"))


# ------------------------------------------------------------------ DP08: when the answer is not yes
def answer_lane(title, tone, sentence, facts, actions, w=300):
    return col(row(ic({"ok": "check", "warn": "warn", "danger": "x"}[tone], 15, T[tone]),
                   txt(title, 13, tone_c(tone), 600), gap=8, extra="width: 100%;"),
               txt(sentence, 13, T["ink"], 600, extra="line-height: 1.35;"),
               col(*[row(txt(k, 12, T["dim"]), sp(), txt(v, 12, tone_c(t, T["ink"]), 500), gap=10,
                         extra=f"width: 100%; padding: 7px 0; border-bottom: 1px solid {T['line']};")
                     for k, v, t in facts], gap=0, extra="width: 100%;"),
               row(*actions, gap=6, extra="width: 100%; flex-wrap: wrap; padding-top: 4px;"),
               gap=13, extra=f"width: {w}px;")


def dp08():
    yes = answer_lane("It was free", "ok", "You hold WS-OPS-A1 for thirty minutes.",
                      [("Started", "14:20", ""), ("Ends", "14:50", "warn"), ("Written to", "the trail", "")],
                      [tbtn("Go in", "accent", "lock", "sm"), gbtn("Leave", "back", "sm")])
    occupied = answer_lane("They are working in it", "warn",
                           "R. Mensah has been signed in since 08:14.",
                           [("Their session", "ends now", "danger"), ("They see", "who took it", ""),
                            ("They reclaim it", "when you leave", "")],
                           [tbtn("End theirs and enter", "danger", "lock", "sm"), gbtn("Cancel", size="sm")])
    su = answer_lane("Another Super User is inside", "danger",
                     "A Super User's session cannot be evicted, by anyone.",
                     [("Holder", "K. Owusu", ""), ("Ends", "12:41 left", "warn"),
                      ("You may", "watch it in Record", "")],
                     [tbtn("Open Record", "accent", "eye", "sm")])
    gone = answer_lane("The machine is not reachable", "danger",
                       "WS-OPS-A1 has not reported since 11:02.",
                       [("Last seen", "11:02", ""), ("Client", "offline", "danger"),
                        ("Nothing", "was blocked", "")],
                       [gbtn("Close", size="sm")])
    def commonality(line, body):
        return col(txt(line, 13, T["ink"], 600, extra="line-height: 1.35;"),
                   txt(body, 12, T["dim"], extra="line-height: 1.5;"), gap=9, extra="width: 404px;")

    cells = [variant("Free", "the ordinary case", yes, 322, 300),
             variant("Below you, occupied", "the only forcing act in the level", occupied, 322, 300),
             variant("A Super User holds it", "un-evictable, by design", su, 322, 300),
             variant("Not reachable", "nobody was blocked", gone, 322, 300),
             variant("Where it lands", "never a modal", commonality(
                 "The answer arrives in the lane that stated the cost.",
                 "You asked in one place and you are answered in that place. Nothing covers the page, "
                 "nothing navigates, and Escape still restores the four cells.", ), 440, 236),
             variant("What it may offer", "one forcing act, at most", commonality(
                 "Only the occupied answer offers to force anything.",
                 "And it names what it costs before it offers it: their session ends now, they are told "
                 "who took it, they reclaim it when you leave.", ), 440, 236),
             variant("What a refusal owes you", "never a dead end", commonality(
                 "A refusal always names somewhere else to go.",
                 "Watch it in Record, ping the holder, or enter a machine directly. A no that leaves you "
                 "with nothing to do is a bug in the answer.", ), 440, 236)]
    return mood("Asking to enter: what comes back",
                "the Engine decides; the lane that stated the cost carries the answer — no modal, no new page",
                cells, brow=eyebrow("BEHAVIOUR", "hierarchy.traverse", "four answers, one place"))


DEPT_PAGE += [("DP07-Held.dc.html", "Department: the session, as a container", dp07),
              ("DP08-Answers.dc.html", "Department: what comes back when you ask", dp08)]
