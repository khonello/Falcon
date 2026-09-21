"""Control/Events/Monitoring/Actions and Updates end-to-end (skipped without
FALCON_TEST_DATABASE_URL).

Pins control-events-monitoring-actions-combo.md: Admin-only Custom Actions validated against
stdlib + Windows-native; every Action has a timeout; native signals fire matching Events;
attached Actions execute independently; timeout is distinct from failure; manual termination
by execution id; polled thresholds/time events; the Dashboard snapshot. And spec 9: the
approval gate, department rollout, escalation past the threshold, aggregate health.
"""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

from engine.control import events, executions
from tests.conftest import requires_db

pytestmark = requires_db


async def test_action_library_rules(engine, org, connect):
    a1 = await connect("cid-a1")
    su = await connect("cid-su")
    w1 = await connect("cid-w1")
    assert await w1.err("control.action_list") == "forbidden"
    # Every Action has a timeout; unknown builtins and missing params are refused.
    assert await a1.err("control.action_create", {"kind": "control", "builtin_type": "screenshot", "timeout_s": 0}) == "invalid"
    assert await a1.err("control.action_create", {"kind": "control", "builtin_type": "nope", "timeout_s": 10}) == "invalid"
    assert await a1.err("control.action_create", {"kind": "control", "builtin_type": "notify", "timeout_s": 10}) == "invalid"
    shot = (await a1.ok("control.action_create", {"kind": "control", "builtin_type": "screenshot", "timeout_s": 10}))["action"]
    assert shot["name"] == "screenshot" and shot["timing"] == {"mode": "immediate"}
    # Custom: Admin only, validated, stdlib-only.
    assert await su.err("control.action_create", {"kind": "custom", "name": "x", "language": "python",
                                                  "script": "print(1)", "timeout_s": 5}) == "forbidden"
    assert await a1.err("control.action_create", {"kind": "custom", "name": "x", "language": "python",
                                                  "script": "import requests", "timeout_s": 5}) == "invalid"
    custom = (await a1.ok("control.action_create", {"kind": "custom", "name": "hello", "language": "python",
                                                    "script": "import os\nprint(os.name)", "timeout_s": 5,
                                                    "timing": {"mode": "delayed", "delay_s": 1}}))["action"]
    assert custom["action_kind"] == "custom" and custom["timing"]["delay_s"] == 1
    lib = await a1.ok("control.action_list")
    assert [a["id"] for a in lib["actions"]["control"]] == [shot["id"]]
    assert [a["id"] for a in lib["actions"]["custom"]] == [custom["id"]]
    assert "notify" in lib["builtin"]
    # Archive, not delete.
    await a1.ok("control.action_delete", {"action_id": custom["id"]})
    assert (await a1.ok("control.action_list"))["actions"]["custom"] == []
    assert await engine.db.pool.fetchval("SELECT count(*) FROM actions") == 2


