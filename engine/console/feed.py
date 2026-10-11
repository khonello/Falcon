"""The audit trail as events the console can show (Audit log, Overview's event volume and live activity, a machine's events).

An audit row is `action_type + target + detail`. The console wants an event: a **kind** to colour and filter by, one plain
**sentence**, the **machine** and the **person**. This module is the one place that turns one into the other, for the reader
(`audit.events`, `audit.summary`, `audit.export`) and for the live push (`audit.event`, sent by the audit trail itself).

Kinds: session, action, flow, assistance, rollout, deviation, violation (the concept's seven) and task, report, admin, system
for the rest of what is recorded. A kind is decided from the action type alone, so filtering by kind is a query, not a scan.
"""

from __future__ import annotations

import csv
import io
from datetime import datetime, timedelta, timezone
from typing import Any

from engine.dispatch import Context, handler
from engine.permissions import int_field, require_role
from protocol import ErrorCode, ProtocolError

# kind -> the action types (exact, or a prefix ending in ".") it covers
KIND_TYPES: dict[str, tuple[str, ...]] = {
    "session": ("session.", "assisted_access."),
    "action": ("action.", "event.", "execution."),
    "flow": ("flow.",),
    "assistance": ("assistance.",),
    "rollout": ("update.",),
    "deviation": ("deviation.",),
    "violation": ("resource.violation", "resource.violation_resolved", "mark.", "issue."),
    "task": ("task.",),
    "report": ("report.", "report_routing."),
    "admin": ("account.", "pc.", "department.", "display_name.", "enroll.", "alert.", "audit.", "rule.", "registry."),
    "system": ("auth.",),
}


def kind_of(action_type: str) -> str:
    for kind, prefixes in KIND_TYPES.items():
        for p in prefixes:
            if action_type == p or (p.endswith(".") and action_type.startswith(p)) or action_type == p.rstrip("."):
                return kind
    if action_type.startswith("resource."):
        return "violation"
    return "system"


def _like_patterns(kinds: list[str]) -> tuple[list[str], list[str]]:
    exact: list[str] = []
    like: list[str] = []
    for k in kinds:
        for p in KIND_TYPES.get(k, ()):
            (like if p.endswith(".") else exact).append(p + "%" if p.endswith(".") else p)
    return exact, like


def _words(action_type: str) -> str:
    return action_type.replace("_", " ").replace(".", " ", 1).replace(".", " ").capitalize()


