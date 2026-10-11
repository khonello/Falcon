"""Restricted marks (the Restricted page, the Mark files page).

A person marks a file or folder **where it already is**, on their own workstation; nothing is moved or copied. The mark says where
the content may be:

    machine   anywhere on that PC, and nowhere else
    path      only in its place: a copy anywhere else is caught, even elsewhere on the same PC

A folder's mark covers every file inside it, and any added later. Content is matched by hash and the mark remembers **every version's
hash**, so editing the original never lets an older copy slip through. A copy anywhere it is not allowed becomes an issue (a file
issue the owner works: ask the person, delete the copy, allow it here too).

    marks.tree        {}                                the files the index holds on your own workstation, with what is marked
    marks.create      {paths: [..], keep}               mark files or folders where they are
    marks.list        {scope?: mine|department|all}     marks with their copy counts
    marks.get         {mark_id}                         one mark: where it is allowed, its copies, what changing it would do
    marks.keep_effect {mark_id, keep}                   what changing where it is allowed would do to the copies, before doing it
    marks.change_keep {mark_id, keep}                   change where it is allowed (the owner, or the Super User)
    marks.unmark      {mark_id}                         stop restricting it; its open copy issues close

Only your own files, on your own workstation, can be marked. The Super User reads every mark; an Admin their own and their
department's.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler
from engine.permissions import int_field, require_role, str_field
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

KEEP = ("machine", "path")
KEEP_WORDS = {"machine": "Anywhere on the PC", "path": "Only in its place"}
SEVERITY_RANK = {"critical": 0, "high": 1, "medium": 2, "low": 3}
TREE_MAX = 5000


def norm(path: str) -> str:
    return path.replace("\\", "/").rstrip("/").lower()


def inside(mark: dict[str, Any], pc_id: int, path: str) -> bool:
    """Is this file the marked file, or in the marked folder, on the marker's own machine?"""
    if pc_id != mark["pc_id"]:
        return False
    p, m = norm(path), norm(mark["path"])
    return p == m if mark["kind"] == "file" else p.startswith(m + "/")


def allowed_at(mark: dict[str, Any], pc_id: int, path: str) -> bool:
    """May this mark's content be at this place? The whole PC for `machine`; its own place for `path`."""
    return pc_id == mark["pc_id"] and (mark["keep"] == "machine" or inside(mark, pc_id, path))


def install(engine: Engine) -> None:
    """Every file event: a marked file or folder gains versions (and new files), and a copy found where the mark does not allow it is flagged."""

    async def on_file(event: dict[str, Any]) -> None:
        if not engine.db.connected or event["op"] not in ("create", "modify", "move", "copy") or event.get("file_index_id") is None:
            return
        db = engine.db
        entry = await db.file_index.get(event["file_index_id"])
        if entry is None or not entry.get("content_hash"):
            return
        pc_id, path, digest = event["pc_id"], entry["path"], entry["content_hash"]
        for mark in await db.marks.active_on_pc(pc_id):
            if inside(mark, pc_id, path):
                await db.marks.add_hash(mark["id"], digest, path)             # a new version, or a new file in a marked folder
        await _flag_copies_of(engine, entry)

    engine.file_index.subscribe(on_file)


async def _flag_copies_of(engine: Engine, entry: dict[str, Any]) -> int:
    """Flag this file if it is a copy of marked content where that mark does not allow it. Returns 1 when flagged."""
    from engine.resource.resource import flag_copy

    db = engine.db
    marks = await db.marks.active_with_hash(entry["content_hash"])
    for mark in marks:
        if allowed_at(mark, entry["pc_id"], entry["path"]):
            return 0                                                           # at a place one of its marks allows
    pc = await db.accounts.pc(entry["pc_id"])
    if pc is None or not marks:
        return 0
    return 1 if await flag_copy(engine, pc, entry, "restricted", None, marks[0]) else 0


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


async def _files_of(db: Any, mark: dict[str, Any]) -> int:
    if mark["kind"] == "file":
        return 1
    return len(await db.file_index.under(mark["pc_id"], mark["path"]))


