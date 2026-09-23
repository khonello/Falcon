# ================================================================== v6: the reserved lane, filled and empty
def _home_body(sel, pop_html):
    strip_ = paged([pc_card_av("Ama", "OPS-07", "Deadline reached", "danger", sel=sel),
                    pc_card_av("Kojo", "OPS-01", "Needs help", "warn"),
                    pc_card_av("Efua", "OPS-02", "Free", None, "free")], 0, 2)
    needs = cgroup(
        crow(ic("ping", 16, T["warn"]), "Kojo needs help", "4 min", "warn", right=tbtn("Answer", "warn", size="sm"), sub="OPS-01, twice"),
        crow(ic("clock", 16, T["danger"]), "Quarterly report overdue", "17:00", "danger", right=tbtn("Verify", "accent", size="sm"), sub="Ama, OPS-07", hover=sel),
        crow(ic("flows", 16, T["danger"]), "Payroll flow failed", "10:52", "danger", sub="OPS-03 unreachable"),
        crow(ic("shield", 16, T["danger"]), "Restricted file on OPS-07", "10:41", "danger", sub="budget-2026.xlsx"))
    return bodywrap(drill(("Operations", True)),
                    title_av(f'<span style="width: 40px; height: 40px; border-radius: 12px; background: {T["ground"]}; display: inline-flex; align-items: center; justify-content: center; flex: none;">{ic("dept", 20, T["dim"])}</span>',
                             "Operations", "7 PCs, 2 Admins", right=row(gbtn("Department action", "automation", "sm"), gap=6)),
                    strip_, f'<span style="height: 18px;"></span>',
                    pills2([("Needs you", "4"), ("Quiet", "3"), ("Reports", "2")], "Needs you"),
                    row(col(needs, gap=0, extra=f"width: {BODY_W}px; flex: none;"), lane(pop_html), gap=22, align="flex-start"))


def screen_lane_filled():
    pop = popover("Ama", "OPS-07",
                  col(row(sicon("native", 16), txt("At the PC", 13.5, weight=600), '<span style="flex: 1;"></span>', txt("since 08:14", 12, T["faint"]), gap=8),
                      row(tbtn("Enter", "accent", "lock"), gbtn("End session"), gap=8),
                      note_line("Entering blocks Ama until you leave. 30 min."),
                      gap=10, extra=f"padding: 12px; border-radius: 12px; background: {T['ground']};"),
                  cgroup(crow(dot(T["warn"], 8), "Quarterly report", "Due 17:00", "warn", sub="Task"),
                         crow(dot(T["ok"], 8), "Payroll to Archive", "Syncing", sub="Flow"),
                         crow(dot(T["danger"], 8), "Restricted file", "Open", "danger", sub="Violation"), gap=6),
                  acard("Names", cgroup(crow(txt("", 1), "You call her", "Ama", right=""), crow(txt("", 1), "She sees you as", "R. Mensah", right=""), gap=6), summary="private to you"),
                  lead=av("AM", "worker", 36),
                  actions=row(tbtn("Ping", "accent", "ping", "sm"), gbtn("Assign task", "tasks", "sm"), gbtn("Run action", "automation", "sm"), gap=6))
    sh = sheet(sidebar_ops("OPS-07"), _home_body(True, pop))
    return page("Lane, filled", topbar2([IND["pings"], IND["deadline"], IND["flow"], IND["done"]]), icon_rail("home", "admin"), sh, statusbar("Connected, TLS pinned", "native   1.4.2"), "native")


def screen_lane_empty():
    sh = sheet(sidebar_ops(None), _home_body(False, lane_hint()))
    return page("Lane, empty", topbar2([IND["pings"], IND["deadline"], IND["flow"], IND["done"]]), icon_rail("home", "admin"), sh, statusbar("Connected, TLS pinned", "native   1.4.2"), "native")
