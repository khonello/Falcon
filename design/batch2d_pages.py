# ================================================================== RC04, RO04: Record and Rollout, redone for reading
# The user, 27 Sep 2026: "I don't like the rollout and record designs. Especially: the lever; attempts; who was
# where, today (this is not easy to parse, don't get too hung up on it [being] nice ... it's actually going to be
# used and must be easily parsed)."
#
# The rule this adds to PATTERNS.md: WHEN A THING WILL BE READ TO ACT ON, WRITE IT. A card per fact, a sentence per
# card, the one act on the same card. No lanes to decode, no ticks to count, no form to fill before acting.

def entry_card(initials, role, sentence, detail, right="", tone=None, now=False):
    ring = f"box-shadow: inset 0 0 0 1.5px {T[tone]};" if now and tone else ""
    return row(av(initials, role, 32),
               col(txt(sentence, 13, T["ink"], 600), txt(detail, 11.5, T["faint"]), gap=2, extra="min-width: 0;"),
               sp(), txt(right, 12, tone_c(tone, T["faint"]), 600) if right else "", gap=12,
               extra=f"width: 100%; box-sizing: border-box; padding: 12px 14px; border-radius: 14px; background: {T['pane']}; {ring}")


def stall_card(slot, sentence, detail, act, tone="warn"):
    return row(slot, col(txt(sentence, 13, T["ink"], 600), txt(detail, 11.5, T["faint"], extra="line-height: 1.4;"), gap=3,
                         extra="min-width: 0; flex: 1;"),
               act, gap=16, extra=f"width: 100%; box-sizing: border-box; padding: 14px 16px; border-radius: 14px; background: {T['pane']};")


# ------------------------------------------------------------------ RC04: Record
def rc04():
    entered = col(
        entry_card("SU", "admin", "You are inside WS-OPS-A1, R. Mensah's workstation", "since 14:20 · R. Mensah is blocked until you leave",
                   "now", "danger", now=True),
        entry_card("AQ", "admin", "A. Quaye is helping Finance on WS-FIN-A1", "since 10:40 · by K. Boateng's consent", "now", "accent"),
        entry_card("RM", "admin", "R. Mensah entered OPS-04", "10:02 – 10:22 · 20 minutes · Adjoa was blocked", "20 min"),
        txt("Everyone else stayed at their own machine today.", 11.5, T["faint"], extra="padding-top: 2px;"),
        gap=9, extra="width: 856px;")
    trail = col(*[row(txt(t, 11, T["faint"], mono=True, extra="width: 44px; flex: none;"), ic(i, 15, T[tn] if tn else T["dim"]),
                      txt(w_, 12.5, T["ink"] if tn else T["dim"], 500 if tn else 400), sp(), txt(who_, 11, T["faint"]), gap=10,
                      extra=f"width: 100%; padding: 8px 0; border-bottom: 1px solid {T['line']};")
                  for t, i, w_, who_, tn in [("14:20", "lock", "You entered WS-OPS-A1", "you", "danger"),
                                             ("11:45", "check", "A violation was marked addressed", "R. Mensah", None),
                                             ("11:41", "shield", "A restricted file turned up on OPS-07", "system", "danger"),
                                             ("10:40", "assistance", "A. Quaye began helping Finance", "A. Quaye", "accent"),
                                             ("10:02", "lock", "R. Mensah entered OPS-04 for 20 minutes", "R. Mensah", None),
                                             ("09:11", "warn", "A hostname did not match on OPS-05", "system", "warn")]],
                gap=0, extra="width: 856px;")
    views = col(thing_card("eye", "ok", "Listener report, channel 14", "HR · addressed by M. Osei, Mon 09:12", "addressed"),
                thing_card("shield", "danger", "A restricted file on OPS-07", "Operations · seen, not addressed", "open", "danger"),
                row(ic("eye", 12, T["faint"]), txt("Who addressed what is yours alone; it is never routed.", 10.5, T["faint"]), gap=6),
                gap=9, extra="width: 396px;")
    place = col(txt("Two things are out of place right now.", 14, T["ink"], 600, extra="line-height: 1.35;"),
                thing_card("file", "danger", "budget-2026.xlsx", "Restricted · on OPS-07, among Workers files"),
                thing_card("warn", "warn", "A hostname did not match", "OPS-05 · logged, not addressed"),
                gap=10, extra="width: 396px;")
    return area_page(
        "Record", "record", ["Record"], "Record", "past and present · two things still out of place", "warn",
        [row(col(kcell("Who was on someone else's machine", "three today", "danger", entered, w=900, h=316, top=True),
                 kcell("The trail", "newest first", "dim", trail, w=900, h=340, top=True), gap=20, extra="flex: none;"),
             col(kcell("Reports and their Views", "one still open", "warn", views, w=440, h=316, top=True),
                 kcell("Out of place", "two", "danger", place, w=440, h=340, top=True), gap=20, extra="flex: none;"),
             gap=20, align="stretch", extra="flex: none;")],
        "RC04 · Who was where is now written: one card per entry, a sentence each, 'now' on the two still held. "
        "Nothing to decode. Everyone who stayed home is one line.",
        eyebrow("PAGE", "Record — redone for reading", "a wide left column"))


