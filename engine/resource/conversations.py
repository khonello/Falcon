"""An Admin's conversations, with nobody above the Admins (the user, 29 Oct 2026; ENGINE-GAPS #17).

Version 1: an Admin talks to the other Admins and to whoever is signed in on a machine, and there is one group of every Admin once there are two or
more. An Admin needs no request to write to anyone; a person at a machine answers in a conversation an Admin started, or asks to talk
(engine/resource/talk.py). The help-ping channels (`assistance.*`) stay as they are for the level
above the Admins.

    chat.list   {}                                   the caller's conversations, latest first: who is in it, the last message, unread, who has seen it
    chat.people {}                                   Admin: who they may write to (the other Admins, and each machine's person, with the machine)
    chat.open   {account_id} | {pc_id} | {admins: true} | {account_ids: [..], title?}   Admin: the conversation with that person (made the first time), the group of
                                                     every Admin, or a small group of the people named (a new one each time)
    chat.get    {conversation_id, before_id?}        its messages, oldest first (100 at a time), and each member's read time
    chat.send   {conversation_id, body}              a message; pushed to the others as `chat.message`
    chat.read   {conversation_id}                    the caller has read it up to now; pushed to the others as `chat.read`
    chat.send_file / chat.file_save / ...         a file sent in a conversation: engine/resource/chatfiles.py

Names are the caller's (Display Names never cross namers).
"""

from __future__ import annotations

from typing import Any

from engine.dispatch import Context, handler
from engine.permissions import int_field, require_account, require_role, str_field
from protocol import ErrorCode, ProtocolError

BODY_MAX = 4000
PAGE = 100
PEOPLE_MAX = 2000
EVERY_ADMIN = "Every Admin"
GROUP_MAX = 20


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


async def _members(ctx: Context, convo: dict[str, Any]) -> list[int]:
    if convo["kind"] == "admins":
        return [a["id"] for a in await ctx.engine.db.accounts.active_admins()]
    return [m["account_id"] for m in await ctx.engine.db.conversations.members([convo["id"]])]


async def _in(ctx: Context, conversation_id: int) -> tuple[dict[str, Any], list[int]]:
    """The conversation, if the caller is in it. One they are not in does not exist, to them."""
    ident = require_account(ctx)
    convo = await ctx.engine.db.conversations.get(conversation_id)
    members = await _members(ctx, convo) if convo else []
    if convo is None or ident.account_id not in members:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such conversation")
    return convo, members


async def _views(ctx: Context, convos: list[dict[str, Any]]) -> list[dict[str, Any]]:
    me = ctx.identity.account_id
    db = ctx.engine.db
    ids = [c["id"] for c in convos]
    if not ids:
        return []
    admins = [a["id"] for a in await db.accounts.active_admins()]
    pair_members: dict[int, list[int]] = {}
    for m in await db.conversations.members(ids):
        pair_members.setdefault(m["conversation_id"], []).append(m["account_id"])
    members = {c["id"]: admins if c["kind"] == "admins" else sorted(pair_members.get(c["id"], [])) for c in convos}
    last = {m["conversation_id"]: m for m in await db.conversations.last_messages(ids)}
    reads: dict[int, dict[int, Any]] = {}
    for r in await db.conversations.reads(ids):
        reads.setdefault(r["conversation_id"], {})[r["account_id"]] = r["read_at"]
    unread = await db.conversations.unread(ids, me)
    asked = await db.conversations.opened_by_request(ids)
    people = sorted({p for ps in members.values() for p in ps} | {m["from_account_id"] for m in last.values()})
    names = await db.accounts.display_names_for(me, people) if people else {}
    out = []
    for c in convos:
        others = [p for p in members[c["id"]] if p != me]
        msg = last.get(c["id"])
        seen = [p for p in others if msg and p != msg["from_account_id"] and reads.get(c["id"], {}).get(p) and reads[c["id"]][p] >= msg["sent_at"]]
        out.append({"conversation_id": c["id"], "kind": c["kind"], "from_request": c["id"] in asked,
                    "title": EVERY_ADMIN if c["kind"] == "admins" else (c.get("title") or ", ".join(str(names.get(p)) for p in others) if c["kind"] == "group"
                                                                        else (names.get(others[0]) if others else None)),
                    "members": [{"account_id": p, "name": names.get(p)} for p in members[c["id"]]],
                    "last": {"body": msg["body"][:200], "from_account_id": msg["from_account_id"], "from": names.get(msg["from_account_id"]),
                             "at": _iso(msg["sent_at"])} if msg else None,
                    "unread": unread.get(c["id"], 0), "seen_by": [{"account_id": p, "name": names.get(p)} for p in seen]})
    return out


