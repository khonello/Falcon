"""Hierarchy end-to-end over the socket against a DB-backed Engine (skipped without
FALCON_TEST_DATABASE_URL). Exercises the rules from hierarchy-system-design.md:
traversal depth, session blocking (vertical vs horizontal, un-evictable Super User),
time limit + extension, display-name non-propagation, report routing, assisted access.
"""

from __future__ import annotations

from datetime import timedelta

from engine.database import _now
from engine.hierarchy import traversal
from tests.conftest import requires_db

pytestmark = requires_db


# --- auth binds identity ------------------------------------------------------------------------

async def test_handshake_resolves_identity_and_claims_native_session(engine, org, connect):
    w1 = await connect("cid-w1", hostname="FIN-01")
    state = await w1.ok("hierarchy.session_state")
    assert state["pc_session"]["occupied_via"] == "native"
    assert state["pc_session"]["occupant_account_id"] == org["w1"]
    assert state["blocked"] is False
    # Unprovisioned client_id is refused; hostname mismatch is a logged deviation, not a refusal.
    import asyncio

    r, w = await asyncio.open_connection("127.0.0.1", engine.port)
    from tests.conftest import Client

    c = Client(r, w)
    await c.recv()
    assert await c.err("auth.respond", {"client_id": "nope"}) == "unauthenticated"
    await c.close()
    await connect("cid-w2", hostname="SOMEWHERE-ELSE")
    devs = await engine.db.audit.deviations()
    assert devs and devs[0]["expectation"] == "account_bound_to_one_pc"


async def test_worker_cannot_traverse_or_see_tree(engine, org, connect):
    w1 = await connect("cid-w1")
    assert await w1.err("hierarchy.traverse", {"pc_id": org["w2_pc"]}) == "forbidden"
    assert await w1.err("hierarchy.tree") == "forbidden"


# --- traversal & session blocking ---------------------------------------------------------------

async def test_admin_traverses_into_idle_worker_pc(engine, org, connect):
    a1 = await connect("cid-a1")
    res = await a1.ok("hierarchy.traverse", {"pc_id": org["w1_pc"]})
    s = res["session"]
    assert s["occupied_via"] == "traversal" and s["restricted_view"] is True and s["super_user_banner"] is False
    assert s["deadline_at"] is not None and res["already_occupying"] is False
    # Second traverse is idempotent for the same occupant.
    again = await a1.ok("hierarchy.traverse", {"pc_id": org["w1_pc"]})
    assert again["already_occupying"] is True and again["session"]["session_id"] == s["session_id"]
    # Admin cannot enter an admin workstation or another department's PC.
    assert await a1.err("hierarchy.traverse", {"pc_id": org["a2_pc"]}) == "forbidden"
    await engine.db.accounts.create_pc("HR-01", org["hr"], "client_pc", "cid-hrw")
    hr_pc = (await engine.db.accounts.pcs_in_department(org["hr"]))[-1]["id"]
    assert await a1.err("hierarchy.traverse", {"pc_id": hr_pc}) == "forbidden"


async def test_vertical_block_or_end_first_and_worker_sees_overlay(engine, org, connect):
    w1 = await connect("cid-w1")
    a1 = await connect("cid-a1")
    # Worker occupies natively -> Admin is told it's occupied unless forcing.
    assert await a1.err("hierarchy.traverse", {"pc_id": org["w1_pc"]}) == "conflict"
    res = await a1.ok("hierarchy.traverse", {"pc_id": org["w1_pc"], "force": True})
    pushes = w1.push_types(await w1.drain_pushes())
    assert "session.ended" in pushes and "session.blocked" in pushes
    state = await w1.ok("hierarchy.session_state")
    assert state["blocked"] is True and state["pc_session"]["occupant_account_id"] == org["a1"]
    # Worker cannot end the Admin's session; cannot re-claim while blocked.
    assert await w1.err("hierarchy.end_session", {"session_id": res["session"]["session_id"]}) == "forbidden"
    assert (await w1.ok("hierarchy.claim_native"))["blocked"] is True
    # Admin leaves -> worker gets session.released and re-claims.
    await a1.ok("hierarchy.end_session", {"session_id": res["session"]["session_id"]})
    assert "session.released" in w1.push_types(await w1.drain_pushes())
    assert (await w1.ok("hierarchy.claim_native"))["blocked"] is False


