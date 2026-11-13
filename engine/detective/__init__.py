"""Detective in the Engine: the behaviour model of `common/detective.py` run over what the Engine already hears, with cases kept, raised and reviewed.

It listens to every file event (create, change, move, copy, delete, hidden/visible, permissions) and to the drive signals, turns each into a `Sig`, asks the
context (is it Falcon's own work? is it restricted? does a task cover it? is the drive familiar?) and feeds the detector. A case that grows is saved; one that
crosses into "case" is raised: the head of the organisation is told, and so is the Admin of the department when it is a department machine. Admin machines are the head of
the organisation's alone to see. It runs by itself: nothing triggers it and the person at the machine is not told.

    detective.cases     {include_noted?, status?}         the cases this person may see, strongest first
    detective.case      {case_id}                         one case: the story, each finding with its evidence, what would make it innocent
    detective.review    {case_id, outcome, note?}         explained | accepted | dismissed | escalated  (the review is kept, never silent)
    detective.overview  {}                                what is open, by intent and level, for the page

The matcher itself runs in its own process (`brain.py`, started by `host.py`; the user, 12 Nov 2026), so however long it thinks the Engine keeps answering.
This module gathers each event's facts, which need the database, sends the event with what the matcher may ask about that machine (`_ctx`), and keeps
and raises what comes back. `FALCON_DETECTIVE_PROCESS=0` runs the same matcher inside the Engine.
"""

from __future__ import annotations

import asyncio
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from common.detective import (
    Case,
    Finding,
    Memory,
    Rule,
    Sig,
    folder_of,
    graph_of,
    name_of,
    rule_options,
    sig_from_dict,
    sig_to_dict,
)
from engine.detective import labels, telling
from engine.detective.brain import CaseView, UpdateView, view_of
from engine.detective.host import LocalMatcher, MatcherGone, ProcessMatcher
from engine.dispatch import Context as HandlerContext
from engine.dispatch import handler
from engine.permissions import int_field, kept, require_role, str_field
from engine.serialize import row, rows
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

TASK_TTL = 120.0
REMEMBER = timedelta(days=30)                   # what a restart puts back on the board: the areas a patient person has covered over days (the matcher itself keeps six hours of detail)
RESUME = timedelta(days=7)
OUTCOMES = ("explained", "accepted", "dismissed", "escalated")
OPEN_LEVELS = ["case", "urgent"]

_matcher: LocalMatcher | ProcessMatcher | None = None
_restored_for = 0                                   # the matcher's generation the last days were put back into (a new process starts empty)
_drives: dict[int, bool] = {}                       # machine -> it has a drive attached (the matcher's own memory, as its last answer said)
_ids: dict[int, int] = {}                           # the matcher's case key -> the case's id in the database
_devices: dict[tuple[int, str], int] = {}          # (pc, drive's own name) -> how many times this machine had seen it before the last plug-in
_keys: dict[tuple[int, str], str] = {}             # (pc, where it is mounted now) -> the drive's own name (its serial when the Worker could read one)
_tasks: dict[int, tuple[float, set[str]]] = {}
_saved: dict[int, int] = {}                       # id(case) -> findings already saved
_rules: dict[int, list[Rule]] = {}                # machine -> what a reviewer has said is fine there


_queue: asyncio.Queue[tuple[str, Any]] | None = None
_worker: asyncio.Task[None] | None = None
MODEL_QUEUE = 20


def reset_state() -> None:
    global _matcher, _restored_for, _queue, _worker
    if _matcher is not None:
        _matcher.kill()
    _matcher, _restored_for = None, 0
    _drives.clear()
    _ids.clear()
    if _worker is not None:
        _worker.cancel()
    _queue, _worker = None, None
    _devices.clear()
    _keys.clear()
    _tasks.clear()
    _saved.clear()
    _rules.clear()


def tasks_changed() -> None:
    _tasks.clear()
    from engine.task import expected

    expected.invalidate()


