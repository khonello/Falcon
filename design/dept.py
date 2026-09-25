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


# ------------------------------------------------------------------ Who governs: two stations, side by side
def mini_station(a, w=300, slot=30):
    """DP02's Station, at column width: who they are, the machine they sit at, the state word, and a
    quiet cluster of the slots they answer for. The slots here are a HEALTH GLYPH -- how many, and
    are they well. Which machine, and what is wrong with it, is the next cell's job."""
    head = row(av(a["initials"], "admin", 34, "native"),
               col(txt(a["name"], 13, T["ink"], 600),
                   txt(a["host"], 11.5, T["faint"], mono=True), gap=2,
                   extra="flex: 1; min-width: 0;"),
               gap=10, extra="width: 100%;")
    state = row(sicon(a["state"], 13), txt(SESSION_WORD[a["state"]], 12, T["dim"]),
                txt(a["when"], 11.5, T["faint"], mono=True), gap=6, extra="width: 100%;")
    govern = col(txt(f'Answers for {len(a["pcs"])}', 11.5, T["faint"]),
                 dept_pcs(a["pcs"], BIGGEST, size=slot, gap=6), gap=7)
    work = row(health_line("Tasks", a["tasks"], w=(w - 24) // 2),
               health_line("Flows", a["flows"], w=(w - 24) // 2), gap=24, extra="width: 100%;")
    told = txt(STATION_LINE[a["initials"]], 12, T["ink"], 500, extra="line-height: 1.4;")
    return col(head, state, rule(), govern, work, told, gap=12, extra=f"width: {w}px;")


def who_governs(w=626):
    half = (w - 26) // 2
    return row(mini_station(ADMINS[0], half), mini_station(ADMINS[1], half),
               gap=26, align="flex-start", extra=f"width: {w}px;")


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
def dp05():
    govern = kcell("Who governs", "one Admin is away helping Finance", "accent",
                   who_governs(626), w=670, h=308, top=True)
    machines = kcell("Its machines", "one behind, one out of place", "warn",
                     machines_grouped(626), w=670, h=308, top=True)
    today = kcell("Today", "two machines were entered", "warn",
                  dept_day(w=816, lane_h=21, gap_y=9), w=900, h=340, top=True)
    waits = kcell("Waiting on you", "two things", "warn", waiting(396), w=440, h=340, top=True)
    return dept_page("Operations", ["Everything", "Operations"], "Operations",
                     "seven machines, two Admins", "dim",
                     [row(govern, machines, gap=20, align="stretch", extra="flex: none;"),
                      row(today, waits, gap=20, align="stretch", extra="flex: none;")],
                     "DP05 · The department at rest, from the mood-board picks. Double-click a cell to open it "
                     "where it stands; double-click an Admin, or a single machine, to go into that place. "
                     "Nothing here offers to enter anybody yet — the act appears when you reach for it.",
                     eyebrow("PAGE", "A department — level 2, looking", "an equal pair over a split"))


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
    return dept_page("Operations", ["Everything", "Operations", "R. Mensah"], "Operations",
                     "choosing whether to enter", "accent",
                     [row(lane, right, gap=20, align="flex-start", extra="flex: none;")],
                     "DP06 · The same page, one Admin opened in place. The reading LEADS this shape because the "
                     "subject is a decision, not a person: the cost is stated before the act. Escape restores "
                     "the four cells exactly. Still level 2 — no lid, no clock, nothing held.",
                     eyebrow("BEHAVIOUR", "Who governs, opened on an Admin", "the reading leads"))


DEPT_PAGE = [("DP05-Department.dc.html", "Department: the page, from the picks", dp05),
             ("DP06-Entering.dc.html", "Department: an Admin opened, the cost first", dp06)]