async def test_event_fires_actions_independently_with_timeout_and_termination(engine, org, connect):
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    shot = (await a1.ok("control.action_create", {"kind": "control", "builtin_type": "screenshot", "timeout_s": 1}))["action"]
    snap = (await a1.ok("control.action_create", {"kind": "monitoring", "builtin_type": "usb_contents", "timeout_s": 30}))["action"]
    assert await a1.err("control.event_create", {"type": "nope", "action_ids": []}) == "invalid"
    ev = (await a1.ok("control.event_create", {"type": "usb.inserted", "action_ids": [snap["id"], shot["id"]]}))["event"]
    assert ev["condition_type"] == "native_pushed" and [a["id"] for a in ev["actions"]] == [snap["id"], shot["id"]]

    # The worker relays a native signal -> the event fires, both actions dispatched to that PC.
    assert await w1.err("control.signal", {"type": "file.created", "data": {}}) == "invalid"   # index handles file.*
    res = await w1.ok("control.signal", {"type": "usb.inserted", "data": {"device": "E:"}})
    assert res["fired"] == 1
    pushes = await w1.drain_pushes()
    execs = [p for p in pushes if p.type == "action.execute"]
    assert sorted(p.payload["action"]["builtin_type"] for p in execs) == ["screenshot", "usb_contents"]
    assert "event.fired" in a1.push_types(await a1.drain_pushes())
    by_type = {p.payload["action"]["builtin_type"]: p.payload["execution_id"] for p in execs}

    # Output streams; the screenshot never reports -> the Engine guard terminates it (timeout).
    await w1.ok("control.execution_output", {"execution_id": by_type["usb_contents"], "chunk": "E:/file1.txt"})
    await executions._guard(engine, by_type["screenshot"])
    ex = (await a1.ok("control.execution", {"execution_id": by_type["screenshot"]}))["execution"]
    assert ex["status"] == "terminated" and ex["terminated_reason"] == "timeout"
    # ...which did not block the other action: it completes successfully.
    await w1.ok("control.execution_result", {"execution_id": by_type["usb_contents"], "status": "success",
                                             "exit_code": 0, "output_log_path": "C:/logs/1.log"})
    ex2 = await a1.ok("control.execution", {"execution_id": by_type["usb_contents"]})
    assert ex2["execution"]["status"] == "success" and ex2["output"] == ["E:/file1.txt"]
    statuses = [p.payload for p in await a1.drain_pushes() if p.type == "action.status"]
    assert {s["execution_id"] for s in statuses} >= set(by_type.values())

    # Manual termination by execution id, then the worker confirms.
    run = await a1.ok("control.action_run", {"action_id": snap["id"], "pc_id": org["w1_pc"]})
    assert next(p for p in await w1.drain_pushes() if p.type == "action.execute").payload["execution_id"] == run["execution_id"]
    await a1.ok("control.terminate", {"execution_id": run["execution_id"]})
    assert "action.terminate" in w1.push_types(await w1.drain_pushes())
    await w1.ok("control.execution_result", {"execution_id": run["execution_id"], "status": "terminated"})
    ex3 = (await a1.ok("control.execution", {"execution_id": run["execution_id"]}))["execution"]
    assert ex3["status"] == "terminated" and ex3["terminated_reason"] == "manual"
    assert await a1.err("control.terminate", {"execution_id": run["execution_id"]}) == "conflict"

    # Dashboard: enabled automations with last-fired, recent executions, live list.
    dash = await a1.ok("control.dashboard")
    assert dash["automations"][0]["event"]["id"] == ev["id"] and dash["automations"][0]["last_fired_at"]
    recent = {a["action"]["id"]: a["recent"] for a in dash["automations"][0]["actions"]}
    assert recent[shot["id"]][0]["status"] == "terminated" and dash["live"] == []
    # Disabling hides it from the dashboard and stops matching.
    await a1.ok("control.event_delete", {"event_id": ev["id"]})
    assert (await a1.ok("control.dashboard"))["automations"] == []
    assert (await w1.ok("control.signal", {"type": "usb.inserted", "data": {}}))["fired"] == 0


async def test_file_events_task_signals_and_match_filters(engine, org, connect):
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    a2 = await connect("cid-a2")
    notify = (await a1.ok("control.action_create", {"kind": "control", "builtin_type": "notify", "timeout_s": 5,
                                                    "params": {"message": "restricted touched"}}))["action"]
    ev = (await a1.ok("control.event_create", {"type": "file.modified", "match": {"path_prefix": "C:/resources/restricted"},
                                               "action_ids": [notify["id"]]}))["event"]
    # A file event outside the prefix, or from another department, does not fire.
    await w1.ok("index.event", {"event": {"op": "modify", "path": "C:/docs/x.txt", "hash": "1"}})
    await a2.ok("index.event", {"event": {"op": "modify", "path": "C:/resources/restricted/y.txt", "hash": "2"}})
    assert [p for p in await w1.drain_pushes() if p.type == "action.execute"] == []
    assert [p for p in await a2.drain_pushes() if p.type == "action.execute"] == []
    # Inside the prefix on a department PC: fires, action lands on that PC.
    await a1.ok("index.event", {"event": {"op": "modify", "path": "C:/resources/restricted/z.txt", "hash": "3"}})
    ex = next(p for p in await a1.drain_pushes() if p.type == "action.execute")
    assert ex.payload["action"]["params"] == {"message": "restricted touched"}
    assert events.last_fired(ev["id"]) is not None
    # Task signals are events too: task.started scoped to one task.
    t = await a1.ok("task.create", {"assignee_account_id": org["w1"], "description": "d", "verification_mode": "none",
                                    "confirm_none": True})
    ev2 = (await a1.ok("control.event_create", {"type": "task.started", "match": {"task_id": t["task"]["id"]},
                                                "action_ids": [notify["id"]]}))["event"]
    await w1.ok("task.start", {"task_id": t["task"]["id"]})
    assert any(p.type == "action.execute" for p in await w1.drain_pushes())
    assert events.last_fired(ev2["id"])


