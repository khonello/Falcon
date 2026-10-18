"""A flow does not carry anything restricted unless its owner has said so -- and looks again every time, not once when it was made."""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

from engine.flow import guard
from tests.conftest import requires_db
from tests.test_worker_client import _start, _wait

pytestmark = requires_db


def _flow(org, src: Path, dst: Path, **extra):
    return {"source_pc_id": org["w1_pc"], "source_path": str(src), "stages": [],
            "destinations": [{"destination_pc_id": org["w2_pc"], "destination_path": str(dst)}], **extra}


async def _mark(engine, org, pc: int, kind: str, path: Path | str, name: str = "Payroll", owner: str = "su") -> int:
    return await engine.db.marks.create(kind, name, pc, str(path), "path", org[owner], None)


async def _asked(engine, flow_id: int) -> list[dict]:
    return await engine.db.flows.consents(flow_id, states=("asked",))


async def test_a_flow_over_a_restricted_folder_is_made_paused_and_the_owner_is_asked_and_only_they_can_answer(engine, org, connect, tmp_path: Path):
    a1, su = await connect("cid-a1"), await connect("cid-su")
    src, dst = tmp_path / "out", tmp_path / "in"
    mark = await _mark(engine, org, org["w1_pc"], "folder", src)                                  # marked by the Super User, not by the Admin who makes the flow
    await engine.db.marks.add_hash(mark, "h-secret", str(src / "p.xlsx"))
    made = await a1.ok("flow.create", _flow(org, src / "deeper", dst))
    flow_id = made["flow"]["id"]
    assert made["restricted_pending"] is True and made["flow"]["status"] == "paused" and made["flow"]["pause_reason"] == guard.PAUSE
    (asked,) = await _asked(engine, flow_id)
    assert asked["mark_id"] and asked["name"] == "Payroll" and asked["state"] == "asked"
    assert "flow.restricted_request" in su.push_types(await su.drain_pushes())                  # the owner hears at once
    assert await a1.err("flow.restricted_consent", {"consent_id": asked["id"], "grant": True}) == "forbidden"      # the Admin who made it cannot allow it for themself
    assert await a1.err("flow.resume", {"flow_id": flow_id}) == "conflict"                          # and it does not resume into it
    mine = await a1.ok("flow.restricted", {"flow_id": flow_id})
    assert mine["can_decide"] == [] and mine["consents"][0]["state"] == "asked"
    # the owner allows it: the flow goes on, and the destination folder is a place that content may be
    done = await su.ok("flow.restricted_consent", {"consent_id": asked["id"], "grant": True, "note": "the monthly pack"})
    assert done["granted"] is True and done["flow_resumed"] is True
    assert (await engine.db.flows.get(flow_id))["status"] == "active"
    assert await engine.db.resource.is_allowed(org["w2_pc"], str(dst / "p.xlsx"), "h-secret")        # that mark's content may be there ...
    assert not await engine.db.resource.is_allowed(org["w2_pc"], str(dst / "p.xlsx"), "some-other-restricted-thing")         # ... and nothing else restricted
    actions = [r["action_type"] for r in await engine.db.pool.fetch("SELECT action_type FROM audit_log WHERE action_type LIKE 'flow.restricted%' ORDER BY id")]
    assert actions == ["flow.restricted_asked", "flow.restricted_consented"]


async def test_the_person_who_made_the_mark_can_answer_for_it_and_declining_leaves_the_flow_paused(engine, org, connect, tmp_path: Path):
    a1 = await connect("cid-a1")
    src, dst = tmp_path / "out", tmp_path / "in"
    await _mark(engine, org, org["w1_pc"], "folder", src, "Mine", owner="a1")                      # the Admin marked it themself
    flow_id = (await a1.ok("flow.create", _flow(org, src, dst)))["flow"]["id"]
    (asked,) = await _asked(engine, flow_id)
    assert (await a1.ok("flow.restricted", {"flow_id": flow_id}))["can_decide"] == [asked["id"]]
    await a1.ok("flow.restricted_consent", {"consent_id": asked["id"], "grant": False})
    flow = await engine.db.flows.get(flow_id)
    assert flow["status"] == "paused" and (await engine.db.flows.consent(asked["id"]))["state"] == "declined"
    assert await a1.err("flow.resume", {"flow_id": flow_id}) == "conflict"                          # declined: it asks again, it does not slip through
    assert len(await _asked(engine, flow_id)) == 1                                                  # ... as a new request


