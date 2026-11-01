"""Version 1: the Admins are IT over every department; departments are labels (docs/design/v1-it-admin.md)."""

from __future__ import annotations

import pytest

from tests.conftest import TEST_MASTER_SECRET, requires_db

pytestmark = [requires_db, pytest.mark.organisation]


async def test_an_it_admin_reaches_every_department_and_makes_departments_and_admins(engine, org, connect):
    a1, a2, w1 = await connect("cid-a1"), await connect("cid-a2"), await connect("cid-w1")
    hr_worker = (await a2.ok("hierarchy.account_create", {"role": "worker", "department_id": org["hr"], "hostname": "HR-01"}))
    # Finance's Admin sees and works HR's machines: the fleet, a machine's page, entering it
    hosts = {m["hostname"] for m in (await a1.ok("machines.list"))["machines"]}
    assert {"FIN-01", "HR-ADM", "HR-01"} <= hosts
    assert (await a1.ok("machines.get", {"pc_id": hr_worker["pc_id"]}))["machine"]["hostname"] == "HR-01"
    assert (await a1.ok("hierarchy.traverse", {"pc_id": hr_worker["pc_id"], "force": True}))["session"]
    # ... and gives an HR Worker a task, which an HR-kept Admin could not
    made = await a1.ok("task.create", {"assignee_account_id": hr_worker["account_id"], "description": "Restart the printer", "items": [], "confirm_none": True,
                                       "verification_mode": "none"})
    assert made["task"]["id"]
    # departments are labels any Admin makes; any Admin adds another Admin, and may take one away, never themself
    dept = await a1.ok("hierarchy.department_create", {"name": "Sales"})
    new_admin = await a1.ok("hierarchy.account_create", {"role": "admin", "department_id": dept["department_id"], "hostname": "SALES-IT"})
    assert new_admin["role"] == "admin" and new_admin["client_key"]
    assert await a1.err("hierarchy.account_create", {"role": "super_user", "hostname": "X"}) == "forbidden"
    assert await a1.err("hierarchy.account_offboard", {"account_id": org["a1"]}) == "forbidden"
    assert (await a1.ok("hierarchy.account_offboard", {"account_id": new_admin["account_id"]}))["status"] == "offboarded"
    assert await w1.err("hierarchy.department_create", {"name": "Nope"}) == "forbidden"
    # the department tree is the whole organisation for every Admin
    tree = await a2.ok("hierarchy.tree")
    assert {d["name"] for d in tree["departments"]} >= {"Finance", "HR", "Sales"}


async def test_two_admins_on_one_machine_are_refused_and_issues_reach_every_admin(engine, org, connect):
    a1, a2 = await connect("cid-a1"), await connect("cid-a2")
    await connect("cid-w1")
    await a1.ok("hierarchy.traverse", {"pc_id": org["w1_pc"], "force": True})
    assert await a2.err("hierarchy.traverse", {"pc_id": org["w1_pc"], "force": True}) in ("forbidden", "conflict")
    # an issue on a Finance machine is in HR's Admin's list too, unassigned until someone takes it
    from engine.console import issues

    await issues.raise_issue(engine, type_="offline", severity="medium", title="Disk nearly full", pc_id=org["w1_pc"], department_id=org["fin"])
    listed = (await a2.ok("issues.list"))["issues"]
    assert [i["title"] for i in listed] == ["Disk nearly full"] and listed[0]["owner"] is None
    took = await a2.ok("issues.assign", {"issue_id": listed[0]["id"]})
    assert took["issue"]["owner"]["you"] is True
    assert (await a1.ok("issues.list"))["issues"][0]["owner"]["account_id"] == org["a2"]


async def test_setup_makes_the_first_it_admin_not_a_super_user(engine):
    from engine.__main__ import first_account

    made = await first_account(engine.db, TEST_MASTER_SECRET, engine.settings, "IT-01")
    who, account_id, client_id, key = made
    acct = await engine.db.accounts.by_id(account_id)
    assert who == "IT Admin" and acct["role"] == "admin" and acct["department_name"] == "IT" and acct["pc_type"] == "admin_workstation"
    assert client_id and len(key) == 64
    assert await first_account(engine.db, TEST_MASTER_SECRET, engine.settings, "IT-02") == ("an Admin", account_id)


