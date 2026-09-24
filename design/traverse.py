# ================================================================== T01-T06: entering someone else's machine
# The one Hierarchy behaviour with no design. A Super User enters an Admin's workstation (or a PC
# directly); an Admin enters a client PC. The Engine has enforced it since Phase 1. What has never
# been drawn is what the WINDOW becomes.
#
# The settled rule that shapes everything here: THE FRAME NEVER CHANGES COLOUR. So the answer cannot
# be "turn the window amber". It has to be structural.
#
# The proposal, in one line: while you are inside, the sheet grows a HELD BAR across its top, and
# the rail becomes THEIRS. The bar is the lid of the box you are standing in -- everything under it
# belongs to the machine you entered -- and the rail says what you can do in there. Your own
# identity stays at the foot of the rail, because you are still you, and the way out is on the bar,
# in the same place, in every state.
#
#   T01  the decision                -- what you are told before you enter, and what it costs them
#   T02  the four answers            -- free, block-or-end, refused, un-evictable
#   T03  inside (the proposal)       -- the held bar, their rail, what is hidden
#   T04  inside (the alternative)    -- your rail kept, theirs appended: drawn so it can be compared
#   T05  the clock and the ways out  -- running, last minutes, extended, left, expired, evicted
#   T06  assisted access             -- the same lid, deliberately different: no clock, a ceiling, consent

HELD_TONE = "warn"
RAIL_FOOT_INK = "#1E1A2E"          # the frame's own dark, for a notch cut out of the rail


# ------------------------------------------------------------------ the new pieces
def tint(tone, a):
    h = tone_c(tone).lstrip("#")
    return f"rgba({int(h[0:2], 16)}, {int(h[2:4], 16)}, {int(h[4:6], 16)}, {a})"


def badged_av(initials, tone, glyph="lock", size=34):
    """The person whose machine this is, with the state's own glyph notched into the avatar. The
    avatar itself stays neutral (settled rule); the badge is the state, and it carries a word on the
    bar beside it."""
    return (f'<span style="position: relative; display: inline-flex; flex: none;">{av(initials, "admin", size, "native")}'
            f'<span style="position: absolute; right: -5px; bottom: -5px; width: 18px; height: 18px; border-radius: 9px; '
            f'background: {tone_c(tone)}; display: inline-flex; align-items: center; justify-content: center;">'
            f'{ic(glyph, 11, "#15121F")}</span></span>')


def held_bar(lead, title, sub, path, right, tone=HELD_TONE, note="", word="You are inside"):
    """The lid of the box. Full width across the sheet, above the sidebar AND the body, so it reads
    as containing everything under it rather than floating over it. Toned, never a deep slab -- it
    is present for half an hour and must not shout for all of it -- and it always carries the word,
    because a hue on its own is not a sentence."""
    trail = []
    for i, step in enumerate(path):
        last = i == len(path) - 1
        if i:
            trail.append(ic("chev", 11, T[tone] if last else T["faint"]))
        trail.append(txt(step, 11.5, T[tone] if last else T["faint"], 600 if last else 400))
    return col(
        row(lead,
            col(row(txt(title, 13.5, T["ink"], 600), (txt(sub, 12, T["faint"], mono=True) if sub else ""),
                    chip(word, tone, 11, dot=True), gap=9),
                row(*trail, gap=5), gap=2, extra="flex: 1; min-width: 0;"),
            '<span style="flex: 1;"></span>', right,
            gap=12, extra="height: 58px; padding: 0 16px; box-sizing: border-box;"),
        (txt(note, 11.5, T["faint"], extra="padding: 0 16px 10px 62px;") if note else ""),
        gap=0, extra=f"flex: none; background: {tint(tone, 0.22)}; border-bottom: 1px solid {tint(tone, 0.45)};")


def held_sheet(bar, sidebar_html, body_html, side_w=280):
    """The sheet, with the bar inside it. Not a band above the sheet and not a pill floating over
    the body: one surface whose lid names whose machine this is."""
    side = (f'<div style="width: {side_w}px; flex: none; background: {SIDE["native"]}; display: flex; '
            f'flex-direction: column; border-right: 1px solid {T["line"]}; overflow: hidden;">{sidebar_html}</div>')
    main = (f'<div style="flex: 1; min-width: 0; display: flex; flex-direction: column; overflow: hidden; '
            f'background: {T["pane"]};">{body_html}</div>')
    inner = f'<div style="display: flex; flex: 1; min-height: 0;">{side}{main}</div>'
    return (f'<div style="flex: 1; min-width: 0; display: flex; flex-direction: column; margin: 0 8px 0 0;">'
            f'<div style="flex: 1; min-height: 0; display: flex; flex-direction: column; background: {T["pane"]}; '
            f'border-radius: 10px; overflow: hidden; box-shadow: {SHEET_SHADOW};">{bar}{inner}</div></div>')


