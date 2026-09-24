# ================================================================== T01-T06: a department, and entering an Admin in it
# The first pass at this got the level wrong. Traversing from Super User to Admin starts in a
# DEPARTMENT -- that is where you choose whom to enter -- and a department had never been drawn in
# the language the Overview is drawn in. Falling back to the old sidebar-and-card-strip shell put a
# page from a different design in the middle of this one.
#
# So the department is a PLACE, drawn like the rest of the Super User work: panels on the gradient,
# titles above them on the frame with a generated state phrase beside them, charts before words, no
# sheet, no sidebar, no card strips. Quieter than the Overview, because a department is smaller: one
# structure instead of four -- and the structure is scoped to this department alone.
#
# ITS SIGNATURE IS A COLONNADE OVER A FLOOR: one column per Admin across the top (they are who you
# choose, so they are the subject), one full-width floor under them (the day, every machine here),
# and a full-width ledger at the foot (what waits on you here). No other page has that shape.
#
# Entering an Admin is then not another design -- it is the same place in another STATE. The
# colonnade re-weights when you choose one (T02) and is held when you are inside them (T03). What
# says you are inside is a slim RED lid across the top: red because the occupant is a Super User,
# which is exactly what red means everywhere else in this system, including on the screen of the
# Admin you are standing in.
#
#   T01  the department      -- the colonnade over the floor
#   T02  an Admin chosen     -- the same page, re-weighted and scoped to them, with Enter
#   T03  inside them         -- the same place, held: the red lid, their rail, their automation
#   T04  the four answers    -- free, block-or-end, a peer refused, a Super User un-evictable
#   T05  the clock           -- the lid's three states, and the four ways it ends
#   T06  assisted access     -- the same skeleton, by consent: accent, a ceiling, no clock

LID_RED = "#B92828"
LID_ASSIST = "#0E6E77"


# ------------------------------------------------------------------ the lid: slim, red, one line
def lid_btn(label, icon=None, strong=False):
    bg = "rgba(255,255,255,0.20)" if strong else "transparent"
    return (f'<button type="button" style="display: inline-flex; align-items: center; gap: 6px; height: 26px; '
            f'padding: 0 11px; border: 0; border-radius: 8px; background: {bg}; color: #fff; '
            f'font-family: {T["sans"]}; font-size: 12.5px; font-weight: 600; cursor: pointer; white-space: nowrap;">'
            f'{ic(icon, 14) if icon else ""}{label}</button>')


def lid(icon_name, text, sub, right, bg=LID_RED):
    """One line, 38 px, the full width of the page. It is chrome, not a panel: it says whose machine
    you are standing in and holds the only way out, in the same place in every state."""
    return row(ic(icon_name, 15, "#fff"),
               txt(text, 12.5, "#fff", 600),
               (txt(sub, 12, "rgba(255,255,255,0.72)", mono=True) if sub else ""),
               '<span style="flex: 1;"></span>', right,
               gap=10, extra=f"height: 38px; padding: 0 8px 0 14px; box-sizing: border-box; border-radius: 10px; "
                             f"background: {bg}; flex: none;")


def lid_clock(left, pct, tone="danger"):
    return row(ring(pct, 26, "#fff", 3),
               txt(left + " left", 12.5, "#fff", 600, mono=True),
               lid_btn("Extend", "clock"), lid_btn("Leave", "back", strong=True),
               gap=9, extra="flex: none;")


# ------------------------------------------------------------------ the place, and its people
DEPT = "Operations"
BIGGEST = 4                      # the largest number of PCs one Admin here governs

ADMINS = [
    {"initials": "RM", "name": "R. Mensah", "host": "WS-OPS-A1", "state": "native", "when": "since 08:14",
     "phrase": ("at their workstation", "dim"),
     "pcs": [("OPS-01", "confirmed"), ("OPS-02", "confirmed"), ("OPS-03", "confirmed"), ("OPS-06", "behind")],
     "tasks": [("confirmed", 5), ("behind", 2), ("failing", 1)],
     "flows": [("confirmed", 3), ("failing", 1)],
     "told": "Four machines, and OPS-06 has been behind since Friday."},
    {"initials": "AQ", "name": "A. Quaye", "host": "WS-OPS-A2", "state": "assisted", "when": "since 10:40",
     "phrase": ("helping Finance", "accent"),
     "pcs": [("OPS-04", "confirmed"), ("OPS-05", "confirmed"), ("OPS-07", "failing")],
     "tasks": [("confirmed", 3), ("behind", 1)],
     "flows": [("confirmed", 1)],
     "told": "Three machines, and OPS-07 keeps a restricted file."},
]
SESSION_WORD = {"native": "At their workstation", "free": "Free", "assisted": "Assisting, by consent",
                "traversed": "Entered", "su": "You are inside"}


