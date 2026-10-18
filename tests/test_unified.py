"""The four core features as one system: what they say to each other on the spine, what they suggest to people, and what the Engine measures about itself."""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from common.detective import Context, Detective, Sig
from engine import database, detective, proposals
from engine.console import marks as marks_mod
from engine.cost import Cost
from engine.flow import guard
from tests.conftest import requires_db

# --- what the Engine measures about itself (no database) ------------------------------------------------------

def test_the_cost_of_work_is_measured_smoothed_and_assumed_until_it_is():
    c = Cost()
    assert c.per_unit("mark_file", 0.02) == (0.02, 0)
    c.observe("mark_file", 1.0, 10)
    assert c.per_unit("mark_file", 0.02) == (0.1, 1)
    c.observe("mark_file", 0.5, 10)
    per, n = c.per_unit("mark_file", 0.02)
    assert n == 2 and 0.05 < per < 0.1                                                           # the newest counts, the history too
    c.observe("mark_file", 1.0, 0)
    c.observe("mark_file", -1.0, 3)
    assert c.per_unit("mark_file", 0.02)[1] == 2                                                 # nonsense is not measured


async def test_the_engine_knows_how_late_its_own_loop_runs_and_says_how_much_longer_a_job_will_take():
    c = Cost()
    await c.probe()
    cap = c.capacity()
    assert cap["cpus"] >= 1 and cap["state"] in ("quiet", "moderate", "busy") and cap["loop_lag_ms"] >= 0
    c.lag_ms = 600.0
    assert c.capacity()["state"] == "busy" and c.slowdown() == 2.5
    c.lag_ms = 0.0


def test_a_list_read_cannot_return_more_than_the_hard_cap_and_only_plain_selects_are_wrapped(monkeypatch):
    monkeypatch.setattr(database, "HARD_ROWS", 7)
    assert database._capped("SELECT * FROM t").endswith("LIMIT 8")
    assert database._capped("SELECT * FROM t LIMIT 5") == "SELECT * FROM t LIMIT 5"
    assert database._capped("UPDATE t SET a = 1 RETURNING id") == "UPDATE t SET a = 1 RETURNING id"
    assert database._capped("SELECT * FROM t FOR UPDATE") == "SELECT * FROM t FOR UPDATE"
    assert database._capped("  WITH x AS (SELECT 1) SELECT * FROM x").startswith("SELECT * FROM (")


@requires_db
async def test_the_cap_cuts_a_table_that_has_outgrown_anything_a_page_was_built_for(engine, org, monkeypatch):
    for i in range(12):
        await engine.db.pool.execute("INSERT INTO departments (name) VALUES ($1)", f"Extra {i}")
    monkeypatch.setattr(database, "HARD_ROWS", 5)
    assert len(await engine.db.accounts.list_departments()) == 5
    monkeypatch.setattr(database, "HARD_ROWS", 200000)
    assert len(await engine.db.accounts.list_departments()) >= 14


@requires_db
async def test_the_marking_estimate_comes_from_what_marking_really_cost_and_says_so(engine, org, connect):
    a1 = await connect("cid-a1")
    for i in range(10):
        await engine.db.pool.execute("SELECT 1")
    await engine.file_index.ingest_sweep_batch(org["a1_pc"], [{"op": "create", "path": f"C:\\proj\\f{i}.txt", "name": f"f{i}.txt", "hash": f"h{i}"} for i in range(30)], first=True)
    first = (await a1.ok("marks.assess", {"paths": ["C:\\proj"]}))["assessed"][0]
    assert first["basis"].startswith("assumed") and first["per_file_ms"] == 20.0 and first["capacity"]["cpus"] >= 1
    engine.cost.observe("mark_file", 3.0, 30)                                                    # a marking took 100 ms a file here
    second = (await a1.ok("marks.assess", {"paths": ["C:\\proj"]}))["assessed"][0]
    assert second["basis"].startswith("measured over 1 earlier job") and second["per_file_ms"] == 100.0 and second["seconds"] >= 3.0
    await a1.ok("marks.create", {"paths": ["C:\\proj"], "keep": "machine"})
    assert engine.cost.per_unit("mark_file", 0.02)[1] == 2                                         # and the real marking was measured for next time


# --- events between the features --------------------------------------------------------------------------------

