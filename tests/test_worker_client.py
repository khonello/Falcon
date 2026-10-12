"""Worker Client against a DB-backed Engine (skipped without FALCON_TEST_DATABASE_URL).

Real subprocesses, real temp directories: the Script Execution Model (streamed output,
timeout vs failure vs manual termination), Flow relay through the Engine to a second PC's
directory with stages, the polling watcher feeding the Global File Index, session blocking,
metrics and program signals, update attempts.
"""

from __future__ import annotations

import asyncio
import base64
import inspect
from pathlib import Path

import pytest

from common.connection import EngineConnection
from tests.conftest import key_for, requires_db
from worker_client.config import WorkerConfig
from worker_client.service import WorkerService
from worker_client.ui import UIContext, run_line

pytestmark = requires_db


def _cfg(engine, tmp_path: Path, client_id: str, roots: list[str]) -> WorkerConfig:
    return WorkerConfig(windows=False, engine_host="127.0.0.1", engine_port=engine.port, client_id=client_id, client_key=key_for(client_id), tls=False,
                        watch_roots=roots, poll_seconds=0.3, metrics_seconds=0.5, idle_sweep_after_seconds=999999,
                        path=tmp_path / f"{client_id}.json")


async def _start(engine, tmp_path: Path, client_id: str, roots: list[str]) -> WorkerService:
    svc = WorkerService(_cfg(engine, tmp_path, client_id, roots), native_watch=False)
    svc.executor.log_dir = tmp_path / f"exec-{client_id}"
    svc.executor.log_dir.mkdir()
    await svc.start()
    return svc


async def _admin(engine) -> EngineConnection:
    a = EngineConnection("127.0.0.1", engine.port, client_id="cid-a1", tls=False, derived_key=key_for("cid-a1"))
    await a.connect()
    return a


async def _wait(cond, timeout: float = 5.0, step: float = 0.1):
    for _ in range(int(timeout / step)):
        if await cond() if inspect.iscoroutinefunction(cond) else cond():
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
        # the row is kept (no hard deletes) but marked as gone: it is no longer a place the file is
        assert await engine.db.file_index.by_name("notes.txt") == []
        kept = await engine.db.pool.fetchrow("SELECT gone_at FROM file_index WHERE filename = 'notes.txt'")
        assert kept is not None and kept["gone_at"] is not None
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
        view6 = await admin.call("control.execution", {"execution_id": ex6})
        assert set(view6["result"]) == {"cpu", "memory", "disk"} and view6["output"] == []
        assert view6["execution"]["summary"].startswith("processor ")

        # What a Custom Action returned: its summary, rows and a picture, kept with the run.
        shows = (await admin.call("control.action_create", {
            "kind": "custom", "name": "shows", "language": "python", "timeout_s": 20,
            "script": "import os, tempfile\np = os.path.join(tempfile.gettempdir(), 'falcon-test-pic.png')\n"
                      "open(p, 'wb').write(b'not really a png')\nprint('working')\n"
                      "print('FALCON:summary 2 rows')\nprint('FALCON:result [{\"a\": 1}, {\"a\": 2}]')\n"
                      "print('FALCON:image ' + p)\n"}))["action"]
        ex8 = (await admin.call("control.action_run", {"action_id": shows["id"], "pc_id": org["w1_pc"]}))["execution_id"]
        assert await _wait(lambda: svc.executor.completed.get(ex8) == "success", timeout=15)
        view8 = await admin.call("control.execution", {"execution_id": ex8})
        assert view8["output"] == ["working"] and view8["result"] == [{"a": 1}, {"a": 2}]
        assert view8["execution"]["summary"] == "2 rows" and view8["execution"]["has_image"] is True
        pic = await admin.call("control.execution_image_get", {"execution_id": ex8})
        assert base64.b64decode(pic["data"]) == b"not really a png" and pic["mime"] == "image/png"
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
    su = EngineConnection("127.0.0.1", engine.port, client_id="cid-su", tls=False, derived_key=key_for("cid-su"))
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


