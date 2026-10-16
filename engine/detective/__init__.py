"""Detective in the Engine: the behaviour model of `common/detective.py` run over what the Engine already hears, with cases kept, raised and reviewed.

It listens to every file event (create, change, move, copy, delete, hidden/visible, permissions) and to the drive signals, turns each into a `Sig`, asks the
context (is it Falcon's own work? is it restricted? does a task cover it? is the drive familiar?) and feeds the detector. A case that grows is saved; one that
crosses into "case" is raised: the Super User is told, and so is the Admin of the department when it is a department machine. Admin machines are the Super
User's alone to see. It runs by itself: nothing triggers it and the person at the machine is not told.

    detective.cases     {include_noted?, status?}         the cases this person may see, strongest first
    detective.case      {case_id}                         one case: the story, each finding with its evidence, what would make it innocent
    detective.review    {case_id, outcome, note?}         explained | accepted | dismissed | escalated  (the review is kept, never silent)
    detective.overview  {}                                what is open, by intent and level, for the page

The matcher runs here for now, over events the Engine already receives; what makes each change attributable to a person's hands or a program (the
Worker's "witness" signals) arrives as more of the same signals, and the matching can move to the machine without changing what this module keeps.
"""

from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from common.detective import (
    Case,
    Context,
    Detective,
    Finding,
    Sig,
    Update,
    folder_of,
    graph_of,
    name_of,
    sig_from_dict,
    sig_to_dict,
)
from engine.dispatch import Context as HandlerContext
from engine.dispatch import handler
from engine.permissions import int_field, require_role, str_field
from engine.serialize import row, rows
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

TASK_TTL = 120.0
REMEMBER = timedelta(hours=6)
RESUME = timedelta(days=7)
OUTCOMES = ("explained", "accepted", "dismissed", "escalated")
OPEN_LEVELS = ["case", "urgent"]

_det: Detective | None = None
_restored = False
_devices: dict[tuple[int, str], int] = {}
_tasks: dict[int, tuple[float, set[str]]] = {}
_saved: dict[int, int] = {}                       # id(case) -> findings already saved


def reset_state() -> None:
    global _det, _restored
    _det, _restored = None, False
    _devices.clear()
    _tasks.clear()
    _saved.clear()


def tasks_changed() -> None:
    _tasks.clear()


def _detector() -> Detective:
    global _det
    if _det is None:
        _det = Detective(Context(task_things=lambda pc: _tasks.get(pc, (0, set()))[1], known_device=lambda pc, dev: _devices.get((pc, dev), 0)))
    return _det


def install(engine: Engine) -> None:
    engine.file_index.subscribe(lambda event: on_file(engine, event), every_op=True)


# --- what the Engine hears, as signals ---------------------------------------------------------------------

def _verb(event: dict[str, Any]) -> str | None:
    op = event["op"]
    if op == "move":
        old = event.get("old_path") or ""
        return "renamed" if old and folder_of(old).lower() == folder_of(event["path"]).lower() else "moved"
    if op == "attrib":
        detail = event.get("detail") or {}
        if "hidden" not in detail:
            return None
        return "hid" if detail["hidden"] and not detail.get("was_hidden") else "unhid" if not detail["hidden"] and detail.get("was_hidden") else None
    return {"create": "created", "modify": "modified", "copy": "copied", "delete": "deleted", "security": "permissions"}.get(op)


async def _flow_wrote(engine: Engine, pc_id: int, path: str, digest: str | None) -> bool:
    """Falcon's own flows write files too: those are not a person's behaviour."""
    from engine.flow.sync import relative_under

    for dest in await engine.db.flows.destinations_for_pc(pc_id):
        if relative_under(path, dest["destination_path"]) is None:
            continue
        own = await engine.db.flows.last_flow_write_at(dest["id"], path)
        if own is not None and (digest is None or own.get("content_hash") == digest):
            return True
    return False


async def _tasks_things(engine: Engine, pc_id: int) -> None:
    """The files (by content) that a task assigned to the person at this machine asks for: a task for exactly this lowers a finding."""
    now = time.monotonic()
    if pc_id in _tasks and now - _tasks[pc_id][0] < TASK_TTL:
        return
    things: set[str] = set()
    for t in await engine.db.tasks.open_with_items():
        if t.get("assignee_pc_id") != pc_id:
            continue
        for item in t["items"]:
            if item.get("file_hash"):
                things.add(item["file_hash"])
            elif item.get("target_type") == "file" and item.get("name"):
                for hit in await engine.db.file_index.by_name(str(item["name"]), pc_ids=[pc_id]):
                    if hit.get("content_hash"):
                        things.add(hit["content_hash"])
    _tasks[pc_id] = (now, things)