def dept_day(w=1276, lane_h=16, gap_y=6):
    """The floor: one lane per MACHINE in this department, named as the columns name them, so the
    day and the columns above it are read with the same labels. Amber is an Admin who entered,
    red is you."""
    lanes = [("OPS-01", [("native", 8.2, 12.0), ("native", 13.0, 17.4)]),
             ("OPS-02", []),
             ("OPS-03", [("native", 9.0, 10.3), ("su", 10.3, 11.0), ("native", 11.0, 17.0)]),
             ("OPS-04", [("native", 8.0, 10.3), ("traversed", 10.3, 11.0), ("native", 11.0, 16.0)]),
             ("OPS-05", [("native", 8.5, 17.5)]),
             ("OPS-06", []),
             ("OPS-07", [("native", 8.2, 16.6)])]
    kind = {"native": T["line2"], "traversed": T["warn"], "su": T["danger"]}
    t0, t1, label_w = 8.0, 18.0, 62
    plot = w - label_w - 12
    out = []
    for hour in range(8, 19, 2):
        x = label_w + ((hour - t0) / (t1 - t0)) * plot
        out.append(f'<line x1="{x:.1f}" y1="2" x2="{x:.1f}" y2="{len(lanes) * (lane_h + gap_y) - gap_y + 2}" '
                   f'stroke="{T["line"]}" stroke-width="1"/>')
        out.append(f'<text x="{x:.1f}" y="{len(lanes) * (lane_h + gap_y) + 15}" text-anchor="middle" '
                   f'fill="{T["faint"]}" font-family="{T["mono"]}" font-size="11">{hour:02d}</text>')
    for i, (name, blocks) in enumerate(lanes):
        y = 2 + i * (lane_h + gap_y)
        out.append(f'<text x="0" y="{y + lane_h / 2 + 4}" fill="{T["dim"]}" font-family="{T["mono"]}" '
                   f'font-size="11.5">{name}</text>')
        out.append(f'<rect x="{label_w}" y="{y}" width="{plot}" height="{lane_h}" rx="6" '
                   f'fill="{T["pane"]}" opacity="0.5"/>')
        for state, a, b in blocks:
            bx = label_w + ((a - t0) / (t1 - t0)) * plot
            bw = max(5, ((b - a) / (t1 - t0)) * plot - 2)
            out.append(f'<rect x="{bx:.1f}" y="{y}" width="{bw:.1f}" height="{lane_h}" rx="6" fill="{kind[state]}"/>')
    h = len(lanes) * (lane_h + gap_y) + 20
    return col(f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(out)}</svg>',
               legend([("At the PC", T["line2"]), ("An Admin entered", T["warn"]), ("You entered", T["danger"])],
                      "OPS-02 and OPS-06 were never signed in today"),
               gap=14, extra=f"width: {w}px;")