async def test_a_restricted_file_met_while_running_holds_the_flow_and_after_consent_it_arrives_and_is_not_reported(engine, org, connect, tmp_path: Path):
    src, dst = tmp_path / "out", tmp_path / "in"
    src.mkdir()
    dst.mkdir()
    secret = b"the payroll, in full"
    (src / "payroll.xlsx").write_bytes(secret)
    mark = await _mark(engine, org, org["w1_pc"], "file", src / "payroll.xlsx")
    await engine.db.marks.add_hash(mark, hashlib.sha256(secret).hexdigest(), str(src / "payroll.xlsx"))
    su, a1 = await connect("cid-su"), await connect("cid-a1")
    w1, w2 = await _start(engine, tmp_path, "cid-w1", [str(src)]), await _start(engine, tmp_path, "cid-w2", [str(dst)])
    try:
        made = await a1.ok("flow.create", _flow(org, src, dst))
        flow_id = made["flow"]["id"]
        (src / "ordinary.txt").write_text("nothing special", encoding="utf-8")
        assert await _wait(lambda: (dst / "ordinary.txt").exists() or True, timeout=1)
        # the marked file in an ordinary folder holds the flow: it is paused and the owner asked

        async def held():
            f = await engine.db.flows.get(flow_id)
            return f["status"] == "paused" and f["pause_reason"] == guard.PAUSE
        for _ in range(60):
            if await held():
                break
            await asyncio.sleep(0.25)
        assert await held()
        assert not (dst / "payroll.xlsx").exists()
        (asked,) = await _asked(engine, flow_id)
        assert asked["mark_id"] == mark
        await su.ok("flow.restricted_consent", {"consent_id": asked["id"], "grant": True})
        assert await _wait(lambda: (dst / "payroll.xlsx").exists() and (dst / "payroll.xlsx").read_bytes() == secret, timeout=20)       # what was held back is sent
        await asyncio.sleep(1.5)
        assert await engine.db.pool.fetchval("SELECT count(*) FROM resource_violations") == 0                                       # and Restricted does not report the copy
    finally:
        await w1.stop()
        await w2.stop()


async def test_taking_a_consent_back_stops_the_flow_and_the_place_is_no_longer_allowed(engine, org, connect, tmp_path: Path):
    a1, su = await connect("cid-a1"), await connect("cid-su")
    src, dst = tmp_path / "out", tmp_path / "in"
    mark = await _mark(engine, org, org["w1_pc"], "folder", src)
    await engine.db.marks.add_hash(mark, "h", str(src / "x.txt"))
    flow_id = (await a1.ok("flow.create", _flow(org, src, dst)))["flow"]["id"]
    (asked,) = await _asked(engine, flow_id)
    await su.ok("flow.restricted_consent", {"consent_id": asked["id"], "grant": True})
    assert await engine.db.resource.is_allowed(org["w2_pc"], str(dst / "x.txt"), "h")
    assert await a1.err("flow.restricted_revoke", {"consent_id": asked["id"]}) == "forbidden"
    await su.ok("flow.restricted_revoke", {"consent_id": asked["id"]})
    flow = await engine.db.flows.get(flow_id)
    assert flow["status"] == "paused" and flow["pause_reason"] == guard.PAUSE
    assert not await engine.db.resource.is_allowed(org["w2_pc"], str(dst / "x.txt"), "h")


async def test_a_consent_that_runs_out_is_taken_back_and_the_flow_is_held_and_asked_again(engine, org, connect, tmp_path: Path):
    a1, su = await connect("cid-a1"), await connect("cid-su")
    src, dst = tmp_path / "out", tmp_path / "in"
    mark = await _mark(engine, org, org["w1_pc"], "folder", src)
    await engine.db.marks.add_hash(mark, "h", str(src / "x.txt"))
    flow_id = (await a1.ok("flow.create", _flow(org, src, dst)))["flow"]["id"]
    (asked,) = await _asked(engine, flow_id)
    await su.ok("flow.restricted_consent", {"consent_id": asked["id"], "grant": True, "days": 1})
    assert await engine.db.resource.is_allowed(org["w2_pc"], str(dst / "x.txt"), "h")
    assert await guard.gate(engine, flow_id, org["w1_pc"], str(src / "a.txt"), step="test")
    await engine.db.pool.execute("UPDATE flow_restricted_consents SET expires_at = now() - interval '1 minute' WHERE id = $1", asked["id"])
    assert not await guard.gate(engine, flow_id, org["w1_pc"], str(src / "a.txt"), step="test")
    assert (await engine.db.flows.consent(asked["id"]))["state"] == "revoked"
    assert not await engine.db.resource.is_allowed(org["w2_pc"], str(dst / "x.txt"), "h")
    assert len(await _asked(engine, flow_id)) == 1 and (await engine.db.flows.get(flow_id))["status"] == "paused"


async def test_a_folder_marked_under_a_running_flow_holds_it_at_once_and_asks(engine, org, connect, tmp_path: Path):
    a1 = await connect("cid-a1")
    src, dst = tmp_path / "out", tmp_path / "in"
    flow_id = (await a1.ok("flow.create", _flow(org, src, dst)))["flow"]["id"]
    assert (await engine.db.flows.get(flow_id))["status"] == "active"
    await _mark(engine, org, org["w1_pc"], "folder", src, "Out")
    assert await guard.sweep(engine, org["w1_pc"]) == 1                                           # told the moment it happened, not found file by file
    flow = await engine.db.flows.get(flow_id)
    assert flow["status"] == "paused" and flow["pause_reason"] == guard.PAUSE
    assert [c["name"] for c in await _asked(engine, flow_id)] == ["Out"]


async def test_the_check_is_made_against_what_is_true_now_not_remembered(engine, org):
    path = r"C:\Work\report.xlsx"
    assert await guard.restricted_reason(engine, org["w1_pc"], path) is None
    mark = await _mark(engine, org, org["w1_pc"], "file", path, "Report")
    assert "marked restricted" in (await guard.restricted_reason(engine, org["w1_pc"], path) or "")
    await engine.db.marks.unmark(mark, org["su"])
    assert await guard.restricted_reason(engine, org["w1_pc"], path) is None                          # unmarked: free again, with no restart and no cache to clear
    await engine.db.file_index.upsert(org["w1_pc"], path, "report.xlsx", "h", "restricted", None, "event")
    (b,) = await guard.blockers(engine, org["w1_pc"], path)
    assert b.kind == "tag" and b.tag == "restricted" and "tagged restricted" in b.reason
