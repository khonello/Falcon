"""One event's reads (engine/database.py, `Database.event_reads`): a plain SELECT asked again within one file event is answered from the first,
and nothing a stage writes is ever hidden from the stages after it. Measured 13 Nov 2026: 21.6 statements an event without it, 15.6 with."""

from __future__ import annotations

import asyncio

from tests.conftest import requires_db

pytestmark = requires_db


async def _pc(db, name: str) -> int:
    return await db.accounts.create_pc(name, None, "client_pc", f"cid-{name}")


async def test_a_lookup_asked_twice_in_one_event_is_read_once_and_a_write_is_seen_at_once(db, monkeypatch):
    import asyncpg

    pc = await _pc(db, "WS-1")
    asked: list[str] = []
    real = asyncpg.pool.Pool.fetchrow

    async def counted(self, sql, *args, **kw):
        asked.append(sql)
        return await real(self, sql, *args, **kw)

    monkeypatch.setattr(asyncpg.pool.Pool, "fetchrow", counted)
    with db.event_reads():
        first = await db.accounts.pc(pc)
        first["hostname"] = "changed by a caller"                         # a caller changing what it got changes nothing kept
        again = await db.accounts.pc(pc)
        assert len(asked) == 1 and again["hostname"] == "WS-1"
        await db.accounts.rename_pc(pc, "WS-1b")
        assert (await db.accounts.pc(pc))["hostname"] == "WS-1b"            # a write forgets what was read: the next stage reads it
        assert len(asked) == 2
    await db.accounts.pc(pc)
    assert len(asked) == 3                                                # outside an event, every read is read


async def test_a_task_started_inside_an_event_reads_the_database_itself(db):
    pc = await _pc(db, "WS-2")
    with db.event_reads():
        await db.accounts.pc(pc)
        await db._pool.execute("UPDATE pcs SET hostname = 'WS-2b' WHERE id = $1", pc)     # written behind the event's back (another machine's event)
        seen = await asyncio.create_task(db.accounts.pc(pc))                             # a task of its own: not this event's reads
        assert seen["hostname"] == "WS-2b"
