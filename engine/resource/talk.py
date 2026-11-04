"""A request to talk (ENGINE-GAPS #19, #23; decided 2 Nov 2026: part of Messages only).

A person at a machine sends one line ("Ask IT"). Every IT Admin sees it. One Admin accepts it, and the conversation opens with that line in it; or an Admin
closes it with a reason the person reads. One open request per person.

    chat.ask            {line}                    the person at a machine; every Admin is pushed `chat.request`
    chat.requests       {}                        Admin: what is waiting, oldest first: {requests: [{id, from, account_id, host, at, line}]}
    chat.request_accept {request_id}              Admin: -> {conversation}; the person is pushed `chat.request_accepted`
    chat.request_close  {request_id, why}         Admin: the person is pushed `chat.request_closed` with the reason
"""

from __future__ import annotations

from typing import Any

from engine.dispatch import Context, handler
from engine.permissions import int_field, require_account, require_role, str_field
from engine.resource.conversations import _views
from protocol import ErrorCode, ProtocolError

LINE_MAX = 300


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


async def _gone(ctx: Context, request_id: int) -> None:
    await ctx.engine.push_to_role("admin", "chat.request_gone", {"request_id": request_id})


async def _open(ctx: Context, request_id: int) -> dict[str, Any]:
    found = await ctx.engine.db.conversations.talk_request(request_id)
    if found is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such request")
    if found["state"] != "open":
        raise ProtocolError(ErrorCode.CONFLICT, "another Admin has already answered this request")
    return found


@handler("chat.ask")
async def chat_ask(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_account(ctx)
    line = " ".join(str(payload.get("line") or "").split())
    if not line or len(line) > LINE_MAX:
        raise ProtocolError(ErrorCode.INVALID, f"say what it is about, in 1 to {LINE_MAX} characters")
    db = ctx.engine.db
    request_id = await db.conversations.add_talk_request(ident.account_id, ident.pc_id, line)
    if request_id is None:
        raise ProtocolError(ErrorCode.CONFLICT, "you have already asked: an Admin will answer")
    await ctx.engine.audit.record(ctx, "chat.asked", target_type="talk_requests", target_id=request_id, pc_id=ident.pc_id)
    await ctx.engine.push_to_role("admin", "chat.request", {"request_id": request_id})
    if ident.pc_id is not None:
        from engine.control import events

        await events.on_signal(ctx.engine, ident.pc_id, "chat.asked", {"request_id": request_id})
    return {"request_id": request_id}


@handler("chat.requests")
async def chat_requests(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "admin")
    db = ctx.engine.db
    found = await db.conversations.talk_requests()
    names = await db.accounts.display_names_for(ident.account_id, sorted({r["from_account_id"] for r in found})) if found else {}
    return {"requests": [{"id": r["id"], "from": names.get(r["from_account_id"]), "account_id": r["from_account_id"], "host": r["hostname"],
                          "at": _iso(r["sent_at"]), "line": r["line"]} for r in found]}


@handler("chat.request_accept")
async def chat_request_accept(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "admin")
    found = await _open(ctx, int_field(payload, "request_id"))
    db = ctx.engine.db
    convo_id = await db.conversations.pair(ident.account_id, found["from_account_id"], ident.account_id)
    if not await db.conversations.decide_talk_request(found["id"], "accepted", ident.account_id, conversation_id=convo_id):
        raise ProtocolError(ErrorCode.CONFLICT, "another Admin has already answered this request")
    await db.conversations.add(convo_id, found["from_account_id"], found["line"])
    await ctx.engine.audit.record(ctx, "chat.request_accepted", target_type="talk_requests", target_id=found["id"], detail={"conversation_id": convo_id})
    await ctx.engine.push_to_account(found["from_account_id"], "chat.request_accepted", {"request_id": found["id"], "conversation_id": convo_id})
    await _gone(ctx, found["id"])
    convo = await db.conversations.get(convo_id)
    assert convo is not None
    return {"conversation": (await _views(ctx, [convo]))[0]}


@handler("chat.request_close")
async def chat_request_close(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "admin")
    found = await _open(ctx, int_field(payload, "request_id"))
    why = " ".join(str_field(payload, "why").split())[:LINE_MAX]
    if not why:
        raise ProtocolError(ErrorCode.INVALID, "say why: the person reads it")
    if not await ctx.engine.db.conversations.decide_talk_request(found["id"], "closed", ident.account_id, why=why):
        raise ProtocolError(ErrorCode.CONFLICT, "another Admin has already answered this request")
    await ctx.engine.audit.record(ctx, "chat.request_closed", target_type="talk_requests", target_id=found["id"], detail={"why": why})
    await ctx.engine.push_to_account(found["from_account_id"], "chat.request_closed", {"request_id": found["id"], "why": why})
    await _gone(ctx, found["id"])
    return {"request_id": found["id"], "state": "closed"}
