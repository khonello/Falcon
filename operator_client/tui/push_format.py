"""One-line descriptions of Engine pushes for live display. (text, is_alert)"""

from __future__ import annotations

from typing import Any


def describe_push(type_: str, p: dict[str, Any]) -> tuple[str, bool]:
    if type_ == "session.blocked":
        return f"your PC is now occupied by {p.get('occupant_name')} ({p.get('occupant_role')}) until {str(p.get('deadline_at', ''))[11:16]}", True
    if type_ == "session.ended":
        return f"session {p.get('session_id')} ended: {p.get('reason')}", True
    if type_ == "session.released":
        return "your PC was released -- `claim` to take it back", False
    if type_ == "session.extended":
        return f"traversal extended until {str(p.get('deadline_at', ''))[11:16]}", False
    if type_ == "assistance.ping":
        return f"PING from {p.get('from_name')} (account {p.get('from_account_id')}) -- `respond {p.get('ping_id')}`", True
    if type_ == "assistance.ping_status":
        n = p.get("unaddressed", 0)
        return (f"{n} unaddressed ping(s)" if n else ""), bool(n)
    if type_ == "assistance.channel_opened":
        return f"channel {p.get('channel_id')} opened; turn: {p.get('turn')}", False
    if type_ == "assistance.message":
        return f"[channel {p.get('channel_id')}] account {p.get('from_account_id')}: {p.get('body')}", False
    if type_ == "assistance.channel_closed":
        return f"channel {p.get('channel_id')} closed by the superior", False
    if type_ == "assistance.listening":
        return f"you are now listening on channel {p.get('channel_id')}", False
    if type_ == "task.assigned":
        return f"task {p.get('task_id')} assigned to you -- `task {p.get('task_id')}`", False
    if type_ == "task.started":
        return f"task {p.get('task_id')} started by the assignee", False
    if type_ == "task.stack":
        items = p.get("items", [])
        return f"task {p.get('task_id')} stack: " + ", ".join(f"{i.get('proposed_filename') or i.get('program_name')}={i.get('status')}" for i in items), False
    if type_ == "task.deadline":
        return f"DEADLINE ({p.get('kind')}) reached for task {p.get('task_id')}", True
    if type_ == "task.completed":
        return f"task {p.get('task_id')} verified complete", False
    if type_ == "task.incomplete":
        return f"task {p.get('task_id')} verified incomplete -- keep going", True
    if type_ == "report.new":
        return f"report #{p.get('id')} [{p.get('category')}]: {p.get('summary')}", False
    if type_ == "report.addressed":
        return f"report #{p.get('report_id')} addressed by department {p.get('department_id')}", False
    if type_ == "alert.delivered":
        return f"ALERT [{p.get('alert_type')}] {p.get('body')}" + (f" -> {p['action_link']}" if p.get("action_link") else ""), p.get("alert_type") in ("emergency", "warning")
    if type_ == "flow.consent_request":
        return f"{p.get('creator_name')} wants a flow into your space at {p.get('destination_path')} -- `flow consent {p.get('flow_id')} yes|no`", True
    if type_ == "flow.consent_answered":
        return f"flow {p.get('flow_id')} consent {'granted' if p.get('granted') else 'DENIED'}", not p.get("granted")
    if type_ == "flow.failed":
        return f"flow {p.get('flow_id')} -> {p.get('destination_path')} FAILED: {p.get('reason')}. {p.get('suggestion') or ''}", True
    if type_ == "flow.synced":
        return f"flow {p.get('flow_id')} synced {p.get('relative_path')}", False
    if type_ == "resource.violation":
        return f"RESOURCE VIOLATION: {p.get('message')}", True
    if type_ == "assisted_access.offer":
        return f"{p.get('requester_name')} asks for hands-on help -- `assist accept {p.get('request_id')}` / `assist decline {p.get('request_id')}`", True
    if type_ == "assisted_access.started":
        return f"assistance session {p.get('session_id')} started on your workstation (until {str(p.get('deadline_at', ''))[11:16]})", False
    if type_ in ("assisted_access.declined", "assisted_access.closed"):
        return f"assistance request {p.get('request_id')} {type_.rsplit('.', 1)[1]}", False
    if type_ == "event.fired":
        return f"event {p.get('event_id')} ({p.get('type')}) fired on pc {p.get('pc_id')}", False
    if type_ == "action.status":
        chunk = f": {p['chunk']}" if p.get("chunk") else ""
        return f"execution {p.get('execution_id')} {p.get('status')}{chunk}", p.get("status") in ("failed", "terminated")
    if type_ == "update.approved":
        return f"version {p.get('version')} approved -- `update rollout` when ready", False
    if type_ == "update.escalated":
        return f"UPDATE FAILING on pc {p.get('pc_id')} ({p.get('failures')}x) -- needs attention", True
    if type_ == "update.prompt":
        return f"Super User: {p.get('message')}", True
    return f"{type_} {p}", False
