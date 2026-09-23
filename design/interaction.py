# ================================================================== X01-X02: how the pages behave
# Two behaviours, not two looks.
#
# X01  A slot can be drawn several ways. One is the default; the others are reachable from the
#      slot itself, so a choice is made against real data rather than against a board.
# X02  The pages are visual and nearly wordless. Reading one is a second state: the chart settles
#      and text arrives beside it -- the sentence the chart was already making, then the facts
#      that back it. Text as an extension of the graph, never a replacement for it.

READ_RULES = [
    ("One sentence first", "what the chart says, in plain words, twelve words or fewer"),
    ("Then facts, one line each", "a short label and one value — never a paragraph"),
    ("Never restate the axis", "the chart is still on screen; the text adds, it does not narrate"),
    ("At most one action", "and only if there is something the Super User can actually do"),
]


def slot_head(title, note, control="none", w=560):
    """A slot's header. The control that changes how it is drawn lives here and nowhere else."""
    if control == "none":
        ctl = ""
    elif control == "hover":
        ctl = row(f'<span style="display: inline-flex; align-items: center; gap: 7px; height: 26px; padding: 0 10px; '
                  f'border-radius: 9px; background: {T["pane"]}; color: {T["dim"]}; font-family: {T["sans"]}; '
                  f'font-size: 12px;">{ic("chart", 14, T["dim"])}Stacked{ic("chevd", 13, T["faint"])}</span>', gap=0)
    else:
        ctl = row(f'<span style="display: inline-flex; align-items: center; gap: 7px; height: 26px; padding: 0 10px; '
                  f'border-radius: 9px; background: {T["accent_soft"]}; color: {T["accent"]}; font-family: {T["sans"]}; '
                  f'font-size: 12px;">{ic("chart", 14, T["accent"])}Stacked{ic("chevd", 13, T["accent"])}</span>', gap=0)
    return row(txt(title, 13.5, T["ink"], 600), txt(note, 11.5, T["faint"]),
               f'<span style="flex: 1;"></span>', ctl, gap=10, extra=f"width: {w}px;")


def chooser(options, current=0, w=210):
    """The list the control opens: the treatments this slot has, the current one ticked. Four
    items, so it is a list rather than a dialog."""
    rows_ = []
    for i, (name, note) in enumerate(options):
        on = i == current
        tick = ic("check", 14, T["accent"]) if on else '<span style="width: 14px;"></span>'
        rows_.append(row(tick, col(txt(name, 12.5, T["ink"] if on else T["dim"], 600 if on else 400),
                                   txt(note, 11, T["faint"]), gap=1, extra="flex: 1; min-width: 0;"),
                         gap=9, extra=f"width: 100%; padding: 8px 10px; border-radius: 9px; "
                                      f"background: {T['accent_soft'] if on else 'transparent'}; box-sizing: border-box;"))
    return col(*rows_, gap=2,
               extra=f"width: {w}px; padding: 6px; border-radius: 14px; background: {T['pane']}; "
                     f"box-shadow: 0 12px 34px rgba(0,0,0,0.45); box-sizing: border-box;")


def x01():
    opts = [("Stacked", "totals comparable"), ("Grouped", "each state on its own"),
            ("Progress", "the rule is the fleet"), ("One bar", "the rollout as one object")]
    rollout_stacked = stacked_bars([(n, [("confirmed", a), ("behind", b), ("failing", f)]) for n, a, b, f in ROLLOUT], w=500)
    rollout_grouped = grouped_bars(ROLLOUT, w=500)

    a = variant("A · At rest", "nothing but the chart",
                col(slot_head("Rollout 1.4.2", "by department", "none", w=520), rollout_stacked, gap=18), CW, CH)
    b = variant("B · Pointed at", "the control appears where the title already is",
                col(slot_head("Rollout 1.4.2", "by department", "hover", w=520), rollout_stacked, gap=18), CW, CH)
    c = variant("C · Open", "four treatments, the current one ticked",
                row(col(slot_head("Rollout 1.4.2", "by department", "open", w=290), rollout_grouped, gap=18,
                        extra="flex: 1; min-width: 0;"),
                    chooser(opts, current=1), gap=14, align="flex-start"), CW, CH)
    d = variant("D · Chosen", "the slot keeps the choice; nothing else on the page moves",
                col(slot_head("Rollout 1.4.2", "by department", "hover", w=520), rollout_grouped, gap=18), CW, CH,
                txt("One choice per slot, remembered. Not a control a person meets on every panel every day.",
                    11.5, T["faint"]))
    return mood("Changing how a slot is drawn",
                "every chart has alternatives; the slot is where one is picked",
                [a, b, c, d], brow=eyebrow("BEHAVIOUR", "applies to every chart slot", "all three pages"))