async def test_only_an_admin_to_admin_flow_needs_consent_and_the_destination_admin_picks_the_folder(engine, org, connect):
    a1, a2 = await connect("cid-a1"), await connect("cid-a2")
    await connect("cid-w1")
    # onto a Worker's machine, in another department too: no consent, the maker names the folder
    to_worker = await a1.ok("flow.create", {"source_pc_id": org["a1_pc"], "source_path": "C:/out", "stages": [],
                                            "destinations": [{"destination_pc_id": org["w1_pc"], "destination_path": "C:/in"}]})
    assert to_worker["consent_pending"] is False and to_worker["flow"]["status"] == "active"
    # a Worker's folder cannot be left to "them": Workers never use the console
    assert await a1.err("flow.create", {"source_pc_id": org["a1_pc"], "source_path": "C:/out2", "stages": [],
                                        "destinations": [{"destination_pc_id": org["w1_pc"], "let_them_choose": True}]}) == "invalid"
    # onto another Admin's machine: that Admin agrees and picks the folder
    to_admin = await a1.ok("flow.create", {"source_pc_id": org["a1_pc"], "source_path": "C:/reports", "stages": [],
                                           "destinations": [{"destination_pc_id": org["a2_pc"], "let_them_choose": True}]})
    flow_id = to_admin["flow"]["id"]
    assert to_admin["consent_pending"] is True
    assert "flow.consent_request" in a2.push_types(await a2.drain_pushes())
    assert await a2.err("flow.consent", {"flow_id": flow_id, "granted": True}) == "invalid"                 # the folder is theirs to name
    done = await a2.ok("flow.consent", {"flow_id": flow_id, "granted": True, "destination_path": "D:/From Finance"})
    assert done["granted"] is True
    flow = (await a1.ok("flow.status", {"flow_id": flow_id}))["flow"]
    assert flow["status"] == "active" and flow["destinations"][0]["destination_path"] == "D:/From Finance"


async def test_a_single_file_flow_follows_its_file_at_the_source_and_its_copy_at_the_destination(engine, org, connect):
    a1, w1 = await connect("cid-a1"), await connect("cid-w1")
    made = await a1.ok("flow.create", {"source_pc_id": org["a1_pc"], "source_path": "C:/out/report.docx", "source_kind": "file", "stages": [],
                                       "destinations": [{"destination_pc_id": org["w1_pc"], "destination_path": "C:/in"}]})
    flow = made["flow"]
    dest = flow["destinations"][0]
    await a1.drain_pushes()

    async def change(path: str, h: str) -> dict:
        await a1.ok("index.event", {"event": {"op": "modify", "path": path, "hash": h}})
        read = next(p for p in await a1.drain_pushes() if p.type == "flow.read")
        await a1.ok("flow.content", {"transfer_id": read.payload["transfer_id"], "hash": h, "content_b64": "QUJD"})
        apply = next(p for p in await w1.drain_pushes() if p.type == "flow.apply").payload
        return {"read": read.payload, "apply": apply}

    # another file in the same folder is not this flow's
    await a1.ok("index.event", {"event": {"op": "modify", "path": "C:/out/other.docx", "hash": "o1"}})
    assert "flow.read" not in a1.push_types(await a1.drain_pushes())
    got = await change("C:/out/report.docx", "r1")
    assert got["apply"]["destination_path"] == "C:/in" and got["apply"]["relative_path"] == "report.docx"
    await w1.ok("flow.sync_result", {"transfer_id": got["apply"]["transfer_id"], "destination_id": dest["id"], "status": "success",
                                     "written_hash": "r1", "written_path": "C:/in/report.docx", "size_before": None, "size_after": 3})

    # renamed and moved at the source: the flow follows it, and its next change still syncs
    await a1.ok("index.event", {"event": {"op": "move", "path": "C:/archive/report-final.docx", "old_path": "C:/out/report.docx", "hash": "r1"}})
    assert (await a1.ok("flow.status", {"flow_id": flow["id"]}))["flow"]["source_path"] == "C:/archive/report-final.docx"
    await a1.drain_pushes()
    # the copy is moved at the destination: the next change is written where it now is
    await w1.ok("index.event", {"event": {"op": "move", "path": "C:/Users/ama/Desktop/report.docx", "old_path": "C:/in/report.docx", "hash": "r1"}})
    got = await change("C:/archive/report-final.docx", "r2")
    assert got["read"]["path"] == "C:/archive/report-final.docx"
    assert got["apply"]["destination_path"] == "C:/Users/ama/Desktop" and got["apply"]["relative_path"] == "report.docx"
    trail = {r["action_type"] for r in await engine.db.audit.recent(limit=50)}
    assert {"flow.source_followed", "flow.copy_followed"} <= trail


