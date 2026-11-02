"""Private: only the people the owner names may open a file or folder, or run a program (ENGINE-GAPS #3; the user, 21 Oct and 2 Nov 2026).

The refusal is Windows' own: the established mechanism (the user, 2 Nov 2026). The machine the mark is on is told to set the item's
permissions so that only the named people -- and the machine's system account, when the owner allows it (backup, antivirus) -- may open or run
it; anyone else gets Windows' "access denied". The Worker keeps the permissions the item had before and puts them back when the mark is
lifted. Windows' own audit of failed opens says who was refused; the Worker reads it and tells the Engine, which notes it on the mark, in the
audit trail and to the owner, and the person refused gets a quiet note from Falcon saying the file is private and whose it is.

    to the machine:   private.apply {mark_id, path, kind, readers: [Windows names], owner, allow_system}     (and again at every connect)
                      private.lift  {mark_id, path}
    from the machine: private.applied {mark_id, ok, granted?, missing?, error?}
                      private.refused {path, who, process?, at}
    marks.readers {mark_id, readers: [account ids], allow_system?}   the owner changes who is named (nobody can ask to be added)

A person is named by their Falcon account; on the machine they are the Windows user last signed in on the machine their account is bound to
(`pcs.windows_user`, said by the Worker at connect). Someone whose Windows name is not known yet is reported back as `missing` and left out
until it is.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler
from engine.permissions import int_field, require_account, require_role, str_field
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine


async def _order(engine: Engine, mark: dict[str, Any]) -> dict[str, Any]:
    readers = (await engine.db.marks.readers([mark["id"]]))[mark["id"]]
    names = await engine.db.accounts.windows_names(sorted(set(readers) | {mark["by_account_id"]}))
    return {"mark_id": mark["id"], "path": mark["path"], "kind": mark["kind"], "allow_system": bool(mark.get("allow_system", True)),
            "owner": names.get(mark["by_account_id"]),
            "readers": sorted({n for a, n in names.items() if n and (a in readers or a == mark["by_account_id"])}),
            "unknown": sorted(a for a in set(readers) | {mark["by_account_id"]} if not names.get(a))}


async def apply(engine: Engine, mark_id: int) -> bool:
    """Tell the mark's machine to make it private now. False when the machine is away: it is told again when it connects."""
    mark = await engine.db.marks.get(mark_id)
    if mark is None or mark.get("protection") != "private" or mark.get("unmarked_at") is not None:
        return False
    if mark["pc_id"] not in engine.online_pc_ids():
        await engine.db.marks.set_applied(mark_id, {"ok": False, "waiting": "the machine is not connected; it is done when it is"})
        return False
    await engine.push_to_pc(mark["pc_id"], "private.apply", await _order(engine, mark))
    return True


async def lift(engine: Engine, mark: dict[str, Any]) -> None:
    await engine.push_to_pc(mark["pc_id"], "private.lift", {"mark_id": mark["id"], "path": mark["path"]})
    await engine.audit.record(None, "private.lift_asked", target_type="resource_marks", target_id=mark["id"], pc_id=mark["pc_id"])


async def on_pc_online(engine: Engine, pc_id: int) -> None:
    """Proactive: every private mark on a machine that (re)connects is applied again; applying is idempotent on the machine."""
    if not engine.db.connected:
        return
    for mark in await engine.db.marks.private_on_pc(pc_id):
        await engine.push_to_pc(pc_id, "private.apply", await _order(engine, mark))


