"""Assistance (Resource & Assistance -> Assistance).

File search: a Global File Index query scoped to the caller's access tier.

Ping: a message request -- a lock-free, repeatable attention signal between a subordinate and their
direct superior (either direction: an Admin may ping a Worker for information), or between two
Admins. The receiver sees a persistent pulsing status (unaddressed count > 0) -- the accountability
mechanism in place of a timeout. Same shared status-indicator mechanism Task deadlines use.

Message Channel: opens when the receiver accepts the request (`assistance.respond`). The one
exception is the Super User writing to an Admin: that opens the channel at once, with no request to
accept (the user, 22 Oct 2026). Either party writes whenever they like -- the one-message-per-turn lock
was dropped the same day. `turn` now only says who is waiting to answer: 'sender' the subordinate
party, 'superior' the superior; it moves to the other party after each message. The superior closes
a channel, even if they pinged first; between two Admins either of them may.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler
from engine.permissions import RANK, int_field, require_account, str_field
from engine.serialize import row, rows
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine


def superior_of(a: dict[str, Any], b: dict[str, Any]) -> dict[str, Any] | None:
    """The higher-ranked of two accounts if they are in a direct vertical relationship
    (Worker <-> Admin of the same department, Admin <-> Super User), else None."""
    hi, lo = (a, b) if RANK[a["role"]] > RANK[b["role"]] else (b, a)
    if hi["role"] == lo["role"]:
        return None
    if hi["role"] == "admin" and lo["role"] == "worker":
        return hi if hi["department_id"] == lo["department_id"] else None
    if hi["role"] == "super_user" and lo["role"] == "admin":
        return hi
    return None


def may_message(a: dict[str, Any], b: dict[str, Any]) -> bool:
    """A direct vertical pair, or two Admins (peers ask each other to talk too)."""
    if a["id"] == b["id"]:
        return False
    return superior_of(a, b) is not None or (a["role"] == "admin" and b["role"] == "admin")


def _channel_parties(channel: dict[str, Any]) -> tuple[int, int]:
    """(subordinate_account_id, superior_account_id)"""
    sup = channel["superior_account_id"]
    sub = channel["initiator_account_id"] if channel["initiator_account_id"] != sup else channel["_other"]
    return sub, sup


async def _load_channel(ctx: Context, channel_id: int) -> dict[str, Any]:
    db = ctx.engine.db
    channel = await db.assistance.channel(channel_id)
    if channel is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such channel")
    ping = await db.assistance.get_ping(channel["opened_via_ping_id"])
    assert ping is not None
    parties = {ping["sender_account_id"], ping["receiver_account_id"]}
    channel["_other"] = next(iter(parties - {channel["superior_account_id"]}))
    me = ctx.identity.account_id
    if me in parties:
        return channel
    raise ProtocolError(ErrorCode.FORBIDDEN, "not a party to this channel")


def turn_of(channel: dict[str, Any]) -> int:
    """The party the channel waits on: the one who has not answered the last message."""
    sub, sup = _channel_parties(channel)
    return sub if channel["turn"] == "sender" else sup


async def _push_ping_status(engine: Engine, receiver_account_id: int) -> None:
    count = await engine.db.assistance.unaddressed_ping_count(receiver_account_id)
    await engine.push_to_account(receiver_account_id, "assistance.ping_status",
                                 {"unaddressed": count, "indicator": "unaddressed_ping" if count else None})


# --- handlers -----------------------------------------------------------------------------------

@handler("assistance.search")
async def search(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"query": str} -> index results filtered by the caller's access tier."""
    ident = require_account(ctx)
    query = str_field(payload, "query")
    results = await ctx.engine.file_index.search(query, role=ident.role, department_id=ident.department_id)
    return {"results": rows(results)}


@handler("assistance.my_admins")
async def my_admins(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Who the caller may ask for help: a Worker's Admins (their own department's), an Admin's Super User.
    -> {"admins": [{"account_id", "name"}]}, named as the caller names them. What the Worker's "ask for
    help" window offers; a ping carries no message, so this is all it needs."""
    ident = require_account(ctx)
    db = ctx.engine.db
    me = await db.accounts.by_id(ident.account_id)
    if me is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such account")
    people = [a for a in await db.accounts.list_all() if a["status"] == "active" and superior_of(me, a) is not None
              and a["id"] != me["id"] and RANK[a["role"]] > RANK[me["role"]]]
    names = await db.accounts.display_names_for(ident.account_id, [a["id"] for a in people])
    return {"admins": [{"account_id": a["id"], "name": names.get(a["id"]) or a.get("hostname") or "your Admin",
                        "role": a["role"]} for a in people]}


