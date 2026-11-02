"""A file sent in a conversation (ENGINE-GAPS #7; engine/resource/chatfiles.py, worker_client/chatfiles.py)."""

from __future__ import annotations

import base64
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tests.conftest import requires_db

CONTENT = b"Q3 numbers, final. " * 1000


async def _answer_read(machine, push, data: bytes = CONTENT) -> dict:
    """What the sender's Worker does with chat.file_read: send the file in one piece."""
    return await machine.ok("chat.file_content", {"file_id": push.payload["file_id"], "index": 0, "total": 1,
                                                  "hash": hashlib.sha256(data).hexdigest(), "content_b64": base64.b64encode(data).decode("ascii")})


@requires_db
@pytest.mark.organisation
async def test_a_file_is_sent_held_saved_and_its_copy_knows_where_it_came_from(engine, org, connect):
    a1, w1 = await connect("cid-a1"), await connect("cid-w1")
    convo = (await a1.ok("chat.open", {"account_id": org["w1"]}))["conversation"]["conversation_id"]
    assert await a1.err("chat.send_file", {"conversation_id": convo, "path": "C:/Users/a1/tools/setup.exe"}) == "forbidden"
    sent = await a1.ok("chat.send_file", {"conversation_id": convo, "path": "C:/Users/a1/Documents/q3.xlsx"})
    assert sent["state"] == "reading"
    read = next(p for p in await a1.drain_pushes() if p.type == "chat.file_read")
    assert read.payload["path"] == "C:/Users/a1/Documents/q3.xlsx"
    assert (await _answer_read(a1, read))["held"] is True
    note = next(p for p in await w1.drain_pushes() if p.type == "chat.message")
    assert note.payload["file"]["name"] == "q3.xlsx" and note.payload["file"]["size"] == len(CONTENT)
    msg = (await w1.ok("chat.get", {"conversation_id": convo}))["messages"][-1]
    assert msg["file"]["state"] == "held" and msg["file"]["file_id"] == sent["file_id"]

    save = await w1.ok("chat.file_save", {"file_id": sent["file_id"]})
    deliver = next(p for p in await w1.drain_pushes() if p.type == "chat.file_deliver")
    assert base64.b64decode(deliver.payload["content_b64"]) == CONTENT and deliver.payload["save_id"] == save["save_id"]
    landed = "C:/Users/w1/Downloads/From Falcon/q3.xlsx"
    await w1.ok("chat.file_saved", {"save_id": save["save_id"], "path": landed, "hash": hashlib.sha256(CONTENT).hexdigest()})
    from engine.console.marks import came_by

    how = await came_by(engine.db, org["w1_pc"], landed, None)
    assert how["how"] == "conversation" and how["from_account_id"] == org["a1"]
    listed = (await a1.ok("chat.files", {"conversation_id": convo}))["files"][0]
    assert listed["state"] == "held" and listed["saved"][0]["path"] == landed

    # held 7 days at most: then the bytes are dropped and the record stays
    from engine.resource import chatfiles

    await engine.db.pool.execute("UPDATE chat_files SET expires_at = $2 WHERE id = $1", sent["file_id"], datetime.now(timezone.utc) - timedelta(minutes=1))
    assert await chatfiles.drop_expired(engine) == 1
    assert not (chatfiles.store(engine) / str(sent["file_id"])).exists()
    assert await w1.err("chat.file_save", {"file_id": sent["file_id"]}) == "conflict"
    assert (await engine.db.chat_files.get(sent["file_id"]))["state"] == "expired"


@requires_db
@pytest.mark.organisation
async def test_someone_elses_restricted_file_waits_for_their_yes_and_the_copy_is_then_allowed(engine, org, connect):
    a1, a2, w1 = await connect("cid-a1"), await connect("cid-a2"), await connect("cid-w1")
    path = "C:/Users/a1/Documents/salaries.xlsx"
    digest = hashlib.sha256(CONTENT).hexdigest()
    await engine.db.file_index.upsert(org["a1_pc"], path, "salaries.xlsx", digest, None, None, "event")
    mark = await engine.db.pool.fetchval(
        "INSERT INTO resource_marks (kind, name, pc_id, path, keep, by_account_id, department_id) VALUES ('file', 'salaries.xlsx', $1, $2, 'machine', $3, $4) RETURNING id",
        org["a1_pc"], path, org["a2"], org["fin"])
    assert mark
    convo = (await a1.ok("chat.open", {"account_id": org["w1"]}))["conversation"]["conversation_id"]
    sent = await a1.ok("chat.send_file", {"conversation_id": convo, "path": path})
    assert sent["state"] == "asked"                                               # A2 restricted it: A2 says
    assert "chat.file_read" not in a1.push_types(await a1.drain_pushes())
    asked = next(p for p in await a2.drain_pushes() if p.type == "chat.file_consent_request")
    assert asked.payload["file_id"] == sent["file_id"]
    assert await a1.err("chat.file_consent", {"file_id": sent["file_id"], "grant": True}) == "forbidden"
    await a2.ok("chat.file_consent", {"file_id": sent["file_id"], "grant": True})
    read = next(p for p in await a1.drain_pushes() if p.type == "chat.file_read")
    await _answer_read(a1, read)
    await w1.ok("chat.file_save", {"file_id": sent["file_id"]})
    assert await engine.db.resource.is_allowed(org["w1_pc"], "C:/Users/w1/Downloads/From Falcon/salaries.xlsx", digest)   # not a stray copy


def test_the_worker_saves_into_downloads_from_falcon_and_never_overwrites(tmp_path: Path):
    import asyncio

    from worker_client.chatfiles import ChatFiles

    said: list[tuple[str, dict]] = []

    async def report(t, p):
        said.append((t, p))
        return {}
    files = ChatFiles(report, downloads_dir=tmp_path)
    for save_id in (1, 2):
        asyncio.run(files.on_deliver({"save_id": save_id, "file_id": 9, "name": "q3.xlsx", "hash": hashlib.sha256(b"abc").hexdigest(),
                                      "index": 0, "total": 1, "content_b64": base64.b64encode(b"abc").decode("ascii")}))
    assert [Path(p["path"]).name for _, p in said] == ["q3.xlsx", "q3 (2).xlsx"]
    assert (tmp_path / "From Falcon" / "q3.xlsx").read_bytes() == b"abc"
    asyncio.run(files.on_deliver({"save_id": 3, "file_id": 9, "name": "run.bat", "index": 0, "total": 1, "content_b64": base64.b64encode(b"x").decode("ascii")}))
    assert said[-1][1].get("error")
