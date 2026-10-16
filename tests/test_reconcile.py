"""The index reconciles by itself: whatever changed while the Engine was not listening is found and told, so nothing is lost to a gap.

A Worker keeps what the Engine was last told (worker_client/snapshot.py) and, on connect and now and then, tells the difference: files that appeared,
changed or went. The Engine treats each exactly as if it had happened live, so Flow, Restricted and Task react as they would have.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from tests.conftest import requires_db
from tests.test_worker_client import _admin, _cfg
from worker_client.service import WorkerService
from worker_client.snapshot import Snapshot


def test_the_snapshot_remembers_what_the_engine_was_told_and_what_has_gone(tmp_path: Path):
    snap = Snapshot(tmp_path / "state.db")
    assert snap.count() == 0
    snap.upsert([("C:\\Docs\\A.txt", 1, 10, "h1"), ("C:\\Docs\\sub\\b.txt", 2, 20, "h2"), ("C:\\Other\\c.txt", 3, 30, "h3")])
    assert snap.known("c:/docs/a.TXT") == (1, 10, "h1")                                    # one spelling per file
    run = snap.next_run()
    snap.mark_seen(["C:\\Docs\\A.txt"], run)
    assert sorted(snap.unseen_under("C:\\Docs", run)) == ["C:\\Docs\\sub\\b.txt"]          # what a walk did not meet is gone
    snap.move_under("C:\\Docs\\sub", "C:\\Docs\\renamed")
    assert snap.known("C:/Docs/renamed/b.txt") == (2, 20, "h2") and snap.known("C:/Docs/sub/b.txt") is None
    snap.remove_under("C:\\Docs")
    assert snap.count() == 1 and snap.known("C:/Other/c.txt") is not None
    snap.close()
    again = Snapshot(tmp_path / "state.db")                                                # it survives a restart
    assert again.count() == 1
    again.close()


async def _until(cond, timeout: float = 10.0) -> bool:
    """Wait for a condition that may be a coroutine."""
    for _ in range(int(timeout / 0.1)):
        res = cond()
        if asyncio.iscoroutine(res):
            res = await res
        if res:
            return True
        await asyncio.sleep(0.1)
    return False


async def _worker(engine, tmp_path: Path, client_id: str, roots: list[str]) -> WorkerService:
    svc = WorkerService(_cfg(engine, tmp_path, client_id, roots), native_watch=False)
    svc.executor.log_dir = tmp_path / f"exec-{client_id}"
    svc.executor.log_dir.mkdir(exist_ok=True)
    await svc.start()
    return svc


async def _indexed(engine, pc_id: int, path: Path):
    return await engine.db.file_index.by_path(pc_id, str(path), present_only=True)


@requires_db
async def test_changes_made_while_the_worker_was_away_are_told_when_it_returns(engine, org, tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "a.txt").write_text("a", encoding="utf-8")
    (docs / "b.txt").write_text("b one", encoding="utf-8")
    svc = await _worker(engine, tmp_path, "cid-w1", [str(docs)])
    try:
        for name in ("a.txt", "b.txt"):                                                    # the first look: a baseline of what is there
            assert await _until(lambda name=name: _present(engine, org["w1_pc"], docs / name), timeout=15)
        before = (await engine.db.file_index.by_path(org["w1_pc"], str(docs / "b.txt")))["content_hash"]
    finally:
        await svc.stop()
    # the machine is off (nothing is listening): a file is deleted, one edited, one made
    (docs / "a.txt").unlink()
    (docs / "b.txt").write_text("b two, longer", encoding="utf-8")
    (docs / "c.txt").write_text("c", encoding="utf-8")
    svc = await _worker(engine, tmp_path, "cid-w1", [str(docs)])
    try:
        assert await _until(lambda: _present(engine, org["w1_pc"], docs / "c.txt"), timeout=15)            # what appeared
        assert await _until(lambda: _absent(engine, org["w1_pc"], docs / "a.txt"), timeout=15)             # what went
        assert (await engine.db.file_index.by_path(org["w1_pc"], str(docs / "b.txt")))["content_hash"] != before      # what changed
        audit = await engine.db.audit.recent(action_prefix="index.caught_up")
        assert audit, "the Engine should record that it was caught up"
        assert await _until(lambda: not svc.watcher._reconciling)                          # it has finished telling
        n = len(await engine.db.audit.recent(action_prefix="index.caught_up"))
        again = await svc.watcher.reconcile()                                              # looking again finds nothing new to say
        assert again == {"changes": 0} and len(await engine.db.audit.recent(action_prefix="index.caught_up")) == n
    finally:
        await svc.stop()


async def _present(engine, pc_id: int, path: Path) -> bool:
    return await _indexed(engine, pc_id, path) is not None


async def _absent(engine, pc_id: int, path: Path) -> bool:
    return await _indexed(engine, pc_id, path) is None


@requires_db
async def test_a_report_that_failed_is_found_again_and_told(engine, org, tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    svc = await _worker(engine, tmp_path, "cid-w1", [str(docs)])
    try:
        await asyncio.sleep(1.0)
        real = svc.watcher.report

        async def failing(type_, payload):
            raise ConnectionError("the Engine was not reachable")

        svc.watcher.report = failing                                                       # the network is down for a moment
        (docs / "lost.txt").write_text("this event never arrived", encoding="utf-8")
        await asyncio.sleep(2.0)
        assert not await _present(engine, org["w1_pc"], docs / "lost.txt")
        svc.watcher.report = real                                                          # and comes back
        assert await _until(lambda: not svc.watcher._reconciling)
        found = await svc.watcher.reconcile()
        assert found.get("changes", 0) >= 1
        assert await _present(engine, org["w1_pc"], docs / "lost.txt")
    finally:
        await svc.stop()


@requires_db
async def test_a_flow_still_delivers_a_file_made_while_its_source_was_away(engine, org, tmp_path: Path):
    src, dst = tmp_path / "out", tmp_path / "in"
    src.mkdir()
    dst.mkdir()
    w2 = await _worker(engine, tmp_path, "cid-w2", [str(dst)])
    w1 = await _worker(engine, tmp_path, "cid-w1", [str(src)])
    admin = await _admin(engine)
    try:
        await admin.call("flow.create", {"source_pc_id": org["w1_pc"], "source_path": str(src), "stages": [],
                                         "destinations": [{"destination_pc_id": org["w2_pc"], "destination_path": str(dst)}]})
        await asyncio.sleep(1.5)
        await w1.stop()                                                                    # the source machine is off
        (src / "while-off.txt").write_text("made while the source was away", encoding="utf-8")
        w1 = await _worker(engine, tmp_path, "cid-w1", [str(src)])                         # it comes back
        assert await _until(lambda: (dst / "while-off.txt").exists(), timeout=25)           # and the destination has it, as if nothing happened
        assert (dst / "while-off.txt").read_text(encoding="utf-8") == "made while the source was away"
    finally:
        await admin.close()
        await w1.stop()
        await w2.stop()


# --- the Engine looks again by itself, now and then ---------------------------------------------------------------

@requires_db
async def test_the_engine_finds_a_copy_of_marked_content_whose_event_it_never_heard(engine, org, connect):
    from engine.console import marks

    a1 = await connect("cid-a1")
    await a1.ok("index.event", {"event": {"op": "create", "path": "C:/Finance/payroll.csv", "hash": "PAY"}})
    await a1.ok("marks.create", {"paths": ["C:/Finance/payroll.csv"], "keep": "path"})
    # a copy lands in the index with no event for the marks to hear (the Engine was down, or the event was lost)
    await engine.db.file_index.upsert(org["w1_pc"], "C:/Users/p/payroll-copy.csv", "payroll-copy.csv", "PAY", None, None, "event")
    assert [i for i in (await a1.ok("issues.list", {"type": "file"}))["issues"] if i["state"] != "resolved"] == []
    assert await marks.heal(engine) == 1                                                  # found on the next look
    assert await marks.heal(engine) == 0                                                  # and not again
    assert len([i for i in (await a1.ok("issues.list", {"type": "file"}))["issues"] if i["state"] != "resolved"]) == 1


@requires_db
async def test_the_engine_gives_a_task_the_file_it_asked_for_when_the_event_was_missed(engine, org, connect):
    from engine.task import expectation

    a1 = await connect("cid-a1")
    made = await a1.ok("task.create", {"assignee_account_id": org["w1"], "description": "write report.docx", "verification_mode": "stack",
                                       "items": [{"target_type": "file", "intent": "create", "name": "report.docx", "path": "C:/new"}]})
    tid = made["task"]["id"]
    await engine.db.file_index.upsert(org["w1_pc"], "C:/new/report.docx", "report.docx", "R", None, None, "event")      # no event reached the Engine
    assert (await a1.ok("task.stack", {"task_id": tid}))["items"][0]["status"] != "passed"
    assert await expectation.heal(engine) == 1
    assert (await a1.ok("task.stack", {"task_id": tid}))["items"][0]["status"] == "passed"
    assert await expectation.heal(engine) == 0


@requires_db
async def test_the_engine_makes_good_a_flow_event_it_missed(engine, org, tmp_path: Path, monkeypatch):
    from engine.flow import sync

    src, dst = tmp_path / "out", tmp_path / "in"
    src.mkdir()
    dst.mkdir()
    w1, w2, admin = await _worker(engine, tmp_path, "cid-w1", [str(src)]), await _worker(engine, tmp_path, "cid-w2", [str(dst)]), await _admin(engine)
    try:
        await admin.call("flow.create", {"source_pc_id": org["w1_pc"], "source_path": str(src), "stages": [],
                                         "destinations": [{"destination_pc_id": org["w2_pc"], "destination_path": str(dst)}]})
        await asyncio.sleep(1.5)

        async def deaf(*_a, **_k):
            return None

        monkeypatch.setattr(sync, "_settle_then_propagate", deaf)                          # the Engine misses the source's event
        (src / "missed.txt").write_text("the event never reached the flow", encoding="utf-8")
        await asyncio.sleep(2.5)
        assert not (dst / "missed.txt").exists()
        monkeypatch.undo()
        await sync.heal(engine)                                                            # the next look
        assert await _until(lambda: (dst / "missed.txt").exists(), timeout=20)
    finally:
        await admin.close()
        await w1.stop()
        await w2.stop()