def sentence(action: str, d: dict[str, Any], host: str | None, names: dict[int, str]) -> str:
    """One plain sentence for what happened. `host` is the machine it concerns, if any."""
    on = f" on {host}" if host else ""
    who = lambda key: names.get(d.get(key)) or "someone"
    if action == "session.traversed":
        return f"Entered {host or 'a machine'}" + (" (outside working hours)" if d.get("outside_hours") else "")
    if action == "session.ended":
        reason = d.get("reason")
        return {"superior_ended": f"A superior ended the session{on}", "expired": f"The session{on} timed out",
                "voluntary": f"Left {host or 'the machine'}"}.get(reason, f"Left {host or 'the machine'}")
    if action == "session.extended":
        return f"Extended the session{on}"
    if action.startswith("assisted_access."):
        return {"assisted_access.offered": f"Offered assisted access{on}", "assisted_access.accepted": f"Started assisted access{on}",
                "assisted_access.closed": f"Ended assisted access{on}", "assisted_access.availability": "Changed whether they can be asked for help",
                "assisted_access.no_match": "Asked for assisted access; nobody was available"}.get(action, _words(action))
    if action == "action.started":
        return f"Action {d.get('action_id', '')} started{on}".replace("  ", " ")
    if action == "action.finished":
        return f"An action finished{on}: {d.get('status', 'done')}"
    if action == "action.terminate_requested":
        return f"Asked to stop a running action{on}"
    if action == "action.timeout_unreported":
        return f"An action never reported back{on}"
    if action == "action.not_run":
        return f"An action did not run{on}: {d.get('why', '')}".rstrip(": ")
    if action == "event.fired":
        return f"A rule fired{on}: {d.get('type', 'an event')}"
    if action == "execution.image_viewed":
        return f"Looked at a screenshot{on}"
    if action.startswith("flow."):
        return {"flow.synced": f"Flow {d.get('flow_id', '')} carried files{on}".replace("  ", " "), "flow.failed": f"A flow failed{on}",
                "flow.conflict": f"A flow met an outside edit{on}", "flow.created": "Created a flow", "flow.edited": "Edited a flow",
                "flow.deleted": "Removed a flow", "flow.paused": "Paused a flow", "flow.resumed": "Resumed a flow",
                "flow.consent": "Answered a flow's request"}.get(action, _words(action))
    if action == "assistance.ping":
        return f"Pinged {who('to_account_id')}"
    if action == "assistance.message":
        return "Sent a message in a conversation"
    if action == "assistance.channel_opened":
        return "Opened a conversation"
    if action == "assistance.channel_closed":
        return "Closed a conversation"
    if action == "assistance.listener_added":
        return "Added a listener to a conversation"
    if action == "update.approved":
        return f"Approved version {d.get('version', '')}".strip()
    if action == "update.attempt":
        return f"Install of {d.get('version', 'an update')} {'succeeded' if d.get('succeeded') else 'failed'}{on}"
    if action == "update.rollout":
        return "Started the rollout in a department"
    if action == "update.prompt":
        return "Asked a department's Admins to move on the rollout"
    if action == "resource.violation":
        return f"Copy of restricted {d.get('path', 'file')} found{on}"
    if action == "resource.violation_resolved":
        return f"A restricted copy was put right{on}"
    if action == "resource.tagged":
        return f"Marked a file as {d.get('tag', 'restricted')}{on}"
    if action == "deviation.logged":
        return f"{_words(str(d.get('kind', 'deviation')))}{on}"
    if action == "report.addressed":
        return "Marked a report addressed"
    if action == "report_routing.set":
        return f"Changed where {d.get('category', 'a kind of report')} goes"
    if action.startswith("task."):
        return {"task.created": "Gave a task", "task.started": "Started a task", "task.verified": "Verified a task",
                "task.dept_created": "Gave a department a task", "task.dept_marked": f"Marked a department task {d.get('state', '')}".strip(),
                "task.dept_completed": "Completed a department task", "task.dept_reopened": "Sent a department task back",
                "task.dept_deadline": "A department task reached its deadline"}.get(action, _words(action))
    if action == "account.created":
        return f"Created a {d.get('role', 'new')} account"
    if action == "account.offboarded":
        return "Offboarded an account"
    if action in ("pc.registered", "pc.rekeyed"):
        return "Registered a machine" if action == "pc.registered" else f"Made a new key for a machine{on}"
    if action == "department.created":
        return "Created a department"
    if action == "auth.connected":
        return f"Connected{on}"
    if action == "auth.disconnected":
        return f"Disconnected{on}"
    if action == "auth.failed":
        return f"Refused a connection that had no valid key ({d.get('reason', '')})"
    if action.startswith("enroll."):
        return {"enroll.requested": f"{d.get('hostname', 'A machine')} asked to be registered",
                "enroll.confirmed": f"Registered {d.get('hostname', 'a machine')}", "enroll.refused": f"Refused to register {d.get('hostname', 'a machine')}",
                "enroll.collected": f"{d.get('hostname', 'A machine')} collected its key"}.get(action, _words(action))
    return _words(action)


_ACCOUNT_KEYS = ("to_account_id", "account_id", "by_account_id", "target_account_id", "admin_id")


async def describe_many(db: Any, entries: list[dict[str, Any]], viewer_account_id: int) -> list[dict[str, Any]]:
    """Each audit row as an event, named for the viewer."""
    pc_ids = sorted({e["pc_id"] for e in entries if e.get("pc_id")})
    hosts: dict[int, str] = {}
    for pc_id in pc_ids:
        pc = await db.accounts.pc(pc_id)
        if pc:
            hosts[pc_id] = pc["hostname"]
    people = {e["actor_account_id"] for e in entries if e.get("actor_account_id")}
    for e in entries:
        for k in _ACCOUNT_KEYS:
            if isinstance((e.get("detail") or {}).get(k), int):
                people.add(e["detail"][k])
    names = await db.accounts.display_names_for(viewer_account_id, sorted(people)) if people else {}
    out = []
    for e in entries:
        d = e.get("detail") or {}
        host = hosts.get(e.get("pc_id")) if e.get("pc_id") else None
        actor = names.get(e["actor_account_id"]) if e.get("actor_account_id") else (
            "Automation" if e["action_type"] in ("action.started", "action.finished", "event.fired") else "System")
        at = e.get("occurred_at") or e.get("at")
        out.append({"id": e.get("id"), "at": at.isoformat() if isinstance(at, datetime) else at, "kind": kind_of(e["action_type"]),
                    "action_type": e["action_type"], "actor": actor, "actor_account_id": e.get("actor_account_id"),
                    "what": sentence(e["action_type"], d, host, names), "pc_id": e.get("pc_id"), "host": host})
    return out


async def describe(db: Any, entry: dict[str, Any], viewer_account_id: int | None = None) -> dict[str, Any]:
    """One live entry (as `AuditTrail.record` builds it) as an event; names are neutral unless a viewer is given."""
    e = {**entry, "action_type": entry.get("action_type") or entry["action"]}
    return (await describe_many(db, [e], viewer_account_id or 0))[0]


def _scope(ident: Any, payload: dict[str, Any]) -> int | None:
    """The department a reader is limited to: an Admin's own, or the one a Super User asks for (None: all)."""
    if ident.role == "admin":
        return ident.department_id
    return int_field(payload, "department_id", required=False)


