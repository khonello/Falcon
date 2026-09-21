"""Repository tests (skipped without FALCON_TEST_DATABASE_URL).

These pin the rules database-schema.md 12 delegates to the data-access layer: display-name
non-propagation, listener scoping, report visibility being additive, polymorphic-ref
validation, and the audit purge being the only delete.
"""

from __future__ import annotations

from datetime import timedelta

import pytest

from engine.database import Conflict, Database, _now
from tests.conftest import requires_db

pytestmark = requires_db


async def seed(db: Database) -> dict[str, int]:
    """Super User; Finance (Admin A1 + Workers W1, W2); HR (Admin A2)."""
    acc = db.accounts
    su = await acc.create("super_user", None, None)
    fin = await acc.create_department("Finance", su)
    hr = await acc.create_department("HR", su)
    su_pc = await acc.create_pc("SU-PC", None, "super_user_workstation", "cid-su")
    a1_pc = await acc.create_pc("FIN-ADM", fin, "admin_workstation", "cid-a1")
    w1_pc = await acc.create_pc("FIN-01", fin, "client_pc", "cid-w1")
    w2_pc = await acc.create_pc("FIN-02", fin, "client_pc", "cid-w2")
    a2_pc = await acc.create_pc("HR-ADM", hr, "admin_workstation", "cid-a2")
    await db.pool.execute("UPDATE accounts SET bound_pc_id = $1 WHERE id = $2", su_pc, su)
    a1 = await acc.create("admin", fin, a1_pc)
    w1 = await acc.create("worker", fin, w1_pc)
    w2 = await acc.create("worker", fin, w2_pc)
    a2 = await acc.create("admin", hr, a2_pc)
    return {"su": su, "fin": fin, "hr": hr, "a1": a1, "w1": w1, "w2": w2, "a2": a2,
            "su_pc": su_pc, "a1_pc": a1_pc, "w1_pc": w1_pc, "w2_pc": w2_pc, "a2_pc": a2_pc}


# --- identity -----------------------------------------------------------------------------------

async def test_by_client_id_resolves_bound_account(db: Database):
    ids = await seed(db)
    acct = await db.accounts.by_client_id("cid-w1")
    assert acct and acct["id"] == ids["w1"] and acct["role"] == "worker" and acct["hostname"] == "FIN-01"
    await db.accounts.offboard(ids["w1"])
    assert await db.accounts.by_client_id("cid-w1") is None      # offboarded = inactive, row kept
    assert (await db.accounts.by_id(ids["w1"]))["status"] == "offboarded"


async def test_display_names_never_propagate_across_layers(db: Database):
    ids = await seed(db)
    # Super User privately labels Admin A1; A1 sets a self-facing name.
    await db.accounts.grant_display_name(ids["su"], ids["a1"], "Finance lead (private)")
    await db.accounts.set_self_name(ids["a1"], "Sam")
    assert await db.accounts.display_name_for(ids["su"], ids["a1"]) == "Finance lead (private)"
    # A Worker below A1 sees A1's own name, never the Super User's label.
    assert await db.accounts.display_name_for(ids["w1"], ids["a1"]) == "Sam"
    # Another Admin sees the self name too, never the label.
    assert await db.accounts.display_name_for(ids["a2"], ids["a1"]) == "Sam"
    # Composed fallback when nothing is set: derived, never stored.
    assert await db.accounts.display_name_for(ids["su"], ids["w2"]) == f"FIN-02-Finance-{ids['w2']}"
    # Re-granting replaces the label (one per namer/named pair).
    await db.accounts.grant_display_name(ids["su"], ids["a1"], "Lead")
    assert await db.accounts.display_name_for(ids["su"], ids["a1"]) == "Lead"


# --- sessions -----------------------------------------------------------------------------------