@handler("private.applied")
async def applied(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_account(ctx)
    mark = await ctx.engine.db.marks.get(int_field(payload, "mark_id"))
    if mark is None or mark["pc_id"] != ident.pc_id:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such private mark on this machine")
    said = {"ok": bool(payload.get("ok")), "at": datetime.now(timezone.utc).isoformat(), "granted": payload.get("granted") or [],
            "missing": payload.get("missing") or [], "error": (str(payload["error"])[:300] if payload.get("error") else None)}
    await ctx.engine.db.marks.set_applied(mark["id"], said)
    await ctx.engine.audit.record(ctx, "private.applied" if said["ok"] else "private.apply_failed", target_type="resource_marks", target_id=mark["id"],
                                  pc_id=ident.pc_id, detail=said)
    if not said["ok"]:
        await ctx.engine.push_to_account(mark["by_account_id"], "private.apply_failed", {"mark_id": mark["id"], "name": mark["name"], "error": said["error"]})
    return {"recorded": True}


@handler("private.refused")
async def refused(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Windows refused someone an item made private on this machine; the Worker read it in Windows' own audit of failed opens."""
    ident = require_account(ctx)
    if ident.pc_id is None:
        raise ProtocolError(ErrorCode.INVALID, "no machine on this connection")
    db = ctx.engine.db
    path = str_field(payload, "path")
    from engine.console.marks import inside, norm

    mark = next((m for m in await db.marks.private_on_pc(ident.pc_id) if norm(m["path"]) == norm(path) or inside(m, ident.pc_id, path)), None)
    who = str(payload.get("who") or "")[:120] or None
    account_id = await db.accounts.by_windows_user(who) if who else None
    try:
        at = datetime.fromisoformat(str(payload.get("at")).replace("Z", "+00:00"))
    except (TypeError, ValueError):
        at = datetime.now(timezone.utc)
    at = at if at.tzinfo else at.replace(tzinfo=timezone.utc)
    refusal = await db.marks.add_refusal(mark["id"] if mark else None, ident.pc_id, who, account_id, str(payload.get("process") or "")[:200] or None, path, at)
    await ctx.engine.audit.record(ctx, "private.refused", target_type="private_refusals", target_id=refusal, pc_id=ident.pc_id,
                                  detail={"path": path, "who": who, "process": payload.get("process"), "mark_id": mark["id"] if mark else None})
    if mark is not None:
        await ctx.engine.push_to_account(mark["by_account_id"], "private.refused", {"mark_id": mark["id"], "name": mark["name"], "who": who,
                                                                                   "account_id": account_id, "at": at.isoformat()})
        owner = (await db.accounts.display_names_for(account_id, [mark["by_account_id"]])).get(mark["by_account_id"]) if account_id else None
        return {"recorded": True, "mark_id": mark["id"], "name": mark["name"], "owner": owner}
    return {"recorded": True, "mark_id": None}


@handler("marks.readers")
async def readers(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"mark_id", "readers": [account ids], "allow_system"?} -- the owner changes who may open a private item. Nobody can ask to be added."""
    ident = require_role(ctx, "super_user", "admin")
    db = ctx.engine.db
    mark = await db.marks.get(int_field(payload, "mark_id"))
    if mark is None or mark.get("unmarked_at") is not None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such mark")
    if mark.get("protection") != "private":
        raise ProtocolError(ErrorCode.CONFLICT, "only a private mark names who may open it")
    if mark["by_account_id"] != ident.account_id:
        raise ProtocolError(ErrorCode.FORBIDDEN, "only the person who made it private changes who may open it")
    from engine.console.marks import _readers

    named = _readers(payload)
    allow_system = payload.get("allow_system", mark.get("allow_system", True))
    if not isinstance(allow_system, bool):
        raise ProtocolError(ErrorCode.INVALID, "allow_system is true or false")
    await db.marks.set_readers(mark["id"], sorted(set(named) | {ident.account_id}), allow_system)
    await ctx.engine.audit.record(ctx, "private.readers_changed", target_type="resource_marks", target_id=mark["id"], pc_id=mark["pc_id"],
                                  detail={"readers": named, "allow_system": allow_system})
    told = await apply(ctx.engine, mark["id"])
    return {"mark_id": mark["id"], "readers": sorted(set(named) | {ident.account_id}), "allow_system": allow_system, "applied_now": told}
