"""Parked with the Super User (docs/design/v1-it-admin.md), 1 Nov 2026: tests cut from tests/. Each says the file it came from and goes back

there; they use that file's imports and fixtures."""


# --- from tests/test_operator_gui.py
async def test_the_super_user_has_their_own_level_and_enters_an_admin_s(console):
    """The Super User's own level is the organisation; operating happens inside an Admin's console, and
    there the console IS that Admin's console, answered by the Engine as that Admin."""
    win, bridge, _ = console("super_user")
    assert prop(win, "menuKeys") == SU_MENU
    assert bridge.viewThroughSession is False

    bridge.state.set_session({"session_id": 4, "pc_id": 101, "occupied_via": "traversal", "super_user_banner": True,
                              "entered_at": _ago(0)})
    assert prop(win, "menuKeys") == ADMIN_MENU
    assert bridge.viewThroughSession is True

    # step back out from an Admin-only page: it is not a page of this level, so the Overview opens
    win.setProperty("view", "automation")
    bridge.state.set_session(None)
    assert prop(win, "menuKeys") == SU_MENU
    assert prop(win, "where") == "overview"


# --- from tests/test_operator_gui.py
async def test_the_super_user_never_opens_an_admin_s_page(console):
    """A machine opens on its department's page; a pruned page lands on Overview (docs/design/su-navigation.md, pruning.md)."""
    win, _, _ = console("super_user")
    win.setProperty("view", "machines/OPS-01")
    assert prop(win, "where") == "departments"
    win.setProperty("view", "access")
    assert prop(win, "where") == "overview"


# --- from tests/test_operator_gui.py
async def test_a_department_without_an_admin_comes_first(console):
    """The one condition on Departments that needs the Super User: its reports come to them."""
    win, bridge, _ = console("super_user")
    view = await _open(win, bridge, "departments", "departmentsView")
    await _wait(lambda: len(prop(view, "all") or []) == 2)
    assert [d["name"] for d in prop(view, "all")] == ["Logistics", "Operations"]


# --- from tests/test_operator_gui.py
async def test_the_super_user_gives_a_task_on_its_own_page(console):
    """New task at the Super User's level is a page, not a drawer over the list: it holds Give back until the work and
    a department with an Admin are set, shows who is told, and sends task.dept_create, then opens the list."""
    win, bridge, _ = console("super_user")
    page = await _open(win, bridge, "tasks/new", "giveTask")
    assert prop(page, "problem") == "Say what needs doing."
    page.setProperty("text", "Collect the signed leave forms")
    assert prop(page, "problem") == "Pick a department."
    page.setProperty("dept", 1)
    await _wait(lambda: prop(page, "problem") == "")
    assert [a["name"] for a in prop(page, "told")] == ["R. Mensah"]
    QMetaObject.invokeMethod(page, "save")
    await _wait(lambda: any(t == "task.dept_create" for t, _ in bridge.conn.seen))
    sent = next(p for t, p in bridge.conn.seen if t == "task.dept_create")
    assert sent["department_id"] == 1 and sent["title"] == "Collect the signed leave forms" and "admin_ids" not in sent
    await _wait(lambda: prop(win, "where") == "tasks")

async def test_one_person_s_pings_are_one_row_with_every_time(console):
    """The Engine answers a row per ping; two pings from Kojo are one row that says twice, answered as the first."""
    win, bridge, _ = console("admin")
    view = await _open(win, bridge, "messages", "messagesView")
    await _wait(lambda: any(r.get("kind") == "ping" for r in (prop(view, "rows") or [])))
    pings = [r for r in prop(view, "rows") if r["kind"] == "ping"]
    assert len(pings) == 1
    assert pings[0]["pings"] == 2 and pings[0]["pid"] == 5 and pings[0]["st"][0] == "Asks to talk, 2 times"
    assert len(pings[0]["times"]) == 2


# --- from tests/test_detective_gui.py
async def test_the_super_user_sees_every_case_by_department_and_decides_only_what_is_sent_up_or_on_an_admin_s_machine(console):
    win, bridge, _ = console("super_user")
    page = await _open(win, bridge, "detective", "detectiveOverview")
    base = {"id": 1, "host": "FIN-02", "intent": "Taking data out", "level": "urgent", "weight": 0.9, "status": "open", "story": ["12:00  opened a.xlsx"], "headline": "Taking data out.",
            "first_at": "2026-10-18T10:00:00Z", "last_at": "2026-10-18T10:05:00Z", "department_id": 2}
    page.setProperty("cases", [base, {**base, "id": 2, "host": "FIN-01", "status": "escalated"}])
    _pump(0.4)
    assert "deptCards" in _names(win.contentItem())
    assert prop(page, "toDecide") == 1                                                       # only the one an Admin sent up is theirs
    QMetaObject.invokeMethod(page, "show", Q_ARG("QVariant", base))
    _pump(0.4)
    assert win.findChild(QObject, "detDecision").property("visible") is False                 # the department's Admin reviews that one
    QMetaObject.invokeMethod(page, "show", Q_ARG("QVariant", {**base, "id": 2, "status": "escalated"}))
    _pump(0.4)
    assert win.findChild(QObject, "detDecision").property("visible") is True
    QMetaObject.invokeMethod(page, "review", Q_ARG("QVariant", "explained"))
    await _wait(lambda: any(t == "detective.review" for t, _ in bridge.conn.seen))
    assert next(p for t, p in bridge.conn.seen if t == "detective.review")["outcome"] == "explained"