async def test_horizontal_is_hard_refused_and_super_user_is_unevictable(engine, org, connect):
    a1 = await connect("cid-a1")
    su = await connect("cid-su")
    # Super User traverses into W1 -> un-evictable, banner on.
    res = await su.ok("hierarchy.traverse", {"pc_id": org["w1_pc"]})
    assert res["session"]["un_evictable"] is True and res["session"]["super_user_banner"] is True
    assert await a1.err("hierarchy.traverse", {"pc_id": org["w1_pc"], "force": True}) == "conflict"
    assert await a1.err("hierarchy.end_session", {"session_id": res["session"]["session_id"]}) == "forbidden"
    # Super User can block-or-end an Admin's traversal (vertical).
    await su.ok("hierarchy.end_session", {"session_id": res["session"]["session_id"]})
    a1_res = await a1.ok("hierarchy.traverse", {"pc_id": org["w2_pc"]})
    assert await su.err("hierarchy.traverse", {"pc_id": org["w2_pc"]}) == "conflict"      # needs force
    su_res = await su.ok("hierarchy.traverse", {"pc_id": org["w2_pc"], "force": True})
    assert "session.ended" in a1.push_types(await a1.drain_pushes())
    assert su_res["session"]["session_id"] != a1_res["session"]["session_id"]
    # Super User into an Admin workstation: allowed (depth), the Admin's native session ends.
    a2 = await connect("cid-a2")
    assert await su.err("hierarchy.traverse", {"pc_id": org["a2_pc"]}) == "conflict"
    await su.ok("hierarchy.traverse", {"pc_id": org["a2_pc"], "force": True})
    assert "session.blocked" in a2.push_types(await a2.drain_pushes())


async def test_time_limit_extension_and_expiry(engine, org, connect):
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    await w1.drain_pushes()
    res = await a1.ok("hierarchy.traverse", {"pc_id": org["w1_pc"], "force": True})
    sid = res["session"]["session_id"]
    ext = await a1.ok("hierarchy.extend_session", {"session_id": sid})
    assert ext["extended_count"] == 1 and ext["deadline_at"] > res["session"]["deadline_at"]
    assert await w1.err("hierarchy.extend_session", {"session_id": sid}) == "forbidden"
    # Force the deadline into the past and run the scheduler hook: block releases.
    await engine.db.pool.execute("UPDATE sessions SET deadline_at = $2 WHERE id = $1", sid, _now() - timedelta(seconds=1))
    await traversal.expire_due_sessions(engine)
    assert (await engine.db.sessions.by_id(sid))["ended_reason"] == "deadline_expired"
    assert "session.released" in w1.push_types(await w1.drain_pushes())
    assert "session.ended" in a1.push_types(await a1.drain_pushes())


async def test_network_drop_mid_traversal_expires_by_the_same_deadline(engine, org, connect):
    a1 = await connect("cid-a1")
    res = await a1.ok("hierarchy.traverse", {"pc_id": org["w1_pc"]})
    sid = res["session"]["session_id"]
    await a1.close()
    import asyncio

    await asyncio.sleep(0.1)
    # Disconnect did NOT end the traversal session -- the deadline governs.
    assert (await engine.db.sessions.by_id(sid))["ended_at"] is None
    await engine.db.pool.execute("UPDATE sessions SET deadline_at = $2 WHERE id = $1", sid, _now() - timedelta(seconds=1))
    await traversal.expire_due_sessions(engine)
    assert (await engine.db.sessions.by_id(sid))["ended_reason"] == "network_drop_deadline_expired"


# --- tree & display names -----------------------------------------------------------------------