async def _view(ctx: Context, found: list[dict[str, Any]]) -> list[dict[str, Any]]:
    db = ctx.engine.db
    names = await db.accounts.display_names_for(ctx.identity.account_id, sorted({m["by_account_id"] for m in found})) if found else {}
    depts = {d["id"]: d["name"] for d in await db.accounts.list_departments()}
    out = []
    for m in found:
        copies = await db.marks.copy_issues(m["id"])
        worst = min((c["severity"] for c in copies), key=lambda s: SEVERITY_RANK[s], default=None)
        out.append({"id": m["id"], "code": f"M-{m['id']}", "kind": m["kind"], "name": m["name"], "pc_id": m["pc_id"], "host": m["hostname"],
                    "path": m["path"], "keep": m["keep"], "keep_label": KEEP_WORDS[m["keep"]],
                    "by": {"account_id": m["by_account_id"], "name": names.get(m["by_account_id"]), "you": m["by_account_id"] == ctx.identity.account_id},
                    "department_id": m["department_id"], "department_name": depts.get(m["department_id"]),
                    "created_at": _iso(m["created_at"]), "unmarked_at": _iso(m["unmarked_at"]),
                    "files": await _files_of(db, m), "versions": m["versions"], "copies": len(copies), "worst": worst})
    return out


async def _load(ctx: Context, mark_id: int, *, owner_only: bool = False) -> dict[str, Any]:
    ident = require_role(ctx, "super_user", "admin")
    mark = await ctx.engine.db.marks.get(mark_id)
    if mark is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such mark")
    mine = mark["by_account_id"] == ident.account_id
    if ident.role == "admin" and not mine and (owner_only or mark["department_id"] != ident.department_id):
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such mark")
    if owner_only and not mine and ident.role != "super_user":
        raise ProtocolError(ErrorCode.FORBIDDEN, "only whoever marked it can change it")
    return mark


@handler("marks.tree")
async def marks_tree(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """The files the index holds on the caller's own workstation, for picking what to mark: {pc_id, hostname, files: [{path, name, marked,
    covered_by}], folders: [{path, files}], truncated}. Only what the index has seen; the rest appears after the machine's next idle sweep."""
    ident = require_role(ctx, "super_user", "admin")
    if ident.pc_id is None:
        raise ProtocolError(ErrorCode.INVALID, "you have no workstation registered")
    db = ctx.engine.db
    files = await db.file_index.present_on_pc(ident.pc_id, TREE_MAX + 1)
    marks = await db.marks.active_on_pc(ident.pc_id)
    out, folders = [], {}
    for f in files[:TREE_MAX]:
        own = next((m["id"] for m in marks if m["kind"] == "file" and norm(m["path"]) == norm(f["path"])), None)
        cover = next((m["id"] for m in marks if m["kind"] == "folder" and inside(m, ident.pc_id, f["path"])), None)
        out.append({"path": f["path"], "name": f["filename"], "marked": own, "covered_by": cover})
        folder = f["path"].replace("\\", "/").rsplit("/", 1)[0] if "/" in f["path"].replace("\\", "/") else ""
        folders[folder] = folders.get(folder, 0) + 1
    pc = await db.accounts.pc(ident.pc_id)
    return {"pc_id": ident.pc_id, "hostname": pc["hostname"] if pc else None, "files": out, "truncated": len(files) > TREE_MAX,
            "folders": [{"path": p, "files": n} for p, n in sorted(folders.items())]}


@handler("marks.create")
async def marks_create(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"paths": [..], "keep": "machine"|"path"} -> {"marks": [...], "copies_found": n}. Each path is a file or a folder the index has
    seen on the caller's own workstation. Copies of the content already elsewhere are found at once and raised as issues."""
    ident = require_role(ctx, "super_user", "admin")
    if ident.pc_id is None:
        raise ProtocolError(ErrorCode.INVALID, "you have no workstation registered")
    keep = str_field(payload, "keep", choices=KEEP)
    paths = payload.get("paths")
    if not isinstance(paths, list) or not paths or not all(isinstance(p, str) and p.strip() for p in paths):
        raise ProtocolError(ErrorCode.INVALID, "paths must be a non-empty list of paths")
    db = ctx.engine.db
    existing = await db.marks.active_on_pc(ident.pc_id)
    made: list[int] = []
    found = 0
    for raw in paths:
        path = raw.strip()
        row = await db.file_index.by_path(ident.pc_id, path, present_only=True)
        below = [] if row else await db.file_index.under(ident.pc_id, path)
        if row is None and not below:
            raise ProtocolError(ErrorCode.NOT_FOUND, f"the file index has not seen anything at {path}")
        if any(norm(m["path"]) == norm(path) for m in existing):
            raise ProtocolError(ErrorCode.CONFLICT, f"{path} is already marked")
        if covering := next((m for m in existing if m["kind"] == "folder" and inside(m, ident.pc_id, path)), None):
            raise ProtocolError(ErrorCode.CONFLICT, f"{path} is already covered by the mark on {covering['path']}")
        kind = "file" if row else "folder"
        targets = [row] if row else below
        hashed = [t for t in targets if t.get("content_hash")]
        if kind == "file" and not hashed:
            raise ProtocolError(ErrorCode.INVALID, "that file has no content hash yet (too large, or still being indexed), so a copy could not be recognised")
        name = (row["filename"] if row else path.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]) or path
        mark_id = await db.marks.create(kind, name, ident.pc_id, path, keep, ident.account_id, ident.department_id)
        for t in hashed:
            await db.marks.add_hash(mark_id, t["content_hash"], t["path"])
        await ctx.engine.audit.record(ctx, "mark.created", target_type="resource_marks", target_id=mark_id, pc_id=ident.pc_id,
                                      detail={"path": path, "kind": kind, "keep": keep, "files": len(targets)})
        made.append(mark_id)
        mark = await db.marks.get(mark_id)
        assert mark is not None
        for digest in {t["content_hash"] for t in hashed}:
            for entry in await db.file_index.by_hash(digest):
                if not allowed_at(mark, entry["pc_id"], entry["path"]):
                    found += await _flag_copies_of(ctx.engine, entry)
    return {"marks": await _view(ctx, [m for m in [await db.marks.get(i) for i in made] if m]), "copies_found": found}