def clock_block(left, pct, tone=HELD_TONE, extend=True):
    """The countdown, as chrome: a ring, the time in mono, and the two levers that act on it. It
    lives on the bar and nowhere else, so there is one place to look and one place to press."""
    return row(ring(pct, 34, T[tone], 4),
               col(txt(left, 13, T["ink"], 600, mono=True), txt("left", 11, T["faint"]), gap=0),
               (tbtn("Extend", tone, "clock", "sm") if extend else ""),
               tbtn("Leave", "accent", "back", "sm"),
               gap=10, extra="flex: none;")


def rail_head(initials, label):
    """Whose surfaces these are, at the TOP of the rail. Who you are stays at the foot. While you
    are inside, those are two different people -- and that is the whole signal."""
    return col(
        f'<span style="position: relative; width: 36px; height: 36px; border-radius: 11px; background: {T["warn_soft"]}; '
        f'box-shadow: inset 0 0 0 1px {tone_c("warn")}66; display: inline-flex; align-items: center; justify-content: center; '
        f'color: {T["warn"]}; font-family: {T["sans"]}; font-size: 12px; font-weight: 700;">{initials}'
        f'<span style="position: absolute; right: -4px; bottom: -4px; width: 17px; height: 17px; border-radius: 9px; '
        f'background: {RAIL_FOOT_INK}; display: inline-flex; align-items: center; justify-content: center;">'
        f'{ic("lock", 10, T["warn"])}</span></span>',
        txt(label, 9.5, T["warn"], 600, extra="text-align: center; white-space: nowrap;"),
        gap=4, extra="align-items: center;")


def rail_div():
    return '<span style="width: 34px; height: 1px; background: rgba(255,255,255,0.18); margin: 5px 0;"></span>'


def held_rail(active, entries, head=None, foot=("SU", "Super User"), divider_after=None):
    items = []
    if head:
        items.append(rail_head(*head))
        items.append(rail_div())
    for key, label, icon in entries:
        on = key == active
        items.append(
            f'<a href="#{key}" aria-label="{label}" style="display: flex; flex-direction: column; align-items: center; gap: 3px; '
            f'width: 56px; padding: 7px 0 6px; border-radius: 10px; background: {T["frame_wash2"] if on else "transparent"}; '
            f'color: {"#fff" if on else T["frame_dim"]}; text-decoration: none; font-family: {T["sans"]}; font-size: 10.5px; '
            f'font-weight: 500;">{ic(icon, 20, sw=1.6)}<span>{label}</span></a>')
        if divider_after and key == divider_after:
            items.append(rail_div())
    initials, rlabel = foot
    who = col(f'<span style="width: 34px; height: 34px; border-radius: 10px; background: #fff; color: {RAIL_FOOT_INK}; '
              f'display: inline-flex; align-items: center; justify-content: center; font-family: {T["sans"]}; '
              f'font-size: 12px; font-weight: 700;">{initials}</span>',
              txt(rlabel, 10.5, T["frame_dim"], 500, extra="text-align: center; white-space: nowrap;"),
              gap=4, extra="align-items: center;")
    return col(*items, '<span style="flex: 1;"></span>', who, gap=6,
               extra="width: 64px; flex: none; align-items: center; padding: 8px 0 10px; box-sizing: border-box;")


ADMIN_NAV = [("hierarchy", "Hierarchy", "home"), ("tasks", "Tasks", "tasks"), ("flows", "Flows", "flows"),
             ("automation", "Automation", "automation"), ("actions", "Actions", "play"),
             ("assistance", "Assistance", "assistance"), ("reports", "Reports", "reports")]
SU_NAV_T = [("overview", "Overview", "pulse"), ("hierarchy", "Hierarchy", "home"), ("views", "Views", "eye"),
            ("reports", "Reports", "reports"), ("updates", "Updates", "shield"), ("tasks", "Tasks", "tasks"),
            ("flows", "Flows", "flows"), ("assistance", "Assistance", "assistance")]


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


