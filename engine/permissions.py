"""Role checks shared by every handler. The Engine decides; clients render.

Hierarchy ranks: super_user > admin > worker. "Vertical" means the caller outranks the subject;
"horizontal" means peers (Admin <-> Admin) -- who have no blocking or eviction rights over each
other.
"""

from __future__ import annotations

from typing import Any

from engine.dispatch import Context, Identity
from protocol import ErrorCode, ProtocolError

RANK = {"super_user": 3, "admin": 2, "worker": 1}


def require_account(ctx: Context) -> Identity:
    if ctx.identity.account_id is None or ctx.identity.role is None:
        raise ProtocolError(ErrorCode.UNAUTHENTICATED, "no account bound to this connection")
    return ctx.identity


def require_role(ctx: Context, *roles: str) -> Identity:
    ident = require_account(ctx)
    if roles and ident.role not in roles:
        raise ProtocolError(ErrorCode.FORBIDDEN, f"requires role {' or '.join(roles)}")
    return ident


def outranks(role_a: str | None, role_b: str | None) -> bool:
    return RANK.get(role_a or "", 0) > RANK.get(role_b or "", 0)


def relationship(requester_role: str | None, other_role: str | None) -> str:
    """'vertical' (requester outranks), 'horizontal' (peers) or 'inferior'."""
    r, o = RANK.get(requester_role or "", 0), RANK.get(other_role or "", 0)
    return "vertical" if r > o else "horizontal" if r == o else "inferior"


def require_department_scope(ident: Identity, department_id: int | None) -> None:
    """Super User reaches every department; an Admin only their own."""
    if ident.role == "super_user":
        return
    if ident.role == "admin" and department_id is not None and department_id == ident.department_id:
        return
    raise ProtocolError(ErrorCode.FORBIDDEN, "outside your department")


def int_field(payload: dict[str, Any], name: str, *, required: bool = True) -> int | None:
    value = payload.get(name)
    if value is None:
        if required:
            raise ProtocolError(ErrorCode.INVALID, f"{name} required")
        return None
    try:
        return int(value)
    except (TypeError, ValueError) as exc:
        raise ProtocolError(ErrorCode.INVALID, f"{name} must be an integer") from exc


def str_field(payload: dict[str, Any], name: str, *, required: bool = True,
              choices: tuple[str, ...] | None = None) -> str | None:
    value = payload.get(name)
    if value is None or value == "":
        if required:
            raise ProtocolError(ErrorCode.INVALID, f"{name} required")
        return None
    value = str(value)
    if choices and value not in choices:
        raise ProtocolError(ErrorCode.INVALID, f"{name} must be one of {', '.join(choices)}")
    return value