async def on_file(engine: Engine, event: dict[str, Any]) -> None:
    if not engine.db.connected or event.get("is_dir"):
        return
    verb = _verb(event)
    if verb is None:
        return
    await _ensure(engine)
    pc_id, path, op = event["pc_id"], event["path"], event["op"]
    digest = event.get("hash")
    tags: set[str] = set()
    entry = None
    if op != "modify":
        entry = await engine.db.file_index.get(event["file_index_id"]) if event.get("file_index_id") else await engine.db.file_index.by_path(pc_id, path)
        digest = digest or (entry or {}).get("content_hash")
        if (entry or {}).get("resource_tag") == "restricted" or (digest and await engine.db.marks.active_with_hash(digest)):
            tags.add("restricted")
    by = "falcon" if op in ("create", "modify", "move", "copy") and await _flow_wrote(engine, pc_id, path, digest) else "unknown"
    det = _detector()
    mem = det.mem.get(pc_id)
    if mem is not None and mem.devices and await engine.db.resource.is_allowed(pc_id, path, digest):
        tags.add("allowed")
    await _tasks_things(engine, pc_id)
    sig = Sig(time.time(), pc_id, verb, path, str(event.get("old_path") or ""), digest or "", "", by, "", frozenset(tags))
    await _apply(engine, det.feed(sig))


async def on_signal(engine: Engine, pc_id: int, etype: str, data: dict[str, Any]) -> None:
    """A drive plugged in or removed (control.signal)."""
    if not engine.db.connected or etype not in ("usb.inserted", "usb.removed"):
        return
    await _ensure(engine)
    device = str(data.get("device") or data.get("path") or "")
    if not device:
        return
    if etype == "usb.inserted":
        _devices[(pc_id, device)] = await engine.db.detective.see_device(pc_id, device)
    await _apply(engine, _detector().feed(Sig(time.time(), pc_id, "attached" if etype == "usb.inserted" else "detached", device, device=device, by="alone")))


# --- keeping what it concludes ------------------------------------------------------------------------------------

def _row(case: Case, department_id: int | None, raised: bool) -> dict[str, Any]:
    n, latest, nxt = case.stage
    return {"pc_id": case.pc, "department_id": department_id, "intent": case.intent, "level": case.level, "weight": case.weight, "stage_count": n, "stage_name": latest,
            "next_stage": nxt, "not_yet": case.not_yet(), "behaviours": sorted(case.behaviours), "headline": case.headline(), "story": case.story(),
            "first_at": datetime.fromtimestamp(case.first_at, timezone.utc), "last_at": datetime.fromtimestamp(case.last_at, timezone.utc),
            "raised_at": datetime.now(timezone.utc) if raised else None}


def _finding_row(f: Finding) -> dict[str, Any]:
    return {"behaviour": f.behaviour, "graph": f.graph, "weight": f.weight, "at": datetime.fromtimestamp(f.at, timezone.utc), "summary": f.summary, "innocent": f.innocent,
            "why": list(dict.fromkeys(f.why)), "things": sorted(f.things)[:50], "evidence": [sig_to_dict(e) for e in f.evidence[-80:]]}


async def _apply(engine: Engine, updates: list[Update]) -> None:
    done: set[int] = set()
    for u in updates:
        case = u.case
        if u.created or u.raised or case.level != "quiet" or case.id is not None:
            if id(case) in done and not u.raised:
                continue
            done.add(id(case))
            await _save(engine, u)


async def _save(engine: Engine, u: Update) -> None:
    case = u.case
    if case.level == "quiet" and case.id is None:
        return                                           # not worth a record yet: it is kept in memory and joins one if the next step makes it so
    pc = await engine.db.accounts.pc(case.pc)
    department_id = pc["department_id"] if pc else None
    fresh = case.findings[_saved.get(id(case), 0):]
    case.id = await engine.db.detective.save_case(case.id, _row(case, department_id, u.raised), [_finding_row(f) for f in fresh])
    _saved[id(case)] = len(case.findings)
    if u.raised:
        await engine.audit.record(None, "detective.raised", target_type="detective_cases", target_id=case.id, pc_id=case.pc,
                                  detail={"intent": case.intent, "level": case.level, "weight": round(case.weight, 2), "stage": case.stage[1]})
        payload = {"case_id": case.id, "intent": case.intent, "level": case.level, "pc_id": case.pc, "host": (pc or {}).get("hostname"), "not_yet": case.not_yet()}
        await engine.push_to_role("super_user", "detective.raised", payload)
        if pc and pc["pc_type"] == "client_pc" and department_id is not None:                 # an Admin's own machine is the Super User's alone
            await engine.push_to_role("admin", "detective.raised", payload, department_id=department_id)