# ------------------------------------------------------------------ T01: the decision
def t01():
    """Before you enter, the card says three things: what you gain in there, what it costs them, and
    how long you have. All three come from data the handlers already return."""
    top = topbar2([IND["rollout"], IND["pings"]], "Go to, do, find")
    rail = held_rail("hierarchy", SU_NAV_T)

    card = popover(
        "R. Mensah", "WS-OPS-A1",
        col(row(sicon("native", 16), txt("At their workstation", 13.5, weight=600),
                '<span style="flex: 1;"></span>', txt("since 08:14", 12, T["faint"]), gap=8),
            row(tbtn("Enter", "accent", "lock"), gbtn("End their session"), gap=8),
            gap=10, extra=f"padding: 12px; border-radius: 12px; background: {T['ground']};"),
        acard("What entering changes",
              cgroup(dfact("automation", "Automation and Actions", "accent", "only here"),
                     dfact("home", "Operations", None, "7 PCs"),
                     dfact("clock", "Thirty minutes", "warn", "extendable"),
                     dfact("lock", "R. Mensah is blocked", "warn", "until you leave"),
                     dfact("shield", "They claim it back when you go"),
                     dfact("reports", "Written to the trail", None, "session.traversed"), gap=9),
              open_=True),
        lead=av("RM", "admin", 36, "native"))

    def admin_card(initials, name, host, status, state="native", sel=False):
        ring_ = f"box-shadow: inset 0 0 0 1px {T['selectline']};" if sel else ""
        return col(row(av(initials, "admin", 34, state),
                       col(txt(name, 14, weight=600), txt(host, 11.5, T["faint"], mono=True),
                           gap=0, extra="flex: 1; min-width: 0;"), gap=10),
                   '<span style="flex: 1;"></span>',
                   row(sicon(state, 14), txt(status, 12.5, T["dim"]), gap=6),
                   gap=8, extra=f"width: 206px; height: 104px; box-sizing: border-box; padding: 13px 14px; "
                                f"border-radius: 14px; background: {T['ground']}; {ring_} flex: none;")

    admins = paged([admin_card("RM", "R. Mensah", "WS-OPS-A1", "At their workstation", "native", sel=True),
                    admin_card("AQ", "A. Quaye", "WS-OPS-A2", "Free", "free")], 0, 1)
    waiting = cgroup(crow(ic("warn", 16, T["danger"]), "Logistics has no Admin", "4 days", "danger",
                          sub="Nobody below you governs it"),
                     crow(ic("shield", 16, T["warn"]), "1.4.3 waits on you", "2 behind", "warn",
                          sub="OPS-06, LOG-02"))
    body = bodywrap(drill(("Everything", False), ("Operations", True)),
                    title_av(dept_glyph(None, "dept", 40), "Operations", "2 Admins, 7 PCs"),
                    admins, '<span style="height: 16px;"></span>',
                    pills2([("Admins", "2"), ("Waiting on you", "2"), ("Trail", "")], "Admins"),
                    row(col(waiting, gap=0, extra=f"width: {BODY_W}px; flex: none;"), lane(card),
                        gap=22, align="flex-start"))
    sh = sheet(sidebar_all(inside=False, sel="A1"), body)
    return page("Entering: the decision", top, rail, sh,
                statusbar("Connected, TLS pinned", "native   no session", "ok"), "native")


# ------------------------------------------------------------------ T02: the four answers
def t02():
    """Asking to enter has four answers and only one of them is a dialog with a lever. The Engine
    decides; the window's whole job is to say which answer came back, naming the person."""
    free = dialog("lock", "accent", "Enter WS-OPS-A1?", "R. Mensah, at their workstation",
                  [dfact("clock", "You get thirty minutes", "warn", "30:00"),
                   dfact("lock", "R. Mensah is blocked until you leave"),
                   dfact("reports", "Written to the trail")],
                  [gbtn("Cancel"), tbtn("Enter", "accent", "lock")])
    force = dialog("warn", "warn", "R. Mensah is working in it", "WS-OPS-A1, since 08:14",
                   [dfact("x", "Their session ends now", "warn"),
                    dfact("monitor", "They see: Super User is in charge of your view"),
                    dfact("shield", "They claim it back the moment you leave")],
                   [gbtn("Cancel"), tbtn("End theirs and enter", "warn", "lock")])
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
    return mood("Entering: the four answers",
                "the Engine decides; the window says which answer came back, and names the person",
                cells, brow=eyebrow("BEHAVIOUR", "hierarchy.traverse", "one dialog, three plain answers"))