# ------------------------------------------------------------------ X02: reading a chart
def fact(label, value, tone=None):
    return row(txt(label, 12.5, T["dim"]), f'<span style="flex: 1;"></span>',
               txt(value, 12.5, tone_c(tone, T["ink"]), 500),
               gap=10, extra=f"width: 100%; padding: 9px 0; border-bottom: 1px solid {T['line']};")


def reading(headline, facts, action="", w=300):
    """The text state: one sentence, then facts on one line each, then at most one action."""
    parts = [txt(headline, 15, T["ink"], 600, extra="line-height: 1.35;"),
             col(*[fact(*f) for f in facts], gap=0, extra="width: 100%;")]
    if action:
        parts.append(row(f'<span style="display: inline-flex; align-items: center; gap: 7px; height: 30px; '
                         f'padding: 0 13px; border-radius: 9px; background: {T["accent_soft"]}; color: {T["accent"]}; '
                         f'font-family: {T["sans"]}; font-size: 12.5px; font-weight: 500;">{action}</span>', gap=0))
    return col(*parts, gap=16, extra=f"width: {w}px; flex: none;")


def focused_bar(w=250):
    """The chart, reduced to the one thing that was clicked. It stays on screen -- the text is an
    extension of it, so it must still be there to extend."""
    return (f'<svg width="{w}" height="64" viewBox="0 0 {w} 64">'
            f'<text x="0" y="14" fill="{T["dim"]}" font-family="{T["sans"]}" font-size="12.5">Logistics</text>'
            f'<rect x="0" y="26" width="{w * 0.62:.0f}" height="20" rx="5" fill="{ST["confirmed"]}"/>'
            f'<rect x="{w * 0.62 + 2:.0f}" y="26" width="{w * 0.31:.0f}" height="20" rx="5" fill="{ST["failing"]}"/>'
            f'<text x="0" y="60" fill="{T["faint"]}" font-family="{T["mono"]}" font-size="11.5">2 of 3</text></svg>')


def x02():
    chart = stacked_bars([(n, [("confirmed", a), ("behind", b), ("failing", f)]) for n, a, b, f in ROLLOUT], w=500)
    small = stacked_bars([(n, [("confirmed", a), ("behind", b), ("failing", f)]) for n, a, b, f in ROLLOUT],
                         w=250, bar_h=14, gap_y=22)

    a = variant("A · The page", "visual, and almost wordless",
                col(slot_head("Rollout 1.4.2", "by department", "none", w=520), chart,
                    legend([("Confirmed", ST["confirmed"]), ("Behind", ST["behind"]), ("Failing", ST["failing"])]),
                    gap=18), CW, CH)

    b = variant("B · The chart is clicked", "it settles to one side; the text arrives beside it",
                col(slot_head("Rollout 1.4.2", "by department", "none", w=520),
                    row(col(small, legend([("Confirmed", ST["confirmed"]), ("Behind", ST["behind"]),
                                           ("Failing", ST["failing"])]), gap=14, extra="flex: none;"),
                        reading("Two PCs are not on 1.4.2 yet, and 1.4.3 cannot be approved until they are.",
                                [("Confirmed", "12 of 14"), ("Retrying", "OPS-06", "warn"),
                                 ("Failing", "LOG-02, 6 attempts", "danger"), ("Approved", "Monday")],
                                action="Nudge both Admins"),
                        gap=22, align="flex-start"),
                    gap=18), CW, CH)

    c = variant("C · One bar is clicked", "the chart reduces to it; the text is about it alone",
                col(slot_head("Rollout 1.4.2", "Logistics", "none", w=520),
                    row(focused_bar(), reading("Logistics has one PC that has failed six times.",
                                               [("On 1.4.2", "2 of 3"), ("Failing", "LOG-02", "danger"),
                                                ("Last attempt", "09:12 today"), ("Admin", "none — the department is empty", "danger")],
                                               action="Open LOG-02"),
                        gap=22, align="flex-start"),
                    gap=18), CW, CH)

    d = variant("D · What the text may be", "the rule, so this never becomes prose",
                col(*[row(f'<span style="width: 6px; height: 6px; border-radius: 3px; background: {T["accent"]}; '
                          f'flex: none;"></span>',
                          col(txt(k, 12.5, T["ink"], 600), txt(v, 11.5, T["faint"]), gap=2, extra="flex: 1;"),
                          gap=10, extra="width: 100%; padding: 9px 0;")
                      for k, v in READ_RULES], gap=0, extra="width: 100%;"), CW, CH,
                txt("Back is the same click, or Escape. The page never navigates away from itself.",
                    11.5, T["faint"]))

    return mood("Reading a chart", "visual first; the words arrive when you ask a chart a question",
                [a, b, c, d], brow=eyebrow("BEHAVIOUR", "applies to every chart slot", "all three pages"))


INTERACTION = [("X01-Choosing.dc.html", "Behaviour: changing how a slot is drawn", x01),
               ("X02-Reading.dc.html", "Behaviour: reading a chart", x02)]
