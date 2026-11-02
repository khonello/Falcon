"""A file sent in a conversation (ENGINE-GAPS #7; the user, 22-23 Oct and 2 Nov 2026).

Anyone in a conversation sends one file from their own machine, once, up to 100 MB. It arrives as a message with the file, and each person in
the conversation saves it -- their machine puts it in Downloads\\From Falcon. There is no step to ask for a file: people ask in a message.

    chat.send_file    {conversation_id, path}      -> {file_id, state: reading | asked}       from the sender's own machine
    chat.file_consent {file_id, grant}             -> the person who restricted it says yes or no (asked)
    chat.file_save    {file_id}                    -> {save_id}: the file is sent to the caller's machine, which saves it
    chat.files        {conversation_id}            -> the files sent in it, with who saved them where
    from the machines: chat.file_content {file_id, index, total, hash, content_b64} | {file_id, error}  (the sender's, answering chat.file_read)
                       chat.file_saved {save_id, path, hash} | {save_id, error}                         (a receiver's, answering chat.file_deliver)

Sending is intentional access, and what it means is decided before anything moves:
  * refused: programs and scripts (a script runs as a Custom Action, where it is checked first), and anything over 100 MB (a Flow carries that);
  * restricted (a mark, a restricted or admin tier, or a copy of marked content): sending is the consent of the person who restricted it, for
    that one copy; anyone else's file waits until that person (for a tier, any IT Admin) says yes. An admin-tier file may go to a Worker (the
    user, 2 Nov 2026). Each copy saved is allowed where it lands, so Restricted does not catch it as a stray copy;
  * every step is in the audit trail, and every saved copy is recorded with where it came from (`chat_file_saves`), which is how Restricted and
    Detective tell a handed-over copy from a stray one.
The Engine holds the bytes on its own disk (beside its data) until they are saved, 7 days at most, then drops them; the record stays.
A Private tag (ENGINE-GAPS #3), when it is built, adds the receiver to who may open the file.
"""

from __future__ import annotations

import base64
import hashlib
import logging
import os
from datetime import datetime, timedelta, timezone
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler
from engine.permissions import int_field, org_wide, require_account, str_field
from engine.serialize import rows
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

MAX_BYTES = 100 * 1024 * 1024
HOLD = timedelta(days=7)
CHUNK_BYTES = 512 * 1024
REFUSED = frozenset({".exe", ".msi", ".bat", ".cmd", ".ps1", ".py", ".vbs", ".js", ".com", ".scr", ".psm1", ".wsf", ".jar", ".lnk"})


def store(engine: Engine) -> Path:
    """Where the Engine holds files on their way (beside its own data, never in the database)."""
    folder = Path(engine.settings.secret_path).parent / "chat-files"
    folder.mkdir(parents=True, exist_ok=True)
    return folder


def _name_of(path: str) -> str:
    return (PureWindowsPath(path).name if "\\" in path or ":" in path else PurePosixPath(path).name) or path


def _size_words(n: int | None) -> str:
    if n is None:
        return "size not known yet"
    return f"{n / 1048576:.1f} MB" if n >= 1048576 else f"{max(1, n // 1024)} KB"


async def _conversation(ctx: Context, conversation_id: int) -> tuple[dict[str, Any], list[int]]:
    from engine.resource.conversations import _in

    return await _in(ctx, conversation_id)