def _window(payload: dict[str, Any]) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)

    def parse(name: str, default: datetime) -> datetime:
        raw = payload.get(name)
        if not raw:
            return default
        try:
            when = datetime.fromisoformat(str(raw))
        except ValueError as exc:
            raise ProtocolError(ErrorCode.INVALID, f"{name} must be ISO 8601") from exc
        return when if when.tzinfo else when.replace(tzinfo=timezone.utc)

    return parse("since", now - timedelta(days=7)), parse("until", now + timedelta(minutes=1))


def _kinds(payload: dict[str, Any]) -> list[str] | None:
    kinds = payload.get("kinds")
    if kinds is None:
        return None
    if not isinstance(kinds, list) or not all(isinstance(k, str) for k in kinds):
        raise ProtocolError(ErrorCode.INVALID, "kinds must be a list of names")
    if unknown := sorted(set(kinds) - set(KIND_TYPES)):
        raise ProtocolError(ErrorCode.INVALID, f"unknown kinds {unknown}; known: {sorted(KIND_TYPES)}")
    return kinds


@handler("audit.events")
async def events(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"since"?, "until"?, "kinds"?:[..], "pc_id"?, "department_id"? (Super User), "actor_account_id"?, "before_id"?,
    "limit"? (500 at most)} -> {"events": [{id, at, kind, actor, what, pc_id, host}], "more": bool}, newest first. An Admin sees
    the events that concern their own department's machines or were made by their own people."""
    ident = require_role(ctx, "super_user", "admin")
    since, until = _window(payload)
    limit = min(int_field(payload, "limit", required=False) or 100, 500)
    found = await ctx.engine.db.audit.feed(
        since=since, until=until, kinds=_kinds(payload), pc_id=int_field(payload, "pc_id", required=False),
        department_id=_scope(ident, payload), actor_account_id=int_field(payload, "actor_account_id", required=False),
        before_id=int_field(payload, "before_id", required=False), limit=limit + 1)
    more = len(found) > limit
    return {"events": await describe_many(ctx.engine.db, found[:limit], ident.account_id), "more": more}


@handler("audit.summary")
async def summary(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"since"?, "until"?, "bucket_minutes"? (default 60), "pc_id"?, "department_id"?} -> {total, actors, violations, by_kind,
    series: [{at, counts: {kind: n}}], kept_days}. What Overview's event volume and the Audit log's *Events over time* draw."""
    ident = require_role(ctx, "super_user", "admin")
    since, until = _window(payload)
    bucket = max(1, min(int_field(payload, "bucket_minutes", required=False) or 60, 24 * 60))
    dept = _scope(ident, payload)
    pc_id = int_field(payload, "pc_id", required=False)
    db = ctx.engine.db.audit
    rows_ = await db.counts(since=since, until=until, bucket_minutes=bucket, pc_id=pc_id, department_id=dept)
    by_kind: dict[str, int] = {}
    series: dict[str, dict[str, int]] = {}
    for r in rows_:
        kind = kind_of(r["action_type"])
        by_kind[kind] = by_kind.get(kind, 0) + r["n"]
        s = series.setdefault(r["bucket"].isoformat(), {})
        s[kind] = s.get(kind, 0) + r["n"]
    return {"total": sum(by_kind.values()), "actors": await db.distinct_actors(since=since, until=until, pc_id=pc_id, department_id=dept),
            "violations": by_kind.get("violation", 0), "by_kind": by_kind,
            "series": [{"at": at, "counts": c} for at, c in sorted(series.items())],
            "kept_days": ctx.engine.settings.audit_retention_days}


@handler("audit.export")
async def export(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """The same filters as audit.events -> {"filename", "csv", "rows"}: when, kind, who, what, machine. At most 20,000 rows.
    Exporting is itself recorded."""
    ident = require_role(ctx, "super_user", "admin")
    since, until = _window(payload)
    found = await ctx.engine.db.audit.feed(
        since=since, until=until, kinds=_kinds(payload), pc_id=int_field(payload, "pc_id", required=False),
        department_id=_scope(ident, payload), actor_account_id=int_field(payload, "actor_account_id", required=False),
        before_id=None, limit=20000)
    items = await describe_many(ctx.engine.db, found, ident.account_id)
    buf = io.StringIO()
    w = csv.writer(buf)
    w.writerow(["when", "kind", "who", "what", "machine"])
    for e in items:
        w.writerow([e["at"], e["kind"], e["actor"], e["what"], e["host"] or ""])
    await ctx.engine.audit.record(ctx, "audit.exported", detail={"rows": len(items), "since": since.isoformat(), "until": until.isoformat()})
    return {"filename": f"falcon-audit-{since:%Y%m%d}-{until:%Y%m%d}.csv", "csv": buf.getvalue(), "rows": len(items)}
