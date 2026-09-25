"""Message-type -> handler registry.

Combo modules register handlers with `@handler("area.operation")`. `engine.server` imports every
combo package so registration happens at startup.

Handler signature:
    async def fn(ctx: Context, payload: dict) -> dict
The return value becomes the response `result`. Raise `ProtocolError` for a typed error response.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field, replace
from typing import TYPE_CHECKING, Any

from protocol import ErrorCode, ProtocolError
from protocol.viewing import VIEW_KEY, VIEW_SESSION, VIEWED_AS_TRAVERSED

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
    department_id: int | None = None
    client_id: str | None = None


@dataclass
class Context:
    engine: Engine
    connection: Connection
    identity: Identity = field(default_factory=Identity)
    # The session the caller currently occupies (their own, or one traversed into).
    active_session_id: int | None = None
    # Set only on the copy `dispatch` makes for a read looked at THROUGH a held session: `identity`
    # is then the Admin being viewed, and this is who is really asking. The audit trail records this.
    viewed_by: Identity | None = None


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
    if message_type in VIEWED_AS_TRAVERSED and payload.get(VIEW_KEY) == VIEW_SESSION:
        viewed = await viewing_identity(ctx)
        if viewed is not None:
            # a copy: the connection's own ctx keeps the Super User, so nothing leaks past this read
            ctx = replace(ctx, identity=viewed, viewed_by=ctx.identity)
    return await fn(ctx, payload)


async def viewing_identity(ctx: Context) -> Identity | None:
    """The Admin a Super User is looking through, or None. Only a Super User, only a traversal, only
    into a workstation bound to an active Admin -- anything else is answered as the caller."""
    ident = ctx.identity
    db = ctx.engine.db
    if ident.role != "super_user" or ident.account_id is None or not db.connected:
        return None
    session = await db.sessions.active_for_account(ident.account_id)
    if session is None or session["occupied_via"] != "traversal":
        return None
    pc = await db.accounts.pc(session["pc_id"])
    if pc is None or pc["pc_type"] != "admin_workstation" or pc["bound_role"] != "admin":
        return None
    return Identity(account_id=pc["bound_account_id"], role="admin", pc_id=pc["id"],
                    department_id=pc["department_id"], client_id=ident.client_id)


def stub(message_type: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    """Placeholder result for a scaffolded handler. Replace the call site with real logic."""
    log.debug("STUB %s payload=%s", message_type, payload)
    return {"stub": True, "type": message_type}
