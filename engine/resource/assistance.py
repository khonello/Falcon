"""Assistance (Resource & Assistance -> Assistance).

File search: a Global File Index query scoped to the caller's access tier.

Ping: lock-free, repeatable attention signal between a subordinate and their direct superior
(either direction: an Admin may ping a Worker for information). The receiver sees a persistent
pulsing status (unaddressed count > 0) -- the accountability mechanism in place of a timeout.
Same shared status-indicator mechanism Task deadlines use.

Message Channel: opens when the receiver responds to a ping. One-message-per-turn lock,
Engine-enforced. `turn` = 'sender' means the subordinate party may post, 'superior' the
superior; it flips after every message. Only the superior closes it, even if they pinged first.

Listeners: either party may add an Admin as a silent real-time observer; deduplicated; each
party sees only the Listeners *they* added. Adding one raises a 'listener_report' Report.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler
from engine.hierarchy import reports
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


def _channel_parties(channel: dict[str, Any]) -> tuple[int, int]:
    """(subordinate_account_id, superior_account_id)"""
    sup = channel["superior_account_id"]
    sub = channel["initiator_account_id"] if channel["initiator_account_id"] != sup else channel["_other"]
    return sub, sup


async def _load_channel(ctx: Context, channel_id: int, *, allow_listener: bool = False) -> dict[str, Any]:
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
    if allow_listener and me in await db.assistance.listener_account_ids(channel_id):
        channel["_listener"] = True
        return channel
    raise ProtocolError(ErrorCode.FORBIDDEN, "not a party to this channel")


def turn_of(channel: dict[str, Any]) -> int:
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


@handler("assistance.ping")
async def ping(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"to_account_id": int}. Receiver must be the caller's direct superior or subordinate.
    Repeatable: no lock on pinging."""
    ident = require_account(ctx)
    to_id = int_field(payload, "to_account_id")
    db = ctx.engine.db
    me = await db.accounts.by_id(ident.account_id)
    other = await db.accounts.by_id(to_id)
    if other is None or other["status"] != "active" or me is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such active account")
    if superior_of(me, other) is None:
        raise ProtocolError(ErrorCode.FORBIDDEN, "pings go between a subordinate and their direct superior")
    ping_id = await db.assistance.ping(ident.account_id, to_id)
    await ctx.engine.audit.record(ctx, "assistance.ping", target_type="pings", target_id=ping_id,
                                  detail={"to_account_id": to_id})
    names = await db.accounts.display_names_for(to_id, [ident.account_id])
    await ctx.engine.push_to_account(to_id, "assistance.ping", {"ping_id": ping_id, "from_account_id": ident.account_id,
                                                                 "from_name": names.get(ident.account_id)})
    await _push_ping_status(ctx.engine, to_id)
    return {"ping_id": ping_id}


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
    """{"ping_id"}. The receiver responds: every unaddressed ping from that sender is
    addressed and a Message Channel opens (or the existing open one is returned)."""
    ident = require_account(ctx)
    ping_id = int_field(payload, "ping_id")
    db = ctx.engine.db
    p = await db.assistance.get_ping(ping_id)
    if p is None or p["receiver_account_id"] != ident.account_id:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such ping addressed to you")
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
    """{"channel_id", "body"} -- refused with CONFLICT if it is not the caller's turn."""
    ident = require_account(ctx)
    channel_id = int_field(payload, "channel_id")
    body = str_field(payload, "body")
    channel = await _load_channel(ctx, channel_id)
    if channel["closed_at"] is not None:
        raise ProtocolError(ErrorCode.CONFLICT, "channel is closed")
    if turn_of(channel) != ident.account_id:
        raise ProtocolError(ErrorCode.CONFLICT, "channel is locked: waiting for the other party's reply")
    next_turn = "superior" if channel["turn"] == "sender" else "sender"
    msg_id = await ctx.engine.db.assistance.post_message(channel_id, ident.account_id, body, next_turn)
    await ctx.engine.audit.record(ctx, "assistance.message", target_type="messages", target_id=msg_id,
                                  detail={"channel_id": channel_id})
    sub, sup = _channel_parties(channel)
    other = sup if ident.account_id == sub else sub
    out = {"channel_id": channel_id, "message_id": msg_id, "from_account_id": ident.account_id, "body": body,
           "turn": next_turn}
    await ctx.engine.push_to_account(other, "assistance.message", out)
    for listener in await ctx.engine.db.assistance.listener_account_ids(channel_id):
        await ctx.engine.push_to_account(listener, "assistance.message", out)  # real time, silent
    return {"message_id": msg_id, "turn": next_turn}


