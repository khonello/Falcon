"""Resource tiers and compliance (Resource -> Folder Structure, Access Control Rules,
Restricted File Tracking, Compliance & Enforcement).

    Super User PC   /resources/{admin,restricted,common}
    Admin PC        /resources/{restricted,workers,common}
    Worker PC       /resources/            (flat)

Tags (file_index.resource_tag): admin | restricted | worker_dept (+ scope department) | common.
A file's tag is derived from the tier folder it sits in on the PC that owns it; `admin` and
`restricted` files are then tracked by content hash system-wide. A copy appearing where its
tier does not permit is a violation:
  * logged as a warning (resource_violations) and audited
  * only THAT file is ignored going forward (Flow will not move it) -- never the structure
  * surfaced to the affected user (the PC's bound account) so they can rectify it
  * raised as a routable Report ('resource_violation')
  * never auto-deleted

Detection reuses the Global File Index event stream (native-first, polling fallback).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler
from engine.hierarchy import reports
from engine.permissions import (
    int_field,
    require_account,
    require_department_scope,
    require_role,
    str_field,
)
from engine.serialize import rows
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

TAGS = ("admin", "restricted", "worker_dept", "common")  # file_index.resource_tag
TRACKED_BY_HASH = ("admin", "restricted")

TIER_FOLDERS = {
    "super_user_workstation": {"admin": "admin", "restricted": "restricted", "common": "common"},
    "admin_workstation": {"restricted": "restricted", "workers": "worker_dept", "common": "common"},
    "client_pc": {},  # flat: no tier folders, tags come from the file's origin (hash)
}


def tag_allowed_on(tag: str, tag_scope_department_id: int | None,
                   pc_type: str, pc_department_id: int | None) -> bool:
    """Access Control Rules table, as a predicate. `tag_scope_department_id` is
    `file_index.resource_tag_scope_department_id`, meaningful only for 'worker_dept'."""
    if tag == "common":
        return True
    if tag == "admin":
        return pc_type == "super_user_workstation"
    if tag == "restricted":
        return pc_type in ("super_user_workstation", "admin_workstation")
    if tag == "worker_dept":
        return (pc_type in ("admin_workstation", "client_pc")
                and tag_scope_department_id is not None
                and pc_department_id == tag_scope_department_id)
    return False


def allowed_tags_for(role: str, department_id: int | None) -> list[tuple[str, int | None]]:
    """What a caller may see in Assistance search / Task target search, as
    (tag, scope_department_id) pairs matching the file_index columns."""
    tags: list[tuple[str, int | None]] = [("common", None)]
    if role in ("admin", "super_user"):
        tags.append(("restricted", None))
    if role == "super_user":
        tags.append(("admin", None))
    if department_id is not None:
        tags.append(("worker_dept", department_id))
    return tags


def derive_tag(path: str, pc_type: str, pc_department_id: int | None) -> tuple[str, int | None] | None:
    """The tag a file gets from the tier folder it sits in on its own PC, or None."""
    parts = path.replace("\\", "/").lower().split("/")
    try:
        i = parts.index("resources")
    except ValueError:
        return None
    folders = TIER_FOLDERS.get(pc_type, {})
    if i + 1 < len(parts) - 1 and parts[i + 1] in folders:
        tag = folders[parts[i + 1]]
        return (tag, pc_department_id if tag == "worker_dept" else None)
    return None


def install(engine: Engine) -> None:
    engine.file_index.subscribe(lambda event: _on_file_event(engine, event))


async def _on_file_event(engine: Engine, event: dict[str, Any]) -> None:
    if not engine.db.connected or event["op"] == "delete" or event.get("file_index_id") is None:
        return
    db = engine.db
    pc = await db.accounts.pc(event["pc_id"])
    if pc is None:
        return
    entry = await db.file_index.get(event["file_index_id"])
    if entry is None:
        return

    # 1. Tag from the tier folder on the PC that owns it (only if the event carried no tag).
    if entry["resource_tag"] is None:
        derived = derive_tag(entry["path"], pc["pc_type"], pc["department_id"])
        if derived:
            await db.file_index.set_tag(entry["id"], *derived)
            entry["resource_tag"], entry["resource_tag_scope_department_id"] = derived

    # 2. Restricted File Tracking: does this content match an admin/restricted file elsewhere?
    tag, scope = entry["resource_tag"], entry["resource_tag_scope_department_id"]
    origin = None
    if tag is None and entry.get("content_hash"):
        for other in await db.file_index.by_hash(entry["content_hash"]):
            if other["id"] != entry["id"] and other["resource_tag"] in TRACKED_BY_HASH:
                tag, scope, origin = other["resource_tag"], None, other
                break
    if tag is None:
        return

    # 3. Compliance: is this tag permitted on this PC?
    if tag_allowed_on(tag, scope, pc["pc_type"], pc["department_id"]):
        return
    if await db.resource.open_violation_for_file(entry["id"]):
        return  # already flagged; the same file keeps being ignored until resolved
    await flag_copy(engine, pc, entry, tag, origin)


async def flag_copy(engine: Engine, pc: dict[str, Any], entry: dict[str, Any], tag: str, origin: dict[str, Any] | None,
                    mark: dict[str, Any] | None = None) -> int | None:
    """A restricted file where it is not allowed: record the violation, write the report, raise the issue, tell the person and fire
    the event. Returns the violation id, or None when it is allowed there (a person allowed it, with a reason), already flagged, or
    nobody uses the machine. `mark` is the restricted mark the copy was recognised by, when it was."""
    db = engine.db
    if await db.resource.open_violation_for_file(entry["id"]):
        return None
    if await db.resource.is_allowed(pc["id"], entry["path"], entry.get("content_hash")):
        return None  # a person allowed it here, with a reason: not reported again
    surfaced_to = pc["bound_account_id"]
    if surfaced_to is None:
        return None
    violation_id = await db.resource.record_violation(entry["id"], tag, pc["id"], "event", surfaced_to)
    await engine.audit.record(None, "resource.violation", target_type="resource_violations", target_id=violation_id,
                              detail={"path": entry["path"], "tag": tag, "pc_id": pc["id"]})
    report_id = await reports.emit(engine, "resource_violation", source_table="resource_violations",
                                   source_id=violation_id,
                                   summary=f"{tag} file {entry['filename']} found on {pc['hostname']}")
    if report_id:
        await db.resource.attach_report(violation_id, report_id)
    await _raise_issue(engine, pc, entry, tag, origin, violation_id, mark)
    await engine.push_to_account(surfaced_to, "resource.violation", {
        "violation_id": violation_id, "path": entry["path"], "tag": tag,
        "message": f"'{entry['filename']}' is a {tag} file and is not permitted on this PC. It is being ignored "
                   f"by the system until you remove it."})
    from engine.control import events

    await events.on_signal(engine, pc["id"], "resource.violation",
                           {"violation_id": violation_id, "path": entry["path"], "tag": tag})
    return violation_id


async def _raise_issue(engine: Engine, pc: dict[str, Any], entry: dict[str, Any], tag: str, origin: dict[str, Any] | None,
                       violation_id: int, mark: dict[str, Any] | None = None) -> None:
    """A copy where it is not allowed is an issue for the department it is in. Critical when it left the original's department,
    high on another machine of the same department (or when there is no original to compare with), medium elsewhere on the
    same machine."""
    from engine.console import issues

    severity = "high"
    origin_pc_id = mark["pc_id"] if mark else (origin["pc_id"] if origin else None)
    if origin_pc_id is not None:
        origin_pc = await engine.db.accounts.pc(origin_pc_id)
        if origin_pc_id == pc["id"]:
            severity = "medium"
        elif origin_pc and origin_pc["department_id"] != pc["department_id"]:
            severity = "critical"
    mark_detail: dict[str, Any] = {}
    if mark:
        by = await engine.db.accounts.display_names_for(pc["bound_account_id"] or mark["by_account_id"], [mark["by_account_id"]])
        mark_detail = {"mark": {"id": mark["id"], "code": f"M-{mark['id']}", "host": mark["hostname"], "path": mark["path"],
                                "keep": mark["keep"], "kind": mark["kind"], "name": mark["name"], "by": by.get(mark["by_account_id"]),
                                "by_account_id": mark["by_account_id"]}}
    folder = entry["path"].replace("\\", "/").rsplit("/", 1)[0] if "/" in entry["path"].replace("\\", "/") else ""
    await issues.raise_issue(
        engine, type_="file", severity=severity, title="Restricted file copied where it isn't allowed", subject=entry["filename"],
        pc_id=pc["id"], source_table="resource_violations", source_id=violation_id,
        detail={"file": entry["filename"], "folder": folder, "path": entry["path"], "tag": tag, "hash": entry.get("content_hash"),
                "violation_id": violation_id, "file_index_id": entry["id"], "origin_pc_id": origin_pc_id, **mark_detail},
        owner_account_id=mark["by_account_id"] if mark else None)
    from engine.console import accountability

    keep = (mark or {}).get("keep")
    await accountability.never(
        engine, "file", kind="worker", severity=severity, subject_account_id=pc["bound_account_id"], pc_id=pc["id"],
        department_id=pc["department_id"], short=f"Copy of {entry['filename']} on {pc['hostname']}",
        expected=("Stay on " + str(mark["hostname"]) if keep == "machine" else f"Stay in {mark['path']} on {mark['hostname']}") if mark
        else f"Stay where a {tag} file is allowed", happened=f"A copy in {folder or 'the machine'}",
        detail={"violation_id": violation_id, "file": entry["filename"], "path": entry["path"]}, source_key=f"violation:{violation_id}")


async def ignored_files(engine: Engine, pc_id: int) -> set[int]:
    """file_index ids on a PC that the system currently ignores (unresolved violations)."""
    return await engine.db.resource.ignored_file_ids(pc_id)


# --- handlers -----------------------------------------------------------------------------------

@handler("resource.violations")
async def violations(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Super User: all; Admin: own department; Worker: those surfaced to them.
    {"include_resolved": bool}"""
    ident = require_account(ctx)
    unresolved_only = not payload.get("include_resolved", False)
    db = ctx.engine.db
    if ident.role == "super_user":
        found = await db.resource.list_violations(unresolved_only=unresolved_only)
    elif ident.role == "admin":
        found = await db.resource.list_violations(department_id=ident.department_id, unresolved_only=unresolved_only)
    else:
        found = await db.resource.list_violations(account_id=ident.account_id, unresolved_only=unresolved_only)
    return {"violations": rows(found)}


