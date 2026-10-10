"""What runs and what is installed on each machine (Control -> Actions; ENGINE-GAPS #5).

"Close a program" is picked from what runs ("open on 5 machines") and "Start a program" from what is installed
on that machine, instead of being typed. The Worker reports both (`control.inventory`); a console asks
(`control.programs`).

  * running    -- the latest list per machine, in memory only (it changes by the second; lost on restart,
                  refilled within a minute by the Workers)
  * installed  -- the latest list per machine, kept in `pc_programs`

Scope as everywhere: an Admin sees their department's machines, the Super User every machine (or the ones named).
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from engine.dispatch import Context, handler
from engine.permissions import require_account, require_department_scope, require_role
from protocol import ErrorCode, ProtocolError

NAME_MAX = 120
RUNNING_MAX = 600          # most distinct programs kept per machine
INSTALLED_MAX = 1500

# pc_id -> {"at": iso, "items": [{"name", "count", "memory"}]}
_running: dict[int, dict[str, Any]] = {}


def reset_state() -> None:
    _running.clear()


def _clean_running(raw: Any) -> list[dict[str, Any]]:
    out = []
    for item in (raw if isinstance(raw, list) else [])[:RUNNING_MAX]:
        if isinstance(item, dict) and item.get("name"):
            out.append({"name": str(item["name"])[:NAME_MAX], "count": max(1, int(item.get("count") or 1)),
                        "memory": max(0, int(item.get("memory") or 0))})
    return out


def _clean_installed(raw: Any) -> list[dict[str, Any]]:
    out = []
    for item in (raw if isinstance(raw, list) else [])[:INSTALLED_MAX]:
        if isinstance(item, dict) and item.get("name"):
            cmd = str(item["command"])[:400] if item.get("command") else None
            out.append({"name": str(item["name"])[:NAME_MAX], "command": cmd})
    return out


@handler("control.inventory")
async def inventory(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Worker: {"running"?: [{name, count, memory}], "installed"?: [{name, command?}]} -- either or both."""
    ident = require_account(ctx)
    if ident.pc_id is None:
        raise ProtocolError(ErrorCode.INVALID, "no pc bound to this connection")
    if "running" in payload:
        _running[ident.pc_id] = {"at": datetime.now(timezone.utc).isoformat(), "items": _clean_running(payload["running"])}
    if "installed" in payload and ctx.engine.db.connected:
        await ctx.engine.db.control.save_programs(ident.pc_id, _clean_installed(payload["installed"]))
    return {"accepted": True}


async def _scope(ctx: Context, payload: dict[str, Any]) -> set[int]:
    ident = require_role(ctx, "super_user", "admin")
    db = ctx.engine.db
    wanted = payload.get("pc_ids")
    if wanted is not None:
        if not isinstance(wanted, list):
            raise ProtocolError(ErrorCode.INVALID, "pc_ids must be a list")
        ids = {int(p) for p in wanted}
        for pc_id in ids:
            pc = await db.accounts.pc(pc_id)
            if pc is None:
                raise ProtocolError(ErrorCode.NOT_FOUND, f"no such pc {pc_id}")
            require_department_scope(ident, pc["department_id"])
        return ids
    if ident.role == "admin":
        return {p["id"] for p in await db.accounts.pcs_in_department(ident.department_id)}
    return {p["id"] for p in await db.accounts.list_pcs() if p["department_id"] is not None}


def _by_name(per_pc: dict[int, list[dict[str, Any]]]) -> list[dict[str, Any]]:
    """One row per program name (case-insensitive), with the machines it is on, most widespread first."""
    rows: dict[str, dict[str, Any]] = {}
    for pc_id, items in per_pc.items():
        for it in items:
            row = rows.setdefault(it["name"].lower(), {"name": it["name"], "machines": 0, "pc_ids": [], "command": None})
            if pc_id not in row["pc_ids"]:
                row["pc_ids"].append(pc_id)
                row["machines"] += 1
            row["command"] = row["command"] or it.get("command")
    return sorted(rows.values(), key=lambda r: (-r["machines"], r["name"].lower()))


@handler("control.programs")
async def programs(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"pc_ids"?} (default: the caller's department; the Super User's: every machine).
    -> {"running": [{name, machines, pc_ids}], "installed": [{name, machines, pc_ids, command}], "reporting": n}.
    `reporting` is how many of the machines in scope have reported what runs since the Engine started."""
    scope = await _scope(ctx, payload)
    running = {pc: _running[pc]["items"] for pc in scope if pc in _running}
    installed: dict[int, list[dict[str, Any]]] = {}
    if ctx.engine.db.connected:
        for row in await ctx.engine.db.control.programs_for(sorted(scope)):
            installed[row["pc_id"]] = row["programs"]
    return {"running": _by_name(running), "installed": _by_name(installed), "reporting": len(running),
            "machines": len(scope)}


def running_on(pc_id: int) -> list[dict[str, Any]]:
    return list(_running.get(pc_id, {}).get("items", []))

