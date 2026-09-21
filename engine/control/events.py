"""Events (Control -> Events, Actions + Events = Automation).

Two evaluation mechanisms, chosen per event type by how it is actually detected:
  * native/pushed  -- OS-emitted (file change, USB, login/logout, program launch). Worker
                      clients relay the signal (`control.signal`); internal combos raise their
                      own (task.*, flow.failed, resource.violation); file.* come straight from
                      the Global File Index stream. The Engine matches them against definitions.
  * polled         -- state, not occurrence (thresholds, idle duration, scheduled time).
                      Worker clients report metrics (`control.metrics`); the Scheduler runs
                      `evaluate_polled` on an interval, Engine-side.

`condition_spec` (JSONB) shape -- an implementation-phase decision (schema 12):
    {"type": "<event type>",
     "pc_ids": [..] | null,            # null = every PC in the creator's department
     "match": {...}}                   # per type, all optional:
        file.*            path_prefix, name_suffix
        program.launched  process
        usb.*             -
        threshold.cpu     percent (>=), duration_s
        threshold.memory  percent (>=)
        system.idle       seconds (>=)
        time.scheduled    at (ISO datetime)          -- fires once
        time.recurring    at ("HH:MM"), days ([0..6]) or interval_s
        task.*            task_id

When an Event fires, each attached Action is dispatched as its own independent execution --
no ordering dependency, no output piping (v1). Task deadlines arrive here as
'task.deadline_soft' / 'task.deadline_final' signals from the Task scheduler jobs.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler
from engine.permissions import (
    int_field,
    require_account,
    require_department_scope,
    require_role,
    str_field,
)
from engine.serialize import row, rows
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

# Event type -> mechanism. Extend as types are defined; the classification follows detection.
EVENT_TYPES: dict[str, str] = {
    "file.created": "native_pushed", "file.modified": "native_pushed", "file.moved": "native_pushed",
    "file.copied": "native_pushed", "file.deleted": "native_pushed", "file.accessed": "native_pushed",
    "usb.inserted": "native_pushed", "usb.removed": "native_pushed",
    "user.login": "native_pushed", "user.logout": "native_pushed",
    "program.launched": "native_pushed", "program.exited": "native_pushed",
    "network.connected": "native_pushed", "network.disconnected": "native_pushed",
    "task.started": "native_pushed", "task.target_appeared": "native_pushed",
    "task.deadline_soft": "native_pushed", "task.deadline_final": "native_pushed",
    "flow.failed": "native_pushed", "resource.violation": "native_pushed",
    "system.idle": "polled", "threshold.cpu": "polled", "threshold.memory": "polled",
    "time.scheduled": "polled", "time.recurring": "polled",
}

FILE_OP_TO_EVENT = {"create": "file.created", "modify": "file.modified", "move": "file.moved",
                    "copy": "file.copied", "delete": "file.deleted"}

# pc_id -> latest metrics {cpu, memory, idle_s, at}
_metrics: dict[int, dict[str, Any]] = {}
# definition id -> last fired (UTC); also tracks one-shot / recurring time events
_last_fired: dict[int, datetime] = {}
# (definition id, pc_id) -> when a threshold first became true (for duration_s)
_threshold_since: dict[tuple[int, int], datetime] = {}


def reset_state() -> None:
    """Forget in-memory state (Engine start; tests). Durable state lives in the database."""
    _metrics.clear()
    _last_fired.clear()
    _threshold_since.clear()


def last_fired(definition_id: int) -> str | None:
    at = _last_fired.get(definition_id)
    return at.isoformat() if at else None


def install(engine: Engine) -> None:
    """file.* events come straight from the Global File Index stream."""

    async def on_file(event: dict[str, Any]) -> None:
        etype = FILE_OP_TO_EVENT.get(event["op"])
        if etype:
            await on_signal(engine, event["pc_id"], etype, {"path": event["path"], "name": event.get("name"),
                                                            "hash": event.get("hash")})
    engine.file_index.subscribe(on_file)


# --- matching -----------------------------------------------------------------------------------

def _pc_in_scope(spec: dict[str, Any], pc_id: int, pcs_in_dept: set[int] | None) -> bool:
    ids = spec.get("pc_ids")
    if ids:
        return pc_id in set(ids)
    return pcs_in_dept is None or pc_id in pcs_in_dept


def matches(spec: dict[str, Any], data: dict[str, Any]) -> bool:
    """Compare a definition's `match` block with a native signal's data."""
    m = spec.get("match") or {}
    path = str(data.get("path", "")).replace("\\", "/").lower()
    if "path_prefix" in m and not path.startswith(str(m["path_prefix"]).replace("\\", "/").lower().rstrip("/") + "/"):
        return False
    if "name_suffix" in m and not str(data.get("name", "")).lower().endswith(str(m["name_suffix"]).lower()):
        return False
    if "process" in m and str(data.get("process", "")).lower() != str(m["process"]).lower():
        return False
    return not ("task_id" in m and data.get("task_id") != m["task_id"])


async def _dept_pcs(engine: Engine, definition: dict[str, Any]) -> set[int] | None:
    creator = await engine.db.accounts.by_id(definition["created_by_account_id"])
    if creator is None or creator["department_id"] is None:
        return None
    return {p["id"] for p in await engine.db.accounts.pcs_in_department(creator["department_id"])}


async def on_signal(engine: Engine, pc_id: int, event_type: str, data: dict[str, Any]) -> int:
    """Entry point for native/pushed signals. Matches enabled definitions of this type, fires
    their attached Actions independently. Returns how many definitions fired."""
    if not engine.db.connected:
        return 0
    fired = 0
    for definition in await engine.db.control.event_definitions(event_type=event_type):
        spec = definition["condition_spec"]
        if not _pc_in_scope(spec, pc_id, await _dept_pcs(engine, definition)) or not matches(spec, data):
            continue
        await fire(engine, definition, pc_id, data)
        fired += 1
    return fired


async def fire(engine: Engine, definition: dict[str, Any], pc_id: int, data: dict[str, Any]) -> None:
    from engine.control import executions

    _last_fired[definition["id"]] = datetime.now(timezone.utc)
    await engine.audit.record(None, "event.fired", target_type="event", target_id=definition["id"],
                              detail={"pc_id": pc_id, "type": definition["condition_spec"].get("type"), "data": data})
    creator = await engine.db.accounts.by_id(definition["created_by_account_id"])
    payload = {"event_id": definition["id"], "type": definition["condition_spec"].get("type"), "pc_id": pc_id,
               "at": _last_fired[definition["id"]].isoformat()}
    await engine.push_to_role("admin", "event.fired", payload, department_id=creator["department_id"] if creator else None)
    await engine.push_to_role("super_user", "event.fired", payload)
    for action in await engine.db.control.actions_for_event(definition["id"]):
        # Each Action independently: a failure to dispatch one never blocks the next.
        try:
            await executions.start(engine, action, definition["id"], pc_id)
        except Exception:
            log.exception("dispatching action %s for event %s failed", action["id"], definition["id"])


# --- polled evaluation --------------------------------------------------------------------------

def _due_recurring(m: dict[str, Any], now: datetime, last: datetime | None) -> bool:
    if "interval_s" in m:
        return last is None or (now - last).total_seconds() >= float(m["interval_s"])
    at = str(m.get("at", ""))
    if ":" not in at:
        return False
    hh, mm = (int(x) for x in at.split(":", 1))
    days = m.get("days")
    if days and now.weekday() not in days:
        return False
    target = now.replace(hour=hh, minute=mm, second=0, microsecond=0)
    return now >= target and (last is None or last < target)


async def evaluate_polled(engine: Engine) -> int:
    """Scheduler job: check every enabled polled definition against current state."""
    if not engine.db.connected:
        return 0
    now = datetime.now(timezone.utc)
    fired = 0
    for definition in await engine.db.control.event_definitions(condition_type="polled"):
        spec = definition["condition_spec"]
        etype, m = spec.get("type"), spec.get("match") or {}
        last = _last_fired.get(definition["id"])
        if etype == "time.scheduled":
            try:
                at = datetime.fromisoformat(str(m.get("at")))
            except (TypeError, ValueError):
                continue
            at = at if at.tzinfo else at.replace(tzinfo=timezone.utc)
            if now >= at and last is None:
                await fire(engine, definition, 0, {"at": at.isoformat()})
                fired += 1
        elif etype == "time.recurring":
            if _due_recurring(m, now, last):
                await fire(engine, definition, 0, {"at": now.isoformat()})
                fired += 1
        elif etype in ("threshold.cpu", "threshold.memory", "system.idle"):
            scope = await _dept_pcs(engine, definition)
            for pc_id, metrics in list(_metrics.items()):
                if not _pc_in_scope(spec, pc_id, scope):
                    continue
                if etype == "system.idle":
                    hit = float(metrics.get("idle_s", 0)) >= float(m.get("seconds", 600))
                else:
                    key = "cpu" if etype == "threshold.cpu" else "memory"
                    hit = float(metrics.get(key, 0)) >= float(m.get("percent", 80))
                since_key = (definition["id"], pc_id)
                if not hit:
                    _threshold_since.pop(since_key, None)
                    continue
                since = _threshold_since.setdefault(since_key, now)
                if (now - since).total_seconds() < float(m.get("duration_s", 0)):
                    continue
                if last is not None and (now - last) < timedelta(seconds=float(m.get("cooldown_s", 300))):
                    continue
                await fire(engine, definition, pc_id, {"metrics": metrics})
                fired += 1
    return fired


# --- handlers -----------------------------------------------------------------------------------

def _parse_spec(payload: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    etype = str_field(payload, "type")
    if etype not in EVENT_TYPES:
        raise ProtocolError(ErrorCode.INVALID, f"unknown event type {etype!r}")
    pc_ids = payload.get("pc_ids")
    if pc_ids is not None and not isinstance(pc_ids, list):
        raise ProtocolError(ErrorCode.INVALID, "pc_ids must be a list or null")
    match = payload.get("match") or {}
    if not isinstance(match, dict):
        raise ProtocolError(ErrorCode.INVALID, "match must be an object")
    if etype == "time.scheduled":
        try:
            datetime.fromisoformat(str(match.get("at")))
        except (TypeError, ValueError) as exc:
            raise ProtocolError(ErrorCode.INVALID, "time.scheduled needs match.at (ISO 8601)") from exc
    if etype == "time.recurring" and "interval_s" not in match and ":" not in str(match.get("at", "")):
        raise ProtocolError(ErrorCode.INVALID, "time.recurring needs match.at ('HH:MM') or match.interval_s")
    return EVENT_TYPES[etype], {"type": etype, "pc_ids": [int(p) for p in pc_ids] if pc_ids else None, "match": match}


async def _load_event_in_scope(ctx: Context, event_id: int) -> dict[str, Any]:
    ev = await ctx.engine.db.control.event(event_id)
    if ev is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such event")
    creator = await ctx.engine.db.accounts.by_id(ev["created_by_account_id"])
    require_department_scope(ctx.identity, creator["department_id"] if creator else None)
    return ev


@handler("control.event_create")
async def event_create(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"type", "pc_ids"?, "match"?, "action_ids": [..], "enabled": bool}"""
    ident = require_role(ctx, "super_user", "admin")
    condition_type, spec = _parse_spec(payload)
    action_ids = payload.get("action_ids") or []
    if not isinstance(action_ids, list):
        raise ProtocolError(ErrorCode.INVALID, "action_ids must be a list")
    from engine.control.actions import load_action_in_scope

    for aid in action_ids:
        await load_action_in_scope(ctx, int(aid))
    if spec["pc_ids"]:
        for pc_id in spec["pc_ids"]:
            pc = await ctx.engine.db.accounts.pc(pc_id)
            if pc is None:
                raise ProtocolError(ErrorCode.NOT_FOUND, f"no such pc {pc_id}")
            require_department_scope(ident, pc["department_id"])
    db = ctx.engine.db
    event_id = await db.control.create_event(ident.account_id, condition_type, spec)
    for seq, aid in enumerate(action_ids, start=1):
        await db.control.attach_action(event_id, int(aid), seq)
    if payload.get("enabled") is False:
        await db.control.update_event(event_id, enabled=False)
    await ctx.engine.audit.record(ctx, "event.created", target_type="event_definitions", target_id=event_id,
                                  detail={"type": spec["type"], "actions": action_ids})
    return {"event": row(await db.control.event(event_id))}