def test_a_task_reads_to_its_assignee_in_plain_words():
    """TK07: the assignee's window says who it is from, what, when it is due and what will show the work -- and a file
    to be made is said to be found by its name, wherever it is saved."""
    from worker_client.windows.spawn import task_spec

    spec = task_spec({"assigner_name": "R. Mensah", "description_raw": "Q3 reconciliation. Reconcile the invoices.",
                      "final_deadline_at": "2026-09-30T17:00:00+00:00", "started_at": None,
                      "items": [{"name": "suppliers-q3.xlsx", "intent": "update", "target_type": "file"},
                                {"name": "reconciliation-q3.docx", "intent": "create", "target_type": "file"},
                                {"name": "gone.docx", "removed": True}]})
    assert spec["from"] == "R. Mensah" and spec["title"] == "Q3 reconciliation" and spec["started"] is False
    assert [s["name"] for s in spec["signs"]] == ["suppliers-q3.xlsx", "reconciliation-q3.docx"]
    assert spec["signs"][1]["hint"] == "save it anywhere; it is found by name"


def test_the_windows_say_what_they_are_and_refuse_what_they_are_not(capsys):
    from worker_client.windows.__main__ import main

    assert main(["nonsense"]) == 2
    assert "usage" in capsys.readouterr().err


def test_ossignals_compare_two_looks():
    from worker_client import ossignals as o

    assert o.diff_drives({}, {"E:\\": "E:"}) == [("usb.inserted", {"device": "E:\\", "path": "E:\\"})]
    assert o.diff_drives({"E:\\": "E:"}, {})[0][0] == "usb.removed"
    assert o.diff_interfaces({"Wi-Fi": False}, {"Wi-Fi": True}) == [("network.connected", {"interface": "Wi-Fi"})]
    assert o.diff_interfaces({"Wi-Fi": True}, {}) == [("network.disconnected", {"interface": "Wi-Fi"})]
    assert o.diff_programs({1: "a.exe"}, {1: "a.exe", 2: "b.exe"}) == [("program.launched", {"process": "b.exe"})]
    assert o.diff_programs({1: "a.exe", 2: "b.exe"}, {1: "a.exe"}) == [("program.exited", {"process": "b.exe"})]
    assert o.diff_sessions({}, {"ama@console": "ama"}) == [("user.login", {"user": "ama"})]
    assert o.diff_sessions({"ama@console": "ama"}, {}) == [("user.logout", {"user": "ama"})]


async def test_the_worker_relays_only_the_signals_an_automation_waits_for(engine, org, tmp_path: Path, monkeypatch):
    """The first look is a baseline; a program that starts afterwards fires the automation that asked,
    and a type nothing waits for is never even read."""
    from worker_client import ossignals

    svc = await _start(engine, tmp_path, "cid-w1", [])
    admin = await _admin(engine)
    try:
        assert svc.ossignals.interest == {}
        note = (await admin.call("control.action_create", {"kind": "control", "builtin_type": "notify",
                                                           "timeout_s": 5, "params": {"message": "started"}}))["action"]
        ev = (await admin.call("control.event_create", {"type": "program.launched", "pc_ids": [org["w1_pc"]],
                                                        "match": {"process": "falcon-test-probe.exe"},
                                                        "action_ids": [note["id"]]}))["event"]
        assert await _wait(lambda: "program.launched" in svc.ossignals.interest, timeout=5)
        assert "usb.inserted" not in svc.ossignals.interest
        await svc.ossignals.tick()                               # the baseline
        assert "drives" not in svc.ossignals._base               # nothing waits for drives: not read
        looks = iter([{1: "explorer.exe"}, {1: "explorer.exe", 2: "falcon-test-probe.exe"},
                      {1: "explorer.exe", 2: "falcon-test-probe.exe", 3: "other.exe"}])
        monkeypatch.setattr(ossignals, "programs", lambda: next(looks))
        svc.ossignals._base.pop("programs", None)
        assert await svc.ossignals.tick() == 0                    # the baseline reports nothing
        assert await svc.ossignals.tick() == 1                    # the probe starts: the match fires
        assert await svc.ossignals.tick() == 0                    # another program starts: not what was asked
        await admin.call("control.event_delete", {"event_id": ev["id"]})
        assert await _wait(lambda: svc.ossignals.interest == {}, timeout=5)
    finally:
        await admin.close()
        await svc.stop()


