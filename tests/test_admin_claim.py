"""An Admin's PC comes in with a claim the store signed: the Admin setup signs in, the store issues the claim, the service knocks with it
and is in at once (docs/SEATS-AND-SETUP.md section 5; installers/windows/store_signin.py, engine/hierarchy/seats.py). Run end to end against
the store stub, with the real sign-in code (PKCE, loopback)."""

from __future__ import annotations

import asyncio
import json
import secrets
import socket
import urllib.request

import pytest

from common.connection import EngineConnection, EngineError
from tests.conftest import requires_db

pytestmark = requires_db


def _browser(url: str) -> None:
    """The person signing in: the stub signs them in at once and redirects to the setup's loopback callback."""
    urllib.request.urlopen(url, timeout=10).read()


def _api(store, method: str, path: str, body: dict | None = None, token: str | None = None) -> dict:
    req = urllib.request.Request(store.url + path, data=json.dumps(body).encode() if body is not None else None, method=method,
                                 headers={"Content-Type": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})})
    with urllib.request.urlopen(req, timeout=10) as r:
        return json.loads(r.read().decode() or "{}")


@pytest.fixture
def store(monkeypatch, tmp_path):
    pytest.importorskip("cryptography")
    monkeypatch.setenv("FALCON_STORE_TEST_KEY", "1")
    from scripts.store_stub import StoreStub

    s = StoreStub(state=tmp_path / "store.json").start()
    yield s
    s.stop()


async def _registered(engine, store, admin_seats: int) -> dict:
    """The Engine registered with the store (what the Engine setup does, step 5), with Admin seats bought."""
    from installers.windows.store_signin import sign_in

    token = await asyncio.to_thread(sign_in, store.url, open_browser=_browser)
    cid = (await asyncio.to_thread(_api, store, "POST", "/api/companies", {"name": "Acme"}, token))["company_id"]
    got = await asyncio.to_thread(_api, store, "POST", f"/api/companies/{cid}/engines",
                                  {"names": ["127.0.0.1"], "port": engine.port, "certificate": "-----BEGIN CERTIFICATE-----\nx\n-----END CERTIFICATE-----"}, token)
    engine.store.identity = {"store_url": store.url, "engine_id": got["engine_id"], "engine_token": got["engine_token"]}
    in_use = await engine.db.seats.in_use("admin")
    if in_use + admin_seats:                                                                  # (a grant is never of 0 seats)
        await asyncio.to_thread(_api, store, "POST", "/_test/grants", {"engine_id": got["engine_id"], "role": "admin", "seats": in_use + admin_seats})
    await asyncio.to_thread(_api, store, "POST", "/_test/grants", {"engine_id": got["engine_id"], "role": "worker", "seats": 50})
    assert await engine.store.fetch_grants() == (2 if in_use + admin_seats else 1)
    return got


def _worker_cfg(engine, tmp_path, claim):
    from worker_client.config import WorkerConfig

    return WorkerConfig(engine_host="127.0.0.1", engine_port=engine.port, tls=False, windows=False, serve_console=True,
                        admin_claim=str(claim), path=tmp_path / "private" / "worker.json")


async def test_the_admin_setup_signs_in_claims_a_seat_and_the_pc_is_in_as_an_admin_at_once(engine, org, connect, store, tmp_path):
    from installers.windows.store_signin import run
    from worker_client.config import WorkerConfig
    from worker_client.knock import knock

    reg = await _registered(engine, store, admin_seats=1)
    said: list[str] = []
    got = await asyncio.to_thread(run, store.url, tmp_path / "private", open_browser=_browser, say=said.append)
    assert got["engine_id"] == reg["engine_id"] and got["claim"].exists() and got["company"].exists()
    assert any("owner@test.local" in s for s in said)
    claim_env = json.loads(got["claim"].read_text(encoding="utf-8"))
    cfg = _worker_cfg(engine, tmp_path, got["claim"])
    assert await asyncio.wait_for(knock(cfg, asyncio.Event(), ladder=(0.2,)), 15) is True        # in at once: nobody had to give a seat
    assert not got["claim"].exists() and cfg.admin_claim == ""                                     # spent, and not kept
    saved = WorkerConfig.load(cfg.path)
    me = EngineConnection("127.0.0.1", engine.port, client_id=saved.client_id, tls=False, derived_key=saved.client_key, hostname=socket.gethostname())
    try:
        ident = await me.connect()
        assert ident.role == "admin"
    finally:
        await me.close()
    a1 = await connect("cid-a1")
    claimed = [e for e in await engine.db.audit.recent(limit=50) if e["action_type"] == "seat.claimed"]
    detail = claimed[0]["detail"] if isinstance(claimed[0]["detail"], dict) else json.loads(claimed[0]["detail"])
    assert detail["member_email"] == "owner@test.local"                                         # who signed in to the store is on record
    assert (await a1.ok("seats.summary"))["admin"]["free"] == 0
    # the same claim, copied to another PC (another install), is refused: a claim works once
    other = EngineConnection("127.0.0.1", engine.port, client_id="", tls=False)
    await other.open()
    try:
        with pytest.raises(EngineError, match="used already"):
            await other.call("knock.hello", {"install_token": secrets.token_urlsafe(24), "hostname": socket.gethostname(),
                                             "hardware_id": claim_env["doc"]["hardware_id"], "admin_claim": claim_env})
    finally:
        await other.close()