async def test_session_open_conflict_and_release(db: Database):
    ids = await seed(db)
    native = await db.sessions.open(ids["w1_pc"], ids["w1"], "native", None, False)
    with pytest.raises(Conflict):
        await db.sessions.open(ids["w1_pc"], ids["a1"], "traversal", _now() + timedelta(minutes=30), False)
    assert await db.sessions.end(native, "superior_ended") is True
    assert await db.sessions.end(native, "superior_ended") is False   # already ended
    trav = await db.sessions.open(ids["w1_pc"], ids["a1"], "traversal", _now() + timedelta(minutes=30), False)
    active = await db.sessions.active_for_pc(ids["w1_pc"])
    assert active["id"] == trav and active["occupant_role"] == "admin"
    assert (await db.sessions.active_for_account(ids["a1"]))["id"] == trav


async def test_expired_sessions_are_listed(db: Database):
    ids = await seed(db)
    past = await db.sessions.open(ids["w1_pc"], ids["a1"], "traversal", _now() - timedelta(seconds=1), False)
    await db.sessions.open(ids["w2_pc"], ids["a1"], "traversal", _now() + timedelta(minutes=5), False)
    expired = await db.sessions.list_expired()
    assert [s["id"] for s in expired] == [past]
    await db.sessions.extend(past, _now() + timedelta(minutes=10))
    assert await db.sessions.list_expired() == []
    assert (await db.sessions.by_id(past))["extended_count"] == 1


async def test_available_helpers_excludes_busy_and_opted_out(db: Database):
    ids = await seed(db)
    assert await db.sessions.available_helpers(None, ids["a1"]) == []       # nobody opted in
    await db.accounts.set_assistance_available(ids["a2"], True)
    helpers = await db.sessions.available_helpers(None, ids["a1"])
    assert [h["id"] for h in helpers] == [ids["a2"]]
    assert await db.sessions.available_helpers(ids["fin"], ids["a1"]) == []  # wrong department
    # A2 traverses somewhere -> no longer available, moment-in-time.
    await db.sessions.open(ids["w1_pc"], ids["a2"], "traversal", _now() + timedelta(minutes=5), False)
    assert await db.sessions.available_helpers(None, ids["a1"]) == []


# --- file index ---------------------------------------------------------------------------------

async def test_file_index_upsert_search_scope(db: Database):
    ids = await seed(db)
    fi = db.file_index
    common = await fi.upsert(ids["w1_pc"], "C:/resources/plan.docx", "plan.docx", "h1", "common", None, "event")
    await fi.upsert(ids["a1_pc"], "C:/resources/restricted/salaries.xlsx", "salaries.xlsx", "h2", "restricted", None, "event")
    await fi.upsert(ids["a1_pc"], "C:/resources/workers/plan-fin.docx", "plan-fin.docx", "h3", "worker_dept", ids["fin"], "idle_sweep")
    await fi.upsert(ids["a2_pc"], "C:/resources/workers/plan-hr.docx", "plan-hr.docx", "h4", "worker_dept", ids["hr"], "event")
    # Upsert keeps the hash when a later event omits it, and updates last_seen.
    again = await fi.upsert(ids["w1_pc"], "C:/resources/plan.docx", "plan.docx", None, None, None, "idle_sweep")
    assert again == common and (await fi.get(common))["content_hash"] == "h1"

    from engine.resource.resource import allowed_tags_for
    names = lambda rows: sorted(r["filename"] for r in rows)
    assert names(await fi.search("plan", allowed_tags=allowed_tags_for("worker", ids["fin"]))) == ["plan-fin.docx", "plan.docx"]
    assert names(await fi.search("", allowed_tags=allowed_tags_for("admin", ids["fin"]))) == ["plan-fin.docx", "plan.docx", "salaries.xlsx"]
    assert names(await fi.search("", allowed_tags=allowed_tags_for("super_user", None))) == ["plan.docx", "salaries.xlsx"]
    assert [r["pc_id"] for r in await fi.by_name("PLAN.docx")] == [ids["w1_pc"]]
    assert await fi.by_name("plan.docx", pc_ids=[ids["a1_pc"]]) == []
    assert len(await fi.by_hash("h2")) == 1


# --- tasks --------------------------------------------------------------------------------------