@handler("chat.list")
async def chat_list(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_account(ctx)
    db = ctx.engine.db
    convos = list(await db.conversations.pairs_of(ident.account_id))
    if ident.role == "admin" and len(await db.accounts.active_admins()) >= 2:
        group = await db.conversations.admins_conversation() or await db.conversations.get(await db.conversations.admins_group())
        convos.insert(0, group)
    views = await _views(ctx, convos)
    views.sort(key=lambda v: (v["last"] or {}).get("at") or "", reverse=True)
    waiting = await db.conversations.open_talk_request(ident.account_id)          # told here so a waiting request survives a restart of the person's program
    return {"conversations": views, "unread": sum(v["unread"] for v in views),
            "request": {"line": waiting["line"], "at": _iso(waiting["sent_at"])} if waiting else None}


@handler("chat.people")
async def chat_people(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Who an Admin may write to: the other active Admins, and the person of each machine (version 1's Admins are IT over every department), with the
    machine and whether it is connected now."""
    ident = require_role(ctx, "admin")
    db = ctx.engine.db
    online = ctx.engine.online_pc_ids()
    rows = [r for r in await db.accounts.fleet() if r["account_id"] and r["account_id"] != ident.account_id
            and r["pc_type"] != "super_user_workstation"][:PEOPLE_MAX]
    admins = {a["id"] for a in await db.accounts.active_admins()}
    names = await db.accounts.display_names_for(ident.account_id, sorted({r["account_id"] for r in rows})) if rows else {}
    people = [{"account_id": r["account_id"], "name": names.get(r["account_id"]), "role": "admin" if r["account_id"] in admins else "worker",
               "pc_id": r["id"], "hostname": r["hostname"], "department": r["department_name"], "online": r["id"] in online} for r in rows]
    people.sort(key=lambda p: (p["role"] != "admin", not p["online"], (p["name"] or "").lower()))
    return {"people": people, "admins_group": len(admins) >= 2}


@handler("chat.open")
async def chat_open(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "admin")
    db = ctx.engine.db
    if payload.get("admins"):
        if len(await db.accounts.active_admins()) < 2:
            raise ProtocolError(ErrorCode.CONFLICT, "the group of every Admin starts once there are two Admins")
        convo_id = await db.conversations.admins_group()
    elif payload.get("account_ids") is not None:
        given = payload["account_ids"]
        if not isinstance(given, list):
            raise ProtocolError(ErrorCode.INVALID, "account_ids is a list")
        others = sorted({int(a) for a in given} - {ident.account_id})
        if not 2 <= len(others) <= GROUP_MAX:
            raise ProtocolError(ErrorCode.INVALID, f"a small group is 2 to {GROUP_MAX} other people")
        for a in others:
            person = await db.accounts.by_id(a)
            if person is None or person["status"] != "active" or person["role"] == "super_user":
                raise ProtocolError(ErrorCode.NOT_FOUND, "no such person")
        title = " ".join(str(payload.get("title") or "").split())[:80] or None
        convo_id = await db.conversations.group(ident.account_id, [ident.account_id, *others], title)
    else:
        account_id = int_field(payload, "account_id", required=False)
        pc_id = int_field(payload, "pc_id", required=False)
        if (account_id is None) == (pc_id is None):
            raise ProtocolError(ErrorCode.INVALID, "give account_id, pc_id or admins")
        if pc_id is not None:
            pc = await db.accounts.pc(pc_id)
            if pc is None:
                raise ProtocolError(ErrorCode.NOT_FOUND, "no such machine")
            account_id = pc["bound_account_id"]
            if account_id is None:
                raise ProtocolError(ErrorCode.CONFLICT, f"nobody is signed in on {pc['hostname']}: it has no person")
        other = await db.accounts.by_id(int(account_id))  # type: ignore[arg-type]
        if other is None or other["status"] != "active" or other["role"] == "super_user":
            raise ProtocolError(ErrorCode.NOT_FOUND, "no such person")
        if other["id"] == ident.account_id:
            raise ProtocolError(ErrorCode.INVALID, "that is you")
        convo_id = await db.conversations.pair(ident.account_id, other["id"], ident.account_id)
    convo = await db.conversations.get(convo_id)
    assert convo is not None
    return {"conversation": (await _views(ctx, [convo]))[0]}


@handler("chat.get")
async def chat_get(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    convo, members = await _in(ctx, int_field(payload, "conversation_id"))
    db = ctx.engine.db
    found = await db.conversations.messages(convo["id"], before_id=int_field(payload, "before_id", required=False), limit=PAGE)
    names = await db.accounts.display_names_for(ctx.identity.account_id, sorted(set(members) | {m["from_account_id"] for m in found}))
    reads = {r["account_id"]: _iso(r["read_at"]) for r in await db.conversations.reads([convo["id"]]) if r["account_id"] in members}
    files = await db.chat_files.by_ids([m["chat_file_id"] for m in found if m.get("chat_file_id")])

    def file_of(m: dict[str, Any]) -> dict[str, Any] | None:
        f = files.get(m.get("chat_file_id"))
        return {"file_id": f["id"], "name": f["name"], "size": f["size_bytes"], "state": f["state"], "expires_at": _iso(f["expires_at"])} if f else None
    messages = [{"message_id": m["id"], "from_account_id": m["from_account_id"], "from": names.get(m["from_account_id"]), "body": m["body"],
                 "at": _iso(m["sent_at"]), "mine": m["from_account_id"] == ctx.identity.account_id, "file": file_of(m)} for m in reversed(found)]
    return {"conversation": (await _views(ctx, [convo]))[0], "messages": messages, "more": len(found) == PAGE,
            "reads": [{"account_id": p, "name": names.get(p), "read_at": reads.get(p)} for p in members]}


@handler("chat.send")
async def chat_send(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    convo, members = await _in(ctx, int_field(payload, "conversation_id"))
    body = str_field(payload, "body").strip()
    if not body:
        raise ProtocolError(ErrorCode.INVALID, "a message needs something written in it")
    if len(body) > BODY_MAX:
        raise ProtocolError(ErrorCode.INVALID, f"a message is at most {BODY_MAX} characters")
    me = ctx.identity.account_id
    db = ctx.engine.db
    msg = await db.conversations.add(convo["id"], me, body)
    await ctx.engine.audit.record(ctx, "chat.sent", target_type="conversations", target_id=convo["id"], detail={"message_id": msg["id"]})
    for p in members:
        if p != me:
            name = (await db.accounts.display_names_for(p, [me])).get(me)
            await ctx.engine.push_to_account(p, "chat.message", {"conversation_id": convo["id"], "message_id": msg["id"], "from_account_id": me,
                                                                 "from": name, "body": body[:200], "at": _iso(msg["sent_at"])})
    return {"message_id": msg["id"], "at": _iso(msg["sent_at"])}


@handler("chat.read")
async def chat_read(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    convo, members = await _in(ctx, int_field(payload, "conversation_id"))
    me = ctx.identity.account_id
    await ctx.engine.db.conversations.read(convo["id"], me)
    for p in members:
        if p != me:
            await ctx.engine.push_to_account(p, "chat.read", {"conversation_id": convo["id"], "account_id": me})
    return {"conversation_id": convo["id"], "read": True}
