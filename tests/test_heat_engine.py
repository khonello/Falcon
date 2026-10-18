"""Hot first on the Engine, and a worst case clamped for marking restricted files."""

from __future__ import annotations

import pytest

from engine.console import marks as marks_mod
from engine.flow import sync
from tests.conftest import requires_db

pytestmark = requires_db


async def _index(engine, pc: int, folder: str, n: int, prefix: str = "f") -> None:
    batch = [{"op": "create", "path": f"{folder}\\{prefix}{i}.txt", "name": f"{prefix}{i}.txt", "hash": f"h-{folder}-{prefix}{i}"} for i in range(n)]
    await engine.file_index.ingest_sweep_batch(pc, batch, first=True)


async def test_anything_that_happens_to_a_file_or_a_machine_makes_it_hot(engine, org, connect):
    assert engine.heat.temperature(f"pc:{org['w1_pc']}") == 0.0
    await engine.file_index.ingest_event(org["w1_pc"], {"op": "create", "path": r"C:\Work\plan.docx", "name": "plan.docx", "hash": "h-plan"})
    assert engine.heat.hot(f"file:{org['w1_pc']}:C:\\Work\\plan.docx") and engine.heat.hot(f"pc:{org['w1_pc']}")
    assert engine.heat.hot(f"file:{org['w1_pc']}:C:\\Work")                                       # and the folder above it
    a1 = await connect("cid-a1")
    await a1.ok("flow.list")
    assert engine.heat.hot(f"pc:{org['a1_pc']}")                                                 # a machine that speaks
    await a1.call("hierarchy.pc_info", {"pc_id": org["w2_pc"]}) if False else None
    assert engine.heat.temperature(f"pc:{org['w2_pc']}") == 0.0                                  # a machine nobody has touched is cold


async def test_healing_flows_goes_to_the_machines_in_use_first_and_leaves_none_out(engine, org, monkeypatch):
    rows = [{"id": i, "source_pc_id": pc, "status": "active", "consent_status": "granted"} for i, pc in enumerate([org["w1_pc"], org["w2_pc"], org["a1_pc"], org["a2_pc"]], start=1)]

    async def list_all():
        return rows

    called: list[int] = []

    async def catch_up(eng, flow_id, only=None):
        called.append(flow_id)
        return True

    monkeypatch.setattr(engine.db.flows, "list_all", list_all)
    monkeypatch.setattr(sync, "catch_up", catch_up)
    engine.heat.touch(f"pc:{org['a2_pc']}", folder=False)                                        # the fourth machine is the one in use
    await sync.heal(engine)
    assert called[0] == 4 and sorted(called) == [1, 2, 3, 4]                                     # hot first; every other flow still done


async def test_a_catch_up_sends_the_files_being_worked_on_before_the_rest(engine, org, connect, monkeypatch):
    a1 = await connect("cid-a1")
    made = await a1.ok("flow.create", {"source_pc_id": org["a1_pc"], "source_path": "C:/out", "stages": [], "destinations": [{"destination_pc_id": org["w1_pc"], "destination_path": "C:/in"}]})
    flow = made["flow"]
    entries = [{"relative_path": f"f{i:03d}.txt", "hash": f"h{i}"} for i in range(40)]
    sent: list[str] = []

    async def propagate(eng, flow_id, source_file, rel, digest, **kw):
        sent.append(rel)
        return "t"

    monkeypatch.setattr(sync, "propagate", propagate)
    engine.heat.touch(f"file:{org['a1_pc']}:C:/out/f037.txt")                                    # a file somebody is working on, last in the listing
    await sync._reconcile(engine, sync.Listing(flow["id"], None, entries))
    assert sent[0] == "f037.txt" and len(sent) == 40 and len(set(sent)) == 40


