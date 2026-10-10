"""Action library (Control -> Action, Control, Monitoring, Custom Actions).

An Action is atomic: Control (do something) or Monitoring (observe something), each with its
own timeout and manual termination, independent of any other Action in the same Event chain.
Custom is a distinct third category (Admin-authored scripts), never merged into the other two.

This combo lives at the Admin interface. Super User reaches it by traversing into an Admin's
view, so Super User may *read* and run built-ins here, but cannot author Custom Actions.

`timing`: {"mode": "immediate"} (default) or {"mode": "delayed", "delay_s": N}. Scheduled and
recurring execution belong to time Events, not to the Action.
"""

from __future__ import annotations

from typing import Any

from engine.control import custom_actions
from engine.dispatch import Context, handler
from engine.permissions import int_field, require_department_scope, require_role, str_field
from engine.serialize import row, rows
from protocol import ErrorCode, ProtocolError

CATEGORIES = ("control", "monitoring", "custom")
STATUSES = ("pending", "success", "failed", "terminated")
SCRIPT_LANGUAGES = ("powershell", "python")

# Built-in actions: what the worker client knows how to execute, with the parameters each takes.
BUILTIN: dict[str, dict[str, Any]] = {
    # control
    "screenshot": {"category": "control", "params": []},
    "notify": {"category": "control", "params": ["message"], "optional": ["stay_s"]},
    "lock_session": {"category": "control", "params": ["duration_s"], "optional": ["message"]},
    "rename_file": {"category": "control", "params": ["new_name"], "optional": ["path", "find_name", "find_hash"]},
    "restore_file": {"category": "control", "params": [], "optional": ["path", "find_name", "find_hash"]},
    "kill_process": {"category": "control", "params": ["name"]},
    "start_process": {"category": "control", "params": ["command"]},
    "shutdown": {"category": "control", "params": [], "optional": ["delay_s", "message"]},
    "reboot": {"category": "control", "params": [], "optional": ["delay_s", "message"]},
    # monitoring
    "process_list": {"category": "monitoring", "params": []},
    "system_metrics": {"category": "monitoring", "params": []},
    "file_activity": {"category": "monitoring", "params": ["path"]},
    "idle_time": {"category": "monitoring", "params": []},
    "snapshot_file": {"category": "monitoring", "params": [], "optional": ["path", "find_name", "find_hash"]},
    "usb_contents": {"category": "monitoring", "params": []},
}


# Settings the design asks for (Actions, AU06). notify: `message`, and `stay_s` (seconds it stays up; absent or 0 =
# until the person closes it). lock_session: `duration_s` (how long the screen stays locked) and an optional
# `message`. reboot/shutdown: `delay_s` (the warning before it happens: 60 or 300 as offered; any 0-3600) and a
# `message`.
# Actions that work on one file name it one of three ways: `path` (the same path on every machine), `find_name` (a file
# name) or `find_hash` (a content hash). The last two are looked up in the file index for each machine the action runs
# on, so every machine gets its own path (executions.resolve_file).
FILE_ACTIONS = frozenset({"rename_file", "restore_file", "snapshot_file"})
LOCATORS = ("path", "find_name", "find_hash")
DELAY_MAX = 3600
SETTLE_SECONDS = 30      # a run needs this much beyond a lock's or message's own length to finish and report


def check_params(builtin_type: str, params: dict[str, Any]) -> dict[str, Any]:
    """The built-in's settings, checked and cleaned (whole numbers, short text). Raises INVALID."""
    spec = BUILTIN[builtin_type]
    known = set(spec["params"]) | set(spec.get("optional", []))
    if unknown := sorted(set(params) - known):
        raise ProtocolError(ErrorCode.INVALID, f"{builtin_type} takes {sorted(known) or 'no settings'}, not {unknown}")
    out = dict(params)
    if builtin_type in FILE_ACTIONS:
        given = [k for k in LOCATORS if str(out.get(k) or "").strip()]
        if len(given) != 1:
            raise ProtocolError(ErrorCode.INVALID, f"{builtin_type} needs exactly one of path, find_name, find_hash")
        out = {k: v for k, v in out.items() if k not in LOCATORS or k == given[0]}
    for key in ("duration_s", "stay_s", "delay_s"):
        if key in out:
            try:
                out[key] = int(out[key])
            except (TypeError, ValueError) as exc:
                raise ProtocolError(ErrorCode.INVALID, f"{key} must be a whole number of seconds") from exc
    if "duration_s" in out and out["duration_s"] <= 0:
        raise ProtocolError(ErrorCode.INVALID, "duration_s must be positive")
    if "stay_s" in out and out["stay_s"] < 0:
        raise ProtocolError(ErrorCode.INVALID, "stay_s must be 0 (until closed) or more")
    if "delay_s" in out and not 0 <= out["delay_s"] <= DELAY_MAX:
        raise ProtocolError(ErrorCode.INVALID, f"delay_s must be between 0 and {DELAY_MAX}")
    if "message" in out:
        out["message"] = str(out["message"]).strip()[:500]
        if builtin_type == "notify" and not out["message"]:
            raise ProtocolError(ErrorCode.INVALID, "message must not be empty")
    return out


