"""Licence codes: a machine joins with a code from the licence that was bought (the user, 2 Nov 2026).

A licence, bought from the licence store, carries codes: admin codes and worker codes. During setup the person installing gives one (the
installer's `--code`); the machine asks to join with it (`enroll.request {licence_code}`), the Engine checks it, and the machine joins at once
as what the code is for -- an IT Admin's workstation or a person's PC -- with nobody typing a code shown on its screen. A code covers a number
of machines (seats); each one that joins with it uses one. It can expire and be withdrawn. Codes are held only as a hash, like a password.

    licence.import {name, reference?, codes: [{code, role: admin|worker, seats?: 1, department?, expires_at?}]}   any IT Admin
                   -> {licence_id, added, already_known}
    licence.list   {}               -> {codes: [{id, licence, last4, role, seats, used, department, expires_at, revoked_at, machines}]}
    licence.revoke {code_id}        -> the code lets no further machine in (the ones that joined stay)

What a code is not: a key. A machine that joins with one is given its own key, as before, and the code is never sent anywhere again. A wrong
code is refused plainly; five wrong ones from one address within an hour and that address is refused for the hour (guessing a code is slow).

Still to be decided with the user: the licence store itself (where licences are bought and how its files are signed); until then a licence's
codes are imported here from what the store hands over (`licence import <file>` in the TUI).
"""

from __future__ import annotations

import hashlib
import time
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler
from engine.permissions import int_field, require_head, str_field
from engine.serialize import rows
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

ROLES = ("admin", "worker")
MAX_CODES = 5000                                  # in one import
MAX_SEATS = 100000
WRONG_LIMIT = 5                                   # wrong codes from one address ...
WRONG_WINDOW = 3600.0                             # ... within this many seconds, and that address is refused until the hour has passed
DEFAULT_DEPARTMENT = {"admin": "IT", "worker": "New machines"}

_wrong: dict[str, list[float]] = {}               # address -> when its wrong codes were given


def reset_state() -> None:
    _wrong.clear()


def normal(code: str) -> str:
    """A code as the store prints it, whatever was typed: no spaces or dashes, upper case."""
    return "".join(ch for ch in str(code) if ch.isalnum()).upper()


def code_hash(code: str) -> str:
    return hashlib.sha256(("falcon-licence:" + normal(code)).encode("utf-8")).hexdigest()


def _refused_address(peer: str | None) -> bool:
    if peer is None:
        return False
    now = time.monotonic()
    recent = [t for t in _wrong.get(peer, []) if now - t < WRONG_WINDOW]
    _wrong[peer] = recent
    return len(recent) >= WRONG_LIMIT


def _wrong_code(peer: str | None) -> None:
    if peer is not None:
        _wrong.setdefault(peer, []).append(time.monotonic())


async def check(engine: Engine, code: str, level: str, peer: str | None) -> dict[str, Any]:
    """The code a machine gave at setup, if it lets a machine of this level in now. Raises with a plain reason otherwise."""
    if _refused_address(peer):
        raise ProtocolError(ErrorCode.FORBIDDEN, "too many wrong licence codes from this address; try again in an hour")
    if not normal(code):
        raise ProtocolError(ErrorCode.INVALID, "the licence code is empty")
    found = await engine.db.licences.by_hash(code_hash(code))
    if found is None:
        _wrong_code(peer)
        await engine.audit.record(None, "licence.wrong_code", target_type="client", target_id=peer or "unknown", detail={"level": level})
        raise ProtocolError(ErrorCode.FORBIDDEN, "that is not a licence code this organisation has")
    if found["role"] != level:
        raise ProtocolError(ErrorCode.FORBIDDEN, f"that is {'an admin' if found['role'] == 'admin' else 'a worker'} code: install the "
                                                 f"{'admin console' if found['role'] == 'admin' else 'worker software'} with it")
    if found["revoked_at"] is not None:
        raise ProtocolError(ErrorCode.FORBIDDEN, "that licence code was withdrawn")
    if found["expires_at"] is not None and found["expires_at"] <= datetime.now(timezone.utc):
        raise ProtocolError(ErrorCode.FORBIDDEN, "that licence code has expired")
    if found["used"] >= found["seats"]:
        raise ProtocolError(ErrorCode.CONFLICT, "that licence code has no machines left")
    return found