# --- from tests/test_detective_gui.py
async def test_the_super_user_can_open_a_move_to_another_machine_from_the_registry(console):
    win, bridge, _ = console("super_user")
    page = await _open(win, bridge, "registry", "registryView")
    assert win.findChild(QObject, "handoverCard") is not None and win.findChild(QObject, "handoverCard").property("visible") is True
    QMetaObject.invokeMethod(page, "openHandover", Q_ARG("QVariant", True))
    await _wait(lambda: any(t == "handover.open" for t, _ in bridge.conn.seen))
    QMetaObject.invokeMethod(page, "openHandover", Q_ARG("QVariant", False))
    await _wait(lambda: any(t == "handover.cancel" for t, _ in bridge.conn.seen))


# --- from tests/test_detective_gui.py
async def test_what_waits_on_the_super_user_includes_suggestions_flows_to_allow_and_a_machine_asking_to_take_over(console):
    win, bridge, _ = console("super_user")
    real = bridge.conn.call

    async def call(type_, payload=None):
        if type_ == "proposals.list":
            return {"proposals": [{"id": 4, "kind": "follow_up_task", "title": "Ask the department's Admin to follow up on FIN-01?", "created_at": "2026-10-18T10:00:00Z"}, {"id": 6, "kind": "pause_flow", "title": "Pause flow #3?", "created_at": "2026-10-18T10:00:00Z"}]}
        if type_ == "flow.restricted_waiting":
            return {"waiting": [{"id": 5, "flow_id": 9, "name": "Payroll", "sample_path": "C:/Finance/Payroll/p.xlsx", "asked_at": "2026-10-18T10:05:00Z"}]}
        if type_ == "handover.status":
            return {"open": True, "waiting": [{"id": 7, "hostname": "SU-NEW", "created_at": "2026-10-18T10:10:00Z"}]}
        return await real(type_, payload or {})

    bridge.conn.call = call
    await _open(win, bridge, "overview", "overviewView")
    loader = win.findChild(QObject, "page")                 # (a page that was left is still around a moment: the loader holds the one on show)
    await _wait(lambda: loader.property("item") is not None and loader.property("item").metaObject().className().startswith("SuOverviewPage"))
    page = loader.property("item")
    await _wait(lambda: {x["kind"] for x in prop(page, "q") or []} >= {"proposal", "restricted", "handover"})
    q = {x["kind"]: x for x in prop(page, "q")}
    assert q["handover"]["title"] == "SU-NEW is asking to become your machine" and q["handover"]["options"][0]["go"] == ["registry", "ask"]
    assert [o["key"] for o in q["proposal"]["options"]] == ["yes", "no"] and q["restricted"]["title"].startswith("Flow 9 wants to carry Payroll")
    assert len([x for x in prop(page, "q") if x["kind"] == "proposal"]) == 1                    # pausing a flow is the department's Admin's: only the follow-up on a case sent up reaches the Super User


# --- from tests/test_detective_gui.py
async def test_the_super_user_s_overview_is_what_waits_a_map_of_the_organisation_and_the_four_core_features_as_tiles(console):
    win, bridge, _ = console("super_user")
    real = bridge.conn.call

    async def call(type_, payload=None):
        if type_ == "detective.overview":
            return {"by_level": {"urgent": 2, "case": 1, "noted": 0}, "by_intent": {}, "reviewed": 0}
        if type_ == "detective.cases":
            return {"cases": [{"id": 1, "intent": "Taking data out", "host": "FIN-02", "level": "urgent"}]}
        if type_ == "flow.list":
            return {"flows": [{"id": 1, "status": "active", "source_hostname": "A", "destinations": []},
                              {"id": 2, "status": "paused", "pause_reason": "restricted:consent", "source_hostname": "B", "destinations": [{"destination_hostname": "C"}]}]}
        if type_ == "marks.list":
            return {"marks": [{"id": 1, "name": "Payroll", "host": "FIN-02", "copies": 2, "carried_by": [2]}]}
        return await real(type_, payload or {})

    bridge.conn.call = call
    await _open(win, bridge, "overview", "overviewView")
    loader = win.findChild(QObject, "page")
    await _wait(lambda: loader.property("item") is not None and loader.property("item").metaObject().className().startswith("SuOverviewPage"))
    page = loader.property("item")
    await _wait(lambda: prop(page, "ov")["by_level"]["urgent"] == 2 and len(prop(page, "flows")) == 2 and len(prop(page, "marks")) == 1)
    for name in ("waitingBand", "orgMap", "quadTasks", "quadFlows", "quadRestricted", "quadDetective"):
        assert page.findChild(QObject, name) is not None, name
    h = lambda n: page.findChild(QObject, n).property("height")          
    assert h("quadTasks") == h("quadFlows") and h("quadRestricted") == h("quadDetective")          # side by side, one height
    assert prop(page, "carried") == 1 and prop(page, "copies") == 2 and len(prop(page, "asking")) == 1