# ------------------------------------------------------------------ T03: inside, the proposal
def sidebar_inside(sel="OPS-07"):
    people = [("Kojo", "OPS-01", "native"), ("Efua", "OPS-02", "free"), ("Yaw", "OPS-03", "native"),
              ("Adjoa", "OPS-04", "traversed"), ("Nana", "OPS-05", "native"), ("Kwame", "OPS-06", "free"),
              ("Ama", "OPS-07", "native")]
    return col(sb_head("Operations", False),
               sb_section("This workstation", ""),
               sb_person("R. Mensah", "WS-OPS-A1", "su", "RM", "admin", right=chip("Held", "warn", 10)),
               sb_section("Their client PCs", "7"),
               *[sb_person(n, h, s, sel=(h == sel)) for n, h, s in people],
               sb_legend(), gap=2, extra="flex: 1; min-height: 0;")


def t03():
    top = topbar2([IND["pings"]], "Go to, do, find")
    rail = held_rail("automation", ADMIN_NAV, head=("RM", "inside"))
    bar = held_bar(badged_av("RM", "warn"), "R. Mensah's workstation", "WS-OPS-A1",
                   ["Everything", "Operations", "R. Mensah"], clock_block("21:18", 0.71),
                   note="Everything below this line is theirs. Your own surfaces come back when you leave.")

    events = cgroup(crow(ic("automation", 16, T["dim"]), "Restricted file opened", "3 actions", sub="On any client PC"),
                    crow(ic("automation", 16, T["dim"]), "Payroll flow fails", "1 action", sub="Notify, then retry"),
                    crow(ic("play", 16, T["ok"]), "Disk under 10 %", "2 actions", "ok", sub="Ran 11:04, clean"),
                    crow(ic("play", 16, T["danger"]), "Nightly cleanup", "timeout", "danger", sub="OPS-03, 120 s"))
    card = popover(
        "Ama", "OPS-07",
        col(row(sicon("native", 16), txt("At the PC", 13.5, weight=600), '<span style="flex: 1;"></span>',
                txt("since 08:14", 12, T["faint"]), gap=8),
            row(tbtn("Enter", "accent", "lock", disabled=True), gbtn("Run action", "play"), gap=8),
            note_line("You already hold a session. Leave WS-OPS-A1 first."),
            gap=10, extra=f"padding: 12px; border-radius: 12px; background: {T['ground']};"),
        acard("Names", cgroup(crow(txt("", 1), "R. Mensah calls her", "Ama", right=""),
                              crow(txt("", 1), "You call her", "A. Mensimah", right=""), gap=6),
              summary="theirs, not yours", open_=True),
        lead=av("AM", "worker", 36, "native"))
    body = bodywrap(drill(("Operations", False), ("R. Mensah", False), ("Automation", True)),
                    title_av(dept_glyph(None, "automation", 40), "Automation",
                             "Authored by R. Mensah — you are working as this Admin sees it",
                             right=row(gbtn("New event", "plus", "sm"), gap=6)),
                    pills2([("Events", "4"), ("Actions", "9"), ("Live", "")], "Events"),
                    row(col(events, gap=0, extra=f"width: {BODY_W}px; flex: none;"), lane(card),
                        gap=22, align="flex-start"),
                    pad="16px 28px 22px")
    sh = held_sheet(bar, sidebar_inside("OPS-07"), body)
    return page("Inside an Admin", top, rail, sh,
                statusbar("Connected, TLS pinned", "inside WS-OPS-A1   21:18 left", "warn"), "native")


