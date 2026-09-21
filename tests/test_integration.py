"""Phase 4 -- full integration: Engine + Operator Client command layer + real Worker Clients
(skipped without FALCON_TEST_DATABASE_URL).

The three Hierarchy example scenarios, the cross-combo chains from the ecosystem synthesis
(Task -> Flow, Task -> Events -> Control, Resource -> Events -> Control, Events -> Control on
a Flow failure), and a network drop mid-traversal with a real Operator connection.
"""

from __future__ import annotations

import asyncio
from datetime import timedelta
from pathlib import Path

from common.connection import EngineConnection
from engine.database import _now
from engine.hierarchy import traversal
from operator_client.core import LocalConfig
from operator_client.tui.shell import run_script
from tests.conftest import requires_db
from worker_client.config import WorkerConfig
from worker_client.service import WorkerService
from worker_client.ui import UIContext
from worker_client.ui import run_line as worker_line

pytestmark = requires_db


# --- harness ------------------------------------------------------------------------------------

def _op(engine, tmp_path: Path, client_id: str) -> LocalConfig:
    return LocalConfig(engine_host="127.0.0.1", engine_port=engine.port, client_id=client_id, tls=False,
                       path=tmp_path / f"op-{client_id}.json")


async def _worker(engine, tmp_path: Path, client_id: str, roots: list[str]) -> WorkerService:
    cfg = WorkerConfig(engine_host="127.0.0.1", engine_port=engine.port, client_id=client_id, tls=False,
                       watch_roots=roots, poll_seconds=0.3, metrics_seconds=0.5, idle_sweep_after_seconds=999999,
                       path=tmp_path / f"w-{client_id}.json")
    svc = WorkerService(cfg, native_watch=False)
    svc.executor.log_dir = tmp_path / f"exec-{client_id}"
    svc.executor.log_dir.mkdir()
    await svc.start()
    return svc


async def _wait(cond, timeout: float = 10.0, step: float = 0.1) -> bool:
    for _ in range(int(timeout / step)):
        ok = await cond() if asyncio.iscoroutinefunction(cond) else cond()
        if ok:
            return True
        await asyncio.sleep(step)
    return False


async def _audit(engine, prefix: str) -> list[dict]:
    return await engine.db.audit.recent(action_prefix=prefix, limit=50)


# --- Scenario 1: Super User auditing department operations ----------------------------------------

async def test_scenario_1_super_user_audits_a_department(engine, org, tmp_path: Path):
    w1 = await _worker(engine, tmp_path, "cid-w1", [])
    try:
        # The Admin has been active: labelled a worker, run an action.
        await run_script(_op(engine, tmp_path, "cid-a1"), [
            "connect", f"name set {org['w1']} Lab PC", "action add monitoring system_metrics timeout=20",
            f"action run 1 {org['w1_pc']}"])
        assert await _wait(lambda: 1 in w1.executor.completed)
        # 1-3: Super User sees every department and its Admins. 4-6: traverses into Admin1's
        # workstation; the red banner is on. 7: reviews Admin1's recent actions. 8: back out.
        su = await run_script(_op(engine, tmp_path, "cid-su"), [
            "connect", "tree", f"traverse {org['a1_pc']}", "status", f"audit actor={org['a1']}", "end", "tree"])
        assert "Finance" in su[1] and "HR" in su[1] and "FIN-ADM" in su[1]
        assert "[RED BANNER]" in su[2] and "Conditional Rendering" not in su[2]     # Super User exemption
        assert "SUPER USER" in su[3].upper() and "super_user_banner    yes" in su[3]
        assert "display_name.set" in su[4] and "action.run" in su[4]
        assert su[5].endswith("(voluntary)")
        assert "TRAVERSAL" not in su[6].split("FIN-ADM")[1].split("\n")[0]        # session gone
        # The audit entry: who, into what, when, how long -- and the review itself is logged.
        ended = [e for e in await _audit(engine, "session.ended") if e["detail"].get("occupied_via") == "traversal"]
        assert ended and ended[0]["actor_account_id"] == org["su"] and ended[0]["detail"]["pc_id"] == org["a1_pc"]
        assert isinstance(ended[0]["detail"]["duration_seconds"], int)
        assert (await _audit(engine, "audit.reviewed"))[0]["target_id"] == str(org["a1"])
        # Display names never leaked: Super User saw the Admin's label for the worker only as
        # the Admin's own view -- the Super User's tree shows the composed fallback.
        assert "Lab PC" not in su[1]
    finally:
        await w1.stop()


# --- Scenario 2: Admin managing a specific Client PC -----------------------------------------------