async def test_marking_a_folder_is_assessed_first_and_a_huge_one_is_refused_with_the_reason(engine, org, connect, monkeypatch):
    monkeypatch.setattr(marks_mod, "MARK_MAX_FILES", 30)
    monkeypatch.setattr(marks_mod, "MARK_CONFIRM_FILES", 5)
    a1 = await connect("cid-a1")
    pc = org["a1_pc"]
    await _index(engine, pc, r"C:\proj\src", 12)
    await _index(engine, pc, r"C:\proj\node_modules\leftpad", 60, "g")                            # generated: covered, never tracked one by one
    await _index(engine, pc, r"C:\huge\data", 80, "d")
    ass = (await a1.ok("marks.assess", {"paths": [r"C:\proj", r"C:\huge", r"C:\proj\src\f1.txt"]}))["assessed"]
    proj, huge, one = ass
    assert proj["files"] == 72 and proj["junk"] == 60 and proj["tracked"] == 12 and proj["verdict"] == "large" and "node_modules" in " ".join(proj["reasons"])
    assert huge["verdict"] == "too_large" and huge["tracked"] == 80 and any("more than one mark can hold" in r for r in huge["reasons"]) and huge["seconds"] > 0
    assert one["verdict"] == "ok" and one["kind"] == "file"
    # create: the huge one is refused whole, and says why; nothing was half-done
    assert await a1.err("marks.create", {"paths": [r"C:\proj\src\f1.txt", r"C:\huge"], "keep": "machine"}) == "invalid"
    assert await engine.db.marks.active_on_pc(pc) == []
    # the large one needs to be confirmed
    assert await a1.err("marks.create", {"paths": [r"C:\proj"], "keep": "machine"}) == "conflict"
    made = await a1.ok("marks.create", {"paths": [r"C:\proj"], "keep": "machine", "confirm_large": True})
    (mark,) = made["marks"]
    hashes = await engine.db.marks.hashes(mark["id"])
    assert len(hashes) == 12                                                                      # the twelve that matter; the sixty generated ones are covered, not tracked


async def test_a_machine_cannot_be_made_to_track_more_than_it_can_hold(engine, org, connect, monkeypatch):
    monkeypatch.setattr(marks_mod, "MARK_MAX_FILES", 30)
    monkeypatch.setattr(marks_mod, "MARK_MAX_MACHINE", 40)
    monkeypatch.setattr(marks_mod, "MARK_CONFIRM_FILES", 1000)
    a1 = await connect("cid-a1")
    pc = org["a1_pc"]
    await _index(engine, pc, r"C:\one", 25, "a")
    await _index(engine, pc, r"C:\two", 25, "b")
    await a1.ok("marks.create", {"paths": [r"C:\one"], "keep": "machine"})
    assert await a1.err("marks.create", {"paths": [r"C:\two"], "keep": "machine"}) == "invalid"       # 25 + 25 is more than the 40 this machine tracks
    ass = (await a1.ok("marks.assess", {"paths": [r"C:\two"]}))
    assert ass["tracked_now"] == 25 and ass["machine_limit"] == 40 and "already tracks 25" in " ".join(ass["assessed"][0]["reasons"])


async def test_healing_marks_looks_at_a_few_thousand_hashes_a_pass_and_carries_on_where_it_left_off(engine, org, monkeypatch):
    monkeypatch.setattr(marks_mod, "HEAL_BUDGET", 4)
    pc = org["a1_pc"]
    mark = await engine.db.marks.create("folder", "Big", pc, r"C:\big", "machine", org["a1"], None)
    for i in range(10):
        await engine.db.marks.add_hash(mark, f"hash{i:02d}", rf"C:\big\f{i}.txt")
    looked: list[str] = []
    real = engine.db.file_index.by_hash

    async def by_hash(digest):
        looked.append(digest)
        return await real(digest)

    monkeypatch.setattr(engine.db.file_index, "by_hash", by_hash)
    marks_mod._heal_cursor.clear()
    for _ in range(3):
        await marks_mod.heal(engine)
    assert len(looked) == 12 and set(looked) == {f"hash{i:02d}" for i in range(10)}               # four a pass, round and round: the whole of it covered in three
    pytest.approx(1)