@handler("control.event_update")
async def event_update(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"event_id", "enabled"?, "match"?, "pc_ids"?, "action_ids"?} -- action_ids replaces the
    attached set (display order = list order)."""
    require_role(ctx, "super_user", "admin")
    event_id = int_field(payload, "event_id")
    ev = await _load_event_in_scope(ctx, event_id)
    db = ctx.engine.db
    spec = None
    if "match" in payload or "pc_ids" in payload:
        merged = {"type": ev["condition_spec"]["type"], "match": payload.get("match", ev["condition_spec"].get("match")),
                  "pc_ids": payload.get("pc_ids", ev["condition_spec"].get("pc_ids"))}
        _, spec = _parse_spec(merged)
    enabled = payload.get("enabled")
    await db.control.update_event(event_id, condition_spec=spec, enabled=None if enabled is None else bool(enabled))
    if "action_ids" in payload:
        from engine.control.actions import load_action_in_scope

        wanted = [int(a) for a in payload["action_ids"] or []]
        for aid in wanted:
            await load_action_in_scope(ctx, aid)
        current = {a["id"] for a in ev["actions"]}
        for aid in current - set(wanted):
            await db.control.detach_action(event_id, aid)
        for seq, aid in enumerate(wanted, start=1):
            await db.control.attach_action(event_id, aid, seq)
    await ctx.engine.audit.record(ctx, "event.updated", target_type="event_definitions", target_id=event_id)
    return {"event": row(await db.control.event(event_id))}


@handler("control.event_delete")
async def event_delete(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Disables (never deletes); executions keep their reference."""
    require_role(ctx, "super_user", "admin")
    event_id = int_field(payload, "event_id")
    await _load_event_in_scope(ctx, event_id)
    await ctx.engine.db.control.update_event(event_id, enabled=False)
    await ctx.engine.audit.record(ctx, "event.disabled", target_type="event_definitions", target_id=event_id)
    return {"event_id": event_id, "enabled": False}


