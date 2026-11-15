"""The Engine's certificate renews itself with a rollover (engine/certs.py; docs/SEATS-AND-SETUP.md section 10): on a real TLS Engine, a
machine pinned to the current certificate is given the next one, and keeps connecting after the Engine switches to it."""

from __future__ import annotations

import ssl
from pathlib import Path

import pytest

from common.connection import EngineConnection
from engine.config import Settings
from engine.server import Engine
from tests.conftest import TEST_DB_URL, TEST_MASTER_SECRET, key_for, requires_db

pytestmark = requires_db


async def _until(cond, tries: int = 100) -> bool:
    import asyncio

    for _ in range(tries):
        if cond():
            return True
        await asyncio.sleep(0.05)
    return False


async def test_a_machine_is_given_the_next_certificate_and_keeps_connecting_after_the_switch(tmp_path: Path, org):
    pytest.importorskip("cryptography")
    from engine.tls import generate_self_signed
    from worker_client.service import trust_next_certificate

    cert, key = generate_self_signed("127.0.0.1,localhost", tmp_path / "data", valid_days=40)       # 40 days left: inside the 60
    pinned = tmp_path / "machine" / "engine.crt"
    pinned.parent.mkdir()
    pinned.write_bytes(cert.read_bytes())                                                            # what the machine was installed with
    eng = Engine(Settings(host="127.0.0.1", port=0, database_url=TEST_DB_URL, tls_cert=cert, tls_key=key, master_secret=TEST_MASTER_SECRET))
    await eng.start()
    try:
        given: list[str] = []
        m = EngineConnection("127.0.0.1", eng.port, client_id="cid-a1", tls=True, ca_cert=pinned, derived_key=key_for("cid-a1"))

        async def on_push(type_, payload):
            if type_ == "engine.next_certificate":
                given.append(payload["pem"])
                trust_next_certificate(str(pinned), payload["pem"])

        m.on_push(on_push)
        await m.connect()
        assert (await m.call("cert.status"))["next"] is None
        await eng.certs.daily()                                                                       # the daily check: 40 days left
        assert eng.certs.next_pem() is not None and await _until(lambda: bool(given))
        assert pinned.read_text(encoding="ascii").count("BEGIN CERTIFICATE") == 2                    # trusts both now
        trust_next_certificate(str(pinned), given[0])
        assert pinned.read_text(encoding="ascii").count("BEGIN CERTIFICATE") == 2                    # given twice, kept once
        await m.close()

        # a machine away when it was given out is given it as it signs in
        late_file = tmp_path / "late.crt"
        late_file.write_bytes(cert.read_bytes())
        late_given: list[str] = []
        late = EngineConnection("127.0.0.1", eng.port, client_id="cid-a1", tls=True, ca_cert=late_file, derived_key=key_for("cid-a1"))

        async def on_late(type_, payload):
            if type_ == "engine.next_certificate":
                late_given.append(payload["pem"])

        late.on_push(on_late)
        await late.connect()
        assert await _until(lambda: bool(late_given))
        await late.close()

        old = cert.read_bytes()
        status = await eng.certs.switch()
        assert cert.read_bytes() != old and (tmp_path / "data" / "engine-old.crt").read_bytes() == old and status["next"] is None
        again = EngineConnection("127.0.0.1", eng.port, client_id="cid-a1", tls=True, ca_cert=pinned, derived_key=key_for("cid-a1"))
        assert (await again.connect()).role == "admin"                                               # served the new one, still trusted
        await again.close()
        only_old = tmp_path / "only-old.crt"
        only_old.write_bytes(old)
        stale = EngineConnection("127.0.0.1", eng.port, client_id="cid-a1", tls=True, ca_cert=only_old, derived_key=key_for("cid-a1"))
        with pytest.raises(ssl.SSLCertVerificationError):
            await stale.connect()                                                                     # never given it: the zip is run again
        await stale.close()
    finally:
        await eng.stop()


async def test_renewing_with_other_names_and_a_switch_with_nothing_to_switch_to(tmp_path: Path, org):
    pytest.importorskip("cryptography")
    from engine.certs import describe
    from engine.tls import generate_self_signed
    from protocol import ProtocolError

    cert, key = generate_self_signed("127.0.0.1,localhost", tmp_path / "data")                      # ten years: nothing to do yet
    eng = Engine(Settings(host="127.0.0.1", port=0, database_url=TEST_DB_URL, tls_cert=cert, tls_key=key, master_secret=TEST_MASTER_SECRET))
    await eng.start()
    try:
        await eng.certs.daily()
        assert eng.certs.next_pem() is None
        with pytest.raises(ProtocolError, match="no next certificate"):
            await eng.certs.switch()
        await eng.certs.renew(["falcon.internal", "127.0.0.1"])
        assert describe(eng.certs.next_pem())["names"] == ["falcon.internal", "127.0.0.1"]
        acts = [e["action_type"] for e in await eng.db.audit.recent(limit=20)]
        assert "cert.next_made" in acts
    finally:
        await eng.stop()
