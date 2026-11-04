"""What the console's pages call (ENGINE-GAPS #23): requests to talk, small groups, reminders, a flow's stops and starts, a rule's skipped and repeated runs,
a machine's programs, and what the Actions, Restricted and Detective pages read."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from engine.control import events
from tests.conftest import requires_db
from tests.test_detective_engine import _leak
from worker_client.ossignals import diff_printers, diff_signins, parse_printers, parse_signins

pytestmark = [requires_db, pytest.mark.organisation]


async def test_a_person_asks_to_talk_and_one_admin_accepts_or_closes_it(engine, org, connect):
    a1, a2, w1 = await connect("cid-a1"), await connect("cid-a2"), await connect("cid-w1")
    asked = await w1.ok("chat.ask", {"line": "  My screen keeps  freezing "})
    assert "chat.request" in a2.push_types(await a2.drain_pushes())
    assert await w1.err("chat.ask", {"line": "again"}) == "conflict"                    # one open request per person
    assert await w1.err("chat.requests") == "forbidden"
    (r,) = (await a1.ok("chat.requests"))["requests"]
    assert r["line"] == "My screen keeps freezing" and r["host"] == "FIN-01" and r["account_id"] == org["w1"]
    opened = await a1.ok("chat.request_accept", {"request_id": asked["request_id"]})
    convo = opened["conversation"]["conversation_id"]
    assert [m["body"] for m in (await a1.ok("chat.get", {"conversation_id": convo}))["messages"]] == ["My screen keeps freezing"]
    assert "chat.request_accepted" in w1.push_types(await w1.drain_pushes())
    assert await a2.err("chat.request_accept", {"request_id": asked["request_id"]}) == "conflict"    # already answered
    assert (await a2.ok("chat.requests"))["requests"] == []
    second = await w1.ok("chat.ask", {"line": "Can I get Visio?"})
    assert await a1.err("chat.request_close", {"request_id": second["request_id"], "why": "  "}) == "invalid"
    await a1.ok("chat.request_close", {"request_id": second["request_id"], "why": "Ask your manager first"})
    told = next(p for p in await w1.drain_pushes() if p.type == "chat.request_closed").payload
    assert told["why"] == "Ask your manager first"


async def test_a_small_group_of_named_people(engine, org, connect):
    a1, w1 = await connect("cid-a1"), await connect("cid-w1")
    got = await a1.ok("chat.open", {"account_ids": [org["w1"], org["w2"], org["a1"]], "title": "Payroll move"})
    convo = got["conversation"]
    assert convo["kind"] == "group" and convo["title"] == "Payroll move" and len(convo["members"]) == 3
    await a1.ok("chat.send", {"conversation_id": convo["conversation_id"], "body": "Friday"})
    assert [c["title"] for c in (await w1.ok("chat.list"))["conversations"]] == ["Payroll move"]
    assert await a1.err("chat.open", {"account_ids": [org["w1"]]}) == "invalid"         # a pair is not a group


async def test_a_late_task_is_reminded(engine, org, connect):
    a1, w1 = await connect("cid-a1"), await connect("cid-w1")
    task = await engine.db.pool.fetchval("INSERT INTO tasks (assigner_account_id, assignee_account_id, description_raw, verification_mode) VALUES ($1, $2, 'File the report', 'none') RETURNING id",
                                         org["a1"], org["w1"])
    await a1.ok("task.remind", {"task_id": task})
    note = next(p for p in await w1.drain_pushes() if p.type == "task.reminder").payload
    assert note["description"] == "File the report"
    assert await a1.err("task.remind", {"task_id": 99999}) == "not_found" and await w1.err("task.remind", {"task_id": task}) == "forbidden"


def _flow(org) -> dict:
    return {"source_pc_id": org["a1_pc"], "source_path": "C:/out", "stages": [], "destinations": [{"destination_pc_id": org["w1_pc"], "destination_path": "C:/in"}]}


async def test_a_stopped_flow_starts_again_and_a_file_kept_beside_is_settled(engine, org, connect):
    a1, w1 = await connect("cid-a1"), await connect("cid-w1")
    flow = (await a1.ok("flow.create", _flow(org)))["flow"]
    assert await a1.err("flow.start", {"flow_id": flow["id"]}) == "conflict"            # it runs
    assert await a1.err("flow.remind", {"flow_id": flow["id"]}) == "conflict"           # it waits for nobody
    await a1.ok("flow.pause", {"flow_id": flow["id"]})
    (listed,) = (await a1.ok("flow.list"))["flows"]
    assert listed["sources"][0]["pause_reason"] == "manual" and listed["sources"][0]["paused_at"] and listed["created_at"]
    assert listed["destinations"][0]["owner_account_id"]
    assert (await a1.ok("flow.start", {"flow_id": flow["id"]}))["flow"]["status"] == "active"
    await a1.ok("flow.delete", {"flow_id": flow["id"]})
    assert (await a1.ok("flow.start", {"flow_id": flow["id"]}))["flow"]["status"] == "active"     # a stopped flow, too

    dest = flow["destinations"][0]["id"]
    await engine.db.flows.log_sync(dest, "", "external", None, conflict_resolved=True, source_relative_path="a.txt", written_path="C:/in/a-modified.txt", outcome="kept_beside")
    await w1.drain_pushes()
    assert await a1.err("flow.keep", {"flow_id": flow["id"], "path": "C:/in/other.txt", "keep": "new"}) == "not_found"
    await a1.ok("flow.keep", {"flow_id": flow["id"], "path": "C:/in/a-modified.txt", "keep": "both"})
    assert "flow.remove" not in w1.push_types(await w1.drain_pushes())
    await a1.ok("flow.keep", {"flow_id": flow["id"], "path": "C:/in/a-modified.txt", "keep": "new"})
    sent = next(p for p in await w1.drain_pushes() if p.type == "flow.remove").payload
    assert sent["settled"] is True and sent["path"] == "C:/in/a-modified.txt"


async def test_a_program_is_ended_with_a_notice_and_a_machine_updates_now_and_eight_days_of_check_ins(engine, org, connect):
    a1, w1 = await connect("cid-a1"), await connect("cid-w1")
    done = await a1.ok("machines.end_program", {"pc_id": org["w1_pc"], "name": "EXCEL.EXE"})
    sent = [p.payload["action"] for p in await w1.drain_pushes() if p.type == "action.execute"]
    assert [a["builtin_type"] for a in sent] == ["kill_process", "notify"] and "EXCEL.EXE" in sent[1]["params"]["message"] and done["execution_id"]
    assert await a1.err("update.now", {"pc_id": org["w1_pc"]}) == "conflict"            # no approved version
    assert len((await a1.ok("machines.get", {"pc_id": org["w1_pc"]}))["check_ins"]) == 8


async def test_a_scheduled_run_is_skipped_and_a_firing_runs_again_only_where_it_failed(engine, org, connect):
    a1, w1 = await connect("cid-a1"), await connect("cid-w1")
    shot = (await a1.ok("control.action_create", {"kind": "control", "builtin_type": "screenshot", "timeout_s": 10}))["action"]
    daily = (await a1.ok("control.event_create", {"type": "time.recurring", "match": {"at": "09:00"}, "pc_ids": [org["w1_pc"]], "action_ids": [shot["id"]]}))["event"]

    async def next_daily() -> dict:
        return next(c for c in (await a1.ok("automation.board"))["coming_up"] if c["event_id"] == daily["id"])
    at = (await next_daily())["at"]
    assert (await next_daily())["skipped"] is False
    await a1.ok("automation.skip", {"event_id": daily["id"], "at": at})
    assert (await next_daily())["skipped"] is True
    await a1.ok("automation.skip", {"event_id": daily["id"], "at": at, "undo": True})
    assert (await next_daily())["skipped"] is False
    await a1.ok("control.event_delete", {"event_id": daily["id"]})
    rule = (await a1.ok("control.event_create", {"type": "time.recurring", "match": {"interval_s": 60}, "pc_ids": [org["w1_pc"]], "action_ids": [shot["id"]]}))["event"]
    now = datetime.now(timezone.utc)
    await a1.ok("automation.skip", {"event_id": rule["id"], "at": now.isoformat()})
    await w1.drain_pushes()
    assert await events.evaluate_polled(engine) == 0                                    # the run due now passes
    assert "action.execute" not in w1.push_types(await w1.drain_pushes())
    events._last_fired[rule["id"]] = now - timedelta(minutes=5)
    assert await events.evaluate_polled(engine) == 1                                    # the next one comes as usual
    run = next(p for p in await w1.drain_pushes() if p.type == "action.execute").payload
    assert await a1.err("automation.run_again", {"event_id": rule["id"], "at": now.isoformat()}) == "conflict"       # nothing went wrong yet
    await w1.ok("control.execution_result", {"execution_id": run["execution_id"], "status": "failed", "exit_code": 1})
    again = await a1.ok("automation.run_again", {"event_id": rule["id"], "at": datetime.now(timezone.utc).isoformat()})
    assert [r["pc_id"] for r in again["runs"]] == [org["w1_pc"]]
    runs = (await a1.ok("actions.runs", {"hand": True}))["runs"]
    assert runs[0]["who"] == "You"


async def test_failed_sign_ins_fire_at_their_count_and_a_printer_going_offline_is_a_signal(engine, org, connect):
    a1, w1 = await connect("cid-a1"), await connect("cid-w1")
    shot = (await a1.ok("control.action_create", {"kind": "control", "builtin_type": "screenshot", "timeout_s": 10}))["action"]
    await a1.ok("control.event_create", {"type": "threshold.signin", "match": {"count": 3, "window_s": 600}, "action_ids": [shot["id"]]})
    made = await a1.ok("control.event_create", {"type": "printer.offline", "match": {"name": "HP-2"}, "action_ids": [shot["id"]]})
    assert [(await w1.ok("control.signal", {"type": "threshold.signin", "data": {"name": "ama"}}))["fired"] for _ in range(4)] == [0, 0, 1, 0]
    assert (await w1.ok("control.signal", {"type": "printer.offline", "data": {"name": "HP-1"}}))["fired"] == 0
    assert (await w1.ok("control.signal", {"type": "printer.offline", "data": {"name": "HP-2"}}))["fired"] == 1
    history = await a1.ok("control.event_history", {"event_id": made["event"]["id"]})
    assert history["firings"][0]["detail"] == "HP-2 stopped responding" and history["firings"][0]["by_hand"] is False
    words = {r["type"]: r["when"] for r in (await a1.ok("automation.board"))["rules"]}
    assert words["threshold.signin"] == "3 sign-ins fail within 10 minutes" and words["printer.offline"] == "a shared printer stops responding"


def test_what_the_worker_reads_for_printers_and_sign_ins():
    now = parse_printers("HP-1\tFalse\t3\nHP-2\tTrue\t3\nHP-3\tFalse\t7\n")
    assert now == {"HP-1": True, "HP-2": False, "HP-3": False}
    assert diff_printers({"HP-1": True, "HP-2": True, "HP-3": False}, now) == [("printer.offline", {"name": "HP-2"})]
    xml = "<Event><EventRecordID>7</EventRecordID><Data Name='TargetUserName'>ama</Data></Event><Event><EventRecordID>8</EventRecordID><Data Name='TargetUserName'>kojo</Data></Event>"
    assert parse_signins(xml) == {"7": "ama", "8": "kojo"}
    assert diff_signins({"7": "ama"}, parse_signins(xml)) == [("threshold.signin", {"name": "kojo"})]


async def test_what_the_actions_issues_and_detective_pages_read(engine, org, connect):
    a1, w1 = await connect("cid-a1"), await connect("cid-w1")
    await a1.ok("control.action_create", {"kind": "control", "builtin_type": "reboot", "timeout_s": 60})
    lib = await a1.ok("control.action_list")
    assert lib["builtin"]["reboot"]["risky"] is True and lib["builtin"]["screenshot"]["impact"] == "Users are not interrupted."
    assert lib["actions"]["control"][0]["risky"] is True and lib["actions"]["control"][0]["created_by_name"]
    await _leak(engine, org["w1_pc"])
    (case,) = (await a1.ok("detective.cases"))["cases"]
    assert case["restricted"] is True
    await a1.ok("index.event", {"event": {"op": "create", "path": "C:/resources/restricted/s.xlsx", "hash": "S"}})
    await w1.ok("index.event", {"event": {"op": "copy", "path": "C:/Users/ama/Desktop/s-copy.xlsx", "hash": "S"}})
    issue = next(i for i in (await a1.ok("issues.list"))["issues"] if i["detail"].get("file") == "s-copy.xlsx")      # the detail is on the list itself
    whats = [e["what"] for e in (await a1.ok("issues.get", {"issue_id": issue["id"]}))["timeline"]]
    assert "Report written; every Admin sees it, and any of them may act on it" in whats and any(w.startswith("Restricted file raised on FIN-01") for w in whats)
    await w1.drain_pushes()
    await a1.ok("issues.act", {"issue_id": issue["id"], "key": "rule"})
    assert "action.execute" in w1.push_types(await w1.drain_pushes())
    rules = (await a1.ok("automation.board"))["rules"]
    assert any(r["name"] == "Delete s-copy.xlsx on FIN-01" and r["type"] == "file.created" for r in rules)


async def test_any_admin_closes_a_task_and_the_record_says_who_and_never_the_person_it_was_given_to(engine, org, connect):
    a2, w1 = await connect("cid-a2"), await connect("cid-w1")
    task = await engine.db.pool.fetchval("INSERT INTO tasks (assigner_account_id, assignee_account_id, description_raw, verification_mode) VALUES ($1, $2, 'File it', 'none') RETURNING id",
                                         org["a1"], org["w1"])
    assert await w1.err("task.verify", {"task_id": task, "outcome": "complete"}) == "forbidden"
    await a2.ok("task.verify", {"task_id": task, "outcome": "complete"})                # another Admin than the one who gave it
    who = await engine.db.pool.fetchval("SELECT verified_by_account_id FROM manual_verifications WHERE task_id = $1", task)
    assert who == org["a2"]


async def test_every_admin_covers_every_flow_and_mark_and_the_trail_says_who(engine, org, connect):
    a1, a2 = await connect("cid-a1"), await connect("cid-a2")
    flow = (await a1.ok("flow.create", _flow(org)))["flow"]
    await a2.ok("flow.pause", {"flow_id": flow["id"]})                                  # another Admin than the one who made it
    who = await engine.db.pool.fetchval("SELECT actor_account_id FROM audit_log WHERE action_type = 'flow.paused' ORDER BY id DESC LIMIT 1")
    assert who == org["a2"]
    from engine.flow import guard

    mark = await engine.db.pool.fetchval(
        "INSERT INTO resource_marks (kind, name, by_account_id, pc_id, path, keep) VALUES ('folder', 'secret', $1, $2, 'C:/secret', 'machine') RETURNING id", org["a1"], org["a1_pc"])
    await a2.ok("marks.unmark", {"mark_id": mark})
    assert await engine.db.pool.fetchval("SELECT unmarked_by_account_id FROM resource_marks WHERE id = $1", mark) == org["a2"]
    assert guard.can_decide(a2_ident(org), {"mark_id": mark, "mark_owner_account_id": org["a1"]}) is True
    assert guard.deciders_text(guard.Blocker(kind="mark", name="x", reason="r")) == "an Admin"


def a2_ident(org: dict):
    from types import SimpleNamespace

    return SimpleNamespace(role="admin", account_id=org["a2"], department_id=None)


async def test_what_the_drawers_send(engine, org, connect):
    a1, a2 = await connect("cid-a1"), await connect("cid-a2")
    shot = (await a1.ok("control.action_create", {"kind": "control", "builtin_type": "screenshot", "timeout_s": 10}))["action"]
    rule = (await a1.ok("control.event_create", {"type": "usb.inserted", "action_ids": [shot["id"]], "action_limits": {str(shot["id"]): 45}}))["event"]
    assert rule["actions"][0]["timeout_seconds"] == 45 and rule["actions"][0]["rule_limit_s"] == 45
    assert await a1.err("control.event_create", {"type": "usb.inserted", "action_ids": [shot["id"]], "action_limits": {str(shot["id"]): 0}}) == "invalid"
    registered = await a1.ok("hierarchy.pc_register", {"hostname": "NEW-PC", "pc_type": "client_pc"})
    assert (await engine.db.accounts.pc(registered["pc_id"]))["department_id"] is None
    flow = await a1.ok("flow.create", {"source_pc_id": org["a1_pc"], "source_path": "C:/out", "stages": [],
                                       "destinations": [{"destination_pc_id": org["a2_pc"], "destination_path": "", "let_them_choose": True, "note": "  For the audit   pack "}]})
    sent = next(p for p in await a2.drain_pushes() if p.type == "flow.consent_request").payload
    assert sent["note"] == "For the audit pack" and flow["flow"]["destinations"][0]["note"] == "For the audit pack"


def test_a_sign_in_outside_working_hours(monkeypatch):
    real = datetime

    class Clock(datetime):
        at = real(2026, 11, 4, 22, 0, tzinfo=timezone.utc)                              # a Wednesday night

        @classmethod
        def now(cls, tz=None):
            return cls.at

    monkeypatch.setattr(events, "datetime", Clock)
    spec = {"match": {"outside_hours": True}}
    assert events.matches(spec, {"user": "ama"}) is True
    Clock.at = real(2026, 11, 4, 10, 0, tzinfo=timezone.utc)
    assert events.matches(spec, {"user": "ama"}) is False
    Clock.at = real(2026, 11, 7, 10, 0, tzinfo=timezone.utc)                            # a Saturday
    assert events.matches(spec, {"user": "ama"}) is True