@handler("control.event_list")
async def event_list(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    ident = require_role(ctx, "super_user", "admin")
    db = ctx.engine.db
    defs = await db.control.event_definitions(enabled_only=False) if ident.role == "super_user" \
        else await db.control.events_in_department(ident.department_id)
    out = []
    for d in rows(defs):
        d["actions"] = rows(await db.control.actions_for_event(d["id"]))
        d["last_fired_at"] = last_fired(d["id"])
        out.append(d)
    return {"events": out, "types": EVENT_TYPES}


@handler("control.signal")
async def signal(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Worker client relays a native OS signal: {"type": "usb.inserted", "data": {...}}.
    file.* signals come through the index instead (index.event) and are refused here."""
    ident = require_account(ctx)
    etype = str_field(payload, "type")
    if EVENT_TYPES.get(etype) != "native_pushed" or etype.startswith(("file.", "task.", "flow.", "resource.")):
        raise ProtocolError(ErrorCode.INVALID, f"{etype!r} is not a relayable native signal")
    if ident.pc_id is None:
        raise ProtocolError(ErrorCode.INVALID, "no pc bound to this connection")
    fired = await on_signal(ctx.engine, ident.pc_id, etype, payload.get("data") or {})
    return {"accepted": True, "fired": fired}


@handler("control.metrics")
async def metrics(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Worker client reports state for polled events: {"cpu": %, "memory": %, "idle_s": n}."""
    ident = require_account(ctx)
    if ident.pc_id is None:
        raise ProtocolError(ErrorCode.INVALID, "no pc bound to this connection")
    _metrics[ident.pc_id] = {"cpu": float(payload.get("cpu", 0)), "memory": float(payload.get("memory", 0)),
                             "idle_s": float(payload.get("idle_s", 0)), "at": datetime.now(timezone.utc).isoformat()}
    return {"accepted": True}