def test_the_screen_builtins_use_their_settings(monkeypatch, capsys):
    from worker_client import builtins as b

    # a restart or shutdown: the warning before it happens, with the message beside it
    ran = []
    monkeypatch.setattr(b.subprocess, "run", lambda cmd, check=False: ran.append(cmd))
    monkeypatch.setattr(b.sys, "platform", "win32")
    assert b.power("reboot", ["300", "Updates tonight"]) == 0
    assert ran[-1] == ["shutdown", "/r", "/t", "300", "/c", "Updates tonight"]
    b.power("shutdown", [])
    assert ran[-1][:4] == ["shutdown", "/s", "/t", "30"]
    monkeypatch.setattr(b.sys, "platform", "linux")
    b.power("reboot", ["90", ""])
    assert ran[-1] == ["shutdown", "-r", "+2"]
    assert "FALCON:summary reboot in 90 s" in capsys.readouterr().out

    # a message with no windows installed says so instead of pretending it was shown
    monkeypatch.setattr(b, "available", lambda: False)
    b.notify(["Back up your files", "30"])
    out = capsys.readouterr().out
    assert "NOTIFY: Back up your files" in out and "not shown" in out

    # a message that stays up for stay_s seconds is taken down after it; one the person closes is not
    class Fake:
        def __init__(self, ends):
            self.ends, self.killed = ends, False
        def wait(self, timeout=None):
            if not self.ends:
                raise b.subprocess.TimeoutExpired("w", timeout)
        def terminate(self):
            self.killed = True
        def poll(self):
            return 0 if self.ends else None
        def kill(self):
            self.killed = True

    monkeypatch.setattr(b, "available", lambda: True)
    shown = []
    monkeypatch.setattr(b, "_window", lambda kind, spec: shown.append((kind, spec)) or Fake(False))
    b.notify(["Meeting soon", "20"])
    assert shown[-1] == ("message", {"text": "Meeting soon", "from": ""})
    assert "taken down after 20 s" in capsys.readouterr().out
    monkeypatch.setattr(b, "_window", lambda kind, spec: Fake(True))
    b.notify(["Read this", ""])
    assert "closed by the person" in capsys.readouterr().out

    # a lock holds its window for the whole duration, then releases the screen
    slept, blocks = [], []
    monkeypatch.setattr(b, "_block_input", lambda on: blocks.append(on) or True)
    monkeypatch.setattr(b.time, "sleep", lambda s: slept.append(s))
    monkeypatch.setattr(b, "_window", lambda kind, spec: shown.append((kind, spec)) or Fake(False))
    b.lock(["900", "In a meeting"])
    assert slept == [900] and shown[-1][0] == "locked" and shown[-1][1]["message"] == "In a meeting"
    assert blocks == [True, False]                  # input blocked for the lock, released after it
    assert "locked for 15 min" in capsys.readouterr().out


async def test_asking_for_help_from_the_tray_pings_the_admin_with_no_message(engine, org, tmp_path: Path, monkeypatch):
    from worker_client.windows import spawn

    shown = []

    class Handle:
        def __init__(self, answer):
            self._answer = answer

        async def answer(self):
            return self._answer

        def close(self):
            pass

    async def fake_open(kind, spec):
        shown.append((kind, spec))
        return Handle({"to": spec["admins"][0]["account_id"]} if kind == "ask" else {"seen": True})

    monkeypatch.setattr(spawn, "open_window", fake_open)
    svc = await _start(engine, tmp_path, "cid-w1", [])
    admin = await _admin(engine)
    try:
        await svc.ask_for_help()
        kinds = [k for k, _ in shown]
        assert kinds == ["ask", "message"]                                   # who to ask, then "Asked ..."
        assert shown[0][1]["admins"][0]["account_id"] == org["a1"]
        assert "Asked" in shown[1][1]["text"]
        status = await admin.call("assistance.ping_status")
        assert status["unaddressed"] == 1 and status["pings"][0]["sender_account_id"] == org["w1"]
        # closing the window without choosing sends nothing
        shown.clear()

        async def closed(kind, spec):
            shown.append((kind, spec))
            return Handle(None)

        monkeypatch.setattr(spawn, "open_window", closed)
        await svc.ask_for_help()
        assert [k for k, _ in shown] == ["ask"]
        assert (await admin.call("assistance.ping_status"))["unaddressed"] == 1
    finally:
        await admin.close()
        await svc.stop()