async def test_polled_thresholds_and_time_events(engine, org, connect):
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    metrics = (await a1.ok("control.action_create", {"kind": "monitoring", "builtin_type": "system_metrics", "timeout_s": 5}))["action"]
    cpu = (await a1.ok("control.event_create", {"type": "threshold.cpu", "match": {"percent": 80, "duration_s": 0},
                                                "action_ids": [metrics["id"]]}))["event"]
    assert cpu["condition_type"] == "polled"
    assert await a1.err("control.event_create", {"type": "time.scheduled", "match": {}, "action_ids": []}) == "invalid"
    past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    once = (await a1.ok("control.event_create", {"type": "time.scheduled", "match": {"at": past}, "action_ids": []}))["event"]
    every = (await a1.ok("control.event_create", {"type": "time.recurring", "match": {"interval_s": 3600}, "action_ids": []}))["event"]

    await w1.ok("control.metrics", {"cpu": 50, "memory": 40, "idle_s": 0})
    fired = await events.evaluate_polled(engine)
    assert fired == 2                                    # the scheduled-once and the recurring, not cpu
    assert events.last_fired(once["id"]) and events.last_fired(every["id"]) and not events.last_fired(cpu["id"])
    assert await events.evaluate_polled(engine) == 0     # once is once; recurring waits its interval
    await w1.ok("control.metrics", {"cpu": 95, "memory": 40, "idle_s": 0})
    assert await events.evaluate_polled(engine) == 1
    assert next(p for p in await w1.drain_pushes() if p.type == "action.execute").payload["action"]["builtin_type"] == "system_metrics"
    assert await events.evaluate_polled(engine) == 0     # cooldown


async def test_update_gate_rollout_escalation_and_health(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    a2 = await connect("cid-a2")
    w1 = await connect("cid-w1")
    w2 = await connect("cid-w2")
    assert await a1.err("updates.approve", {"version": "1.0.0"}) == "forbidden"
    v1 = await su.ok("updates.approve", {"version": "1.0.0"})
    assert await su.err("updates.approve", {"version": "1.0.0"}) == "conflict"
    # Nobody is confirmed on 1.0.0 yet -> 1.1.0 cannot be approved (hard gate).
    assert await su.err("updates.approve", {"version": "1.1.0"}) == "conflict"
    # Finance Admin rolls out to their department: the two workers + admin PC are told.
    roll = await a1.ok("updates.rollout_department")
    assert {t["pc_id"] for t in roll["targeted"]} == {org["a1_pc"], org["w1_pc"], org["w2_pc"]}
    assert "update.available" in w1.push_types(await w1.drain_pushes())
    assert await a1.err("updates.rollout_department", {"department_id": org["hr"]}) == "forbidden"
    # A failed first report from a fresh install leaves the PC "never confirmed" (still behind).
    r0 = await w2.ok("updates.report_status", {"version": "1.0.0", "succeeded": False})
    assert r0["current_version_id"] is None and r0["failures"] == 1
    for c in (w1, w2, a1, a2, su):
        await c.ok("updates.report_status", {"version": "1.0.0", "succeeded": True})
    health = await su.ok("updates.rollout_health")
    assert all(h["pending"] == 0 for h in health["departments"]) and health["version"]["id"] == v1["version_id"]
    # Gate opens; HR admin sees the approval; W1 fails three times -> escalated to its Admin + report.
    await su.ok("updates.approve", {"version": "1.1.0"})
    assert "update.approved" in a2.push_types(await a2.drain_pushes())
    await a1.drain_pushes()
    for i in range(3):
        r = await w1.ok("updates.report_status", {"version": "1.1.0", "succeeded": False})
        assert r["failures"] == i + 1 and r["escalated"] == (i == 2)
    assert "update.escalated" in a1.push_types(await a1.drain_pushes())
    assert (await su.ok("reports.list"))["reports"][0]["category"] == "update_status"
    mine = await a1.ok("updates.rollout_health")
    assert mine["departments"][0]["escalated"] == 1
    assert sorted(b["pc_id"] for b in mine["pcs_behind"]) == sorted([org["a1_pc"], org["w1_pc"], org["w2_pc"]])
    # Super User prompts the department; success resets the failure count.
    await su.ok("updates.prompt_admin", {"department_id": org["fin"]})
    assert "update.prompt" in a1.push_types(await a1.drain_pushes())
    r = await w1.ok("updates.report_status", {"version": "1.1.0", "succeeded": True})
    assert r["failures"] == 0 and r["target_version_id"] is None
    await asyncio.sleep(0)