async def test_scenario_2_admin_manages_a_client_pc_and_updates_the_department(engine, org, tmp_path: Path):
    w1 = await _worker(engine, tmp_path, "cid-w1", [])
    w2 = await _worker(engine, tmp_path, "cid-w2", [])
    try:
        # 1-3: Admin sees the department's PCs, enters PC "FIN-01"; the worker there is blocked.
        a1 = await run_script(_op(engine, tmp_path, "cid-a1"), [
            "connect", "tree", f"traverse {org['w1_pc']} force", "session",
            # 5: a department-wide policy update -- one Custom Action, every PC, independent runs
            "action custom policy python " + str(_script(tmp_path, "print('policy v2 applied')")) + " timeout=20",
            f"action run 1 dept={org['fin']}",
            "end"])
        assert "FIN-01" in a1[1] and "FIN-02" in a1[1] and "HR-ADM" not in a1[1]
        assert a1[2].startswith("entered pc") and "Conditional Rendering" in a1[2]
        assert await _wait(lambda: not w1.lockout.is_blocked)    # released after `end`
        assert "started on FIN-01" in a1[5] or "started on FIN-ADM" in a1[5]
        assert await _wait(lambda: 1 in w1.executor.completed and 1 in w2.executor.completed
                           or (len(w1.executor.completed) + len(w2.executor.completed)) >= 2, timeout=20)
        assert all(v == "success" for v in list(w1.executor.completed.values()) + list(w2.executor.completed.values()))
        # Audit: the traversal with its duration, and the department-wide run.
        ended = [e for e in await _audit(engine, "session.ended") if e["detail"].get("occupied_via") == "traversal"]
        assert ended[0]["actor_account_id"] == org["a1"] and ended[0]["detail"]["pc_id"] == org["w1_pc"]
        run = (await _audit(engine, "action.run"))[0]
        assert run["detail"]["department_id"] == org["fin"] and len(run["detail"]["pcs"]) == 3
    finally:
        await w1.stop()
        await w2.stop()


def _script(tmp_path: Path, body: str) -> Path:
    p = tmp_path / "policy.py"
    p.write_text(body + "\n", encoding="utf-8")
    return p


# --- Scenario 3: Client receives an alert ---------------------------------------------------------

async def test_scenario_3_client_receives_alert_and_has_no_control(engine, org, tmp_path: Path):
    w1 = await _worker(engine, tmp_path, "cid-w1", [])
    seen: list[tuple[str, dict]] = []

    async def notify(t, p):
        seen.append((t, p))

    w1.on_notify(notify)
    try:
        await run_script(_op(engine, tmp_path, "cid-a1"), [
            "connect", f"alert warning department Department policy update applied - restart required by end of day dept={org['fin']} link=restart://now"])
        assert await _wait(lambda: any(t == "alert.delivered" for t, _ in seen))
        alert = next(p for t, p in seen if t == "alert.delivered")
        assert "restart required" in alert["body"] and alert["action_link"] == "restart://now"
        ui = UIContext(w1)
        assert "restart requir" in await worker_line(ui, "alerts")
        assert "connected" in await worker_line(ui, "status")
        # No software control available to the client: none of the operator commands exist here.
        for cmd in ("tree", f"traverse {org['w2_pc']}", "action add control notify message=x", "dashboard", "flows"):
            assert "unknown command" in await worker_line(ui, cmd)
        # And the Engine refuses even a hand-crafted control request from a worker identity.
        assert (await worker_line(ui, "task verify 1 complete")).startswith("usage")
    finally:
        await w1.stop()


# --- Cross-combo chains --------------------------------------------------------------------------

