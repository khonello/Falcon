"""Flow with real Workers, for the things a live drill found: big files, files already there, what a paused or absent destination missed.

(`scripts/live_drill.py flow` runs the same ideas against a running Engine and separate Worker processes.)
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from pathlib import Path

from engine.flow import sync
from tests.conftest import requires_db
from tests.test_worker_client import _admin, _start, _wait

pytestmark = requires_db


def _flow(org, src: Path, dst: Path, **extra):
    return {"source_pc_id": org["w1_pc"], "source_path": str(src), "stages": [],
            "destinations": [{"destination_pc_id": org["w2_pc"], "destination_path": str(dst)}], **extra}


async def test_a_file_bigger_than_one_message_arrives_whole_in_chunks(engine, org, tmp_path: Path):
    src, dst = tmp_path / "out", tmp_path / "in"
    src.mkdir()
    dst.mkdir()
    w1, w2, admin = await _start(engine, tmp_path, "cid-w1", [str(src)]), await _start(engine, tmp_path, "cid-w2", [str(dst)]), await _admin(engine)
    try:
        await admin.call("flow.create", _flow(org, src, dst))
        big = bytes(range(256)) * (sync.CHUNK_BYTES * 5 // 256 + 17)                         # five and a bit chunks, not a round size
        (src / "big.bin").write_bytes(big)
        assert await _wait(lambda: (dst / "big.bin").exists() and (dst / "big.bin").stat().st_size == len(big), timeout=20)
        assert hashlib.sha256((dst / "big.bin").read_bytes()).hexdigest() == hashlib.sha256(big).hexdigest()
        assert await _wait(lambda: w1.conn.connected and w2.conn.connected)                  # nobody was disconnected for it
        assert await _wait(lambda: not sync._transfers)                                      # and nothing is left half-done
    finally:
        await admin.close()
        await w1.stop()
        await w2.stop()


async def test_a_flow_made_over_files_already_there_sends_them(engine, org, tmp_path: Path):
    src, dst = tmp_path / "out", tmp_path / "in"
    (src / "old").mkdir(parents=True)
    dst.mkdir()
    (src / "a.txt").write_text("a", encoding="utf-8")
    (src / "old" / "b.txt").write_text("b", encoding="utf-8")
    w1, w2, admin = await _start(engine, tmp_path, "cid-w1", [str(src)]), await _start(engine, tmp_path, "cid-w2", [str(dst)]), await _admin(engine)
    try:
        await admin.call("flow.create", _flow(org, src, dst))
        assert await _wait(lambda: (dst / "a.txt").exists() and (dst / "old" / "b.txt").exists(), timeout=15)
        # asking again sends nothing twice: both are what the destination was last given
        sync.catch_up_later(engine, await engine.db.pool.fetchval("SELECT max(id) FROM flows"))
        await asyncio.sleep(2)
        rows = await engine.db.pool.fetch("SELECT 1 FROM flow_sync_log WHERE written_by = 'flow_sync'")
        assert len(rows) == 2
    finally:
        await admin.close()
        await w1.stop()
        await w2.stop()


async def test_resuming_a_flow_sends_what_was_missed_while_it_was_paused(engine, org, tmp_path: Path):
    src, dst = tmp_path / "out", tmp_path / "in"
    src.mkdir()
    dst.mkdir()
    w1, w2, admin = await _start(engine, tmp_path, "cid-w1", [str(src)]), await _start(engine, tmp_path, "cid-w2", [str(dst)]), await _admin(engine)
    try:
        fid = (await admin.call("flow.create", _flow(org, src, dst)))["flow"]["id"]
        await admin.call("flow.pause", {"flow_id": fid})
        (src / "while-paused.txt").write_text("missed", encoding="utf-8")
        await asyncio.sleep(2.5)
        assert not (dst / "while-paused.txt").exists()                                       # paused means paused
        await admin.call("flow.resume", {"flow_id": fid})
        assert await _wait(lambda: (dst / "while-paused.txt").exists(), timeout=15)
    finally:
        await admin.close()
        await w1.stop()
        await w2.stop()


async def test_a_destination_that_was_away_is_paused_as_unreachable_then_resumed_and_caught_up(engine, org, tmp_path: Path):
    src, dst = tmp_path / "out", tmp_path / "in"
    src.mkdir()
    dst.mkdir()
    w1, w2, admin = await _start(engine, tmp_path, "cid-w1", [str(src)]), await _start(engine, tmp_path, "cid-w2", [str(dst)]), await _admin(engine)
    try:
        fid = (await admin.call("flow.create", _flow(org, src, dst)))["flow"]["id"]
        await asyncio.sleep(1.0)
        await w2.stop()                                                                      # the destination goes away
        assert await _wait(lambda: org["w2_pc"] not in engine.online_pc_ids())
        (src / "while-away.txt").write_text("sent while the destination was away", encoding="utf-8")

        async def paused():
            f = await engine.db.flows.get(fid)
            return f["destinations"][0]["paused_reason"] == "destination:unreachable"
        assert await _wait(paused, timeout=15)                                               # said, not forgotten
        (tmp_path / "again").mkdir()
        w2 = await _start(engine, tmp_path / "again", "cid-w2", [str(dst)])                  # and it returns
        assert await _wait(lambda: (dst / "while-away.txt").exists(), timeout=20)
        f = await engine.db.flows.get(fid)
        assert f["destinations"][0]["paused_reason"] is None                                 # resumed by itself
    finally:
        await admin.close()
        await w1.stop()
        await w2.stop()


async def test_a_transfer_nobody_finished_is_failed_not_kept_forever(engine, org, tmp_path: Path):
    src, dst = tmp_path / "out", tmp_path / "in"
    src.mkdir()
    dst.mkdir()
    admin = await _admin(engine)
    try:
        fid = (await admin.call("flow.create", _flow(org, src, dst)))["flow"]["id"]
        flow = await engine.db.flows.get(fid)
        stale = sync.Transfer(id="stale", flow_id=fid, source_pc_id=org["w1_pc"], source_path="x", relative_path="x", hash=None,
                              pending_destinations={flow["destinations"][0]["id"]}, created=time.monotonic() - sync.TRANSFER_SECONDS - 1)
        sync._transfers["stale"] = stale
        await sync.expire_transfers(engine)
        assert "stale" not in sync._transfers
        f = await engine.db.flows.get(fid)
        assert f["destinations"][0]["paused_reason"] == "source:unreadable"                  # the source never answered
    finally:
        await admin.close()


async def test_a_flow_never_overwrites_a_file_it_did_not_write(engine, org, tmp_path: Path):
    """A destination already holding a different file of the same name keeps it, beside the new one; the flow's own earlier write is replaced cleanly."""
    src, dst = tmp_path / "out", tmp_path / "in"
    src.mkdir()
    dst.mkdir()
    (src / "report.txt").write_text("from the source", encoding="utf-8")
    (dst / "report.txt").write_text("a person's own report", encoding="utf-8")                # not the flow's
    w1, w2, admin = await _start(engine, tmp_path, "cid-w1", [str(src)]), await _start(engine, tmp_path, "cid-w2", [str(dst)]), await _admin(engine)
    try:
        await admin.call("flow.create", _flow(org, src, dst, confirm_collisions=True))
        assert await _wait(lambda: (dst / "report.txt").exists() and (dst / "report.txt").read_text(encoding="utf-8") == "from the source", timeout=15)
        kept = dst / "report-modified.txt"
        assert kept.exists() and kept.read_text(encoding="utf-8") == "a person's own report"           # nothing of theirs was lost
        audit = await engine.db.audit.recent(action_prefix="flow.conflict")
        assert audit and "did not write" in str(audit[0]["detail"])                                  # and it was said
        # the flow's own earlier write, untouched, is replaced without fuss
        (src / "report.txt").write_text("the source moves on", encoding="utf-8")
        assert await _wait(lambda: (dst / "report.txt").read_text(encoding="utf-8") == "the source moves on", timeout=15)
        assert sorted(p.name for p in dst.iterdir()) == ["report-modified.txt", "report.txt"]       # no second copy was made
    finally:
        await admin.close()
        await w1.stop()
        await w2.stop()