async def test_task_create_links_program_to_file_and_manual_verification_completes(db: Database):
    ids = await seed(db)
    task_id = await db.tasks.create(
        {"assigner_account_id": ids["a1"], "assignee_account_id": ids["w1"],
         "description_raw": "Use Excel to update budget.xlsx by Friday", "verification_mode": "stack"},
        [{"sequence": 1, "target_type": "file", "intent": "update", "proposed_filename": "budget.xlsx"},
         {"sequence": 2, "target_type": "program", "intent": "used_with_file", "program_name": "excel",
          "linked_file_sequence": 1}])
    task = await db.tasks.get(task_id)
    assert task["status"] == "active" and len(task["items"]) == 2
    file_item, prog_item = task["items"]
    assert prog_item["linked_file_verification_item_id"] == file_item["id"]

    await db.tasks.mark_started(task_id)
    assert (await db.tasks.get(task_id))["status"] == "in_progress"
    await db.tasks.add_expectation(file_item["id"], "file_modified", {"hash": "abc"})
    assert (await db.tasks.expectations(task_id))[0]["signal_type"] == "file_modified"

    await db.tasks.record_manual_verification(task_id, ids["a1"], "incomplete")
    assert (await db.tasks.get(task_id))["status"] == "in_progress"      # incomplete does not close
    await db.tasks.record_manual_verification(task_id, ids["a1"], "complete")
    done = await db.tasks.get(task_id)
    assert done["status"] == "completed" and done["completed_at"] is not None
    assert done["manual_verification"]["outcome"] == "complete"
    assert await db.tasks.list_for(ids["w1"]) == []
    assert len(await db.tasks.list_for(ids["w1"], include_completed=True)) == 1


# --- flows --------------------------------------------------------------------------------------

async def test_flow_create_graph_edges_and_history(db: Database):
    ids = await seed(db)
    flow_id = await db.flows.create(
        {"created_by_account_id": ids["a1"], "source_pc_id": ids["a1_pc"], "source_path": "C:/out",
         "consent_status": "not_required"},
        destinations=[{"destination_pc_id": ids["w1_pc"], "destination_path": "C:/in", "owner_account_id": ids["w1"]},
                      {"destination_pc_id": ids["w2_pc"], "destination_path": "C:/in", "owner_account_id": ids["w2"],
                       "parent_index": 1}],
        stages=[{"stage_type": "branch"}, {"stage_type": "transformation", "parent_index": 0, "config": {"to": "pdf"}}])
    flow = await db.flows.get(flow_id)
    assert flow["stages"][1]["parent_stage_id"] == flow["stages"][0]["id"]
    assert flow["stages"][1]["config"] == {"to": "pdf"}
    assert flow["destinations"][1]["parent_stage_id"] == flow["stages"][1]["id"]
    edges = await db.flows.graph_edges()
    assert (f"{ids['a1_pc']}:C:/out", f"{ids['w1_pc']}:C:/in") in edges
    assert [f["id"] for f in await db.flows.sources_for_pc(ids["a1_pc"])] == [flow_id]

    dest = flow["destinations"][0]["id"]
    await db.flows.log_sync(dest, "h1", "flow_sync", None)
    await db.flows.log_sync(dest, "h2", "external", ids["w1"], conflict_resolved=True)
    assert (await db.flows.last_sync(dest))["written_by"] == "external"
    assert len(await db.flows.history(flow_id)) == 2
    await db.flows.set_status(flow_id, "paused", "transformation:convert_failed")
    assert (await db.flows.get(flow_id))["pause_reason"] == "transformation:convert_failed"
    await db.flows.set_status(flow_id, "inactive")
    assert await db.flows.sources_for_pc(ids["a1_pc"]) == []            # still a row, just inactive
    assert await db.pool.fetchval("SELECT count(*) FROM flows") == 1


# --- reports ------------------------------------------------------------------------------------