@handler("assistance.people")
async def people(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Everyone the caller may message, named as the caller names them: the Super User's Admins; an Admin's
    Super User, the other Admins and their own Workers; a Worker's Admins. `request` says whether writing
    to them is a request they accept first (everyone but the Super User writing to an Admin).
    -> {"people": [{"account_id", "name", "role", "department_id", "department_name", "hostname", "request"}]}"""
    ident = require_account(ctx)
    db = ctx.engine.db
    me = await db.accounts.by_id(ident.account_id)
    if me is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such account")
    them = [a for a in await db.accounts.list_all() if a["status"] == "active" and may_message(me, a)]
    names = await db.accounts.display_names_for(ident.account_id, [a["id"] for a in them])
    return {"people": [{"account_id": a["id"], "name": names.get(a["id"]) or a.get("hostname") or a["role"],
                        "role": a["role"], "department_id": a["department_id"], "department_name": a.get("department_name"),
                        "hostname": a.get("hostname"),
                        "request": not (me["role"] == "super_user" and a["role"] == "admin")} for a in them]}


async def _may_close(ctx: Context, channel: dict[str, Any], account_id: int) -> bool:
    """The superior closes; between two Admins either of them does."""
    sub, sup = _channel_parties(channel)
    if account_id == sup:
        return True
    a, b = await ctx.engine.db.accounts.by_id(sub), await ctx.engine.db.accounts.by_id(sup)
    return bool(a and b and a["role"] == "admin" and b["role"] == "admin")


@handler("assistance.ping")
async def ping(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"to_account_id": int}. A message request to the caller's direct superior or subordinate, or to
    another Admin. Repeatable: no lock on pinging. From the Super User to an Admin it is no request: the
    channel opens at once (-> {"ping_id", "channel_id", "opened"}) and the Admin has nothing to accept."""
    ident = require_account(ctx)
    to_id = int_field(payload, "to_account_id")
    db = ctx.engine.db
    me = await db.accounts.by_id(ident.account_id)
    other = await db.accounts.by_id(to_id)
    if other is None or other["status"] != "active" or me is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such active account")
    if not may_message(me, other):
        raise ProtocolError(ErrorCode.FORBIDDEN, "messages go between a subordinate and their direct superior, or two Admins")
    if me["role"] == "super_user" and other["role"] == "admin":
        return await _open_directly(ctx, me, other)
    already_waiting = await db.assistance.unaddressed_from(ident.account_id, to_id)
    ping_id = await db.assistance.ping(ident.account_id, to_id)
    if not already_waiting and other["role"] == "admin" and me["role"] == "worker":
        from engine.console import accountability

        sender_pc = await db.accounts.pc(me["bound_pc_id"]) if me["bound_pc_id"] else None
        await accountability.watch(ctx.engine, "help", target_table="pings", target_id=ping_id, kind="admin", account_id=to_id,
                                   pc_id=me["bound_pc_id"], department_id=other["department_id"],
                                   label=f"Help request from {sender_pc['hostname'] if sender_pc else 'a worker'}")
    await ctx.engine.audit.record(ctx, "assistance.ping", target_type="pings", target_id=ping_id,
                                  detail={"to_account_id": to_id})
    names = await db.accounts.display_names_for(to_id, [ident.account_id])
    await ctx.engine.push_to_account(to_id, "assistance.ping", {"ping_id": ping_id, "from_account_id": ident.account_id,
                                                                 "from_name": names.get(ident.account_id)})
    await _push_ping_status(ctx.engine, to_id)
    return {"ping_id": ping_id}


async def _open_directly(ctx: Context, su: dict[str, Any], admin: dict[str, Any]) -> dict[str, Any]:
    """The Super User writes to an Admin: the request is recorded and addressed at once, and the channel
    opens (or the open one is reused) with the Super User to speak."""
    db = ctx.engine.db
    ping_id = await db.assistance.ping(su["id"], admin["id"])
    await db.assistance.address_pings(admin["id"], su["id"])
    await db.assistance.address_pings(su["id"], admin["id"])     # writing to them answers their own request too
    await _push_ping_status(ctx.engine, su["id"])
    await ctx.engine.audit.record(ctx, "assistance.ping", target_type="pings", target_id=ping_id,
                                  detail={"to_account_id": admin["id"], "direct": True})
    channel = await db.assistance.open_channel_between(su["id"], admin["id"])
    opened = channel is None
    if channel is None:
        channel_id = await db.assistance.open_channel(ping_id, su["id"], su["id"], "superior")
        channel = await db.assistance.channel(channel_id)
        await ctx.engine.audit.record(ctx, "assistance.channel_opened", target_type="message_channels",
                                      target_id=channel_id, detail={"ping_id": ping_id, "direct": True})
    assert channel is not None
    out = {"channel_id": channel["id"], "opened": opened, "turn": channel["turn"],
           "superior_account_id": channel["superior_account_id"]}
    if opened:
        await ctx.engine.push_to_account(admin["id"], "assistance.channel_opened", out)
    return {"ping_id": ping_id, **out}


@handler("assistance.ping_status")
async def ping_status(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Unaddressed pings for the caller as receiver -- drives the pulsing indicator."""
    ident = require_account(ctx)
    pings = await ctx.engine.db.assistance.unaddressed_pings(ident.account_id)
    names = await ctx.engine.db.accounts.display_names_for(ident.account_id, [p["sender_account_id"] for p in pings])
    out = rows(pings)
    for p in out:
        p["from_name"] = names.get(p["sender_account_id"])
    return {"unaddressed": len(out), "pings": out, "indicator": "unaddressed_ping" if out else None}


@handler("assistance.respond")
async def respond(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"ping_id"}. The receiver accepts the request: every unaddressed ping from that sender is
    addressed and a Message Channel opens (or the existing open one is returned). Writing back
    accepts too -- the client calls this first. Between two Admins the receiver is recorded as the
    channel's `superior_account_id`, though either of them may close it."""
    ident = require_account(ctx)
    ping_id = int_field(payload, "ping_id")
    db = ctx.engine.db
    p = await db.assistance.get_ping(ping_id)
    if p is None or p["receiver_account_id"] != ident.account_id:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such message addressed to you")
    await db.assistance.address_pings(ident.account_id, p["sender_account_id"])
    channel = await db.assistance.open_channel_between(p["sender_account_id"], p["receiver_account_id"])
    opened = False
    if channel is None:
        me = await db.accounts.by_id(ident.account_id)
        sender = await db.accounts.by_id(p["sender_account_id"])
        assert me and sender
        sup = superior_of(me, sender) or me
        # The ping sender speaks first. 'sender' = subordinate's turn, 'superior' = superior's.
        first_turn = "superior" if p["sender_account_id"] == sup["id"] else "sender"
        channel_id = await db.assistance.open_channel(ping_id, p["sender_account_id"], sup["id"], first_turn)
        channel = await db.assistance.channel(channel_id)
        opened = True
        await ctx.engine.audit.record(ctx, "assistance.channel_opened", target_type="message_channels",
                                      target_id=channel_id, detail={"ping_id": ping_id})
    assert channel is not None
    await _push_ping_status(ctx.engine, ident.account_id)
    payload_out = {"channel_id": channel["id"], "opened": opened, "turn": channel["turn"],
                   "superior_account_id": channel["superior_account_id"]}
    await ctx.engine.push_to_account(p["sender_account_id"], "assistance.channel_opened", payload_out)
    return payload_out


@handler("assistance.message")
async def message(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"channel_id", "body"} -- either party, whenever they like, while the channel is open."""
    ident = require_account(ctx)
    channel_id = int_field(payload, "channel_id")
    body = str_field(payload, "body")
    channel = await _load_channel(ctx, channel_id)
    if channel["closed_at"] is not None:
        raise ProtocolError(ErrorCode.CONFLICT, "channel is closed")
    sub, sup = _channel_parties(channel)
    next_turn = "superior" if ident.account_id == sub else "sender"      # the other party now owes an answer
    msg_id = await ctx.engine.db.assistance.post_message(channel_id, ident.account_id, body, next_turn)
    await ctx.engine.audit.record(ctx, "assistance.message", target_type="messages", target_id=msg_id,
                                  detail={"channel_id": channel_id})
    other = sup if ident.account_id == sub else sub
    out = {"channel_id": channel_id, "message_id": msg_id, "from_account_id": ident.account_id, "body": body,
           "turn": next_turn}
    await ctx.engine.push_to_account(other, "assistance.message", out)
    return {"message_id": msg_id, "turn": next_turn}


@handler("assistance.close_channel")
async def close_channel(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Superior only -- regardless of who pinged first. Between two Admins, either of them."""
    ident = require_account(ctx)
    channel_id = int_field(payload, "channel_id")
    channel = await _load_channel(ctx, channel_id)
    sub, sup = _channel_parties(channel)
    if not await _may_close(ctx, channel, ident.account_id):
        raise ProtocolError(ErrorCode.FORBIDDEN, "only the superior closes a channel")
    await ctx.engine.db.assistance.close_channel(channel_id)
    await ctx.engine.audit.record(ctx, "assistance.channel_closed", target_type="message_channels",
                                  target_id=channel_id)
    await ctx.engine.push_to_account(sup if ident.account_id == sub else sub, "assistance.channel_closed",
                                     {"channel_id": channel_id})
    return {"channel_id": channel_id, "closed": True}


@handler("assistance.channel")
async def channel(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Channel state + messages for a party."""
    ident = require_account(ctx)
    channel_id = int_field(payload, "channel_id")
    ch = await _load_channel(ctx, channel_id)
    msgs = await ctx.engine.db.assistance.messages(channel_id)
    sub, sup = _channel_parties(ch)
    names = await ctx.engine.db.accounts.display_names_for(ident.account_id, [sub, sup])
    view = row({k: v for k, v in ch.items() if not k.startswith("_")}) or {}
    view["subordinate_account_id"] = sub
    view["names"] = {str(k): v for k, v in names.items()}
    view["my_turn"] = ch["closed_at"] is None and turn_of(ch) == ident.account_id     # waiting on me; not a lock
    view["can_close"] = ch["closed_at"] is None and await _may_close(ctx, ch, ident.account_id)
    return {"channel": view, "messages": rows(msgs)}


@handler("assistance.channels")
async def channels(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Channels the caller is a party to or listens on."""
    ident = require_account(ctx)
    return {"channels": rows(await ctx.engine.db.assistance.channels_for(ident.account_id))}


