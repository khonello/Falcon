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

import time
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler
from engine.permissions import int_field, require_role, str_field
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

# Worst cases, clamped. Marking a folder asks the Engine to track every file in it by content and to look for copies of each, and a folder like node_modules can hold
# a million generated files. So a mark is assessed first (how many files, about how long, what the weight is) and refused, or asked to be confirmed, before anything starts.
MARK_MAX_FILES = 20000             # tracked by content in one mark
MARK_MAX_MACHINE = 100000          # tracked by content across all one machine's marks
MARK_CONFIRM_FILES = 2000          # more than this is allowed only when it is confirmed
SECONDS_PER_FILE = 0.02            # what tracking one file costs the Engine (a row, a lookup for copies): deliberately pessimistic
HEAL_BUDGET = 4000                 # content hashes looked at per healing pass, rotating, so a huge mark cannot make one pass take for ever
JUNK_FOLDERS = ("node_modules", ".git", "__pycache__", ".venv", "venv", "site-packages", ".gradle", ".m2", "bower_components", "$recycle.bin", ".cache", ".next", ".tox",
                "dist", "build", "target", "obj", "bin", "pods", ".idea", ".vs")      # generated, rebuildable: covered by a folder mark, never tracked file by file
_heal_cursor: dict[int, int] = {}

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


MOVE_WINDOW_SECONDS = 10.0
_just_left: dict[tuple[int, str], tuple[float, int, str]] = {}      # (pc, hash) -> (when, mark, the place it left)


def reset_state() -> None:
    _just_left.clear()


def install(engine: Engine) -> None:
    """Every file event: a marked file or folder gains versions (and new files), and a copy found where the mark does not allow it is flagged."""

    async def on_file(event: dict[str, Any]) -> None:
        if not engine.db.connected or event["op"] not in ("create", "modify", "move", "copy") or event.get("file_index_id") is None:
            return
        db = engine.db
        if event["op"] == "move" and event.get("old_path"):
            await _follow(engine, event["pc_id"], str(event["old_path"]), event["path"])      # the marked file itself moved: the mark goes with it
        elif event["op"] == "create":
            entry = await db.file_index.get(event["file_index_id"])
            left = _just_left.pop((event["pc_id"], (entry or {}).get("content_hash") or ""), None)
            if left is not None and time.monotonic() - left[0] <= MOVE_WINDOW_SECONDS:
                await _follow(engine, event["pc_id"], left[2], event["path"])                 # it left one place and appeared in another: it moved
        entry = await db.file_index.get(event["file_index_id"])
        if entry is None or not entry.get("content_hash"):
            return
        pc_id, path, digest = event["pc_id"], entry["path"], entry["content_hash"]
        for mark in await db.marks.active_on_pc(pc_id):
            if inside(mark, pc_id, path) and await db.marks.add_hash(mark["id"], digest, path):       # a new version, or a new file in a marked folder
                engine.marked.invalidate()
        await _flag_copies_of(engine, entry)

    async def on_any(event: dict[str, Any]) -> None:
        if not engine.db.connected:
            return
        if event.get("is_dir") and event["op"] == "move" and event.get("old_path"):
            await _follow(engine, event["pc_id"], str(event["old_path"]), event["path"])      # a marked folder (or one holding marked files) moved
        elif event["op"] == "delete" and not event.get("is_dir"):
            # a marked file that was deleted may be about to reappear elsewhere (some moves arrive as a delete and a create)
            row = await engine.db.file_index.by_path(event["pc_id"], event["path"])
            digest = (row or {}).get("content_hash")
            if digest:
                for mark in await engine.db.marks.active_on_pc(event["pc_id"]):
                    if mark["kind"] == "file" and norm(mark["path"]) == norm(event["path"]):
                        _just_left[(event["pc_id"], digest)] = (time.monotonic(), mark["id"], event["path"])
        if len(_just_left) > 2000:                                       # bounded: what left long ago and never reappeared is forgotten
            for k in [k for k, v in _just_left.items() if time.monotonic() - v[0] > MOVE_WINDOW_SECONDS][:1000]:
                _just_left.pop(k, None)

    engine.file_index.subscribe(on_file, stage="guard", name="marks")
    engine.file_index.subscribe(on_any, every_op=True, stage="guard", name="marks.follow")


