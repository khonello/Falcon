"""A file's journey (Resource & Assistance; ENGINE-GAPS #9): where the same content has been, and what was done about
it, in the order it happened.

A file is followed by its CONTENT (the hash), because a copy has a different path and sits on a different machine.
The timeline is built from what the Engine already records:

  * first_seen / copied   the file index: each place the same content was indexed, by when it first appeared there
  * moved / renamed       the history of file events: it left one place for another (a rename is a move within a folder)
  * deleted               the history: it was removed from a machine
  * edited                the history: its content changed (recorded at most once per ten minutes per file)
  * attributes_changed, permissions_changed
                          the history: read-only / hidden changed, or who may open it changed, with the content untouched
  * tagged                the audit trail (resource.tagged), with who classified it
  * flagged, owner_told   a Restricted File Tracking violation: found where it should not be, and the person told
  * resolved              the audit trail (resource.violation_resolved), with who
  * synced, conflict      the flow sync log: a flow carried it to another machine, or an outside edit was in the way

A folder being renamed above the file is not followed (the file's own path did not change event by event).
Scope: the Super User sees the whole journey. An Admin sees only what happened on their own department's machines (a
copy elsewhere is not theirs to read), and a file with no place in their department is "not found" to them.
Names are the caller's (Display Names are never shared across namers).
"""

from __future__ import annotations

import posixpath
from typing import Any

from engine.dispatch import Context, handler
from engine.permissions import int_field, require_role
from engine.serialize import row
from protocol import ErrorCode, ProtocolError

TAG_WORDS = {"admin": "an Admin file", "restricted": "a restricted file", "worker_dept": "a department file",
             "common": "a common file"}


def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


def _norm(path: str) -> str:
    return path.replace("\\", "/")


def _folder_and_name(path: str) -> tuple[str, str]:
    folder, name = posixpath.split(_norm(path))
    return folder.lower(), name


