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
import base64
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
    # What a run returned is kept with it: a picture (asked for, audited, size-capped, its own
    # department and the Super User only) and, after 90 days, cleared but still said to have been.
    pic = base64.b64encode(b"PNG fake").decode()
    assert await w1.err("control.execution_image", {"execution_id": by_type["usb_contents"], "mime": "image/gif",
                                                    "data": pic}) == "invalid"
    big = base64.b64encode(b"x" * (executions.IMAGE_MAX + 1)).decode()
    assert await w1.err("control.execution_image", {"execution_id": by_type["usb_contents"], "mime": "image/png",
                                                    "data": big}) == "invalid"
    await w1.ok("control.execution_image", {"execution_id": by_type["usb_contents"], "mime": "image/png", "data": pic})
    assert (await a1.ok("control.execution_image_get", {"execution_id": by_type["usb_contents"]}))["data"] == pic
    a2 = await connect("cid-a2")
    assert await a2.err("control.execution_image_get", {"execution_id": by_type["usb_contents"]}) == "forbidden"
    assert await a1.err("control.execution_image_get", {"execution_id": by_type["screenshot"]}) == "not_found"
    viewed = await engine.db.audit.recent(limit=5)
    assert any(r["action_type"] == "execution.image_viewed" for r in viewed)
    assert await engine.db.control.clear_outputs_older_than(0) == 2
    gone = await a1.ok("control.execution", {"execution_id": by_type["usb_contents"]})
    assert gone["expired"] is True and gone["output"] == [] and gone["execution"]["has_image"] is False
    assert await a1.err("control.execution_image_get", {"execution_id": by_type["usb_contents"]}) == "not_found"
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


async def test_a_tier_is_matched_and_what_an_automation_did_is_read_back(engine, org, connect):
    """AU04 / AU09: "a Restricted file is changed" matches the file's tier, not a typed path; the
    automation's history names the machine, the file, and each action's outcome under its firing."""
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    notify = (await a1.ok("control.action_create", {"kind": "control", "builtin_type": "notify", "timeout_s": 5,
                                                    "params": {"message": "m"}, "name": "Notify me"}))["action"]
    assert await a1.err("control.event_create", {"type": "file.modified", "match": {"tier": "secret"},
                                                 "action_ids": []}) == "invalid"
    ev = (await a1.ok("control.event_create", {"type": "file.modified", "match": {"tier": "restricted"},
                                               "action_ids": [notify["id"]]}))["event"]
    await a1.ok("index.event", {"event": {"op": "modify", "path": "C:/docs/plain.txt", "hash": "p"}})
    assert [p for p in await a1.drain_pushes() if p.type == "action.execute"] == []
    await a1.ok("index.event", {"event": {"op": "modify", "path": "C:/resources/restricted/budget.xlsx", "hash": "b"}})
    run = next(p for p in await a1.drain_pushes() if p.type == "action.execute").payload
    await a1.ok("control.execution_result", {"execution_id": run["execution_id"], "status": "success", "exit_code": 0})

    hist = await a1.ok("control.event_history", {"event_id": ev["id"]})
    assert hist["fired_today"] == 1 and hist["running"] == []
    firing = hist["firings"][0]
    assert firing["subject"] == "budget.xlsx" and firing["hostname"]
    assert [(r["action_name"], r["status"]) for r in firing["runs"]] == [("Notify me", "success")]
    assert await w1.err("control.event_history", {"event_id": ev["id"]}) == "forbidden"

    # the level a threshold is drawn against: where this department's machines sit now
    await w1.ok("control.metrics", {"cpu": 30, "memory": 50, "idle_s": 5})
    lv = await a1.ok("control.levels")
    assert lv["machines"] == 1 and lv["cpu"] == [30.0, 30.0]
    # ...and a typical day from the stored samples (one per machine per interval; the next report
    # inside the interval is not stored)
    await w1.ok("control.metrics", {"cpu": 90, "memory": 50, "idle_s": 5})
    typical = (await a1.ok("control.levels"))["typical"]
    assert typical["samples"] == 1 and typical["cpu"] == [30.0, 30.0] and typical["machines"] == 1
    assert (await a1.ok("control.levels", {"pc_ids": [org["w2_pc"]]}))["typical"] is None


