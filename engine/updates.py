"""Update & deployment model (spec 9).

  * the head of the organisation approves version N+1 -- hard gate: every PC must be confirmed on N first.
  * Rollout cascades: Admins execute it within their own departments (worker clients are told
    to update; they retry on idle by themselves).
  * One-step-back compatibility: N supports N-1 only; a PC on N-1 mid-rollout is fully normal.
  * Failed attempts are retried by the client when idle; past a threshold (open item 10.4,
    count-based here and tunable via FALCON_UPDATE_ESCALATION_FAILURES) the failure escalates
    to that PC's Admin as an actionable notice and an 'update_status' report.
  * the head of the organisation sees an aggregate rollout-health view grouped by department, never per-PC
    noise -- and can prompt an Admin whose department looks stalled.
"""

from __future__ import annotations

import logging
from typing import Any

from engine import permissions
from engine.dispatch import Context, handler
from engine.hierarchy import reports
from engine.permissions import (
    int_field,
    kept,
    org_wide,
    require_account,
    require_department_scope,
    require_head,
    require_role,
    str_field,
)
from engine.serialize import row, rows
from protocol import ErrorCode, ProtocolError

log = logging.getLogger(__name__)


def _behind_view(rows_: list[dict[str, Any]]) -> list[dict[str, Any]]:
    # `failures` is how many attempts have been made and lost: what the head of the organisation reads to tell a
    # machine that is retrying from one that has given up. A PC with no status row has made none.
    return rows([{"pc_id": r["id"], "hostname": r["hostname"], "department_id": r["department_id"],
                  "current_version_id": r["current_version_id"],
                  "failures": r.get("attempt_failure_count") or 0,
                  "last_attempt_at": r.get("last_attempt_at"),
                  "escalated": r.get("escalated_at") is not None} for r in rows_])