async def _follow(engine: Engine, pc_id: int, old_path: str, new_path: str) -> None:
    """The original was moved or renamed, not copied: the mark follows it, and anything raised about the new place closes."""
    from engine.console.issues import resolve_issue

    db = engine.db
    followed = await db.marks.follow(pc_id, old_path, new_path)
    if followed:
        engine.marked.invalidate()                                  # (the mark's place changed)
    for mark_id in followed:
        mark = await db.marks.get(mark_id)
        if mark is None:
            continue
        cleared = 0
        for c in await db.marks.copy_issues(mark_id):
            if c["state"] != "resolved" and allowed_at(mark, c["pc_id"], c["detail"].get("path", "")):
                cleared += int(await resolve_issue(engine, c["id"], "The marked file was moved: this is it"))
        await engine.audit.record(None, "mark.followed", target_type="resource_marks", target_id=mark_id, pc_id=pc_id,
                                  detail={"from": old_path, "to": new_path, "cleared": cleared})


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


async def heal(engine: Engine) -> int:
    """Proactive: now and then every active mark's content is checked against everything the index holds, so a copy whose event was missed (or
    that arrived before its original was marked) is found anyway. Returns how many copies were newly flagged."""
    if not engine.db.connected:
        return 0
    db = engine.db
    flagged = 0
    budget = HEAL_BUDGET
    # hot machines first; a mark too big for what is left of the budget is carried on from where it stopped at the next pass, so the whole of it is covered in time
    for mark in engine.heat.hottest(await db.marks.list(), key=lambda m: f"pc:{m['pc_id']}"):
        digests = await db.marks.hashes(mark["id"])
        start = _heal_cursor.get(mark["id"], 0) % max(1, len(digests))
        order = digests[start:] + digests[:start]
        done = 0
        for digest in order:
            if budget <= 0:
                break
            budget -= 1
            done += 1
            for entry in await db.file_index.by_hash(digest):
                if not allowed_at(mark, entry["pc_id"], entry["path"]):
                    flagged += await _flag_copies_of(engine, entry)
        _heal_cursor[mark["id"]] = (start + done) % max(1, len(digests))
        if budget <= 0:
            break
    if flagged:
        await engine.audit.record(None, "mark.healed", target_type="resource_marks", target_id=None, detail={"flagged": flagged})
    return flagged


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


async def _counts(db: Any, mark: dict[str, Any]) -> tuple[int, int]:
    """(files inside, of which generated -- covered by the mark but not tracked one by one)."""
    if mark["kind"] == "file":
        return 1, 0
    c = await db.file_index.count_under(mark["pc_id"], mark["path"], JUNK_FOLDERS)
    return c["files"], c["junk"]


async def _view(ctx: Context, found: list[dict[str, Any]]) -> list[dict[str, Any]]:
    db = ctx.engine.db
    names = await db.accounts.display_names_for(ctx.identity.account_id, sorted({m["by_account_id"] for m in found})) if found else {}
    depts = {d["id"]: d["name"] for d in await db.accounts.list_departments()}
    out = []
    carried = await db.flows.carried_by_consent([m["id"] for m in found])
    for m in found:
        copies = await db.marks.copy_issues(m["id"])
        files, generated = await _counts(db, m)
        worst = min((c["severity"] for c in copies), key=lambda s: SEVERITY_RANK[s], default=None)
        out.append({"id": m["id"], "code": f"M-{m['id']}", "kind": m["kind"], "name": m["name"], "pc_id": m["pc_id"], "host": m["hostname"],
                    "path": m["path"], "keep": m["keep"], "keep_label": KEEP_WORDS[m["keep"]],
                    "by": {"account_id": m["by_account_id"], "name": names.get(m["by_account_id"]), "you": m["by_account_id"] == ctx.identity.account_id},
                    "department_id": m["department_id"], "department_name": depts.get(m["department_id"]),
                    "created_at": _iso(m["created_at"]), "unmarked_at": _iso(m["unmarked_at"]),
                    "files": files, "generated": generated, "tracked": files - generated, "carried_by": carried.get(m["id"], []),
                    "versions": m["versions"], "copies": len(copies), "worst": worst})
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