async def test_a_time_automation_runs_its_actions_on_its_machines(engine, org, connect):
    """A time event belongs to no one machine: its actions run on each machine it covers (named
    machines, or the creator's department), never on a machine id of 0."""
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    lock = (await a1.ok("control.action_create", {"kind": "control", "builtin_type": "lock_session", "timeout_s": 5,
                                                  "params": {"duration_s": 60}}))["action"]
    past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    await a1.ok("control.event_create", {"type": "time.scheduled", "match": {"at": past}, "pc_ids": [org["w1_pc"]],
                                         "action_ids": [lock["id"]]})
    assert await events.evaluate_polled(engine) == 1
    run = next(p for p in await w1.drain_pushes() if p.type == "action.execute").payload
    assert run["action"]["builtin_type"] == "lock_session"
    assert (await engine.db.control.execution(run["execution_id"]))["target_pc_id"] == org["w1_pc"]



async def test_a_super_user_automation_is_seen_from_a_department_by_its_own_machines(engine, org, connect):
    """An organisation-wide automation (the Super User's, no machines named) runs on every
    department's machines. A department's Admin sees it read-only, and what it did there counts
    only their machines: HR's Admin never sees Finance's runs."""
    su = await connect("cid-su")
    a1 = await connect("cid-a1")      # Finance: FIN-ADM, FIN-01, FIN-02
    a2 = await connect("cid-a2")      # HR: HR-ADM
    log_ = (await su.ok("control.action_create", {"kind": "control", "builtin_type": "notify", "timeout_s": 5, "params": {"message": "m"},
                                                  "name": "Log it"}))["action"]
    past = (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()
    ev = (await su.ok("control.event_create", {"type": "time.scheduled", "match": {"at": past},
                                               "action_ids": [log_["id"]]}))["event"]
    assert await events.evaluate_polled(engine) == 1
    runs = await engine.db.control.executions_for_event(ev["id"])
    fin = {org["a1_pc"], org["w1_pc"], org["w2_pc"]}
    assert {r["target_pc_id"] for r in runs} == fin | {org["a2_pc"]}       # every department's machines

    # Both departments see it, marked read-only; neither can change or switch it.
    for admin in (a1, a2):
        listed = {e["id"]: e for e in (await admin.ok("control.event_list"))["events"]}
        assert listed[ev["id"]]["org_wide"] and listed[ev["id"]]["read_only"]
        assert await admin.err("control.event_update", {"event_id": ev["id"], "enabled": False}) == "forbidden"
        assert await admin.err("control.event_delete", {"event_id": ev["id"]}) == "forbidden"
    su_list = {e["id"]: e for e in (await su.ok("control.event_list"))["events"]}
    assert su_list[ev["id"]]["org_wide"] and not su_list[ev["id"]]["read_only"]

    # What it did, from each department: only its own machines, and how many of them it reached.
    hist_fin = await a1.ok("control.event_history", {"event_id": ev["id"]})
    assert {r["target_pc_id"] for f in hist_fin["firings"] for r in f["runs"]} == fin
    assert hist_fin["firings"][0]["machines"] == 3
    hist_hr = await a2.ok("control.event_history", {"event_id": ev["id"]})
    assert {r["target_pc_id"] for f in hist_hr["firings"] for r in f["runs"]} == {org["a2_pc"]}
    assert hist_hr["firings"][0]["machines"] == 1
    hist_su = await su.ok("control.event_history", {"event_id": ev["id"]})
    assert hist_su["firings"][0]["machines"] == 4

    # The dashboard: HR's live runs are HR's only.
    dash = await a2.ok("control.dashboard")
    assert {x["target_pc_id"] for x in dash["live"]} <= {org["a2_pc"]}
    mine = next(a for a in dash["automations"] if a["event"]["id"] == ev["id"])
    assert mine["event"]["read_only"]
    assert {r["target_pc_id"] for a in mine["actions"] for r in a["recent"]} <= {org["a2_pc"]}

    # One naming only Finance's machines does not reach HR at all.
    only_fin = (await su.ok("control.event_create", {"type": "time.scheduled", "match": {"at": past},
                                                     "pc_ids": [org["w1_pc"]], "action_ids": [log_["id"]]}))["event"]
    assert only_fin["id"] in {e["id"] for e in (await a1.ok("control.event_list"))["events"]}
    assert only_fin["id"] not in {e["id"] for e in (await a2.ok("control.event_list"))["events"]}
    assert await a2.err("control.event_history", {"event_id": only_fin["id"]}) == "forbidden"


async def test_the_shelves_count_files_per_tier_in_the_department(engine, org, connect):
    """RS03: an Admin's shelves are their workstation's tiers, each with how many files sit on it."""
    a1 = await connect("cid-a1")
    await a1.ok("index.event", {"event": {"op": "create", "path": "C:/resources/restricted/pay.xlsx", "hash": "r1"}})
    await a1.ok("index.event", {"event": {"op": "create", "path": "C:/resources/common/menu.pdf", "hash": "c1"}})
    await a1.ok("index.event", {"event": {"op": "create", "path": "C:/resources/common/map.pdf", "hash": "c2"}})
    shelves = {s["folder"]: s["files"] for s in (await a1.ok("resource.shelves"))["shelves"]}
    assert shelves == {"restricted": 1, "workers": 0, "common": 2}
    w1 = await connect("cid-w1")
    assert await w1.err("resource.shelves") == "forbidden"


async def test_a_machine_watches_only_the_os_signals_an_automation_waits_for(engine, org, connect):
    """The Worker asks which OS signals matter on its machine (and their match blocks), is told to ask
    again when an automation changes, and relays a file being opened like any other OS signal."""
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    w2 = await connect("cid-w2")
    assert (await w1.ok("control.signal_interest"))["interest"] == {}
    note = (await a1.ok("control.action_create", {"kind": "control", "builtin_type": "notify", "timeout_s": 5,
                                                  "params": {"message": "opened"}}))["action"]
    ev = (await a1.ok("control.event_create", {"type": "file.accessed", "pc_ids": [org["w1_pc"]],
                                               "match": {"path_prefix": "C:/Finance"},
                                               "action_ids": [note["id"]]}))["event"]
    assert "control.interest_changed" in w1.push_types(await w1.drain_pushes())
    assert (await w1.ok("control.signal_interest"))["interest"] == {"file.accessed": [{"path_prefix": "C:/Finance"}]}
    assert (await w2.ok("control.signal_interest"))["interest"] == {}          # named machines only
    res = await w1.ok("control.signal", {"type": "file.accessed",
                                         "data": {"path": "C:/Finance/budget.xlsx", "process": "EXCEL.EXE"}})
    assert res["fired"] == 1
    assert (await w1.ok("control.signal", {"type": "file.accessed", "data": {"path": "C:/Other/x.txt"}}))["fired"] == 0
    await a1.ok("control.event_delete", {"event_id": ev["id"]})
    assert "control.interest_changed" in w1.push_types(await w1.drain_pushes())
    assert (await w1.ok("control.signal_interest"))["interest"] == {}


async def test_built_in_actions_take_the_settings_the_design_asks_for(engine, org, connect):
    a1 = await connect("cid-a1")

    def make(builtin, params, timeout=5):
        return a1.call("control.action_create", {"kind": "control", "builtin_type": builtin, "timeout_s": timeout,
                                                 "params": params})

    ok = (await make("notify", {"message": "  Back up your files  ", "stay_s": "45"})).result["action"]
    assert ok["params"] == {"message": "Back up your files", "stay_s": 45}
    assert ok["timeout_seconds"] == 5 + 70          # 45 s on screen + settling: a run is never cut short
    lock = (await make("lock_session", {"duration_s": 900, "message": "Meeting"})).result["action"]
    assert lock["timeout_seconds"] == 930
    reboot = (await make("reboot", {"delay_s": 300, "message": "Updates"})).result["action"]
    assert reboot["params"]["delay_s"] == 300 and reboot["timeout_seconds"] == 330
    assert (await make("reboot", {})).result["action"]["params"] == {}                      # all optional

    for builtin, params in [("notify", {"message": "  "}), ("notify", {"message": "x", "stay_s": -1}),
                            ("notify", {"message": "x", "stay_s": "soon"}), ("lock_session", {"duration_s": 0}),
                            ("reboot", {"delay_s": 99999}), ("reboot", {"colour": "red"})]:
        assert (await make(builtin, params)).error["code"] == "invalid", (builtin, params)
    upd = await a1.ok("control.action_update", {"action_id": lock["id"], "params": {"duration_s": 1800}})
    assert upd["action"]["timeout_seconds"] == 1830
    assert await a1.err("control.action_update", {"action_id": lock["id"], "params": {"duration_s": -5}}) == "invalid"


async def test_programs_are_picked_from_what_runs_and_what_is_installed(engine, org, connect):
    a1 = await connect("cid-a1")
    a2 = await connect("cid-a2")
    w1 = await connect("cid-w1")
    w2 = await connect("cid-w2")
    await w1.ok("control.inventory", {"running": [{"name": "EXCEL.EXE", "count": 2, "memory": 500},
                                                  {"name": "chrome.exe", "count": 9, "memory": 900}],
                                      "installed": [{"name": "Microsoft Excel", "command": "C:/Office/EXCEL.EXE"},
                                                    {"name": "Notepad", "command": None}]})
    await w2.ok("control.inventory", {"running": [{"name": "excel.exe", "count": 1, "memory": 100}],
                                      "installed": [{"name": "Microsoft Excel", "command": None}]})
    res = await a1.ok("control.programs")
    running = {r["name"].lower(): r for r in res["running"]}
    assert running["excel.exe"]["machines"] == 2 and sorted(running["excel.exe"]["pc_ids"]) == sorted([org["w1_pc"], org["w2_pc"]])
    assert running["chrome.exe"]["machines"] == 1 and res["reporting"] == 2
    assert res["running"][0]["name"].lower() == "excel.exe"                       # most widespread first
    excel = next(i for i in res["installed"] if i["name"] == "Microsoft Excel")
    assert excel["machines"] == 2 and excel["command"] == "C:/Office/EXCEL.EXE"   # a command found anywhere is kept
    # one machine: only what is installed there
    one = await a1.ok("control.programs", {"pc_ids": [org["w1_pc"]]})
    assert sorted(i["name"] for i in one["installed"]) == ["Microsoft Excel", "Notepad"]
    # scope: HR's Admin sees none of Finance's machines; a worker may not ask at all
    assert (await a2.ok("control.programs"))["running"] == []
    assert await a2.err("control.programs", {"pc_ids": [org["w1_pc"]]}) == "forbidden"
    assert await w1.err("control.programs") == "forbidden"
    # the list is replaced, never grown; junk is dropped
    await w1.ok("control.inventory", {"running": [{"name": ""}, "junk", {"name": "calc.exe"}]})
    assert [r["name"] for r in (await a1.ok("control.programs", {"pc_ids": [org["w1_pc"]]}))["running"]] == ["calc.exe"]
    assert len((await a1.ok("control.programs", {"pc_ids": [org["w1_pc"]]}))["installed"]) == 2   # untouched


async def test_a_file_action_uses_each_machines_own_path(engine, org, connect):
    """The same file sits at different paths on different machines: the Admin names it (by name or content hash),
    and each machine is sent the path the file index has for it. No copy, or several, is said plainly."""
    a1 = await connect("cid-a1")
    a2 = await connect("cid-a2")
    w1 = await connect("cid-w1")
    w2 = await connect("cid-w2")
    idx = engine.db.file_index
    await idx.upsert(org["w1_pc"], "C:/Finance/budget.xlsx", "budget.xlsx", "h-budget", None, None, "idle_sweep")
    await idx.upsert(org["w2_pc"], "D:/Docs/Budget.xlsx", "Budget.xlsx", "h-budget", None, None, "idle_sweep")

    # naming the file by name and by path at once (or by neither) is refused
    for params in ({"new_name": "x.xlsx", "path": "C:/a.txt", "find_name": "a.txt"}, {"new_name": "x.xlsx"}):
        assert await a1.err("control.action_create", {"kind": "control", "builtin_type": "rename_file", "timeout_s": 20,
                                                      "params": params}) == "invalid"

    where = await a1.ok("control.file_locations", {"find_name": "budget.xlsx"})
    assert where["found"] == 2 and {m["hostname"]: m["paths"] for m in where["machines"] if m["paths"]} == {
        "FIN-01": ["C:/Finance/budget.xlsx"], "FIN-02": ["D:/Docs/Budget.xlsx"]}
    assert (await a1.ok("control.file_locations", {"find_hash": "h-budget"}))["found"] == 2
    assert await a1.err("control.file_locations", {}) == "invalid"
    assert await a2.err("control.file_locations", {"find_name": "budget.xlsx", "pc_ids": [org["w1_pc"]]}) == "forbidden"

    rename = (await a1.ok("control.action_create", {"kind": "control", "builtin_type": "rename_file", "timeout_s": 20,
                                                    "params": {"find_name": "budget.xlsx", "new_name": "budget-old.xlsx"}}))["action"]
    assert rename["params"] == {"find_name": "budget.xlsx", "new_name": "budget-old.xlsx"}
    await a1.ok("control.action_run", {"action_id": rename["id"], "department_id": org["fin"]})
    sent = {}
    for who, w in (("w1", w1), ("w2", w2)):
        run = next(p for p in await w.drain_pushes() if p.type == "action.execute").payload
        sent[who] = run["action"]["params"]
    assert sent["w1"] == {"new_name": "budget-old.xlsx", "path": "C:/Finance/budget.xlsx"}      # each its own path
    assert sent["w2"] == {"new_name": "budget-old.xlsx", "path": "D:/Docs/Budget.xlsx"}

    # a second copy on FIN-01 and none on FIN-02: each is reported, neither is guessed at, nothing is sent
    await idx.upsert(org["w1_pc"], "C:/Old/budget.xlsx", "budget.xlsx", "h-old", None, None, "idle_sweep")
    await engine.db.pool.execute("DELETE FROM file_index WHERE pc_id = $1", org["w2_pc"])
    await a1.ok("control.action_run", {"action_id": rename["id"], "department_id": org["fin"]})
    assert [p for w in (w1, w2) for p in await w.drain_pushes() if p.type == "action.execute"] == []
    runs = {}
    for r in await engine.db.control.last_executions_for_action(rename["id"], limit=10):    # newest first
        runs.setdefault(r["target_pc_id"], r)
    assert runs[org["w1_pc"]]["status"] == "failed" and "2 copies" in runs[org["w1_pc"]]["summary"]
    assert runs[org["w2_pc"]]["status"] == "failed" and "not on this machine" in runs[org["w2_pc"]]["summary"]
    where = await a1.ok("control.file_locations", {"find_name": "budget.xlsx"})
    assert (where["found"], where["missing"], where["several"]) == (0, 2, 1)     # FIN-02 and the Admin's own PC have none

    # a plain path still goes to every machine unchanged
    fixed = (await a1.ok("control.action_create", {"kind": "control", "builtin_type": "restore_file", "timeout_s": 20,
                                                   "params": {"path": "C:/Same/everywhere.txt"}}))["action"]
    await a1.ok("control.action_run", {"action_id": fixed["id"], "pc_id": org["w1_pc"]})
    assert next(p for p in await w1.drain_pushes() if p.type == "action.execute").payload["action"]["params"] == {
        "path": "C:/Same/everywhere.txt"}
