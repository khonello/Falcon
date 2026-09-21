"""Shared fixtures.

Database-backed tests need a *dedicated* test database (they drop and recreate the public
schema) -- never point this at the dev database:

    $env:FALCON_TEST_DATABASE_URL = "postgresql://falcon:falcon@localhost:5432/falcon_test"

Without it, DB tests are skipped and the rest of the suite still runs.
"""

from __future__ import annotations

import asyncio
import os
from typing import Any

import pytest

from engine.config import Settings
from engine.database import Database
from engine.server import Engine
from protocol import Envelope, Kind, decode, encode, request

TEST_DB_URL = os.environ.get("FALCON_TEST_DATABASE_URL")

requires_db = pytest.mark.skipif(not TEST_DB_URL, reason="FALCON_TEST_DATABASE_URL not set")


async def _wipe_and_migrate(database: Database) -> None:
    async with database.pool.acquire() as conn:
        await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    await database.migrate()


@pytest.fixture
async def db() -> Database:
    """A connected Database on a freshly wiped + migrated schema."""
    assert TEST_DB_URL
    database = Database(TEST_DB_URL)
    await database.connect()
    await _wipe_and_migrate(database)
    try:
        yield database
    finally:
        await database.close()


# --- a live Engine on the test database ---------------------------------------------------------

class Client:
    """Minimal protocol client: sends requests, collects pushes, matches responses by id."""

    def __init__(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        self.reader, self.writer = reader, writer
        self.pushes: list[Envelope] = []

    async def recv(self) -> Envelope:
        return decode(await asyncio.wait_for(self.reader.readuntil(b"\n"), 5))

    async def call(self, type_: str, payload: dict[str, Any] | None = None) -> Envelope:
        env = request(type_, payload)
        self.writer.write(encode(env))
        await self.writer.drain()
        while True:
            msg = await self.recv()
            if msg.kind is Kind.RESPONSE and msg.id == env.id:
                return msg
            if msg.kind is Kind.PUSH:
                self.pushes.append(msg)

    async def ok(self, type_: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        resp = await self.call(type_, payload)
        assert resp.ok, (type_, resp.error)
        return resp.result or {}

    async def err(self, type_: str, payload: dict[str, Any] | None = None) -> str:
        resp = await self.call(type_, payload)
        assert not resp.ok, (type_, resp.result)
        return resp.error["code"]

    async def drain_pushes(self, wait: float = 0.15) -> list[Envelope]:
        """Collect pushes that arrive within `wait` seconds."""
        try:
            while True:
                msg = await asyncio.wait_for(self.recv(), wait)
                if msg.kind is Kind.PUSH:
                    self.pushes.append(msg)
        except asyncio.TimeoutError:
            pass
        out, self.pushes = self.pushes, []
        return out

    def push_types(self, pushes: list[Envelope]) -> list[str]:
        return [p.type for p in pushes if p.type]

    async def close(self) -> None:
        self.writer.close()
        try:
            await self.writer.wait_closed()
        except ConnectionError:
            pass


@pytest.fixture
async def engine() -> Engine:
    """An Engine listening on loopback (plaintext, auth stubbed) against a fresh test DB."""
    assert TEST_DB_URL
    eng = Engine(Settings(host="127.0.0.1", port=0, database_url=TEST_DB_URL, dev_plaintext=True))
    await eng.db.connect()
    await _wipe_and_migrate(eng.db)
    await eng.db.close()
    await eng.start()
    try:
        yield eng
    finally:
        await eng.stop()


@pytest.fixture
async def connect(engine: Engine):
    """connect(client_id, hostname=None) -> authenticated Client. Closes all on teardown."""
    clients: list[Client] = []

    async def _connect(client_id: str, hostname: str | None = None) -> Client:
        reader, writer = await asyncio.open_connection("127.0.0.1", engine.port)
        c = Client(reader, writer)
        challenge = await c.recv()
        assert challenge.type == "auth.challenge"
        await c.ok("auth.respond", {"client_id": client_id, "hmac": "stub", "hostname": hostname})
        clients.append(c)
        return c

    yield _connect
    for c in clients:
        await c.close()
    await asyncio.sleep(0.05)  # let the Engine process disconnects before teardown


async def seed_org(db: Database) -> dict[str, int]:
    """Super User; Finance (Admin A1 + Workers W1, W2); HR (Admin A2). client ids: cid-<key>."""
    acc = db.accounts
    su = await acc.create("super_user", None, None)
    fin = await acc.create_department("Finance", su)
    hr = await acc.create_department("HR", su)
    su_pc = await acc.create_pc("SU-PC", None, "super_user_workstation", "cid-su")
    a1_pc = await acc.create_pc("FIN-ADM", fin, "admin_workstation", "cid-a1")
    w1_pc = await acc.create_pc("FIN-01", fin, "client_pc", "cid-w1")
    w2_pc = await acc.create_pc("FIN-02", fin, "client_pc", "cid-w2")
    a2_pc = await acc.create_pc("HR-ADM", hr, "admin_workstation", "cid-a2")
    await db.pool.execute("UPDATE accounts SET bound_pc_id = $1 WHERE id = $2", su_pc, su)
    a1 = await acc.create("admin", fin, a1_pc)
    w1 = await acc.create("worker", fin, w1_pc)
    w2 = await acc.create("worker", fin, w2_pc)
    a2 = await acc.create("admin", hr, a2_pc)
    return {"su": su, "fin": fin, "hr": hr, "a1": a1, "w1": w1, "w2": w2, "a2": a2,
            "su_pc": su_pc, "a1_pc": a1_pc, "w1_pc": w1_pc, "w2_pc": w2_pc, "a2_pc": a2_pc}


@pytest.fixture
async def org(engine: Engine) -> dict[str, int]:
    return await seed_org(engine.db)
