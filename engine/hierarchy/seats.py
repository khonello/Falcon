"""Machines knock; Admins give seats (docs/SEATS-AND-SETUP.md, sections 6 and 7; decided with the user 14 Nov 2026).

    knock.hello    {install_token, hostname, os?, mac?, hardware_id?, user?, admin_claim?}   before the handshake: "this installed PC is here"
                   -> {status: waiting} | {status: seated, client_id, client_key, account_id, pc_id, role} (the key once per seating) | {status: collected}
                   With an Admin claim (signed by the store, for this Engine and this PC, unexpired, never used): in at once as an Admin, if an
                   Admin seat is free (docs/SEATS-AND-SETUP.md section 5).
    knocks.list    {}                    the knocking PCs, with what they say about themselves; look-alikes flagged
    seats.summary  {}                    per kind (admin, worker): bought, in use, free, until when, in grace
    seat.give      {knock_id, department_id?}   any Admin: the knocking PC gets a Worker seat in that department (required when departments
                                         exist; with none, the default "New machines"), if one is free
    seat.take      {pc_id}               any Admin: the machine's seat is taken back (never the last Admin seat); it knocks again
    seats.refresh  {}                    any Admin: ask the store now for grants it has not been given
    company.file   {}                    any Admin: the store-signed company file (where this Engine is), given with the Worker setup

Knocking grants nothing: a knocking PC reaches nothing but this. There is no code; look-alike PCs are told apart by their name, who is
signed in, their address and their hardware identity, and two that look alike are flagged. An Engine not registered with the store has no
seat limit (development, tests): `free` is None there, and nothing is taken back for want of a grant.
"""

from __future__ import annotations

import hashlib
import logging
import time
from collections import deque
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler
from engine.permissions import int_field, require_role
from engine.serialize import rows
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

ROLES = ("admin", "worker")
GRACE = timedelta(days=7)
WARN_DAYS = (30, 7, 1)
DEFAULT_DEPARTMENT = "New machines"
ADMIN_DEPARTMENT = "IT"                    # where an Admin's PC that came in with its store claim is put
NEW_PER_ADDRESS = 20                       # new knocking PCs from one address an hour: more is refused for the hour, and flagged
NEW_WINDOW = 3600.0
MAX_WAITING = 5000

_new_from: dict[str, deque[float]] = {}


def reset_state() -> None:
    _new_from.clear()


def _hash(token: str) -> str:
    return hashlib.sha256(("falcon-knock:" + token).encode("utf-8")).hexdigest()


def _clean(value: Any, limit: int) -> str | None:
    text = " ".join(str(value or "").split())[:limit]
    return text or None


def _peer(ctx: Context) -> str | None:
    peer = getattr(ctx.connection, "peer", None)
    return str(peer[0]) if peer else None


# --- counting ---------------------------------------------------------------------------------------------------------

async def valid_grants(engine: Engine, now: datetime | None = None) -> list[dict[str, Any]]:
    """The grants that count now (from their start to the end of their grace), each checked again: a row changed by hand counts for nothing."""
    from engine.store import good_grant

    now = now or datetime.now(timezone.utc)
    out = []
    for g in await engine.db.seats.grants():
        if not (g["valid_from"] <= now < g["valid_until"] + GRACE):
            continue
        if good_grant(engine, g["envelope"]) is None:
            continue
        out.append(g)
    return out


async def summary(engine: Engine, now: datetime | None = None) -> dict[str, Any]:
    now = now or datetime.now(timezone.utc)
    registered = engine.store.registered
    grants = await valid_grants(engine, now) if registered else []
    out: dict[str, Any] = {"registered": registered}
    for role in ROLES:
        mine = [g for g in grants if g["role"] == role]
        in_use = await engine.db.seats.in_use(role)
        bought = sum(g["seats"] for g in mine) if registered else None
        ending = min((g["valid_until"] for g in mine), default=None)
        out[role] = {"bought": bought, "in_use": in_use, "free": None if bought is None else max(0, bought - in_use),
                     "valid_until": max((g["valid_until"] for g in mine), default=None),
                     "next_end": ending,
                     "in_grace": any(g["valid_until"] <= now for g in mine),
                     "grace_ends": min((g["valid_until"] + GRACE for g in mine if g["valid_until"] <= now), default=None)}
    return out


