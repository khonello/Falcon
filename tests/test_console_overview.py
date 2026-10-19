"""The Overviews, the reports board and the Super User's decisions (WP5)."""

from __future__ import annotations

import dataclasses
from datetime import datetime, timedelta, timezone

from engine.hierarchy import reports
from tests.conftest import requires_db

pytestmark = requires_db


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
