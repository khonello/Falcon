"""The rollout gate: who holds the next version back, leaving machines out, approving with a reason, retrying, adoption (WP7)."""

from __future__ import annotations

from tests.conftest import requires_db

pytestmark = requires_db

ALL_PCS = ("su_pc", "a1_pc", "w1_pc", "w2_pc", "a2_pc")


async def _everyone_on(engine, org, version_id: int, version: str, except_: tuple[str, ...] = ()) -> None:
    for key in ALL_PCS:
        if key not in except_:
            await engine.db.updates.record_attempt(org[key], version_id, True, version_id)
            await engine.db.updates.log_version(org[key], version)


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


async def test_failed_installs_say_what_went_wrong_and_adoption_counts_machines_day_by_day(engine, org, connect):
    su = await connect("cid-su")
    w1 = await connect("cid-w1")
    first = await su.ok("updates.approve", {"version": "1.0"})
    await _everyone_on(engine, org, first["version_id"], "1.0")
    await su.ok("updates.approve", {"version": "1.1"})                                           # everyone runs 1.0, so 1.1 is approved: now everyone is behind it
    for _ in range(2):
        await w1.ok("updates.report_status", {"version": "1.1", "succeeded": False, "running": "1.0", "error": "A file was in use"})
    gate = await su.ok("rollout.gate")
    row = next(h for h in gate["holding"] if h["hostname"] == "FIN-01")
    assert row["attempts"] == 2 and row["last_error"] == "A file was in use" and row["last_attempt_at"] and row["should_run"] == "1.1"
    assert gate["strip"]["failed_installs"] == 2 and gate["strip"]["failed_hosts"] == [{"hostname": "FIN-01", "n": 2}]
    assert gate["strip"]["holding"] == 5 and gate["strip"]["running"] == 0

    await w1.ok("updates.report_status", {"version": "1.1", "succeeded": True, "running": "1.1"})
    second = (await su.ok("rollout.gate"))["adoption"]
    [today] = second
    assert today["n"] == 1 and today["joined"] == ["FIN-01"] and today["note"] == "1.1 approved"
    assert all(h["hostname"] != "FIN-01" for h in (await su.ok("rollout.gate"))["holding"]) and (await su.ok("rollout.gate"))["strip"]["holding"] == 4


async def test_the_file_event_history_ages_out_with_the_audit_trail_and_nothing_newer_is_touched(engine, org):
    db = engine.db
    await db.pool.execute("INSERT INTO file_events (pc_id, op, path, occurred_at) VALUES ($1, 'create', 'C:/old.txt', now() - interval '120 days')", org["w1_pc"])
    await db.pool.execute("INSERT INTO file_events (pc_id, op, path, occurred_at) VALUES ($1, 'create', 'C:/new.txt', now() - interval '10 days')", org["w1_pc"])
    await engine.audit.run_retention()
    assert [r["path"] for r in await db.pool.fetch("SELECT path FROM file_events ORDER BY id")] == ["C:/new.txt"]


async def test_retention_says_what_it_did_and_a_failing_part_does_not_stop_the_rest(engine, org, caplog):
    import logging

    caplog.set_level(logging.INFO)
    await engine.db.pool.execute("INSERT INTO file_events (pc_id, op, path, occurred_at) VALUES ($1, 'create', 'C:/old.txt', now() - interval '200 days')", org["w1_pc"])
    await engine.audit.run_retention()
    text = caplog.text
    assert "retention: starting" in text and "retention: ok, 1 file events older than" in text and "retention: ok," in text and "FAILED" not in text

    async def boom(days):
        raise RuntimeError("disk full")

    engine.db.audit.purge_file_events_older_than = boom
    caplog.clear()
    await engine.audit.run_retention()
    assert "retention: FAILED to clear file events" in caplog.text and "retention: ok" in caplog.text            # the other parts still ran