async def _ensure(engine: Engine) -> None:
    """After a restart: the last hours of activity go back into each machine's memory (without being judged again), and open cases resume."""
    global _restored
    if _restored:
        return
    _restored = True
    det = _detector()
    since = datetime.now(timezone.utc) - REMEMBER
    for r in await engine.db.detective.recent_events(since):
        verb = _verb({"op": r["op"], "path": r["path"], "old_path": r["old_path"], "detail": r["detail"] or {}})
        if verb:
            det.remember(Sig(r["occurred_at"].timestamp(), r["pc_id"], verb, r["path"], r["old_path"] or "", r["content_hash"] or ""))
    for c in await engine.db.detective.open_since(datetime.now(timezone.utc) - RESUME):
        case = Case(pc=c["pc_id"], id=c["id"], first_at=c["first_at"].timestamp(), last_at=c["last_at"].timestamp())
        for f in await engine.db.detective.findings(c["id"]):
            case.findings.append(Finding(f["behaviour"], f["graph"], f["at"].timestamp(), c["pc_id"], float(f["weight"]), frozenset(f["things"] or []), f["summary"],
                                         [sig_from_dict(e) for e in f["evidence"] or []], f["innocent"] or "", list(f["why"] or [])))
        det.cases.append(case)
        _saved[id(case)] = len(case.findings)


# --- who sees what ----------------------------------------------------------------------------------------------------------

def _scope(ctx: HandlerContext) -> dict[str, Any]:
    ident = require_role(ctx, "super_user", "admin")
    if ident.role == "super_user":
        return {}
    return {"department_id": ident.department_id, "only_pc_types": ["client_pc"]}           # an Admin: their department's machines, never their own or another Admin's


def _view(c: dict[str, Any]) -> dict[str, Any]:
    out = row(c) or {}
    out["host"] = c.get("hostname")
    return out


async def _visible(ctx: HandlerContext, case_id: int) -> dict[str, Any]:
    case = await ctx.engine.db.detective.case(case_id)
    scope = _scope(ctx)
    if case is None or (scope and (case["pc_department_id"] != scope["department_id"] or case["pc_type"] != "client_pc")):
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such case")
    return case


@handler("detective.cases")
async def cases(ctx: HandlerContext, payload: dict[str, Any]) -> dict[str, Any]:
    scope = _scope(ctx)
    levels = ["noted", "case", "urgent"] if payload.get("include_noted") else OPEN_LEVELS
    status = payload.get("status")
    if status is not None and status not in ("open", "reviewed", *OUTCOMES):
        raise ProtocolError(ErrorCode.INVALID, "status is open, reviewed, explained, accepted, dismissed or escalated")
    if status in ("reviewed", *OUTCOMES):
        levels = None                                                  # anything that was reviewed, whatever its level was
    return {"cases": [_view(c) for c in await ctx.engine.db.detective.cases(levels=levels, status=status, **scope)]}


@handler("detective.case")
async def case(ctx: HandlerContext, payload: dict[str, Any]) -> dict[str, Any]:
    c = await _visible(ctx, int_field(payload, "case_id"))
    found = await ctx.engine.db.detective.findings(c["id"])
    names = await ctx.engine.db.accounts.display_names_for(ctx.identity.account_id, [c["reviewed_by_account_id"]] if c.get("reviewed_by_account_id") else [])
    out = _view(c)
    out["reviewed_by"] = names.get(c.get("reviewed_by_account_id"))
    seen: set[Sig] = set()
    sigs = [e for f in found for e in (sig_from_dict(x) for x in (f["evidence"] or [])) if not (e in seen or seen.add(e))]
    return {"case": out, "findings": rows(found), "graph": graph_of(sigs)}


@handler("detective.review")
async def review(ctx: HandlerContext, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "super_user", "admin")
    c = await _visible(ctx, int_field(payload, "case_id"))
    outcome = str_field(payload, "outcome", choices=OUTCOMES)
    note = " ".join(str(payload.get("note") or "").split())[:500] or None
    if not await ctx.engine.db.detective.review(c["id"], outcome, ident.account_id, note):
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such case")
    await ctx.engine.audit.record(ctx, f"detective.{outcome}", target_type="detective_cases", target_id=c["id"], pc_id=c["pc_id"], detail={"note": note, "intent": c["intent"]})
    if outcome == "escalated":
        await ctx.engine.push_to_role("super_user", "detective.escalated", {"case_id": c["id"], "intent": c["intent"], "host": c.get("hostname")})
    return {"case_id": c["id"], "status": outcome}


@handler("detective.overview")
async def overview(ctx: HandlerContext, payload: dict[str, Any]) -> dict[str, Any]:
    scope = _scope(ctx)
    counts = await ctx.engine.db.detective.counts(**scope)
    open_ = [c for c in counts if c["status"] == "open"]
    by_level = {lv: sum(c["n"] for c in open_ if c["level"] == lv) for lv in ("noted", "case", "urgent")}
    by_intent: dict[str, int] = {}
    for c in open_:
        if c["level"] in ("case", "urgent"):
            by_intent[c["intent"]] = by_intent.get(c["intent"], 0) + c["n"]
    return {"by_level": by_level, "by_intent": by_intent, "reviewed": sum(c["n"] for c in counts if c["status"] != "open")}


__all__ = ["case", "cases", "install", "name_of", "on_file", "on_signal", "overview", "reset_state", "review"]