def run_length(params: dict[str, Any]) -> int:
    """How long a run lasts by its own settings (a lock, a message that stays up, a restart's warning)."""
    return max(int(params.get("duration_s") or 0), int(params.get("stay_s") or 0), int(params.get("delay_s") or 0))


def parse_timing(raw: Any) -> dict[str, Any]:
    if raw in (None, {}):
        return {"mode": "immediate"}
    if not isinstance(raw, dict) or raw.get("mode") not in ("immediate", "delayed"):
        raise ProtocolError(ErrorCode.INVALID, "timing.mode must be immediate or delayed")
    if raw["mode"] == "delayed":
        try:
            delay = int(raw.get("delay_s", 0))
        except (TypeError, ValueError) as exc:
            raise ProtocolError(ErrorCode.INVALID, "timing.delay_s must be an integer") from exc
        if delay <= 0:
            raise ProtocolError(ErrorCode.INVALID, "timing.delay_s must be positive")
        return {"mode": "delayed", "delay_s": delay}
    return {"mode": "immediate"}


async def load_action_in_scope(ctx: Context, action_id: int) -> dict[str, Any]:
    action = await ctx.engine.db.control.action(action_id)
    if action is None or action.get("archived_at"):
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such action")
    creator = await ctx.engine.db.accounts.by_id(action["created_by_account_id"])
    require_department_scope(ctx.identity, creator["department_id"] if creator else None)
    return action