async def department_for(engine: Engine, code: dict[str, Any], asked: int | None, level: str) -> int:
    """Where a machine joining with a code goes: the department it asked for, else the code's, else IT for an Admin and "New machines" for a
    worker. A department is a label (version 1): an Admin moves the machine on the Departments page whenever they like."""
    if asked is not None:
        return asked
    name = code.get("department") or DEFAULT_DEPARTMENT[level]
    found = next((d for d in await engine.db.accounts.list_departments() if d["name"].lower() == name.lower()), None)
    if found is not None:
        return int(found["id"])
    import asyncpg

    try:
        return await engine.db.accounts.create_department(name, None)
    except asyncpg.UniqueViolationError:                                                # made by another joining at the same moment
        return int(next(d["id"] for d in await engine.db.accounts.list_departments() if d["name"].lower() == name.lower()))


@handler("licence.import")
async def licence_import(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_head(ctx)
    name = " ".join(str_field(payload, "name").split())[:120]
    if not name:
        raise ProtocolError(ErrorCode.INVALID, "name the licence")
    reference = str(payload.get("reference") or "").strip()[:120] or None
    given = payload.get("codes")
    if not isinstance(given, list) or not given or len(given) > MAX_CODES:
        raise ProtocolError(ErrorCode.INVALID, f"codes is a list of 1 to {MAX_CODES}")
    codes = []
    seen: set[str] = set()
    for i, c in enumerate(given):
        if not isinstance(c, dict):
            raise ProtocolError(ErrorCode.INVALID, f"code {i}: an object {{code, role, seats?, department?, expires_at?}}")
        plain = normal(str(c.get("code") or ""))
        if len(plain) < 8:
            raise ProtocolError(ErrorCode.INVALID, f"code {i}: too short to be a licence code (8 letters or digits at least)")
        role = str_field(c, "role", choices=ROLES)
        seats = int(c.get("seats") or 1)
        if not 1 <= seats <= MAX_SEATS:
            raise ProtocolError(ErrorCode.INVALID, f"code {i}: seats is 1 to {MAX_SEATS}")
        expires = c.get("expires_at")
        if expires:
            try:
                expires = datetime.fromisoformat(str(expires).replace("Z", "+00:00"))
            except ValueError as exc:
                raise ProtocolError(ErrorCode.INVALID, f"code {i}: expires_at must be ISO 8601") from exc
            expires = expires if expires.tzinfo else expires.replace(tzinfo=timezone.utc)
        h = code_hash(plain)
        if h in seen:
            continue
        seen.add(h)
        codes.append({"code_hash": h, "last4": plain[-4:], "role": role, "seats": seats,
                      "department": (" ".join(str(c.get("department") or "").split())[:80] or None), "expires_at": expires or None})
    licence_id, added, known = await ctx.engine.db.licences.import_(name, reference, codes, ident.account_id)
    await ctx.engine.audit.record(ctx, "licence.imported", target_type="licences", target_id=licence_id,
                                  detail={"name": name, "reference": reference, "added": added, "already_known": known,
                                          "admin": sum(c["role"] == "admin" for c in codes), "worker": sum(c["role"] == "worker" for c in codes)})
    return {"licence_id": licence_id, "added": added, "already_known": known}


@handler("licence.list")
async def licence_list(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    require_head(ctx)
    db = ctx.engine.db
    out = rows(await db.licences.list())
    for c in out:
        c["machines"] = rows(await db.licences.joined_with(c["id"]))
        c["left"] = c["seats"] - c["used"]
    return {"codes": out}


@handler("licence.revoke")
async def licence_revoke(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_head(ctx)
    code_id = int_field(payload, "code_id")
    if not await ctx.engine.db.licences.revoke(code_id, ident.account_id):
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such licence code, or it was withdrawn already")
    await ctx.engine.audit.record(ctx, "licence.revoked", target_type="licence_codes", target_id=code_id)
    return {"code_id": code_id, "revoked": True}