@handler("updates.current")
async def current(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    require_account(ctx)
    return {"version": row(await ctx.engine.db.updates.current_version())}


@handler("updates.approve")
async def approve(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """The head of the organisation only. {"version": "1.2.0"}. Refused while any PC is not confirmed on the
    current version -- the system never has more than N and N+1 in flight."""
    ident = require_head(ctx)
    version = str_field(payload, "version")
    db = ctx.engine.db
    if await db.updates.version_by_string(version):
        raise ProtocolError(ErrorCode.CONFLICT, f"version {version} already approved")
    cur = await db.updates.current_version()
    left_out: set[int] = {x["pc_id"] for x in await db.updates.exclusions("next")}      # machines the coming approval does not wait for
    if cur is not None:
        behind = await db.updates.pcs_behind(cur["id"])
        chosen = payload.get("leave_out")
        if chosen:
            if not isinstance(chosen, list) or not all(isinstance(i, int) for i in chosen) or not set(chosen) <= {b["id"] for b in behind}:
                raise ProtocolError(ErrorCode.INVALID, "leave_out must be machines that are behind")
            reason = " ".join(str(payload.get("reason") or "").split())[:300]
            if not reason:
                raise ProtocolError(ErrorCode.INVALID, "leaving machines out of the gate needs a reason")
            for pc_id in chosen:
                await db.updates.exclude_from_gate(pc_id, "next", reason, ident.account_id)
            left_out |= set(chosen)
        behind = [b for b in behind if b["id"] not in left_out]
        if behind:
            raise ProtocolError(ErrorCode.CONFLICT,
                                f"{len(behind)} PC(s) are not yet confirmed on {cur['version_string']}: "
                                + ", ".join(b["hostname"] for b in behind[:5]))
    version_id = await db.updates.approve_version(version, ident.account_id)
    await db.updates.convert_exclusions(version)
    await db.updates.staged_done(version)
    await ctx.engine.audit.record(ctx, "update.approved", target_type="versions", target_id=version_id,
                                  detail={"version": version})
    await ctx.engine.push_to_role("admin", "update.approved", {"version_id": version_id, "version": version})
    from engine.console import accountability

    for pc in await db.accounts.list_pcs():          # every machine must be on it within the time the rule allows
        if pc["department_id"] is not None and pc["id"] not in left_out:
            await accountability.watch(ctx.engine, "version", target_table=f"version:{version}", target_id=pc["id"], kind="pc",
                                       pc_id=pc["id"], department_id=pc["department_id"], label=pc["hostname"],
                                       extra={"version_id": version_id, "version": version})
    return {"version_id": version_id, "version": version, "left_out": sorted(left_out)}


@handler("updates.rollout_department")
async def rollout_department(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Admin executes the approved rollout for their own department (the head of the organisation may too).
    {"department_id"?} -- targets every PC in the department not yet on the current version."""
    ident = require_role(ctx, "super_user", "admin")
    department_id = int_field(payload, "department_id", required=org_wide(ident)) or ident.department_id
    require_department_scope(ident, department_id)
    db = ctx.engine.db
    cur = await db.updates.current_version()
    if cur is None:
        raise ProtocolError(ErrorCode.CONFLICT, "no approved version")
    targets = [b for b in await db.updates.pcs_behind(cur["id"]) if b["department_id"] == department_id]
    if not targets:
        return {"version": cur["version_string"], "targeted": []}
    await db.updates.set_target([t["id"] for t in targets], cur["id"])
    for t in targets:
        await ctx.engine.push_to_pc(t["id"], "update.available", {"version_id": cur["id"],
                                                                  "version": cur["version_string"]})
    await ctx.engine.audit.record(ctx, "update.rollout", target_type="departments", target_id=department_id,
                                  detail={"version": cur["version_string"], "pcs": [t["id"] for t in targets]})
    return {"version": cur["version_string"], "targeted": _behind_view(targets)}


@handler("updates.report_status")
async def report_status(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Worker client reports an attempt: {"version": str, "succeeded": bool, "running": str?}
    -- `running` (the version the PC is actually on) is required for a failed first report.
    Past the escalation threshold, failures become an actionable notice to the PC's Admin."""
    ident = require_account(ctx)
    if ident.pc_id is None:
        raise ProtocolError(ErrorCode.INVALID, "no pc bound to this connection")
    version = str_field(payload, "version")
    succeeded = bool(payload.get("succeeded", False))
    db = ctx.engine.db
    v = await db.updates.version_by_string(version)
    if v is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, f"unknown version {version}")
    # `running` (what the PC is actually on) is recorded when it is an approved version; an
    # unknown build (a fresh install) leaves current_version_id NULL = never confirmed, behind.
    running = str_field(payload, "running", required=False)
    rv = await db.updates.version_by_string(running) if running else None
    error = " ".join(str(payload.get("error") or "").split())[:200] or None
    st = await db.updates.record_attempt(ident.pc_id, v["id"], succeeded, rv["id"] if rv else None, error)
    if succeeded:
        await db.updates.log_version(ident.pc_id, running or version)
    await ctx.engine.audit.record(ctx, "update.attempt", target_type="pc_version_status", target_id=ident.pc_id,
                                  detail={"version": version, "succeeded": succeeded,
                                          "failures": st["attempt_failure_count"]})
    from engine.console import issues

    cur = await db.updates.current_version()
    if succeeded and cur is not None and (rv is None or rv["id"] == cur["id"] or v["id"] == cur["id"]):
        await issues.resolve_source(ctx.engine, "pc_version_status", ident.pc_id, f"Now on {version}")
    elif not succeeded:
        await issues.raise_issue(
            ctx.engine, type_="update", severity="low", title="One version behind", subject=f"{running or 'unknown'} -> {version}",
            pc_id=ident.pc_id, source_table="pc_version_status", source_id=ident.pc_id, state="waiting", label="Retrying",
            detail={"current": running, "target": version, "attempts": st["attempt_failure_count"],
                    "last_attempt_at": st["last_attempt_at"].isoformat() if st.get("last_attempt_at") else None})
        found = await db.issues.by_source("pc_version_status", ident.pc_id)
        if found:
            await db.issues.set_detail(found["id"], {"attempts": st["attempt_failure_count"], "target": version,
                                                     "current": running or found["detail"].get("current")})
    escalated = False
    threshold = ctx.engine.settings.update_escalation_failures
    if not succeeded and st["attempt_failure_count"] >= threshold and st["escalated_at"] is None:
        await db.updates.mark_escalated(ident.pc_id)
        escalated = True
        found = await db.issues.by_source("pc_version_status", ident.pc_id)
        if found:
            await db.issues.set_severity(found["id"], "high", "Update past the escalation limit", f"{running or 'unknown'} -> {version}")
            admins = [a for a in await db.accounts.active_admins() if permissions.ADMIN_SCOPE == "organisation" or a["department_id"] == ident.department_id]
            if not admins:
                await db.issues.escalate(found["id"], None)
            await db.issues.log(found["id"], "escalated", f"Failed {st['attempt_failure_count']} times: past the limit")
        await reports.emit(ctx.engine, "update_status", source_table="pc_version_status", source_id=st["id"],
                           summary=f"update to {version} failed {st['attempt_failure_count']}x on pc {ident.pc_id}")
        await ctx.engine.push_to_role("admin", "update.escalated",
                                      {"pc_id": ident.pc_id, "version": version,
                                       "failures": st["attempt_failure_count"]},
                                      department_id=ident.department_id)
    return {"failures": st["attempt_failure_count"], "escalated": escalated,
            "current_version_id": st["current_version_id"], "target_version_id": st["target_version_id"]}


@handler("updates.rollout_health")
async def rollout_health(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """The head of the organisation: aggregate by department. Admin: their own department plus its PCs behind."""
    ident = require_role(ctx, "super_user", "admin")
    db = ctx.engine.db
    cur = await db.updates.current_version()
    health = await db.updates.rollout_health_by_department()
    behind = await db.updates.pcs_behind(cur["id"]) if cur else []
    if kept(ident):
        health = [h for h in health if h["department_id"] == ident.department_id]
        behind = [b for b in behind if b["department_id"] == ident.department_id]
    # The head of the organisation sees every PC that is behind, not only the per-department totals: the fleet is
    # what the N+1 gate is actually held on, so it is drawn one square per PC.
    return {"version": row(cur), "departments": rows(health), "pcs_behind": _behind_view(behind)}


@handler("updates.prompt_admin")
async def prompt_admin(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """The head of the organisation's second lever: nudge a department's Admins whose rollout looks stalled.
    {"department_id", "message"?}"""
    require_head(ctx)
    department_id = int_field(payload, "department_id")
    message = payload.get("message") or "You are being asked about your department's update rollout."
    await ctx.engine.push_to_role("admin", "update.prompt", {"message": message}, department_id=department_id)
    await ctx.engine.audit.record(ctx, "update.prompt", target_type="departments", target_id=department_id)
    return {"department_id": department_id, "prompted": True}


# --- the packages a machine updates itself from (Phase 9: the update pipeline) ---------------------------------------------------------
#
# A version's packages sit on the Engine's own disk, one per role: data/updates/<version>/<role>.zip, each a payload folder zipped
# (`python -m installers.payload <role> <folder>`, then zipped). A machine told `update.available` fetches its role's package in pieces over
# its own connection (`update.fetch`), checks the hash against what the Engine said, checks the payload's own manifest, and runs the
# installer's upgrade (worker_client/updater.py). Nothing is fetched from anywhere else: the Engine is the one source a machine trusts.

FETCH_CHUNK = 512 * 1024
ROLES = ("worker", "admin")
_hashes: dict[str, tuple[float, int, str]] = {}            # package path -> (mtime, size, sha256): a package is hashed once


def packages_dir(engine: Any) -> Any:
    from pathlib import Path

    return Path(engine.settings.secret_path).parent / "updates"


def _package(engine: Any, version: str, role: str) -> tuple[Any, int, str] | None:
    import hashlib
    import re

    if not re.fullmatch(r"[0-9A-Za-z][0-9A-Za-z.\-+]{0,39}", version) or role not in ROLES:
        return None
    path = packages_dir(engine) / version / f"{role}.zip"
    if not path.is_file():
        return None
    st = path.stat()
    cached = _hashes.get(str(path))
    if cached is None or cached[0] != st.st_mtime:
        h = hashlib.sha256()
        with path.open("rb") as f:
            for block in iter(lambda: f.read(1 << 20), b""):
                h.update(block)
        cached = (st.st_mtime, st.st_size, h.hexdigest())
        _hashes[str(path)] = cached
    return path, cached[1], cached[2]


@handler("update.fetch")
async def update_fetch(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"version", "role", "index"} -> {"total", "size", "sha256", "index", "content_b64"}: one piece of a version's package, to a machine
    (only a version that was approved; only the packages that exist)."""
    import asyncio
    import base64

    ident = require_account(ctx)
    if ident.pc_id is None:
        raise ProtocolError(ErrorCode.INVALID, "a package is fetched by a machine")
    version, role = str_field(payload, "version"), str_field(payload, "role", choices=ROLES)
    if await ctx.engine.db.updates.version_by_string(version) is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "that version was never approved")
    found = await asyncio.to_thread(_package, ctx.engine, version, role)
    if found is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, f"there is no {role} package for {version} on the Engine")
    path, size, digest = found
    total = max(1, (size + FETCH_CHUNK - 1) // FETCH_CHUNK)
    index = int_field(payload, "index", required=False) or 0
    if not 0 <= index < total:
        raise ProtocolError(ErrorCode.INVALID, "no such piece")

    def read() -> bytes:
        with path.open("rb") as f:
            f.seek(index * FETCH_CHUNK)
            return f.read(FETCH_CHUNK)
    piece = await asyncio.to_thread(read)
    if index == 0:
        await ctx.engine.audit.record(ctx, "update.fetched", target_type="pcs", target_id=ident.pc_id, pc_id=ident.pc_id,
                                      detail={"version": version, "role": role, "bytes": size})
    return {"version": version, "role": role, "total": total, "size": size, "sha256": digest, "index": index,
            "content_b64": base64.b64encode(piece).decode("ascii")}


@handler("updates.packages")
async def update_packages(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """What packages the Engine holds: [{version, role, bytes, sha256, approved}] -- an approved version with no package for a role cannot
    reach that role's machines."""
    import asyncio

    require_head(ctx)
    base = packages_dir(ctx.engine)
    out = []
    if base.is_dir():
        for folder in sorted(p for p in base.iterdir() if p.is_dir()):
            for role in ROLES:
                found = await asyncio.to_thread(_package, ctx.engine, folder.name, role)
                if found:
                    out.append({"version": folder.name, "role": role, "bytes": found[1], "sha256": found[2],
                                "approved": await ctx.engine.db.updates.version_by_string(folder.name) is not None})
    return {"packages": out, "folder": str(base)}