# ------------------------------------------------------------------ T04: inside, the alternative rail
def t04():
    """The same moment with the other answer to the rail question: you keep your eight and theirs is
    appended under a divider. Ten entries, two authorities in one column, and nothing says which of
    them acts on their machine and which leaves it. Drawn so it can be compared, not argued about."""
    top = topbar2([IND["pings"]], "Go to, do, find")
    rail = held_rail("automation",
                     SU_NAV_T + [("automation", "Automation", "automation"), ("actions", "Actions", "play")],
                     divider_after="assistance")
    bar = held_bar(badged_av("RM", "warn"), "R. Mensah's workstation", "WS-OPS-A1",
                   ["Everything", "Operations", "R. Mensah"], clock_block("21:18", 0.71))
    events = cgroup(crow(ic("automation", 16, T["dim"]), "Restricted file opened", "3 actions", sub="On any client PC"),
                    crow(ic("automation", 16, T["dim"]), "Payroll flow fails", "1 action", sub="Notify, then retry"),
                    crow(ic("play", 16, T["ok"]), "Disk under 10 %", "2 actions", "ok", sub="Ran 11:04, clean"))
    # an annotation, not a UI element: dashed, so it cannot be mistaken for chrome we are proposing
    caution = row(ic("warn", 15, T["warn"]),
                  txt("<b>Why this loses:</b> Overview, Views and Updates are yours, not theirs — "
                      "pressing one walks out of their machine without saying so, and the divider is "
                      "the only thing telling you which half is which.", 12.5, T["warn"], 400,
                      extra="line-height: 1.5;"), gap=9,
                  align="flex-start",
                  extra=f"width: {BODY_W}px; padding: 11px 14px; border-radius: 12px; "
                        f"border: 1px dashed {tint('warn', 0.5)}; box-sizing: border-box;")
    body = bodywrap(drill(("Operations", False), ("R. Mensah", False), ("Automation", True)),
                    title_av(dept_glyph(None, "automation", 40), "Automation", "Authored by R. Mensah"),
                    pills2([("Events", "4"), ("Actions", "9"), ("Live", "")], "Events"),
                    col(caution, '<span style="height: 12px;"></span>', events, gap=0,
                        extra=f"width: {BODY_W}px; flex: none;"),
                    pad="16px 28px 22px")
    sh = held_sheet(bar, sidebar_inside("OPS-07"), body)
    return page("Inside: the alternative rail", top, rail, sh,
                statusbar("Connected, TLS pinned", "inside WS-OPS-A1   21:18 left", "warn"), "native")