# ------------------------------------------------------------------ RO04: Rollout
def ro04():
    ops = [(f"{i:02d}", st, who, line, tone) for i, (st, who, line, tone) in enumerate([
        ("ok", "Kojo", "on 1.4.2", None), ("ok", "Efua", "on 1.4.2", None), ("ok", "Yaw", "on 1.4.2", None),
        ("ok", "Adjoa", "on 1.4.2", None), ("ok", "Nana", "on 1.4.2", None), ("warn", "Kwame", "still on 1.4.1", "warn"),
        ("ok", "Ama", "on 1.4.2", None), ("ok", "Kofi", "on 1.4.2", None)], start=1)]
    # centred: each department's heading over its machines, the machines centred in the room left of the pager
    head = lambda name, sub, tone=None, pad=0: row(txt(name, 13, T["ink"], 600), txt(sub, 11.5, tone_c(tone, T["faint"])), gap=10,
                                                   extra=f"justify-content: center; width: 1212px; padding-top: {pad}px;")
    fleet = col(
        head("Operations", "13 of 14 on 1.4.2"),
        paged_row(ops, 8, 58, "6 more", "", w=1316),
        head("Logistics", "1 of 2 on 1.4.2", pad=12),
        row(sp(), *[col(calm_slot(n, st, 58), txt(who, 12, T["ink"], 600), txt(line, 10.5, tone_c(tone, T["faint"]), 500 if tone else 400),
                        gap=3, extra="align-items: center; width: 92px;") for n, st, who, line, tone in
                    [("01", "ok", "Esi", "on 1.4.2", None), ("02", "danger", "Abena", "still on 1.4.1", "danger")]], sp(), gap=14,
            extra="width: 1212px;"),
        txt("Finance: 2 of 2, all current — folded away.", 11.5, T["faint"], extra="text-align: center; width: 1212px;"),
        gap=10, extra="width: 1316px;")
    gate = col(txt("1.4.3 can't be approved yet.", 15, T["ink"], 600, extra="line-height: 1.35;"),
               txt("Two machines are still on 1.4.1. Every machine must be on 1.4.2 first.", 12, T["dim"], extra="line-height: 1.45;"),
               row(tbtn("Approve 1.4.3", "accent", "check", disabled=True), gap=0),
               txt("This unlocks by itself when the two catch up.", 11.5, T["faint"]), gap=11, extra="width: 396px;")
    holding = col(
        stall_card(calm_slot("06", "warn", 44),
                   "OPS-06 won't update — Kwame's machine, Operations",
                   "Tried 6 times since Friday. The last try, at 11:20, failed. R. Mensah was told on Saturday.",
                   tbtn("Ask R. Mensah to look", "warn", size="sm")),
        stall_card(calm_slot("02", "danger", 44),
                   "LOG-02 is offline — Abena's machine, Logistics",
                   "Off since Monday. It will update by itself when it comes back. Nobody governs Logistics to follow it up.",
                   gbtn("Assign an Admin", size="sm")),
        txt("Failed updates retry on their own when a machine is idle. Only machines past the limit are shown here.",
            11.5, T["faint"], extra="padding-top: 2px;"),
        gap=10, extra="width: 856px;")
    return area_page(
        "Rollout", "rollout", ["Rollout"], "Rollout", "1.4.2 on 16 of 18 machines", "warn",
        [row(kcell("The fleet", "two machines behind", "warn", fleet, w=1360, h=350), gap=0, extra="flex: none;"),
         row(kcell("The gate", "1.4.3 waits", "warn", gate, w=440, h=306, top=True),
             kcell("Holding it up", "two machines", "warn", holding, w=900, h=306, top=True),
             gap=20, align="stretch", extra="flex: none;")],
        "RO04 · The lever and the attempts are one cell now: a card per machine holding the rollout up, what happened in plain "
        "words, and the one thing you can do on the same card. The fleet keeps its paging.",
        eyebrow("PAGE", "Rollout — redone for reading", "a band over two"))


