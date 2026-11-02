"""A machine joins with a code from the licence that was bought, and nobody confirms it (the user, 2 Nov 2026; engine/hierarchy/licences.py)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from common.connection import EngineConnection
from tests.conftest import requires_db

pytestmark = [requires_db, pytest.mark.organisation]

LICENCE = {"name": "Falcon, 25 machines", "reference": "ORD-2026-0042",
           "codes": [{"code": "ADMN-7Q4K-2W9X-1111", "role": "admin", "seats": 1},
                     {"code": "WRKR-5T8M-3Z6P-2222", "role": "worker", "seats": 2, "department": "Sales"},
                     {"code": "WRKR-OLD0-OLD0-3333", "role": "worker", "seats": 5, "expires_at": "2020-01-01T00:00:00Z"}]}


async def _machine(engine) -> EngineConnection:
    m = EngineConnection("127.0.0.1", engine.port, client_id="", tls=False)               # no key yet: it only asks
    await m.open()
    return m


async def _ask(engine, code: str, level: str = "worker", host: str = "NEW-PC") -> tuple[EngineConnection, dict]:
    m = await _machine(engine)
    return m, await m.call("enroll.request", {"hostname": host, "os": "Windows 11", "level": level, "licence_code": code})


async def test_a_machine_joins_with_its_licence_code_and_nobody_confirms_it(engine, org, connect):
    a1 = await connect("cid-a1")
    got = await a1.ok("licence.import", LICENCE)
    assert got["added"] == 3 and got["already_known"] == 0
    assert (await a1.ok("licence.import", {**LICENCE, "name": "again"}))["already_known"] == 3     # a code is held once

    machines = []
    try:
        # a worker code, typed the way people type (lower case, spaces): it joins at once, as a worker, in the code's department
        m, asked = await _ask(engine, "wrkr 5t8m 3z6p 2222", host="SALES-01")
        machines.append(m)
        assert asked["status"] == "confirmed"
        key = await m.call("enroll.wait", {"token": asked["token"]})
        assert key["status"] == "confirmed" and key["client_id"] and key["client_key"]
        account = await engine.db.accounts.by_id(key["account_id"])
        assert account["role"] == "worker" and account["department_name"] == "Sales"

        # an admin code makes an IT Admin's workstation, in IT
        m, asked = await _ask(engine, "ADMN-7Q4K-2W9X-1111", level="admin", host="IT-02")
        machines.append(m)
        admin = await engine.db.accounts.by_id(asked and (await m.call("enroll.wait", {"token": asked["token"]}))["account_id"])
        assert admin["role"] == "admin" and admin["department_name"] == "IT"

        # what a code is for is what the machine becomes: a worker code does not make an Admin, nor an admin code a worker
        m = await _machine(engine)
        machines.append(m)
        for code, level in (("WRKR-5T8M-3Z6P-2222", "admin"), ("ADMN-7Q4K-2W9X-1111", "worker")):
            try:
                await m.call("enroll.request", {"hostname": "X", "level": level, "licence_code": code})
                raise AssertionError("a code for the other role was taken")
            except Exception as exc:                                                        # noqa: BLE001
                assert "code" in str(exc)
        # seats run out; an expired code and a withdrawn one let nobody in
        m, asked = await _ask(engine, "WRKR-5T8M-3Z6P-2222", host="SALES-02")
        machines.append(m)
        assert asked["status"] == "confirmed"
        for code, word in (("WRKR-5T8M-3Z6P-2222", "no machines left"), ("WRKR-OLD0-OLD0-3333", "expired")):
            try:
                await _ask(engine, code, host="SALES-03")
                raise AssertionError("let in")
            except Exception as exc:                                                        # noqa: BLE001
                assert word in str(exc)

        listed = (await a1.ok("licence.list"))["codes"]
        sales = next(c for c in listed if c["last4"] == "2222")
        assert sales["used"] == 2 and sales["left"] == 0 and [x["hostname"] for x in sales["machines"]] == ["SALES-01", "SALES-02"]
        assert "WRKR" not in json.dumps(listed) and "code_hash" not in json.dumps(listed)         # only ever the last four
        await a1.ok("licence.revoke", {"code_id": next(c["id"] for c in listed if c["last4"] == "1111")})
        try:
            await _ask(engine, "ADMN-7Q4K-2W9X-1111", level="admin", host="IT-03")
            raise AssertionError("a withdrawn code let a machine in")
        except Exception as exc:                                                            # noqa: BLE001
            assert "withdrawn" in str(exc)
        kinds = [r["action_type"] for r in await engine.db.pool.fetch("SELECT action_type FROM audit_log WHERE action_type LIKE 'licence.%' "
                                                                       "OR action_type = 'enroll.licensed' ORDER BY id")]
        assert kinds.count("enroll.licensed") == 3 and "licence.imported" in kinds and "licence.revoked" in kinds
    finally:
        for m in machines:
            await m.close()


async def test_guessing_codes_is_slow_and_a_worker_cannot_import_a_licence(engine, org, connect):
    w1 = await connect("cid-w1")
    assert await w1.err("licence.import", LICENCE) == "forbidden"
    m = await _machine(engine)
    try:
        for i in range(5):
            try:
                await m.call("enroll.request", {"hostname": "GUESS", "licence_code": f"GUESS{i:04d}XYZ"})
            except Exception as exc:                                                        # noqa: BLE001
                assert "not a licence code" in str(exc)
        try:
            await m.call("enroll.request", {"hostname": "GUESS", "licence_code": "ANOTHER-GUESS"})
            raise AssertionError("a sixth guess was looked at")
        except Exception as exc:                                                            # noqa: BLE001
            assert "too many wrong licence codes" in str(exc)
    finally:
        await m.close()


async def test_the_worker_joins_with_the_code_it_was_installed_with_and_does_not_keep_it(engine, org, connect, tmp_path: Path):
    from worker_client.config import WorkerConfig
    from worker_client.enroll import enroll

    a1 = await connect("cid-a1")
    await a1.ok("licence.import", {"name": "one", "codes": [{"code": "WRKR-AAAA-BBBB-4444", "role": "worker"}]})
    cfg = WorkerConfig(path=tmp_path / "worker.json", engine_host="127.0.0.1", engine_port=engine.port, tls=False, enroll_code="WRKR-AAAA-BBBB-4444")
    shown: list[str] = []
    got = await enroll(cfg, show=shown.append, poll=0.2, hostname="OPS-30")
    assert got["status"] == "confirmed" and cfg.client_id and cfg.client_key
    assert cfg.enroll_code == "" and "WRKR" not in (tmp_path / "worker.json").read_text(encoding="utf-8")    # used, and not kept here
    assert any("licence code" in s for s in shown) and not any("Code " in s for s in shown)              # no code to show anyone
