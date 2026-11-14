"""Machines knock; Admins give seats (engine/hierarchy/seats.py, engine/store.py; docs/SEATS-AND-SETUP.md sections 6 and 7)."""

from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

import pytest

from common.connection import EngineConnection, EngineError
from engine.hierarchy import seats
from engine.store import add_grants
from tests.conftest import requires_db

pytestmark = requires_db

ENGINE_ID = "e_test"


async def _knocker(engine) -> EngineConnection:
    m = EngineConnection("127.0.0.1", engine.port, client_id="", tls=False)
    await m.open()
    return m


async def _knock(m: EngineConnection, token: str, name: str = "FIN-07", **facts) -> dict:
    return await m.call("knock.hello", {"install_token": token, "hostname": name, "os": "Windows 11", "mac": "aa:bb:cc:00:00:07",
                                        "hardware_id": facts.pop("hardware_id", f"hw-{name}"), "user": "ama", **facts})


def _registered(engine, monkeypatch) -> None:
    monkeypatch.setenv("FALCON_STORE_TEST_KEY", "1")
    engine.store.identity = {"store_url": "http://127.0.0.1:9", "engine_id": ENGINE_ID, "engine_token": "t"}


def _grant(role: str, n: int, start: datetime, end: datetime, engine_id: str = ENGINE_ID) -> dict:
    pytest.importorskip("cryptography")
    from scripts.store_stub import sign

    iso = lambda d: d.strftime("%Y-%m-%dT%H:%M:%SZ")
    return sign({"kind": "grant", "grant_id": "g_" + secrets.token_hex(4), "company_id": "c_1", "engine_id": engine_id, "role": role, "seats": n,
                 "valid_from": iso(start), "valid_until": iso(end), "paddle_ref": "sub_1", "issued_at": iso(start)})


async def test_a_pc_knocks_is_seen_is_given_a_seat_signs_in_and_loses_it_when_taken_back(engine, org, connect):
    a1 = await connect("cid-a1")
    m = await _knocker(engine)
    token = secrets.token_urlsafe(24)
    try:
        assert (await _knock(m, token))["status"] == "waiting"
        assert (await _knock(m, token, user="kojo"))["status"] == "waiting"                  # one row per installed PC, kept up to date
        waiting = (await a1.ok("knocks.list"))["knocks"]
        assert len(waiting) == 1 and waiting[0]["hostname"] == "FIN-07" and waiting[0]["signed_in_user"] == "kojo" and waiting[0]["knocks"] == 2
        assert "knock.waiting" in a1.push_types(await a1.drain_pushes())
        # departments exist: one must be chosen
        assert await a1.err("seat.give", {"knock_id": waiting[0]["id"]}) == "invalid"
        given = await a1.ok("seat.give", {"knock_id": waiting[0]["id"], "department_id": org["fin"]})
        got = await _knock(m, token)
        assert got["status"] == "seated" and got["pc_id"] == given["pc_id"]
        assert (await _knock(m, token))["status"] == "collected"                            # the key once per seating
    finally:
        await m.close()
    w = EngineConnection("127.0.0.1", engine.port, client_id=got["client_id"], tls=False, derived_key=got["client_key"], hostname="FIN-07")
    ident = await w.connect()
    assert ident.role == "worker" and ident.pc_id == got["pc_id"] and ident.department_id == org["fin"]
    assert (await a1.ok("knocks.list"))["knocks"] == []
    await a1.ok("seat.take", {"pc_id": got["pc_id"]})
    old = EngineConnection("127.0.0.1", engine.port, client_id=got["client_id"], tls=False, derived_key=got["client_key"], hostname="FIN-07")
    with pytest.raises(EngineError) as refused:
        await old.connect()
    assert refused.value.code == "no_seat"                                                 # it knows to knock again
    stranger = EngineConnection("127.0.0.1", engine.port, client_id=got["client_id"], tls=False, derived_key="00" * 32)
    with pytest.raises(EngineError) as plain:
        await stranger.connect()
    assert plain.value.code == "unauthenticated"                                           # without the key, nothing is said about seats
    for c in (w, old, stranger):
        await c.close()
    m = await _knocker(engine)
    try:
        assert (await _knock(m, token))["status"] == "waiting"                             # the same installed PC, knocking again
        again = (await a1.ok("knocks.list"))["knocks"][0]
        await a1.ok("seat.give", {"knock_id": again["id"], "department_id": org["hr"]})
        second = await _knock(m, token)
        assert second["pc_id"] == got["pc_id"] and second["client_key"] != got["client_key"]   # its own machine again, never its old key
    finally:
        await m.close()