async def test_a_deleted_source_file_leaves_the_destination_copy_and_comes_back_without_a_collision(engine, org, tmp_path: Path):
    src, dst = tmp_path / "out", tmp_path / "in"
    src.mkdir()
    dst.mkdir()
    w1, w2, admin = await _start(engine, tmp_path, "cid-w1", [str(src)]), await _start(engine, tmp_path, "cid-w2", [str(dst)]), await _admin(engine)
    try:
        await admin.call("flow.create", _flow(org, src, dst))
        (src / "a.txt").write_text("version one", encoding="utf-8")
        assert await _wait(lambda: (dst / "a.txt").exists(), timeout=15)
        (src / "a.txt").unlink()
        await asyncio.sleep(3)
        assert (dst / "a.txt").read_text(encoding="utf-8") == "version one"                        # the destination keeps its copy
        (src / "a.txt").write_text("version one", encoding="utf-8")                                # the same file comes back
        await asyncio.sleep(4)
        assert sorted(p.name for p in dst.iterdir()) == ["a.txt"]                                  # no collision, no duplicate
        (src / "a.txt").unlink()
        await asyncio.sleep(2)
        (src / "a.txt").write_text("version two", encoding="utf-8")                                # a different one comes back
        assert await _wait(lambda: (dst / "a.txt").read_text(encoding="utf-8") == "version two", timeout=15)
        assert sorted(p.name for p in dst.iterdir()) == ["a.txt"]                                  # untouched since the flow wrote it: replaced cleanly
    finally:
        await admin.close()
        await w1.stop()
        await w2.stop()