async def test_a_windows_notification_makes_the_watcher_look_at_once(monkeypatch):
    """A drive arriving is reported the moment Windows says so, not at the next interval (here a minute away)."""
    from worker_client import ossignals

    sent = []

    async def report(type_, payload):
        sent.append((type_, payload))
        return {}

    watcher = ossignals.OsSignals(report, interval=60.0)
    looks = iter([{}, {"E:\\": "E:"}])
    monkeypatch.setattr(ossignals, "drives", lambda: next(looks))
    watcher.set_interest({"usb.inserted": [{}]})
    await watcher.start(native=False)
    try:
        await watcher.tick()                      # the baseline
        watcher.nudge("drives")                   # what Windows' notification does, from its own thread
        for _ in range(40):
            if sent:
                break
            await asyncio.sleep(0.1)
        assert sent == [("control.signal", {"type": "usb.inserted", "data": {"device": "E:\\", "path": "E:\\"}})]
    finally:
        await watcher.stop()


def test_the_windows_notifier_hears_windows_messages():
    import ctypes
    import sys
    import time

    import pytest

    if sys.platform != "win32":
        pytest.skip("Windows only")
    from worker_client import winnotify as w

    got: list[str] = []
    n = w.WindowsNotifier(got.append)
    assert n.start() is True and n._hwnd
    try:
        ctypes.windll.user32.PostMessageW(n._hwnd, w.WM_DEVICECHANGE, w.DBT_DEVNODES_CHANGED, 0)
        ctypes.windll.user32.PostMessageW(n._hwnd, w.WM_WTSSESSION_CHANGE, 5, 1)
        for _ in range(30):
            if {"drives", "sessions"} <= set(got):
                break
            time.sleep(0.1)
        assert {"drives", "sessions"} <= set(got)
    finally:
        n.stop()
    assert not n._thread.is_alive()


async def test_the_worker_reports_what_runs_and_what_is_installed(engine, org, tmp_path: Path):
    svc = await _start(engine, tmp_path, "cid-w1", [])
    admin = await _admin(engine)
    try:
        import sys

        async def reported():
            res = await admin.call("control.programs", {"pc_ids": [org["w1_pc"]]})
            return res["reporting"] == 1 and (sys.platform != "win32" or len(res["installed"]) > 0)
        assert await _wait(reported, timeout=15)
        res = await admin.call("control.programs", {"pc_ids": [org["w1_pc"]]})
        assert any("python" in r["name"].lower() for r in res["running"])        # this very test process
    finally:
        await admin.close()
        await svc.stop()