async def test_tree_scope_and_display_names_do_not_propagate(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    await su.ok("hierarchy.set_display_name", {"account_id": org["a1"], "label": "Finance lead"})
    await a1.ok("hierarchy.set_self_name", {"label": "Sam"})
    assert await a1.err("hierarchy.set_display_name", {"account_id": org["su"], "label": "boss"}) == "forbidden"
    assert await a1.err("hierarchy.set_display_name", {"account_id": org["a2"], "label": "peer"}) == "forbidden"
    await a1.ok("hierarchy.set_display_name", {"account_id": org["w1"], "label": "Desk 1"})

    su_tree = await su.ok("hierarchy.tree")
    assert [d["name"] for d in su_tree["departments"]] == ["Finance", "HR"]
    fin = su_tree["departments"][0]
    assert fin["admins"][0]["name"] == "Finance lead"
    assert fin["workers"][0]["session"]["occupied_via"] == "native"
    a1_tree = await a1.ok("hierarchy.tree")
    assert [d["name"] for d in a1_tree["departments"]] == ["Finance"]
    assert a1_tree["departments"][0]["workers"][0]["name"] == "Desk 1"
    # The worker sees the Admin's self name, never the Super User's label.
    names = (await w1.ok("hierarchy.resolve_names", {"account_ids": [org["a1"], org["w2"]]}))["names"]
    assert names[str(org["a1"])] == "Sam" and names[str(org["w2"])] == f"FIN-02-Finance-{org['w2']}"


# --- accounts -----------------------------------------------------------------------------------

async def test_provisioning_and_offboarding(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    new_dept = await su.ok("hierarchy.department_create", {"name": "Ops"})
    assert await su.err("hierarchy.department_create", {"name": "Ops"}) == "conflict"
    assert await a1.err("hierarchy.department_create", {"name": "Nope"}) == "forbidden"
    created = await a1.ok("hierarchy.account_create", {"role": "worker", "department_id": org["fin"], "hostname": "FIN-03"})
    assert created["client_id"]
    assert await a1.err("hierarchy.account_create", {"role": "admin", "department_id": org["fin"], "hostname": "X"}) == "forbidden"
    assert await a1.err("hierarchy.account_create", {"role": "worker", "department_id": new_dept["department_id"], "hostname": "X"}) == "forbidden"
    # The new worker can connect with the issued client_id.
    w3 = await connect(created["client_id"], hostname="FIN-03")
    assert (await w3.ok("hierarchy.session_state"))["pc_session"]["occupied_via"] == "native"
    # Offboard ends the session and deactivates; the row stays.
    await a1.ok("hierarchy.account_offboard", {"account_id": created["account_id"]})
    assert "session.ended" in w3.push_types(await w3.drain_pushes())
    assert (await engine.db.accounts.by_id(created["account_id"]))["status"] == "offboarded"
    assert await engine.db.accounts.by_client_id(created["client_id"]) is None


# --- reports & routing --------------------------------------------------------------------------

async def test_report_routing_is_additive_and_views_are_super_user_only(engine, org, connect):
    from engine.hierarchy import reports

    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    a2 = await connect("cid-a2")
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


# --- alerts -------------------------------------------------------------------------------------

async def test_alerts_are_role_filtered_and_pushed(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    a2 = await connect("cid-a2")
    assert await a1.err("alerts.create", {"type": "warning", "audience": "all_users", "body": "x"}) == "forbidden"
    assert await a1.err("alerts.create", {"type": "warning", "audience": "department", "department_id": org["hr"], "body": "x"}) == "forbidden"
    await a1.ok("alerts.create", {"type": "routine", "audience": "department", "department_id": org["fin"], "body": "fin only"})
    await su.ok("alerts.create", {"type": "emergency", "audience": "all_users", "body": "everyone"})
    for c, expected in ((w1, ["alert.delivered", "alert.delivered"]), (a2, ["alert.delivered"])):
        assert c.push_types(await c.drain_pushes()) == expected
    assert sorted(a["body"] for a in (await w1.ok("alerts.list"))["alerts"]) == ["everyone", "fin only"]
    assert [a["body"] for a in (await a2.ok("alerts.list"))["alerts"]] == ["everyone"]


# --- assisted access ----------------------------------------------------------------------------

async def test_assisted_access_consent_flow(engine, org, connect):
    a1 = await connect("cid-a1")
    a2 = await connect("cid-a2")
    su = await connect("cid-su")
    # Nobody available -> no match, never queued.
    res = await a1.ok("assisted_access.request", {"department_id": org["hr"]})
    assert res["matched"] is False
    await a2.ok("assisted_access.set_available", {"available": True})
    helpers = (await a1.ok("assisted_access.available_helpers"))["helpers"]
    assert [h["id"] for h in helpers] == [org["a2"]]
    res = await a1.ok("assisted_access.request", {"department_id": org["hr"], "narrowing": {"monitoring_actions": False,
                                                                                            "resource_files": True}})
    assert res["matched"] is True and res["helper_account_id"] == org["a2"]
    offer = next(p for p in await a2.drain_pushes() if p.type == "assisted_access.offer")
    # Narrowing can only remove: resource_files stays False despite the requester asking for True.
    assert offer.payload["scope"]["monitoring_actions"] is False and offer.payload["scope"]["resource_files"] is False
    assert offer.payload["scope"]["control_actions"] is True
    assert await a1.err("assisted_access.accept", {"request_id": res["request_id"]}) == "not_found"  # not the helper

    acc = await a2.ok("assisted_access.accept", {"request_id": res["request_id"]})
    assert "assisted_access.started" in a1.push_types(await a1.drain_pushes())
    session = await engine.db.sessions.by_id(acc["session_id"])
    assert session["occupied_via"] == "assisted_access" and session["pc_id"] == org["a1_pc"]
    assert session["un_evictable"] is False
    # Super User always sees the report; helper is no longer available while occupying.
    assert su.push_types(await su.drain_pushes()) == ["report.new"]
    assert (await su.ok("reports.list"))["reports"][0]["category"] == "cross_department_assistance"
    assert (await a1.ok("assisted_access.available_helpers"))["helpers"] == []
    # Either party closes it; the requester re-claims their workstation.
    await a1.ok("assisted_access.close", {"request_id": res["request_id"]})
    assert "assisted_access.closed" in a2.push_types(await a2.drain_pushes())
    assert (await engine.db.sessions.by_id(acc["session_id"]))["ended_reason"] == "voluntary"
    assert (await a1.ok("hierarchy.claim_native"))["blocked"] is False