@handler("control.action_list")
async def action_list(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Library: built-in types plus the department's stored actions, grouped by category."""
    ident = require_role(ctx, "super_user", "admin")
    db = ctx.engine.db
    stored = await db.control.actions() if ident.role == "super_user" else await db.control.actions_in_department(
        ident.department_id)
    grouped: dict[str, list[dict[str, Any]]] = {"control": [], "monitoring": [], "custom": []}
    for a in rows(stored):
        grouped[a["action_kind"]].append(a)
    return {"builtin": BUILTIN, "actions": grouped}


@handler("control.action_create")
async def action_create(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Built-in: {"kind": "control"|"monitoring", "builtin_type", "params"?, "timeout_s", "name"?,
    "timing"?}. Custom (Admin only): {"kind": "custom", "name", "language", "script",
    "timeout_s", "description"?, "timing"?} -- validated against stdlib + Windows-native."""
    ident = require_role(ctx, "super_user", "admin")
    kind = str_field(payload, "kind", choices=CATEGORIES)
    timeout_s = int_field(payload, "timeout_s")
    if timeout_s <= 0:
        raise ProtocolError(ErrorCode.INVALID, "timeout_s must be positive -- every Action has a timeout")
    timing = parse_timing(payload.get("timing"))
    name = str_field(payload, "name", required=kind == "custom")
    db = ctx.engine.db
    if kind == "custom":
        if ident.role != "admin":
            raise ProtocolError(ErrorCode.FORBIDDEN, "Custom Actions are authored by Admins only")
        language = str_field(payload, "language", choices=SCRIPT_LANGUAGES)
        script = str_field(payload, "script")
        result = custom_actions.validate(language, script)
        if not result.ok:
            raise ProtocolError(ErrorCode.INVALID, "script rejected: " + "; ".join(result.problems))
        action_id = await db.control.create_action(
            ident.account_id, "custom", timeout_s, custom_script=script, custom_script_language=language,
            name=name, description=payload.get("description"), timing=timing)
    else:
        builtin_type = str_field(payload, "builtin_type")
        spec = BUILTIN.get(builtin_type)
        if spec is None or spec["category"] != kind:
            raise ProtocolError(ErrorCode.INVALID, f"unknown {kind} builtin {builtin_type!r}")
        params = payload.get("params") or {}
        if not isinstance(params, dict):
            raise ProtocolError(ErrorCode.INVALID, "params must be an object")
        missing = [p for p in spec["params"] if p not in params]
        if missing:
            raise ProtocolError(ErrorCode.INVALID, f"missing params: {', '.join(missing)}")
        params = check_params(builtin_type, params)
        timeout_s = max(timeout_s, run_length(params) + SETTLE_SECONDS)     # never cut a lock short
        action_id = await db.control.create_action(
            ident.account_id, kind, timeout_s, builtin_type=builtin_type, name=name or builtin_type,
            description=payload.get("description"), params=params, timing=timing)
    await ctx.engine.audit.record(ctx, "action.created", target_type="actions", target_id=action_id,
                                  detail={"kind": kind, "name": name})
    return {"action": row(await db.control.action(action_id))}


@handler("control.action_update")
async def action_update(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"action_id", "timeout_s"?, "name"?, "description"?, "params"?, "timing"?, "script"?}"""
    ident = require_role(ctx, "super_user", "admin")
    action_id = int_field(payload, "action_id")
    action = await load_action_in_scope(ctx, action_id)
    script = payload.get("script")
    if script is not None:
        if action["action_kind"] != "custom" or ident.role != "admin":
            raise ProtocolError(ErrorCode.FORBIDDEN, "only an Admin edits a Custom Action's script")
        result = custom_actions.validate(action["custom_script_language"], str(script))
        if not result.ok:
            raise ProtocolError(ErrorCode.INVALID, "script rejected: " + "; ".join(result.problems))
    timeout_s = int_field(payload, "timeout_s", required=False)
    if timeout_s is not None and timeout_s <= 0:
        raise ProtocolError(ErrorCode.INVALID, "timeout_s must be positive")
    params = payload.get("params")
    if params is not None and action["action_kind"] != "custom":
        if not isinstance(params, dict):
            raise ProtocolError(ErrorCode.INVALID, "params must be an object")
        params = check_params(action["builtin_type"], params)
        timeout_s = max(timeout_s or action["timeout_seconds"], run_length(params) + SETTLE_SECONDS)
    await ctx.engine.db.control.update_action(
        action_id, timeout_seconds=timeout_s, custom_script=str(script) if script is not None else None,
        name=payload.get("name"), description=payload.get("description"), params=params,
        timing=parse_timing(payload["timing"]) if "timing" in payload else None)
    await ctx.engine.audit.record(ctx, "action.updated", target_type="actions", target_id=action_id)
    return {"action": row(await ctx.engine.db.control.action(action_id))}


@handler("control.action_delete")
async def action_delete(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Archives (never deletes) -- past executions keep their reference."""
    require_role(ctx, "super_user", "admin")
    action_id = int_field(payload, "action_id")
    await load_action_in_scope(ctx, action_id)
    await ctx.engine.db.control.archive_action(action_id)
    await ctx.engine.audit.record(ctx, "action.archived", target_type="actions", target_id=action_id)
    return {"action_id": action_id, "archived": True}


@handler("control.action_run")
async def action_run(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Run an Action now, outside any Event. {"action_id", "pc_id"} for one PC, or
    {"action_id", "department_id"} for every PC in a department (a department-wide policy
    update, Hierarchy scenario 2) -- each PC is its own independent execution."""
    ident = require_role(ctx, "super_user", "admin")
    action_id = int_field(payload, "action_id")
    action = await load_action_in_scope(ctx, action_id)
    db = ctx.engine.db
    pc_id = int_field(payload, "pc_id", required=False)
    department_id = int_field(payload, "department_id", required=False)
    if pc_id is None and department_id is None:
        raise ProtocolError(ErrorCode.INVALID, "pc_id or department_id required")
    if pc_id is not None:
        pc = await db.accounts.pc(pc_id)
        if pc is None:
            raise ProtocolError(ErrorCode.NOT_FOUND, "no such pc")
        require_department_scope(ident, pc["department_id"])
        targets = [pc]
    else:
        require_department_scope(ident, department_id)
        targets = await db.accounts.pcs_in_department(department_id)
    from engine.control import executions

    executions_started = []
    for pc in targets:
        execution_id = await executions.start(ctx.engine, action, None, pc["id"], actor=ctx)
        executions_started.append({"pc_id": pc["id"], "hostname": pc["hostname"], "execution_id": execution_id})
    await ctx.engine.audit.record(ctx, "action.run", target_type="actions", target_id=action_id,
                                  detail={"pcs": [e["pc_id"] for e in executions_started], "department_id": department_id})
    return {"execution_id": executions_started[0]["execution_id"] if len(executions_started) == 1 else None,
            "executions": executions_started}