def _match(engine: Engine | None = None) -> LocalMatcher | ProcessMatcher:
    global _matcher
    if _matcher is None:
        own = engine is None or getattr(engine.settings, "detective_process", True)
        _matcher = ProcessMatcher() if own else LocalMatcher()
    return _matcher


def device_uses(pc: int, device: str) -> int:
    """How many times this machine had seen this drive before it was last plugged in, whatever letter it has now (by its own name, its serial)."""
    return _devices.get((pc, _keys.get((pc, device), device)), 0)


def _ctx(pc: int) -> dict[str, Any]:
    """What the matcher may ask about one machine, sent with each of its events: the files its tasks cover, its drives' familiarity, what was ruled fine."""
    uses = {key: n for (p, key), n in _devices.items() if p == pc}
    uses.update({mount: _devices.get((pc, key), 0) for (p, mount), key in _keys.items() if p == pc})
    return {"tasks": _tasks.get(pc, (0, set()))[1], "uses": uses, "rules": _rules.get(pc, [])}


async def _feed(engine: Engine, sig: Sig) -> None:
    try:
        updates, drives = await _match(engine).call("feed", sig, _ctx(sig.pc))
    except MatcherGone:
        log.warning("detective: an event on machine %s was not read (the matcher had stopped)", sig.pc)
        return
    _drives[sig.pc] = drives
    await _apply(engine, updates)


async def memory(pc: int) -> Memory | None:
    """A copy of what the matcher remembers of one machine (for the tests, and for looking into Detective itself)."""
    return await _match().call("memory", pc)


async def stop() -> None:
    if _matcher is not None:
        await _matcher.stop()


def install(engine: Engine) -> None:
    engine.file_index.subscribe(lambda event: on_file(engine, event), every_op=True, stage="judge", name="detective")

    async def hear_signal(event: Any) -> None:
        await on_signal(engine, event.data["pc_id"], event.data["type"], event.data["data"])

    engine.bus.on("os.signal", hear_signal, stage="judge", name="detective.signal")

    async def hear_task(event: Any) -> None:
        tasks_changed()                                   # what a task covers is part of what Detective weighs

    engine.bus.on("task.*", hear_task, stage="judge", name="detective.tasks")


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
    """The files (by content) that a task assigned to the person at this machine asks for: Task owns this knowledge (engine/task/expected.py); Detective keeps a copy for the
    findings that span several files, refreshed from it."""
    from engine.task import expected

    now = time.monotonic()
    if pc_id in _tasks and now - _tasks[pc_id][0] < TASK_TTL:
        return
    _tasks[pc_id] = (now, await expected.hashes_for(engine, pc_id))


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
    facts = event.get("facts") or {}                      # what the earlier stages found out (engine/bus.py): read, not asked again
    entry = None
    if op != "modify":
        if "entry" in facts:
            entry = facts["entry"]
        else:
            entry = await engine.db.file_index.get(event["file_index_id"]) if event.get("file_index_id") else await engine.db.file_index.by_path(pc_id, path)
        digest = digest or (entry or {}).get("content_hash")
        if "restricted" in facts:
            restricted = facts["restricted"] is not None
        else:
            restricted = (entry or {}).get("resource_tag") == "restricted" or bool(digest and await engine.db.marks.active_with_hash(digest))
        if restricted:
            tags.add("restricted")
            if facts.get("own_scope") if "own_scope" in facts else await _own_scope(engine, pc_id, entry or {}):
                tags.add("own_scope")
    if op == "delete" and digest and not await engine.db.file_index.by_hash(digest):
        tags.add("only_copy")                           # nothing else the index knows of holds this content
    seen = event.get("witness") or {}
    wrote = facts["flow_wrote"] if "flow_wrote" in facts else (op in ("create", "modify", "move", "copy") and await _flow_wrote(engine, pc_id, path, digest))
    by = "falcon" if wrote else seen.get("by", "unknown")
    if event.get("drive"):
        _drives[pc_id] = await _match(engine).call("know_drive", pc_id, str(event["drive"]), time.time())
        if op == "delete":
            return                                      # a file taken off a drive is not erasing anything on this machine
    if _drives.get(pc_id) and await engine.db.resource.is_allowed(pc_id, path, digest):
        tags.add("allowed")
    if facts.get("task_expects"):
        tags.add("task_expected")                           # Task's fact: an open task asks for exactly this
    if facts.get("flow_bypass"):
        tags.add("flow_bypass")                             # Flow's fact: this is what a flow delivers here, put here by hand instead
    await _tasks_things(engine, pc_id)
    info: dict[str, Any] = {"title": seen["title"]} if by == "hand" and seen.get("title") else {}
    if event.get("late"):
        info["late"] = True                              # found afterwards: when it happened is the file's own time, and who did it cannot be told
    sig = Sig(event.get("at") or time.time(), pc_id, verb, path, str(event.get("old_path") or ""), digest or "", seen.get("program") or (seen.get("front", "") if by == "hand" else ""), by, "",
              frozenset(tags), info)
    await _feed(engine, sig)


