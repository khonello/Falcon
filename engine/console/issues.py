"""Issues: the tickets an Admin works (Issues page, Overview's open issues, a machine's health, a department's worst).

An issue is raised from something the system already records and resolved when its cause goes away -- or when a person acts on it:

    file       a copy of a restricted file where it is not allowed       (resource violation)
    update     an update that failed, and one past the escalation limit  (update attempts)
    deviation  a machine that presented another name                      (the deviation log)
    flow       a flow waiting for someone to agree                        (flow consent)
    offline    a machine that stopped checking in                         (connections)

A help request is not an issue: it is a ping, and lives in Messages.

    issues.list    {department_id?, pc_id?, type?, owner?: "me"|"unassigned"|<account_id>}   -> issues + the strip's figures
    issues.get     {issue_id}                                  -> the issue, what it means, its facts, what can be done, its timeline
    issues.act     {issue_id, key, reason?, message?, pick?}   -> do one of the things `issues.get` offered
    issues.assign  {issue_id, account_id?}                     -> take it (no account: yourself), give it, or hand it back (null)
    issues.escalate{issue_id, note?}                           -> an Admin sends it up to the Super User
    issues.note    {issue_id, text}                            -> add a line to its timeline

Scope: the Super User sees every issue; an Admin their own department's. Owner: the one person named when it is raised (a
file's marker, a flow's destination owner), else the department's only Admin, else nobody -- unassigned, any Admin of the
department may take it. A department with no Admin escalates to the Super User, who then owns it.

Severity of a file copy: **critical** when it left the original's department, **high** when it is on another machine in the same
department (or an unmarked restricted file), **medium** when it is another place on the same machine.
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import TYPE_CHECKING, Any

from engine.console.feed import describe_many
from engine.dispatch import Context, handler
from engine.permissions import int_field, require_department_scope, require_role, str_field
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

TARGET_HOURS = {"file": 1, "update": 24, "deviation": 8, "flow": 72, "offline": 72, "component": 24}
TYPE_LABEL = {"file": "Restricted file", "update": "Stuck update", "deviation": "Deviation", "flow": "Flow blocked", "offline": "Not checking in", "component": "Part of the Worker"}
SEVERITIES = ("critical", "high", "medium", "low")
OFFLINE_AFTER = timedelta(minutes=20)           # a machine quiet for this long raises an issue
OFFLINE_MEDIUM_AFTER = timedelta(hours=24)


# --- raising and resolving (called by the combos that record the causes) --------------------------

async def _default_owner(engine: Engine, department_id: int | None) -> tuple[int | None, bool]:
    """(owner, escalated): the department's only Admin owns it; with several it is unassigned; with none it goes to the Super User."""
    if department_id is None:
        return None, True
    admins = [a for a in await engine.db.accounts.active_admins() if a["department_id"] == department_id]
    if len(admins) == 1:
        return admins[0]["id"], False
    return None, not admins


async def raise_issue(engine: Engine, *, type_: str, severity: str, title: str, subject: str = "", pc_id: int | None = None,
                      source_table: str | None = None, source_id: int | None = None, detail: dict[str, Any] | None = None,
                      owner_account_id: int | None = None, state: str = "open", label: str | None = None,
                      department_id: int | None = None) -> tuple[int, bool]:
    """Raise an issue (once per cause). Returns (id, created). Tells the people who should hear of it, as it happens."""
    db = engine.db
    if department_id is None and pc_id is not None:
        pc = await db.accounts.pc(pc_id)
        department_id = pc["department_id"] if pc else None
    owner, escalated = (owner_account_id, False) if owner_account_id is not None else await _default_owner(engine, department_id)
    issue_id, created = await db.issues.raise_({
        "type": type_, "severity": severity, "title": title, "subject": subject, "pc_id": pc_id, "department_id": department_id,
        "owner_account_id": owner, "target_hours": TARGET_HOURS[type_], "state": state, "label": label or ("Escalated" if escalated else None),
        "detail": detail or {}, "source_table": source_table, "source_id": source_id,
        "escalated_at": datetime.now(timezone.utc) if escalated else None})
    if not created:
        return issue_id, False
    await db.issues.log(issue_id, "raised", f"{title}" + (f": {subject}" if subject else ""))
    issue = await db.issues.get(issue_id)
    assert issue is not None
    await engine.audit.record(None, "issue.raised", target_type="issues", target_id=issue_id, pc_id=pc_id,
                              detail={"code": issue["code"], "type": type_, "severity": severity, "title": title, "department_id": department_id})
    payload = {"issue_id": issue_id, "code": issue["code"], "type": type_, "severity": severity, "title": title, "subject": subject,
               "pc_id": pc_id, "department_id": department_id}
    await engine.push_to_role("super_user", "issue.raised", payload)
    if department_id is not None:
        await engine.push_to_role("admin", "issue.raised", payload, department_id=department_id)
    return issue_id, True