async def test_a_new_worker_registers_itself_by_asking_and_then_runs(engine, org, tmp_path: Path):
    from worker_client.enroll import EnrollmentEnded, enroll

    cfg = _cfg(engine, tmp_path, "", [])
    cfg.client_id, cfg.client_key = "", ""
    screen: list[str] = []
    admin = await _admin(engine)
    try:
        task = asyncio.create_task(enroll(cfg, department_id=org["fin"], show=screen.append, poll=0.3, hostname="LOBBY-PC"))
        assert await _wait(lambda: any("Code" in line for line in screen), timeout=10)
        code = next(line for line in screen if "Code" in line).split("Code")[1].replace(" ", "").strip()
        waiting = (await admin.call("enroll.list"))["requests"]
        assert [(r["hostname"], r["requested_department_id"]) for r in waiting] == [("LOBBY-PC", org["fin"])]
        done = await admin.call("enroll.confirm", {"enrollment_id": waiting[0]["id"], "code": code})
        got = await asyncio.wait_for(task, 15)
        assert got["client_id"] and got["pc_id"] == done["pc_id"] and "Registered" in screen[-1]
        assert cfg.client_id == got["client_id"] and cfg.client_key == got["client_key"]            # written into the config
        from worker_client.config import WorkerConfig
        assert WorkerConfig.load(cfg.path).client_key == got["client_key"]                          # and saved to disk

        # and it runs as an ordinary Worker with what it was given
        cfg.metrics_seconds = 0.5
        svc = WorkerService(cfg, native_watch=False)
        svc.executor.log_dir = tmp_path / "exec-new"
        svc.executor.log_dir.mkdir()
        await svc.start()
        try:
            assert svc.identity.role == "worker" and svc.identity.department_id == org["fin"]
        finally:
            await svc.stop()

        # a refused request ends in plain words and writes no key
        cfg2 = _cfg(engine, tmp_path, "", [])
        cfg2.client_id, cfg2.client_key = "", ""
        screen2: list[str] = []
        task2 = asyncio.create_task(enroll(cfg2, department_id=org["fin"], show=screen2.append, poll=0.3, hostname="STRAY-PC"))
        assert await _wait(lambda: any("Code" in line for line in screen2), timeout=10)
        pending = (await admin.call("enroll.list"))["requests"]
        await admin.call("enroll.refuse", {"enrollment_id": pending[0]["id"], "reason": "not ours"})
        with pytest.raises(EnrollmentEnded) as ended:
            await asyncio.wait_for(task2, 15)
        assert "refused" in str(ended.value) and "not ours" in str(ended.value) and cfg2.client_key == ""
    finally:
        await admin.close()


async def _events(engine, pc_id: int) -> list[tuple[str, bool, str, str | None]]:
    rows = await engine.db.pool.fetch("SELECT op, is_dir, path, old_path FROM file_events WHERE pc_id = $1 ORDER BY id", pc_id)
    return [(r["op"], r["is_dir"], r["path"].replace("\\", "/").rsplit("/", 1)[-1],
             r["old_path"].replace("\\", "/").rsplit("/", 1)[-1] if r["old_path"] else None) for r in rows]


async def test_the_worker_reports_renames_moves_attributes_and_folders_as_the_os_emits_them(engine, org, tmp_path: Path):
    """Native watcher (the OS's own directory notifications): a rename and a move carry where the file was, a
    read-only flag is not mistaken for an edit, and folders are reported too."""
    import os
    import stat

    docs = tmp_path / "docs"
    docs.mkdir()
    svc = WorkerService(_cfg(engine, tmp_path, "cid-w1", [str(docs)]), native_watch=True)
    svc.executor.log_dir = tmp_path / "exec"
    svc.executor.log_dir.mkdir()
    await svc.start()
    try:
        assert svc.watcher.mode == "native"
        f = docs / "budget.xlsx"
        f.write_text("numbers", encoding="utf-8")
        await asyncio.sleep(1.0)
        f.rename(docs / "budget-old.xlsx")                                  # a rename
        (docs / "archive").mkdir()                                          # a folder is made
        await asyncio.sleep(1.0)
        (docs / "budget-old.xlsx").rename(docs / "archive" / "budget-old.xlsx")      # a move into it
        await asyncio.sleep(1.0)
        os.chmod(docs / "archive" / "budget-old.xlsx", stat.S_IREAD)                # attributes, content untouched
        await asyncio.sleep(1.0)
        os.chmod(docs / "archive" / "budget-old.xlsx", stat.S_IWRITE | stat.S_IREAD)
        (docs / "archive").rename(docs / "archive2")                        # a folder is renamed
        await asyncio.sleep(1.0)
        got = await _events_wait(engine, org["w1_pc"], lambda ev: any(e[0] == "attrib" for e in ev)
                                 and any(e[0] == "move" and e[1] for e in ev))
        assert ("create", False, "budget.xlsx", None) in got
        assert ("move", False, "budget-old.xlsx", "budget.xlsx") in got                    # the rename knows where it was
        assert ("move", False, "budget-old.xlsx", "budget-old.xlsx") in got                # and so does the move
        assert ("create", True, "archive", None) in got                                    # folders are reported
        assert ("move", True, "archive2", "archive") in got
        assert any(e[0] == "attrib" and e[2] == "budget-old.xlsx" for e in got)           # a flag, not an edit
        # the index: only where the file is now
        here = await engine.db.file_index.by_name("budget-old.xlsx")
        assert len(here) == 1 and "archive" in here[0]["path"]
        gone = await engine.db.pool.fetch("SELECT path FROM file_index WHERE gone_at IS NOT NULL")
        assert len(gone) >= 2                                                              # the places it has left
    finally:
        await svc.stop()