async def _own_scope(engine: Engine, pc_id: int, entry: dict[str, Any]) -> bool:
    """Restricted material that belongs to the department this machine is in: that is what the people there work with."""
    scope = entry.get("resource_tag_scope_department_id")
    if scope is None:
        return False
    pc = await engine.db.accounts.pc(pc_id) or {}
    return pc.get("department_id") == scope


async def _outside_role(engine: Engine, pc_id: int, entry: dict[str, Any], path: str) -> bool:
    """Is this file outside what this person is meant to have in front of them? A restricted or admin-tier file that belongs to another department, an admin-tier file
    on a worker's machine, or a restricted file on somebody else's share. Resource tiers are the Engine's own idea of who is meant to see what."""
    tag = entry.get("resource_tag")
    if tag not in ("restricted", "admin"):
        return False
    pc = await engine.db.accounts.pc(pc_id) or {}
    scope = entry.get("resource_tag_scope_department_id")
    if scope is not None and pc.get("department_id") is not None and scope != pc["department_id"]:
        return True
    if tag == "admin" and pc.get("pc_type") == "client_pc":
        return True
    host = path.replace("/", "\\")
    if host.startswith("\\\\") and tag == "restricted":
        owner = host[2:].split("\\", 1)[0].lower()
        return bool(owner) and owner != str(pc.get("hostname") or "").lower()
    return False


async def _on_opened(engine: Engine, pc_id: int, data: dict[str, Any]) -> None:
    """Which files were opened lately (a batch from the machine). Only the ones that matter become something Detective reads: restricted ones, and ones outside this
    person's work; the rest of what was opened is nobody's business."""
    await _ensure(engine)
    now = time.time()
    for item in (data.get("files") or [])[:300]:
        path = str((item or {}).get("path") or "")
        if not path:
            continue
        entry = await engine.db.file_index.by_path(pc_id, path)
        if entry is None or entry.get("gone_at") is not None:
            continue
        digest = entry.get("content_hash")
        tags: set[str] = set()
        if entry.get("resource_tag") == "restricted" or (digest and await engine.db.marks.active_with_hash(digest)):
            tags.add("restricted")
        if await _outside_role(engine, pc_id, entry, path):
            tags.add("outside_role")
        if not tags:
            continue
        sig = Sig(now, pc_id, "opened", path, "", digest or "", str((item or {}).get("process") or "")[:120], "unknown", "", frozenset(tags))
        await _feed(engine, sig)


async def on_presence(engine: Engine, pc_id: int, online: bool) -> None:
    """A machine stopped reporting (or is back). Going quiet only matters when something worth a look had just happened on it: the watch is being slipped."""
    if not engine.db.connected or online:
        return
    await _ensure(engine)
    await _feed(engine, Sig(time.time(), pc_id, "silent", by="alone"))