async def resolve_issue(engine: Engine, issue_id: int, resolution: str, *, by: Context | None = None, label: str | None = None) -> bool:
    """Resolve an issue (a person acted, or its cause went away). False when it was already resolved."""
    db = engine.db
    actor = ((by.viewed_by or by.identity).account_id if by else None)
    if not await db.issues.resolve(issue_id, resolution, actor):
        return False
    await db.issues.log(issue_id, "resolved", resolution, actor)
    issue = await db.issues.get(issue_id)
    assert issue is not None
    if issue["type"] == "file" and issue["detail"].get("violation_id"):
        await db.resource.resolve(issue["detail"]["violation_id"])       # the violation closes with its issue
    await engine.audit.record(by, "issue.resolved", target_type="issues", target_id=issue_id, pc_id=issue["pc_id"],
                              detail={"code": issue["code"], "resolution": resolution, "department_id": issue["department_id"]})
    payload = {"issue_id": issue_id, "code": issue["code"], "resolution": resolution, "department_id": issue["department_id"]}
    await engine.push_to_role("super_user", "issue.resolved", payload)
    if issue["department_id"] is not None:
        await engine.push_to_role("admin", "issue.resolved", payload, department_id=issue["department_id"])
    return True


async def resolve_source(engine: Engine, source_table: str, source_id: int, resolution: str, *, by: Context | None = None) -> bool:
    """Resolve the open issue a cause raised, if there is one."""
    if not engine.db.connected:
        return False
    issue = await engine.db.issues.by_source(source_table, source_id)
    return await resolve_issue(engine, issue["id"], resolution, by=by) if issue else False


# --- reading ------------------------------------------------------------------------------------

def _iso(value: Any) -> str | None:
    return value.isoformat() if value is not None else None


async def _view(ctx: Context, found: list[dict[str, Any]]) -> list[dict[str, Any]]:
    ident = ctx.identity
    names = await ctx.engine.db.accounts.display_names_for(
        ident.account_id, sorted({i["owner_account_id"] for i in found if i["owner_account_id"]})) if found else {}
    now = datetime.now(timezone.utc)
    out = []
    for i in found:
        age = ((i["resolved_at"] or now) - i["opened_at"]).total_seconds() / 3600
        out.append({
            "id": i["id"], "code": i["code"], "type": i["type"], "type_label": TYPE_LABEL[i["type"]], "severity": i["severity"],
            "title": i["title"], "subject": i["subject"], "pc_id": i["pc_id"], "host": i["hostname"],
            "department_id": i["department_id"], "department_name": i["department_name"], "opened_at": _iso(i["opened_at"]),
            "age_hours": round(age, 2), "target_hours": i["target_hours"],
            "past_target": i["state"] != "resolved" and age > i["target_hours"],
            "owner": {"account_id": i["owner_account_id"], "name": names.get(i["owner_account_id"]),
                      "you": i["owner_account_id"] == ident.account_id} if i["owner_account_id"] else None,
            "state": i["state"], "label": i["label"] or {"open": "Open", "waiting": "Waiting", "resolved": "Resolved"}[i["state"]],
            "escalated": i["escalated_at"] is not None, "resolved_at": _iso(i["resolved_at"]), "resolution": i["resolution"]})
    return out


