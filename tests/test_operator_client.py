"""Operator Client core + TUI command layer against a DB-backed Engine (skipped without
FALCON_TEST_DATABASE_URL). No prompt_toolkit needed: the command layer is UI-free."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from operator_client.core import ClientState, EngineConnection, EngineError, LocalConfig
from operator_client.tui.shell import ShellContext, parse, run_line, run_script
from tests.conftest import key_for, requires_db

pytestmark = requires_db


def test_arg_grammar():
    words, args = parse('task item add file create "my report.docx" path=C:/new link=1 dest=1:C:/a dest=2:C:/b')
    assert words[:4] == ["task", "item", "add", "file"]
    assert args.positional[5] == "my report.docx"
    assert args.opt("path") == "C:/new" and args.opt_int("link") == 1
    assert args.all("dest") == ["1:C:/a", "2:C:/b"]
    # Windows paths and `x=1` in prose stay positional (keys must be lowercase identifiers).
    _, a2 = parse("task propose 3 write C:/out/x.txt where x=1 wins")
    assert "C:/out/x.txt" in a2.positional and "x" not in a2.options
    _, a3 = parse(r'action custom p python C:\Users\me\policy.py path="C:\Temp\my dir\f.txt"')
    assert a3.positional[4] == r"C:\Users\me\policy.py" and a3.opt("path") == r"C:\Temp\my dir\f.txt"


async def test_connection_handshake_call_and_push(engine, org):
    state = ClientState()
    conn = EngineConnection("127.0.0.1", engine.port, client_id="cid-a1", tls=False, derived_key=key_for("cid-a1"), hostname="FIN-ADM")
    conn.on_push(state.on_push)
    ident = await conn.connect()
    assert ident.role == "admin" and ident.account_id == org["a1"]
    tree = await conn.call("hierarchy.tree")
    assert tree["departments"][0]["name"] == "Finance"
    with pytest.raises(EngineError) as exc:
        await conn.call("hierarchy.traverse", {"pc_id": org["a2_pc"]})
    assert exc.value.code == "forbidden"
    # A push reaches the state: a Super User forces into A1's workstation.
    su = EngineConnection("127.0.0.1", engine.port, client_id="cid-su", tls=False, derived_key=key_for("cid-su"))
    await su.connect()
    await su.call("hierarchy.traverse", {"pc_id": org["a1_pc"], "force": True})
    await asyncio.sleep(0.2)
    state.pc_id = ident.pc_id
    state.account_id = ident.account_id
    assert any(t == "session.blocked" for _, t, _ in state.recent_pushes)
    await su.close()
    await conn.close()


async def test_local_config_roundtrip(tmp_path: Path):
    cfg = LocalConfig(engine_host="engine.local", engine_port=7401, client_id="abc", tls=False, path=tmp_path / "op.json")
    cfg.cache["departments"] = [{"id": 1, "name": "Finance"}]
    cfg.save()
    back = LocalConfig.load(tmp_path / "op.json")
    assert back.engine_address == "engine.local:7401" and back.client_id == "abc" and back.tls is False
    assert back.cache["departments"][0]["name"] == "Finance"


def _cfg(engine, tmp_path: Path, client_id: str) -> LocalConfig:
    return LocalConfig(engine_host="127.0.0.1", engine_port=engine.port, client_id=client_id, client_key=key_for(client_id), tls=False,
                       path=tmp_path / f"{client_id}.json")


async def test_scripted_admin_session(engine, org, tmp_path: Path):
    out = await run_script(_cfg(engine, tmp_path, "cid-a1"), [
        "connect", "status", "tree", f"traverse {org['w1_pc']}", "extend", "session", "end",
        f"name set {org['w1']} Desk 1", f"names {org['w1']}", "help traverse", "nope", "quit", "tree"])
    assert out[0].startswith("connected to 127.0.0.1") and "as Admin" in out[0]
    assert "role        Admin" in out[1].replace("  ", " ").replace("   ", " ") or "Admin" in out[1]
    assert "Finance" in out[2] and "WORKER" in out[2]
    assert out[3].startswith("entered pc") and "restricted view" in out[3]
    assert out[4].startswith("deadline now")
    assert "TRAVERSAL" in out[5]
    assert out[6].endswith("(voluntary)")
    assert "Desk 1" in out[7] and "Desk 1" in out[8]
    assert "traverse <pc_id> [force]" in out[9]
    assert out[10].startswith("unknown command")
    assert out[11] == "bye" and len(out) == 12          # quit stops the script


async def test_scripted_task_flow_end_to_end(engine, org, tmp_path: Path):
    from tests.test_task import ScriptedLLM

    engine.llm = ScriptedLLM({"the name of the software program or application mentioned": "Word",
                              "What should happen with the program Word?": "use it"})
    # Admin proposes, edits the stack, creates; worker starts; admin verifies.
    admin = await run_script(_cfg(engine, tmp_path, "cid-a1"), [
        "connect",
        f"task propose {org['w1']} Use Word to write report.docx into C:/new by Friday",
        "task items",
        "task item add program installed_available 7-Zip",
        "task item rm 3",
        "task create",
        "tasks",
    ])
    assert "report.docx" in admin[1] and "used_with_file" in admin[1] and "by Friday" in admin[1]
    assert "7-Zip" in admin[3] and "7-Zip" not in admin[4]
    assert admin[5].startswith("task ") and "created" in admin[5]
    task_id = int(admin[5].split()[1])
    assert str(task_id) in admin[6]

    worker = await run_script(_cfg(engine, tmp_path, "cid-w1"), [
        "connect", "tasks", f"task start {task_id}", f"task {task_id}", f"task verify {task_id} complete"])
    assert "in_progress" in worker[2]
    assert "verification stack" in worker[3]
    assert worker[4].startswith("forbidden")

    admin2 = await run_script(_cfg(engine, tmp_path, "cid-a1"), [
        "connect", f"task stack {task_id}", f"task verify {task_id} complete", "tasks", "tasks all"])
    assert "pending" in admin2[1]
    assert "-> completed" in admin2[2]
    assert str(task_id) not in admin2[3] and str(task_id) in admin2[4]


async def test_scripted_flow_assistance_control_updates(engine, org, tmp_path: Path):
    a1 = _cfg(engine, tmp_path, "cid-a1")
    out = await run_script(a1, [
        "connect",
        (f"flow create src={org['a1_pc']}:C:/out dest={org['w1_pc']}:C:/in@1 dest={org['w2_pc']}:C:/in@2 "
         "stage=transformation:to=pdf stage=branch@0 stage=categorization@1:by=extension"),
        "flows",
        f"flow create src={org['a1_pc']}:C:/out2 dest={org['a2_pc']}:C:/from-fin",
        "action add control notify message=hello timeout=5",
        "actions",
        "event add usb.inserted actions=1",
        "events",
        "dashboard",
        f"ping {org['w1']}",
        "updates",
        "violations",
        "reports",
    ])
    assert out[1].startswith("flow 1 active") and "transformation" in out[1] and "categorization" in out[1]
    assert "1" in out[2]
    assert "waiting for the destination owner's consent" in out[3]
    assert out[4].startswith("action 1 'notify' created")
    assert "notify" in out[5] and "built-in" in out[5]
    assert out[6].startswith("event 1 (native_pushed)")
    assert "usb.inserted" in out[7]
    assert "ENABLED AUTOMATIONS" in out[8] and "never run" in out[8]
    assert out[9] == "forbidden: pings go between a subordinate and their direct superior" or out[9].startswith("ping ")
    assert "current version: (none approved)" in out[10]
    assert out[11] == "(none)" and out[12] == "(none)"

    # HR admin answers the consent request; Super User approves a version and sees reports.
    a2 = await run_script(_cfg(engine, tmp_path, "cid-a2"), ["connect", "flow consent 2 yes", "assist available on"])
    assert a2[1] == "flow 2: consent granted" and a2[2] == "available for assistance"
    su = await run_script(_cfg(engine, tmp_path, "cid-su"), [
        "connect", "update approve 1.0.0", "routing", "routing set flow_failure 1", "addressed",
        "alert announcement all_users Maintenance tonight", "alerts"])
    assert su[1].startswith("version 1.0.0 approved")
    assert "flow_failure" in su[2] and "flow_failure -> departments [1]" in su[3]
    assert su[4] == "(none)"
    assert su[5].startswith("alert ") and "delivered" in su[5]
    assert "Maintenance tonight" in su[6]


async def test_push_updates_state_and_indicators(engine, org, tmp_path: Path):
    state = ClientState()
    ctx = ShellContext(config=_cfg(engine, tmp_path, "cid-w1"), state=state)
    import operator_client.tui.commands  # noqa: F401

    await run_line(ctx, "connect")
    assert state.connected and state.role == "worker" and state.session["occupied_via"] == "native"
    admin = EngineConnection("127.0.0.1", engine.port, client_id="cid-a1", tls=False, derived_key=key_for("cid-a1"))
    await admin.connect()
    await admin.call("hierarchy.traverse", {"pc_id": org["w1_pc"], "force": True})
    await admin.call("assistance.ping", {"to_account_id": org["w1"]})
    await asyncio.sleep(0.3)
    assert state.blocked_by and state.session is None
    kinds = {i.kind for i in state.indicators}
    assert {"blocked", "session", "unaddressed_ping"} <= kinds and state.unaddressed_pings == 1
    status = await run_line(ctx, "status")
    assert "BLOCKED" in status and "unaddressed ping" in status
    sid = (await admin.call("hierarchy.session_state", {"pc_id": org["w1_pc"]}))["pc_session"]["session_id"]
    await admin.call("hierarchy.end_session", {"session_id": sid})
    await asyncio.sleep(0.3)
    assert state.blocked_by is None
    assert (await run_line(ctx, "claim")).startswith("claimed native session")
    await admin.close()
    assert ctx.conn is not None
    await ctx.conn.close()


def test_deadline_phrases_resolve_mechanically():
    from datetime import datetime, timezone

    from operator_client.core.deadlines import resolve_phrase

    now = datetime(2026, 9, 21, 10, 0, tzinfo=timezone.utc)  # a Monday
    assert resolve_phrase("by Friday", now) == datetime(2026, 9, 25, 17, 0, tzinfo=timezone.utc)
    assert resolve_phrase("before end of day Thursday", now) == datetime(2026, 9, 24, 17, 0, tzinfo=timezone.utc)
    assert resolve_phrase("by 3pm tomorrow", now) == datetime(2026, 9, 22, 15, 0, tzinfo=timezone.utc)
    assert resolve_phrase("today", now) == datetime(2026, 9, 21, 17, 0, tzinfo=timezone.utc)
    assert resolve_phrase("tonight", now) == datetime(2026, 9, 21, 23, 59, tzinfo=timezone.utc)
    assert resolve_phrase("by Monday", now) == datetime(2026, 9, 21, 17, 0, tzinfo=timezone.utc)   # still ahead today
    evening = datetime(2026, 9, 21, 18, 0, tzinfo=timezone.utc)
    assert resolve_phrase("by Monday", evening) == datetime(2026, 9, 28, 17, 0, tzinfo=timezone.utc)  # past -> next week
    assert resolve_phrase("next friday", now) == datetime(2026, 9, 25, 17, 0, tzinfo=timezone.utc)
    assert resolve_phrase("next monday", now) == datetime(2026, 9, 28, 17, 0, tzinfo=timezone.utc)
    assert resolve_phrase("2026-10-01T09:00:00+00:00", now) == datetime(2026, 10, 1, 9, 0, tzinfo=timezone.utc)
    assert resolve_phrase("by Monday or Wednesday", now) is None
    assert resolve_phrase("when you can", now) is None