async def _events_wait(engine, pc_id: int, ok, timeout: float = 15.0):
    ev = []
    for _ in range(int(timeout / 0.3)):
        ev = await _events(engine, pc_id)
        if ok(ev):
            return ev
        await asyncio.sleep(0.3)
    return ev


async def test_the_polling_watcher_tells_a_move_from_a_delete_and_a_create(engine, org, tmp_path: Path):
    docs = tmp_path / "docs"
    docs.mkdir()
    (docs / "plan.docx").write_text("the plan", encoding="utf-8")
    svc = await _start(engine, tmp_path, "cid-w1", [str(docs)])         # polling: native_watch is off
    try:
        assert svc.watcher.mode == "polling"
        (docs / "plan.docx").rename(docs / "plan-v2.docx")
        got = await _events_wait(engine, org["w1_pc"], lambda ev: any(e[0] == "move" for e in ev), timeout=40.0)
        assert ("move", False, "plan-v2.docx", "plan.docx") in got
        assert not any(e[0] == "delete" for e in got)                  # not a delete followed by a create
    finally:
        await svc.stop()


async def test_the_worker_says_what_it_is_and_reports_disk_network_and_processes(engine, org, tmp_path: Path):
    from worker_client.service import VERSION

    svc = await _start(engine, tmp_path, "cid-w1", [])
    admin = await _admin(engine)
    try:
        async def reported():
            res = await admin.call("machines.get", {"pc_id": org["w1_pc"]})
            m = res["machine"]
            return bool(m["disk"] is not None and res["processes"] and m["os"])
        assert await _wait(reported, timeout=15)
        res = await admin.call("machines.get", {"pc_id": org["w1_pc"]})
        m = res["machine"]
        assert m["version"] == VERSION and m["online"] and m["agent_started_at"] and 0 <= m["disk"] <= 100
        assert any("python" in p["name"].lower() for p in res["processes"]["items"])    # this very test process, with its pid
        assert all(isinstance(p["pid"], int) for p in res["processes"]["items"])
    finally:
        await admin.close()
        await svc.stop()


async def test_the_worker_shows_the_ask_to_delete_a_copy_and_retries_an_update_now(engine, org, tmp_path: Path, monkeypatch):
    from worker_client.windows import spawn

    shown = []

    class Handle:
        async def answer(self):
            return {"seen": True}

        def close(self):
            pass

    async def fake_open(kind, spec):
        shown.append((kind, spec))
        return Handle()

    monkeypatch.setattr(spawn, "open_window", fake_open)
    cfg = _cfg(engine, tmp_path, "cid-w1", [])
    cfg.windows = True
    svc = WorkerService(cfg, native_watch=False)
    svc.executor.log_dir = tmp_path / "exec"
    svc.executor.log_dir.mkdir()
    monkeypatch.setattr(svc, "_start_tray", lambda: asyncio.sleep(0))
    await svc.start()
    admin = await _admin(engine)
    try:
        tried = []

        async def attempt(*, force=False):
            tried.append(force)
            return False

        monkeypatch.setattr(svc.updater, "attempt", attempt)
        await admin.call("index.event", {"event": {"op": "create", "path": "C:/resources/restricted/s.xlsx", "hash": "S"}})
        await svc.call("index.event", {"event": {"op": "copy", "path": "C:/Users/ama/Desktop/s-copy.xlsx", "hash": "S"}})
        issue = (await admin.call("issues.list"))["issues"][0]
        await admin.call("issues.act", {"issue_id": issue["id"], "key": "ask"})
        assert await _wait(lambda: any(k == "message" and "Please delete s-copy.xlsx" in s["text"] for k, s in shown), timeout=10)
        await svc._on_push("update.available", {"version": "9.9.9", "now": True})
        assert await _wait(lambda: tried == [True], timeout=5)
    finally:
        await admin.close()
        await svc.stop()


