# ================================================================== v8: the Super User surfaces
# super-user-reference.md: governance, not operation. Aggregate visibility, approval authority, audit.
# §5 is load-bearing: Super User has NO native Control / Events / Monitoring. That combo exists only by
# traversing into an Admin, so the rail differs from the Admin's and the Automation entry is a doorway.

SU_NAV = [("home", "Hierarchy"), ("eye", "Views"), ("reports", "Reports"), ("shield", "Updates"),
          ("tasks", "Tasks"), ("flows", "Flows"), ("assistance", "Assistance")]


def su_rail(active):
    global NAV
    was, NAV = NAV, SU_NAV
    out = icon_rail(active, "su")
    NAV = was
    return out


def su_page(name, active, side, body, inds=None, state="native", band_html=""):
    top = topbar2(inds or [IND["pings"], IND["rollout"]], "Go to, do, find")
    sh = sheet(side, body, state=state, band_html=band_html)
    return page(name, top, su_rail(active), sh, statusbar("Connected, TLS pinned", "native   1.4.2"), state)


def dept_glyph(tone=None, icon="dept", size=40):
    bg = T[tone + "_soft"] if tone else T["ground"]
    return (f'<span style="width: {size}px; height: {size}px; border-radius: 12px; background: {bg}; display: inline-flex; '
            f'align-items: center; justify-content: center; flex: none;">{ic(icon, int(size / 2), T[tone] if tone else T["dim"])}</span>')


# ------------------------------------------------------------------ 1. Departments and Admins
def screen_su_departments():
    side = col(sb_head("Departments"),
               sb_section("Three", ""),
               sb_item("dept", "Operations", "2 Admins, 7 PCs", sel=True),
               sb_item("dept", "Finance", "1 Admin, 4 PCs"),
               sb_item("dept", "Logistics", "3 PCs", right=chip("No Admin", "warn", 10)),
               sb_section("Yours alone", ""),
               sb_item("user", "Your display name", "SU"),
               row(txt("Only you create departments and assign Admins.", 11.5, T["faint"], extra="line-height: 1.5;"),
                   extra="padding: 10px 16px; margin-top: auto;"),
               gap=2, extra="flex: 1;")

    admins = cgroup(
        crow(av("RM", "admin", 30), "R. Mensah", "4 PCs", sub="WS-OPS-A1, you call him Mensah (Ops)", sel=True),
        crow(av("AQ", "admin", 30), "A. Quaye", "3 PCs", sub="WS-OPS-A2, you call her Quaye (Ops)"),
        crow(ic("plus", 16, T["dim"]), "Assign another Admin", right=""))

    pop = popover("R. Mensah", "Admin of Operations",
                  cgroup(crow(sicon("native"), "At his own level", "since 08:02", right=""),
                         crow(txt("", 1), "Client PCs", "4", right=""),
                         crow(txt("", 1), "Account", "3012", right=""), gap=6),
                  row(tbtn("Enter his view", "accent", "lock"), gbtn("Block first"), gap=8),
                  col(row(txt("What you call him", 12, T["dim"], 500), '<span style="flex: 1;"></span>', row(ic("eye", 12, T["faint"]), txt("only you", 11, T["faint"]), gap=4), gap=6),
                      f'<input type="text" value="Mensah (Ops)" aria-label="Display name" style="height: 38px; padding: 0 12px; border: 0; border-radius: 10px; background: {T["ground"]}; font-family: {T["sans"]}; font-size: 13.5px; color: {T["ink"]}; width: 100%; box-sizing: border-box;">',
                      note_line("His Workers never see this name."), gap=8),
                  acard("Offboarding", col(note_line("Everything on his PC pauses until someone is onboarded onto it. Nothing is deleted or reassigned."),
                                           row(gbtn("Offboard R. Mensah", "x", "sm"), gap=6), gap=8), summary="preserved, paused"),
                  lead=av("RM", "admin", 36))

    body = bodywrap(drill(("Departments", False), ("Operations", True)),
                    title_av(dept_glyph(), "Operations", "2 Admins, 7 Client PCs",
                             right=row(gbtn("New department", "plus", "sm"), gap=6)),
                    pills2([("Admins", "2"), ("Client PCs", "7"), ("Naming", "")], "Admins"),
                    row(col(admins, gap=0, extra=f"width: {BODY_W}px; flex: none;"), lane(pop), gap=22, align="flex-start"))
    return su_page("Super User: departments and Admins", "home", side, body)