def _is_mine(i: dict[str, Any], ident: Any) -> bool:
    """Waiting on this person: theirs, or nobody's in their department (an Admin); the Super User's: escalated to them."""
    if i["state"] == "resolved":
        return False
    if ident.role == "super_user":
        return i["owner"] is None and i["escalated"] or bool(i["owner"] and i["owner"]["you"])
    return bool(i["owner"] and i["owner"]["you"]) or (i["owner"] is None and not i["escalated"])


@handler("issues.list")
async def issues_list(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"department_id"? (Super User), "pc_id"?, "type"?, "owner"?: "me"|"unassigned"|<account_id>} -> {"issues": [...], "summary": {...}}.
    Open and waiting issues, worst first, and those resolved today (so *Done today* can be shown). summary: open, waiting,
    past_target, done_today, mine (waiting on this person), by_type, by_severity."""
    ident = require_role(ctx, "super_user", "admin")
    db = ctx.engine.db
    department = ident.department_id if ident.role == "admin" else int_field(payload, "department_id", required=False)
    type_ = str_field(payload, "type", required=False, choices=tuple(TYPE_LABEL))
    owner = payload.get("owner")
    owner_id = ident.account_id if owner == "me" else (int(owner) if isinstance(owner, int) else None)
    midnight = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    found = await _view(ctx, await db.issues.list(department_id=department, pc_id=int_field(payload, "pc_id", required=False),
                                                  type_=type_, owner_account_id=owner_id, include_resolved_since=midnight))
    if owner == "unassigned":
        found = [i for i in found if i["owner"] is None]
    live = [i for i in found if i["state"] != "resolved"]
    by_type: dict[str, int] = {}
    by_sev: dict[str, int] = {}
    for i in live:
        by_type[i["type"]] = by_type.get(i["type"], 0) + 1
        by_sev[i["severity"]] = by_sev.get(i["severity"], 0) + 1
    return {"issues": found, "summary": {
        "open": sum(1 for i in live if i["state"] == "open"), "waiting": sum(1 for i in live if i["state"] == "waiting"),
        "past_target": sum(1 for i in live if i["past_target"]), "done_today": len(found) - len(live),
        "mine": sum(1 for i in found if _is_mine(i, ident)), "by_type": by_type, "by_severity": by_sev}}


async def _load(ctx: Context, issue_id: int) -> dict[str, Any]:
    ident = require_role(ctx, "super_user", "admin")
    issue = await ctx.engine.db.issues.get(issue_id)
    if issue is None:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such issue")
    if ident.role == "admin" and issue["department_id"] != ident.department_id:
        raise ProtocolError(ErrorCode.NOT_FOUND, "no such issue")
    return issue


async def _timeline(ctx: Context, issue: dict[str, Any]) -> list[dict[str, Any]]:
    """What was recorded about the issue, and what the audit trail shows on its machine around it."""
    db = ctx.engine.db
    ident = ctx.identity
    entries = await db.issues.entries(issue["id"])
    names = await db.accounts.display_names_for(ident.account_id, sorted({e["actor_account_id"] for e in entries if e["actor_account_id"]})) if entries else {}
    out = [{"at": _iso(e["at"]), "who": (names.get(e["actor_account_id"]) if e["actor_account_id"] else "System"),
            "what": e["text"], "kind": e["kind"], "you": e["actor_account_id"] == ident.account_id} for e in entries]
    if issue["pc_id"] is not None:
        since = issue["opened_at"] - timedelta(hours=2)
        until = (issue["resolved_at"] or datetime.now(timezone.utc)) + timedelta(minutes=1)
        around = await db.audit.feed(since=since, until=until, kinds=None, pc_id=issue["pc_id"], department_id=None,
                                     actor_account_id=None, before_id=None, limit=8)
        for e in await describe_many(db, around, ident.account_id):
            if e["action_type"].startswith("issue."):
                continue
            out.append({"at": e["at"], "who": e["actor"], "what": e["what"], "kind": e["kind"], "you": False})
    return sorted(out, key=lambda e: e["at"])


@handler("issues.get")
async def issues_get(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"issue_id"} -> {"issue", "lead", "facts": [[label, value]], "options": [...], "why": [...], "timeline": [...]}.
    `options` is what the person can do about it now, each {key, title, desc, verb, done, need?: reason|message|pick, pick?, hint?}."""
    issue = await _load(ctx, int_field(payload, "issue_id"))
    from engine.console.plays import build

    view = (await _view(ctx, [issue]))[0]
    lead, facts, options, why = await build(ctx, issue)
    if issue["state"] == "resolved":
        options = []
    return {"issue": view, "detail": issue["detail"], "lead": lead, "facts": facts, "options": options, "why": why,
            "timeline": await _timeline(ctx, issue)}