@handler("marks.list")
async def marks_list(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"scope"?: "mine" (default) | "department" (an Admin) | "all" (Super User)} -> {"marks": [...], "summary": {marks, files, copies, with_copies}}."""
    ident = require_role(ctx, "super_user", "admin")
    scope = str_field(payload, "scope", required=False, choices=("mine", "department", "all")) or "mine"
    if scope == "all" and ident.role != "super_user":
        raise ProtocolError(ErrorCode.FORBIDDEN, "only the Super User reads every mark")
    db = ctx.engine.db.marks
    if scope == "mine":
        found = await db.list(by_account_id=ident.account_id)
    elif scope == "department":
        found = await db.list(department_id=ident.department_id if ident.role == "admin" else int_field(payload, "department_id"))
    else:
        found = await db.list()
    view = await _view(ctx, found)
    return {"marks": view, "summary": {"marks": len(view), "files": sum(m["files"] for m in view), "copies": sum(m["copies"] for m in view),
                                       "with_copies": sum(1 for m in view if m["copies"])}}


async def _effect(ctx: Context, mark: dict[str, Any], keep: str) -> dict[str, int]:
    """What changing where a mark allows its content would do: copies it would catch, and copies it would stop catching."""
    db = ctx.engine.db
    if keep == mark["keep"]:
        return {"would_flag": 0, "would_clear": 0}
    would_flag = would_clear = 0
    hashes = await db.marks.hashes(mark["id"])
    if keep == "path":                          # tighter: copies elsewhere on the same PC are now wrong
        for digest in hashes:
            for e in await db.file_index.by_hash(digest):
                if e["pc_id"] == mark["pc_id"] and not inside(mark, e["pc_id"], e["path"]) and not await db.resource.is_allowed(
                        e["pc_id"], e["path"], digest):
                    would_flag += 1
    else:                                       # looser: copies on the same PC are fine
        would_clear = sum(1 for c in await db.marks.copy_issues(mark["id"]) if c["pc_id"] == mark["pc_id"] and c["state"] != "resolved")
    return {"would_flag": would_flag, "would_clear": would_clear}


@handler("marks.get")
async def marks_get(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"mark_id"} -> {"mark", "copies": [{issue_id, code, severity, state, label, host, file, folder, path, signed_in, opened_at, age_hours}],
    "resolved_copies": [...] (this week), "change": {keep, effect: {would_flag, would_clear}}}."""
    mark = await _load(ctx, int_field(payload, "mark_id"))
    db = ctx.engine.db
    now = datetime.now(timezone.utc)
    online = ctx.engine.online_pc_ids()

    async def rows(found: list[dict[str, Any]]) -> list[dict[str, Any]]:
        out = []
        for c in found:
            pc = await db.accounts.pc(c["pc_id"])
            who = None
            if pc and pc["bound_account_id"] and c["pc_id"] in online:
                who = (await db.accounts.display_names_for(ctx.identity.account_id, [pc["bound_account_id"]])).get(pc["bound_account_id"])
            d = c["detail"]
            out.append({"issue_id": c["id"], "code": c["code"], "severity": c["severity"], "state": c["state"], "label": c["label"],
                        "pc_id": c["pc_id"], "host": c["hostname"], "file": d.get("file"), "folder": d.get("folder"), "path": d.get("path"),
                        "signed_in": who, "opened_at": _iso(c["opened_at"]), "resolution": c["resolution"],
                        "age_hours": round(((c["resolved_at"] or now) - c["opened_at"]).total_seconds() / 3600, 2)})
        return out

    other = "path" if mark["keep"] == "machine" else "machine"
    return {"mark": (await _view(ctx, [mark]))[0], "copies": await rows(await db.marks.copy_issues(mark["id"])),
            "resolved_copies": [c for c in await rows(await db.marks.copy_issues(mark["id"], include_resolved_since=now - timedelta(days=7)))
                                if c["state"] == "resolved"],
            "change": {"keep": other, "keep_label": KEEP_WORDS[other], "effect": await _effect(ctx, mark, other)}}


