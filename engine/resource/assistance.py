"""Assistance (Resource & Assistance -> Assistance).

File search: a Global File Index query scoped to the caller's access tier.

Ping: lock-free, repeatable attention signal. The receiver sees a persistent pulsing status
(unaddressed count > 0) -- the accountability mechanism in place of a timeout. Same shared
status-indicator mechanism Task deadlines use.

Message Channel: opens only once the superior responds to a ping. One-message-per-turn lock,
Engine-enforced (not client-side). Only the superior closes it, even if they pinged first.

Listeners: either party may add an Admin as a silent real-time observer; deduplicated; each
party sees only the Listeners *they* added. Fully audited.
"""

from __future__ import annotations

from typing import Any

from engine.dispatch import Context, handler, stub
from protocol import ErrorCode, ProtocolError

CHANNEL_STATES = ("open", "closed")


def next_turn(last_author_id: int | None, superior_id: int, subordinate_id: int) -> int:
    """Who may post next. Subordinate opens; then it strictly alternates."""
    if last_author_id is None or last_author_id == superior_id:
        return subordinate_id
    return superior_id


def assert_may_post(author_id: int, expected_id: int) -> None:
    if author_id != expected_id:
        raise ProtocolError(ErrorCode.CONFLICT, "channel is locked: waiting for the other party")


@handler("assistance.search")
async def search(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"query": str} -> index results filtered by allowed_tags_for(role, department)."""
    return stub("assistance.search", payload)


@handler("assistance.ping")
async def ping(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"to_account_id": int}. Pushes `assistance.ping_status` to the receiver."""
    return stub("assistance.ping", payload)


@handler("assistance.ping_status")
async def ping_status(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Unaddressed count for the caller -- drives the pulsing indicator."""
    return stub("assistance.ping_status", payload)


@handler("assistance.respond")
async def respond(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Superior responds to a ping -> opens the Message Channel."""
    return stub("assistance.respond", payload)


@handler("assistance.message")
async def message(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"channel_id", "body"} -- refused with CONFLICT if it is not the caller's turn."""
    return stub("assistance.message", payload)


@handler("assistance.close_channel")
async def close_channel(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Superior only."""
    return stub("assistance.close_channel", payload)


@handler("assistance.add_listener")
async def add_listener(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"channel_id", "admin_account_id"} -- listener must be an Admin; deduplicated."""
    return stub("assistance.add_listener", payload)


@handler("assistance.my_listeners")
async def my_listeners(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Only the Listeners the caller added -- never the other party's."""
    return stub("assistance.my_listeners", payload)


@handler("assistance.channel")
async def channel(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Channel state + messages for a party or a Listener."""
    return stub("assistance.channel", payload)
