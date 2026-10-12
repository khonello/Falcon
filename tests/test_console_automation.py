"""The Automation and Actions pages: rules with how they fired and how their runs ended, the library with its runs, a test on one machine (WP8)."""

from __future__ import annotations

from tests.conftest import requires_db

pytestmark = requires_db


async def _run(engine, action_id: int, event_id: int | None, pc_id: int, status: str, reason: str | None = None, summary: str | None = None) -> int:
    ex = await engine.db.control.start_execution(action_id, event_id, pc_id)
    await engine.db.control.finish_execution(ex, status, terminated_reason=reason, summary=summary, exit_code=0 if status == "success" else 1)
    return ex


async def test_the_automation_board_counts_firings_and_how_the_runs_ended_and_an_admin_sees_only_their_department(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    shot = (await a1.ok("control.action_create", {"kind": "control", "builtin_type": "screenshot", "timeout_s": 10, "name": "Snapshot the screen"}))["action"]
    note = (await a1.ok("control.action_create", {"kind": "control", "builtin_type": "notify", "timeout_s": 10, "params": {"message": "hello"}, "name": "Tell the Admin"}))["action"]
    r1 = (await a1.ok("control.event_create", {"type": "usb.inserted", "action_ids": [shot["id"], note["id"]], "name": "Snapshot a USB drive"}))["event"]
    r2 = (await su.ok("control.event_create", {"type": "program.launched", "match": {"process": "excel.exe"}, "action_ids": [note["id"]]}))["event"]
    assert r1["name"] == "Snapshot a USB drive" and r2["name"] is None

    await engine.audit.record(None, "event.fired", target_type="event", target_id=r1["id"], detail={"pc_id": org["w1_pc"]})
    await _run(engine, shot["id"], r1["id"], org["w1_pc"], "success", summary="Screenshot of FIN-01")
    await _run(engine, note["id"], r1["id"], org["w1_pc"], "failed")
    await engine.audit.record(None, "event.fired", target_type="event", target_id=r2["id"], detail={"pc_id": org["a2_pc"]})            # on an HR machine
    await _run(engine, note["id"], r2["id"], org["a2_pc"], "success")
    await _run(engine, shot["id"], None, org["w2_pc"], "terminated", reason="timeout")                                                  # by hand, ran out of time
    await _run(engine, shot["id"], None, org["w2_pc"], "terminated", reason="manual")                                                   # by hand, stopped

    board = await a1.ok("automation.board")
    rules = {r["event_id"]: r for r in board["rules"]}
    assert set(rules) == {r1["id"], r2["id"]}                                                    # their own, and the Super User's that reaches the department
    mine, org_wide = rules[r1["id"]], rules[r2["id"]]
    assert mine["name"] == "Snapshot a USB drive" and mine["kind"] == "Event" and mine["when"] == "a USB drive is inserted" and mine["read_only"] is False
    assert mine["fired"] == 1 and mine["last_run"] == "1 failed, 1 success" and mine["last_run_problem"] is True and mine["problems"] == 1
    assert [a["name"] for a in mine["actions"]] == ["Snapshot the screen", "Tell the Admin"]
    assert org_wide["name"] == "Excel.exe starts" and org_wide["owner"] == "Super User" and org_wide["read_only"] is True
    assert org_wide["fired"] == 0 and org_wide["last_run"] is None                              # it fired on an HR machine, which this department does not see
    assert board["strip"] == {"rules": 2, "on": 2, "fired": 1, "problems": 2, "set_by_super_user": 1}
    today = board["days"][-1]
    assert len(board["days"]) == 7 and (today["Success"], today["Failed"], today["Timed out"], today["Stopped by you"]) == (1, 1, 1, 1)

    whole = await su.ok("automation.board")
    assert whole["strip"]["fired"] == 2 and {r["event_id"]: r for r in whole["rules"]}[r2["id"]]["fired"] == 1 and whole["days"][-1]["Success"] == 2
    assert (await su.ok("control.event_history", {"event_id": r1["id"]}))["firings"][0]["runs"][0]["outcome"] in ("Success", "Failed")

    lib = await a1.ok("actions.board")
    by_name = {a["name"]: a for a in lib["actions"]}
    assert by_name["Snapshot the screen"]["runs"] == 3 and by_name["Snapshot the screen"]["by_hand"] == 2 and by_name["Snapshot the screen"]["problems"] == 1
    assert [u["event_id"] for u in by_name["Snapshot the screen"]["used_by"]] == [r1["id"]] and by_name["Tell the Admin"]["used_by"][0]["name"] in ("Snapshot a USB drive", "Excel.exe starts")
    assert by_name["Snapshot the screen"]["last_run"]["outcome"] in ("Stopped by you", "Timed out", "Success") and by_name["Snapshot the screen"]["days"][-1]["Timed out"] == 1
    assert lib["strip"]["actions"] == 2 and lib["strip"]["control"] == 2 and lib["strip"]["custom"] == 0 and lib["strip"]["runs"] == 4 and lib["strip"]["by_hand"] == 2

    runs = await a1.ok("actions.runs", {"action_id": shot["id"], "hand": True})
    assert runs["total"] == 2 and {r["outcome"] for r in runs["runs"]} == {"Timed out", "Stopped by you"} and all(r["by"] == "hand" for r in runs["runs"])
    first = (await a1.ok("actions.runs", {"event_id": r1["id"]}))["runs"]
    assert {r["by"] for r in first} == {"rule: Snapshot a USB drive"} and any(r["summary"] == "Screenshot of FIN-01" for r in first)
    w1 = await connect("cid-w1")
    assert await w1.err("automation.board") == "forbidden" and await w1.err("actions.board") == "forbidden"


async def test_a_rule_can_be_tested_on_one_machine_it_applies_to(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    note = (await a1.ok("control.action_create", {"kind": "control", "builtin_type": "notify", "timeout_s": 10, "params": {"message": "hello"}}))["action"]
    rule = (await a1.ok("control.event_create", {"type": "usb.inserted", "action_ids": [note["id"]]}))["event"]
    empty = (await a1.ok("control.event_create", {"type": "user.login", "action_ids": []}))["event"]
    await w1.drain_pushes()

    done = await a1.ok("control.event_test", {"event_id": rule["id"], "pc_id": org["w1_pc"]})
    assert len(done["runs"]) == 1 and done["runs"][0]["execution_id"]
    assert "action.execute" in w1.push_types(await w1.drain_pushes())
    ran = await a1.ok("actions.runs", {"action_id": note["id"], "hand": True})
    assert ran["total"] == 1 and ran["runs"][0]["outcome"] == "Running" and ran["runs"][0]["host"] == "FIN-01"
    assert (await a1.ok("automation.board"))["rules"][0]["fired"] == 0                           # a test is not the rule firing

    assert await a1.err("control.event_test", {"event_id": rule["id"], "pc_id": org["a2_pc"]}) == "forbidden"       # another department's machine
    assert await a1.err("control.event_test", {"event_id": rule["id"], "pc_id": org["w2_pc"]}) == "unavailable"     # offline
    assert await a1.err("control.event_test", {"event_id": empty["id"], "pc_id": org["w1_pc"]}) == "conflict"       # nothing to run
    assert await su.err("control.event_test", {"event_id": 9999, "pc_id": org["w1_pc"]}) == "not_found"
    assert "event.tested" in {e["action_type"] for e in (await su.ok("audit.events"))["events"]}