@handler("marks.keep_effect")
async def marks_keep_effect(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    mark = await _load(ctx, int_field(payload, "mark_id"))
    keep = str_field(payload, "keep", choices=KEEP)
    return {"keep": keep, "effect": await _effect(ctx, mark, keep)}


@handler("marks.change_keep")
async def marks_change_keep(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Change where a mark allows its content. Copies it now allows close; copies it now catches are raised. Recorded."""
    from engine.console.issues import resolve_issue

    mark = await _load(ctx, int_field(payload, "mark_id"), owner_only=True)
    keep = str_field(payload, "keep", choices=KEEP)
    if keep == mark["keep"]:
        raise ProtocolError(ErrorCode.CONFLICT, f"it is already kept to {KEEP_WORDS[keep].lower()}")
    db = ctx.engine.db
    effect = await _effect(ctx, mark, keep)
    await db.marks.set_keep(mark["id"], keep)
    fresh = await db.marks.get(mark["id"])
    assert fresh is not None
    cleared = flagged = 0
    for c in await db.marks.copy_issues(mark["id"]):
        if c["state"] != "resolved" and allowed_at(fresh, c["pc_id"], c["detail"].get("path", "")):
            cleared += int(await resolve_issue(ctx.engine, c["id"], "Allowed now: the mark is kept to the whole machine", by=ctx))
    for digest in await db.marks.hashes(mark["id"]):
        for e in await db.file_index.by_hash(digest):
            if not allowed_at(fresh, e["pc_id"], e["path"]):
                flagged += await _flag_copies_of(ctx.engine, e)
    await ctx.engine.audit.record(ctx, "mark.changed", target_type="resource_marks", target_id=mark["id"], pc_id=mark["pc_id"],
                                  detail={"keep": keep, "was": mark["keep"], "cleared": cleared, "flagged": flagged})
    return {"mark": (await _view(ctx, [fresh]))[0], "cleared": cleared, "flagged": flagged, "effect": effect}


@handler("marks.unmark")
async def marks_unmark(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Stop restricting a file or folder. Its open copy issues close; the mark and its history are kept (unmarked)."""
    from engine.console.issues import resolve_issue

    mark = await _load(ctx, int_field(payload, "mark_id"), owner_only=True)
    db = ctx.engine.db
    if not await db.marks.unmark(mark["id"], ctx.identity.account_id):
        raise ProtocolError(ErrorCode.CONFLICT, "it is already unmarked")
    closed = 0
    for issue_id in await db.marks.resolve_open_copies(mark["id"]):
        closed += int(await resolve_issue(ctx.engine, issue_id, "The mark was removed", by=ctx))
    await ctx.engine.audit.record(ctx, "mark.removed", target_type="resource_marks", target_id=mark["id"], pc_id=mark["pc_id"],
                                  detail={"path": mark["path"], "copies_closed": closed})
    return {"mark_id": mark["id"], "copies_closed": closed}