# ------------------------------------------------------------------ 2. Views — yours alone
def screen_su_views():
    side = col(sb_head("Views", False),
               sb_section("Yours alone", ""),
               sb_item("eye", "Who addressed what", sel=True, right=txt("12", 11, T["select_sub"])),
               sb_item("reports", "Routing", right=txt("5", 11, T["faint"])),
               sb_item("home", "Across departments", right=txt("3", 11, T["faint"])),
               row(txt("A View is never a Report and never routes. It is how you see the handling of a report, without that handling becoming one.", 11.5, T["faint"], extra="line-height: 1.5;"),
                   extra="padding: 10px 16px; margin-top: auto;"),
               gap=2, extra="flex: 1;")

    seen = col(log_group("Today",
                         crow(av("RM", "admin", 26), "Resource violation, OPS-07", "Addressed 10:55", "ok", sub="Operations, 14 min after it was routed"),
                         crow(av("AQ", "admin", 26), "Listener report", "Seen 09:40", "warn", sub="Operations, not addressed yet")),
               f'<span style="height: 12px;"></span>',
               log_group("Monday",
                         crow(av("KB", "admin", 26), "Flow failure, FIN-02", "Addressed 16:20", "ok", sub="Finance"),
                         crow(av("RM", "admin", 26), "Deviation, unbound account", "Addressed 11:05", "ok", sub="Operations")), gap=0)

    pop = popover("Resource violation", "OPS-07, routed to Operations",
                  cgroup(crow(av("RM", "admin", 24), "Addressed by", "R. Mensah", right=""),
                         crow(txt("", 1), "Routed at", "10:41", right=""),
                         crow(txt("", 1), "Addressed at", "10:55", "ok", right=""),
                         crow(txt("", 1), "Also reached", "you, always", right=""), gap=6),
                  note_line("Your own copy of the report is untouched by this. Marking changes only this View."),
                  acard("The report itself", cgroup(crow(ic("shield", 15, T["danger"]), "budget-2026.xlsx", "restricted", "danger", right=""),
                                                    crow(ic("folder", 15, T["dim"]), "found in /workers/", "OPS-07", right=""), gap=6), summary="open it"),
                  lead=dept_glyph("ok", "eye", 36))

    body = bodywrap(drill(("Views", False), ("Who addressed what", True)),
                    title_av(dept_glyph(icon="eye"), "Who addressed what", "Every department, every routed report",
                             trail=chip("Yours alone", "accent", 11)),
                    pills2([("All", "12"), ("Addressed", "9"), ("Seen only", "2"), ("Untouched", "1")], "All"),
                    row(col(seen, gap=0, extra=f"width: {BODY_W}px; flex: none;"), lane(pop), gap=22, align="flex-start"))
    return su_page("Super User: Views", "eye", side, body)


# ------------------------------------------------------------------ 3. Updates and rollout health
def screen_su_updates():
    side = col(sb_head("Updates", False),
               sb_section("Versions", ""),
               sb_item("shield", "1.4.2", "rolling out", sel=True, right=chip("12 of 14", "warn", 10)),
               sb_item("shield", "1.4.3", "waiting for 1.4.2", right=chip("Blocked", "neutral", 10)),
               sb_item("shield", "1.4.1", "previous", right=chip("Supported", "ok", 10)),
               row(txt("N+1 cannot be approved until every PC confirms N. A PC on N-1 keeps working.", 11.5, T["faint"], extra="line-height: 1.5;"),
                   extra="padding: 10px 16px; margin-top: auto;"),
               gap=2, extra="flex: 1;")

    health = cgroup(
        crow(dept_glyph("ok", "dept", 30), "Operations", "6 of 7", "ok", sub="OPS-06 retries when idle"),
        crow(dept_glyph("warn", "dept", 30), "Finance", "4 of 4", "ok", sub="all confirmed Monday"),
        crow(dept_glyph("danger", "dept", 30), "Logistics", "2 of 3", "danger", sub="LOG-02 failed 6 times", sel=True))

    approve = col(row(txt("1.4.3 waits for 2 more PCs", 13.5, weight=600), '<span style="flex: 1;"></span>', txt("12 of 14", 12.5, T["warn"], mono=True), gap=8),
                  barline("Confirmed on 1.4.2", "86 %", 0.86, T["warn"]),
                  row(tbtn("Approve 1.4.3", "accent", "check", disabled=True), txt("once all 14 confirm", 12, T["faint"]), gap=10),
                  gap=12, extra=f"padding: 14px; border-radius: 12px; background: {T['ground']};")

    pop = popover("Logistics", "2 of 3 confirmed",
                  cgroup(crow(av("LO", "worker", 24), "LOG-01", "1.4.2", "ok", right=""),
                         crow(av("LO", "worker", 24), "LOG-03", "1.4.2", "ok", right=""),
                         crow(av("LO", "worker", 24), "LOG-02", "failed 6 times", "danger", right=""), gap=6),
                  note_line("Retries happen on idle and connectivity. Past the threshold the Admin is escalated to automatically."),
                  row(tbtn("Notify the Admin", "warn", "bell"), gap=8),
                  acard("There is no Admin here", col(note_line("Logistics has no Admin, so automatic escalation has nowhere to go. Assign one, or handle it yourself by traversing in."),
                                                      row(gbtn("Assign an Admin", "plus", "sm"), gap=6), gap=8), summary="zero-Admin department", tone="warn"),
                  lead=dept_glyph("danger", "dept", 36))

    body = bodywrap(drill(("Updates", False), ("1.4.2", True)),
                    title_av(dept_glyph(icon="shield"), "Rollout 1.4.2", "Approved by you, Monday 08:00",
                             trail=chip("12 of 14", "warn", 11)),
                    pills2([("By department", "3"), ("Failing", "1"), ("History", "")], "By department"),
                    row(col(approve, f'<span style="height: 12px;"></span>', health, gap=0, extra=f"width: {BODY_W}px; flex: none;"),
                        lane(pop), gap=22, align="flex-start"))
    return su_page("Super User: updates", "shield", side, body)


