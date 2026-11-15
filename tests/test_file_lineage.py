"""One identity for a file that survives rename, move and edit (proposals item 1, the exact links; migration 061, engine/file_index.py `_link`).

A row of the index is a place; its lineage is the file. These are the ways a real machine changes a file, each played as the Worker reports it."""

from __future__ import annotations

import os

from tests.conftest import requires_db
from worker_client import fsmeta

pytestmark = requires_db


def ev(op: str, path: str, **kw) -> dict:
    return {"op": op, "path": path, "name": path.rsplit("\\", 1)[-1], **kw}


async def _row(engine, pc: int, path: str) -> dict:
    row = await engine.db.file_index.by_path(pc, path)
    assert row is not None, path
    return row


async def test_an_edit_and_a_rename_keep_the_file_and_a_new_file_is_its_own(engine, org):
    fi, pc = engine.file_index, org["w1_pc"]
    await fi.ingest_event(pc, ev("create", r"C:\Users\ama\Documents\budget.xlsx", hash="h1", file_id="a:1"))
    first = await _row(engine, pc, r"C:\Users\ama\Documents\budget.xlsx")
    assert first["lineage_id"] and first["linked_by"] == "new" and first["file_id"] == "a:1"
    await fi.ingest_event(pc, ev("modify", r"C:\Users\ama\Documents\budget.xlsx", hash="h2", file_id="a:1"))
    assert (await _row(engine, pc, r"C:\Users\ama\Documents\budget.xlsx"))["lineage_id"] == first["lineage_id"]
    await fi.ingest_event(pc, ev("move", r"C:\Users\ama\Documents\budget-final.xlsx", old_path=r"C:\Users\ama\Documents\budget.xlsx", hash="h2", file_id="a:1"))
    renamed = await _row(engine, pc, r"C:\Users\ama\Documents\budget-final.xlsx")
    assert renamed["lineage_id"] == first["lineage_id"] and renamed["linked_by"] == "move"
    assert (await _row(engine, pc, r"C:\Users\ama\Documents\budget.xlsx"))["gone_at"] is not None
    await fi.ingest_event(pc, ev("create", r"C:\Users\ama\Documents\other.docx", hash="h9", file_id="a:9"))
    assert (await _row(engine, pc, r"C:\Users\ama\Documents\other.docx"))["lineage_id"] != first["lineage_id"]


async def test_an_editors_save_by_replace_is_still_the_same_file(engine, org):
    """Word: write a temp file, move the document aside, move the temp file into its name, delete the old one. Each step changes the Windows id."""
    fi, pc, doc = engine.file_index, org["w1_pc"], r"C:\Users\ama\Documents\report.docx"
    await fi.ingest_event(pc, ev("create", doc, hash="h1", file_id="a:10"))
    lineage = (await _row(engine, pc, doc))["lineage_id"]
    await fi.ingest_event(pc, ev("create", r"C:\Users\ama\Documents\~WRD0001.tmp", hash="h2", file_id="a:11"))
    await fi.ingest_event(pc, ev("move", r"C:\Users\ama\Documents\~WRL0002.tmp", old_path=doc, hash="h1", file_id="a:10"))
    await fi.ingest_event(pc, ev("move", doc, old_path=r"C:\Users\ama\Documents\~WRD0001.tmp", hash="h2", file_id="a:11"))
    await fi.ingest_event(pc, ev("delete", r"C:\Users\ama\Documents\~WRL0002.tmp"))
    saved = await _row(engine, pc, doc)
    assert saved["lineage_id"] == lineage and saved["linked_by"] == "replaced" and saved["content_hash"] == "h2" and saved["gone_at"] is None
    # an editor that writes a temp file and moves it straight over the document (the document never leaves)
    note = r"C:\Users\ama\Desktop\notes.txt"
    await fi.ingest_event(pc, ev("create", note, hash="n1", file_id="a:20"))
    kept = (await _row(engine, pc, note))["lineage_id"]
    await fi.ingest_event(pc, ev("create", note + ".tmp", hash="n2", file_id="a:21"))
    await fi.ingest_event(pc, ev("move", note, old_path=note + ".tmp", hash="n2", file_id="a:21"))
    assert (await _row(engine, pc, note))["lineage_id"] == kept


async def test_a_rename_the_watcher_missed_is_found_by_the_windows_file_id(engine, org):
    fi, pc = engine.file_index, org["w1_pc"]
    await fi.ingest_event(pc, ev("create", r"C:\Users\ama\Documents\plan.docx", hash="p1", file_id="a:30"))
    lineage = (await _row(engine, pc, r"C:\Users\ama\Documents\plan.docx"))["lineage_id"]
    await fi.ingest_event(pc, ev("delete", r"C:\Users\ama\Documents\plan.docx"))
    await fi.ingest_event(pc, ev("create", r"C:\Users\ama\Documents\Old\plan-v1.docx", hash="p1", file_id="a:30"))     # a delete and a create, as polling saw it
    found = await _row(engine, pc, r"C:\Users\ama\Documents\Old\plan-v1.docx")
    assert found["lineage_id"] == lineage and found["linked_by"] == "file_id"
    # the same id on another machine means nothing (an id is the machine's own)
    await fi.ingest_event(org["w2_pc"], ev("create", r"C:\x\y.docx", hash="other", file_id="a:30"))
    assert (await _row(engine, org["w2_pc"], r"C:\x\y.docx"))["lineage_id"] != lineage