def test_the_consoles_input_becomes_send_input_steps_and_malformed_events_are_dropped():
    from worker_client.screenstream import ABSOLUTE, KEYUP, UNICODE, WHEEL, plan

    steps = plan([{"t": "move", "x": 0.5, "y": 2.0}, {"t": "down", "button": "right", "x": 0, "y": 1}, {"t": "up", "button": "left", "x": 0, "y": 0},
                  {"t": "wheel", "delta": 99999}, {"t": "key", "vk": 0x141, "down": False}, {"t": "text", "text": "é"},
                  {"t": "move"}, {"t": "down", "x": "no", "y": 0}, {"t": "bogus"}, {"t": "down", "button": "side", "x": 0, "y": 0}])
    assert steps[0] == ("mouse", 0x0001 | ABSOLUTE, 32767, 65535, 0)                    # clamped to the screen
    assert steps[1] == ("mouse", 0x0001 | ABSOLUTE | 0x0008, 0, 65535, 0) and steps[2] == ("mouse", 0x0001 | ABSOLUTE | 0x0004, 0, 0, 0)
    assert steps[3] == ("mouse", WHEEL, 0, 0, 1200)                                      # one notch of the wheel is never more than a few at a time
    assert steps[4] == ("key", 0x41, 0, KEYUP)                                            # the virtual-key code is one byte
    assert steps[5:] == [("key", 0, ord("é"), UNICODE), ("key", 0, ord("é"), UNICODE | KEYUP)]    # the malformed ones produced nothing


async def test_the_screen_streamer_sends_changed_pictures_not_faster_than_asked_and_stops_when_told():
    from worker_client.screenstream import ScreenStreamer

    sent: list[dict] = []
    pictures = [b"one", b"one", b"two"]
    keep = {"value": True}

    async def report(type_, payload):
        sent.append(payload)
        return {"keep": keep["value"]}

    calls = {"n": 0}

    def capture(width):
        picture = pictures[min(calls["n"], len(pictures) - 1)]
        calls["n"] += 1
        return 1920, 1080, width, 540, picture

    streamer = ScreenStreamer(report, capture=capture)
    streamer.start(7, 960, 5)
    for _ in range(100):
        if len(sent) >= 2:
            break
        await asyncio.sleep(0.05)
    assert [s["session_id"] for s in sent[:2]] == [7, 7] and sent[0]["w"] == 960 and sent[0]["screen_w"] == 1920
    assert sent[0]["png_b64"] != sent[1]["png_b64"]                                   # the unchanged second picture was not sent again
    assert streamer.active == {7}
    keep["value"] = False                                                              # the Engine says stop in its reply
    for _ in range(100):
        if not streamer.active:
            break
        await asyncio.sleep(0.05)
    assert streamer.active == set()
    streamer.start(8, 640, 1)
    streamer.stop(8)
    await streamer.shutdown()
    assert streamer.active == set()


def test_the_lockout_tells_viewing_from_blocking():
    from worker_client.lockout import Lockout

    lock = Lockout()
    blocked, viewed = [], []
    lock.on_change(blocked.append)
    lock.on_view_change(viewed.append)
    lock.view({"occupant_name": "R. Mensah"})
    assert lock.viewing_by and not lock.is_blocked and viewed == [lock.viewing_by]
    lock.block({"occupant_name": "R. Mensah"})                                         # control: the cover replaces the bar
    assert lock.is_blocked and lock.viewing_by is None and viewed[-1] is None and blocked[-1]["occupant_name"] == "R. Mensah"
    lock.view({"occupant_name": "R. Mensah"})                                          # back to looking: the cover goes, the bar returns
    assert not lock.is_blocked and blocked[-1] is None and viewed[-1]["occupant_name"] == "R. Mensah"
    lock.release()
    assert lock.viewing_by is None and viewed[-1] is None