@requires_db
async def test_a_mark_is_an_event_and_every_flow_through_it_stops_and_asks_without_marks_knowing_about_flows(engine, org, connect, monkeypatch):
    a1 = await connect("cid-a1")
    made = await a1.ok("flow.create", {"source_pc_id": org["a1_pc"], "source_path": "C:/data", "stages": [], "destinations": [{"destination_pc_id": org["w1_pc"], "destination_path": "C:/in"}]})
    flow_id = made["flow"]["id"]
    await engine.file_index.ingest_sweep_batch(org["a1_pc"], [{"op": "create", "path": "C:\\data\\p.xlsx", "name": "p.xlsx", "hash": "h-p"}], first=True)
    seen = []

    async def look(event):
        seen.append(event.kind)

    engine.bus.on("mark.*", look, stage="tell", name="test")
    await a1.ok("marks.create", {"paths": ["C:\\data"], "keep": "machine"})
    assert "mark.created" in seen
    flow = await engine.db.flows.get(flow_id)
    assert flow["status"] == "paused" and flow["pause_reason"] == guard.PAUSE                    # Flow heard the event and held itself
    assert [c["name"] for c in await engine.db.flows.consents(flow_id, states=("asked",))] == ["data"]


@requires_db
async def test_a_task_states_what_it_expects_and_the_others_read_it_off_the_event(engine, org, connect):
    a1 = await connect("cid-a1")
    fid = await engine.file_index.ingest_event(org["w1_pc"], {"op": "create", "path": "C:\\Users\\kojo\\board-pack.zip", "name": "board-pack.zip", "hash": "h-board"})
    await a1.ok("task.create", {"assignee_account_id": org["w1"], "description": "put board-pack.zip on the drive", "verification_mode": "stack",
                                "items": [{"target_type": "file", "intent": "exists", "name": "board-pack.zip", "file_index_id": fid}]})
    assert engine.bus.counts["task.created"] == 1                                                # the creation is an event, not a call into Detective
    caught = []

    async def look(event):
        caught.append(event)

    engine.bus.on("file.*", look, stage="tell", name="test")
    await engine.file_index.ingest_event(org["w1_pc"], {"op": "copy", "path": "E:\\board-pack.zip", "old_path": "C:\\Users\\kojo\\board-pack.zip", "name": "board-pack.zip", "hash": "h-board"})
    await engine.file_index.ingest_event(org["w1_pc"], {"op": "create", "path": "C:\\Users\\kojo\\other.zip", "name": "other.zip", "hash": "h-other"})
    asked, other = caught[-2], caught[-1]
    assert asked.facts["task_expects"] is True and other.facts["task_expects"] is False


@requires_db
async def test_what_a_flow_delivers_put_there_by_hand_is_a_way_round_the_flow_and_a_flow_s_own_write_is_not(engine, org, connect):
    a1 = await connect("cid-a1")
    made = await a1.ok("flow.create", {"source_pc_id": org["a1_pc"], "source_path": "C:/out", "stages": [], "destinations": [{"destination_pc_id": org["w1_pc"], "destination_path": "C:/in"}]})
    flow_id, dest_id = made["flow"]["id"], made["flow"]["destinations"][0]["id"]
    await engine.file_index.ingest_sweep_batch(org["a1_pc"], [{"op": "create", "path": "C:\\out\\a.xlsx", "name": "a.xlsx", "hash": "h-a"}, {"op": "create", "path": "C:\\out\\b.xlsx", "name": "b.xlsx", "hash": "h-b"}], first=True)
    caught = []

    async def look(event):
        caught.append(event)

    engine.bus.on("file.*", look, stage="tell", name="test")
    await engine.db.flows.log_sync(dest_id, "h-b", "flow_sync", None, source_relative_path="b.xlsx", written_path="C:\\in\\b.xlsx", source_hash="h-b")        # the flow wrote b
    await engine.file_index.ingest_event(org["w1_pc"], {"op": "copy", "path": "C:\\in\\a.xlsx", "name": "a.xlsx", "hash": "h-a", "old_path": "E:\\a.xlsx"})        # a person put a there
    await engine.file_index.ingest_event(org["w1_pc"], {"op": "create", "path": "C:\\in\\b.xlsx", "name": "b.xlsx", "hash": "h-b"})
    by_hand, by_flow = caught[-2], caught[-1]
    assert by_hand.facts["flow_bypass"] == flow_id and by_hand.facts["flow_route"]["destination"] == [flow_id] and by_hand.facts["flow_wrote"] is False
    assert "flow_bypass" not in by_flow.facts and by_flow.facts["flow_wrote"] is True
    graphs = [r["graph"] for r in await engine.db.pool.fetch("SELECT graph FROM detective_findings")]
    assert "flow_bypass" in graphs


# --- what the features suggest to people ------------------------------------------------------------------------