@handler("resource.journey")
async def journey(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"file_index_id"} -> {"file", "places": [...], "events": [{at, kind, pc_id, hostname, path, who, text}]}.
    Events are oldest first. `kind` is first_seen, copied, moved, renamed, deleted, edited, attributes_changed,
    permissions_changed, tagged, flagged, owner_told, resolved, synced or conflict. Each place says whether it is still
    there (`gone_at` is when the file left it)."""
    ident = require_role(ctx, "super_user", "admin")
    db = ctx.engine.db
    file_id = int_field(payload, "file_index_id")
    entry = await db.file_index.get(file_id)
    if entry is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such indexed file")

    pcs: dict[int, dict[str, Any]] = {}

    async def pc_of(pc_id: int | None) -> dict[str, Any] | None:
        if pc_id is None:
            return None
        if pc_id not in pcs:
            pcs[pc_id] = await db.accounts.pc(pc_id) or {}
        return pcs[pc_id] or None

    def mine(pc: dict[str, Any] | None) -> bool:
        return ident.role == "super_user" or bool(pc and pc.get("department_id") == ident.department_id)

    places = [p for p in await db.file_index.same_content(file_id) if mine(await pc_of(p["pc_id"]))]
    if not places:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such indexed file")
    by_id = {p["id"]: p for p in places}
    raw: list[tuple[Any, dict[str, Any]]] = []          # (when, event) -- names are filled in below
    people: set[int] = set()

    def add(at: Any, kind: str, pc_id: int | None, path: str | None, text: str, who_id: int | None = None) -> None:
        if who_id is not None:
            people.add(who_id)
        raw.append((at, {"kind": kind, "pc_id": pc_id, "path": path, "who_id": who_id, "text": text}))

    # What the OS reported happened to these places (and the places they came from, through any chain of moves)
    where = {(p["pc_id"], p["path"]) for p in places}
    history: list[dict[str, Any]] = []
    for _ in range(6):
        history = await db.file_index.events_for_paths(sorted(where))
        before = len(where)
        where |= {(h["pc_id"], h["old_path"]) for h in history if h["op"] == "move" and h["old_path"] and not h["is_dir"]}
        if len(where) == before:
            break
    history = [h for h in history if not h["is_dir"] and mine(await pc_of(h["pc_id"]))]
    moved_to = {(h["pc_id"], h["path"]) for h in history if h["op"] == "move"}

    origin_done = False
    for p in places:                                     # earliest first
        if (p["pc_id"], p["path"]) in moved_to:
            continue                                     # it got here by a move, which the history tells below
        host = (await pc_of(p["pc_id"]) or {}).get("hostname", "a machine")
        if not origin_done:
            origin_done = True
            add(p["first_seen_at"], "first_seen", p["pc_id"], p["path"], f"First known on {host}: {p['path']}")
        else:
            add(p["first_seen_at"], "copied", p["pc_id"], p["path"], f"A copy appeared on {host}: {p['path']}")
    for h in history:
        host = (await pc_of(h["pc_id"]) or {}).get("hostname", "a machine")
        op = h["op"]
        if op == "move" and h["old_path"]:
            (of, on), (nf, nn) = _folder_and_name(h["old_path"]), _folder_and_name(h["path"])
            if of == nf:
                add(h["occurred_at"], "renamed", h["pc_id"], h["path"], f"Renamed on {host}: {on} to {nn}")
            else:
                add(h["occurred_at"], "moved", h["pc_id"], h["path"], f"Moved on {host}: {h['old_path']} to {h['path']}")
        elif op == "delete":
            add(h["occurred_at"], "deleted", h["pc_id"], h["path"], f"Deleted from {host}: {h['path']}")
        elif op == "modify":
            add(h["occurred_at"], "edited", h["pc_id"], h["path"], f"Edited on {host}: {h['path']}")
        elif op == "attrib":
            add(h["occurred_at"], "attributes_changed", h["pc_id"], h["path"], f"Attributes changed on {host}: {h['path']}")
        elif op == "security":
            add(h["occurred_at"], "permissions_changed", h["pc_id"], h["path"], f"Who may open it changed on {host}: {h['path']}")

    for a in await db.audit.for_targets("file_index", [str(i) for i in by_id], ["resource.tagged"]):
        p = by_id[int(a["target_id"])]
        host = (await pc_of(p["pc_id"]) or {}).get("hostname", "a machine")
        tag = (a["detail"] or {}).get("tag")
        add(a["occurred_at"], "tagged", p["pc_id"], p["path"], f"Marked as {TAG_WORDS.get(tag, tag)} on {host}", a["actor_account_id"])

    violations = await db.resource.violations_for_files(list(by_id))
    resolved_by = {int(a["target_id"]): a for a in await db.audit.for_targets(
        "resource_violations", [str(v["id"]) for v in violations], ["resource.violation_resolved"])}
    for v in violations:
        if not mine({"department_id": v["department_id"]}):
            continue
        p = by_id[v["file_index_id"]]
        add(v["detected_at"], "flagged", v["found_on_pc_id"], p["path"],
            f"Flagged: {TAG_WORDS.get(v['expected_tag'], v['expected_tag'])} found on {v['hostname']}, where it should not be")
        add(v["detected_at"], "owner_told", v["found_on_pc_id"], p["path"], "The person using that machine was told", v["surfaced_to_account_id"])
        if v["resolved_at"] is not None:
            r = resolved_by.get(v["id"])
            add(v["resolved_at"], "resolved", v["found_on_pc_id"], p["path"], f"Marked put right on {v['hostname']}",
                r["actor_account_id"] if r else None)

    if entry["content_hash"]:
        for sync in await db.flows.syncs_for_content(entry["content_hash"]):
            dest, src = await pc_of(sync["destination_pc_id"]), await pc_of(sync["source_pc_id"])
            if not (mine(dest) or mine(src)):
                continue
            where = (dest or {}).get("hostname", "remote storage")
            path = sync["written_path"] or sync["destination_path"]
            if sync["written_by"] == "external":
                add(sync["occurred_at"], "conflict", sync["destination_pc_id"], path,
                    f"Changed on {where} outside flow {sync['flow_id']}" + ("; kept and the flow carried on" if sync["conflict_resolved"] else ""),
                    sync["written_by_account_id"])
            else:
                add(sync["occurred_at"], "synced", sync["destination_pc_id"], path, f"Flow {sync['flow_id']} carried it to {where}")

    names = await db.accounts.display_names_for(ident.account_id, sorted(people)) if people else {}
    events = []
    for at, ev in sorted(raw, key=lambda t: t[0]):
        who_id = ev.pop("who_id")
        host = (await pc_of(ev["pc_id"]) or {}).get("hostname")
        who = names.get(who_id) if who_id is not None else None
        events.append({"at": _iso(at), **ev, "hostname": host, "who": who,
                       "text": ev["text"] + (f" ({who})" if who and ev["kind"] in ("tagged", "resolved", "conflict", "owner_told") else "")})
    return {"file": {"id": entry["id"], "filename": entry["filename"], "content_hash": entry["content_hash"],
                     "tag": entry["resource_tag"]},
            "places": [{**(row(p) or {}), "hostname": (await pc_of(p["pc_id"]) or {}).get("hostname")} for p in places],
            "events": events}