async def on_signal(engine: Engine, pc_id: int, etype: str, data: dict[str, Any]) -> None:
    """What the OS tells the Worker that bears on behaviour: a drive plugged in or removed, a tool that photographs the screen started, a log cleared (control.signal)."""
    if not engine.db.connected:
        return
    if etype == "program.launched":
        from common.detective import CAPTURE_TOOLS

        process = str(data.get("process") or "")
        if not any(t in process.lower() for t in CAPTURE_TOOLS):
            return
        await _ensure(engine)
        await _feed(engine, Sig(time.time(), pc_id, "launched", program=process[:120], by="unknown"))
        return
    if etype == "file.opened":
        await _on_opened(engine, pc_id, data)
        return
    if etype == "network.upload":
        await _ensure(engine)
        process = str(data.get("process") or "")[:120]
        info = {"bytes": int(data.get("bytes") or 0), "to": str(data.get("to") or "")[:60], "destinations": int(data.get("destinations") or 1), "seconds": int(data.get("seconds") or 60)}
        await _feed(engine, Sig(time.time(), pc_id, "uploaded", program=process, by="unknown", info=info))
        return
    if etype == "screen.captured":
        await _ensure(engine)
        kind = "screen" if data.get("kind") == "screen" else "region"
        await _feed(engine, Sig(time.time(), pc_id, "captured", program=str(data.get("process") or "")[:120], by="hand", info={"kind": kind}))
        return
    if etype == "log.cleared":
        await _ensure(engine)
        which = str(data.get("log") or "event")[:40]
        await _feed(engine, Sig(time.time(), pc_id, "cleared", by="unknown", info={"what": f"the {which} log", "log": which}))
        return
    if etype not in ("usb.inserted", "usb.removed"):
        return
    await _ensure(engine)
    device = str(data.get("device") or data.get("path") or "")
    if not device:
        return
    info: dict[str, Any] = {k: str(data[k])[:80] for k in ("serial", "label") if data.get(k)}
    if etype == "usb.inserted":
        key = info.get("serial") or device                  # the same drive in another letter is still the same drive
        _keys[(pc_id, device)] = key
        _devices[(pc_id, key)] = await engine.db.detective.see_device(pc_id, key)
    await _feed(engine, Sig(time.time(), pc_id, "attached" if etype == "usb.inserted" else "detached", device, device=device, by="alone", info=info))


# --- keeping what it concludes ------------------------------------------------------------------------------------

def _row(case: CaseView | Case, department_id: int | None, raised: bool) -> dict[str, Any]:
    if isinstance(case, Case):
        case = view_of(case)
    n, latest, nxt = case.stage
    return {"pc_id": case.pc, "department_id": department_id, "intent": case.intent, "level": case.level, "weight": case.weight, "stage_count": n, "stage_name": latest,
            "next_stage": nxt, "not_yet": case.not_yet, "behaviours": case.behaviours, "headline": case.headline, "story": case.story,
            "first_at": datetime.fromtimestamp(case.first_at, timezone.utc), "last_at": datetime.fromtimestamp(case.last_at, timezone.utc),
            "raised_at": datetime.now(timezone.utc) if raised else None}


def _finding_row(f: Finding) -> dict[str, Any]:
    return {"behaviour": f.behaviour, "graph": f.graph, "weight": f.weight, "at": datetime.fromtimestamp(f.at, timezone.utc), "summary": f.summary, "innocent": f.innocent,
            "why": list(dict.fromkeys(f.why)), "things": sorted(f.things)[:50], "evidence": [sig_to_dict(e) for e in f.evidence[-80:]]}


async def _apply(engine: Engine, updates: list[UpdateView]) -> None:
    done: set[int] = set()
    for u in updates:
        case = u.case
        if case.id is None and case.key in _ids:
            case.id = _ids[case.key]                     # saved by an earlier event's answer, which the matcher may not have heard of yet
        if u.created or u.raised or case.level != "quiet" or case.id is not None:
            if case.key in done and not u.raised:
                continue
            done.add(case.key)
            await _save(engine, u)