async def test_a_claim_is_refused_if_changed_for_another_engine_or_machine_or_with_no_admin_seat_free(engine, org, store, tmp_path):
    from scripts.store_stub import now_iso, sign

    reg = await _registered(engine, store, admin_seats=1)
    host = socket.gethostname()

    def claim(**over) -> dict:
        doc = {"kind": "admin_claim", "claim_id": "a_" + secrets.token_hex(4), "company_id": "c_1", "engine_id": reg["engine_id"],
               "member_email": "kofi@acme.test", "hostname": host, "hardware_id": "hw-1", "issued_at": now_iso(), "expires_at": now_iso(600)}
        return sign({**doc, **over})

    m = EngineConnection("127.0.0.1", engine.port, client_id="", tls=False)
    await m.open()

    async def knock_with(env, name: str = host) -> dict:
        return await m.call("knock.hello", {"install_token": secrets.token_urlsafe(24), "hostname": name, "hardware_id": "hw-1", "admin_claim": env})

    try:
        tampered = claim()
        tampered["doc"]["member_email"] = "mallory@evil.test"
        for env, said in ((tampered, "cannot be trusted"), (claim(engine_id="e_other"), "another Engine"),
                          (claim(expires_at=now_iso(-60)), "expired"), (claim(hostname="SOMEONE-ELSE"), "another machine"),
                          (claim(hardware_id="hw-2"), "another machine")):
            with pytest.raises(EngineError, match=said):
                await knock_with(env)
        assert (await knock_with(claim()))["status"] == "seated"                                  # the one free Admin seat
        with pytest.raises(EngineError, match="no Admin seat is free"):
            await knock_with(claim())
    finally:
        await m.close()
    rows = await engine.db.seats.knocks(None)
    assert sum(1 for r in rows if r["status"] == "seated") == 1                                    # the refused claims let nobody in


async def test_an_engine_not_registered_with_the_store_takes_no_claim(engine, org, monkeypatch):
    pytest.importorskip("cryptography")
    monkeypatch.setenv("FALCON_STORE_TEST_KEY", "1")
    from scripts.store_stub import now_iso, sign

    env = sign({"kind": "admin_claim", "claim_id": "a_1", "company_id": "c_1", "engine_id": "e_1", "member_email": "kofi@acme.test",
                "hostname": "IT-02", "hardware_id": "", "issued_at": now_iso(), "expires_at": now_iso(600)})
    m = EngineConnection("127.0.0.1", engine.port, client_id="", tls=False)
    await m.open()
    try:
        with pytest.raises(EngineError, match="another Engine"):
            await m.call("knock.hello", {"install_token": secrets.token_urlsafe(24), "hostname": "IT-02", "admin_claim": env})
    finally:
        await m.close()


async def test_a_claim_that_finds_no_free_seat_asks_the_store_first_for_seats_just_bought(engine, org, store, tmp_path):
    from installers.windows.store_signin import run
    from worker_client.knock import knock

    reg = await _registered(engine, store, admin_seats=0)                                       # every Admin seat is in use
    await asyncio.to_thread(_api, store, "POST", "/_test/grants", {"engine_id": reg["engine_id"], "role": "admin", "seats": 1})   # bought now
    got = await asyncio.to_thread(run, store.url, tmp_path / "private", open_browser=_browser, say=lambda m: None)   # the Engine has not asked
    cfg = _worker_cfg(engine, tmp_path, got["claim"])
    assert await asyncio.wait_for(knock(cfg, asyncio.Event(), ladder=(0.2,)), 15) is True        # not refused: the Engine asked the store


async def test_the_console_is_given_the_company_file_for_the_worker_setup_zip(engine, org, connect, store, tmp_path, monkeypatch):
    from common import signed

    a1 = await connect("cid-a1")
    assert await a1.err("company.file") == "conflict"                                         # not registered: there is none
    reg = await _registered(engine, store, admin_seats=1)
    monkeypatch.setattr(type(engine.store), "path", property(lambda self: tmp_path / "store.json"))
    (tmp_path / "company.falcon").write_text(json.dumps(reg["company"]), encoding="utf-8")
    got = await a1.ok("company.file")
    assert got["file_name"] == "acme.falcon" and got["port"] == engine.port and got["certificates"] == 1
    assert signed.check(got["envelope"], "company")["engine_id"] == reg["engine_id"]          # exactly as the store signed it