async def _free(engine: Engine, role: str) -> int | None:
    return (await summary(engine))[role]["free"]


# --- knocking ---------------------------------------------------------------------------------------------------------

def _too_many_new(peer: str | None) -> bool:
    if peer is None:
        return False
    now = time.monotonic()
    q = _new_from.setdefault(peer, deque())
    while q and now - q[0] > NEW_WINDOW:
        q.popleft()
    return len(q) >= NEW_PER_ADDRESS


@handler("knock.hello")
async def knock_hello(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """An installed PC says it is here. One row per install token; the answer is what it should do next."""
    engine, db = ctx.engine, ctx.engine.db
    token = str(payload.get("install_token") or "")
    if not 20 <= len(token) <= 200:
        raise ProtocolError(ErrorCode.INVALID, "an install token is needed (the Worker setup makes one)")
    facts = {"hostname": _clean(payload.get("hostname"), 80), "os": _clean(payload.get("os"), 80), "mac": _clean(payload.get("mac"), 40),
             "hardware_id": _clean(payload.get("hardware_id"), 120), "user": _clean(payload.get("user"), 120)}
    if not facts["hostname"]:
        raise ProtocolError(ErrorCode.INVALID, "a machine must say its name")
    peer = _peer(ctx)
    if await db.seats.knock_by_hash(_hash(token)) is None:
        if _too_many_new(peer):
            log.warning("too many new machines knocking from %s", peer)
            await engine.audit.record(None, "knock.flooded", target_type="knocks", target_id=peer or "", detail={"address": peer})
            raise ProtocolError(ErrorCode.CONFLICT, "too many new machines are knocking from this address; try again in an hour")
        if await db.seats.count_waiting() >= MAX_WAITING:
            raise ProtocolError(ErrorCode.UNAVAILABLE, "too many machines are waiting for a seat")
    claim = _check_claim(engine, payload.get("admin_claim"), facts) if payload.get("admin_claim") is not None else None
    row = await db.seats.knock(_hash(token), facts, peer)
    ctx.connection.knock_id = row["id"]
    if row["created"]:
        if peer is not None:
            _new_from.setdefault(peer, deque()).append(time.monotonic())
        await engine.audit.record(None, "knock.new", target_type="knocks", target_id=row["id"],
                                  detail={"hostname": facts["hostname"], "user": facts["user"], "address": peer})
        await engine.push_to_role("admin", "knock.waiting", {"knock_id": row["id"], "hostname": facts["hostname"]})
    if claim is not None and row["status"] == "waiting":
        await _claim_seat(engine, row, claim, payload["admin_claim"])
        row = {**row, "status": "seated", "pc_id": (await db.seats.get_knock(row["id"]))["pc_id"]}
    if row["status"] == "seated":
        if await db.seats.deliver(row["id"]):
            pc = await db.accounts.pc(row["pc_id"])
            assert pc is not None
            await engine.audit.record(None, "seat.collected", target_type="pcs", target_id=row["pc_id"], pc_id=row["pc_id"])
            seat = await db.seats.active(row["pc_id"])
            return {"status": "seated", "client_id": pc["client_id"], "client_key": engine.client_key(pc["client_id"], pc["key_generation"]),
                    "account_id": pc["bound_account_id"], "pc_id": row["pc_id"], "role": seat["role"] if seat else None}
        return {"status": "collected"}                     # its key was handed over already (an Admin takes the seat back and gives it again)
    return {"status": "waiting"}


def _check_claim(engine: Engine, envelope: Any, facts: dict[str, Any]) -> dict[str, Any]:
    """An Admin claim the store signed for this Engine and this PC, still in date. Its single use is checked when it is spent."""
    from common import signed
    from engine.store import parse_time

    try:
        doc = signed.check(envelope, "admin_claim")
    except signed.SignatureError as exc:
        raise ProtocolError(ErrorCode.FORBIDDEN, f"the Admin claim cannot be trusted: {exc}") from exc
    ident = engine.store.identity
    if ident is None or doc.get("engine_id") != ident.get("engine_id"):
        raise ProtocolError(ErrorCode.FORBIDDEN, "the Admin claim is for another Engine")
    try:
        expires = parse_time(str(doc.get("expires_at")))
    except ValueError as exc:
        raise ProtocolError(ErrorCode.FORBIDDEN, "the Admin claim has no end") from exc
    if expires <= datetime.now(timezone.utc):
        raise ProtocolError(ErrorCode.FORBIDDEN, "the Admin claim has expired: sign in again from the Admin setup")
    if str(doc.get("hostname") or "").lower() != (facts["hostname"] or "").lower() or (doc.get("hardware_id") and doc.get("hardware_id") != facts["hardware_id"]):
        raise ProtocolError(ErrorCode.FORBIDDEN, "the Admin claim was made for another machine")
    if not doc.get("claim_id"):
        raise ProtocolError(ErrorCode.FORBIDDEN, "the Admin claim has no id")
    return doc


async def _claim_seat(engine: Engine, knock: dict[str, Any], claim: dict[str, Any], envelope: dict[str, Any]) -> None:
    """The claim is spent and the PC is in as an Admin's workstation, if an Admin seat is free."""
    db = engine.db
    if await db.seats.claim_used(str(claim["claim_id"])):
        raise ProtocolError(ErrorCode.FORBIDDEN, "this Admin claim was used already: sign in again from the Admin setup")
    free = await _free(engine, "admin")
    if free is not None and free <= 0 and engine.store.registered:
        await engine.store.fetch_grants()                                           # bought a moment ago, perhaps: ask the store first
        free = await _free(engine, "admin")
    if free is not None and free <= 0:
        raise ProtocolError(ErrorCode.CONFLICT, "no Admin seat is free: more are bought in the store, or an Admin takes a seat back")
    if not await db.seats.use_claim(str(claim["claim_id"]), str(claim.get("member_email") or ""), knock["id"], envelope):
        raise ProtocolError(ErrorCode.FORBIDDEN, "this Admin claim was used already: sign in again from the Admin setup")
    department_id = await named_department(engine, ADMIN_DEPARTMENT)
    pc_id = await _seat(engine, knock, "admin", department_id, None)
    await db.seats.claim_seated(str(claim["claim_id"]), pc_id)
    await engine.audit.record(None, "seat.claimed", target_type="pcs", target_id=pc_id, pc_id=pc_id,
                              detail={"hostname": knock["hostname"], "member_email": claim.get("member_email"), "claim_id": claim["claim_id"],
                                      "knock_id": knock["id"], "role": "admin"})
    await engine.push_to_role("admin", "seat.given", {"pc_id": pc_id, "hostname": knock["hostname"], "role": "admin"})
    await engine.push_to_role("admin", "machines.changed", {"pc_id": pc_id})


def _alike(knocks: list[dict[str, Any]], seated: list[dict[str, Any]]) -> dict[int, list[str]]:
    """Why each knocking PC looks like another one: the same name, or the same hardware under another name."""
    flags: dict[int, list[str]] = {}
    for k in knocks:
        for other in knocks + seated:
            if other["id"] == k["id"]:
                continue                                           # (one table: an id is one installed PC)
            if other["hostname"] and other["hostname"].lower() == (k["hostname"] or "").lower():
                flags.setdefault(k["id"], []).append(f"another machine is also called {k['hostname']}")
            elif other.get("hardware_id") and other.get("hardware_id") == k.get("hardware_id"):
                flags.setdefault(k["id"], []).append(f"the same hardware as {other['hostname']}")
    return {i: sorted(set(v)) for i, v in flags.items()}


@handler("knocks.list")
async def knocks_list(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    require_role(ctx, "super_user", "admin")
    db = ctx.engine.db
    waiting = await db.seats.knocks("waiting")
    seated = await db.seats.knocks("seated")
    flags = _alike(waiting, seated)
    return {"knocks": [{**r, "look_alike": flags.get(r["id"], [])} for r in rows(waiting)]}


@handler("seats.summary")
async def seats_summary(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    require_role(ctx, "super_user", "admin")
    got = await summary(ctx.engine)
    for role in ROLES:
        for k in ("valid_until", "next_end", "grace_ends"):
            if got[role][k] is not None:
                got[role][k] = got[role][k].isoformat()
    return got


# --- giving and taking ------------------------------------------------------------------------------------------------

async def _department(engine: Engine, asked: int | None) -> int:
    departments = await engine.db.accounts.list_departments()
    if asked is not None:
        if asked not in {d["id"] for d in departments}:
            raise ProtocolError(ErrorCode.NOT_FOUND, "no such department")
        return asked
    if departments:
        raise ProtocolError(ErrorCode.INVALID, "say which department this machine goes into")
    return await named_department(engine, DEFAULT_DEPARTMENT)


async def named_department(engine: Engine, name: str) -> int:
    """The department of that name, made if it is not there yet (a department is a label in version 1: an Admin moves a machine whenever)."""
    import asyncpg

    found = next((d for d in await engine.db.accounts.list_departments() if d["name"].lower() == name.lower()), None)
    if found is not None:
        return int(found["id"])
    try:
        return await engine.db.accounts.create_department(name, None)
    except asyncpg.UniqueViolationError:                                            # made by another machine at the same moment
        return int(next(d["id"] for d in await engine.db.accounts.list_departments() if d["name"].lower() == name.lower()))


@handler("seat.give")
async def seat_give(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "super_user", "admin")
    engine, db = ctx.engine, ctx.engine.db
    knock = await db.seats.get_knock(int_field(payload, "knock_id"))
    if knock is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such knocking machine")
    if knock["status"] != "waiting":
        raise ProtocolError(ErrorCode.CONFLICT, f"{knock['hostname']} already has a seat")
    department_id = await _department(engine, int_field(payload, "department_id", required=False))
    free = await _free(engine, "worker")
    if free is not None and free <= 0:
        raise ProtocolError(ErrorCode.CONFLICT, "no Worker seat is free: more are bought in the store")
    pc_id = await _seat(engine, knock, "worker", department_id, ident.account_id)
    await engine.audit.record(ctx, "seat.given", target_type="pcs", target_id=pc_id, pc_id=pc_id,
                              detail={"hostname": knock["hostname"], "department_id": department_id, "knock_id": knock["id"], "role": "worker"})
    await engine.push_to_role("admin", "seat.given", {"pc_id": pc_id, "hostname": knock["hostname"], "role": "worker"})
    await engine.push_to_role("admin", "machines.changed", {"pc_id": pc_id})
    return {"pc_id": pc_id, "hostname": knock["hostname"], "department_id": department_id, "role": "worker"}


async def _seat(engine: Engine, knock: dict[str, Any], role: str, department_id: int, by_account_id: int | None) -> int:
    """The knocking PC is in: its account and machine (made, or brought back with a new key), its seat, and a nudge on its open connection."""
    db = engine.db
    if knock["pc_id"] is not None and await _role_of(engine, knock["pc_id"]) != role:
        knock = {**knock, "pc_id": None}                                            # a Worker PC become an Admin's (or back): a new account
    if knock["pc_id"] is None:
        from engine.hierarchy.accounts import provision

        made = await provision(engine, role, department_id, knock["hostname"], seat_by=by_account_id)     # (and its seat)
        pc_id = made["pc_id"]
    else:
        pc_id = knock["pc_id"]
        await db.seats.reactivate(pc_id)
        await db.accounts.move_pc(pc_id, department_id)
        await db.accounts.rekey_pc(pc_id)                                           # never the key it had before
        await db.seats.give(pc_id, role, by_account_id)
    await db.seats.seated(knock["id"], pc_id)
    for conn in list(engine.connections):
        if getattr(conn, "knock_id", None) == knock["id"]:
            await conn.push("knock.seated", {"pc_id": pc_id})
    return pc_id


async def _role_of(engine: Engine, pc_id: int) -> str | None:
    return await engine.db.seats.last_role(pc_id)


async def take_back(engine: Engine, pc_id: int, by_account_id: int | None, reason: str) -> bool:
    """The machine's seat goes: its account stops, its key stops working, its connections close; it knocks again, and its history stays."""
    db = engine.db
    if not await db.seats.take(pc_id, by_account_id, reason):
        return False
    pc = await db.accounts.pc(pc_id)
    if pc and pc["bound_account_id"]:
        await db.accounts.offboard(pc["bound_account_id"])
    await db.accounts.rekey_pc(pc_id)
    await db.seats.back_to_waiting(pc_id)
    for conn in list(engine.connections):
        ident = getattr(getattr(conn, "ctx", None), "identity", None)
        if ident is not None and ident.pc_id == pc_id:
            conn.writer.close()
    await engine.audit.record(None, "seat.taken", target_type="pcs", target_id=pc_id, pc_id=pc_id,
                              detail={"hostname": pc["hostname"] if pc else None, "reason": reason, "by_account_id": by_account_id})
    await engine.push_to_role("admin", "seat.taken", {"pc_id": pc_id, "hostname": pc["hostname"] if pc else None, "reason": reason})
    await engine.push_to_role("admin", "machines.changed", {"pc_id": pc_id})
    return True


@handler("seat.take")
async def seat_take(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "super_user", "admin")
    engine, db = ctx.engine, ctx.engine.db
    pc_id = int_field(payload, "pc_id")
    seat = await db.seats.active(pc_id)
    if seat is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "that machine has no seat")
    if seat["role"] == "admin" and await db.seats.in_use("admin") <= 1:
        raise ProtocolError(ErrorCode.FORBIDDEN, "the last Admin seat cannot be taken back: nobody could give a seat after it")
    await take_back(engine, pc_id, ident.account_id, "taken back by an Admin")
    return {"pc_id": pc_id, "role": seat["role"]}


@handler("seats.refresh")
async def seats_refresh(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    require_role(ctx, "super_user", "admin")
    if not ctx.engine.store.registered:
        raise ProtocolError(ErrorCode.CONFLICT, "this Engine is not registered with the store, so it has no seats to look for")
    added = await ctx.engine.store.fetch_grants()
    await ctx.engine.store.report_usage()
    if added:
        await ctx.engine.push_to_role("admin", "seats.changed", {"added": added})
    return {"added": added}


@handler("company.file")
async def company_file(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """What the console puts in the Worker setup zip beside the setup (docs/SEATS-AND-SETUP.md section 6): the file as the store signed it."""
    import json

    from common import signed

    require_role(ctx, "super_user", "admin")
    store = ctx.engine.store
    if not store.registered:
        raise ProtocolError(ErrorCode.CONFLICT, "this Engine is not registered with the store, so it has no company file")
    path = store.path.parent / "company.falcon"
    try:
        envelope = json.loads(path.read_text(encoding="utf-8"))
        doc = signed.check(envelope, "company")
    except (OSError, ValueError, signed.SignatureError) as exc:
        raise ProtocolError(ErrorCode.UNAVAILABLE, f"the company file cannot be read ({exc}): ask the store again with cert renew") from exc
    slug = "".join(ch for ch in str(doc.get("company_name") or "company").lower() if ch.isalnum()) or "company"
    return {"file_name": f"{slug}.falcon", "envelope": envelope, "names": doc.get("names"), "port": doc.get("port"),
            "certificates": len(doc.get("certificates") or [])}


# --- at sign-in -------------------------------------------------------------------------------------------------------

async def refused_for_no_seat(engine: Engine, client_id: str, nonce: str, presented: str) -> bool:
    """A machine whose seat was taken back, proving it holds the key that seat had: it is told `no_seat` (and knocks again). Anyone else
    gets the same refusal as every failed sign-in."""
    from engine.auth import verify

    pc = await engine.db.seats.taken_from(client_id)
    if pc is None:
        return False
    return any(verify(engine.master_secret, client_id, nonce, presented, g) for g in range(max(1, pc["key_generation"] - 2), pc["key_generation"]))


# --- the end of a seat period (daily) ---------------------------------------------------------------------------------

async def watch_periods(engine: Engine, now: datetime | None = None) -> int:
    """Issues before a grant ends (30, 7, 1 days) and during its grace; after the grace, seats in use beyond what valid grants cover are
    taken back, the most recently given first (never the last Admin seat). Returns how many were taken back."""
    if not engine.db.connected or not engine.store.registered:
        return 0
    from engine.console import issues
    from engine.store import good_grant

    now = now or datetime.now(timezone.utc)
    for g in await engine.db.seats.grants():
        if good_grant(engine, g["envelope"]) is None:
            continue
        left = g["valid_until"] - now
        kind = "Admin" if g["role"] == "admin" else "Worker"
        when = g["valid_until"].strftime("%d %b %Y")
        for days in WARN_DAYS:
            if timedelta(0) < left <= timedelta(days=days):
                await issues.raise_issue(engine, type_="seats", severity={30: "low", 7: "medium", 1: "high"}[days],
                                         title=f"{g['seats']} {kind} seats end on {when}", subject="Renew them in the store",
                                         source_table=f"seat_grants:{days}d", source_id=g["id"],
                                         detail={"grant_id": g["grant_id"], "role": g["role"], "seats": g["seats"], "valid_until": g["valid_until"].isoformat()})
                break
        if g["valid_until"] <= now < g["valid_until"] + GRACE:
            ends = (g["valid_until"] + GRACE).strftime("%d %b %Y")
            await issues.raise_issue(engine, type_="seats", severity="critical", title=f"{g['seats']} {kind} seats ended on {when}",
                                     subject=f"Machines keep working until {ends}; renew in the store before then",
                                     source_table="seat_grants:grace", source_id=g["id"],
                                     detail={"grant_id": g["grant_id"], "role": g["role"], "grace_ends": (g["valid_until"] + GRACE).isoformat()})
    taken = 0
    counts = await summary(engine, now)
    for role in ROLES:
        over = counts[role]["in_use"] - (counts[role]["bought"] or 0)
        if over <= 0:
            continue
        if role == "admin":
            over = min(over, counts[role]["in_use"] - 1)                     # never the last Admin seat
        for seat in await engine.db.seats.newest(role, max(0, over)):
            if await take_back(engine, seat["pc_id"], None, "the seat period ended"):
                taken += 1
    return taken



# --- the issue a seat period raises (engine/console/plays.py draws it) -------------------------------------------------

def view(issue: dict[str, Any]) -> tuple[str, list[list[Any]], list[dict[str, Any]], list[str]]:
    from engine.console.plays import _opt

    d = issue["detail"] or {}
    kind = "Admin" if d.get("role") == "admin" else "Worker"
    if "grace_ends" in d:
        lead = (f"{d.get('seats', '')} {kind} seats have ended. The machines using them keep working until {str(d['grace_ends'])[:10]}; then any "
                f"beyond the seats still bought lose access and knock again. Renew them in the store.")
    else:
        lead = f"{d.get('seats', '')} {kind} seats end on {str(d.get('valid_until', ''))[:10]}. Renew them in the store before then."
    facts = [["Seats", f"{d.get('seats', '')} {kind}"], ["Ends", str(d.get("valid_until") or d.get("grace_ends") or "")[:10]]]
    return lead, facts, [_opt("check", "Look for new seats now", "Ask the store at once for seats bought since it last asked. "
                              "If these have been renewed, this is resolved.", "Look now", "Resolved")], []


async def act(ctx: Context, issue: dict[str, Any], key: str) -> dict[str, Any]:
    from engine.console.plays import _finish

    engine = ctx.engine
    added = await engine.store.fetch_grants()
    d = issue["detail"] or {}
    renewed = any(g["role"] == d.get("role") and g["grant_id"] != d.get("grant_id") and g["valid_until"].isoformat() > str(d.get("valid_until") or d.get("grace_ends") or "")
                  for g in await valid_grants(engine))
    who = (ctx.viewed_by or ctx.identity).account_id
    await engine.db.issues.log(issue["id"], "acted", f"Asked the store: {added} new grant(s)", who)
    if renewed:
        return await _finish(ctx, issue, "Renewed")
    return {"issue_id": issue["id"], "state": issue["state"], "said": "No renewal yet: they are renewed in the store"}