async def _case(engine, org, with_old: bool = True):
    """A case on the first Worker's machine, made of copies out of a folder that is not restricted."""
    t = time.time()
    det = Detective(Context())
    for i in range(6):
        det.feed(Sig(t + i, org["w1_pc"], "copied", f"C:\\Users\\kojo\\Staging\\p{i}.xlsx", f"C:\\Data\\Reports\\p{i}.xlsx" if with_old else "", f"h{i}", by="hand", program="explorer.exe"))
    det.feed(Sig(t + 10, org["w1_pc"], "attached", "E:\\", device="E:\\", by="alone"))
    case = max(det.cases, key=lambda c: c.weight)
    case.id = await engine.db.detective.save_case(None, detective._row(case, 1, True), [detective._finding_row(f) for f in case.findings])
    return case


@requires_db
async def test_detective_proposes_to_the_features_it_cannot_change_and_nothing_happens_until_a_person_says_so(engine, org, connect, tmp_path):
    su, a1, a2 = await connect("cid-su"), await connect("cid-a1"), await connect("cid-a2")
    made = await a1.ok("flow.create", {"source_pc_id": org["w1_pc"], "source_path": "C:/Data/Reports", "stages": [], "destinations": [{"destination_pc_id": org["w2_pc"], "destination_path": "C:/in"}]})
    flow_id = made["flow"]["id"]
    case = await _case(engine, org)
    await engine.announce("case.raised", {"case_id": case.id, "pc_id": org["w1_pc"], "level": "urgent", "behaviours": ["exfiltration", "collection"], "intent": "Taking data out", "host": "FIN-01"})
    found = (await su.ok("proposals.list", {}))["proposals"]
    assert {p["kind"] for p in found} == {"pause_flow", "mark_folder"}
    mark = next(p for p in found if p["kind"] == "mark_folder")
    assert mark["detail"]["path"].lower() == "c:\\data\\reports" and mark["pc_id"] == org["w1_pc"]
    assert (await engine.db.flows.get(flow_id))["status"] == "active"                            # a suggestion changed nothing
    await engine.announce("case.raised", {"case_id": case.id, "pc_id": org["w1_pc"], "level": "urgent", "behaviours": ["exfiltration"], "intent": "Taking data out", "host": "FIN-01"})
    assert len((await su.ok("proposals.list", {}))["proposals"]) == 2                            # the same suggestion is not made twice while it stands
    # who can see and answer
    assert (await a2.ok("proposals.list", {}))["proposals"] == []                                 # another department's Admin sees none of it
    assert await a2.err("proposals.decide", {"proposal_id": mark["id"], "accept": True}) == "not_found"
    pause = next(p for p in found if p["kind"] == "pause_flow")
    # the Admin of the department owns the flow: accepting pauses it, as the Admin's act
    done = await a1.ok("proposals.decide", {"proposal_id": pause["id"], "accept": True, "note": "yes"})
    assert done["paused"] is True and (await engine.db.flows.get(flow_id))["status"] == "paused"
    acts = [r["action_type"] for r in await engine.db.pool.fetch("SELECT action_type FROM audit_log WHERE action_type LIKE 'proposal.%' ORDER BY id")]
    assert acts == ["proposal.made", "proposal.made", "proposal.accepted"]
    told = await su.ok("proposals.decide", {"proposal_id": mark["id"], "accept": False, "note": "not now"})
    assert told["accepted"] is False and (await su.ok("proposals.list", {"state": "dismissed"}))["proposals"][0]["id"] == mark["id"]
    assert await su.err("proposals.decide", {"proposal_id": mark["id"], "accept": True}) == "conflict"        # answered already


@requires_db
async def test_an_escalated_case_proposes_a_follow_up_for_the_super_user_to_give_as_a_task(engine, org, connect):
    su, a1 = await connect("cid-su"), await connect("cid-a1")
    case = await _case(engine, org)
    await a1.ok("detective.review", {"case_id": case.id, "outcome": "escalated", "note": "needs you"})
    (prop,) = [p for p in (await su.ok("proposals.list", {}))["proposals"] if p["kind"] == "follow_up_task"]
    got = await su.ok("proposals.decide", {"proposal_id": prop["id"], "accept": True})
    assert "case" in got["task_description"] and got["how"].startswith("create the task")


@requires_db
async def test_the_features_cannot_flood_a_person_with_suggestions(engine, org, monkeypatch):
    monkeypatch.setattr(proposals, "MAX_OPEN", 3)
    made = [await proposals.propose(engine, "mark_folder", f"k{i}", f"Mark {i}?", detail={}, pc_id=org["w1_pc"]) for i in range(6)]
    assert [m is not None for m in made] == [True, True, True, False, False, False]
    await asyncio.sleep(0)
    assert marks_mod.MARK_MAX_FILES > 0