# ------------------------------------------------------------------ T05: the clock, and the ways out
def t05():
    def barcell(tone, left, pct, extend=True, note=""):
        bar = held_bar(badged_av("RM", tone, size=30), "R. Mensah's workstation", "WS-OPS-A1",
                       ["Everything", "Operations", "R. Mensah"],
                       clock_block(left, pct, tone, extend), tone=tone, note=note)
        return col(bar, gap=0, extra="width: 100%;")

    def notice(icon_name, tone, line, sub, action):
        return col(f'<span style="width: 46px; height: 46px; border-radius: 14px; background: {T[tone + "_soft"]}; '
                   f'display: inline-flex; align-items: center; justify-content: center;">{ic(icon_name, 22, T[tone])}</span>',
                   txt(line, 14.5, T["ink"], 600, extra="text-align: center;"),
                   txt(sub, 12.5, T["faint"], extra="text-align: center; max-width: 268px; line-height: 1.5;"),
                   action, gap=11,
                   extra="width: 100%; align-items: center; justify-content: center; padding: 6px 0;")

    running = barcell("warn", "21:18", 0.71)
    last = barcell("danger", "4:41", 0.15,
                   note="At zero the Engine ends it. Nothing is saved or lost — you are simply out.")
    extended = col(barcell("warn", "35:00", 0.97), '<span style="height: 16px;"></span>',
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
    theirs = col(row('<span style="flex: 1;"></span>',
                     row(ic("shield", 15, "#fff"), txt("Super User is in charge of your view", 12.5, "#fff", 500),
                         f'<span style="display: inline-flex; align-items: center; padding: 4px 11px; border-radius: 999px; '
                         f'background: rgba(255,255,255,0.18); color: #fff; font-family: {T["sans"]}; font-size: 12.5px; '
                         f'font-weight: 600;">Claim</span>',
                         gap=9, extra="padding: 6px 8px 6px 14px; border-radius: 999px; background: #B92828;"),
                     '<span style="flex: 1;"></span>', gap=0, extra="width: 100%;"),
                 '<span style="height: 14px;"></span>',
                 col(ring(0.71, 62, T["danger"], 5, "21:18"), txt("Read only", 14.5, T["ink"], 600),
                     txt("Until the Super User leaves.", 12.5, T["faint"]), gap=9, extra="align-items: center;"),
                 gap=0, extra="width: 100%; align-items: center;")

    cells = [variant("Running", "the ordinary half hour", running, 1348, 132),
             variant("Under five minutes", "the lid turns; the lever is the same one", last, 1348, 152),
             variant("Extended", "a toast confirms, the trail records it", extended, 1348, 176),
             variant("You left", "your own rail is back", left_, 326, 250),
             variant("Time ran out", "never silent", expired, 326, 250),
             variant("Ended from above", "an Admin, evicted", evicted, 326, 250),
             variant("Meanwhile, on their screen", "the whole window is occupied", theirs, 326, 250)]
    return mood("The clock, and the six ways it ends",
                "one place to look, one place to press — and no ending that happens quietly",
                cells, brow=eyebrow("BEHAVIOUR", "the traversal deadline", "chrome, never a page"))


# ------------------------------------------------------------------ T06: assisted access
def t06():
    """A separate state machine, and it must LOOK separate. The same lid, four differences: accent
    instead of warn, a ceiling instead of a clock, consent instead of eviction, and your own rail
    stays -- because you never left your own machine. If these two ever look alike, this failed."""
    top = topbar2([IND["pings"]], "Go to, do, find")
    rail = held_rail("assistance", SU_NAV_T)

    ceiling = col(*[row(ic("check" if ok else "x", 14, T["ok"] if ok else T["faint"]),
                        txt(label, 12, T["dim"] if ok else T["faint"]), gap=8,
                        extra="height: 26px; padding: 0 16px;")
                    for label, ok in [("Screen, read only", True), ("Workers and common files", True),
                                      ("Control and Actions", False), ("Restricted files", False)]],
                  gap=0, extra="flex: none;")
    right = row(col(txt("By consent", 12.5, T["accent"], 600),
                    txt("either of you can end it", 11, T["faint"]), gap=0),
                tbtn("End help", "accent", "x", "sm"), gap=12)
    bar = held_bar(badged_av("KB", "assist", "assistance"), "Helping K. Boateng", "FIN-02",
                   ["Finance", "K. Boateng"], right, tone="assist", word="Assisting, by consent",
                   note="No clock: assistance ends when one of you ends it, not when time runs out.")

    screen = (f'<div style="height: 430px; border-radius: 14px; background: linear-gradient(135deg, #222B3A, #171E29); '
              f'display: flex; align-items: center; justify-content: center; color: {T["faint"]}; '
              f'font-family: {T["sans"]}; font-size: 13px;">FIN-02, live — read only</div>')
    talk = col(*[row(av("KB" if w != "You" else "SU", "admin", 28, "assisted" if w != "You" else "native"),
                     col(row(txt(w, 12.5, weight=600), txt(t, 11, T["faint"]), gap=7),
                         txt(x, 12.5, extra="line-height: 1.45;"), gap=2, extra="flex: 1;"),
                     gap=10, align="flex-start", extra="padding: 8px 0;")
                 for w, t, x in [("K. Boateng", "11:02", "Payroll export hangs at 40 % since the update."),
                                 ("You", "11:05", "There is a lock file from Monday. Delete it and retry.")]], gap=0)
    composer = row(f'<input type="text" placeholder="Message" aria-label="Message" style="flex: 1; height: 38px; '
                   f'padding: 0 13px; border: 0; border-radius: 10px; background: {T["ground"]}; '
                   f'font-family: {T["sans"]}; font-size: 13.5px; color: {T["ink"]};">', tbtn("Send", "accent"), gap=8)
    side = col(sb_head("Assistance", False), sb_section("Helping", "1"),
               sb_person("K. Boateng", "FIN-02", "assisted", "KB", "admin", sel=True),
               sb_section("What you may reach", ""),
               ceiling,
               sb_section("Offers waiting", "2", False),
               sb_legend(), gap=2, extra="flex: 1; min-height: 0;")
    body = bodywrap(drill(("Finance", False), ("K. Boateng", True)),
                    title_av(av("KB", "admin", 40, "assisted"), "K. Boateng",
                             "Finance — by consent, not by authority",
                             trail=chip("Read only", "accent", 11, dot=True)),
                    row(col(screen, gap=0, extra="flex: 1; min-width: 0;"),
                        col(talk, '<span style="height: 8px;"></span>', composer, gap=0,
                            extra="width: 340px; flex: none;"), gap=20, align="flex-start"),
                    pad="16px 28px 22px")
    sh = held_sheet(bar, side, body)
    return page("Assisted access", top, rail, sh,
                statusbar("Connected, TLS pinned", "assisting FIN-02   no deadline", "ok"), "native")


TRAVERSE = [("T01-Enter.dc.html", "Entering: the decision", t01),
            ("T02-Answers.dc.html", "Entering: the four answers", t02),
            ("T03-Inside.dc.html", "Inside an Admin: the held bar, and their rail", t03),
            ("T04-Inside-Alt.dc.html", "Inside: the alternative rail, for comparison", t04),
            ("T05-Clock.dc.html", "The clock, and the six ways it ends", t05),
            ("T06-Assisted.dc.html", "Assisted access: the same lid, deliberately different", t06)]