# --- from tests/test_console_overview.py
async def test_a_report_says_whose_it_is_and_the_board_measures_how_fast_a_department_takes_them(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    await su.ok("reports.routing_set", {"category": "deviation", "department_ids": []})     # departments start routed; this one is taken back
    # a deviation on FIN-01: Finance has an Admin, but the category is not routed there, so it is the Super User's
    first = await reports.emit(engine, "deviation", source_table="pcs", source_id=org["w1_pc"], summary="FIN-01 showed another name")
    board = await su.ok("reports.board")
    [r] = board["reports"]
    assert r["id"] == first and r["owner"] == "unrouted" and r["host"] == "FIN-01" and r["department_name"] == "Finance" and r["label"] == "Deviation"
    assert board["strip"] == {"waiting": 1, "with_department": 0, "addressed": 0, "typical_minutes": None}
    assert (await a1.ok("reports.board"))["reports"] == []                                    # not routed to Finance: not the Admin's to see

    queue = await su.ok("overview.queue")
    [card] = queue["decisions"]
    assert card["id"] == "reports:deviation" and card["kind"] == "reports" and card["report_ids"] == [first]
    assert {o["key"] for o in card["options"]} >= {"mark", "route", "later"} and "Finance" in card["why"]

    done = await su.ok("overview.decide", {"decision": card["id"], "option": "route"})
    assert done["done"] == "Routed" and done["decisions"] == []                                 # routed to Finance: it leaves the Super User's list
    mine = (await a1.ok("reports.board"))
    assert [x["id"] for x in mine["reports"]] == [first] and mine["reports"][0]["owner"] == "dept" and mine["strip"]["waiting"] == 1
    await engine.db.pool.execute("UPDATE reports SET generated_at = now() - interval '90 minutes' WHERE id = $1", first)
    await a1.ok("reports.mark", {"report_id": first})
    after = await su.ok("reports.board")
    assert after["reports"][0]["addressed"]["took_minutes"] in (90, 91) and after["strip"]["addressed"] == 1
    finance = next(h for h in after["handling"] if h["name"] == "Finance")
    assert finance["done"] == 1 and finance["waiting"] == 0 and 89 <= finance["median_minutes"] <= 92
    assert (await a1.ok("reports.board"))["strip"]["typical_minutes"] in (90, 91)
    assert await a1.err("overview.queue") == "forbidden"


# --- from tests/test_console_overview.py
async def test_a_department_with_no_admin_is_a_decision_and_a_worker_can_be_promoted_into_it(engine, org, connect):
    su = await connect("cid-su")
    dept = (await su.ok("hierarchy.department_create", {"name": "Logistics"}))["department_id"]
    worker = await su.ok("hierarchy.account_create", {"role": "worker", "department_id": dept, "hostname": "LOG-01"})
    await reports.emit(engine, "update_status", source_table="pcs", source_id=worker["pc_id"], summary="update to 1.2 failed 3x on LOG-01")

    queue = await su.ok("overview.queue")
    ids = [c["id"] for c in queue["decisions"]]
    assert f"seat:{dept}" in ids and "reports:update_status" in ids                           # nobody below the Super User can take either
    seat = next(c for c in queue["decisions"] if c["id"] == f"seat:{dept}")
    keys = [o["key"] for o in seat["options"]]
    assert f"promote:{worker['account_id']}" in keys and "provision" in keys and "elsewhere" in keys
    elsewhere = next(o for o in seat["options"] if o["key"] == "elsewhere")
    assert "one department" in elsewhere["disabled"] and await su.err("overview.decide", {"decision": seat["id"], "option": "elsewhere"}) == "conflict"

    made = (await su.ok("overview.decide", {"decision": seat["id"], "option": f"promote:{worker['account_id']}"}))
    assert made["result"]["role"] == "admin" and made["result"]["client_key"] and made["result"]["key_generation"] == 2
    assert f"seat:{dept}" not in [c["id"] for c in made["decisions"]]
    assert (await su.ok("hierarchy.account_get", {"account_id": worker["account_id"]}))["account"]["role"] == "admin"
    assert await su.err("overview.decide", {"decision": seat["id"], "option": "provision", "hostname": "X"}) == "not_found"       # no longer waiting
    assert await su.err("hierarchy.admin_promote", {"account_id": org["a1"]}) == "conflict"                                         # an Admin is not a Worker

    departments = {d["name"]: d for d in (await su.ok("overview.departments"))["departments"]}
    assert departments["Logistics"]["vacant"] is False and departments["Finance"]["machines"] == 3


# --- from tests/test_console_overview.py
async def test_a_report_about_an_admin_can_be_asked_about_limited_or_noted_and_the_limit_is_enforced(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    deadline = datetime.now(timezone.utc) + timedelta(minutes=30)
    session = await engine.db.sessions.open(org["w1_pc"], org["a1"], "traversal", deadline, False)
    await reports.emit(engine, "about_admin", source_table="sessions", source_id=session, summary="An Admin entered FIN-01 outside working hours")
    await engine.db.sessions.end(session, "voluntary")

    [card] = (await su.ok("overview.queue"))["decisions"]
    assert card["id"] == "reports:about_admin" and "never routed" in card["why"] and card["about"]
    assert [r["department_id"] for r in card["reports"]] == [org["fin"]]                      # counts against the Admin's own department
    assert {"ask", "limit", "fine", "mark"} <= {o["key"] for o in card["options"]} and "route" not in {o["key"] for o in card["options"]}
    assert await su.err("overview.decide", {"decision": card["id"], "option": "ask"}) == "invalid"                              # a message is needed

    await a1.drain_pushes()
    await su.ok("overview.decide", {"decision": card["id"], "option": "ask", "message": "Why were you in FIN-01 at 2 a.m.?"})
    assert "admin.question" in a1.push_types(await a1.drain_pushes())

    await su.ok("overview.decide", {"decision": card["id"], "option": "limit"})
    assert (await su.ok("hierarchy.account_get", {"account_id": org["a1"]}))["account"]["hours_limited"] is True
    engine.settings = dataclasses.replace(engine.settings, working_hours="00:00-00:00")      # always outside working hours
    assert await a1.err("hierarchy.traverse", {"pc_id": org["w2_pc"]}) == "forbidden"
    await su.ok("hierarchy.admin_limit", {"account_id": org["a1"], "on": False})
    assert (await a1.call("hierarchy.traverse", {"pc_id": org["w2_pc"]})).error is None

    assert await su.err("overview.decide", {"decision": card["id"], "option": "fine"}) == "invalid"                             # a reason is needed
    await su.ok("overview.decide", {"decision": card["id"], "option": "fine", "reason": "He was covering the night shift"})
    assert (await su.ok("overview.queue"))["decisions"] == []
    addressed = (await su.ok("reports.board"))["reports"][0]["addressed"]
    assert addressed["by"]
    assert await a1.err("hierarchy.admin_limit", {"account_id": org["a1"], "on": True}) == "forbidden"


# --- from tests/test_console_overview.py
async def test_a_department_calling_its_work_done_waits_for_the_super_user_to_complete_or_send_it_back(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    when = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    task = (await su.ok("task.dept_create", {"department_id": org["fin"], "title": "Prepare the stock count", "deadline_at": when}))["task"]["id"]
    assert (await su.ok("overview.queue"))["decisions"] == []                                   # nothing to decide until an Admin says it is done
    await a1.ok("task.dept_mark", {"task_id": task, "state": "done"})
    [card] = (await su.ok("overview.queue"))["decisions"]
    assert card["id"] == f"dtask:{task}" and "Prepare the stock count" in card["title"] and {o["key"] for o in card["options"]} == {"complete", "notyet"}

    assert await su.err("overview.decide", {"decision": card["id"], "option": "notyet"}) == "invalid"
    back = await su.ok("overview.decide", {"decision": card["id"], "option": "notyet", "message": "The cellar is not counted"})
    assert back["done"] == "Sent back" and back["decisions"] == []
    await a1.ok("task.dept_mark", {"task_id": task, "state": "done"})
    done = await su.ok("overview.decide", {"decision": f"dtask:{task}", "option": "complete"})
    assert done["done"] == "Marked complete" and done["decisions"] == []
    assert (await su.ok("task.dept_get", {"task_id": task}))["task"]["standing"] == "complete"


# --- from tests/test_console_overview.py
async def test_the_overviews_add_up_what_the_console_shows(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    first = await su.ok("overview.su")
    assert first["kpis"]["machines"] == 5 and first["kpis"]["online"] >= 3 and first["kpis"]["waiting"] == 0 and len(first["days"]) == 7
    assert set(first["days"][0]) == {"day", "critical", "high", "medium", "low"} and first["worth_a_look"] == []

    admin = await a1.ok("overview.admin")
    assert admin["machines"]["total"] == 3 and admin["waiting"]["total"] == admin["waiting"]["to_verify"] + admin["waiting"]["issues"] + admin["waiting"]["pings"]
    assert admin["sessions_held"] == 0 and admin["issues"]["open"] >= 0
    assert await w1.err("overview.admin") == "forbidden" and await a1.err("overview.su") == "forbidden"

    rows = (await su.ok("overview.departments"))["departments"]
    assert {r["name"] for r in rows} == {"Finance", "HR"} and all(r["vacant"] is False for r in rows)
    assert [r["name"] for r in (await a1.ok("overview.departments"))["departments"]] == ["Finance"]


# --- from tests/test_console_rollout.py
async def test_a_staged_version_waits_on_the_machines_holding_the_gate_and_can_be_approved_leaving_them_out_with_a_reason(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    w2 = await connect("cid-w2", hello={"version": "1.0"})
    first = await su.ok("updates.approve", {"version": "1.0"})
    await _everyone_on(engine, org, first["version_id"], "1.0", except_=("w2_pc",))
    assert (await su.ok("overview.queue"))["decisions"] == []                                 # nothing is ready, so nothing to decide

    assert await a1.err("updates.stage", {"version": "1.1"}) == "forbidden"
    assert (await su.ok("updates.stage", {"version": "1.1", "note": "adds the new tray"}))["was_staged"] is False
    assert (await su.ok("updates.stage", {"version": "1.1"}))["was_staged"] is True
    assert await su.err("updates.stage", {"version": "1.0"}) == "conflict"

    gate = await su.ok("rollout.gate")
    assert gate["current"]["version"] == "1.0" and gate["current"]["approved_by"] == "You" and gate["next"]["version"] == "1.1" and gate["next"]["note"] == "adds the new tray"
    [held] = gate["holding"]
    assert held["hostname"] == "FIN-02" and held["state"] == "retrying" and held["should_run"] == "1.0" and held["next_try"] == "Next idle window"
    assert gate["can_approve"] is False and gate["strip"]["holding"] == 1
    assert [h["hostname"] for h in (await a1.ok("rollout.gate"))["holding"]] == ["FIN-02"] and (await a1.ok("rollout.gate"))["can_approve"] is False

    [card] = (await su.ok("overview.queue"))["decisions"]
    assert card["id"] == "gate:1.1" and card["kind"] == "version-gate" and card["machines"] == ["FIN-02"] and {o["key"] for o in card["options"]} == {"wait", "without"}
    assert await su.err("updates.approve", {"version": "1.1"}) == "conflict"                  # the gate holds
    assert await su.err("updates.approve", {"version": "1.1", "leave_out": [org["w2_pc"]]}) == "invalid"     # a reason is needed
    assert await su.err("updates.approve", {"version": "1.1", "leave_out": [999]}) == "invalid"
    assert await su.err("overview.decide", {"decision": "gate:1.1", "option": "without"}) == "invalid"

    done = await su.ok("overview.decide", {"decision": "gate:1.1", "option": "without", "reason": "FIN-02 is being replaced next week"})
    assert done["done"] == "1.1 approved without FIN-02" and done["result"]["left_out"] == [org["w2_pc"]] and done["decisions"] == []
    left = await engine.db.updates.exclusions("1.1")                                         # recorded against the version it was left out of
    assert [(x["pc_id"], x["reason"]) for x in left] == [(org["w2_pc"], "FIN-02 is being replaced next week")] and await engine.db.updates.exclusions("next") == []
    assert (await su.ok("rollout.gate"))["current"]["version"] == "1.1" and (await su.ok("rollout.gate"))["next"] is None
    assert w2 is not None


# --- from tests/test_console_rollout.py
async def test_a_card_can_wait_and_a_machine_can_be_left_out_and_taken_back_and_told_to_retry(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    first = await su.ok("updates.approve", {"version": "1.0"})
    await _everyone_on(engine, org, first["version_id"], "1.0", except_=("w1_pc", "w2_pc"))
    await su.ok("updates.stage", {"version": "1.1"})

    assert await a1.err("updates.leave_out", {"pc_id": org["w1_pc"], "reason": "x"}) == "forbidden"            # an Admin cannot leave a machine out
    assert await su.err("updates.leave_out", {"pc_id": org["w1_pc"]}) == "invalid"
    await su.ok("updates.leave_out", {"pc_id": org["w1_pc"], "reason": "its disk is failing"})
    rows = {h["hostname"]: h for h in (await su.ok("rollout.gate"))["holding"]}
    assert rows["FIN-01"]["state"] == "left_out" and rows["FIN-01"]["left_out"]["reason"] == "its disk is failing" and rows["FIN-02"]["state"] == "offline"
    assert (await su.ok("rollout.gate"))["strip"]["left_out"] == 1 and rows["FIN-02"]["last_error"] == "Not checking in"
    assert (await su.ok("updates.take_back", {"pc_id": org["w1_pc"]}))["was_left_out"] is True
    assert {h["hostname"]: h["state"] for h in (await su.ok("rollout.gate"))["holding"]}["FIN-01"] == "retrying"

    await w1.drain_pushes()
    assert (await a1.ok("updates.retry", {"pc_id": org["w1_pc"], "when": "now"}))["when"] == "now"
    assert "update.available" in w1.push_types(await w1.drain_pushes())
    assert await a1.err("updates.retry", {"pc_id": org["w2_pc"], "when": "now"}) == "unavailable"           # offline: only when it is back
    assert (await a1.ok("updates.retry", {"pc_id": org["w2_pc"]}))["when"] == "when it is back"
    assert await a1.err("updates.retry", {"pc_id": org["a2_pc"]}) == "forbidden"                              # another department's machine

    # put aside, the card does not come back at once
    [card] = (await su.ok("overview.queue"))["decisions"]
    assert (await su.ok("overview.decide", {"decision": card["id"], "option": "wait"}))["decisions"] == []
    assert (await su.ok("overview.queue"))["decisions"] == []


# --- from tests/test_operator_client.py
async def test_scripted_department_task(engine, org, tmp_path: Path):
    su = await run_script(_cfg(engine, tmp_path, "cid-su"), [
        "connect", f"dtask give {org['fin']} due=2099-01-02T17:00 Move the tender files to the archive", "dtasks"])
    assert su[1].startswith("task 1 'Move the tender files to the archive' for Finance: told") and "told 1 Admin(s)" in su[1]
    admin = await run_script(_cfg(engine, tmp_path, "cid-a1"), [
        "connect", "dtasks", "dtask mark 1 seen", "dtask mark 1 done", "dtask 1"])
    assert "1 not yet seen by you" in admin[1]
    assert "you: seen" in admin[2] and "you: done" in admin[3] and "done" in admin[4]
    back = await run_script(_cfg(engine, tmp_path, "cid-su"), [
        "connect", "dtask reopen 1 The 2024 folder is still missing", "dtask 1", "dtask complete 1"])
    assert "ongoing" in back[1] and "2024 folder" in back[2] and "complete" in back[3]


# --- from tests/test_operator_client.py
async def test_scripted_overview_board_and_decisions(engine, org, tmp_path: Path):
    from engine.hierarchy import reports

    await engine.db.reports.set_routing("deviation", [], org["su"])      # departments start routed; this is the one taken back
    await reports.emit(engine, "deviation", source_table="pcs", source_id=org["w1_pc"], summary="FIN-01 showed another name")
    out = await run_script(_cfg(engine, tmp_path, "cid-su"), [
        "connect", "overview", "board", "decisions", "decide reports:deviation route", "decisions", "departments-board"])
    assert "waiting on you" in out[1] and "deviations, 7 days:" in out[1]
    assert "waiting 2" in out[2] and "unrouted" in out[2] and "handling:" in out[2]
    assert "reports:deviation" in out[3] and "route" in out[3]
    assert "Routed" in out[4] and "1 still waiting" in out[4]                       # the client's own name mismatch has no department to route to
    assert "reports:deviation" in out[5] and "Finance" in out[6] and "HR" in out[6]


# --- from tests/test_operator_client.py
async def test_scripted_rollout_gate(engine, org, tmp_path: Path):
    first = await engine.db.updates.approve_version("1.0", org["su"])
    for key in ("su_pc", "a1_pc", "w1_pc", "a2_pc"):
        await engine.db.updates.record_attempt(org[key], first, True, first)
    out = await run_script(_cfg(engine, tmp_path, "cid-su"), [
        "connect", "update stage 1.1 the_new_tray", "gate", f"update leave-out {org['w2_pc']} being_replaced", "decisions", "update approve 1.1", "update take-back 1"])
    assert "1.1 is ready" in out[1] and "next 1.1" in out[2] and "FIN-02" in out[2] and "holding 1" in out[2]
    assert "left out of the gate" in out[3] and "gate:1.1" in out[4] and "approved" in out[5] and "leaving out" in out[5]


# --- from tests/test_task.py
async def test_a_department_task_is_not_an_admins_task(engine, org, connect):
    """The Super User gives a department a task: no checks, one deadline, a state per Admin told, the task standing
    at the furthest any has got, and only the Super User closes it or sends it back. Admin -> Worker tasks keep theirs."""
    from datetime import datetime, timedelta, timezone

    acc = engine.db.accounts
    pc = await acc.create_pc("FIN-ADM2", org["fin"], "admin_workstation", "cid-a1b")
    a1b = await acc.create("admin", org["fin"], pc)
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    a1_2 = await connect("cid-a1b")
    a2 = await connect("cid-a2")
    due = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()

    # the old call is for an Admin's task to a Worker; the Super User gives a department a task instead
    assert await su.err("task.propose", {"description": "d", "assignee_account_id": org["a1"]}) == "forbidden"
    for bad in ({"department_id": org["fin"], "title": "x"}, {"department_id": 999, "title": "x", "deadline_at": due},
                {"department_id": org["fin"], "title": "  ", "deadline_at": due},
                {"department_id": org["fin"], "title": "x", "deadline_at": due, "admin_ids": [org["a2"]]}):
        assert await su.err("task.dept_create", bad) in ("invalid", "not_found"), bad
    assert await a1.err("task.dept_create", {"department_id": org["fin"], "title": "x", "deadline_at": due}) == "forbidden"

    made = await su.ok("task.dept_create", {"department_id": org["fin"], "title": "Move last year's tender files to the archive",
                                            "deadline_at": due})
    task = made["task"]
    assert task["told"] == 2 and task["standing"] == "told" and {a["state"] for a in task["admins"]} == {"told"}
    for w in (a1, a1_2):
        assert "task.dept_assigned" in w.push_types(await w.drain_pushes())
    assert a2.push_types(await a2.drain_pushes()) == []                          # HR's Admin is not told

    # an Admin sees the task and only their own row; the strip counts what is unseen
    mine = await a1.ok("task.dept_list")
    assert mine["unseen"] == 1 and [t["id"] for t in mine["tasks"]] == [task["id"]]
    assert [a["account_id"] for a in mine["tasks"][0]["admins"]] == [org["a1"]]
    assert (await a2.ok("task.dept_list"))["tasks"] == [] and await a2.err("task.dept_get", {"task_id": task["id"]}) == "not_found"

    # marking: own row only, the task stands at the furthest any Admin has got
    assert await a2.err("task.dept_mark", {"task_id": task["id"], "state": "seen"}) == "not_found"
    assert await a1.err("task.dept_mark", {"task_id": task["id"], "state": "told"}) == "invalid"
    seen = (await a1.ok("task.dept_mark", {"task_id": task["id"], "state": "seen"}))["task"]
    assert seen["my_state"] == "seen" and seen["standing"] == "seen"
    assert (await a1.ok("task.dept_list"))["unseen"] == 0
    upd = [p for p in await su.drain_pushes() if p.type == "task.dept_updated"]
    assert upd and upd[0].payload["state"] == "seen"
    await a1_2.ok("task.dept_mark", {"task_id": task["id"], "state": "done"})
    assert (await a1.ok("task.dept_get", {"task_id": task["id"]}))["task"]["standing"] == "done"     # the furthest
    seen_by_su = (await su.ok("task.dept_get", {"task_id": task["id"]}))["task"]
    assert sorted(a["state"] for a in seen_by_su["admins"]) == ["done", "seen"] and all(a["seen_at"] for a in seen_by_su["admins"])

    # only the Super User who gave it closes or reopens it; an Admin saying done does not close it
    assert await a1.err("task.dept_complete", {"task_id": task["id"]}) == "forbidden"
    back = (await su.ok("task.dept_reopen", {"task_id": task["id"], "note": "The 2024 folder is still missing."}))["task"]
    assert back["standing"] == "seen" or back["standing"] == "ongoing"
    assert sorted(a["state"] for a in back["admins"]) == ["ongoing", "seen"]       # the one who was done is ongoing again
    for w in (a1, a1_2):
        sent = [p for p in await w.drain_pushes() if p.type == "task.dept_reopened"]
        assert sent and "2024 folder" in sent[0].payload["note"]                   # every Admin on it sees the note
    assert (await a1.ok("task.dept_get", {"task_id": task["id"]}))["task"]["notes"][0]["text"].startswith("The 2024")
    assert await su.err("task.dept_reopen", {"task_id": task["id"], "note": " "}) == "invalid"
    done = (await su.ok("task.dept_complete", {"task_id": task["id"]}))["task"]
    assert done["standing"] == "complete" and done["completed_at"]
    assert "task.dept_completed" in a1.push_types(await a1.drain_pushes())
    assert await a1.err("task.dept_mark", {"task_id": task["id"], "state": "done"}) == "conflict"
    assert (await su.ok("task.dept_list"))["tasks"] == [] and len((await su.ok("task.dept_list", {"include_completed": True}))["tasks"]) == 1

    # told only some: the Super User picks
    one = (await su.ok("task.dept_create", {"department_id": org["fin"], "title": "Count the licences", "deadline_at": due,
                                            "admin_ids": [a1b]}))["task"]
    assert one["told"] == 1 and (await a1.ok("task.dept_list"))["tasks"] == []
    assert [t["id"] for t in (await a1_2.ok("task.dept_list"))["tasks"]] == [one["id"]]


# --- from tests/test_task.py
async def test_the_super_user_gives_departments_tasks_not_admin_style_ones(engine, org, connect):
    """Tasks with checks go from an Admin to a Worker. The Super User gives a department a task instead
    (task.dept_create, tested in test_a_department_task_is_not_an_admins_task), so the old call refuses them."""
    su = await connect("cid-su")
    for assignee in (org["w1"], org["a1"]):
        assert await su.err("task.create", {"assignee_account_id": assignee, "description": "x",
                                            "verification_mode": "none", "confirm_none": True}) == "forbidden"
    assert (await su.ok("task.list"))["tasks"] == []


# --- from tests/test_hierarchy.py
async def test_report_routing_is_additive_and_views_are_super_user_only(engine, org, connect):
    from engine.hierarchy import reports

    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    a2 = await connect("cid-a2")
    await su.ok("reports.routing_set", {"category": "flow_failure", "department_ids": []})   # departments start routed; begin from the Super User alone
    await reports.emit(engine, "flow_failure", source_table="flow_sync_log", source_id=1, summary="f1")
    assert su.push_types(await su.drain_pushes()) == ["report.new"]
    assert a1.push_types(await a1.drain_pushes()) == []
    assert len((await su.ok("reports.list"))["reports"]) == 1
    assert (await a1.ok("reports.list"))["reports"] == []

    assert await a1.err("reports.routing_set", {"category": "flow_failure", "department_ids": [org["fin"]]}) == "forbidden"
    await su.ok("reports.routing_set", {"category": "flow_failure", "department_ids": [org["fin"]]})
    rid = await reports.emit(engine, "flow_failure", source_table="flow_sync_log", source_id=2, summary="f2")
    assert a1.push_types(await a1.drain_pushes()) == ["report.new"]
    assert a2.push_types(await a2.drain_pushes()) == []
    # The pane shows every report in the routed category, including earlier ones.
    assert sorted(r["id"] for r in (await a1.ok("reports.list"))["reports"]) == [rid - 1, rid]
    assert len((await su.ok("reports.list"))["reports"]) == 2                 # still sees all
    assert su.push_types(await su.drain_pushes()) == ["report.new"]

    assert await a2.err("reports.mark", {"report_id": rid}) == "not_found"     # not routed to HR
    await a1.ok("reports.mark", {"report_id": rid})
    assert su.push_types(await su.drain_pushes()) == ["report.addressed"]
    assert await a1.err("reports.addressed_view") == "forbidden"
    view = (await su.ok("reports.addressed_view"))["addressed"]
    assert view[0]["report_id"] == rid and view[0]["addressed_by_department_id"] == org["fin"]


# --- from tests/test_hierarchy.py
async def test_a_new_department_is_routed_every_kind_but_the_ones_about_an_admin(engine, org, connect):
    from engine.database import DEFAULT_ROUTED
    from engine.hierarchy.reports import CATEGORIES, FIXED_CATEGORIES

    assert sorted(DEFAULT_ROUTED) == sorted(c for c in CATEGORIES if c not in FIXED_CATEGORIES)
    su = await connect("cid-su")
    routing = (await su.ok("reports.routing_get"))["routing"]
    for dept in (org["fin"], org["hr"]):
        assert sorted(r["category"] for r in routing if r["routed_department_id"] == dept) == sorted(DEFAULT_ROUTED)


# --- from tests/test_hierarchy.py
async def test_a_report_keeps_its_words_and_each_reader_sees_it_alone(engine, org, connect):
    from engine.hierarchy import reports

    su = await connect("cid-su")
    a1 = await connect("cid-a1")      # Finance
    a2 = await connect("cid-a2")      # HR
    await su.ok("reports.routing_set", {"category": "flow_failure", "department_ids": [org["fin"]]})
    rid = await reports.emit(engine, "flow_failure", source_table="flow_sync_log", source_id=3,
                             summary="Payroll sync stopped: the destination is full")
    row = (await a1.ok("reports.list"))["reports"][0]
    assert row["summary"] == "Payroll sync stopped: the destination is full" and row["seen_at"] is None

    assert (await a1.ok("reports.seen", {"report_ids": [rid]}))["seen"] == [rid]
    assert (await a1.ok("reports.seen", {"report_ids": [rid]}))["seen"] == []        # first open kept
    assert (await a1.ok("reports.list"))["reports"][0]["seen_at"] is not None
    assert (await su.ok("reports.list"))["reports"][0]["seen_at"] is None            # seen is per reader
    assert await a2.err("reports.seen", {"report_ids": [rid]}) == "not_found"         # not routed to HR
    assert await su.err("reports.seen", {"report_ids": []}) == "invalid"
    assert (await su.ok("reports.seen", {"report_ids": [rid]}))["seen"] == [rid]


# --- from tests/test_hierarchy.py
async def test_routing_a_department_with_or_without_earlier_reports(engine, org, connect):
    from engine.hierarchy import reports

    su = await connect("cid-su")
    a1 = await connect("cid-a1")      # Finance
    a2 = await connect("cid-a2")      # HR
    await su.ok("reports.routing_set", {"category": "deviation", "department_ids": []})     # departments start routed; begin from the Super User alone
    old = await reports.emit(engine, "deviation", source_table="flow_sync_log", source_id=1, summary="old")

    # Finance is added with the earlier reports (the default): it sees the one already written.
    res = await su.ok("reports.routing_set", {"category": "deviation", "department_ids": [org["fin"]]})
    assert res["added"] == [org["fin"]] and res["removed"] == [] and res["earlier_unaddressed"] == 1
    assert [r["id"] for r in (await a1.ok("reports.list"))["reports"]] == [old]

    # HR is added for new reports only: the old one stays the Super User's (and Finance's).
    res = await su.ok("reports.routing_set", {"category": "deviation", "department_ids": [org["fin"], org["hr"]],
                                              "include_earlier": False})
    assert res["added"] == [org["hr"]] and res["earlier_unaddressed"] == 0
    assert (await a2.ok("reports.list"))["reports"] == []
    new = await reports.emit(engine, "deviation", source_table="flow_sync_log", source_id=2, summary="new")
    assert [r["id"] for r in (await a2.ok("reports.list"))["reports"]] == [new]
    # Finance kept what it had: re-saving the category did not reset it to "new only".
    assert sorted(r["id"] for r in (await a1.ok("reports.list"))["reports"]) == [old, new]
    routing = {r["routed_department_id"]: r for r in (await su.ok("reports.routing_get"))["routing"] if r["category"] == "deviation"}
    assert routing[org["fin"]]["includes_earlier"] is True and routing[org["hr"]]["includes_earlier"] is False

    # Finance addresses the old one, then is removed: it no longer sees the category, and the
    # Super User's View still says Finance addressed it.
    await a1.ok("reports.mark", {"report_id": old})
    res = await su.ok("reports.routing_set", {"category": "deviation", "department_ids": [org["hr"]]})
    assert res["removed"] == [org["fin"]] and res["added"] == []
    assert (await a1.ok("reports.list"))["reports"] == []
    assert (await su.ok("reports.addressed_view"))["addressed"][0]["report_id"] == old
    # An empty list sends the category back to the Super User only.
    await su.ok("reports.routing_set", {"category": "deviation", "department_ids": []})
    assert (await a2.ok("reports.list"))["reports"] == []
    assert len((await su.ok("reports.list"))["reports"]) == 2
    assert await su.err("reports.routing_set", {"category": "deviation", "department_ids": [],
                                                "include_earlier": "no"}) == "invalid"
    audit = [e for e in (await su.ok("audit.recent", {"limit": 20}))["entries"] if e["action_type"] == "report_routing.set"]
    assert audit and {"added", "removed", "include_earlier"} <= set(audit[0]["detail"])


# --- from tests/test_hierarchy.py
async def test_about_admin_reports_reach_the_super_user_only_and_updates_route_by_default(engine, org, connect):
    from engine.hierarchy import traversal

    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    # every department starts with update escalations routed to it
    routing = (await su.ok("reports.routing_get"))
    assert {r["routed_department_id"] for r in routing["routing"] if r["category"] == "update_status"} == {org["fin"], org["hr"]}
    assert routing["fixed"] == ["about_admin"]
    # an Admin's own conduct can never be routed
    assert await su.err("reports.routing_set", {"category": "about_admin", "department_ids": [org["fin"]]}) == "forbidden"
    # an Admin entering a machine outside working hours is reported, to the Super User only
    engine.settings = dataclasses.replace(engine.settings, working_hours="00:00-00:00")   # every entry is outside
    await su.drain_pushes()
    await a1.ok("hierarchy.traverse", {"pc_id": org["w1_pc"]})
    assert [r["category"] for r in (await su.ok("reports.list"))["reports"]] == ["about_admin"]
    assert "report.new" in su.push_types(await su.drain_pushes())
    assert (await a1.ok("reports.list"))["reports"] == []
    assert traversal.outside_working_hours("06:00-18:00", datetime(2026, 10, 9, 2, 14, tzinfo=timezone.utc)) is True
    assert traversal.outside_working_hours("06:00-18:00", datetime(2026, 10, 9, 10, 0, tzinfo=timezone.utc)) is False
    assert traversal.outside_working_hours("22:00-06:00", datetime(2026, 10, 9, 23, 0, tzinfo=timezone.utc)) is False