def _in_junk(path: str) -> bool:
    parts = path.replace("\\", "/").lower().split("/")
    return any(p in JUNK_FOLDERS for p in parts[:-1])


def _minutes(seconds: float) -> str:
    return "under a minute" if seconds < 60 else f"about {round(seconds / 60)} minute{'s' if seconds >= 90 else ''}" if seconds < 5400 else f"about {seconds / 3600:.1f} hours"


async def assess(db: Any, pc_id: int, path: str, *, already: int = 0, cost: Any = None) -> dict[str, Any]:
    """What marking this would cost, from the index, before anything is done: files, how many of them are generated (not tracked one by one), a pessimistic time, and a verdict
    ("ok", "large" = allowed once confirmed, "too_large" = refused) with the reasons in words a person can act on."""
    row = await db.file_index.by_path(pc_id, path, present_only=True)
    per_file, measured = cost.per_unit("mark_file", SECONDS_PER_FILE) if cost is not None else (SECONDS_PER_FILE, 0)
    slow = cost.slowdown() if cost is not None else 1.0
    capacity = cost.capacity() if cost is not None else None
    basis = f"measured over {measured} earlier job{'s' if measured != 1 else ''} on this Engine" if measured else "assumed (nothing measured yet)"
    if row is not None:
        return {"path": path, "kind": "file", "files": 1, "junk": 0, "tracked": 1, "seconds": round(per_file * slow, 3), "verdict": "ok", "reasons": [], "heaviest": [],
                "limit": MARK_MAX_FILES, "per_file_ms": round(per_file * 1000, 1), "basis": basis, "capacity": capacity}
    counts = await db.file_index.count_under(pc_id, path, JUNK_FOLDERS)
    files, junk = counts["files"], counts["junk"]
    tracked = files - junk
    seconds = tracked * per_file * slow
    reasons: list[str] = []
    heaviest = await db.file_index.heaviest_under(pc_id, path) if files > MARK_CONFIRM_FILES else []
    verdict = "ok"
    if junk:
        reasons.append(f"{junk:,} of its {files:,} files are in generated folders such as node_modules; they are covered by the mark but not tracked one by one")
    if tracked > MARK_MAX_FILES:
        verdict = "too_large"
        reasons.append(f"{tracked:,} files to track is more than one mark can hold ({MARK_MAX_FILES:,}); at about {per_file * 1000:.0f} ms each that would take {_minutes(seconds)}")
    elif already + tracked > MARK_MAX_MACHINE:
        verdict = "too_large"
        reasons.append(f"this machine already tracks {already:,} files by content and the most it can is {MARK_MAX_MACHINE:,}; this would add {tracked:,}")
    elif tracked > MARK_CONFIRM_FILES:
        verdict = "large"
        reasons.append(f"{tracked:,} files to track will take {_minutes(seconds)}")
    if verdict != "ok" and heaviest:
        reasons.append("the weight is in: " + ", ".join(f"{h['name']} ({h['files']:,})" for h in heaviest[:3]) + " -- mark a narrower folder, or the files that matter")
    if slow > 1.0 and verdict != "too_large":
        reasons.append(f"the Engine is {capacity['state']} right now, so allow about {slow:.1f} times longer than usual" if capacity else "the Engine is busy")
    if verdict == "ok" and slow > 1.0 and seconds > 120:
        verdict = "large"                                              # a job that is fine on a quiet Engine is asked about when it is busy
    return {"path": path, "kind": "folder", "files": files, "junk": junk, "tracked": tracked, "seconds": round(seconds, 1), "verdict": verdict, "reasons": reasons,
            "heaviest": heaviest, "limit": MARK_MAX_FILES, "per_file_ms": round(per_file * 1000, 1), "basis": basis, "capacity": capacity}


async def _tracked_on(db: Any, pc_id: int, marks: list[dict[str, Any]]) -> int:
    total = 0
    for m in marks:
        if m["kind"] == "file":
            total += 1
        else:
            c = await db.file_index.count_under(m["pc_id"], m["path"], JUNK_FOLDERS)
            total += c["files"] - c["junk"]
    return total