@handler("issues.act")
async def issues_act(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"issue_id", "key", "reason"?, "message"?, "pick"?} -- one of the options `issues.get` offered. Resolves the issue, or sets it
    waiting, as that option says; every act is recorded in its timeline and in the audit trail."""
    issue = await _load(ctx, int_field(payload, "issue_id"))
    if issue["state"] == "resolved":
        raise ProtocolError(ErrorCode.CONFLICT, "this issue is already resolved")
    from engine.console.plays import act

    result = await act(ctx, issue, str_field(payload, "key"), payload)
    fresh = await ctx.engine.db.issues.get(issue["id"])
    assert fresh is not None
    await ctx.engine.audit.record(ctx, "issue.acted", target_type="issues", target_id=issue["id"], pc_id=issue["pc_id"],
                                  detail={"code": issue["code"], "key": payload["key"], "department_id": issue["department_id"]})
    return {"issue": (await _view(ctx, [fresh]))[0], "done": result}


@handler("issues.assign")
async def issues_assign(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """{"issue_id", "account_id"?}: no account takes it yourself; an Admin of the department (the Super User: any Admin) may be
    given it; `null` hands it back (unassigned)."""
    ident = ctx.identity
    issue = await _load(ctx, int_field(payload, "issue_id"))
    db = ctx.engine.db
    target = payload.get("account_id", ident.account_id)
    if target is not None:
        who = await db.accounts.by_id(int(target))
        if who is None or who["status"] != "active" or who["role"] not in ("admin", "super_user"):
            raise ProtocolError(ErrorCode.INVALID, "an issue is given to an Admin")
        if who["role"] == "admin":
            require_department_scope(ident, who["department_id"])
            if who["department_id"] != issue["department_id"]:
                raise ProtocolError(ErrorCode.INVALID, "that Admin is not in this issue's department")
        elif ident.role != "super_user":
            raise ProtocolError(ErrorCode.FORBIDDEN, "only the Super User gives an issue to themselves")
    await db.issues.assign(issue["id"], None if target is None else int(target))
    names = await db.accounts.display_names_for(ident.account_id, [int(target)]) if target is not None else {}
    text = "Handed back, unassigned" if target is None else ("Took it" if target == ident.account_id else f"Given to {names.get(int(target))}")
    await db.issues.log(issue["id"], "assigned", text, ident.account_id)
    await ctx.engine.audit.record(ctx, "issue.assigned", target_type="issues", target_id=issue["id"], pc_id=issue["pc_id"],
                                  detail={"code": issue["code"], "owner": target, "department_id": issue["department_id"]})
    return {"issue": (await _view(ctx, [await db.issues.get(issue["id"])]))[0]}


@handler("issues.escalate")
async def issues_escalate(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """An Admin sends an issue up: it becomes the Super User's (unassigned in the department, escalated)."""
    require_role(ctx, "admin")
    issue = await _load(ctx, int_field(payload, "issue_id"))
    if issue["state"] == "resolved":
        raise ProtocolError(ErrorCode.CONFLICT, "this issue is already resolved")
    db = ctx.engine.db
    note = str_field(payload, "note", required=False) or ""
    await db.issues.escalate(issue["id"], None)
    await db.issues.set_state(issue["id"], issue["state"], "Escalated")
    await db.issues.log(issue["id"], "escalated", "Sent up to the Super User" + (f": {note}" if note else ""), ctx.identity.account_id)
    await ctx.engine.audit.record(ctx, "issue.escalated", target_type="issues", target_id=issue["id"], pc_id=issue["pc_id"],
                                  detail={"code": issue["code"], "department_id": issue["department_id"]})
    await ctx.engine.push_to_role("super_user", "issue.escalated", {"issue_id": issue["id"], "code": issue["code"], "title": issue["title"]})
    return {"issue": (await _view(ctx, [await db.issues.get(issue["id"])]))[0]}