# ------------------------------------------------------------------ 4. The traversal trail
def screen_su_audit():
    side = col(sb_head("Hierarchy"),
               sb_section("Everything", ""),
               sb_item("home", "Departments", right=txt("3", 11, T["faint"])),
               sb_item("clock", "Who was where", sel=True, right=txt("24 h", 11, T["select_sub"])),
               sb_item("warn", "Deviations", right=txt("1", 11, T["faint"])),
               sb_section("Operations", "2 Admins"),
               sb_person("R. Mensah", "WS-OPS-A1", "traversed", "RM", "admin"),
               sb_person("A. Quaye", "WS-OPS-A2", "native", "AQ", "admin"),
               sb_legend(), gap=2, extra="flex: 1;")

    trail = col(log_group("Today",
                          crow(av("SU", "su", 26), "You entered OPS-04", "10:41", sub="through R. Mensah, 21 min", sel=True),
                          crow(av("RM", "admin", 26), "R. Mensah entered OPS-04", "10:20", "warn", sub="still inside, 21:18 left"),
                          crow(av("AQ", "admin", 26), "A. Quaye assisted K. Boateng", "09:31", sub="Operations helping Finance, 29 min, by consent"),
                          crow(av("RM", "admin", 26), "R. Mensah blocked Ama", "08:58", sub="OPS-07, 4 min")),
                f'<span style="height: 12px;"></span>',
                log_group("Monday", crow(av("SU", "su", 26), "You approved 1.4.2", "08:00", sub="14 PCs")), gap=0)

    pop = popover("You entered OPS-04", "Today 10:41",
                  cgroup(crow(ic("dept", 15, T["dim"]), "Operations", "10:41", right=""),
                         crow(av("RM", "admin", 24), "R. Mensah", "blocked to pass", "warn", right=""),
                         crow(av("AD", "worker", 24), "Adjoa, OPS-04", "10:43", right=""), gap=6),
                  note_line("Everything you did inside is logged as you, not as R. Mensah."),
                  acard("What you did", cgroup(crow(ic("folder", 15, T["dim"]), "Opened 3 folders", "", right=""),
                                               crow(ic("camera", 15, T["dim"]), "Took 1 screenshot", "", right=""),
                                               crow(ic("lock", 15, T["warn"]), "Opened a restricted folder", "exempt", "warn", right=""), gap=6), summary="5 actions"),
                  lead=av("SU", "su", 36))

    body = bodywrap(drill(("Hierarchy", False), ("Who was where", True)),
                    title_av(dept_glyph(icon="clock"), "Who was where", "Every traversal, who, how deep, how long"),
                    pills2([("Last 24 h", "24"), ("Yours", "4"), ("Assisted", "2"), ("Deviations", "1")], "Last 24 h"),
                    row(col(trail, gap=0, extra=f"width: {BODY_W}px; flex: none;"), lane(pop), gap=22, align="flex-start"))
    return su_page("Super User: who was where", "home", side, body)
