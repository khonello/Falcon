"""Moving the Super User to a dedicated machine: the same account, one machine at a time, only with the current Super User's say-so."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from common.connection import ConnectionError_, EngineConnection, EngineError
from engine.hierarchy import handover
from tests.conftest import key_for, requires_db

pytestmark = requires_db


async def _new_machine(engine) -> EngineConnection:
    m = EngineConnection("127.0.0.1", engine.port, client_id="", tls=False)
    await m.open()
    return m


async def test_a_machine_cannot_ask_to_be_the_super_user_s_unless_a_handover_is_open(engine, org, connect):
    m = await _new_machine(engine)
    try:
        with pytest.raises(EngineError) as err:
            await m.call("enroll.request", {"hostname": "SU-REAL", "level": "super_user"})
        assert err.value.code == "forbidden"
    finally:
        await m.close()


async def test_only_the_super_user_opens_confirms_or_cancels(engine, org, connect):
    a1 = await connect("cid-a1")
    for op in ("handover.open", "handover.cancel", "handover.status"):
        assert await a1.err(op, {}) == "forbidden"
    assert await a1.err("handover.confirm", {"enrollment_id": 1, "code": "0000"}) == "forbidden"


async def test_the_same_super_user_moves_to_the_new_machine_and_the_old_one_stops_being_theirs(engine, org, connect):
    su = await connect("cid-su")
    old_pc = (await engine.db.accounts.by_id(org["su"]))["bound_pc_id"]
    assert (await su.ok("handover.open", {}))["open"] is True
    new = await _new_machine(engine)
    try:
        asked = await new.call("enroll.request", {"hostname": "SU-DEDICATED", "level": "super_user"})
        status = await su.ok("handover.status", {})
        assert status["open"] and [w["hostname"] for w in status["waiting"]] == ["SU-DEDICATED"]
        eid = status["waiting"][0]["id"]
        assert "code" not in status["waiting"][0]                                               # the code is on the new machine's screen, not here
        # the ordinary confirmation will not do it, and a wrong code does not move anything
        assert await su.err("enroll.confirm", {"enrollment_id": eid, "code": asked["code"], "department_id": org["fin"]}) == "forbidden"
        wrong = "0000" if asked["code"] != "0000" else "1111"
        assert await su.err("handover.confirm", {"enrollment_id": eid, "code": wrong}) == "invalid"
        assert (await engine.db.accounts.by_id(org["su"]))["bound_pc_id"] == old_pc

        moved = await su.ok("handover.confirm", {"enrollment_id": eid, "code": asked["code"]})
        assert moved["status"] == "moved" and moved["from_pc"] == old_pc and moved["account_id"] == org["su"]
        acct = await engine.db.accounts.by_id(org["su"])
        assert acct["bound_pc_id"] == moved["to_pc"] and acct["status"] == "active" and acct["role"] == "super_user"     # the SAME account
        supers = [a for a in await engine.db.accounts.list_all() if a["role"] == "super_user" and a["status"] == "active"]
        assert len(supers) == 1                                                                  # there is always exactly one

        got = await new.call("enroll.wait", {"token": asked["token"]})                           # the new machine collects its own key, once
        assert got["status"] == "confirmed" and got["account_id"] == org["su"]
        again = await new.call("enroll.wait", {"token": asked["token"]})
        assert again["status"] == "collected"
        # ... and signs in as the Super User
        console = EngineConnection("127.0.0.1", engine.port, client_id=got["client_id"], tls=False, derived_key=got["client_key"])
        ident = await console.connect()
        try:
            assert ident.role == "super_user" and ident.account_id == org["su"]
        finally:
            await console.close()
        # the old machine's key no longer opens anything
        old = EngineConnection("127.0.0.1", engine.port, client_id="cid-su", tls=False, derived_key=key_for("cid-su"))
        with pytest.raises((EngineError, ConnectionError_)):
            await old.connect()
        kinds = [r["action_type"] for r in await engine.db.pool.fetch("SELECT action_type FROM audit_log WHERE action_type LIKE 'handover.%'")]
        assert kinds == ["handover.opened", "handover.completed"]
        assert handover.is_open() is False                                                       # one handover, then closed
    finally:
        await new.close()


async def test_a_window_that_has_closed_cannot_be_used_and_cancel_refuses_whoever_waits(engine, org, connect):
    su = await connect("cid-su")
    await su.ok("handover.open", {})
    new = await _new_machine(engine)
    try:
        asked = await new.call("enroll.request", {"hostname": "SU-DEDICATED", "level": "super_user"})
        eid = (await su.ok("handover.status", {}))["waiting"][0]["id"]
        handover._open["until"] = datetime.now(timezone.utc) - timedelta(seconds=1)              # ten minutes pass
        assert await su.err("handover.confirm", {"enrollment_id": eid, "code": asked["code"]}) == "conflict"
        assert (await engine.db.accounts.by_id(org["su"]))["bound_pc_id"] is not None
        await su.ok("handover.open", {})
        assert (await su.ok("handover.cancel", {}))["refused"] == 1
        assert (await new.call("enroll.wait", {"token": asked["token"]}))["status"] == "refused"
        assert await su.err("handover.confirm", {"enrollment_id": eid, "code": asked["code"]}) in ("conflict", "forbidden")
    finally:
        await new.close()


async def test_five_wrong_codes_refuse_the_request(engine, org, connect):
    su = await connect("cid-su")
    await su.ok("handover.open", {})
    new = await _new_machine(engine)
    try:
        asked = await new.call("enroll.request", {"hostname": "SU-DEDICATED", "level": "super_user"})
        eid = (await su.ok("handover.status", {}))["waiting"][0]["id"]
        wrong = "0000" if asked["code"] != "0000" else "1111"
        results = [await su.err("handover.confirm", {"enrollment_id": eid, "code": wrong}) for _ in range(handover.MAX_WRONG_CODES)]
        assert results[-1] == "forbidden" and results[0] == "invalid"
        assert (await new.call("enroll.wait", {"token": asked["token"]}))["status"] == "refused"
    finally:
        await new.close()


async def test_a_new_machine_joins_from_its_own_console_settings(engine, org, connect, tmp_path):
    """What `python -m operator_client --handover-join` does: asks, shows a code, and once the current Super User confirms it keeps its own key."""
    import asyncio

    from operator_client.core.config import LocalConfig
    from operator_client.core.handover_join import HandoverEnded, join

    su = await connect("cid-su")
    cfg = LocalConfig(path=tmp_path / "operator.json", engine_host="127.0.0.1", engine_port=engine.port, tls=False)
    shown: list[str] = []
    # nothing open: it ends, saying so, and keeps nothing
    with pytest.raises(HandoverEnded):
        await join(cfg, show=shown.append, poll=0.1, hostname="SU-DEDICATED")
    assert cfg.client_id == ""
    await su.ok("handover.open", {})
    joining = asyncio.create_task(join(cfg, show=shown.append, poll=0.1, hostname="SU-DEDICATED"))
    for _ in range(100):
        status = await su.ok("handover.status", {})
        if status["waiting"]:
            break
        await asyncio.sleep(0.05)
    code = "".join(next(line for line in shown if "Code" in line).split("Code")[1].split())
    await su.ok("handover.confirm", {"enrollment_id": status["waiting"][0]["id"], "code": code})
    got = await asyncio.wait_for(joining, 10)
    assert got["account_id"] == org["su"]
    saved = LocalConfig.load(tmp_path / "operator.json")
    assert saved.client_id == got["client_id"] and saved.client_key == got["client_key"]            # written, for the console to sign in with
    # and a request nobody answers ends by itself
    await su.ok("handover.open", {})
    with pytest.raises(HandoverEnded):
        await join(LocalConfig(path=tmp_path / "other.json", engine_host="127.0.0.1", engine_port=engine.port, tls=False), show=shown.append,
                   poll=0.05, hostname="SU-LATE", give_up_after=0.5)