async def test_an_admin_who_left_hands_what_they_owned_to_another_admin(engine, org, connect):
    """An Admin leaving is known by their account being offboarded, not by the machine. What they still own (restrictions, flows, rules,
    actions, tasks to verify, issues) is handed to another Admin with a tool (TUI `account handover`)."""
    a1, a2 = await connect("cid-a1"), await connect("cid-a2")
    await connect("cid-w1")
    await a2.ok("index.event", {"event": {"op": "create", "path": "C:/HR/payroll.xlsx", "hash": "P1"}})
    [mark] = (await a2.ok("marks.create", {"paths": ["C:/HR/payroll.xlsx"], "keep": "path"}))["marks"]
    flow = (await a2.ok("flow.create", {"source_pc_id": org["a2_pc"], "source_path": "C:/out", "stages": [],
                                        "destinations": [{"destination_pc_id": org["w1_pc"], "destination_path": "C:/in"}]}))["flow"]
    shot = (await a2.ok("control.action_create", {"kind": "control", "builtin_type": "screenshot", "timeout_s": 10}))["action"]
    rule = (await a2.ok("control.event_create", {"type": "usb.inserted", "action_ids": [shot["id"]]}))["event"]

    owns = await a1.ok("hierarchy.ownership", {"account_id": org["a2"]})
    assert owns["owned"]["restrictions"] == [mark["id"]] and owns["owned"]["flows"] == [flow["id"]] and owns["owned"]["rules"] == [rule["id"]]
    assert await a1.err("hierarchy.hand_over", {"from_account_id": org["a2"], "to_account_id": org["a1"]}) == "conflict"   # still active
    await a1.ok("hierarchy.account_offboard", {"account_id": org["a2"]})
    assert await a1.err("hierarchy.hand_over", {"from_account_id": org["a2"], "to_account_id": org["w1"]}) == "invalid"   # not an Admin
    done = await a1.ok("hierarchy.hand_over", {"from_account_id": org["a2"], "to_account_id": org["a1"]})
    assert done["moved"]["restrictions"] == [mark["id"]] and done["moved"]["actions"] == [shot["id"]] and done["total"] == 4
    assert (await engine.db.marks.get(mark["id"]))["by_account_id"] == org["a1"]
    assert (await a1.ok("hierarchy.ownership", {"account_id": org["a2"]}))["total"] == 0
    assert any(r["action_type"] == "account.handed_over" for r in await engine.db.audit.recent(limit=10))


async def test_a_department_is_renamed_and_a_machine_moved_into_another_with_whoever_is_bound_to_it(engine, org, connect):
    a1, w1 = await connect("cid-a1"), await connect("cid-w1")
    sales = (await a1.ok("hierarchy.department_create", {"name": "Sales"}))["department_id"]
    assert (await a1.ok("hierarchy.department_rename", {"department_id": sales, "name": " Sales  and   Marketing "}))["name"] == "Sales and Marketing"
    assert await a1.err("hierarchy.department_rename", {"department_id": sales, "name": "HR"}) == "conflict"
    assert await a1.err("hierarchy.department_rename", {"department_id": 9999, "name": "Nowhere"}) == "not_found"
    moved = await a1.ok("hierarchy.pc_move", {"pc_id": org["w1_pc"], "department_id": sales})
    assert moved["moved"] is True and moved["accounts"] == [org["w1"]]
    assert (await engine.db.accounts.pc(org["w1_pc"]))["department_id"] == sales
    assert (await engine.db.accounts.by_id(org["w1"]))["department_id"] == sales
    assert (await a1.ok("hierarchy.pc_move", {"pc_id": org["w1_pc"], "department_id": sales}))["moved"] is False
    assert await a1.err("hierarchy.pc_move", {"pc_id": org["w1_pc"], "department_id": 9999}) == "not_found"
    assert await w1.err("hierarchy.pc_move", {"pc_id": org["w1_pc"], "department_id": org["fin"]}) == "forbidden"
    kinds = [r["action_type"] for r in await engine.db.pool.fetch("SELECT action_type FROM audit_log WHERE action_type IN ('department.renamed', 'pc.moved') ORDER BY id")]
    assert kinds == ["department.renamed", "pc.moved"]


async def test_an_account_of_the_parked_role_cannot_sign_in(engine, org, connect):
    """The Super User is parked (parked/README.md): its account is refused at the handshake; an Admin still signs in."""
    with pytest.raises(AssertionError, match="not part of this version"):
        await connect("cid-su")
    assert (await (await connect("cid-a1")).ok("hierarchy.tree"))["departments"]