@handler("assistance.close_channel")
async def close_channel(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Superior only -- regardless of who pinged first."""
    ident = require_account(ctx)
    channel_id = int_field(payload, "channel_id")
    channel = await _load_channel(ctx, channel_id)
    if ident.account_id != channel["superior_account_id"]:
        raise ProtocolError(ErrorCode.FORBIDDEN, "only the superior closes a channel")
    await ctx.engine.db.assistance.close_channel(channel_id)
    await ctx.engine.audit.record(ctx, "assistance.channel_closed", target_type="message_channels",
                                  target_id=channel_id)
    sub, _ = _channel_parties(channel)
    await ctx.engine.push_to_account(sub, "assistance.channel_closed", {"channel_id": channel_id})
    return {"channel_id": channel_id, "closed": True}


@handler("assistance.add_listener")
async def add_listener(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"channel_id", "admin_account_id"} -- either party adds an Admin; deduplicated; the
    other party is not informed. Fully audited and reported."""
    ident = require_account(ctx)
    channel_id = int_field(payload, "channel_id")
    admin_id = int_field(payload, "admin_account_id")
    channel = await _load_channel(ctx, channel_id)
    if channel["closed_at"] is not None:
        raise ProtocolError(ErrorCode.CONFLICT, "channel is closed")
    listener = await ctx.engine.db.accounts.by_id(admin_id)
    if listener is None or listener["role"] != "admin" or listener["status"] != "active":
        raise ProtocolError(ErrorCode.INVALID, "a Listener must be an active Admin")
    if admin_id in _channel_parties(channel):
        raise ProtocolError(ErrorCode.INVALID, "a channel party cannot listen to their own channel")
    inserted = await ctx.engine.db.assistance.add_listener(channel_id, admin_id, ident.account_id)
    await ctx.engine.audit.record(ctx, "assistance.listener_added", target_type="listeners", target_id=admin_id,
                                  detail={"channel_id": channel_id, "deduplicated": not inserted})
    if inserted:
        await reports.emit(ctx.engine, "listener_report", source_table="message_channels", source_id=channel_id,
                           summary=f"listener added to channel #{channel_id}")
        await ctx.engine.push_to_account(admin_id, "assistance.listening", {"channel_id": channel_id})
    return {"channel_id": channel_id, "listener_account_id": admin_id, "added": inserted}


@handler("assistance.my_listeners")
async def my_listeners(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Only the Listeners the caller added -- never the other party's."""
    ident = require_account(ctx)
    channel_id = int_field(payload, "channel_id")
    await _load_channel(ctx, channel_id)
    found = await ctx.engine.db.assistance.listeners_added_by(channel_id, ident.account_id)
    names = await ctx.engine.db.accounts.display_names_for(ident.account_id, [l["listener_account_id"] for l in found])
    out = rows(found)
    for l in out:
        l["name"] = names.get(l["listener_account_id"])
    return {"listeners": out}


@handler("assistance.channel")
async def channel(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Channel state + messages for a party or a Listener."""
    ident = require_account(ctx)
    channel_id = int_field(payload, "channel_id")
    ch = await _load_channel(ctx, channel_id, allow_listener=True)
    msgs = await ctx.engine.db.assistance.messages(channel_id)
    sub, sup = _channel_parties(ch)
    names = await ctx.engine.db.accounts.display_names_for(ident.account_id, [sub, sup])
    view = row({k: v for k, v in ch.items() if not k.startswith("_")}) or {}
    view["subordinate_account_id"] = sub
    view["names"] = {str(k): v for k, v in names.items()}
    view["my_turn"] = ch["closed_at"] is None and not ch.get("_listener") and turn_of(ch) == ident.account_id
    return {"channel": view, "messages": rows(msgs)}


@handler("assistance.channels")
async def channels(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Channels the caller is a party to or listens on."""
    ident = require_account(ctx)
    return {"channels": rows(await ctx.engine.db.assistance.channels_for(ident.account_id))}