@handler("issues.note")
async def issues_note(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    issue = await _load(ctx, int_field(payload, "issue_id"))
    text = " ".join(str_field(payload, "text").split())[:500]
    if not text:
        raise ProtocolError(ErrorCode.INVALID, "a note needs words")
    await ctx.engine.db.issues.log(issue["id"], "note", text, ctx.identity.account_id)
    return {"timeline": await _timeline(ctx, issue)}


# --- what clears an issue by itself, and the sweep for machines that went quiet ------------------

def install(engine: Engine) -> None:
    """A copy that is deleted or moved away clears its file issue; a machine that connects again clears its offline issue."""

    async def on_file(event: dict[str, Any]) -> None:
        if not engine.db.connected or event["op"] not in ("delete", "move"):
            return
        gone = event["path"] if event["op"] == "delete" else event.get("old_path")
        if not gone:
            return
        for issue in await engine.db.issues.file_issues_at(event["pc_id"], gone):
            await resolve_issue(engine, issue["id"], "The copy is gone")

    engine.file_index.subscribe(on_file)


async def on_execution(engine: Engine, execution_id: int, status: str, summary: str | None) -> None:
    """A run started for an issue (a copy deleted from here) has finished: it clears the issue, or says why it did not."""
    if not engine.db.connected:
        return
    issue = await engine.db.issues.by_execution(execution_id)
    if issue is None:
        return
    if status == "success":
        await resolve_issue(engine, issue["id"], summary or "Done")
    else:
        await engine.db.issues.set_state(issue["id"], "open", "Open")
        await engine.db.issues.log(issue["id"], "failed", f"It did not work ({status})" + (f": {summary}" if summary else ""))


async def on_connected(engine: Engine, pc_id: int) -> None:
    """A machine's client connected: it is checking in, so its offline issue (if any) is over."""
    if not engine.db.connected:
        return
    for issue in await engine.db.issues.open_of_type(pc_id, "offline"):
        await resolve_issue(engine, issue["id"], "It is checking in again")


async def sweep(engine: Engine) -> int:
    """Scheduler: raise an issue for a machine that was connected and has gone quiet; make it medium after a day. Never-connected
    machines (not installed yet) are not issues. Returns how many were raised."""
    if not engine.db.connected:
        return 0
    online = engine.online_pc_ids()
    now = datetime.now(timezone.utc)
    raised = 0
    for pc in await engine.db.accounts.quiet_pcs(now - OFFLINE_AFTER):
        if pc["id"] in online:
            continue
        severity = "medium" if now - pc["last_seen_at"] > OFFLINE_MEDIUM_AFTER else "low"
        issue_id, created = await raise_issue(
            engine, type_="offline", severity=severity, title="Machine not checking in", subject=f"last seen {pc['last_seen_at']:%a %H:%M}",
            pc_id=pc["id"], source_table="offline_pcs", source_id=pc["id"], detail={"last_seen_at": pc["last_seen_at"].isoformat()},
            state="waiting", label="Waiting")
        if created:
            raised += 1
        else:
            existing = await engine.db.issues.get(issue_id)
            if existing and existing["severity"] != severity and existing["state"] != "resolved":
                await engine.db.issues.set_severity(issue_id, severity)
    return raised