@handler("chat.send_file")
async def send_file(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_account(ctx)
    convo, _members = await _conversation(ctx, int_field(payload, "conversation_id"))
    if ident.pc_id is None:
        raise ProtocolError(ErrorCode.INVALID, "a file is sent from your own machine")
    path = str_field(payload, "path").strip()
    name = _name_of(path)
    ext = os.path.splitext(name)[1].lower()
    if ext in REFUSED:
        raise ProtocolError(ErrorCode.FORBIDDEN, "programs and scripts are not sent in a conversation: a script runs as a Custom Action, where it is checked first")
    db = ctx.engine.db
    entry = await db.file_index.by_path(ident.pc_id, path)
    size = (entry or {}).get("size_bytes")
    if size is not None and size > MAX_BYTES:
        raise ProtocolError(ErrorCode.INVALID, "a file over 100 MB goes by a Flow, not in a conversation")
    from engine.flow import guard

    found = await guard.blockers(ctx.engine, ident.pc_id, path, (entry or {}).get("content_hash"))
    restricted = None
    consent_by: int | None = None
    needs_yes = False
    if found:
        mine = [b for b in found if (b.kind == "mark" and b.owner_account_id == ident.account_id) or (b.kind == "tag" and org_wide(ident))]
        others = [b for b in found if b not in mine]
        restricted = {"reasons": [b.reason for b in found], "mark_ids": [b.mark_id for b in found if b.mark_id],
                      "consented_by": ident.account_id if not others else None}
        if others:
            needs_yes = True
            owner = next((b.owner_account_id for b in others if b.kind == "mark" and b.owner_account_id), None)
            consent_by = owner                                      # None: a restricted or admin tier, which any IT Admin may answer
    file_id = await db.chat_files.create(convo["id"], ident.account_id, ident.pc_id, path, name, size, "asked" if needs_yes else "reading",
                                         restricted=restricted, consent_account_id=consent_by)
    await ctx.engine.audit.record(ctx, "chat.file_offered", target_type="chat_files", target_id=file_id, pc_id=ident.pc_id,
                                  detail={"conversation_id": convo["id"], "name": name, "restricted": restricted, "waits_for": consent_by})
    if needs_yes:
        await _ask_owner(ctx.engine, file_id, consent_by, ident.account_id, name, restricted)
        return {"file_id": file_id, "state": "asked", "waits_for": "the person who restricted it" if consent_by else "an IT Admin"}
    await ctx.engine.push_to_pc(ident.pc_id, "chat.file_read", {"file_id": file_id, "path": path, "max_bytes": MAX_BYTES})
    return {"file_id": file_id, "state": "reading"}


async def _ask_owner(engine: Engine, file_id: int, owner: int | None, sender: int, name: str, restricted: dict[str, Any] | None) -> None:
    targets = [owner] if owner else [a["id"] for a in await engine.db.accounts.active_admins() if a["id"] != sender]
    for t in targets:
        who = (await engine.db.accounts.display_names_for(t, [sender])).get(sender)
        await engine.push_to_account(t, "chat.file_consent_request", {"file_id": file_id, "name": name, "from_account_id": sender, "from": who,
                                                                      "why": (restricted or {}).get("reasons", [])})


@handler("chat.file_consent")
async def file_consent(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_account(ctx)
    db = ctx.engine.db
    f = await db.chat_files.get(int_field(payload, "file_id"))
    if f is None or f["state"] != "asked":
        raise ProtocolError(ErrorCode.NOT_FOUND, "no file waiting for an answer with that id")
    may = f["consent_account_id"] == ident.account_id if f["consent_account_id"] else (ident.role == "admin" and org_wide(ident))
    if not may:
        raise ProtocolError(ErrorCode.FORBIDDEN, "only the person who restricted it can answer")
    grant = payload.get("grant")
    if not isinstance(grant, bool):
        raise ProtocolError(ErrorCode.INVALID, "grant is true or false")
    restricted = dict(f["restricted"] or {})
    if grant:
        restricted["consented_by"] = ident.account_id
        await db.chat_files.set_state(f["id"], "reading")
        await db.pool.execute("UPDATE chat_files SET restricted = $2 WHERE id = $1", f["id"], restricted)
        await ctx.engine.push_to_pc(f["from_pc_id"], "chat.file_read", {"file_id": f["id"], "path": f["source_path"], "max_bytes": MAX_BYTES})
    else:
        await db.chat_files.set_state(f["id"], "refused", "the person who restricted it said no")
        await ctx.engine.push_to_account(f["from_account_id"], "chat.file_refused", {"file_id": f["id"], "name": f["name"],
                                                                                     "why": "the person who restricted it said no"})
    await ctx.engine.audit.record(ctx, "chat.file_consent", target_type="chat_files", target_id=f["id"], detail={"granted": grant})
    return {"file_id": f["id"], "granted": grant}


@handler("chat.file_content")
async def file_content(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """The sender's machine sends the file, in pieces; the last one makes it a message in the conversation."""
    ident = require_account(ctx)
    db = ctx.engine.db
    f = await db.chat_files.get(int_field(payload, "file_id"))
    if f is None or f["from_pc_id"] != ident.pc_id or f["state"] != "reading":
        raise ProtocolError(ErrorCode.NOT_FOUND, "no file is being read from this machine with that id")
    if payload.get("error"):
        why = {"too_big": "it is over 100 MB (a Flow carries that)", "refused": "programs and scripts are not sent"}.get(str(payload["error"]),
                                                                                                                         "the machine could not read it")
        await db.chat_files.set_state(f["id"], "refused", why)
        await ctx.engine.push_to_account(f["from_account_id"], "chat.file_refused", {"file_id": f["id"], "name": f["name"], "why": why})
        return {"accepted": False}
    try:
        index, total = int(payload["index"]), int(payload["total"])
        piece = base64.b64decode(str(payload.get("content_b64") or ""))
    except (KeyError, TypeError, ValueError) as exc:
        raise ProtocolError(ErrorCode.INVALID, "a piece needs index, total and content") from exc
    if not 0 <= index < total or total * CHUNK_BYTES > MAX_BYTES + CHUNK_BYTES:
        raise ProtocolError(ErrorCode.INVALID, "piece out of range")
    part = store(ctx.engine) / f"{f['id']}.part"
    with part.open("r+b" if part.exists() else "wb") as out:
        out.seek(index * CHUNK_BYTES)
        out.write(piece)
    pieces = store(ctx.engine) / f"{f['id']}.pieces"
    got = set(pieces.read_text(encoding="utf-8").split()) if pieces.exists() else set()
    got.add(str(index))
    pieces.write_text(" ".join(sorted(got, key=int)), encoding="utf-8")
    if len(got) < total:
        return {"accepted": True, "waiting": total - len(got)}
    data = part.read_bytes()
    digest = hashlib.sha256(data).hexdigest()
    if payload.get("hash") and payload["hash"] != digest or len(data) > MAX_BYTES:
        await db.chat_files.set_state(f["id"], "refused", "it did not arrive whole")
        part.unlink(missing_ok=True)
        pieces.unlink(missing_ok=True)
        return {"accepted": False}
    held = store(ctx.engine) / str(f["id"])
    os.replace(part, held)
    pieces.unlink(missing_ok=True)
    body = f"Sent a file: {f['name']} ({_size_words(len(data))})"
    msg = await db.conversations.add(f["conversation_id"], f["from_account_id"], body, chat_file_id=f["id"])
    await db.chat_files.held(f["id"], digest, len(data), datetime.now(timezone.utc) + HOLD, msg["id"])
    await ctx.engine.audit.record(ctx, "chat.file_sent", target_type="chat_files", target_id=f["id"], pc_id=ident.pc_id,
                                  detail={"conversation_id": f["conversation_id"], "name": f["name"], "bytes": len(data), "hash": digest})
    from engine.resource.conversations import _members

    convo = await db.conversations.get(f["conversation_id"])
    for p in await _members(ctx, convo):
        name = (await db.accounts.display_names_for(p, [f["from_account_id"]])).get(f["from_account_id"])
        await ctx.engine.push_to_account(p, "chat.message", {"conversation_id": f["conversation_id"], "message_id": msg["id"],
                                                             "from_account_id": f["from_account_id"], "from": name, "body": body,
                                                             "at": msg["sent_at"].isoformat(),
                                                             "file": {"file_id": f["id"], "name": f["name"], "size": len(data)}})
    return {"accepted": True, "held": True, "message_id": msg["id"]}


@handler("chat.file_save")
async def file_save(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Save a file sent in a conversation onto the caller's own machine (Downloads\\From Falcon)."""
    ident = require_account(ctx)
    db = ctx.engine.db
    f = await db.chat_files.get(int_field(payload, "file_id"))
    if f is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such file")
    await _conversation(ctx, f["conversation_id"])                              # only someone in the conversation
    if f["state"] == "expired":
        raise ProtocolError(ErrorCode.CONFLICT, "it was held for 7 days and is gone: ask for it again")
    if f["state"] != "held":
        raise ProtocolError(ErrorCode.CONFLICT, "it has not arrived yet")
    if ident.pc_id is None:
        raise ProtocolError(ErrorCode.INVALID, "a file is saved onto your own machine")
    if ident.pc_id not in ctx.engine.online_pc_ids():
        raise ProtocolError(ErrorCode.CONFLICT, "your machine is not connected: save it once it is")
    save_id = await db.chat_files.ask_save(f["id"], ident.account_id, ident.pc_id)
    restricted = f["restricted"] or {}
    if restricted:
        # the consent was for this file to go to the people in the conversation: wherever it lands on this machine, it is allowed there
        for mark_id in restricted.get("mark_ids") or [None]:
            await db.resource.allow(ident.pc_id, "Downloads/From Falcon/" + f["name"], f["content_hash"], restricted.get("consented_by") or f["from_account_id"],
                                    f"handed over in a conversation (file {f['id']})", mark_id)
    data = (store(ctx.engine) / str(f["id"])).read_bytes()
    total = max(1, (len(data) + CHUNK_BYTES - 1) // CHUNK_BYTES)
    for index in range(total):
        await ctx.engine.push_to_pc(ident.pc_id, "chat.file_deliver", {
            "save_id": save_id, "file_id": f["id"], "name": f["name"], "hash": f["content_hash"], "index": index, "total": total,
            "content_b64": base64.b64encode(data[index * CHUNK_BYTES:(index + 1) * CHUNK_BYTES]).decode("ascii")})
    await ctx.engine.audit.record(ctx, "chat.file_save_asked", target_type="chat_files", target_id=f["id"], pc_id=ident.pc_id,
                                  detail={"save_id": save_id})
    return {"save_id": save_id, "file_id": f["id"]}


@handler("chat.file_saved")
async def file_saved(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_account(ctx)
    db = ctx.engine.db
    save = await db.chat_files.save(int_field(payload, "save_id"))
    if save is None or save["pc_id"] != ident.pc_id:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such save for this machine")
    if payload.get("error"):
        await ctx.engine.audit.record(ctx, "chat.file_save_failed", target_type="chat_files", target_id=save["chat_file_id"], pc_id=ident.pc_id,
                                      detail={"save_id": save["id"], "error": str(payload["error"])[:200]})
        await ctx.engine.push_to_account(save["account_id"], "chat.file_save_failed", {"file_id": save["chat_file_id"], "why": str(payload["error"])[:200]})
        return {"recorded": True}
    path = str_field(payload, "path")
    done = await db.chat_files.saved(save["id"], path, str(payload.get("hash") or "") or None)
    await ctx.engine.audit.record(ctx, "chat.file_saved", target_type="chat_files", target_id=save["chat_file_id"], pc_id=ident.pc_id,
                                  detail={"save_id": save["id"], "path": path})
    await ctx.engine.push_to_account(save["account_id"], "chat.file_saved", {"file_id": save["chat_file_id"], "path": path})
    return {"recorded": done is not None}


@handler("chat.files")
async def files(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    convo, _members = await _conversation(ctx, int_field(payload, "conversation_id"))
    db = ctx.engine.db
    out = rows(await db.pool.fetch("SELECT id, message_id, from_account_id, name, size_bytes, state, reason, created_at, held_at, expires_at "
                                   "FROM chat_files WHERE conversation_id = $1 ORDER BY id", convo["id"]))
    for f in out:
        f["saved"] = [{"account_id": s["account_id"], "machine": s["hostname"], "path": s["path"], "at": s["saved_at"].isoformat() if s["saved_at"] else None}
                      for s in await db.chat_files.saves(f["id"])]
    return {"files": out}


async def drop_expired(engine: Engine) -> int:
    """Scheduler: files held for 7 days are dropped from the Engine's disk; their record stays (state expired)."""
    if not engine.db.connected:
        return 0
    gone = await engine.db.chat_files.expire_due()
    for f in gone:
        (store(engine) / str(f["id"])).unlink(missing_ok=True)
    if gone:
        await engine.audit.record(None, "chat.files_dropped", target_type="chat_files", target_id=gone[0]["id"], detail={"ids": [f["id"] for f in gone]})
    return len(gone)
