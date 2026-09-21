"""Message-type -> handler registry.

Combo modules register handlers with `@handler("area.operation")`. `engine.server` imports every
combo package so registration happens at startup.

Handler signature:
    async def fn(ctx: Context, payload: dict) -> dict
The return value becomes the response `result`. Raise `ProtocolError` for a typed error response.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Awaitable, Callable

from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.connection import Connection
    from engine.server import Engine

log = logging.getLogger(__name__)


@dataclass
class Identity:
    """Who the caller is, as established by the auth handshake (spec 8.2).

    In the scaffold `auth.verify` is stubbed to accept, so this carries whatever the client
    *claimed* -- trustworthy only once real auth is filled in last.
    """

    account_id: int | None = None
    role: str | None = None  # 'super_user' | 'admin' | 'worker'
    pc_id: int | None = None
    client_id: str | None = None


@dataclass
class Context:
    engine: "Engine"
    connection: "Connection"
    identity: Identity = field(default_factory=Identity)
    # The session the caller currently occupies (their own, or one traversed into).
    active_session_id: int | None = None


Handler = Callable[[Context, dict[str, Any]], Awaitable[dict[str, Any]]]

_registry: dict[str, Handler] = {}


def handler(message_type: str) -> Callable[[Handler], Handler]:
    def register(fn: Handler) -> Handler:
        if message_type in _registry:
            raise RuntimeError(f"duplicate handler for {message_type!r}")
        _registry[message_type] = fn
        return fn

    return register


def registered_types() -> list[str]:
    return sorted(_registry)


async def dispatch(ctx: Context, message_type: str, payload: dict[str, Any]) -> dict[str, Any]:
    fn = _registry.get(message_type)
    if fn is None:
        raise ProtocolError(ErrorCode.UNKNOWN_TYPE, f"no handler for {message_type!r}")
    return await fn(ctx, payload)


def stub(message_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Placeholder result for a scaffolded handler. Replace the call site with real logic."""
    log.debug("STUB %s payload=%s", message_type, payload)
    return {"stub": True, "type": message_type}