async def test_report_visibility_is_additive_and_views_are_separate(db: Database):
    ids = await seed(db)
    with pytest.raises(ValueError):
        await db.reports.write("resource_violation", "not_a_table", 1)
    r1 = await db.reports.write("resource_violation", "resource_violations", 1)
    r2 = await db.reports.write("flow_failure", "flow_sync_log", 1)
    # Nothing routed: Super User sees everything, Finance's Admin sees nothing.
    assert {r["id"] for r in await db.reports.all()} == {r1, r2}
    assert await db.reports.routed_to_department(ids["fin"]) == []
    # Route resource_violation to Finance: additive -- Super User still sees both.
    await db.reports.set_routing("resource_violation", [ids["fin"]], ids["su"])
    assert [r["id"] for r in await db.reports.routed_to_department(ids["fin"])] == [r1]
    assert await db.reports.routed_to_department(ids["hr"]) == []
    assert {r["id"] for r in await db.reports.all()} == {r1, r2}
    # Admin marks addressed -> a View row; the report row is untouched.
    await db.reports.mark_addressed(r1, ids["a1"])
    assert (await db.reports.routed_to_department(ids["fin"]))[0]["addressed_at"] is not None
    views = await db.reports.addressed_views()
    assert views[0]["report_id"] == r1 and views[0]["addressed_by_department_id"] == ids["fin"]
    assert await db.pool.fetchval("SELECT count(*) FROM reports") == 2
    # Replacing routing clears the pane.
    await db.reports.set_routing("resource_violation", [], ids["su"])
    assert await db.reports.routed_to_department(ids["fin"]) == []


# --- assistance ---------------------------------------------------------------------------------

async def test_ping_channel_turns_and_listener_scoping(db: Database):
    ids = await seed(db)
    p1 = await db.assistance.ping(ids["w1"], ids["a1"])
    await db.assistance.ping(ids["w1"], ids["a1"])                    # repeatable, no lock
    assert await db.assistance.unaddressed_ping_count(ids["a1"]) == 2
    chan = await db.assistance.open_channel(p1, ids["w1"], ids["a1"])
    await db.assistance.address_pings(ids["a1"], ids["w1"])
    assert await db.assistance.unaddressed_ping_count(ids["a1"]) == 0
    assert (await db.assistance.channel(chan))["turn"] == "sender"
    await db.assistance.post_message(chan, ids["w1"], "help?", next_turn="superior")
    assert (await db.assistance.channel(chan))["turn"] == "superior"

    # W1 adds A2 as listener; A1 independently adds A2 too -> dedup, A1's add is a no-op.
    assert await db.assistance.add_listener(chan, ids["a2"], ids["w1"]) is True
    assert await db.assistance.add_listener(chan, ids["a2"], ids["a1"]) is False
    assert [l["listener_account_id"] for l in await db.assistance.listeners_added_by(chan, ids["w1"])] == [ids["a2"]]
    assert await db.assistance.listeners_added_by(chan, ids["a1"]) == []   # A1 sees none of W1's
    assert await db.assistance.listener_account_ids(chan) == [ids["a2"]]
    assert [c["id"] for c in await db.assistance.channels_for(ids["a2"])] == [chan]
    await db.assistance.close_channel(chan)
    assert (await db.assistance.channel(chan))["closed_at"] is not None
    assert await db.assistance.open_channel_between(ids["w1"], ids["a1"]) is None


# --- control ------------------------------------------------------------------------------------

async def test_control_event_actions_and_executions(db: Database):
    ids = await seed(db)
    ev = await db.control.create_event(ids["a1"], "native_pushed", {"type": "usb.inserted"})
    shot = await db.control.create_action(ids["a1"], "control", 30, builtin_type="screenshot")
    custom = await db.control.create_action(ids["a1"], "custom", 60, custom_script="print(1)",
                                            custom_script_language="python")
    await db.control.attach_action(ev, custom, 2)
    await db.control.attach_action(ev, shot, 1)
    assert [a["id"] for a in await db.control.actions_for_event(ev)] == [shot, custom]
    assert [e["id"] for e in await db.control.event_definitions(event_type="usb.inserted")] == [ev]
    assert await db.control.event_definitions(event_type="usb.removed") == []
    await db.control.update_event(ev, enabled=False)
    assert await db.control.event_definitions(event_type="usb.inserted") == []

    ex = await db.control.start_execution(shot, ev, ids["w1_pc"])
    assert [e["id"] for e in await db.control.live_executions()] == [ex]
    await db.control.finish_execution(ex, "terminated", terminated_reason="timeout", output_log_path="/tmp/x.log")
    done = await db.control.execution(ex)
    assert done["status"] == "terminated" and done["terminated_reason"] == "timeout" and done["ended_at"]
    await db.control.finish_execution(ex, "success")                      # no-op: already finished
    assert (await db.control.execution(ex))["status"] == "terminated"

    await db.control.archive_action(custom)
    assert [a["id"] for a in await db.control.actions(created_by=ids["a1"])] == [shot]
    assert await db.pool.fetchval("SELECT count(*) FROM actions") == 2  # archived, not deleted