def station(a, w, slot=46, heroes=None, wide=False, slots=True):
    """One Admin, drawn. Their machine, the PCs they govern (against the largest here, so their size
    reads at the same time as their state), their work, and the one sentence it is making."""
    head = row(av(a["initials"], "admin", 38, "native"),
               col(txt(a["host"], 12.5, T["ink"], 600, mono=True),
                   row(sicon(a["state"], 13), txt(SESSION_WORD[a["state"]] + " · " + a["when"], 12, T["faint"]),
                       gap=6), gap=3, extra="flex: 1; min-width: 0;"),
               gap=12, extra="width: 100%;")
    pcs = col(txt("Governs, against the largest here", 11.5, T["faint"]),
              dept_pcs(a["pcs"], BIGGEST, size=slot, gap=8), gap=10) if slots else ""
    if heroes:
        work = row(*[hero(v, k, s, tone) for v, k, s, tone in heroes], gap=40, extra="flex: none;")
    else:
        bw = min(268, (w - 60) // 2)
        work = row(health_line("Tasks", a["tasks"], w=bw), health_line("Flows", a["flows"], w=bw),
                   gap=24, extra="width: 100%;")
    told = txt(a["told"], 12.5, T["ink"], 500, extra="line-height: 1.4;")
    if wide:
        return col(head, row(pcs, '<span style="width: 52px;"></span>', work, gap=0, align="flex-end",
                             extra="width: 100%;"), told, gap=18, extra=f"width: {w}px;")
    return col(head, pcs, work, told, gap=16, extra=f"width: {w}px;")


def foot_band(sentence, facts, action="", w=1316):
    """The foot of the page: one generated sentence, the facts on the same line, one action. It is a
    reading, so it is words -- but it is one band, not a stack of rows."""
    pairs = row(*[row(txt(k, 12, T["faint"]), txt(v, 12.5, tone_c(tone, T["ink"]), 600), gap=7)
                  for k, v, tone in facts], gap=26, extra="flex: none;")
    return row(txt(sentence, 14, T["ink"], 600, extra="line-height: 1.35; max-width: 520px;"),
               '<span style="flex: 1;"></span>', pairs,
               (tbtn(action[0], action[1], action[2], "sm") if action else ""),
               gap=26, extra=f"width: {w}px;")


def place_page(title, lid_html, crumbs, heading, phrase, tone, bands, note, brow, rail, top,
               status=("native   no session", "ok")):
    """The shell every board here shares: the top bar, the rail, and the page itself drawn straight
    on the gradient. The heading carries the department's own state phrase, in its tone."""
    trail = []
    for i, step in enumerate(crumbs):
        if i:
            trail.append(ic("chev", 12, T["frame_faint"]))
        trail.append(txt(step, 12.5, "#fff" if i == len(crumbs) - 1 else T["frame_faint"],
                         600 if i == len(crumbs) - 1 else 400))
    head = col(row(*trail, gap=6, extra="flex: none;"),
               row(txt(heading, 24, "#fff", 700, extra="letter-spacing: -0.3px;"),
                   txt(phrase, 13, tone_c(tone, T["frame_dim"]), 500),
                   '<span style="flex: 1;"></span>',
                   txt("Wednesday, 14:20", 12.5, T["frame_faint"]),
                   gap=14, extra="width: 100%; flex: none;"),
               gap=5, extra="flex: none;")
    inner = col(brow if brow else "", lid_html if lid_html else "", head, *bands,
                (row(txt(note, 11.5, T["frame_faint"]), gap=0, extra="flex: none;") if note else ""),
                gap=12, extra="flex: 1; min-width: 0; display: flex; flex-direction: column; "
                              "padding: 6px 22px 8px 6px; box-sizing: border-box; overflow: hidden;")
    return page(title, top, rail, inner, statusbar("Connected, TLS pinned", status[0], status[1]), "native")


SU_NAV_T = [("overview", "Overview", "pulse"), ("hierarchy", "Hierarchy", "home"), ("views", "Views", "eye"),
            ("reports", "Reports", "reports"), ("updates", "Updates", "shield"), ("tasks", "Tasks", "tasks"),
            ("flows", "Flows", "flows"), ("assistance", "Assistance", "assistance")]
ADMIN_NAV = [("hierarchy", "Hierarchy", "home"), ("tasks", "Tasks", "tasks"), ("flows", "Flows", "flows"),
             ("automation", "Automation", "automation"), ("actions", "Actions", "play"),
             ("assistance", "Assistance", "assistance"), ("reports", "Reports", "reports")]


def rail_head(initials, label, tone="danger"):
    """Whose surfaces these are, at the TOP of the rail. Who you are stays at the foot. While you
    are inside, those are two different people, and the rail says so without a word of prose."""
    return col(
        f'<span style="position: relative; width: 36px; height: 36px; border-radius: 11px; '
        f'background: {tone_c(tone)}; display: inline-flex; align-items: center; justify-content: center; '
        f'color: #15121F; font-family: {T["sans"]}; font-size: 12px; font-weight: 700;">{initials}</span>',
        txt(label, 9.5, tone_c(tone), 600, extra="text-align: center; white-space: nowrap;"),
        gap=4, extra="align-items: center;")


def held_rail(active, entries, head=None, foot=("SU", "Super User")):
    items = []
    if head:
        items.append(rail_head(*head))
        items.append('<span style="width: 34px; height: 1px; background: rgba(255,255,255,0.18); margin: 5px 0;"></span>')
    for key, label, icon in entries:
        on = key == active
        items.append(
            f'<a href="#{key}" aria-label="{label}" style="display: flex; flex-direction: column; align-items: center; '
            f'gap: 3px; width: 56px; padding: 7px 0 6px; border-radius: 10px; '
            f'background: {T["frame_wash2"] if on else "transparent"}; color: {"#fff" if on else T["frame_dim"]}; '
            f'text-decoration: none; font-family: {T["sans"]}; font-size: 10.5px; font-weight: 500;">'
            f'{ic(icon, 20, sw=1.6)}<span>{label}</span></a>')
    initials, rlabel = foot
    who = col(f'<span style="width: 34px; height: 34px; border-radius: 10px; background: #fff; color: #1E1A2E; '
              f'display: inline-flex; align-items: center; justify-content: center; font-family: {T["sans"]}; '
              f'font-size: 12px; font-weight: 700;">{initials}</span>',
              txt(rlabel, 10.5, T["frame_dim"], 500, extra="text-align: center; white-space: nowrap;"),
              gap=4, extra="align-items: center;")
    return col(*items, '<span style="flex: 1;"></span>', who, gap=6,
               extra="width: 64px; flex: none; align-items: center; padding: 8px 0 10px; box-sizing: border-box;")


# ------------------------------------------------------------------ T01: the department
def t01():
    """Four cells, and the widths do the ranking: the two Admins share the top because neither is
    chosen yet, and the day takes the wide cell below because it is the one thing that says what
    actually happened here. Nothing is a full-width band any more."""
    top = topbar2([IND["rollout"], IND["pings"]], "Go to, do, find")
    rail = held_rail("hierarchy", SU_NAV_T)
    cols = row(kcell(ADMINS[0]["name"], *ADMINS[0]["phrase"], station(ADMINS[0], 626), w=670, h=330, top=True),
               kcell(ADMINS[1]["name"], *ADMINS[1]["phrase"], station(ADMINS[1], 626), w=670, h=330, top=True),
               gap=20, align="stretch", extra="flex: none;")
    floor = kcell("Today, here", "two machines were entered", "warn",
                  dept_day(w=816), w=900, h=330, top=True)
    waits = kcell("What waits on you here", "two things", "warn",
                  reading_block("Nothing here is ungoverned; two machines need a decision.",
                                [("Client PCs", "7", ""), ("Behind", "OPS-06", "warn"),
                                 ("Out of place", "OPS-07", "danger"), ("Reports", "2", "warn")],
                                "Open reports", w=396),
                  w=440, h=330, top=True)
    return place_page("Operations", "", ["Everything", "Operations"], "Operations",
                      "one Admin is away helping Finance", "accent",
                      [cols, row(floor, waits, gap=20, align="stretch", extra="flex: none;")],
                      "T01 · The department at rest: two Admins, the day they share, and what waits on you. "
                      "A column opens an Admin; a slot inside one opens that client PC.",
                      eyebrow("PAGE", "A department — where you choose an Admin", "four cells, two doors"),
                      rail, top)


# ------------------------------------------------------------------ T02: an Admin chosen
def t02():
    """One level, as on the Overview: the column you pick grows WHERE IT IS, the other quietens, and
    the two bands beneath re-scope to the person rather than the department."""
    top = topbar2([IND["rollout"], IND["pings"]], "Go to, do, find")
    rail = held_rail("hierarchy", SU_NAV_T)
    chosen = kcell("R. Mensah", "chosen · Esc to go back", "accent",
                   station(ADMINS[0], 856, slot=54,
                           heroes=[("8", "tasks", "one overdue", None), ("4", "flows", "one failing", None),
                                   ("2", "pings", "unanswered", "warn")]),
                   w=900, h=330, top=True)
    other = kcell(ADMINS[1]["name"], "still there", "dim",
                  col(row(av("AQ", "admin", 32, "native"),
                          col(txt("WS-OPS-A2", 12, T["faint"], mono=True),
                              txt("Assisting Finance", 11.5, T["faint"]), gap=2), gap=10),
                      dept_pcs(ADMINS[1]["pcs"], BIGGEST, size=34, gap=7),
                      col(health_line("Tasks", ADMINS[1]["tasks"], w=340),
                          health_line("Flows", ADMINS[1]["flows"], w=340), gap=12, extra="opacity: 0.55;"),
                      txt("Three machines, quiet.", 12, T["faint"]), gap=16, extra="width: 396px;"),
                  w=440, h=330, top=True)
    day = kcell("Their day", "you entered once", "warn",
                col(scoped_day(["OPS-01", "OPS-02", "OPS-03", "OPS-06"],
                               {"OPS-01": (9.0, 16.4), "OPS-03": (10.3, 11.0)}, w=580),
                    txt("You were in OPS-03 for forty minutes this morning.", 12.5, T["ink"], 500), gap=14),
                w=670, h=330, top=True)
    entering = kcell("Entering", "thirty minutes, and they are blocked", "warn",
                     reading_block("Entering takes R. Mensah's workstation until you leave.",
                                   [("You get", "Automation and Actions", "accent"),
                                    ("You get", "Operations, as they see it", ""),
                                    ("They get", "a red screen, and Claim", "danger"),
                                    ("Time", "30 minutes, extendable", "warn")],
                                   "Enter WS-OPS-A1", w=600),
                     w=670, h=330, top=True)
    return place_page("Operations — an Admin chosen", "", ["Everything", "Operations", "R. Mensah"],
                      "Operations", "R. Mensah governs four of the seven", "dim",
                      [row(chosen, other, gap=20, align="stretch", extra="flex: none;"),
                       row(day, entering, gap=20, align="stretch", extra="flex: none;")],
                      "T02 · The same page, re-weighted. The chosen column grows where it stands, the other "
                      "quietens rather than leaving, and the floor re-scopes to the person. One level only.",
                      eyebrow("BEHAVIOUR", "choosing an Admin", "the colonnade re-weights, it does not navigate"),
                      rail, top)


# ------------------------------------------------------------------ T03: inside them
def automation_ladder(rows_, w=1276):
    """Their automation, which is the whole reason a Super User enters an Admin at all: one line per
    event, its actions drawn as the segments hanging off it, coloured by what happened last. It
    answers 'which of their automations is healthy' without reading a word."""
    label_w, lane_h, gap_y, pad = 210, 26, 12, 8
    out = []
    for i, (name, when, actions) in enumerate(rows_):
        y = i * (lane_h + gap_y)
        out.append(f'<text x="0" y="{y + 17}" fill="{T["ink"]}" font-family="{T["sans"]}" font-size="12.5">{name}</text>')
        out.append(f'<text x="{label_w - 14}" y="{y + 17}" text-anchor="end" fill="{T["faint"]}" '
                   f'font-family="{T["mono"]}" font-size="11">{when}</text>')
        x = label_w
        for label, state in actions:
            aw = 16 + len(label) * 6.6
            out.append(f'<rect x="{x:.1f}" y="{y}" width="{aw:.1f}" height="{lane_h}" rx="9" '
                       f'fill="{ST[state]}" opacity="{0.9 if state != "quiet" else 0.5}"/>')
            out.append(f'<text x="{x + aw / 2:.1f}" y="{y + 17}" text-anchor="middle" fill="{CHART_BG}" '
                       f'font-family="{T["sans"]}" font-size="11.5" font-weight="500">{label}</text>')
            x += aw + pad
    h = len(rows_) * (lane_h + gap_y)
    return col(f'<svg width="{w}" height="{h}" viewBox="0 0 {w} {h}">{"".join(out)}</svg>',
               legend([("Ran clean", ST["confirmed"]), ("Retried", ST["behind"]), ("Failed or timed out", ST["failing"])]),
               gap=14, extra=f"width: {w}px;")


def t03():
    """Four cells again, and the weight has moved: whose machine this is is said by the lid and the
    rail, so the person takes the narrow cell and THEIR AUTOMATION takes the wide one -- it is the
    thing that exists nowhere else in a Super User's window, and the reason you came in."""
    top = topbar2([IND["pings"]], "Go to, do, find")
    rail = held_rail("automation", ADMIN_NAV, head=("RM", "inside"))
    bar = lid("shield", "You are inside R. Mensah", "WS-OPS-A1", lid_clock("21:18", 0.71))
    held = ADMINS[0] | {"state": "su", "when": "you entered 14:12"}
    who = kcell("R. Mensah", "blocked while you are in", "danger",
                station(held, 396, slots=False), w=440, h=310, top=True)
    auto = kcell("Their automation", "one failed last night", "danger",
                 automation_ladder([("Restricted file opened", "11:41", [("Notify Admin", "confirmed"),
                                                                        ("Lock folder", "confirmed"),
                                                                        ("Report", "confirmed")]),
                                    ("Payroll flow fails", "10:52", [("Notify", "confirmed"), ("Retry", "behind")]),
                                    ("Disk under 10 %", "11:04", [("Clear temp", "confirmed"), ("Report", "confirmed")]),
                                    ("Nightly cleanup", "02:00", [("Archive", "confirmed"), ("Prune", "failing")])],
                                   w=816),
                 w=900, h=310, top=True)
    machines = kcell("Their client PCs", "one behind", "warn",
                     col(dept_pcs(ADMINS[0]["pcs"], BIGGEST, size=58, gap=10),
                         row(*[hero(v, k, s, tone) for v, k, s, tone in
                               [("8", "tasks", "one overdue", None), ("4", "flows", "one failing", None),
                                ("2", "pings", "unanswered", "warn")]], gap=40, extra="flex: none;"),
                         txt("OPS-06 is still retrying 1.4.2; the other three confirmed on Tuesday.",
                             12.5, T["ink"], 500, extra="line-height: 1.4;"),
                         gap=20, extra="width: 596px;"),
                     w=670, h=310, top=True)
    only = kcell("Only in here", "the reason you entered", "accent",
                 reading_block("Automation and Actions exist nowhere else in your window.",
                               [("Events", "4", ""), ("Actions", "9", ""),
                                ("Last run", "11:04, clean", "ok"), ("Left of your time", "21:18", "danger")],
                               "Run an action", w=596),
                 w=670, h=310, top=True)
    return place_page("Inside R. Mensah", bar, ["Everything", "Operations", "R. Mensah"],
                      "Operations", "as R. Mensah sees it", "danger",
                      [row(who, auto, gap=20, align="stretch", extra="flex: none;"),
                       row(machines, only, gap=20, align="stretch", extra="flex: none;")],
                      "T03 · The same place, held. Red because the occupant is a Super User — the same red "
                      "R. Mensah's own screen is showing. The rail is theirs; you are still you, at its foot.",
                      eyebrow("STATE", "traversed into an Admin", "the place does not change, its state does"),
                      rail, top, status=("inside WS-OPS-A1   21:18 left", "danger"))


# ------------------------------------------------------------------ T04: the four answers
def dfact(icon, text, tone=None, tail=""):
    t = txt(tail, 12, T["faint"], mono=True) if tail else ""
    return row(ic(icon, 14, tone_c(tone, T["faint"])),
               txt(text, 12.5, tone_c(tone) if tone else T["dim"], 500 if tone else 400),
               '<span style="flex: 1;"></span>', t, gap=9, extra="width: 100%;")


def dialog(icon_name, tone, title, sub, facts, actions, w=580):
    head = row(f'<span style="width: 38px; height: 38px; border-radius: 12px; background: {T[tone + "_soft"]}; '
               f'display: inline-flex; align-items: center; justify-content: center; flex: none;">{ic(icon_name, 19, T[tone])}</span>',
               col(txt(title, 15, T["ink"], 600), txt(sub, 12, T["faint"], mono=True) if sub else "",
                   gap=2, extra="flex: 1; min-width: 0;"), gap=12)
    return col(head, col(*facts, gap=9, extra="width: 100%;"),
               row('<span style="flex: 1;"></span>', *actions, gap=8, extra="width: 100%;"),
               gap=16, extra=f"width: {w}px; box-sizing: border-box; padding: 20px; border-radius: 16px; "
                             f"background: {T['pane']}; box-shadow: 0 24px 60px rgba(0,0,0,0.55), 0 0 0 1px {T['line']}; flex: none;")


def t04():
    free = dialog("lock", "accent", "Enter WS-OPS-A1?", "R. Mensah, at their workstation",
                  [dfact("clock", "You get thirty minutes", "warn", "30:00"),
                   dfact("shield", "Their screen turns red until you leave", "danger"),
                   dfact("reports", "Written to the trail")],
                  [gbtn("Cancel"), tbtn("Enter", "accent", "lock")])
    force = dialog("warn", "danger", "R. Mensah is working in it", "WS-OPS-A1, since 08:14",
                   [dfact("x", "Their session ends now", "danger"),
                    dfact("monitor", "They see: Super User is in charge of your view"),
                    dfact("shield", "They claim it back the moment you leave")],
                   [gbtn("Cancel"), tbtn("End theirs and enter", "danger", "lock")])
    peer = dialog("x", "danger", "You cannot enter OPS-04", "A. Quaye is inside it",
                  [dfact("user", "A peer holds this session", "danger"),
                   dfact("x", "No rights to block a horizontal session"),
                   dfact("ping", "Ask them to leave, or wait")],
                  [gbtn("Close"), tbtn("Ping A. Quaye", "accent", "ping")])
    su = dialog("shield", "danger", "You cannot enter OPS-07", "Another Super User is inside",
                [dfact("shield", "A Super User's session is un-evictable", "danger"),
                 dfact("clock", "It ends when they leave, or at their deadline", None, "12:41"),
                 dfact("eye", "You can watch it in Views")],
                [gbtn("Close"), tbtn("Open Views", "accent", "eye")])
    cells = [variant("Free", "the ordinary case", free, 660, 306),
             variant("Below you, occupied", "block-or-end: the only forcing dialog", force, 660, 306),
             variant("A peer holds it", "hard refusal, no force offered", peer, 660, 306),
             variant("A Super User holds it", "un-evictable, by design", su, 660, 306)]
    return mood("Asking to enter: the four answers",
                "the Engine decides; the window says which answer came back, and names the person",
                cells, brow=eyebrow("BEHAVIOUR", "hierarchy.traverse", "one dialog, three plain answers"))


# ------------------------------------------------------------------ T05: the clock, and the ways out
def t05():
    def lidcell(left, pct, bg=LID_RED, sub="WS-OPS-A1", text="You are inside R. Mensah"):
        return col(lid("shield", text, sub, lid_clock(left, pct), bg=bg), gap=0, extra="width: 100%;")

    def notice(icon_name, tone, line, sub, action):
        return col(f'<span style="width: 44px; height: 44px; border-radius: 14px; background: {T[tone + "_soft"]}; '
                   f'display: inline-flex; align-items: center; justify-content: center;">{ic(icon_name, 21, T[tone])}</span>',
                   txt(line, 14, T["ink"], 600, extra="text-align: center;"),
                   txt(sub, 12.5, T["faint"], extra="text-align: center; max-width: 262px; line-height: 1.5;"),
                   action, gap=10,
                   extra="width: 100%; align-items: center; justify-content: center; padding: 4px 0;")

    running = lidcell("21:18", 0.71)
    last = col(lidcell("4:41", 0.15), '<span style="height: 10px;"></span>',
               txt("Under five minutes the ring is all that changes. At zero the Engine ends the session; "
                   "nothing is saved or lost, you are simply out.", 12, T["faint"], extra="line-height: 1.5;"),
               gap=0, extra="width: 100%;")
    extended = col(lidcell("35:00", 0.97), '<span style="height: 12px;"></span>',
                   toast("Extended to 15:20 · second extension", "ok"), gap=0, extra="width: 100%;")
    left_ = notice("check", "ok", "You left WS-OPS-A1",
                   "R. Mensah has their workstation back, and your own rail is up again.",
                   row(tbtn("Enter again", "accent", "lock", "sm"), gap=6))
    expired = notice("clock", "warn", "Your thirty minutes ran out",
                     "The Engine ended it at 15:20. Nothing of theirs is still on screen.",
                     row(tbtn("Enter again", "accent", "lock", "sm"), gbtn("See the trail", "reports", "sm"), gap=6))
    evicted = notice("shield", "danger", "The Super User ended your session",
                     "You were inside OPS-01. It went back to Kojo at 11:42.",
                     row(gbtn("See the trail", "reports", "sm"), gap=6))
    theirs = col(lid("shield", "Super User is in charge of your view", "",
                     row(txt("21:18", 12.5, "#fff", 600, mono=True), lid_btn("Claim", "lock", strong=True), gap=9)),
                 '<span style="height: 12px;"></span>',
                 txt("The same red, on their side of it. Their whole window is held, so the lid is all "
                     "they get and Claim is the only lever on it.", 12, T["faint"], extra="line-height: 1.5;"),
                 gap=0, extra="width: 100%;")

    states = col(running, '<span style="height: 16px;"></span>', last, gap=0, extra="width: 100%;")
    endings = col(*[row(ic(i, 16, T[t]),
                        col(txt(line, 12.5, T["ink"], 600), txt(sub, 11.5, T["faint"], extra="line-height: 1.45;"),
                            gap=2, extra="flex: 1; min-width: 0;"),
                        gap=10, align="flex-start",
                        extra=f"width: 100%; padding: 10px 0; border-bottom: 1px solid {T['line']};")
                    for i, t, line, sub in
                    [("check", "ok", "You left", "Their workstation goes back to them; your own rail returns."),
                     ("clock", "warn", "Time ran out", "The Engine ends it at zero and says so — never silently."),
                     ("shield", "danger", "Ended from above", "Only to an Admin: a Super User's session cannot be evicted."),
                     ("power", "dim", "The link dropped", "The session stands until its deadline; you rejoin into it.")]],
                 gap=0, extra="width: 100%;")

    cells = [variant("Running, and the last five minutes", "the ring is all that changes", states, 900, 236),
             variant("What they see", "the same red, from under it", theirs, 440, 236),
             variant("Extended", "a toast confirms; the trail records it", extended, 670, 286),
             variant("How it ends", "four ways, none of them quiet", endings, 670, 286)]
    return mood("The lid, and the four ways it ends",
                "one place to look, one place to press — and no ending that happens quietly",
                cells, brow=eyebrow("CHROME", "the traversal deadline", "38 px, one line, never a panel"))


# ------------------------------------------------------------------ T06: assisted access
def t06():
    """A separate state machine, and it has to LOOK separate while using the same skeleton: teal
    instead of red, a ceiling instead of a clock, consent instead of eviction, and your own rail
    stays -- because you never left your machine."""
    top = topbar2([IND["pings"]], "Go to, do, find")
    rail = held_rail("assistance", SU_NAV_T)
    bar = lid("assistance", "Helping K. Boateng, by consent", "FIN-02",
              row(txt("no deadline", 12, "rgba(255,255,255,0.72)"), lid_btn("End help", "x", strong=True), gap=9),
              bg=LID_ASSIST)

    guest = {"initials": "KB", "name": "K. Boateng", "host": "FIN-02", "state": "assisted", "when": "since 11:02",
             "phrase": ("asked for help", "accent"),
             "pcs": [("FIN-01", "confirmed"), ("FIN-02", "behind"), ("FIN-03", "confirmed")],
             "tasks": [("confirmed", 2), ("behind", 1)], "flows": [("confirmed", 2), ("failing", 1)],
             "told": "Their payroll flow has hung since the update."}
    screen = kcell("Their screen", "read only, while they watch", "accent",
                   col(f'<div style="width: 816px; height: 172px; border-radius: 14px; '
                       f'background: linear-gradient(135deg, #222B3A, #171E29); display: flex; align-items: center; '
                       f'justify-content: center; color: {T["faint"]}; font-family: {T["sans"]}; font-size: 13px;">'
                       f'FIN-02, live</div>',
                       txt("They see everything you do, and either of you can end it.",
                           12.5, T["ink"], 500), gap=16, extra="width: 816px;"),
                   w=900, h=310, top=True)

    def gate(label, ok):
        return row(ic("check" if ok else "x", 15, T["ok"] if ok else T["faint"]),
                   txt(label, 12.5, T["dim"] if ok else T["faint"]),
                   '<span style="flex: 1;"></span>',
                   txt("allowed" if ok else "closed", 11.5, T["ok"] if ok else T["faint"], 600),
                   gap=10, extra=f"width: 396px; padding: 9px 0; border-bottom: 1px solid {T['line']};")
    ceiling = kcell("What you may reach", "two of four", "accent",
                    col(gate("Their screen, read only", True), gate("Workers and common files", True),
                        gate("Control and Actions", False), gate("Restricted files", False),
                        txt("The ceiling is theirs to set, and it does not widen while you are in it.",
                            12.5, T["ink"], 500, extra="line-height: 1.45;"), gap=10, extra="width: 396px;"),
                    w=440, h=310, top=True)
    talk = kcell("The channel", "two messages", "dim",
                 col(*[row(av("SU" if w_ == "You" else "KB", "admin", 28, "native"),
                           col(row(txt(w_, 12.5, T["ink"], 600), txt(t_, 11, T["faint"]), gap=7),
                               txt(x_, 12.5, T["dim"], extra="line-height: 1.45;"), gap=2, extra="flex: 1;"),
                           gap=10, align="flex-start", extra="width: 100%; padding: 4px 0;")
                       for w_, t_, x_ in [("K. Boateng", "11:02", "Payroll export hangs at 40 % since the update."),
                                          ("You", "11:05", "There is a lock file from Monday. Delete it and retry.")]],
                     row(f'<input type="text" placeholder="Message" aria-label="Message" style="flex: 1; height: 36px; '
                         f'padding: 0 13px; border: 0; border-radius: 10px; background: {T["pane"]}; '
                         f'font-family: {T["sans"]}; font-size: 13px; color: {T["ink"]};">',
                         tbtn("Send", "accent", size="sm"), gap=8, extra="width: 100%;"),
                     gap=12, extra="width: 596px;"),
                 w=670, h=310, top=True)
    theirs = kcell("K. Boateng", "Finance · asked for help", "accent",
                   station(guest, 596, slot=42), w=670, h=310, top=True)
    return place_page("Assisted access", bar, ["Finance", "K. Boateng"], "Finance",
                      "you are a guest here, not an authority", "accent",
                      [row(screen, ceiling, gap=20, align="stretch", extra="flex: none;"),
                       row(theirs, talk, gap=20, align="stretch", extra="flex: none;")],
                      "T06 · The same skeleton, deliberately unlike the one beside it: teal, a ceiling instead "
                      "of a clock, no eviction, and your own rail kept — you never left your machine.",
                      eyebrow("STATE", "assisted access", "a separate state machine, and it looks it"),
                      rail, top, status=("assisting FIN-02   no deadline", "ok"))


TRAVERSE = [("T01-Department.dc.html", "A department: the colonnade over the floor", t01),
            ("T02-Admin.dc.html", "An Admin chosen: the same page, re-weighted", t02),
            ("T03-Inside.dc.html", "Inside an Admin: the same place, held", t03),
            ("T04-Answers.dc.html", "Asking to enter: the four answers", t04),
            ("T05-Clock.dc.html", "The lid, and the four ways it ends", t05),
            ("T06-Assisted.dc.html", "Assisted access: the same skeleton, by consent", t06)]