@handler("resource.shelves")
async def shelves(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """The tiers the caller keeps (their workstation's tier folders, schema RS) with how many files sit on
    each -- the Resources page's shelves. Admin: across their department; Super User: everywhere."""
    ident = require_role(ctx, "super_user", "admin")
    pc_type = "super_user_workstation" if ident.role == "super_user" else "admin_workstation"
    counts = {r["tag"]: r["files"] for r in await ctx.engine.db.file_index.tier_counts(
        None if ident.role == "super_user" else ident.department_id)}
    return {"shelves": [{"folder": folder, "tag": tag, "files": counts.get(tag, 0)}
                        for folder, tag in TIER_FOLDERS[pc_type].items()]}


@handler("resource.resolve")
async def resolve(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"violation_id"} -- the affected user (or their Admin / Super User) marks it rectified;
    the file stops being ignored. If the copy is still there, the next event re-flags it."""
    ident = require_account(ctx)
    violation_id = int_field(payload, "violation_id")
    v = await ctx.engine.db.resource.violation(violation_id)
    if v is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such violation")
    if ident.account_id != v["surfaced_to_account_id"]:
        require_role(ctx, "super_user", "admin")
        require_department_scope(ident, v["department_id"])
    await ctx.engine.db.resource.resolve(violation_id)
    await ctx.engine.audit.record(ctx, "resource.violation_resolved", target_type="resource_violations",
                                  target_id=violation_id)
    from engine.console import issues

    await issues.resolve_source(ctx.engine, "resource_violations", violation_id, "Put right", by=ctx)
    return {"violation_id": violation_id, "resolved": True}


@handler("resource.tag")
async def tag(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"file_index_id", "tag", "scope_department_id"?} -- an Admin (own department) or Super
    User classifies a file explicitly, e.g. one that lives outside a tier folder."""
    ident = require_role(ctx, "super_user", "admin")
    file_index_id = int_field(payload, "file_index_id")
    new_tag = str_field(payload, "tag", choices=TAGS)
    scope = int_field(payload, "scope_department_id", required=new_tag == "worker_dept")
    if new_tag == "admin" and ident.role != "super_user":
        raise ProtocolError(ErrorCode.FORBIDDEN, "only Super User assigns the admin tier")
    entry = await ctx.engine.db.file_index.get(file_index_id)
    if entry is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such indexed file")
    pc = await ctx.engine.db.accounts.pc(entry["pc_id"])
    require_department_scope(ident, pc["department_id"] if pc else None)
    await ctx.engine.db.file_index.set_tag(file_index_id, new_tag, scope if new_tag == "worker_dept" else None)
    await ctx.engine.audit.record(ctx, "resource.tagged", target_type="file_index", target_id=file_index_id,
                                  detail={"tag": new_tag, "scope": scope})
    return {"file_index_id": file_index_id, "tag": new_tag}