async def test_chain_task_target_appears_flow_carries_it_and_event_fires_action(engine, org, tmp_path: Path):
    """Task -> Global File Index -> Flow (file moves to another PC) and Task -> Events -> Control
    (the target appearing fires an Event whose Action runs on the assignee's PC)."""
    docs = tmp_path / "w1docs"
    inbox = tmp_path / "w2inbox"
    docs.mkdir()
    inbox.mkdir()
    w1 = await _worker(engine, tmp_path, "cid-w1", [str(docs)])
    w2 = await _worker(engine, tmp_path, "cid-w2", [str(inbox)])
    try:
        out = await run_script(_op(engine, tmp_path, "cid-a1"), [
            "connect",
            # Task: create-intent target, name-first, no path.
            "task item add file create q4-analysis.xlsx", f"task create assignee={org['w1']} desc='Q4 analysis'",
            # Flow: whatever lands in the worker's docs flows on to the second PC.
            f"flow create src={org['w1_pc']}:{docs} dest={org['w2_pc']}:{inbox}",
            # Event: when the task's target appears, notify (an Action on the assignee's PC).
            "action add control notify message=target-arrived timeout=10",
            "event add task.target_appeared actions=1 match_task_id=1",
        ])
        assert "task 1 created" in out[2] and "flow 1 active" in out[3] and out[5].startswith("event 1"), out
        # The worker starts and produces the file wherever they like.
        assert (await run_script(_op(engine, tmp_path, "cid-a1"), ["connect", "task 1"]))[1]
        ui = UIContext(w1)
        assert "in_progress" in await worker_line(ui, "task start 1")
        (docs / "q4-analysis.xlsx").write_bytes(b"numbers")
        # Task: the create item binds and passes -- tracked by identity, not location.
        async def item_passed():
            t = await engine.db.tasks.get(1)
            return t is not None and t["items"][0]["file_index_id"] is not None
        assert await _wait(item_passed)
        # Flow: the same file event carried it to the other PC.
        assert await _wait(lambda: (inbox / "q4-analysis.xlsx").exists())
        assert (inbox / "q4-analysis.xlsx").read_bytes() == b"numbers"
        # Events -> Control: the target appearing fired the event; the action ran on w1.
        assert await _wait(lambda: 1 in w1.executor.completed, timeout=15)
        assert w1.executor.completed[1] == "success"
        fired = await _audit(engine, "event.fired")
        assert fired and fired[0]["detail"]["type"] == "task.target_appeared"
        # Manual verification is still the only completion.
        t = await engine.db.tasks.get(1)
        assert t["status"] == "in_progress"
        done = await run_script(_op(engine, tmp_path, "cid-a1"), ["connect", "task stack 1", "task verify 1 complete"])
        assert "passed" in done[1] and "-> completed" in done[2]
    finally:
        await w1.stop()
        await w2.stop()


async def test_chain_resource_violation_fires_event_and_flow_ignores_the_file(engine, org, tmp_path: Path):
    """Resource -> Events -> Control: a restricted file appearing on a worker PC is a violation
    that fires an Event whose Action runs; Flow will not move the offending file."""
    adm = tmp_path / "resources"          # the tier root is literally /resources/
    (adm / "restricted").mkdir(parents=True)
    docs = tmp_path / "w1docs"
    docs.mkdir()
    inbox = tmp_path / "w2inbox"
    inbox.mkdir()
    a1_worker = await _worker(engine, tmp_path, "cid-a1", [str(adm)])   # the Admin PC's own service
    w1 = await _worker(engine, tmp_path, "cid-w1", [str(docs)])
    w2 = await _worker(engine, tmp_path, "cid-w2", [str(inbox)])
    try:
        # Tag by folder: the Admin's /restricted/ file is tracked by hash.
        (adm / "restricted" / "salaries.xlsx").write_bytes(b"SECRET-PAYROLL")
        async def tagged():
            rows = await engine.db.file_index.by_hash(__import__("hashlib").sha256(b"SECRET-PAYROLL").hexdigest())
            return bool(rows) and rows[0]["resource_tag"] == "restricted"
        assert await _wait(tagged)
        # Automation: on a violation, snapshot the system (an action on the offending PC); and a
        # flow out of the worker's docs.
        su = EngineConnection("127.0.0.1", engine.port, client_id="cid-su", tls=False)
        await su.connect()
        setup = await run_script(_op(engine, tmp_path, "cid-a1"), [
            "connect", "action add monitoring process_list timeout=20", "event add resource.violation actions=1",
            f"flow create src={org['w1_pc']}:{docs} dest={org['w2_pc']}:{inbox}"])
        assert setup[2].startswith("event 1") and "flow 1 active" in setup[3]
        # The worker copies the restricted content (renamed) into their docs.
        (docs / "totally-innocent.xlsx").write_bytes(b"SECRET-PAYROLL")
        assert await _wait(lambda: len(w1.lockout.blocked_by or {}) == 0 and True)  # no block; just checks liveness
        async def violated():
            return bool(await engine.db.resource.list_violations(department_id=org["fin"]))
        assert await _wait(violated)
        # Super User got the report; the event fired; the action ran on the worker's PC.
        await asyncio.sleep(0.5)
        assert (await engine.db.reports.all())[0]["category"] == "resource_violation"
        assert await _wait(lambda: 1 in w1.executor.completed, timeout=15)
        fired = await _audit(engine, "event.fired")
        assert fired and fired[0]["detail"]["type"] == "resource.violation"
        # Flow ignores that one file; an innocent file still flows.
        (docs / "memo.txt").write_bytes(b"ok")
        assert await _wait(lambda: (inbox / "memo.txt").exists())
        await asyncio.sleep(1.0)
        assert not (inbox / "totally-innocent.xlsx").exists()
        # The worker sees it, removes it, resolves; the file is no longer ignored.
        ui = UIContext(w1)
        assert "totally-innocent.xlsx" in await worker_line(ui, "violations")
        (docs / "totally-innocent.xlsx").unlink()
        vid = (await engine.db.resource.list_violations(department_id=org["fin"]))[0]["id"]
        assert "resolved" in await worker_line(ui, f"violation resolve {vid}")
        assert await engine.db.resource.ignored_file_ids(org["w1_pc"]) == set()
        await su.close()
    finally:
        await a1_worker.stop()
        await w1.stop()
        await w2.stop()


