"""A flow never touches anything restricted -- and looks again every time, not once when it was made."""

from __future__ import annotations

import asyncio
import hashlib
from pathlib import Path

from engine.flow import guard
from tests.conftest import requires_db
from tests.test_worker_client import _admin, _start, _wait

pytestmark = requires_db


def _flow(org, src: Path, dst: Path, **extra):
    return {"source_pc_id": org["w1_pc"], "source_path": str(src), "stages": [],
            "destinations": [{"destination_pc_id": org["w2_pc"], "destination_path": str(dst)}], **extra}


async def _mark(engine, org, pc: int, kind: str, path: Path | str, name: str = "Payroll") -> int:
    return await engine.db.marks.create(kind, name, pc, str(path), "path", org["a1"], None)


async def test_a_flow_cannot_be_made_over_a_restricted_folder_at_either_end(engine, org, connect, tmp_path: Path):
    a1 = await connect("cid-a1")
    src, dst = tmp_path / "out", tmp_path / "in"
    await _mark(engine, org, org["w1_pc"], "folder", src)
    payload = {"source_pc_id": org["w1_pc"], "source_path": str(src / "deeper"), "stages": [], "destinations": [{"destination_pc_id": org["w2_pc"], "destination_path": str(dst)}]}
    assert await a1.err("flow.create", payload) == "invalid"                                          # a folder inside a restricted folder is restricted too
    await _mark(engine, org, org["w2_pc"], "folder", dst, "Board")
    ok_src = tmp_path / "elsewhere"
    assert await a1.err("flow.create", {**payload, "source_path": str(ok_src)}) == "invalid"             # ... and so is a destination


async def test_a_restricted_file_in_an_ordinary_folder_is_never_sent_and_a_copy_of_its_content_is_not_either(engine, org, tmp_path: Path):
    src, dst = tmp_path / "out", tmp_path / "in"
    src.mkdir()
    dst.mkdir()
    secret = b"the payroll, in full"
    digest = hashlib.sha256(secret).hexdigest()
    (src / "payroll.xlsx").write_bytes(secret)
    mark = await _mark(engine, org, org["w1_pc"], "file", src / "payroll.xlsx")
    await engine.db.marks.add_hash(mark, digest, str(src / "payroll.xlsx"))
    w1, w2, admin = await _start(engine, tmp_path, "cid-w1", [str(src)]), await _start(engine, tmp_path, "cid-w2", [str(dst)]), await _admin(engine)
    try:
        await admin.call("flow.create", _flow(org, src, dst))
        (src / "ordinary.txt").write_text("nothing special", encoding="utf-8")
        (src / "copy-of-payroll.bin").write_bytes(secret)                                              # same content, another name, another place in the folder
        assert await _wait(lambda: (dst / "ordinary.txt").exists(), timeout=15)                        # the flow works
        await asyncio.sleep(3)
        assert not (dst / "payroll.xlsx").exists() and not (dst / "copy-of-payroll.bin").exists()     # ... and left both alone
        said = await engine.db.pool.fetch("SELECT detail FROM audit_log WHERE action_type = 'flow.refused_restricted'")
        assert len(said) >= 2 and any("marked restricted" in str(r["detail"]) for r in said) and any("a copy of" in str(r["detail"]) for r in said)
    finally:
        await admin.close()
        await w1.stop()
        await w2.stop()


async def test_a_folder_marked_restricted_under_a_running_flow_stops_it_at_once_and_it_will_not_resume_into_it(engine, org, tmp_path: Path):
    src, dst = tmp_path / "out", tmp_path / "in"
    src.mkdir()
    dst.mkdir()
    w1, w2, admin = await _start(engine, tmp_path, "cid-w1", [str(src)]), await _start(engine, tmp_path, "cid-w2", [str(dst)]), await _admin(engine)
    try:
        made = await admin.call("flow.create", _flow(org, src, dst))
        flow_id = made["flow"]["id"]
        (src / "a.txt").write_text("a", encoding="utf-8")
        assert await _wait(lambda: (dst / "a.txt").exists(), timeout=15)
        await _mark(engine, org, org["w1_pc"], "folder", src, "Out")
        assert await guard.sweep(engine, org["w1_pc"]) == 1                                           # told the moment it happened, not found file by file
        flow = await engine.db.flows.get(flow_id)
        assert flow["status"] == "paused" and flow["pause_reason"] == "restricted:source"
        (src / "b.txt").write_text("b", encoding="utf-8")
        await asyncio.sleep(3)
        assert not (dst / "b.txt").exists()
        try:
            await admin.call("flow.resume", {"flow_id": flow_id})
            raise AssertionError("it resumed into a restricted folder")
        except Exception as exc:  # noqa: BLE001
            assert "restricted" in str(exc).lower()
    finally:
        await admin.close()
        await w1.stop()
        await w2.stop()


async def test_a_destination_that_becomes_restricted_is_paused_and_nothing_more_is_written_there(engine, org, tmp_path: Path):
    src, dst = tmp_path / "out", tmp_path / "in"
    src.mkdir()
    dst.mkdir()
    w1, w2, admin = await _start(engine, tmp_path, "cid-w1", [str(src)]), await _start(engine, tmp_path, "cid-w2", [str(dst)]), await _admin(engine)
    try:
        made = await admin.call("flow.create", _flow(org, src, dst))
        await _mark(engine, org, org["w2_pc"], "folder", dst, "Board")
        assert await guard.sweep(engine, org["w2_pc"]) == 1
        flow = await engine.db.flows.get(made["flow"]["id"])
        assert flow["destinations"][0]["paused_reason"] == "destination:restricted"
        (src / "c.txt").write_text("c", encoding="utf-8")
        await asyncio.sleep(3)
        assert not (dst / "c.txt").exists()
    finally:
        await admin.close()
        await w1.stop()
        await w2.stop()


async def test_the_check_is_made_against_what_is_true_now_not_remembered(engine, org):
    path = r"C:\Work\report.xlsx"
    assert await guard.restricted_reason(engine, org["w1_pc"], path) is None
    mark = await _mark(engine, org, org["w1_pc"], "file", path, "Report")
    assert "marked restricted" in (await guard.restricted_reason(engine, org["w1_pc"], path) or "")
    await engine.db.marks.unmark(mark, org["a1"])
    assert await guard.restricted_reason(engine, org["w1_pc"], path) is None                          # unmarked: free again, with no restart and no cache to clear
    await engine.db.file_index.upsert(org["w1_pc"], path, "report.xlsx", "h", "restricted", None, "event")
    assert "tagged restricted" in (await guard.restricted_reason(engine, org["w1_pc"], path) or "")
