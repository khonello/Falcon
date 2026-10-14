"""A console that must not hold its machine's key asks the Worker service to answer the Engine's challenge (common/signpipe.py)."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import os
import sys
import time
import uuid

import pytest

from common import signpipe
from tests.conftest import key_for, requires_db

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="named pipes: Windows")


def expected(key: bytes, nonce: str) -> str:
    return hmac.new(key, nonce.encode(), hashlib.sha256).hexdigest()


def test_the_reply_is_the_challenge_signed_and_nothing_else_is_signed():
    key = b"k" * 32
    assert json.loads(signpipe.respond(key, b'{"nonce": "abc"}')) == {"hmac": expected(key, "abc")}
    assert json.loads(signpipe.respond(key, b'{"whoami": true}', "pc-7")) == {"client_id": "pc-7"}
    for bad in (b"not json", b"{}", b'{"nonce": ""}', json.dumps({"nonce": "x" * 300}).encode(), b"[1]"):
        assert "error" in json.loads(signpipe.respond(key, bad))                       # nothing odd is ever signed
    assert b"k" * 32 not in signpipe.respond(key, b'{"nonce": "abc"}')              # and the key is never in an answer


@pytest.fixture
def pipe():
    name = rf"\\.\pipe\FalconSignTest{uuid.uuid4().hex[:8]}"
    key = os.urandom(32)
    server = signpipe.SignPipeServer(key, name=name, client_id="cid-test")
    assert server.start()
    for _ in range(50):
        if os.path.exists(name):
            break
        time.sleep(0.05)
    yield name, key, server
    server.stop()


@windows_only
def test_a_console_gets_its_challenge_signed_over_a_real_pipe(pipe):
    name, key, server = pipe
    assert signpipe.sign("a-nonce", name=name) == expected(key, "a-nonce")
    assert signpipe.sign("another", name=name) == expected(key, "another")           # one pipe serves many, one after another
    assert signpipe.whoami(name=name) == "cid-test"
    with pytest.raises(OSError):
        signpipe.sign("x" * 300, name=name)                                          # refused, not signed
    assert server.served >= 3 and server.error is None


@windows_only
def test_a_client_that_connects_and_says_nothing_does_not_hold_the_pipe(pipe):
    name, key, server = pipe
    with open(name, "r+b", buffering=0):                                              # says nothing
        try:
            got = signpipe.sign("still-works", name=name)                                # others are served meanwhile
        except OSError as exc:
            raise AssertionError(f"not served while one client was silent: {exc!r}; server.error={server.error}; served={server.served}") from exc
        assert got == expected(key, "still-works")
        time.sleep(signpipe.CLIENT_SECONDS + 0.5)                                    # and it is let go
    assert signpipe.sign("after", name=name) == expected(key, "after")


@windows_only
def test_with_no_service_there_is_nothing_to_ask():
    with pytest.raises(OSError):
        signpipe.sign("n", name=r"\\.\pipe\FalconNobodyHome", seconds=0.2)
    assert not signpipe.available(r"\\.\pipe\FalconNobodyHome")


@windows_only
def test_the_config_takes_its_address_from_the_machine_and_its_id_from_the_service(pipe, tmp_path, monkeypatch):
    from operator_client.core.config import LocalConfig, machine_defaults

    name, key, _ = pipe
    machine = tmp_path / "ProgramData" / "Falcon"
    machine.mkdir(parents=True)
    (machine / "console.json").write_text(json.dumps({"engine_host": "falcon.internal", "engine_port": 7400, "tls": True,
                                                      "ca_cert": "C:/ProgramData/Falcon/engine.crt", "signer": "pipe",
                                                      "client_key": "must-be-ignored"}), encoding="utf-8")
    monkeypatch.setenv("PROGRAMDATA", str(tmp_path / "ProgramData"))
    monkeypatch.setattr(signpipe, "PIPE_NAME", name)
    assert "client_key" not in machine_defaults()
    cfg = LocalConfig.load(tmp_path / "nobody" / "operator.json")                     # this person has no file of their own
    assert (cfg.engine_host, cfg.signer, cfg.client_id, cfg.client_key) == ("falcon.internal", "pipe", "cid-test", "")
    assert cfg.signer_fn()("n") == expected(key, "n")
    # a person's own file wins over what the machine says
    own = tmp_path / "me" / "operator.json"
    own.parent.mkdir()
    own.write_text(json.dumps({"engine_host": "mine.example", "client_key": "ab" * 32, "client_id": "me"}), encoding="utf-8")
    cfg = LocalConfig.load(own)
    assert cfg.engine_host == "mine.example" and cfg.signer_fn() is None              # a key of its own: it signs itself


@windows_only
@requires_db
async def test_the_engine_accepts_a_console_signed_for_by_the_service(engine, org, pipe):
    from common.connection import ConnectionError_, EngineConnection, EngineError

    name, _, _ = pipe
    key = bytes.fromhex(key_for("cid-a1").hex()) if isinstance(key_for("cid-a1"), bytes) else bytes.fromhex(key_for("cid-a1"))
    server = signpipe.SignPipeServer(key, name=name + "x", client_id="cid-a1")
    assert server.start()
    try:
        for _ in range(50):
            if os.path.exists(name + "x"):
                break
            await asyncio.sleep(0.05)
        conn = EngineConnection("127.0.0.1", engine.port, client_id="cid-a1", tls=False, derived_key=None,
                                signer=lambda nonce: signpipe.sign(nonce, name=name + "x"))
        ident = await conn.connect()                                                   # no key in this process at all
        assert ident.role == "admin" and ident.account_id == org["a1"]
        await conn.close()
        bad = EngineConnection("127.0.0.1", engine.port, client_id="cid-a1", tls=False, derived_key=None,
                               signer=lambda nonce: signpipe.sign(nonce, name=r"\\.\pipe\FalconNobodyHome", seconds=0.1))
        with pytest.raises((EngineError, ConnectionError_)):                              # nobody to sign: the Engine refuses
            await bad.connect()
        await bad.close()
    finally:
        server.stop()