async def _save(engine: Engine, u: UpdateView) -> None:
    case = u.case
    if case.level == "quiet" and case.id is None:
        return                                           # not worth a record yet: it is kept in memory and joins one if the next step makes it so
    pc = await engine.db.accounts.pc(case.pc)
    department_id = pc["department_id"] if pc else None
    fresh = case.findings[max(0, _saved.get(case.key, 0) - case.findings_from):]
    case.id = await engine.db.detective.save_case(case.id, _row(case, department_id, u.raised), [_finding_row(f) for f in fresh])
    _ids[case.key] = case.id
    _saved[case.key] = max(_saved.get(case.key, 0), case.total)
    _match(engine).post("saved_as", case.key, case.id, case.total)
    if u.raised and engine.llm.available:
        _ask(engine, "opinion", (case.id, case.story))
        if telling.smoothing(engine.llm):
            _ask(engine, "telling", case.id)
    if u.raised:
        await engine.audit.record(None, "detective.raised", target_type="detective_cases", target_id=case.id, pc_id=case.pc,
                                  detail={"intent": case.intent, "level": case.level, "weight": round(case.weight, 2), "stage": case.stage[1]})
        payload = {"case_id": case.id, "intent": case.intent, "level": case.level, "pc_id": case.pc, "host": (pc or {}).get("hostname"), "not_yet": case.not_yet}
        await engine.announce("case.raised", {**payload, "behaviours": case.behaviours, "weight": round(case.weight, 2)}, source="system", pc=case.pc)
        await engine.push_to_role("super_user", "detective.raised", payload)
        if pc and pc["pc_type"] == "client_pc" and department_id is not None:                 # an Admin's own machine is the head of the organisation's alone
            await engine.push_to_role("admin", "detective.raised", payload, department_id=department_id)


# --- the local model, in the background, advisory ---------------------------------------------------------------------------

def _ask(engine: Engine, kind: str, what: Any) -> None:
    """Queue a question for the model. Never waits, never blocks a file operation, and drops the question when the model is away or the queue is full."""
    global _queue, _worker
    if not engine.llm.available:
        return
    if _queue is None:
        _queue = asyncio.Queue(maxsize=MODEL_QUEUE)
    if _worker is None or _worker.done():
        _worker = asyncio.ensure_future(_model_worker(engine, _queue))
    try:
        _queue.put_nowait((kind, what))
    except asyncio.QueueFull:
        log.debug("detective: the model's queue is full; a question was dropped")


async def _model_worker(engine: Engine, queue: asyncio.Queue[tuple[str, Any]]) -> None:
    while True:
        kind, what = await queue.get()
        try:
            if kind == "opinion":
                await _opinion(engine, *what)
            elif kind == "telling":
                await _tell(engine, what)
        except asyncio.CancelledError:
            raise
        except Exception:
            log.exception("detective: the model's reading failed")


async def _opinion(engine: Engine, case_id: int | None, story: list[str]) -> None:
    if case_id is None:
        return
    says = await labels.second_opinion(engine.llm, story)
    if says is None:
        return
    await engine.db.detective.set_model_says(case_id, says)
    c = await engine.db.detective.case(case_id)
    if c is not None:
        payload = {"case_id": case_id, "model_says": says}
        await engine.push_to_role("super_user", "detective.updated", payload)
        if c["pc_type"] == "client_pc" and c.get("department_id") is not None:
            await engine.push_to_role("admin", "detective.updated", payload, department_id=c["department_id"])


async def _tell(engine: Engine, case_id: int | None) -> None:
    """Smooth a case's account with the model, paragraph by paragraph; keep only what passes the check (engine/detective/telling.py)."""
    if case_id is None:
        return
    c = await engine.db.detective.case(case_id)
    if c is None:
        return
    t = telling.compose(c, await engine.db.detective.findings(case_id), await engine.db.sessions.signed_in_at(c["pc_id"], c["first_at"]), c.get("hostname"))
    if (c.get("telling") or {}).get("fingerprint") == t.fingerprint():
        return                                                        # (asked twice while the first answer was coming)
    paragraphs = await telling.smooth(engine.llm, t)
    await engine.db.detective.set_telling(case_id, {"fingerprint": t.fingerprint(), "paragraphs": paragraphs})
    if any(paragraphs):
        payload = {"case_id": case_id, "telling": True}
        await engine.push_to_role("super_user", "detective.updated", payload)
        if c["pc_type"] == "client_pc" and c.get("department_id") is not None:
            await engine.push_to_role("admin", "detective.updated", payload, department_id=c["department_id"])