async def test_a_copy_is_a_file_of_its_own_that_remembers_what_it_was_copied_from(engine, org):
    fi, pc = engine.file_index, org["w1_pc"]
    await fi.ingest_event(pc, ev("create", r"C:\Finance\payroll.xlsx", hash="q1", file_id="a:40"))
    original = await _row(engine, pc, r"C:\Finance\payroll.xlsx")
    await fi.ingest_event(pc, ev("copy", r"C:\Users\ama\Desktop\payroll.xlsx", old_path=r"C:\Finance\payroll.xlsx", hash="q1", file_id="a:41"))
    copy = await _row(engine, pc, r"C:\Users\ama\Desktop\payroll.xlsx")
    assert copy["lineage_id"] != original["lineage_id"] and copy["linked_by"] == "copy"
    assert (await engine.db.file_index.lineage(copy["lineage_id"]))["copy_of"] == original["lineage_id"]
    # the same content turning up on another machine, with no copy event: a copy too, by its content
    await fi.ingest_event(org["w2_pc"], ev("create", r"C:\Users\kojo\Downloads\payroll.xlsx", hash="q1", file_id="b:1"))
    there = await _row(engine, org["w2_pc"], r"C:\Users\kojo\Downloads\payroll.xlsx")
    assert there["linked_by"] == "hash" and (await engine.db.file_index.lineage(there["lineage_id"]))["copy_of"] == original["lineage_id"]


async def test_a_file_carried_to_a_drive_and_edited_there_is_still_one_journey(engine, org, connect):
    """The gap this closes: the copy's new content matches nothing, but the copy remembers where it came from."""
    fi, pc = engine.file_index, org["w1_pc"]
    await fi.ingest_event(pc, ev("create", r"C:\Finance\budget-2026.xlsx", hash="b1", file_id="a:50"))
    await fi.ingest_event(pc, ev("copy", r"E:\budget-2026.xlsx", old_path=r"C:\Finance\budget-2026.xlsx", hash="b1", file_id="e:1"))
    await fi.ingest_event(pc, ev("modify", r"E:\budget-2026.xlsx", hash="b2-edited", file_id="e:1"))
    await fi.ingest_event(pc, ev("move", r"E:\notes.xlsx", old_path=r"E:\budget-2026.xlsx", hash="b2-edited", file_id="e:1"))
    carried = await _row(engine, pc, r"E:\notes.xlsx")
    a1 = await connect("cid-a1")
    journey = await a1.ok("resource.journey", {"file_index_id": carried["id"]})
    paths = {p["path"] for p in journey["places"]}
    assert r"C:\Finance\budget-2026.xlsx" in paths and r"E:\notes.xlsx" in paths
    kinds = [e["kind"] for e in journey["events"]]
    assert "first_seen" in kinds and "edited" in kinds and "renamed" in kinds
    # and the lineage, as an Admin reads it
    lin = await a1.ok("index.lineage", {"file_index_id": carried["id"]})
    assert lin["lineage"]["first_name"] == "budget-2026.xlsx" and lin["lineage"]["began_by"] == "copy" and lin["lineage"]["copy_of"]
    assert [p["linked_by"] for p in lin["places"]] == ["copy", "move"] and lin["places"][1]["how"] == "moved or renamed here"
    root = await a1.ok("index.lineage", {"file_index_id": (await _row(engine, pc, r"C:\Finance\budget-2026.xlsx"))["id"]})
    assert [c["first_path"] for c in root["copies"]] == [r"E:\budget-2026.xlsx"]
    assert await (await connect("cid-a2")).err("index.lineage", {"file_index_id": carried["id"]}) == "not_found"     # another department's machine


async def test_the_sweep_gives_a_place_it_meets_for_the_first_time_its_file(engine, org):
    fi, pc = engine.file_index, org["w1_pc"]
    await fi.ingest_event(pc, ev("create", r"C:\Users\ama\Documents\a.txt", hash="s1", file_id="a:60"))
    lineage = (await _row(engine, pc, r"C:\Users\ama\Documents\a.txt"))["lineage_id"]
    await fi.ingest_sweep_batch(pc, [ev("modify", r"C:\Users\ama\Documents\a.txt", hash="s1", file_id="a:60"),
                                     ev("modify", r"C:\Users\ama\Documents\b.txt", hash="s2", file_id="a:61")], first=True)
    assert (await _row(engine, pc, r"C:\Users\ama\Documents\a.txt"))["lineage_id"] == lineage                    # left as it was
    b = await _row(engine, pc, r"C:\Users\ama\Documents\b.txt")
    assert b["lineage_id"] and b["linked_by"] == "new" and b["file_id"] == "a:61"


def test_the_worker_gives_each_file_its_windows_id(tmp_path):
    f = tmp_path / "x.txt"
    f.write_text("one")
    fid = fsmeta.file_id_of(str(f))
    assert fid and ":" in fid
    os.replace(f, tmp_path / "y.txt")                                               # a rename on the same drive keeps it
    assert fsmeta.file_id_of(str(tmp_path / "y.txt")) == fid
    assert fsmeta.file_id_of(str(tmp_path / "missing")) is None
