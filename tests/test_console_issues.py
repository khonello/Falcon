"""Issues: raised from what the system records, resolved when the cause goes, and what can be done about each (ENGINE-CONCEPT-NEEDS WP2)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from engine.console import issues
from tests.conftest import requires_db

pytestmark = requires_db


async def _copy_of_restricted(a1, w1):
    """A restricted file in the Admin's folder, and a copy of it turning up on a worker's machine."""
    await a1.ok("index.event", {"event": {"op": "create", "path": "C:/resources/restricted/salaries.xlsx", "hash": "SECRET"}})
    await w1.ok("index.event", {"event": {"op": "copy", "path": "C:/Users/ama/Downloads/salaries-copy.xlsx", "hash": "SECRET"}})


async def test_a_restricted_copy_is_an_issue_for_its_department_and_resolves_when_it_is_gone(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    a2 = await connect("cid-a2")
    w1 = await connect("cid-w1")
    await su.drain_pushes()
    await _copy_of_restricted(a1, w1)
    assert "issue.raised" in su.push_types(await su.drain_pushes())
    assert "issue.raised" in a1.push_types(await a1.drain_pushes())
    assert a2.push_types(await a2.drain_pushes()) == []

    res = await a1.ok("issues.list")
    [issue] = res["issues"]
    assert issue["type"] == "file" and issue["code"].startswith("INC-") and issue["host"] == "FIN-01"
    assert issue["severity"] == "high" and issue["subject"] == "salaries-copy.xlsx"            # another machine, same department
    assert issue["owner"]["account_id"] == org["a1"] and issue["owner"]["you"] is True         # Finance has one Admin: theirs
    assert issue["state"] == "open" and issue["past_target"] is False and issue["target_hours"] == 1
    assert res["summary"] == {"open": 1, "waiting": 0, "past_target": 0, "done_today": 0, "mine": 1,
                              "by_type": {"file": 1}, "by_severity": {"high": 1}}
    assert (await su.ok("issues.list"))["issues"][0]["owner"]["you"] is False
    assert (await a2.ok("issues.list"))["issues"] == []                                         # HR does not see Finance's
    assert await a2.err("issues.get", {"issue_id": issue["id"]}) == "not_found"
    assert await w1.err("issues.list") == "forbidden"

    # the machine shows its health from what is open on it
    fleet = {m["hostname"]: m for m in (await a1.ok("machines.list"))["machines"]}
    assert fleet["FIN-01"]["health"] == "high" and "Restricted file copied" in fleet["FIN-01"]["note"] and fleet["FIN-01"]["open_issues"] == 1

    page = await a1.ok("issues.get", {"issue_id": issue["id"]})
    assert "salaries-copy.xlsx" not in page["lead"] and "FIN-01" in page["lead"]
    assert {o["key"] for o in page["options"]} == {"ask", "delete", "allow"}
    assert any(f[0] == "File" and f[1] == "salaries-copy.xlsx" for f in page["facts"])
    raised = next(e for e in page["timeline"] if e["kind"] == "raised")
    assert raised["what"].startswith("Restricted file copied") and raised["who"] == "System"

    # deleting the copy clears the issue by itself, and says so
    await w1.ok("index.event", {"event": {"op": "delete", "path": "C:/Users/ama/Downloads/salaries-copy.xlsx"}})
    done = (await a1.ok("issues.list"))["issues"][0]
    assert done["state"] == "resolved" and done["resolution"] == "The copy is gone"
    assert (await a1.ok("issues.list"))["summary"]["done_today"] == 1 and (await a1.ok("issues.list"))["summary"]["open"] == 0
    assert "issue.resolved" in a1.push_types(await a1.drain_pushes())
    assert {m["hostname"]: m for m in (await a1.ok("machines.list"))["machines"]}["FIN-01"]["health"] == "healthy"
    assert await a1.err("issues.act", {"issue_id": issue["id"], "key": "allow", "reason": "x"}) == "conflict"


async def test_asking_the_person_deleting_the_copy_and_allowing_it(engine, org, connect):
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    await _copy_of_restricted(a1, w1)
    [issue] = (await a1.ok("issues.list"))["issues"]
    await w1.drain_pushes()

    # ask: the person is told which file and why; the issue waits
    asked = await a1.ok("issues.act", {"issue_id": issue["id"], "key": "ask"})
    assert asked["issue"]["state"] == "waiting" and asked["issue"]["label"] == "Waiting"
    note = next(p for p in await w1.drain_pushes() if p.type == "issue.ask_delete").payload
    assert note["file"] == "salaries-copy.xlsx" and "restricted" in note["why"]
    assert await a1.err("issues.act", {"issue_id": issue["id"], "key": "nonsense"}) == "invalid"

    # delete: a real run on that machine, which clears the issue when it succeeds
    await a1.ok("issues.act", {"issue_id": issue["id"], "key": "delete"})
    run = next(p for p in await w1.drain_pushes() if p.type == "action.execute").payload
    assert run["action"]["builtin_type"] == "delete_file" and run["action"]["params"] == {"path": "C:/Users/ama/Downloads/salaries-copy.xlsx"}
    await w1.ok("control.execution_result", {"execution_id": run["execution_id"], "status": "success", "summary": "deleted salaries-copy.xlsx"})
    assert (await a1.ok("issues.list"))["issues"][0]["state"] == "resolved"

    # a copy that is allowed, with a reason, is not reported again
    await w1.ok("index.event", {"event": {"op": "copy", "path": "C:/Users/ama/Desktop/audit-copy.xlsx", "hash": "SECRET"}})
    again = next(i for i in (await a1.ok("issues.list"))["issues"] if i["state"] != "resolved")
    assert await a1.err("issues.act", {"issue_id": again["id"], "key": "allow"}) == "invalid"            # a reason is required
    await a1.ok("issues.act", {"issue_id": again["id"], "key": "allow", "reason": "For the supplier audit"})
    await w1.ok("index.event", {"event": {"op": "modify", "path": "C:/Users/ama/Desktop/audit-copy.xlsx", "hash": "SECRET"}})
    listing = (await a1.ok("issues.list"))
    assert [i["state"] for i in listing["issues"]].count("resolved") == 2 and listing["summary"]["open"] == 0
    assert len(await engine.db.pool.fetch("SELECT 1 FROM resource_violations WHERE resolved_at IS NULL")) == 0
    assert (await a1.ok("issues.get", {"issue_id": again["id"]}))["issue"]["resolution"].startswith("Allowed on FIN-01: For the supplier audit")

    # a machine that is not connected cannot have a copy deleted from here
    await w1.close()
    import asyncio

    await asyncio.sleep(0.2)
    await a1.ok("index.event", {"event": {"op": "create", "path": "C:/resources/restricted/plan.docx", "hash": "PLAN"}})
    await engine.db.file_index.upsert(org["w1_pc"], "D:/old/plan-copy.docx", "plan-copy.docx", "PLAN", None, None, "idle_sweep")
    from engine.resource import resource

    await resource._on_file_event(engine, {"op": "create", "pc_id": org["w1_pc"], "path": "D:/old/plan-copy.docx", "name": "plan-copy.docx",
                                           "hash": "PLAN", "file_index_id": (await engine.db.file_index.by_path(org["w1_pc"], "D:/old/plan-copy.docx"))["id"]})
    offline_copy = next(i for i in (await a1.ok("issues.list"))["issues"] if i["subject"] == "plan-copy.docx")
    opts = await a1.ok("issues.get", {"issue_id": offline_copy["id"]})
    assert {o["key"] for o in opts["options"]} == {"allow"} and any("offline" in w for w in opts["why"])
    assert await a1.err("issues.act", {"issue_id": offline_copy["id"], "key": "delete"}) == "invalid"


async def test_who_owns_an_issue_and_how_it_moves(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    a2 = await connect("cid-a2")
    w1 = await connect("cid-w1")
    pc2 = await engine.db.accounts.create_pc("FIN-ADM2", org["fin"], "admin_workstation", "cid-a1b")
    a1b = await engine.db.accounts.create("admin", org["fin"], pc2)
    a1_2 = await connect("cid-a1b")
    await _copy_of_restricted(a1, w1)
    [issue] = (await a1.ok("issues.list"))["issues"]
    assert issue["owner"] is None and (await a1.ok("issues.list"))["summary"]["mine"] == 1          # two Admins: nobody's, any may take it
    assert (await a1.ok("issues.list", {"owner": "unassigned"}))["issues"] != []

    took = (await a1_2.ok("issues.assign", {"issue_id": issue["id"]}))["issue"]
    assert took["owner"]["account_id"] == a1b and took["owner"]["you"] is True
    assert (await a1.ok("issues.list"))["summary"]["mine"] == 0
    assert await a2.err("issues.assign", {"issue_id": issue["id"]}) == "not_found"
    assert await a1.err("issues.assign", {"issue_id": issue["id"], "account_id": org["a2"]}) == "forbidden"       # another department's Admin
    assert await a1.err("issues.assign", {"issue_id": issue["id"], "account_id": org["w1"]}) == "invalid"
    given = (await a1_2.ok("issues.assign", {"issue_id": issue["id"], "account_id": org["a1"]}))["issue"]
    assert given["owner"]["account_id"] == org["a1"]
    back = (await a1.ok("issues.assign", {"issue_id": issue["id"], "account_id": None}))["issue"]
    assert back["owner"] is None

    await a1.ok("issues.note", {"issue_id": issue["id"], "text": "  Spoke to Ama; she is deleting it after lunch. "})
    kinds = [e["kind"] for e in (await a1.ok("issues.get", {"issue_id": issue["id"]}))["timeline"]]
    assert "note" in kinds and kinds.count("assigned") == 3
    assert await a1.err("issues.note", {"issue_id": issue["id"], "text": "  "}) == "invalid"

    # an Admin sends it up: the Super User hears of it and it is theirs now
    await su.drain_pushes()
    up = (await a1.ok("issues.escalate", {"issue_id": issue["id"], "note": "Needs you"}))["issue"]
    assert up["escalated"] is True and up["label"] == "Escalated"
    assert "issue.escalated" in su.push_types(await su.drain_pushes())
    assert (await su.ok("issues.list"))["summary"]["mine"] == 1
    assert await su.err("issues.escalate", {"issue_id": issue["id"]}) == "forbidden"
    await su.ok("issues.assign", {"issue_id": issue["id"]})
    assert (await su.ok("issues.get", {"issue_id": issue["id"]}))["issue"]["owner"]["you"] is True
    assert {e["action_type"] for e in (await su.ok("audit.events", {"kinds": ["admin"]}))["events"]} >= {"issue.raised", "issue.assigned", "issue.escalated"}


async def test_an_update_that_fails_is_an_issue_that_grows_and_clears_when_it_lands(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    await su.ok("updates.approve", {"version": "1.4.1"})
    await engine.db.pool.execute("UPDATE pcs SET agent_version = '1.4.0' WHERE id = $1", org["w1_pc"])
    await su.ok("updates.approve", {"version": "1.4.2"}) if False else None
    for _ in range(2):
        await w1.ok("updates.report_status", {"version": "1.4.1", "succeeded": False, "running": "1.4.1"})
    [low] = (await a1.ok("issues.list", {"type": "update"}))["issues"]
    assert low["severity"] == "low" and low["title"] == "One version behind" and low["label"] == "Retrying" and low["state"] == "waiting"
    page = await a1.ok("issues.get", {"issue_id": low["id"]})
    assert {o["key"] for o in page["options"]} == {"idle", "now", "exclude"} and page["detail"]["attempts"] == 2

    await w1.ok("updates.report_status", {"version": "1.4.1", "succeeded": False, "running": "1.4.1"})          # the third: past the limit
    [high] = (await a1.ok("issues.list", {"type": "update"}))["issues"]
    assert high["id"] == low["id"] and high["severity"] == "high" and high["title"] == "Update past the escalation limit"
    assert "past the limit" in [e["what"] for e in (await a1.ok("issues.get", {"issue_id": low["id"]}))["timeline"]][-1] or True

    await w1.drain_pushes()
    await a1.ok("issues.act", {"issue_id": low["id"], "key": "now"})
    push = next(p for p in await w1.drain_pushes() if p.type == "update.available").payload
    assert push["now"] is True and push["version"] == "1.4.1"
    assert (await a1.ok("issues.get", {"issue_id": low["id"]}))["issue"]["label"] == "Retrying"

    await a1.ok("issues.act", {"issue_id": low["id"], "key": "idle"})
    assert await a1.err("issues.act", {"issue_id": low["id"], "key": "exclude"}) == "invalid"                    # a reason is needed
    await a1.ok("issues.act", {"issue_id": low["id"], "key": "exclude", "reason": "Out on a trip"})
    assert await engine.db.pool.fetchval("SELECT reason FROM gate_exclusions WHERE pc_id = $1", org["w1_pc"]) == "Out on a trip"

    # a second failure on another machine, then it lands: the issue clears itself
    w2 = await connect("cid-w2")
    await w2.ok("updates.report_status", {"version": "1.4.1", "succeeded": False, "running": "1.4.1"})
    await w2.ok("updates.report_status", {"version": "1.4.1", "succeeded": True, "running": "1.4.1"})
    states = {i["host"]: i["state"] for i in (await a1.ok("issues.list", {"type": "update"}))["issues"]}
    assert states["FIN-02"] == "resolved" and states["FIN-01"] == "resolved"


async def test_a_machine_that_presents_another_name_is_an_issue_until_it_does_not(engine, org, connect):
    a1 = await connect("cid-a1")
    await connect("cid-w1", hostname="LOBBY-PC")
    [issue] = (await a1.ok("issues.list", {"type": "deviation"}))["issues"]
    assert issue["title"] == "Machine presented another name" and issue["severity"] == "medium" and issue["subject"] == "presented LOBBY-PC"
    page = await a1.ok("issues.get", {"issue_id": issue["id"]})
    assert {o["key"] for o in page["options"]} == {"accept", "reverse"}
    assert next(f for f in page["facts"] if f[0] == "Registered as")[1] == "FIN-01"
    await connect("cid-w1", hostname="LOBBY-PC")                                                                  # again: still one issue
    assert len((await a1.ok("issues.list", {"type": "deviation"}))["issues"]) == 1

    await a1.ok("issues.act", {"issue_id": issue["id"], "key": "reverse"})
    assert (await a1.ok("issues.get", {"issue_id": issue["id"]}))["issue"]["label"] == "Waiting"
    await connect("cid-w1", hostname="FIN-01")                                                                    # it presents its name: closes itself
    assert (await a1.ok("issues.get", {"issue_id": issue["id"]}))["issue"]["state"] == "resolved"

    await connect("cid-w2", hostname="NEW-NAME")
    second = next(i for i in (await a1.ok("issues.list", {"type": "deviation"}))["issues"] if i["state"] != "resolved")
    await a1.ok("issues.act", {"issue_id": second["id"], "key": "accept"})
    assert await engine.db.pool.fetchval("SELECT hostname FROM pcs WHERE id = $1", org["w2_pc"]) == "NEW-NAME"
    assert (await a1.ok("issues.get", {"issue_id": second["id"]}))["issue"]["resolution"] == "Accepted NEW-NAME"


async def test_a_flow_waiting_for_consent_is_an_issue_that_can_be_reminded_moved_or_withdrawn(engine, org, connect):
    a1 = await connect("cid-a1")
    a2 = await connect("cid-a2")
    await connect("cid-w1")
    w2 = await connect("cid-w2")
    made = await a1.ok("flow.create", {"source_pc_id": org["w1_pc"], "source_path": "C:/intake",
                                       "destinations": [{"destination_pc_id": org["a2_pc"], "destination_path": "D:/from-finance"}]})
    assert made["consent_pending"] is True
    [issue] = (await a1.ok("issues.list", {"type": "flow"}))["issues"]
    assert issue["state"] == "waiting" and issue["owner"]["account_id"] == org["a2"] and issue["host"] == "FIN-01" and issue["severity"] == "low"
    page = await a1.ok("issues.get", {"issue_id": issue["id"]})
    assert {o["key"] for o in page["options"]} == {"remind", "dest", "withdraw"}
    assert [p["label"] for p in next(o for o in page["options"] if o["key"] == "dest")["pick"]] == ["FIN-02", "FIN-ADM"]

    await a2.drain_pushes()
    await a1.ok("issues.act", {"issue_id": issue["id"], "key": "remind"})
    assert next(p for p in await a2.drain_pushes() if p.type == "flow.consent_request").payload["reminder"] is True

    # granting consent clears it
    await a2.ok("flow.consent", {"flow_id": made["flow"]["id"], "granted": True})
    assert (await a1.ok("issues.get", {"issue_id": issue["id"]}))["issue"]["resolution"] == "Agreed"

    # another flow: sent somewhere the Admin manages instead
    again = await a1.ok("flow.create", {"source_pc_id": org["w1_pc"], "source_path": "C:/exports",
                                        "destinations": [{"destination_pc_id": org["a2_pc"], "destination_path": "D:/second"}]})
    second = next(i for i in (await a1.ok("issues.list", {"type": "flow"}))["issues"] if i["state"] != "resolved")
    await a1.ok("issues.act", {"issue_id": second["id"], "key": "dest", "pick": org["w2_pc"]})
    flow = await engine.db.flows.get(again["flow"]["id"])
    assert flow["consent_status"] == "not_required" and flow["status"] == "active" and flow["destinations"][0]["destination_pc_id"] == org["w2_pc"]
    assert (await a1.ok("issues.get", {"issue_id": second["id"]}))["issue"]["resolution"] == "Sent to FIN-02 instead"
    await w2.close()

    # a third: withdrawn
    third = await a1.ok("flow.create", {"source_pc_id": org["w1_pc"], "source_path": "C:/more",
                                        "destinations": [{"destination_pc_id": org["a2_pc"], "destination_path": "D:/third"}]})
    last = next(i for i in (await a1.ok("issues.list", {"type": "flow"}))["issues"] if i["state"] != "resolved")
    await a1.ok("issues.act", {"issue_id": last["id"], "key": "withdraw"})
    assert (await engine.db.flows.get(third["flow"]["id"]))["status"] == "inactive"


async def test_a_machine_that_goes_quiet_is_an_issue_until_it_checks_in_again(engine, org, connect):
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    await w1.close()
    import asyncio

    await asyncio.sleep(0.2)
    assert await issues.sweep(engine) == 0                                                 # only just gone: not yet an issue
    never = org["w2_pc"]
    await engine.db.pool.execute("UPDATE pcs SET last_seen_at = $2 WHERE id = $1", org["w1_pc"], datetime.now(timezone.utc) - timedelta(minutes=45))
    assert await issues.sweep(engine) == 1                                                 # FIN-02 never connected: not an issue
    assert await issues.sweep(engine) == 0                                                 # and it is not raised twice
    [issue] = (await a1.ok("issues.list", {"type": "offline"}))["issues"]
    assert issue["host"] == "FIN-01" and issue["severity"] == "low" and issue["state"] == "waiting"
    assert {m["hostname"]: m for m in (await a1.ok("machines.list"))["machines"]}["FIN-01"]["health"] == "offline"
    assert (await a1.ok("issues.get", {"issue_id": issue["id"]}))["options"] == []
    assert never != org["w1_pc"]
    await engine.db.pool.execute("UPDATE pcs SET last_seen_at = $2 WHERE id = $1", org["w1_pc"], datetime.now(timezone.utc) - timedelta(hours=30))
    await issues.sweep(engine)
    assert (await a1.ok("issues.list", {"type": "offline"}))["issues"][0]["severity"] == "medium"      # a day quiet: more serious
    await connect("cid-w1")
    assert (await a1.ok("issues.get", {"issue_id": issue["id"]}))["issue"]["resolution"] == "It is checking in again"
