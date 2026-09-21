"""Worker Client against a DB-backed Engine (skipped without FALCON_TEST_DATABASE_URL).

Real subprocesses, real temp directories: the Script Execution Model (streamed output,
timeout vs failure vs manual termination), Flow relay through the Engine to a second PC's
directory with stages, the polling watcher feeding the Global File Index, session blocking,
metrics and program signals, update attempts.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from common.connection import EngineConnection
from tests.conftest import requires_db
from worker_client.config import WorkerConfig
from worker_client.service import WorkerService
from worker_client.ui import UIContext, run_line

pytestmark = requires_db


def _cfg(engine, tmp_path: Path, client_id: str, roots: list[str]) -> WorkerConfig:
    return WorkerConfig(engine_host="127.0.0.1", engine_port=engine.port, client_id=client_id, tls=False,
                        watch_roots=roots, poll_seconds=0.3, metrics_seconds=0.5, idle_sweep_after_seconds=999999,
                        path=tmp_path / f"{client_id}.json")


async def _start(engine, tmp_path: Path, client_id: str, roots: list[str]) -> WorkerService:
    svc = WorkerService(_cfg(engine, tmp_path, client_id, roots), native_watch=False)
    svc.executor.log_dir = tmp_path / f"exec-{client_id}"
    svc.executor.log_dir.mkdir()
    await svc.start()
    return svc


async def _admin(engine) -> EngineConnection:
    a = EngineConnection("127.0.0.1", engine.port, client_id="cid-a1", tls=False)
    await a.connect()
    return a


async def _wait(cond, timeout: float = 5.0, step: float = 0.1):
    for _ in range(int(timeout / step)):
        if await cond() if asyncio.iscoroutinefunction(cond) else cond():
            return True
        await asyncio.sleep(step)
    return False


async def test_service_connects_claims_native_and_reports_metrics(engine, org, tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    svc = await _start(engine, tmp_path, "cid-w1", [str(docs)])
    try:
        assert svc.identity.pc_id == org["w1_pc"] and svc.native_session_id is not None
        assert svc.watcher.mode == "polling"
        from engine.control import events as ev

        assert await _wait(lambda: org["w1_pc"] in ev._metrics)
        ctx = UIContext(svc)
        st = await run_line(ctx, "status")
        assert "connected     yes" in st.replace("  ", " ") or "yes" in st
        assert "polling" in st
    finally:
        await svc.stop()


async def test_watcher_feeds_the_index_and_task_expectations(engine, org, tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    svc = await _start(engine, tmp_path, "cid-w1", [str(docs)])
    admin = await _admin(engine)
    try:
        # A Create-intent task for a file that does not exist yet.
        res = await admin.call("task.create", {"assignee_account_id": org["w1"], "description": "write notes.txt",
                                               "verification_mode": "stack",
                                               "items": [{"target_type": "file", "intent": "create", "name": "notes.txt"}]})
        task_id = res["task"]["id"]
        (docs / "notes.txt").write_text("hello", encoding="utf-8")
        assert await _wait(lambda: svc.watcher.events_reported >= 1)
        indexed = await engine.db.file_index.by_name("notes.txt")
        assert len(indexed) == 1 and indexed[0]["pc_id"] == org["w1_pc"] and indexed[0]["content_hash"]
        stack = (await admin.call("task.stack", {"task_id": task_id}))["items"]
        assert stack[0]["status"] == "passed"           # the file appeared -> create item bound + passed
        # Modify -> modify event; delete -> delete event (row kept).
        (docs / "notes.txt").write_text("hello again", encoding="utf-8")
        assert await _wait(lambda: svc.watcher.events_reported >= 2)
        (docs / "notes.txt").unlink()
        assert await _wait(lambda: svc.watcher.events_reported >= 3)
        assert len(await engine.db.file_index.by_name("notes.txt")) == 1
        # Manual sweep reports every remaining file in batches.
        for i in range(3):
            (docs / f"f{i}.txt").write_text(str(i), encoding="utf-8")
        n = await svc.watcher.sweep()
        assert n == 3 and svc.watcher.sweeps_completed == 1
    finally:
        await admin.close()
        await svc.stop()


async def test_executor_runs_custom_and_builtin_actions_with_timeout_and_terminate(engine, org, tmp_path: Path):
    svc = await _start(engine, tmp_path, "cid-w1", [])
    admin = await _admin(engine)
    try:
        # Custom python action: streamed output, success.
        custom = (await admin.call("control.action_create", {
            "kind": "custom", "name": "hello", "language": "python", "timeout_s": 20,
            "script": "import sys, time\nprint('line one'); sys.stdout.flush()\ntime.sleep(0.7)\nprint('line two')\n"}))["action"]
        ex = (await admin.call("control.action_run", {"action_id": custom["id"], "pc_id": org["w1_pc"]}))["execution_id"]
        assert await _wait(lambda: svc.executor.completed.get(ex) == "success", timeout=15)
        view = await admin.call("control.execution", {"execution_id": ex})
        assert view["execution"]["status"] == "success" and view["execution"]["exit_code"] == 0
        assert "line one" in view["output"] and any("line two" in o for o in view["output"])
        assert view["execution"]["output_log_path"].endswith(f"{ex}.log")

        # Failure: non-zero exit is `failed`.
        bad = (await admin.call("control.action_create", {
            "kind": "custom", "name": "bad", "language": "python", "timeout_s": 20, "script": "import sys\nsys.exit(3)\n"}))["action"]
        ex2 = (await admin.call("control.action_run", {"action_id": bad["id"], "pc_id": org["w1_pc"]}))["execution_id"]
        assert await _wait(lambda: svc.executor.completed.get(ex2) == "failed", timeout=15)
        assert (await admin.call("control.execution", {"execution_id": ex2}))["execution"]["status"] == "failed"

        # Timeout: a hanging script is killed and reported as `timeout`, not `failed`.
        slow = (await admin.call("control.action_create", {
            "kind": "custom", "name": "slow", "language": "python", "timeout_s": 1, "script": "import time\ntime.sleep(30)\n"}))["action"]
        ex3 = (await admin.call("control.action_run", {"action_id": slow["id"], "pc_id": org["w1_pc"]}))["execution_id"]
        assert await _wait(lambda: svc.executor.completed.get(ex3) == "timeout", timeout=15)
        e3 = (await admin.call("control.execution", {"execution_id": ex3}))["execution"]
        assert e3["status"] == "terminated" and e3["terminated_reason"] == "timeout"

        # Manual termination by id, while running.
        ex4 = (await admin.call("control.action_run", {"action_id": custom["id"], "pc_id": org["w1_pc"]}))["execution_id"]
        long_ = (await admin.call("control.action_create", {
            "kind": "custom", "name": "long", "language": "python", "timeout_s": 60, "script": "import time\ntime.sleep(60)\n"}))["action"]
        ex5 = (await admin.call("control.action_run", {"action_id": long_["id"], "pc_id": org["w1_pc"]}))["execution_id"]
        assert await _wait(lambda: ex5 in svc.executor.running, timeout=10)
        await admin.call("control.terminate", {"execution_id": ex5})
        assert await _wait(lambda: svc.executor.completed.get(ex5) == "terminated", timeout=15)
        e5 = (await admin.call("control.execution", {"execution_id": ex5}))["execution"]
        assert e5["status"] == "terminated" and e5["terminated_reason"] == "manual"
        assert await _wait(lambda: svc.executor.completed.get(ex4) == "success", timeout=15)  # unaffected

        # Built-in monitoring action runs through the same path; power actions are refused by default.
        metrics = (await admin.call("control.action_create", {"kind": "monitoring", "builtin_type": "system_metrics", "timeout_s": 20}))["action"]
        ex6 = (await admin.call("control.action_run", {"action_id": metrics["id"], "pc_id": org["w1_pc"]}))["execution_id"]
        assert await _wait(lambda: svc.executor.completed.get(ex6) == "success", timeout=15)
        assert '"cpu"' in "".join((await admin.call("control.execution", {"execution_id": ex6}))["output"])
        off = (await admin.call("control.action_create", {"kind": "control", "builtin_type": "shutdown", "timeout_s": 5}))["action"]
        ex7 = (await admin.call("control.action_run", {"action_id": off["id"], "pc_id": org["w1_pc"]}))["execution_id"]
        assert await _wait(lambda: svc.executor.completed.get(ex7) == "failed", timeout=10)
        # A script tampered with in transit is rejected on arrival.
        await svc.executor.execute({"execution_id": 999, "action": {"kind": "custom", "language": "python",
                                                                     "script": "import requests"}, "timeout_s": 5})
        assert svc.executor.completed[999] == "failed"
    finally:
        await admin.close()
        await svc.stop()


async def test_flow_relay_between_two_workers_with_stages_and_conflict(engine, org, tmp_path: Path):
    src = tmp_path / "out"
    dst = tmp_path / "in"
    src.mkdir()
    dst.mkdir()
    w1 = await _start(engine, tmp_path, "cid-w1", [str(src)])
    w2 = await _start(engine, tmp_path, "cid-w2", [str(dst)])
    admin = await _admin(engine)
    try:
        flow = (await admin.call("flow.create", {
            "source_pc_id": org["w1_pc"], "source_path": str(src),
            "stages": [{"stage_type": "categorization", "config": {"by": "extension"}}],
            "destinations": [{"destination_pc_id": org["w2_pc"], "destination_path": str(dst), "parent_index": 0}]}))["flow"]
        (src / "report.txt").write_text("quarterly numbers", encoding="utf-8")
        # w1's watcher reports -> Engine flow.read -> w1 flow.content -> Engine flow.apply -> w2 writes.
        landed = dst / "txt" / "report.txt"
        assert await _wait(lambda: landed.exists(), timeout=10)
        assert landed.read_text(encoding="utf-8") == "quarterly numbers"

        async def synced():
            return bool(await engine.db.flows.history(flow["id"]))
        assert await _wait(synced)
        rows = await engine.db.flows.history(flow["id"])
        assert rows[0]["written_by"] == "flow_sync"
        # w2's own watcher sees the write it made; the Engine attributes it to the flow (no conflict).
        await asyncio.sleep(1.0)
        rows = await engine.db.flows.history(flow["id"])
        assert all(h["written_by"] == "flow_sync" for h in rows)
        # An external edit at the destination is preserved as -modified and re-synced.
        landed.write_text("edited locally", encoding="utf-8")
        modified = dst / "txt" / "report-modified.txt"
        assert await _wait(lambda: modified.exists() and landed.exists()
                           and landed.read_text(encoding="utf-8") == "quarterly numbers", timeout=10)
        assert modified.read_text(encoding="utf-8") == "edited locally"
        rows = await engine.db.flows.history(flow["id"])
        assert any(h["written_by"] == "external" and h["conflict_resolved"] for h in rows)
        # An unsupported transformation fails only that destination with the predefined suggestion.
        bad = (await admin.call("flow.create", {
            "source_pc_id": org["w1_pc"], "source_path": str(src / "sub"),
            "stages": [{"stage_type": "transformation", "config": {"to": "pdf"}}],
            "destinations": [{"destination_pc_id": org["w2_pc"], "destination_path": str(dst / "pdfs"), "parent_index": 0}]}))["flow"]
        (src / "sub").mkdir()
        (src / "sub" / "memo.txt").write_text("x", encoding="utf-8")

        async def paused():
            f = await engine.db.flows.get(bad["id"])
            return bool(f and f["destinations"][0]["paused_reason"] == "transformation:unsupported_format")
        assert await _wait(paused, timeout=10)
    finally:
        await admin.close()
        await w1.stop()
        await w2.stop()


async def test_session_blocking_surface_and_worker_ui(engine, org, tmp_path: Path):
    svc = await _start(engine, tmp_path, "cid-w1", [])
    admin = await _admin(engine)
    try:
        seen: list[str] = []

        async def notify(type_, payload):
            seen.append(type_)

        svc.on_notify(notify)
        res = await admin.call("hierarchy.traverse", {"pc_id": org["w1_pc"], "force": True})
        assert await _wait(lambda: svc.lockout.is_blocked)
        assert svc.lockout.blocked_by["occupant_account_id"] == org["a1"]
        ctx = UIContext(svc)
        assert "TRAVERSAL IN PROGRESS" in await run_line(ctx, "status")
        await admin.call("hierarchy.end_session", {"session_id": res["session"]["session_id"]})
        assert await _wait(lambda: not svc.lockout.is_blocked and svc.native_session_id is not None)
        assert "session.blocked" in seen and "session.released" in seen
        # The narrow UI: tasks, ping the Admin, respond, message.
        await admin.call("task.create", {"assignee_account_id": org["w1"], "description": "tidy up",
                                         "verification_mode": "none", "confirm_none": True})
        assert "tidy up" in await run_line(ctx, "tasks")
        out = await run_line(ctx, f"ping {org['a1']}")
        assert out.startswith("ping ")
        assert "unknown" in (out := await run_line(ctx, "task verify 1 complete")) or "usage" in out  # no verify in the worker UI
        p = await admin.call("assistance.ping", {"to_account_id": org["w1"]})
        assert "1 unaddressed" in await run_line(ctx, "pings")
        assert (await run_line(ctx, f"respond {p['ping_id']}")).startswith("channel ")
        assert "waiting" in await run_line(ctx, "channel")
    finally:
        await admin.close()
        await svc.stop()


async def test_program_signals_and_update_attempt(engine, org, tmp_path: Path):
    svc = await _start(engine, tmp_path, "cid-w1", [])
    admin = await _admin(engine)
    su = EngineConnection("127.0.0.1", engine.port, client_id="cid-su", tls=False)
    await su.connect()
    try:
        # A program item for the interpreter running these tests: present + running.
        import sys

        exe = Path(sys.executable).name
        res = await admin.call("task.create", {"assignee_account_id": org["w1"], "description": "use python",
                                               "verification_mode": "stack",
                                               "items": [{"target_type": "program", "intent": "installed_available", "name": exe}]})
        await svc._refresh_tasks()
        assert svc.signals.watch_programs
        assert await svc.signals.report_programs() == 1
        stack = (await admin.call("task.stack", {"task_id": res["task"]["id"]}))["items"]
        assert stack[0]["status"] == "passed"
        # Update: approved version pushed to the PC; with no update command the attempt fails honestly.
        await su.call("updates.approve", {"version": "9.9.9"})
        await admin.call("updates.rollout_department")
        assert await _wait(lambda: svc.updater.pending == "9.9.9")
        assert await svc.updater.attempt() is False
        st = await engine.db.updates.status_for_pc(org["w1_pc"])
        assert st["attempt_failure_count"] >= 1 and st["current_version_id"] is None   # never confirmed
        assert any(b["id"] == org["w1_pc"] for b in await engine.db.updates.pcs_behind(
            (await engine.db.updates.current_version())["id"]))
    finally:
        await su.close()
        await admin.close()
        await svc.stop()


def test_worker_config_roundtrip(tmp_path: Path):
    cfg = WorkerConfig(engine_host="h", engine_port=1, client_id="c", watch_roots=["/x"], path=tmp_path / "w.json")
    cfg.save()
    back = WorkerConfig.load(tmp_path / "w.json")
    assert back.engine_address == "h:1" and back.watch_roots == ["/x"] and back.client_id == "c"
