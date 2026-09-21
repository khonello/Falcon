"""Phase 5: real authentication and TLS.

Key derivation, the challenge/response against a DB-backed Engine (wrong key, unknown client,
offboarded account, rekey), the DEV_BYPASS_AUTH switch, and a TLS handshake with a generated,
pinned self-signed certificate. The DB-backed parts skip without FALCON_TEST_DATABASE_URL."""

from __future__ import annotations

import asyncio
import os
import ssl
from pathlib import Path

import pytest

from common.connection import ConnectionError_, EngineConnection, EngineError
from engine import auth
from engine.config import Settings
from engine.master_secret import load_or_create
from engine.server import Engine
from tests.conftest import TEST_DB_URL, TEST_MASTER_SECRET, answer, key_for, requires_db


def test_key_derivation_is_deterministic_and_generation_bound():
    k1 = auth.derive_client_key(TEST_MASTER_SECRET, "cid-a1")
    assert k1 == auth.derive_client_key(TEST_MASTER_SECRET, "cid-a1", 1) and len(k1) == 32
    assert k1 != auth.derive_client_key(TEST_MASTER_SECRET, "cid-a1", 2)
    assert k1 != auth.derive_client_key(TEST_MASTER_SECRET, "cid-a2")
    assert k1 != auth.derive_client_key(b"x" * 32, "cid-a1")
    nonce = auth.new_nonce()
    assert auth.verify(TEST_MASTER_SECRET, "cid-a1", nonce, auth.expected_response(k1, nonce))
    assert not auth.verify(TEST_MASTER_SECRET, "cid-a1", nonce, auth.expected_response(k1, "other"))
    assert not auth.verify(TEST_MASTER_SECRET, "cid-a1", nonce, "")
    assert not auth.verify(None, "cid-a1", nonce, auth.expected_response(k1, nonce))


def test_master_secret_file_is_created_once(tmp_path: Path):
    p = tmp_path / "nested" / "master.secret"
    first = load_or_create(p)
    assert len(first) == 32 and p.exists()
    assert load_or_create(p) == first                      # stable across restarts
    if os.name != "nt":
        assert (p.stat().st_mode & 0o777) == 0o600           # owner-only where the Engine deploys


@requires_db
async def test_wrong_key_unknown_client_and_offboarded_are_refused(engine, org, connect):
    # right key -> identity
    ok = await connect("cid-a1")
    assert ok is not None

    async def attempt(client_id: str, hmac_value: str) -> str:
        reader, writer = await asyncio.open_connection("127.0.0.1", engine.port)
        from tests.conftest import Client

        c = Client(reader, writer)
        challenge = await c.recv()
        code = await c.err("auth.respond", {"client_id": client_id,
                                            "hmac": hmac_value if hmac_value != "@good" else answer(client_id, challenge.payload["nonce"])})
        await c.close()
        return code

    assert await attempt("cid-a1", "deadbeef") == "unauthenticated"           # wrong key
    assert await attempt("cid-a1", "") == "unauthenticated"                   # the old "stub" shape
    assert await attempt("cid-nobody", "@good") == "unauthenticated"          # never provisioned
    await engine.db.accounts.offboard(org["w2"])
    assert await attempt("cid-w2", "@good") == "unauthenticated"              # offboarded = revoked
    failures = [e for e in await engine.db.audit.recent(limit=50) if e["action_type"] == "auth.failed"]
    assert len(failures) >= 4 and all(e["target_id"] for e in failures)


@requires_db
async def test_provisioning_issues_a_key_and_rekey_rotates_it(engine, org, connect):
    su = await connect("cid-su")
    res = await su.ok("hierarchy.account_create", {"role": "worker", "hostname": "FIN-09", "department_id": org["fin"]})
    assert res["client_key"] == key_for(res["client_id"])
    assert len(bytes.fromhex(res["client_key"])) == 32

    # the new worker connects with that key through the real client code path
    w = EngineConnection("127.0.0.1", engine.port, client_id=res["client_id"], tls=False, derived_key=res["client_key"])
    ident = await w.connect()
    assert ident.role == "worker" and ident.pc_id == res["pc_id"]

    # rekey: old key stops verifying, the live connection is dropped, the new key works
    rk = await su.ok("hierarchy.pc_rekey", {"pc_id": res["pc_id"]})
    assert rk["key_generation"] == 2 and rk["client_key"] != res["client_key"]
    for _ in range(40):
        if not w.connected:
            break
        await asyncio.sleep(0.05)
    assert not w.connected
    await w.close()
    old = EngineConnection("127.0.0.1", engine.port, client_id=res["client_id"], tls=False, derived_key=res["client_key"])
    with pytest.raises(EngineError):
        await old.connect()
    await old.close()
    new = EngineConnection("127.0.0.1", engine.port, client_id=res["client_id"], tls=False, derived_key=rk["client_key"])
    assert (await new.connect()).pc_id == res["pc_id"]
    await new.close()

    # scope: an Admin may rekey PCs in their department only
    a2 = await connect("cid-a2")
    assert await a2.err("hierarchy.pc_rekey", {"pc_id": res["pc_id"]}) == "forbidden"


@requires_db
async def test_dev_bypass_auth_skips_the_handshake_but_still_resolves_identity(org):
    """The loud dev switch: no challenge, any hmac; identity still comes from the provisioned id."""
    eng = Engine(Settings(host="127.0.0.1", port=0, database_url=TEST_DB_URL, dev_plaintext=True,
                          dev_bypass_auth=True, master_secret=TEST_MASTER_SECRET))
    await eng.start()
    try:
        conn = EngineConnection("127.0.0.1", eng.port, client_id="cid-a1", tls=False, request_timeout=1.0)
        ident = await conn.connect()          # no key at all
        assert ident.role == "admin"
        await conn.close()
    finally:
        await eng.stop()


@requires_db
async def test_tls_with_pinned_self_signed_certificate(tmp_path: Path, org):
    from engine.tls import generate_self_signed

    cert, key = generate_self_signed("127.0.0.1,localhost", tmp_path)
    eng = Engine(Settings(host="127.0.0.1", port=0, database_url=TEST_DB_URL, tls_cert=cert, tls_key=key,
                          master_secret=TEST_MASTER_SECRET))
    await eng.start()
    try:
        pinned = EngineConnection("127.0.0.1", eng.port, client_id="cid-a1", tls=True, ca_cert=cert,
                                  derived_key=key_for("cid-a1"))
        assert (await pinned.connect()).role == "admin"
        tree = await pinned.call("hierarchy.tree")
        assert tree["departments"]
        await pinned.close()

        # no pinned cert -> the system trust store does not know this Engine -> fails loudly
        unpinned = EngineConnection("127.0.0.1", eng.port, client_id="cid-a1", tls=True, derived_key=key_for("cid-a1"))
        with pytest.raises(ssl.SSLCertVerificationError):
            await unpinned.connect()
        await unpinned.close()

        # a plaintext client against a TLS Engine cannot complete a handshake either
        plain = EngineConnection("127.0.0.1", eng.port, client_id="cid-a1", tls=False, derived_key=key_for("cid-a1"),
                                 request_timeout=1.5)
        with pytest.raises((OSError, EngineError, ConnectionError_, asyncio.TimeoutError)):
            await plain.connect()
        await plain.close()
    finally:
        await eng.stop()


def test_engine_refuses_to_start_without_tls_unless_dev_plaintext():
    eng = Engine(Settings(host="127.0.0.1", port=0, database_url=None, master_secret=TEST_MASTER_SECRET))
    with pytest.raises(SystemExit):
        eng._ssl_context()
