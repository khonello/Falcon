"""End-to-end scaffold smoke test: start the Engine on a loopback port (no DB, no TLS), speak
the protocol over a real socket, and confirm every registered handler answers."""

import asyncio

import pytest

from engine.config import Settings
from engine.dispatch import registered_types
from engine.server import Engine
from protocol import Kind, decode, encode, request
from tests.conftest import TEST_MASTER_SECRET, answer


class Client:
    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.reader, self.writer = reader, writer

    async def recv(self):
        return decode(await self.reader.readuntil(b"\n"))

    async def call(self, type_: str, payload: dict | None = None):
        env = request(type_, payload)
        self.writer.write(encode(env))
        await self.writer.drain()
        while True:
            msg = await self.recv()
            if msg.kind is Kind.RESPONSE and msg.id == env.id:
                return msg

    async def close(self):
        self.writer.close()
        await self.writer.wait_closed()


@pytest.fixture
async def engine(monkeypatch):
    monkeypatch.setenv("FALCON_TLS_CERT", "")
    settings = Settings(host="127.0.0.1", port=0, database_url=None, dev_plaintext=True,
                        master_secret=TEST_MASTER_SECRET)
    eng = Engine(settings)
    await eng.start()
    yield eng
    await eng.stop()


@pytest.fixture
async def client(engine):
    reader, writer = await asyncio.open_connection("127.0.0.1", engine.port)
    c = Client(reader, writer)
    yield c
    await c.close()


async def test_challenge_then_handshake(client):
    challenge = await client.recv()
    assert challenge.kind is Kind.PUSH and challenge.type == "auth.challenge"
    assert len(challenge.payload["nonce"]) == 64

    # Anything but auth.* / system.* is refused before the handshake completes.
    refused = await client.call("hierarchy.tree")
    assert refused.ok is False and refused.error["code"] == "unauthenticated"

    # A wrong answer is refused; the nonce is single-use, so the next attempt needs a new connection.
    bad = await client.call("auth.respond", {"client_id": "test-client", "hmac": "stub"})
    assert bad.ok is False and bad.error["code"] == "unauthenticated"
    again = await client.call("auth.respond", {"client_id": "test-client",
                                               "hmac": answer("test-client", challenge.payload["nonce"])})
    assert again.ok is False  # challenge already consumed


async def test_handshake_with_the_right_key(client):
    challenge = await client.recv()
    ok = await client.call("auth.respond", {"client_id": "test-client",
                                            "hmac": answer("test-client", challenge.payload["nonce"])})
    assert ok.ok is True and ok.result["authenticated"] is True


async def test_every_registered_type_dispatches(client):
    challenge = await client.recv()
    await client.call("auth.respond", {"client_id": "t", "hmac": answer("t", challenge.payload["nonce"])})
    for message_type in registered_types():
        if message_type == "auth.respond":
            continue
        resp = await client.call(message_type, {})
        assert resp.kind is Kind.RESPONSE, message_type
        # A stub result or a typed error (e.g. INVALID for missing fields) -- never INTERNAL.
        if not resp.ok:
            assert resp.error["code"] != "internal", (message_type, resp.error)


async def test_unknown_type_and_bad_json(client):
    challenge = await client.recv()
    await client.call("auth.respond", {"client_id": "t", "hmac": answer("t", challenge.payload["nonce"])})
    resp = await client.call("nope.nothing")
    assert resp.ok is False and resp.error["code"] == "unknown_type"

    client.writer.write(b"{garbage\n")
    await client.writer.drain()
    bad = await client.recv()
    assert bad.ok is False and bad.error["code"] == "bad_message"


async def test_dev_bypass_auth_skips_challenge():
    settings = Settings(host="127.0.0.1", port=0, dev_plaintext=True, dev_bypass_auth=True)
    eng = Engine(settings)
    await eng.start()
    try:
        reader, writer = await asyncio.open_connection("127.0.0.1", eng.port)
        c = Client(reader, writer)
        # No challenge arrives; the first thing we get back is our own response.
        resp = await c.call("system.ping")
        assert resp.ok and resp.result["pong"] is True
        await c.close()
    finally:
        await eng.stop()