# --- audit --------------------------------------------------------------------------------------

async def test_audit_write_validation_and_purge(db: Database):
    ids = await seed(db)
    with pytest.raises(ValueError):
        await db.audit.write({"action": "x", "target_type": "nope"})
    await db.audit.write({"actor_account_id": ids["a1"], "action": "session.traversed", "target_type": "session",
                          "target_id": "1", "detail": {"pc": 1}})
    await db.audit.write({"action": "old", "at": _now() - timedelta(days=91)})
    assert [e["action_type"] for e in await db.audit.recent(action_prefix="session.")] == ["session.traversed"]
    assert await db.audit.purge_older_than(90) == 1
    assert await db.pool.fetchval("SELECT count(*) FROM audit_log") == 1
    dev = await db.audit.write_deviation({"kind": "account_bound_to_one_pc", "surfaced_to_account_id": ids["a1"],
                                          "detail": {"expected": "FIN-01", "found": "OTHER"}})
    assert (await db.audit.deviations())[0]["id"] == dev


# --- updates / alerts ---------------------------------------------------------------------------

async def test_update_gate_and_rollout_health(db: Database):
    ids = await seed(db)
    v1 = await db.updates.approve_version("1.0.0", ids["su"])
    assert (await db.updates.current_version())["id"] == v1
    assert len(await db.updates.pcs_behind(v1)) == 5                     # nobody has reported yet
    for pc in ("su_pc", "a1_pc", "w1_pc", "w2_pc", "a2_pc"):
        await db.updates.record_attempt(ids[pc], v1, True)
    assert await db.updates.pcs_behind(v1) == []                          # gate opens for N+1
    v2 = await db.updates.approve_version("1.1.0", ids["su"])
    await db.updates.set_target([ids["w1_pc"]], v2)
    st = await db.updates.record_attempt(ids["w1_pc"], v2, False)
    assert st["attempt_failure_count"] == 1 and st["current_version_id"] == v1 and st["target_version_id"] == v2
    st = await db.updates.record_attempt(ids["w1_pc"], v2, False)
    assert st["attempt_failure_count"] == 2
    await db.updates.mark_escalated(ids["w1_pc"])
    health = {h["department_name"]: h for h in await db.updates.rollout_health_by_department()}
    assert health["Finance"]["pending"] == 1 and health["Finance"]["escalated"] == 1 and health["HR"]["pending"] == 0
    st = await db.updates.record_attempt(ids["w1_pc"], v2, True)
    assert st["attempt_failure_count"] == 0 and st["escalated_at"] is None and st["current_version_id"] == v2


async def test_alerts_audience_filtering(db: Database):
    ids = await seed(db)
    await db.alerts.create(ids["su"], "announcement", "all_users", "hello all")
    await db.alerts.create(ids["su"], "warning", "admin_only", "admins only")
    await db.alerts.create(ids["a1"], "routine", "department", "finance only", department_id=ids["fin"])
    await db.alerts.create(ids["a1"], "emergency", "specific_users", "just w2", recipient_account_ids=[ids["w2"]])
    await db.alerts.create(ids["su"], "routine", "all_users", "later", deliver_at=_now() + timedelta(hours=1))
    bodies = lambda rows: sorted(r["body"] for r in rows)
    assert bodies(await db.alerts.for_account(ids["w1"], "worker", ids["fin"])) == ["finance only", "hello all"]
    assert bodies(await db.alerts.for_account(ids["w2"], "worker", ids["fin"])) == ["finance only", "hello all", "just w2"]
    assert bodies(await db.alerts.for_account(ids["a2"], "admin", ids["hr"])) == ["admins only", "hello all"]
    assert bodies(await db.alerts.for_account(ids["su"], "super_user", None)) == ["admins only", "hello all"]
    assert [a["body"] for a in await db.alerts.pending()] == ["later"]
