"""Machines asking to be registered (ENGINE-GAPS #15): a request, never a grant; paired by a code on the machine's own
screen; the key goes only to the machine that asked, once."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone

import pytest

from common.connection import EngineConnection, EngineError
from engine.hierarchy import enrollment
from tests.conftest import requires_db

pytestmark = requires_db


async def _machine(engine) -> EngineConnection:
    """A machine with no key: connected, never authenticated."""
    m = EngineConnection("127.0.0.1", engine.port, client_id="", tls=False)
    await m.open()
    return m


async def _ask(m: EngineConnection, **kw) -> dict:
    return await m.call("enroll.request", {"hostname": "NEW-PC", "os": "Windows 11", "mac": "aa:bb:cc:dd:ee:ff", **kw})


async def _record(into: list[str], type_: str, payload: dict) -> None:
    into.append(type_)


async def test_a_new_machine_asks_and_a_person_confirms_with_the_code_on_its_screen(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    a2 = await connect("cid-a2")
    pushed: list[str] = []
    m = await _machine(engine)
    m.on_push(lambda t, p: _record(pushed, t, p))
    try:
        # a machine with no key may ask and collect, and nothing else
        for forbidden in ("reports.list", "enroll.list"):
            with pytest.raises(EngineError) as no:
                await m.call(forbidden)
            assert no.value.code == "unauthenticated"

        asked = await _ask(m, department_id=org["fin"])
        assert len(asked["code"]) == 4 and asked["code"].isdigit() and asked["token"]
        assert (await m.call("enroll.wait", {"token": asked["token"]}))["status"] == "pending"
        # the Super User and the department's Admin are told; another department's Admin is not
        assert "enroll.requested" in su.push_types(await su.drain_pushes())
        assert "enroll.requested" in a1.push_types(await a1.drain_pushes())
        assert a2.push_types(await a2.drain_pushes()) == []

        # the waiting list: no code in it (it is on the machine's screen), scoped by department
        waiting = (await a1.ok("enroll.list"))["requests"]
        assert [(r["hostname"], r["requested_department_name"]) for r in waiting] == [("NEW-PC", "Finance")]
        assert "code" not in waiting[0] and "token_hash" not in waiting[0]
        assert (await a2.ok("enroll.list"))["requests"] == [] and len((await su.ok("enroll.list"))["requests"]) == 1
        eid = asked["enrollment_id"]

        # the wrong code is refused and counted; another department's Admin cannot see the request at all
        wrong = "0000" if asked["code"] != "0000" else "1111"
        assert await a1.err("enroll.confirm", {"enrollment_id": eid, "code": wrong}) == "invalid"
        assert await a2.err("enroll.confirm", {"enrollment_id": eid, "code": asked["code"]}) == "not_found"
        assert await a2.err("enroll.refuse", {"enrollment_id": eid}) == "not_found"

        done = await a1.ok("enroll.confirm", {"enrollment_id": eid, "code": asked["code"]})
        assert done["status"] == "confirmed" and done["role"] == "worker"
        assert "client_key" not in done                                           # the confirmer is never given the key
        for _ in range(30):
            if "enroll.decided" in pushed:
                break
            await asyncio.sleep(0.1)
        assert "enroll.decided" in pushed                                         # the machine is nudged to collect

        got = await m.call("enroll.wait", {"token": asked["token"]})
        assert got["status"] == "confirmed" and got["client_id"] and got["client_key"]
        assert (await m.call("enroll.wait", {"token": asked["token"]}))["status"] == "collected"   # the key, once

        # and the machine is now a real one: it connects with that key as a Worker of Finance
        real = EngineConnection("127.0.0.1", engine.port, client_id=got["client_id"], tls=False,
                                derived_key=got["client_key"], hostname="NEW-PC")
        ident = await real.connect()
        assert ident.role == "worker" and ident.department_id == org["fin"] and ident.pc_id == got["pc_id"]
        await real.close()
        kinds = [e["action_type"] for e in (await su.ok("audit.recent", {"limit": 30}))["entries"]]
        assert {"enroll.requested", "enroll.confirmed", "enroll.collected"} <= set(kinds)
        assert (await su.ok("enroll.list"))["requests"] == []
        assert await a1.err("enroll.confirm", {"enrollment_id": eid, "code": asked["code"]}) == "conflict"
    finally:
        await m.close()


async def test_who_may_confirm_what_and_how_a_request_ends_otherwise(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    machines = []
    try:
        # an Admin workstation is not an Admin's call to make
        m1 = await _machine(engine)
        machines.append(m1)
        wants_admin = await _ask(m1, department_id=org["fin"], level="admin")
        assert await a1.err("enroll.confirm", {"enrollment_id": wants_admin["enrollment_id"],
                                               "code": wants_admin["code"]}) == "forbidden"
        ok = await su.ok("enroll.confirm", {"enrollment_id": wants_admin["enrollment_id"], "code": wants_admin["code"]})
        assert ok["role"] == "admin"

        # a machine that named no department: an Admin does not see it, the Super User must say which
        m2 = await _machine(engine)
        machines.append(m2)
        nameless = await _ask(m2)
        assert (await a1.ok("enroll.list"))["requests"] == []
        assert await su.err("enroll.confirm", {"enrollment_id": nameless["enrollment_id"], "code": nameless["code"]}) == "invalid"
        done = await su.ok("enroll.confirm", {"enrollment_id": nameless["enrollment_id"], "code": nameless["code"],
                                              "department_id": org["hr"]})
        assert done["department_id"] == org["hr"]

        # refusing: the machine learns it
        m3 = await _machine(engine)
        machines.append(m3)
        r3 = await _ask(m3, department_id=org["fin"])
        await a1.ok("enroll.refuse", {"enrollment_id": r3["enrollment_id"], "reason": "not one of ours"})
        refused = await m3.call("enroll.wait", {"token": r3["token"]})
        assert refused["status"] == "refused" and refused["reason"] == "not one of ours"

        # five wrong codes refuse it for good
        m4 = await _machine(engine)
        machines.append(m4)
        r4 = await _ask(m4, department_id=org["fin"])
        wrong = "0000" if r4["code"] != "0000" else "1111"
        for _ in range(4):
            assert await a1.err("enroll.confirm", {"enrollment_id": r4["enrollment_id"], "code": wrong}) == "invalid"
        assert await a1.err("enroll.confirm", {"enrollment_id": r4["enrollment_id"], "code": wrong}) == "forbidden"
        assert (await m4.call("enroll.wait", {"token": r4["token"]}))["status"] == "refused"

        # a request that waits too long expires, and can no longer be confirmed
        m5 = await _machine(engine)
        machines.append(m5)
        r5 = await _ask(m5, department_id=org["fin"])
        await engine.db.pool.execute("UPDATE enrollments SET expires_at = $2 WHERE id = $1", r5["enrollment_id"],
                                     datetime.now(timezone.utc) - timedelta(minutes=1))
        assert await enrollment.expire(engine) == 1
        assert (await m5.call("enroll.wait", {"token": r5["token"]}))["status"] == "expired"
        assert await a1.err("enroll.confirm", {"enrollment_id": r5["enrollment_id"], "code": r5["code"]}) == "conflict"
        with pytest.raises(EngineError) as unknown:
            await m5.call("enroll.wait", {"token": "not-a-token"})
        assert unknown.value.code == "not_found"
    finally:
        for m in machines:
            await m.close()


async def test_one_address_cannot_flood_the_waiting_list(engine, org):
    machines = []
    try:
        for i in range(enrollment.MAX_PENDING_PER_ADDRESS):
            m = await _machine(engine)
            machines.append(m)
            await m.call("enroll.request", {"hostname": f"PC-{i}"})
        extra = await _machine(engine)
        machines.append(extra)
        with pytest.raises(EngineError) as err:
            await extra.call("enroll.request", {"hostname": "PC-X"})
        assert err.value.code == "conflict"
        with pytest.raises(EngineError) as blank:
            await extra.call("enroll.request", {"hostname": "  "})
        assert blank.value.code == "invalid"
        with pytest.raises(EngineError) as level:
            await extra.call("enroll.request", {"hostname": "PC-Y", "level": "super_user"})
        assert level.value.code == "invalid"
    finally:
        for m in machines:
            await m.close()