BATCH2D = [("RC04-Record.dc.html", "Record: redone for reading", rc04),
           ("RO04-Rollout.dc.html", "Rollout: redone for reading", ro04)]

# ------------------------------------------------------------------ RC05: Record, with the readable timeline back
# The user, 27 Sep 2026: "Am not opposing the timeline, it been used a lot already, just make it readable like it
# done in super user areas or other areas." So the lanes are the Overview's own day timeline (dept_day: labelled
# lanes, an hour axis, gridlines, a legend -- the one on the department's Today), and the written entries sit
# beside it as its key.
def rc05():
    day = dept_day(w=856, lane_h=16, gap_y=7)
    entered = col(
        entry_card("SU", "admin", "You entered OPS-03", "10:20 – 11:00 · Yaw was blocked", "40 min", "danger"),
        entry_card("AQ", "admin", "A. Quaye is helping Finance", "since 10:40 · by consent", "now", "accent"),
        entry_card("RM", "admin", "R. Mensah entered OPS-04", "10:02 – 10:22 · Adjoa blocked", "20 min"),
        txt("Everyone else stayed at their own machine.", 11.5, T["faint"]), gap=9, extra="width: 396px;")
    trail = col(*[row(txt(t, 11, T["faint"], mono=True, extra="width: 44px; flex: none;"), ic(i, 15, T[tn] if tn else T["dim"]),
                      txt(w_, 12, T["ink"] if tn else T["dim"], 500 if tn else 400), gap=10,
                      extra=f"width: 100%; padding: 8px 0; border-bottom: 1px solid {T['line']};")
                  for t, i, w_, tn in [("11:45", "check", "A violation was addressed", None),
                                       ("11:41", "shield", "A restricted file on OPS-07", "danger"),
                                       ("11:00", "lock", "You left OPS-03 after 40 minutes", "danger"),
                                       ("10:40", "assistance", "A. Quaye began helping Finance", "accent"),
                                       ("09:11", "warn", "A hostname did not match", "warn")]],
                gap=0, extra="width: 396px;")
    views = col(thing_card("eye", "ok", "Listener report, channel 14", "HR · addressed Mon 09:12", "addressed"),
                thing_card("shield", "danger", "A restricted file on OPS-07", "Operations · not addressed", "open", "danger"),
                txt("Who addressed what is yours alone; it is never routed.", 10.5, T["faint"]), gap=9, extra="width: 396px;")
    place = col(txt("Two things are out of place right now.", 13.5, T["ink"], 600, extra="line-height: 1.35;"),
                thing_card("file", "danger", "budget-2026.xlsx", "Restricted · on OPS-07"),
                thing_card("warn", "warn", "A hostname did not match", "OPS-05 · not addressed"), gap=10, extra="width: 396px;")
    return area_page(
        "Record", "record", ["Record"], "Record", "past and present · two things still out of place", "warn",
        [row(kcell("Who was where, today", "you entered one machine", "danger", day, w=900, h=316, top=True),
             kcell("Entered today", "three", "danger", entered, w=440, h=316, top=True),
             gap=20, align="stretch", extra="flex: none;"),
         row(kcell("The trail", "newest first", "dim", trail, w=440, h=340, top=True),
             kcell("Reports and their Views", "one still open", "warn", views, w=440, h=340, top=True),
             kcell("Out of place", "two", "danger", place, w=440, h=340, top=True),
             gap=20, align="stretch", extra="flex: none;")],
        "RC05 · The timeline back, drawn the way the Overview and the department draw their day — labelled lanes, an hour axis, a "
        "legend — with the written entries beside it as its key. Below: the trail, reports and their Views, what is out of place.",
        eyebrow("PAGE", "Record — the readable timeline", "a pair over three"))


BATCH2D += [("RC05-Record.dc.html", "Record: the readable timeline", rc05)]
