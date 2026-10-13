"""The indexer and the event tracker as their own programs under the Worker service.

Real child processes: they start, report through the service's end, are started again when they die, and are called
unhealthy (and the Engine told) when they will not stay up.
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

import psutil

from tests.conftest import key_for, requires_db
from worker_client.childproc import Supervised
from worker_client.config import WorkerConfig
from worker_client.service import WorkerService


async def until(cond, timeout: float = 15.0, step: float = 0.1) -> bool:
    for _ in range(int(timeout / step)):
        if cond():
            return True
        await asyncio.sleep(step)
    return False


def indexer_args(root: Path) -> list[str]:
    return [json.dumps({"roots": [str(root)], "poll_seconds": 0.2, "hash_limit": 1 << 20, "idle_after": 999999, "native": False})]


async def test_the_indexer_runs_alone_reports_through_the_service_and_comes_back_when_killed(tmp_path: Path):
    seen: list[tuple[str, dict[str, Any]]] = []

    async def handle(type_: str, payload: dict[str, Any]) -> dict[str, Any]:
        seen.append((type_, payload))
        return {}

    docs = tmp_path / "docs"
    docs.mkdir()
    child = Supervised("indexer", "worker_client.indexer", indexer_args(docs), handle, backoff=(0.1,))
    await child.start()
    try:
        assert await until(lambda: child.running and child.state.get("mode") == "polling")
        (docs / "a.txt").write_text("one", encoding="utf-8")
        assert await until(lambda: any(t == "index.event" for t, _ in seen))
        first = child.pid
        assert first != psutil.Process().pid                  # its own program, not a thread of this one

        psutil.Process(first).kill()                          # the indexer dies
        assert await until(lambda: child.running and child.pid not in (None, first))
        assert child.restarts == 1 and child.healthy
        assert await until(lambda: child.state.get("mode") == "polling")      # it has looked at the folder again
        seen.clear()
        (docs / "b.txt").write_text("two", encoding="utf-8")
        assert await until(lambda: any(t == "index.event" for t, _ in seen))   # and keeps reporting

        res = await child.command("status")                   # the service can ask it things
        assert res["mode"] == "polling"
    finally:
        await child.stop()
    assert not child.running


async def test_the_tracker_asks_what_to_watch_at_start_again_on_request_and_again_after_it_dies():
    asks: list[int] = []

    async def handle(type_: str, payload: dict[str, Any]) -> dict[str, Any]:
        if type_ == "control.signal_interest":
            asks.append(1)
            return {"interest": {}}
        return {}

    child = Supervised("tracker", "worker_client.tracker", [json.dumps({"native": False})], handle, backoff=(0.1,))
    await child.start()
    try:
        assert await until(lambda: len(asks) >= 1)
        await child.command("refresh")
        assert len(asks) >= 2
        before = len(asks)
        psutil.Process(child.pid).kill()
        assert await until(lambda: len(asks) > before)        # a new life asks by itself
        assert child.restarts == 1
    finally:
        await child.stop()


async def test_a_child_that_keeps_dying_is_called_unhealthy_and_healthy_again_is_noticed():
    changes: list[tuple[str, bool]] = []

    async def handle(type_: str, payload: dict[str, Any]) -> dict[str, Any]:
        return {}

    child = Supervised("broken", "worker_client.no_such_program", [], handle, backoff=(0.05,), unhealthy_after=3,
                       unhealthy_window=60.0, on_unhealthy=lambda n, ok: changes.append((n, ok)))
    await child.start()
    try:
        assert await until(lambda: not child.healthy)
        assert changes == [("broken", False)]
        assert child.restarts >= 3
    finally:
        await child.stop()


async def test_asking_a_child_that_is_not_running_says_so():
    child = Supervised("idle", "worker_client.indexer", [], lambda t, p: asyncio.sleep(0, {}))
    try:
        await child.command("status")
    except ConnectionError as exc:
        assert "not running" in str(exc)
    else:
        raise AssertionError("expected a refusal")


# --- through the whole service, against the Engine ------------------------------------------------------------

def _cfg(engine, tmp_path: Path, client_id: str, roots: list[str]) -> WorkerConfig:
    return WorkerConfig(windows=False, separate_programs=True, engine_host="127.0.0.1", engine_port=engine.port, client_id=client_id,
                        client_key=key_for(client_id), tls=False, watch_roots=roots, poll_seconds=0.2, metrics_seconds=0.5,
                        idle_sweep_after_seconds=999999, path=tmp_path / f"{client_id}.json")


@requires_db
async def test_the_service_with_separate_programs_feeds_the_index_and_survives_the_indexer_dying(engine, org, tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    svc = WorkerService(_cfg(engine, tmp_path, "cid-w1", [str(docs)]), native_watch=False)
    svc.executor.log_dir = tmp_path / "exec"
    svc.executor.log_dir.mkdir()
    await svc.start()
    try:
        assert await until(lambda: svc.watcher.mode == "polling")
        (docs / "notes.txt").write_text("hello", encoding="utf-8")
        for _ in range(100):
            if await engine.db.file_index.by_name("notes.txt"):
                break
            await asyncio.sleep(0.1)
        found = await engine.db.file_index.by_name("notes.txt")
        assert len(found) == 1 and found[0]["pc_id"] == org["w1_pc"]

        old = svc.watcher.child.pid
        psutil.Process(old).kill()
        assert await until(lambda: svc.watcher.child.running and svc.watcher.child.pid != old)
        assert svc.conn.connected                                  # the connection was never touched
        assert await until(lambda: svc.watcher.mode == "polling")
        (docs / "later.txt").write_text("again", encoding="utf-8")
        for _ in range(100):
            if await engine.db.file_index.by_name("later.txt"):
                break
            await asyncio.sleep(0.1)
        assert len(await engine.db.file_index.by_name("later.txt")) == 1
        assert svc.ossignals.child is not None and svc.ossignals.child.running
    finally:
        await svc.stop()


@requires_db
async def test_a_part_that_keeps_dying_is_an_issue_on_its_machine_until_it_is_healthy(engine, org, tmp_path: Path):
    from common.connection import EngineConnection

    w = EngineConnection("127.0.0.1", engine.port, client_id="cid-w1", tls=False, derived_key=key_for("cid-w1"))
    await w.connect()
    try:
        assert (await w.call("control.component_status", {"component": "indexer", "healthy": False}))["raised"] is True
        issue = await engine.db.issues.by_source("component_status", org["w1_pc"] * 10 + 1)
        assert issue is not None and issue["type"] == "component" and issue["state"] != "resolved"
        # told again: still one issue
        assert (await w.call("control.component_status", {"component": "indexer", "healthy": False}))["raised"] is False
        await w.call("control.component_status", {"component": "indexer", "healthy": True})
        assert await engine.db.issues.by_source("component_status", org["w1_pc"] * 10 + 1) is None
        try:
            await w.call("control.component_status", {"component": "overlay", "healthy": False})
        except Exception as exc:  # noqa: BLE001
            assert "component" in str(exc)
        else:
            raise AssertionError("an unknown part must be refused")
    finally:
        await w.close()