async def test_chain_flow_failure_is_reported_routed_and_fires_an_action(engine, org, tmp_path: Path):
    """Events -> Control on a Flow failure: an unsupported Transformation pauses the branch,
    raises a routed report, and fires an Event whose Action runs -- then resume works."""
    src = tmp_path / "src"
    dst = tmp_path / "dst"
    src.mkdir()
    dst.mkdir()
    w1 = await _worker(engine, tmp_path, "cid-w1", [str(src)])
    w2 = await _worker(engine, tmp_path, "cid-w2", [str(dst)])
    try:
        await run_script(_op(engine, tmp_path, "cid-su"), ["connect", f"routing set flow_failure {org['fin']}"])
        out = await run_script(_op(engine, tmp_path, "cid-a1"), [
            "connect", "action add control notify message=flow-broke timeout=10", "event add flow.failed actions=1",
            f"flow create src={org['w1_pc']}:{src} dest={org['w2_pc']}:{dst}@0 stage=transformation:to=pdf"])
        assert "flow 1 active" in out[3]
        (src / "memo.txt").write_bytes(b"hello")
        async def paused():
            f = await engine.db.flows.get(1)
            return bool(f and f["destinations"][0]["paused_reason"] == "transformation:unsupported_format")
        assert await _wait(paused)
        # Routed to Finance: the Admin's pane shows it; the Event fired; the action ran on the destination PC.
        pane = await run_script(_op(engine, tmp_path, "cid-a1"), ["connect", "reports", "flow 1"])
        assert "flow_failure" in pane[1] and "unsupported_format" in pane[2] and "Remove the Transformation" not in pane[2]
        assert "cannot be converted" in pane[2]
        assert await _wait(lambda: 1 in w2.executor.completed, timeout=15)
        # Fix the flow (drop the stage) and resume: the file now syncs.
        fixed = await run_script(_op(engine, tmp_path, "cid-a1"), [
            "connect", f"flow edit 1 dest={org['w2_pc']}:{dst}", "flow resume 1", "flow trigger 1 memo.txt"])
        assert "transfer" in fixed[3]
        assert await _wait(lambda: (dst / "memo.txt").exists())
    finally:
        await w1.stop()
        await w2.stop()


# --- Network drop mid-traversal -------------------------------------------------------------------

async def test_network_drop_mid_traversal_with_real_clients(engine, org, tmp_path: Path):
    w1 = await _worker(engine, tmp_path, "cid-w1", [])
    try:
        admin = EngineConnection("127.0.0.1", engine.port, client_id="cid-a1", tls=False)
        await admin.connect()
        res = await admin.call("hierarchy.traverse", {"pc_id": org["w1_pc"], "force": True})
        sid = res["session"]["session_id"]
        assert await _wait(lambda: w1.lockout.is_blocked)
        # The Admin's laptop drops off the network. Nothing happens to the block: the worker
        # stays blocked, and the traversal session is still active.
        await admin.close()
        await asyncio.sleep(0.5)
        assert w1.lockout.is_blocked and (await engine.db.sessions.by_id(sid))["ended_at"] is None
        # ...until the same deadline that always governed the session fires.
        await engine.db.pool.execute("UPDATE sessions SET deadline_at = $2 WHERE id = $1", sid, _now() - timedelta(seconds=1))
        await traversal.expire_due_sessions(engine)
        assert (await engine.db.sessions.by_id(sid))["ended_reason"] == "network_drop_deadline_expired"
        assert await _wait(lambda: not w1.lockout.is_blocked and w1.native_session_id is not None)
        ended = (await _audit(engine, "session.ended"))[0]
        assert ended["detail"]["reason"] == "network_drop_deadline_expired"
    finally:
        await w1.stop()