async def test_seats_are_counted_from_signed_grants_and_none_are_given_beyond_them(engine, org, connect, monkeypatch):
    a1 = await connect("cid-a1")
    now = datetime.now(timezone.utc)
    assert (await a1.ok("seats.summary"))["worker"]["free"] is None                      # not registered: no limit (development)
    _registered(engine, monkeypatch)
    assert await add_grants(engine, [_grant("worker", 1, now - timedelta(days=1), now + timedelta(days=300))]) == 1
    forged = _grant("worker", 50, now - timedelta(days=1), now + timedelta(days=300))
    forged["doc"]["seats"] = 500
    other = _grant("worker", 50, now - timedelta(days=1), now + timedelta(days=300), engine_id="e_someone_else")
    assert await add_grants(engine, [forged, other]) == 0                                 # changed, or for another Engine: refused
    summary = await a1.ok("seats.summary")
    assert summary["registered"] and summary["worker"]["bought"] == 1 and summary["worker"]["free"] == 1
    m = await _knocker(engine)
    try:
        await _knock(m, secrets.token_urlsafe(24), "FIN-08")
        await _knock(m, secrets.token_urlsafe(24), "FIN-09")
        k8, k9 = (await a1.ok("knocks.list"))["knocks"]
        await a1.ok("seat.give", {"knock_id": k8["id"], "department_id": org["fin"]})
        assert await a1.err("seat.give", {"knock_id": k9["id"], "department_id": org["fin"]}) == "conflict"     # no seat free
    finally:
        await m.close()


async def test_look_alikes_are_flagged_and_one_address_cannot_flood_the_list(engine, org, connect, monkeypatch):
    a1 = await connect("cid-a1")
    m = await _knocker(engine)
    try:
        await _knock(m, secrets.token_urlsafe(24), "FIN-02", hardware_id="hw-1")
        await _knock(m, secrets.token_urlsafe(24), "FIN-02", hardware_id="hw-2")                     # the same name
        await _knock(m, secrets.token_urlsafe(24), "LAPTOP-X", hardware_id="hw-1")                   # the same hardware, another name
        flags = {k["hostname"] + "/" + k["hardware_id"]: k["look_alike"] for k in (await a1.ok("knocks.list"))["knocks"]}
        assert any("also called FIN-02" in f for f in flags["FIN-02/hw-1"]) and any("same hardware as FIN-02" in f for f in flags["LAPTOP-X/hw-1"])
        monkeypatch.setattr(seats, "NEW_PER_ADDRESS", 3)
        with pytest.raises(EngineError) as flood:
            await _knock(m, secrets.token_urlsafe(24), "FIN-99")
        assert flood.value.code == "conflict"
    finally:
        await m.close()


async def test_with_no_department_at_all_a_seated_machine_goes_into_new_machines(engine):
    """(An Admin always belongs to a department, so this is an Engine with none yet.)"""
    assert await engine.db.accounts.list_departments() == []
    dept = await seats._department(engine, None)
    assert {d["id"]: d["name"] for d in await engine.db.accounts.list_departments()}[dept] == "New machines"


async def test_the_last_admin_seat_is_never_taken_back(engine, org, connect):
    a1 = await connect("cid-a1")
    from engine.hierarchy.accounts import provision

    made = await provision(engine, "admin", org["fin"], "IT-09")
    assert await engine.db.seats.in_use("admin") == 1
    assert await a1.err("seat.take", {"pc_id": made["pc_id"]}) == "forbidden"


async def test_a_period_warns_then_grace_then_the_newest_seats_over_the_count_go(engine, org, connect, monkeypatch):
    _registered(engine, monkeypatch)
    now = datetime.now(timezone.utc)
    from engine.hierarchy.accounts import provision

    pcs = [(await provision(engine, "worker", org["fin"], f"FIN-{i}"))["pc_id"] for i in range(3)]
    await add_grants(engine, [_grant("worker", 2, now - timedelta(days=400), now - timedelta(days=8)),      # ended, and past its grace
                              _grant("worker", 1, now - timedelta(days=10), now + timedelta(days=20))])     # ends in 20 days
    taken = await seats.watch_periods(engine, now)
    assert taken == 2 and await engine.db.seats.in_use("worker") == 1
    assert await engine.db.seats.active(pcs[0]) is not None                                # the oldest kept, the newest two taken back
    assert await engine.db.seats.active(pcs[1]) is None and await engine.db.seats.active(pcs[2]) is None
    titles = [i["title"] for i in await engine.db.issues.list(type_="seats")]
    assert any("1 Worker seats end on" in t for t in titles)                               # 20 days left: the 30-day warning
    assert await seats.watch_periods(engine, now) == 0                                     # (and asked again, nothing more is taken)
    assert len(await engine.db.issues.list(type_="seats")) == len(titles)                   # nor raised twice


async def test_the_tui_lists_knocks_gives_and_takes_back_a_seat(engine, org, tmp_path):
    from operator_client.tui.shell import run_script
    from tests.test_operator_client import _cfg

    m = await _knocker(engine)
    try:
        await _knock(m, secrets.token_urlsafe(24), "FIN-11")
    finally:
        await m.close()
    knock_id = (await engine.db.seats.knocks())[0]["id"]
    out = "\n".join(await run_script(_cfg(engine, tmp_path, "cid-a1"), ["connect", "seats", "knocks", f"seat give {knock_id} {org['fin']}"]))
    assert "not registered with the store" in out and "FIN-11" in out and "has a Worker seat" in out
    pc_id = (await engine.db.seats.get_knock(knock_id))["pc_id"]
    out = "\n".join(await run_script(_cfg(engine, tmp_path, "cid-a1"), ["connect", f"seat take {pc_id}", "knocks"]))
    assert "taken back" in out and "FIN-11" in out