async def _ensure(engine: Engine) -> None:
    """After a restart, and whenever the matcher's process is new: the last days of activity go back into each machine's memory (without being judged
    again), and open cases resume."""
    global _restored_for
    m = _match(engine)
    generation = await m.ready()
    if _restored_for == generation:
        return
    first = _restored_for == 0
    _restored_for = generation
    _saved.clear()
    _ids.clear()
    _drives.clear()
    if first:
        for r in await engine.db.detective.live_rules():
            _rules.setdefault(r["pc_id"], []).append(_rule(r))
    since = datetime.now(timezone.utc) - REMEMBER
    batch: list[Sig] = []
    for r in await engine.db.detective.recent_events(since):
        verb = _verb({"op": r["op"], "path": r["path"], "old_path": r["old_path"], "detail": r["detail"] or {}})
        if verb:
            batch.append(Sig(r["occurred_at"].timestamp(), r["pc_id"], verb, r["path"], r["old_path"] or "", r["content_hash"] or "", by=(r["detail"] or {}).get("by", "unknown")))
        if len(batch) >= 2000:
            _drives.update(await m.call("remember", batch))
            batch = []
    if batch:
        _drives.update(await m.call("remember", batch))
    for c in await engine.db.detective.open_since(datetime.now(timezone.utc) - RESUME):
        case = Case(pc=c["pc_id"], id=c["id"], first_at=c["first_at"].timestamp(), last_at=c["last_at"].timestamp())
        for f in await engine.db.detective.findings(c["id"]):
            case.findings.append(Finding(f["behaviour"], f["graph"], f["at"].timestamp(), c["pc_id"], float(f["weight"]), frozenset(f["things"] or []), f["summary"],
                                         [sig_from_dict(e) for e in f["evidence"] or []], f["innocent"] or "", list(f["why"] or [])))
        key = await m.call("restore", case)
        _saved[key] = len(case.findings)
        _ids[key] = c["id"]


def _rule(r: dict[str, Any]) -> Rule:
    return Rule(r["id"], r["pc_id"], r["graph"], r["kind"], r["value"], r["made_at"].strftime("%d %b") if r.get("made_at") else "")


# --- who sees what ----------------------------------------------------------------------------------------------------------

def _scope(ctx: HandlerContext) -> dict[str, Any]:
    ident = require_role(ctx, "super_user", "admin")
    if ident.role == "super_user":
        return {}
    if not kept(ident):
        return {"only_pc_types": ["client_pc"]}                                                    # IT: every department's machines, never an Admin's
    return {"department_id": ident.department_id, "only_pc_types": ["client_pc"]}           # an Admin: their department's machines, never their own or another Admin's


def _view(c: dict[str, Any]) -> dict[str, Any]:
    out = row(c) or {}
    out["host"] = c.get("hostname")
    out.pop("telling", None)                      # (the account is said in words by detective.case, not as it is kept)
    return out


async def _visible(ctx: HandlerContext, case_id: int) -> dict[str, Any]:
    case = await ctx.engine.db.detective.case(case_id)
    scope = _scope(ctx)
    if case is None or (scope and ((scope.get("department_id") is not None and case["pc_department_id"] != scope["department_id"])
                                   or case["pc_type"] != "client_pc")):
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
    found = await ctx.engine.db.detective.cases(levels=levels, status=status, **scope)
    restricted = await ctx.engine.db.detective.restricted_among([c["id"] for c in found])
    return {"cases": [{**_view(c), "restricted": c["id"] in restricted} for c in found]}