@handler("marks.assess")
async def marks_assess(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"paths": [..]} -> {"assessed": [{path, kind, files, junk, tracked, seconds, verdict, reasons, heaviest, limit}], "tracked_now", "machine_limit"}: what marking these would
    cost, before it is done. Nothing is changed."""
    ident = require_role(ctx, "super_user", "admin")
    if ident.pc_id is None:
        raise ProtocolError(ErrorCode.INVALID, "you have no workstation registered")
    paths = payload.get("paths")
    if not isinstance(paths, list) or not paths or len(paths) > 50 or not all(isinstance(p, str) and p.strip() for p in paths):
        raise ProtocolError(ErrorCode.INVALID, "paths must be a list of 1 to 50 paths")
    db = ctx.engine.db
    now = await _tracked_on(db, ident.pc_id, await db.marks.active_on_pc(ident.pc_id))
    out, running = [], now
    for raw in paths:
        a = await assess(db, ident.pc_id, raw.strip(), already=running, cost=ctx.engine.cost)
        if a["verdict"] != "too_large":
            running += a["tracked"]
        out.append(a)
    return {"assessed": out, "tracked_now": now, "machine_limit": MARK_MAX_MACHINE, "capacity": ctx.engine.cost.capacity()}


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
    if len(paths) > 50:
        raise ProtocolError(ErrorCode.INVALID, "mark at most 50 paths at a time")
    db = ctx.engine.db
    existing = await db.marks.active_on_pc(ident.pc_id)
    # Assess everything first, so nothing is half done: a refusal names the path, how many files, how long it would take and where the weight is.
    running = await _tracked_on(db, ident.pc_id, existing)
    for raw in paths:
        a = await assess(db, ident.pc_id, raw.strip(), already=running, cost=ctx.engine.cost)
        if a["verdict"] == "too_large":
            raise ProtocolError(ErrorCode.INVALID, f"{a['path']} is too large to mark as it is: " + "; ".join(a["reasons"]))
        if a["verdict"] == "large" and not payload.get("confirm_large"):
            raise ProtocolError(ErrorCode.CONFLICT, f"{a['path']} is large: " + "; ".join(a["reasons"]) + " -- confirm to go ahead (confirm_large)")
        running += a["tracked"]
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
        hashed = [t for t in targets if t.get("content_hash") and not _in_junk(t["path"])]
        if kind == "file" and not hashed:
            raise ProtocolError(ErrorCode.INVALID, "that file has no content hash yet (too large, or still being indexed), so a copy could not be recognised")
        name = (row["filename"] if row else path.replace("\\", "/").rstrip("/").rsplit("/", 1)[-1]) or path
        began = time.perf_counter()
        mark_id = await db.marks.create(kind, name, ident.pc_id, path, keep, ident.account_id, ident.department_id)
        for t in hashed:
            await db.marks.add_hash(mark_id, t["content_hash"], t["path"])
        ctx.engine.marked.invalidate()
        ctx.engine.cost.observe("mark_file", time.perf_counter() - began, max(1, len(hashed)))           # what it really cost, for the next estimate
        await ctx.engine.audit.record(ctx, "mark.created", target_type="resource_marks", target_id=mark_id, pc_id=ident.pc_id,
                                      detail={"path": path, "kind": kind, "keep": keep, "files": len(targets)})
        made.append(mark_id)
        mark = await db.marks.get(mark_id)
        assert mark is not None
        await ctx.engine.announce("mark.created", {"mark_id": mark_id, "pc_id": ident.pc_id, "path": path, "kind": kind}, pc=ident.pc_id)   # (Flow hears it and stops at once)
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
    ctx.engine.marked.invalidate()
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
    ctx.engine.marked.invalidate()
    await ctx.engine.announce("mark.removed", {"mark_id": mark["id"], "pc_id": mark["pc_id"], "path": mark["path"]}, pc=mark["pc_id"])
    closed = 0
    for issue_id in await db.marks.resolve_open_copies(mark["id"]):
        closed += int(await resolve_issue(ctx.engine, issue_id, "The mark was removed", by=ctx))
    await ctx.engine.audit.record(ctx, "mark.removed", target_type="resource_marks", target_id=mark["id"], pc_id=mark["pc_id"],
                                  detail={"path": mark["path"], "copies_closed": closed})
    return {"mark_id": mark["id"], "copies_closed": closed}