@handler("detective.case")
async def case(ctx: HandlerContext, payload: dict[str, Any]) -> dict[str, Any]:
    c = await _visible(ctx, int_field(payload, "case_id"))
    found = await ctx.engine.db.detective.findings(c["id"])
    names = await ctx.engine.db.accounts.display_names_for(ctx.identity.account_id, [c["reviewed_by_account_id"]] if c.get("reviewed_by_account_id") else [])
    out = _view(c)
    out["reviewed_by"] = names.get(c.get("reviewed_by_account_id"))
    seen: set[Sig] = set()
    sigs = [e for f in found for e in (sig_from_dict(x) for x in (f["evidence"] or [])) if not (e in seen or seen.add(e))]
    again = [Finding(f["behaviour"], f["graph"], f["at"].timestamp(), c["pc_id"], float(f["weight"]), frozenset(), "", [sig_from_dict(e) for e in f["evidence"] or []], "", list(f["why"] or []))
             for f in found]
    held = Case(pc=c["pc_id"], findings=again)
    return {"case": out, "findings": rows(found), "graph": graph_of(sigs), "rule_options": rule_options(again), "board": held.board(),
            "glance": await _glance(ctx, c, sigs), "telling": await _telling(ctx, c, found)}


async def _telling(ctx: HandlerContext, c: dict[str, Any], found: list[dict[str, Any]]) -> dict[str, Any]:
    """The case told in words (ENGINE-GAPS #15): the Engine's own account, every fact filled in from the case, or the model's smoothing of it
    when that passed the check and was made from the case as it is now. People are named the way this viewer names them."""
    db = ctx.engine.db
    t = telling.compose(c, found, await db.sessions.signed_in_at(c["pc_id"], c["first_at"]), c.get("hostname"))
    people = sorted({p.value for para in t.paragraphs for p in para if isinstance(p, telling.Fact) and p.kind == "person"})
    names = await db.accounts.display_names_for(ctx.identity.account_id, people) if people else {}
    kept_ = c.get("telling") or {}
    fresh = kept_.get("fingerprint") == t.fingerprint()
    if not fresh and telling.smoothing(ctx.engine.llm) and ctx.engine.llm.available:
        _ask(ctx.engine, "telling", c["id"])
    return t.view(names, kept_.get("paragraphs") if fresh else None)


async def _glance(ctx: HandlerContext, c: dict[str, Any], sigs: list[Sig]) -> dict[str, Any]:
    """The At a glance panel (ENGINE-GAPS #16): how far it got (the last stage reached and the next), whether restricted files are involved, who was
    signed in when it began (not who is signed in now), the earlier cases on the same machine and how they ended, and when it was raised."""
    db = ctx.engine.db
    then = await db.sessions.signed_in_at(c["pc_id"], c["first_at"])
    earlier = await db.detective.earlier_on_pc(c["pc_id"], c["first_at"])
    names = await db.accounts.display_names_for(ctx.identity.account_id, sorted({s["occupant_account_id"] for s in then})) if then else {}
    return {"stage": c.get("stage_name"), "stage_count": c.get("stage_count"), "next_stage": c.get("next_stage"),
            "restricted": any("restricted" in e.tags for e in sigs),
            "signed_in_then": [{"account_id": s["occupant_account_id"], "name": names.get(s["occupant_account_id"]),
                                "how": "their own" if s["occupied_via"] == "native" else "entered"} for s in then],
            "earlier": [{"case_id": e["id"], "intent": e["intent"], "level": e["level"], "outcome": e["status"], "headline": e["headline"],
                         "at": e["first_at"].isoformat()} for e in earlier],
            "raised_at": c["raised_at"].isoformat() if c.get("raised_at") else None,
            "lasted_s": int((c["last_at"] - c["first_at"]).total_seconds())}


@handler("detective.review")
async def review(ctx: HandlerContext, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "super_user", "admin")
    c = await _visible(ctx, int_field(payload, "case_id"))
    outcome = str_field(payload, "outcome", choices=OUTCOMES)
    note = " ".join(str(payload.get("note") or "").split())[:500] or None
    keep = payload.get("remember")                                    # "and treat this as fine next time": {"kind": "program"|"folder"|"drive"}, only on a dismissal or an explanation
    kind = keep.get("kind") if isinstance(keep, dict) else None
    if keep is not None and (outcome not in ("dismissed", "explained") or kind not in ("program", "folder", "drive")):
        raise ProtocolError(ErrorCode.INVALID, "a rule is written down only with a dismissal or an explanation, for a program, a folder or a drive")
    if not await ctx.engine.db.detective.review(c["id"], outcome, ident.account_id, note):
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such case")
    if outcome != "escalated":                                       # (escalated: still being worked, and still growing)
        _match(ctx.engine).post("close", c["id"])
    made: list[dict[str, Any]] = []
    if kind:
        made = await _write_rules(ctx, c, kind, ident.account_id)
    await ctx.engine.audit.record(ctx, f"detective.{outcome}", target_type="detective_cases", target_id=c["id"], pc_id=c["pc_id"], detail={"note": note, "intent": c["intent"]})
    await ctx.engine.announce("case.reviewed", {"case_id": c["id"], "outcome": outcome, "pc_id": c["pc_id"], "intent": c["intent"], "host": c.get("hostname")}, pc=c["pc_id"])
    if outcome == "escalated":
        await ctx.engine.push_to_role("super_user", "detective.escalated", {"case_id": c["id"], "intent": c["intent"], "host": c.get("hostname")})
    return {"case_id": c["id"], "status": outcome, "rules": made}


async def _write_rules(ctx: HandlerContext, c: dict[str, Any], kind: str, account_id: int) -> list[dict[str, Any]]:
    """The reviewer said this is fine, and to remember it: one rule per kind of finding in the case that involves that program, folder or drive."""
    found = [Finding(f["behaviour"], f["graph"], f["at"].timestamp(), c["pc_id"], float(f["weight"]), frozenset(), "", [sig_from_dict(e) for e in f["evidence"] or []], "")
             for f in await ctx.engine.db.detective.findings(c["id"])]
    made: list[dict[str, Any]] = []
    for o in (o for o in rule_options(found) if o["kind"] == kind):
        rid = await ctx.engine.db.detective.add_rule(c["pc_id"], o["graph"], kind, o["value"], c["id"], account_id)
        if rid is None:
            continue                                                       # already written down
        _rules.setdefault(c["pc_id"], []).append(Rule(rid, c["pc_id"], o["graph"], kind, o["value"]))
        await ctx.engine.audit.record(ctx, "detective.rule_made", target_type="detective_rules", target_id=rid, pc_id=c["pc_id"], detail={**o, "case_id": c["id"]})
        made.append({"id": rid, **o})
    return made


@handler("detective.rules")
async def rules(ctx: HandlerContext, payload: dict[str, Any]) -> dict[str, Any]:
    return {"rules": [_view(r) for r in await ctx.engine.db.detective.rules(**_scope(ctx))]}


@handler("detective.rule_revoke")
async def rule_revoke(ctx: HandlerContext, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "super_user", "admin")
    r = await ctx.engine.db.detective.rule(int_field(payload, "rule_id"))
    scope = _scope(ctx)
    if r is None or (scope and (r["pc_department_id"] != scope["department_id"] or r["pc_type"] != "client_pc")):
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such rule")
    if not await ctx.engine.db.detective.revoke_rule(r["id"], ident.account_id):
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such rule")
    _rules[r["pc_id"]] = [x for x in _rules.get(r["pc_id"], []) if x.id != r["id"]]
    await ctx.engine.audit.record(ctx, "detective.rule_revoked", target_type="detective_rules", target_id=r["id"], pc_id=r["pc_id"], detail={"graph": r["graph"], "kind": r["kind"], "value": r["value"]})
    return {"rule_id": r["id"]}


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


__all__ = ["case", "cases", "install", "name_of", "on_file", "on_signal", "overview", "reset_state", "review", "rule_revoke", "rules"]
