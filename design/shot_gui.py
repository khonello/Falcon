"""Render the Operator Client GUI offscreen with a stubbed connection, and save a PNG.

    python design/shot_gui.py <out-dir> [admin|super_user] [rail-index] [page] [focus-department-id] [--option[=value] ...]

Options pick the state to render, e.g. `--flow=4`, `--stepout`, `--dialog=offboard`, `--connect=unreachable`:
each `--name[=value]` is the FALCON_SHOT_<NAME> setting (no value means 1), so nothing is set in the shell.

The stub answers the same handlers the real views call, with a small organisation that matches the
design boards, so a screenshot of the app can be put beside a screenshot of the board.
"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
if os.name == "nt":
    os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")   # offscreen Qt ships no fonts


def take_options(argv: list[str]) -> list[str]:
    """`--name[=value]` -> FALCON_SHOT_<NAME>; returns the positional arguments that remain."""
    rest = []
    for arg in argv:
        if arg.startswith("--"):
            name, _, value = arg[2:].partition("=")
            os.environ["FALCON_SHOT_" + name.upper().replace("-", "_")] = value or "1"
        else:
            rest.append(arg)
    return rest
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PySide6.QtCore import Q_ARG, QMetaObject, QTimer  # noqa: E402

from operator_client.core.config import LocalConfig  # noqa: E402
from operator_client.gui import app as gui_app  # noqa: E402

TREE = [{
    "department_id": 1, "name": "Operations",
    "admins": [
        {"account_id": 3012, "name": "R. Mensah", "pc_id": 11, "hostname": "WS-OPS-A1", "role": "admin",
         "session": {"occupied_via": "native", "occupant_name": "R. Mensah"}},
        {"account_id": 3013, "name": "A. Quaye", "pc_id": 12, "hostname": "WS-OPS-A2", "role": "admin", "session": None},
    ],
    "workers": [
        {"account_id": 4001, "name": "Kojo", "pc_id": 21, "hostname": "OPS-01", "role": "worker",
         "session": {"occupied_via": "native", "occupant_name": "Kojo"}},
        {"account_id": 4002, "name": "Efua", "pc_id": 22, "hostname": "OPS-02", "role": "worker", "session": None},
        {"account_id": 4003, "name": "Yaw", "pc_id": 23, "hostname": "OPS-03", "role": "worker",
         "session": {"occupied_via": "native", "occupant_name": "Yaw"}},
        {"account_id": 4004, "name": "Adjoa", "pc_id": 24, "hostname": "OPS-04", "role": "worker",
         "session": {"occupied_via": "traversal", "occupant_name": "R. Mensah", "occupant_role": "admin"}},
        {"account_id": 4005, "name": "Nana", "pc_id": 25, "hostname": "OPS-05", "role": "worker",
         "session": {"occupied_via": "native", "occupant_name": "Nana"}},
        {"account_id": 4006, "name": "Kwame", "pc_id": 26, "hostname": "OPS-06", "role": "worker", "session": None},
        {"account_id": 4007, "name": "Ama", "pc_id": 27, "hostname": "OPS-07", "role": "worker",
         "session": {"occupied_via": "native", "occupant_name": "Ama"}},
    ],
}]

SUPER_TREE = TREE + [
    {"department_id": 2, "name": "Finance",
     "admins": [{"account_id": 3020, "name": "K. Boateng", "pc_id": 30, "hostname": "WS-FIN-A1", "role": "admin", "session": None}],
     "workers": [{"account_id": 4101, "name": "Afi", "pc_id": 31, "hostname": "FIN-01", "role": "worker", "session": None},
                 {"account_id": 4102, "name": "Kofi", "pc_id": 32, "hostname": "FIN-02", "role": "worker",
                  "session": {"occupied_via": "assisted", "occupant_name": "A. Quaye"}}]},
    {"department_id": 3, "name": "Logistics", "admins": [],
     "workers": [{"account_id": 4201, "name": "Esi", "pc_id": 41, "hostname": "LOG-01", "role": "worker", "session": None},
                 {"account_id": 4202, "name": "Abena", "pc_id": 42, "hostname": "LOG-02", "role": "worker", "session": None}]},
]


def _at(hour: float, days_ago: int = 0) -> str:
    now = datetime.now().astimezone()
    base = (now - timedelta(days=days_ago)).replace(hour=int(hour), minute=int((hour % 1) * 60),
                                                    second=0, microsecond=0)
    return base.isoformat()


def _sessions() -> list[dict]:
    """A day on the fleet: native stretches, one Admin traversal, one Super User entry, one assist."""
    rows = [
        (21, "Kojo", 4001, "worker", "native", 8.2, 12.0), (21, "Kojo", 4001, "worker", "native", 13.0, None),
        (23, "Yaw", 4003, "worker", "native", 9.0, 12.5),
        (23, "R. Mensah", 3012, "admin", "traversal", 12.5, 13.2),
        (23, "Yaw", 4003, "worker", "native", 13.2, None),
        (24, "Adjoa", 4004, "worker", "native", 8.0, 10.3),
        (24, "R. Mensah", 3012, "admin", "traversal", 10.3, 11.0),
        (24, "Adjoa", 4004, "worker", "native", 11.0, None),
        (25, "Nana", 4005, "worker", "native", 8.5, None),
        (27, "Ama", 4007, "worker", "native", 8.2, 10.7),
        (27, "You", 1, "super_user", "traversal", 10.7, 11.1),
        (27, "Ama", 4007, "worker", "native", 11.1, None),
        (32, "A. Quaye", 3013, "admin", "assisted_access", 9.4, 10.2),
    ]
    dept = {21: 1, 23: 1, 24: 1, 25: 1, 27: 1, 32: 2}
    host = {21: "OPS-01", 23: "OPS-03", 24: "OPS-04", 25: "OPS-05", 27: "OPS-07", 32: "FIN-02"}
    return [{"session_id": i + 1, "pc_id": pc, "hostname": host[pc], "department_id": dept[pc],
             "occupant_account_id": acc, "occupant_name": name, "occupant_role": role,
             "occupied_via": via, "entered_at": _at(a), "ended_at": _at(b) if b else None,
             "ended_reason": "voluntary" if b else None, "deadline_at": None,
             "extended_count": 0, "un_evictable": False, "restricted_view": False, "super_user_banner": False}
            for i, (pc, name, acc, role, via, a, b) in enumerate(rows)]


def _attempts() -> list[dict]:
    """Successful update attempts over the week -- what the confirmations trend accumulates."""
    per_day = [(6, 2), (5, 2), (4, 1), (3, 1), (2, 1), (1, 1), (0, 1)]
    out, pc = [], 20
    for days_ago, n in per_day:
        for _ in range(n):
            pc += 1
            out.append({"id": pc, "actor_account_id": None, "action_type": "update.attempt",
                        "target_type": "pc_version_status", "target_id": pc,
                        "detail": {"version": "1.4.2", "succeeded": True},
                        "occurred_at": _at(11, days_ago), "actor_name": "engine"})
    return out



def _dest(i, host, path, parent=None, paused=None, owner=None):
    return {"id": i, "parent_stage_id": parent, "destination_pc_id": i, "destination_hostname": host, "destination_path": path,
            "paused_reason": paused, "owner_account_id": owner,
            "suggestion": "OPS-03 has not answered since 11:20 — check it is switched on, then resume." if paused else None}


def _act(i, kind, builtin, name, timeout=60, **extra):
    return {"id": i, "kind": kind, "action_kind": kind, "builtin_type": builtin, "name": name,
            "timeout_seconds": timeout, "timing": {"mode": "immediate"}, **extra}


ACTIONS = {
    "control": [_act(1, "control", "notify", "Notify me", 30), _act(2, "control", "lock_session", "Lock the screen", 60),
                _act(3, "control", "screenshot", "screenshot", 30), _act(4, "control", "kill_process", "Close Excel", 30),
                _act(8, "control", "reboot", "reboot", 120), _act(9, "control", "start_process", "Open the backup tool", 60),
                _act(10, "control", "shutdown", "shutdown", 120)],
    "monitoring": [_act(5, "monitoring", "system_metrics", "system_metrics", 30), _act(6, "monitoring", "process_list", "process_list", 30),
                   _act(11, "monitoring", "usb_contents", "usb_contents", 60), _act(12, "monitoring", "idle_time", "idle_time", 30),
                   _act(13, "monitoring", "file_activity", "Watch Finance", 60)],
    "custom": [_act(7, "custom", None, "Clear temp", 120, custom_script_language="powershell"),
               _act(14, "custom", None, "Archive quarter", 600, custom_script_language="python")],
}
_A = {a["id"]: a for k in ACTIONS for a in ACTIONS[k]}


def _ev(i, type_, match, actions, pcs=None, enabled=True):
    return {"id": i, "enabled": enabled, "condition_type": "native_pushed", "last_fired_at": None,
            "condition_spec": {"type": type_, "pc_ids": pcs, "match": match}, "actions": [_A[a] for a in actions]}


EVENTS = [
    _ev(1, "file.modified", {"tier": "restricted"}, [1, 2]),
    _ev(2, "threshold.memory", {"percent": 92}, [7]),
    _ev(3, "time.recurring", {"at": "18:00", "days": [0, 1, 2, 3, 4]}, [2]),
    _ev(4, "usb.inserted", {}, [11, 3], pcs=[23, 27]),
    _ev(5, "user.login", {}, [1]),
    _ev(6, "threshold.cpu", {"percent": 85, "duration_s": 300}, [6]),
    _ev(7, "task.deadline_final", {}, [1], enabled=False),
]


# The audit trail as audit.recent sends it (the Record page's "The trail")
TRAIL = [
    {"action_type": "resource.violation_resolved", "actor_account_id": 3012, "actor_name": "R. Mensah", "occurred_at": _at(11.75), "detail": {}},
    {"action_type": "resource.violation", "actor_account_id": None, "actor_name": "engine", "occurred_at": _at(11.68), "detail": {"hostname": "OPS-07"}},
    {"action_type": "session.ended", "actor_account_id": 1, "actor_name": "You", "occurred_at": _at(11.1), "detail": {"hostname": "OPS-07"}},
    {"action_type": "session.traversed", "actor_account_id": 1, "actor_name": "You", "occurred_at": _at(10.7), "detail": {"hostname": "OPS-07"}},
    {"action_type": "assisted_access.accepted", "actor_account_id": 3013, "actor_name": "A. Quaye", "occurred_at": _at(9.4), "detail": {}},
    {"action_type": "session.traversed", "actor_account_id": 3012, "actor_name": "R. Mensah", "occurred_at": _at(10.3), "detail": {"hostname": "OPS-04"}},
    {"action_type": "update.attempt", "actor_account_id": None, "actor_name": "engine", "occurred_at": _at(9.1), "detail": {}},
    {"action_type": "task.created", "actor_account_id": 3012, "actor_name": "R. Mensah", "occurred_at": _at(8.8), "detail": {}},
]

# Flows as flow.list sends them: the shape (stages, destinations) rides along so every flow can be drawn
FLOWS = [
    {"id": 1, "created_by_account_id": 3012, "source_pc_id": 21, "source_hostname": "OPS-01", "status": "active",
      "consent_status": "not_required", "source_path": "C:/Users/kojo/Documents/Invoices",
      "stages": [], "destinations": [_dest(1, "OPS-05", "D:/Shared/Invoices")]},
    {"id": 2, "created_by_account_id": 3012, "source_pc_id": 25, "source_hostname": "OPS-05", "status": "active",
      "consent_status": "not_required", "source_path": "C:/Users/ama/Desktop/Scans",
      "stages": [{"id": 1, "parent_stage_id": None, "stage_type": "categorization"}],
      "destinations": [_dest(2, "OPS-02", "D:/Scans/Receipts", 1), _dest(3, "OPS-06", "D:/Scans/Forms", 1)]},
    {"id": 3, "created_by_account_id": 3012, "source_pc_id": 27, "source_hostname": "OPS-07", "status": "active",
      "consent_status": "pending", "source_path": "C:/Users/efua/Documents/Reports",
      "stages": [], "destinations": [_dest(4, "FIN-02", "D:/Inbox/Ops reports", owner=3021)]},
    {"id": 4, "created_by_account_id": 3012, "source_pc_id": 21, "source_hostname": "OPS-01", "status": "paused",
      "consent_status": "not_required", "source_path": "C:/Users/kojo/Documents/Payroll",
      "suggestion": "OPS-03 has not answered since 11:20 — check it is switched on, then resume.",
      "stages": [{"id": 2, "parent_stage_id": None, "stage_type": "transformation"}],
      "destinations": [_dest(5, "OPS-03", "D:/Archive/payroll", 2, paused="unreachable"),
                       _dest(6, "OPS-04", "D:/Archive/payroll", 2), _dest(7, "OPS-06", "D:/Archive/payroll", 2)]},
]

STUB = {
    "updates.rollout_health": {
        "version": {"id": 4, "version_string": "1.4.2"},
        "departments": [{"department_id": 1, "department_name": "Operations", "pcs": 7, "current": 6, "pending": 1, "escalated": 0},
                        {"department_id": 2, "department_name": "Finance", "pcs": 2, "current": 2, "pending": 0, "escalated": 0},
                        {"department_id": 3, "department_name": "Logistics", "pcs": 2, "current": 1, "pending": 0, "escalated": 1}],
        "pcs_behind": [{"pc_id": 26, "hostname": "OPS-06", "department_id": 1, "current_version_id": 3,
                        "failures": 1, "last_attempt_at": _at(9.5), "escalated": False},
                       {"pc_id": 42, "hostname": "LOG-02", "department_id": 3, "current_version_id": 2,
                        "failures": 6, "last_attempt_at": _at(7.5), "escalated": True}],
    },
    "resource.violations": {"violations": [
        {"id": 7, "expected_tag": "restricted", "filename": "budget-2026.xlsx", "file_index_id": 70,
         "path": "C:/Shared/workers/budget-2026.xlsx", "hostname": "OPS-07", "department_id": 1, "found_on_pc_id": 27,
         "surfaced_to_account_id": 4007, "detected_via": "event", "detected_at": _at(10.7), "resolved_at": None},
        {"id": 5, "expected_tag": "restricted", "filename": "pay-scales-2026.xlsx", "file_index_id": 71,
         "path": "C:/Users/yaw/Desktop/pay-scales-2026.xlsx", "hostname": "OPS-03", "department_id": 1, "found_on_pc_id": 23,
         "surfaced_to_account_id": 4003, "detected_via": "polling_fallback", "detected_at": _at(8.2), "resolved_at": None}]},
    "resource.shelves": {"shelves": [{"folder": "restricted", "tag": "restricted", "files": 5},
                                     {"folder": "workers", "tag": "worker_dept", "files": 24},
                                     {"folder": "common", "tag": "common", "files": 40}]},
    "audit.deviations": {"deviations": [
        {"id": 3, "expectation": "account_used_from_unbound_pc", "detected_at": _at(11.1), "resolved_at": _at(11.4)},
        {"id": 2, "expectation": "hostname_did_not_match_certificate", "detected_at": _at(9.2), "resolved_at": None}]},
    "reports.routing_get": {
        "categories": ["listener_report", "resource_violation", "flow_failure",
                       "cross_department_assistance", "system_deviation"],
        "routing": [{"category": "listener_report", "routed_department_id": 1, "department_name": "Operations"},
                    {"category": "resource_violation", "routed_department_id": 1, "department_name": "Operations"},
                    {"category": "resource_violation", "routed_department_id": 2, "department_name": "Finance"}]},
    "control.action_list": {"builtin": {t: {"category": c, "params": []} for c, ts in (
        ("control", ["screenshot", "notify", "lock_session", "rename_file", "restore_file", "kill_process", "start_process",
                     "shutdown", "reboot"]),
        ("monitoring", ["process_list", "system_metrics", "file_activity", "idle_time", "snapshot_file", "usb_contents"]))
        for t in ts}, "actions": ACTIONS},
    "control.execution": {"execution": {"id": 95, "status": "success"}, "output": ["locked"]},
    "control.action_run": {"execution_id": 95, "executions": [{"pc_id": 27, "hostname": "OPS-07", "execution_id": 95}]},
    "control.event_list": {"types": {}, "events": EVENTS},
    # everything running this second, whichever automation started it (AU04's "Running now")
    "control.dashboard": {"automations": [], "live": [
        {"id": 95, "action_id": 3, "target_pc_id": 23, "builtin_type": "lock_session",
         "status": "pending", "started_at": "2026-09-28T14:18:00+00:00"}]},
    "control.event_history": {"event_id": 1, "fired_today": 3, "running": [
        {"id": 91, "action_name": "Lock the screen", "builtin_type": "lock_session", "status": "pending", "hostname": "OPS-03"}],
        "firings": [
        {"at": _at(14.3), "hostname": "OPS-03", "subject": "payroll.xlsx", "runs": [
            {"id": 91, "action_name": "Notify me", "builtin_type": "notify", "status": "success"},
            {"id": 92, "action_name": "Lock the screen", "builtin_type": "lock_session", "status": "pending"}]},
        {"at": _at(11.68), "hostname": "OPS-07", "subject": "budget-2026.xlsx", "runs": [
            {"id": 81, "action_name": "Notify me", "builtin_type": "notify", "status": "success"},
            {"id": 82, "action_name": "Lock the screen", "builtin_type": "lock_session", "status": "success"}]},
        {"at": _at(10.03), "hostname": "OPS-03", "subject": "payroll.xlsx", "runs": [
            {"id": 71, "action_name": "Notify me", "builtin_type": "notify", "status": "success"},
            {"id": 72, "action_name": "Lock the screen", "builtin_type": "lock_session", "status": "terminated",
             "terminated_reason": "timeout"}]},
        {"at": _at(8.92), "hostname": "OPS-07", "subject": "budget-2026.xlsx", "runs": [
            {"id": 61, "action_name": "Notify me", "builtin_type": "notify", "status": "success"},
            {"id": 62, "action_name": "Lock the screen", "builtin_type": "lock_session", "status": "success"}]}]},
    "assistance.ping_status": {"unaddressed": 2, "indicator": "unaddressed_ping", "pings": [
        {"id": 31, "sender_account_id": 4001, "from_name": "Kojo", "sent_at": _at(9.67)},
        {"id": 32, "sender_account_id": 4001, "from_name": "Kojo", "sent_at": _at(10.25)}]},
    "assistance.channels": {"channels": [
        {"id": 14, "initiator_account_id": 4007, "superior_account_id": 3012, "turn": "superior", "closed_at": None, "opened_at": _at(11.03)},
        {"id": 12, "initiator_account_id": 3012, "superior_account_id": 1, "turn": "superior", "closed_at": None, "opened_at": _at(10.5)},
        {"id": 9, "initiator_account_id": 4002, "superior_account_id": 3012, "turn": "sender", "closed_at": _at(9.4), "opened_at": _at(8.9)}]},
    "assistance.channel": {"channel": {"id": 14, "initiator_account_id": 4007, "superior_account_id": 3012, "turn": "superior",
                                       "closed_at": None, "opened_at": _at(11.03), "my_turn": True, "subordinate_account_id": 4007}, "messages": [
        {"id": 1, "sender_account_id": 4007, "body": "I can't open the budget file any more.", "sent_at": _at(11.03)},
        {"id": 2, "sender_account_id": 3012, "body": "It is restricted; it should not be on your machine. Move it to Documents.", "sent_at": _at(11.08)},
        {"id": 3, "sender_account_id": 4007, "body": "Done — it says moved. Is that all?", "sent_at": _at(11.15)}]},
    "assistance.my_listeners": {"listeners": [{"listener_account_id": 3013, "name": "A. Quaye"}]},
    "assistance.search": {"results": [
        {"id": 1, "filename": "budget-template-2026.xlsx", "path": "C:/resources/common/budget-template-2026.xlsx", "pc_id": 11, "resource_tag": "common"},
        {"id": 2, "filename": "budget-q3-draft.xlsx", "path": "C:/resources/workers/budget-q3-draft.xlsx", "pc_id": 11, "resource_tag": "worker_dept"},
        {"id": 3, "filename": "budget-notes.docx", "path": "C:/Users/yaw/Documents/budget-notes.docx", "pc_id": 23, "resource_tag": None}]},
    "reports.list": {"reports": [
        {"id": 41, "category": "resource_violation", "source_table": "resource_violations", "source_id": 7,
         "generated_at": _at(11.68), "addressed_at": None},
        {"id": 40, "category": "flow_failure", "source_table": "flow_destinations", "source_id": 5,
         "generated_at": _at(11.33), "addressed_at": None},
        {"id": 38, "category": "directory_structure_conflict", "source_table": "flows", "source_id": 2,
         "generated_at": _at(14.6, 1), "addressed_at": None},
        {"id": 35, "category": "listener_report", "source_table": "message_channels", "source_id": 14,
         "generated_at": _at(9.5, 3), "addressed_at": _at(10, 3)},
        {"id": 33, "category": "resource_violation", "source_table": "resource_violations", "source_id": 3,
         "generated_at": _at(15.2, 4), "addressed_at": _at(9, 2)}]},
    "reports.addressed_view": {"addressed": [
        {"report_id": 35, "addressed_at": _at(9.2, 3), "category": "listener_report", "addressed_by_department_id": 2},
        {"report_id": 33, "addressed_at": _at(9, 2), "category": "resource_violation", "addressed_by_department_id": 1}]},
    "control.levels": {"machines": 7, "cpu": [21, 42], "memory": [38, 61], "idle_s": [0, 900]},
    "task.list": {"tasks": [
        {"id": 1, "description_raw": "Update the fleet inventory in inventory-2026.xlsx", "status": "in_progress", "started_at": _at(9.2), "assigner_account_id": 3012, "assignee_account_id": 4001, "assignee_name": "Kojo", "soft_deadline_at": None, "final_deadline_at": None},
        {"id": 2, "description_raw": "Reconcile the Q3 supplier invoices and produce reconciliation-q3.docx", "status": "in_progress", "started_at": _at(9.25), "assigner_account_id": 3012, "assignee_account_id": 4003, "assignee_name": "Yaw", "soft_deadline_at": None, "final_deadline_at": None},
        {"id": 3, "description_raw": "Archive last quarter's folder", "status": "active", "assigner_account_id": 3012, "assignee_account_id": 4004, "assignee_name": "Adjoa", "soft_deadline_at": _at(9), "final_deadline_at": None},
        {"id": 4, "description_raw": "Prepare the onboarding pack for the new starters", "status": "active", "assigner_account_id": 3012, "assignee_account_id": 4005, "assignee_name": "Nana", "soft_deadline_at": _at(9), "final_deadline_at": None},
        {"id": 5, "description_raw": "Finish the quarterly report", "status": "in_progress", "started_at": _at(8.1), "assigner_account_id": 3012, "assignee_account_id": 4007, "assignee_name": "Ama", "soft_deadline_at": _at(8, 2), "final_deadline_at": _at(9, 1)},
        {"id": 6, "description_raw": "Tidy the shared drive", "status": "active", "assigner_account_id": 3013, "assignee_account_id": 4002, "assignee_name": "Efua", "soft_deadline_at": None, "final_deadline_at": None},
        {"id": 7, "description_raw": "Check the printer logs", "status": "active", "assigner_account_id": 3012, "assignee_account_id": 4006, "assignee_name": "Kwame", "soft_deadline_at": None, "final_deadline_at": None},
        {"id": 12, "description_raw": "Department audit for Operations", "status": "active", "assigner_account_id": 1,
         "assigner_name": "Super User", "assignee_account_id": 3012, "assignee_name": "R. Mensah", "soft_deadline_at": None,
         "final_deadline_at": _at(17, -2)},
        {"id": 8, "assignee_account_id": 4101, "assignee_name": "Afi", "soft_deadline_at": None, "final_deadline_at": None},
        {"id": 9, "assignee_account_id": 4102, "assignee_name": "Kofi", "soft_deadline_at": None, "final_deadline_at": None},
        {"id": 10, "assignee_account_id": 4201, "assignee_name": "Esi", "soft_deadline_at": _at(8, 3), "final_deadline_at": _at(9, 2)},
        {"id": 11, "assignee_account_id": 4202, "assignee_name": "Abena", "soft_deadline_at": None, "final_deadline_at": None}]},
    "task.get": {"task": {
        "id": 2, "description_raw": "Reconcile the Q3 supplier invoices against suppliers-q3.xlsx and produce reconciliation-q3.docx",
        "status": "in_progress", "verification_mode": "stack", "assigner_account_id": 3012, "assigner_name": "R. Mensah",
        "assignee_account_id": 4003, "assignee_name": "Yaw", "final_deadline_at": _at(17, -3), "started_at": _at(9.25),
        "items": [
            {"id": 1, "sequence": 1, "target_type": "file", "intent": "update", "proposed_filename": "suppliers-q3.xlsx",
             "status": "passed", "file_path": "D:/Finance/Q3/suppliers-q3.xlsx", "file_last_seen_at": _at(10.7)},
            {"id": 2, "sequence": 2, "target_type": "file", "intent": "create", "proposed_filename": "reconciliation-q3.docx",
             "status": "passed", "file_path": "C:/Users/yaw/Documents/reconciliation-q3.docx", "file_last_seen_at": _at(13.1)},
            {"id": 3, "sequence": 3, "target_type": "program", "intent": "used_with_file", "program_name": "Excel",
             "status": "failed", "file_path": None}]}},
    "task.propose": {
        "llm_available": True, "final_deadline": None, "soft_deadline": None,
        "items": [{"target_type": "file", "intent": "update", "name": "suppliers-q3.xlsx", "file_index_id": 91},
                  {"target_type": "file", "intent": "create", "name": "reconciliation-q3.docx"}],
        "flags": [{"kind": "ambiguous_deadline", "candidates": ["Monday", "Wednesday"]}],
        "collisions": [{"item_index": 1, "name": "reconciliation-q3.docx", "path": None,
                        "existing": [{"file_index_id": 92, "path": "C:/Users/yaw/Documents/reconciliation-q3.docx", "pc_id": 23}]}],
        "proposed_split": [{"description": "Reconcile the Q3 supplier invoices and produce reconciliation-q3.docx", "targets": []},
                           {"description": "archive last quarter's folder", "targets": []}]},
    "flow.list": {"flows": FLOWS},
    "flow.status": {"flow": FLOWS[3]},
    "flow.history": {"history": [
        {"id": 1, "written_by": "external", "written_path": "D:/Archive/payroll/payroll-aug (kept 14.05).xlsx",
         "destination_path": "D:/Archive/payroll", "conflict_resolved": False, "occurred_at": "2026-09-27T14:05:00+00:00"},
        {"id": 2, "written_by": "flow", "destination_path": "D:/Archive/payroll", "occurred_at": "2026-09-27T13:40:00+00:00"}]},
    "index.folders": {"pc_id": 21, "hostname": "OPS-01", "folders": [
        {"path": "C:/Users/kojo/Documents/Invoices", "name": "Invoices", "files": 214},
        {"path": "C:/Users/kojo/Documents/Payroll", "name": "Payroll", "files": 38},
        {"path": "C:/Users/kojo/Desktop/Scans", "name": "Scans", "files": 91}]},
}


# FALCON_SHOT_SCALE=1: the worst case the design is held to -- ten departments, ~240 machines, several failing
SCALE_DEPTS = [("Operations", "OPS", 14, ["RM:R. Mensah", "AQ:A. Quaye"], {6: (6, False)}),
               ("Logistics", "LOG", 2, [], {2: (9, True)}),
               ("Finance", "FIN", 22, ["KB:K. Boateng"], {}),
               ("Harbour", "HAR", 48, ["MA:M. Addo", "JT:J. Tetteh"], {12: (10, False), 17: (10, False), 31: (10, False), 40: (10, False)}),
               ("Customs", "CUS", 31, ["EO:E. Owusu"], {}),
               ("Records", "REC", 9, ["AB:A. Boakye"], {}),
               ("Procurement", "PRO", 17, ["NA:N. Ansah"], {}),
               ("Legal", "LEG", 6, ["SD:S. Darko"], {}),
               ("Payroll", "PAY", 12, ["YF:Y. Frimpong"], {}),
               ("Fleet", "FLT", 64, ["KA:K. Asante"], {n: (11 if n in (41, 44, 50) else 4, n in (41, 44, 50))
                                                        for n in (3, 8, 11, 19, 22, 27, 33, 41, 44, 50, 58, 61)})]


def scale_data():
    tree, depts, behind, pc, acc = [], [], [], 100, 5000
    for di, (name, pre, n, admins, bad) in enumerate(SCALE_DEPTS, start=1):
        a = []
        for spec in admins:
            _, full = spec.split(":")
            acc += 1
            a.append({"account_id": acc, "name": full, "pc_id": None, "hostname": f"WS-{pre}-A{len(a) + 1}", "role": "admin",
                      "session": {"occupied_via": "native"}})
        w = []
        for i in range(1, n + 1):
            pc += 1
            acc += 1
            w.append({"account_id": acc, "name": f"Worker {i}", "pc_id": pc, "hostname": f"{pre}-{i:02d}", "role": "worker", "session": None})
            if i in bad:
                f, esc = bad[i]
                behind.append({"pc_id": pc, "hostname": f"{pre}-{i:02d}", "department_id": di, "current_version_id": 3,
                               "failures": f, "last_attempt_at": _at(11.3), "escalated": esc})
        tree.append({"department_id": di, "name": name, "admins": a, "workers": w})
        depts.append({"department_id": di, "department_name": name, "pcs": n, "current": n - len(bad), "pending": len(bad),
                      "escalated": sum(1 for f, e in bad.values() if e)})
    return tree, {"version": {"id": 4, "version_string": "1.4.2"}, "departments": depts, "pcs_behind": behind}


def main(out_dir: Path, role: str = "admin", view: int = 0, page: int = 0, focus: int = 0) -> None:
    from operator_client.core.state import Indicator

    cfg = LocalConfig.load()
    app, engine, bridge = gui_app.create(cfg, auto_connect=False)

    tree = SUPER_TREE if role == "super_user" else TREE
    scale_health = None
    if os.environ.get("FALCON_SHOT_SCALE"):
        tree, scale_health = scale_data()
    bridge.state.connected = True
    bridge.state.role = role
    bridge.state.account_id = 1 if role == "super_user" else 3012
    bridge.state.pc_id = 1 if role == "super_user" else 11
    bridge.state.department_id = 0 if role == "super_user" else 1
    bridge.state.indicators = [
        Indicator(kind="unaddressed_ping", text="2 pings", key="Kojo, OPS-01, twice"),
        Indicator(kind="deadline_reached", text="Deadline", key="Quarterly report, Ama OPS-07"),
        Indicator(kind="flow_failure", text="Flow failed", key="Payroll to Archive, OPS-03 unreachable"),
        Indicator(kind="task_completed", text="Task done", key="Fleet inventory, Yaw OPS-03"),
    ]

    # FALCON_SHOT_EMPTY=1 renders a system that has only just been bootstrapped: no version, no
    # sessions, no violations. It is how the "a panel is never blank" rule is checked in the real
    # app rather than only on a board.
    empty = os.environ.get("FALCON_SHOT_EMPTY") == "1"

    def fake_call(type_, payload, callback):
        if empty:
            data = {"departments": [], "sessions": [], "entries": [], "violations": [],
                    "deviations": [], "tasks": [], "flows": [], "categories": [], "routing": [],
                    "version": None, "pcs_behind": [], "since": _at(6), "now": _at(18)}
            callback.call([bridge.js_engine.toScriptValue(True), bridge.js_engine.toScriptValue(data)])
            return
        if type_ == "hierarchy.tree":
            data = {"departments": tree}
        elif type_ == "hierarchy.sessions_today":
            rows = _sessions()
            if scale_health:
                remap = {21: 101, 23: 103, 24: 104, 25: 105, 27: 107, 32: 118}
                for r in rows:
                    r["pc_id"] = remap.get(r["pc_id"], r["pc_id"])
            data = {"since": _at(6), "now": _at(18), "sessions": rows}
        elif type_ == "audit.recent":
            p = payload.toVariant() if hasattr(payload, "toVariant") else (payload or {})
            data = {"entries": _attempts() if (p or {}).get("prefix") == "update.attempt" else TRAIL}
        elif type_ == "updates.rollout_health" and scale_health:
            data = scale_health
        else:
            data = STUB.get(type_, {})
        callback.call([bridge.js_engine.toScriptValue(True), bridge.js_engine.toScriptValue(data)])

    bridge.call = fake_call  # type: ignore[assignment]
    # FALCON_SHOT_HOLD=1: this Super User holds R. Mensah's workstation, 28:41 left of thirty minutes
    if os.environ.get("FALCON_SHOT_HOLD") or os.environ.get("FALCON_SHOT_INSIDE"):
        now = datetime.now().astimezone()
        bridge.state.session = {
            "session_id": 9, "pc_id": 11, "occupant_account_id": 1, "occupant_name": "You",
            "occupant_role": "super_user", "occupied_via": "traversal",
            "entered_at": (now - timedelta(seconds=79)).isoformat(),
            "deadline_at": (now + timedelta(minutes=28, seconds=41)).isoformat(),
            "extended_count": 0, "un_evictable": True, "restricted_view": False, "super_user_banner": True}
    # FALCON_SHOT_PC=<pc_id>: holding that client PC and inside it -- level 4
    if os.environ.get("FALCON_SHOT_PC"):
        now = datetime.now().astimezone()
        me = 1 if role == "super_user" else 3012
        bridge.state.session = {
            "session_id": 10, "pc_id": int(os.environ["FALCON_SHOT_PC"]), "occupant_account_id": me,
            "occupant_name": "You" if role == "super_user" else "R. Mensah", "occupant_role": role, "occupied_via": "traversal",
            "entered_at": (now - timedelta(minutes=5)).isoformat(),
            "deadline_at": (now + timedelta(minutes=24, seconds=10)).isoformat(),
            "extended_count": 0, "un_evictable": role == "super_user", "restricted_view": False, "super_user_banner": role == "super_user"}
    # FALCON_SHOT_CONNECT=<connecting|key|unreachable|certificate>: the connect screen with that outcome (ST01)
    if os.environ.get("FALCON_SHOT_CONNECT"):
        kind = os.environ["FALCON_SHOT_CONNECT"]
        bridge.state.connected = False
        bridge._conn_state = "connecting" if kind == "connecting" else "failed"
        bridge._fail_kind = "" if kind == "connecting" else kind
    # FALCON_SHOT_LOST=1: the link dropped mid-session (ST03); FALCON_SHOT_RENAMED=1: connected, name changed
    if os.environ.get("FALCON_SHOT_RENAMED"):
        bridge._name_notice = {"expected": "WS-OPS-A1", "announced": "WS-OPS-A1-NEW"}
    bridge._extension_minutes = 15
    # FALCON_SHOT_BLOCKED=1: someone above is on this operator's own machine
    if os.environ.get("FALCON_SHOT_BLOCKED"):
        bridge.state.blocked_by = {"occupant_name": "the Super User", "occupant_role": "super_user"}
    bridge.stateChanged.emit()
    bridge.connected.emit()

    from PySide6.QtCore import QSize
    win = engine.rootObjects()[0]
    win.setMinimumSize(QSize(0, 0))
    win.setMaximumSize(QSize(16777215, 16777215))
    win.resize(1440, 900)
    win.setWidth(1440)
    win.setHeight(900)
    out_dir.mkdir(parents=True, exist_ok=True)

    win.setProperty("view", view)
    overview = win.findChild(object, "overviewView")
    if overview is not None and os.environ.get("FALCON_SHOT_OPEN"):
        overview.setProperty("opened", os.environ["FALCON_SHOT_OPEN"])
    # FALCON_SHOT_DEPT=<id> enters that department -- level 2, inside Authority
    if os.environ.get("FALCON_SHOT_DEPT"):
        win.setProperty("departmentId", int(os.environ["FALCON_SHOT_DEPT"]))
        # FALCON_SHOT_MAX=machines maximises that chart -- one chart, nothing else on the page
        if os.environ.get("FALCON_SHOT_MAX"):
            dept = win.findChild(object, "departmentView")
            if dept is not None:
                dept.setProperty("maximised", os.environ["FALCON_SHOT_MAX"])

    # FALCON_SHOT_ENTER=1 opens the first Admin in place (DP06); FALCON_SHOT_ANSWER=<kind> puts
    # that answer in the lane (DP08); FALCON_SHOT_INSIDE=1 goes in -- level 3, their interface
    def later():
        # FALCON_SHOT_ROLLOUT_DEPT=<id> maximises that department on the Rollout page
        if os.environ.get("FALCON_SHOT_ROLLOUT_DEPT"):
            rv = win.findChild(object, "rolloutView")
            if rv is not None:
                rv.setProperty("openDept", int(os.environ["FALCON_SHOT_ROLLOUT_DEPT"]))
        dept = win.findChild(object, "departmentView")
        if os.environ.get("FALCON_SHOT_ENTER") and dept is not None:
            dept.setProperty("entering", True)
            if os.environ.get("FALCON_SHOT_ANSWER"):
                lane = win.findChild(object, "enteringAdmin")
                lane.setProperty("answer", {"kind": os.environ["FALCON_SHOT_ANSWER"], "holder": "K. Owusu",
                                            "message": "no such pc"})
        # FALCON_SHOT_TASK=<id> opens one task; FALCON_SHOT_NEWTASK=1 opens a proposed new task
        tv = win.findChild(object, "tasksView")
        if os.environ.get("FALCON_SHOT_TASK") and tv is not None:
            QMetaObject.invokeMethod(tv, "open", Q_ARG("QVariant", int(os.environ["FALCON_SHOT_TASK"])))
        if os.environ.get("FALCON_SHOT_NEWTASK") and tv is not None:
            tv.setProperty("mode", "new")
            nt = win.findChild(object, "newTaskWords")
            words = win.findChild(object, "newTaskText")
            if words is not None:
                words.setProperty("text", "Reconcile the Q3 supplier invoices against suppliers-q3.xlsx and produce "
                                          "reconciliation-q3.docx by Monday or Wednesday. Also archive last quarter's folder.")
            for obj in tv.findChildren(object):
                if obj.metaObject().className().startswith("NewTask"):
                    obj.setProperty("assignee", {"account_id": 4003, "name": "Yaw", "hostname": "OPS-03"})
                    QMetaObject.invokeMethod(obj, "propose")
                    break
        # FALCON_SHOT_FLOW=<id> opens one flow; FALCON_SHOT_NEWFLOW=1 opens a half-written new flow
        fv = win.findChild(object, "flowsView")
        if os.environ.get("FALCON_SHOT_FLOW") and fv is not None:
            QMetaObject.invokeMethod(fv, "open", Q_ARG("QVariant", int(os.environ["FALCON_SHOT_FLOW"])))
        if os.environ.get("FALCON_SHOT_NEWFLOW") and fv is not None:
            fv.setProperty("mode", "new")
            for obj in fv.findChildren(object):
                if obj.metaObject().className().startswith("NewFlow"):
                    obj.setProperty("source", {"pc_id": 21, "hostname": "OPS-01"})
                    obj.setProperty("sourcePath", "C:/Users/kojo/Documents/Invoices")
                    obj.setProperty("stages", [{"stage_type": "categorization"}])
                    obj.setProperty("destinations", [{"pc_id": 25, "hostname": "OPS-05", "path": "D:/Shared/Invoices"},
                                                     {"pc_id": 0, "hostname": "", "path": ""}])
                    obj.setProperty("problem", "D:/Shared/Invoices on OPS-05 already holds 12 files this flow did not write.")
                    obj.setProperty("askCollision", True)
                    break
        # FALCON_SHOT_NEWAUTO=<1|2|3> opens the automation maker at that step, filled in from the first one
        if os.environ.get("FALCON_SHOT_NEWAUTO"):
            av = win.findChild(object, "automationView")
            na = win.findChild(object, "newAutomation")
            ev = STUB["control.event_list"]["events"][int(os.environ.get("FALCON_SHOT_AUTOEV", "0"))]
            QMetaObject.invokeMethod(na, "start", Q_ARG("QVariant", ev))
            na.setProperty("editing", None)
            na.setProperty("pcIds", [23, 24, 26, 27])
            na.setProperty("actionIds", [a["id"] for a in ev["actions"]])
            na.setProperty("step", int(os.environ["FALCON_SHOT_NEWAUTO"]))
            av.setProperty("mode", "new")
        # FALCON_SHOT_ACTION=<id> chooses that action on the Actions page (and tries it on OPS-07);
        # FALCON_SHOT_CUSTOM=1 opens a new custom action with a script already dropped
        acv = win.findChild(object, "actionsView")
        if os.environ.get("FALCON_SHOT_ACTION") and acv is not None:
            want = int(os.environ["FALCON_SHOT_ACTION"])
            act = next(a for k in ACTIONS for a in ACTIONS[k] if a["id"] == want)
            QMetaObject.invokeMethod(acv, "choose", Q_ARG("QVariant", act))
            acv.setProperty("tryPc", 27)
            QMetaObject.invokeMethod(acv, "tryIt")
            QTimer.singleShot(200, lambda: QMetaObject.invokeMethod(acv, "readTrial"))
        if os.environ.get("FALCON_SHOT_CUSTOM") and acv is not None:
            QMetaObject.invokeMethod(acv, "newCustom")
            acv.setProperty("scriptPath", "C:/Users/rm/Documents/clear_temp.ps1")
            acv.setProperty("scriptText", "\n".join(["# empties the temp folders"] * 40))
            acv.setProperty("check", {"ok": True, "problems": []})
            acv.setProperty("customName", "Clear temp")
            acv.setProperty("customDoes", "Empties the temp folders to free disk space.")
        # FALCON_SHOT_DIALOG=<extend|rekey|offboard|register|admin|key|force>: that dialog open (DG01)
        dlg = os.environ.get("FALCON_SHOT_DIALOG")
        if dlg:
            def open_dialog():
                pcv = win.findChild(object, "pcView")
                if dlg == "extend":
                    QMetaObject.invokeMethod(win, "extendSession")
                elif dlg in ("rekey", "offboard"):
                    QMetaObject.invokeMethod(pcv, dlg)
                elif dlg in ("register", "admin"):
                    QMetaObject.invokeMethod(win, "registerMachine", Q_ARG("QVariant", 3), Q_ARG("QVariant", "Logistics"),
                                             Q_ARG("QVariant", "admin" if dlg == "admin" else "worker"))
                elif dlg == "key":
                    QMetaObject.invokeMethod(win, "showKey", Q_ARG("QVariant", "OPS-15 is registered"),
                                             Q_ARG("QVariant", "Give these to whoever sets up OPS-15. They go into its install package."),
                                             Q_ARG("QVariant", "pX3rT0aQv9LmE2sK7wYb"), Q_ARG("QVariant", "7f3a91c2e04b5d18aa6e0c77"))
                elif dlg == "force":
                    QMetaObject.invokeMethod(win, "ask", Q_ARG("QVariant", {
                        "title": "End Yaw's session and enter?", "lead": "Yaw is working at OPS-03 now.",
                        "rows": [["Their session", "ends now", "danger"], ["They see", "who took it", ""], ["They get it back", "when you leave", ""]],
                        "act": "End theirs and enter", "actTone": "danger"}), Q_ARG("QVariant", None))
            QTimer.singleShot(300, open_dialog)
        # FALCON_SHOT_LOST=1: the link drops after the page has loaded, as it does in use (ST03)
        if os.environ.get("FALCON_SHOT_LOST"):
            now = datetime.now().astimezone()
            bridge._held = {"session_id": 10, "pc_id": 23, "deadline_at": (now + timedelta(minutes=19)).isoformat()}
            bridge._conn_state, bridge._retry_in, bridge._lost_at = "lost", 4, now.strftime("%H:%M")
            bridge.state.connected = False
            bridge.stateChanged.emit()
        # FALCON_SHOT_RESOURCES=1 opens Resources from the Admin's home (with FALCON_SHOT_FIND, files to shelve)
        if os.environ.get("FALCON_SHOT_RESOURCES"):
            QMetaObject.invokeMethod(win, "show", Q_ARG("QVariant", "resources"))
            rv = win.findChild(object, "resourcesView")
            if os.environ.get("FALCON_SHOT_FIND") and rv is not None:
                QMetaObject.invokeMethod(rv, "search", Q_ARG("QVariant", os.environ["FALCON_SHOT_FIND"]))
        # FALCON_SHOT_FIND=<text> types that into Assistance's file search
        asv = win.findChild(object, "assistanceView")
        if os.environ.get("FALCON_SHOT_FIND") and asv is not None:
            QMetaObject.invokeMethod(asv, "search", Q_ARG("QVariant", os.environ["FALCON_SHOT_FIND"]))
        # FALCON_SHOT_STEPOUT=1 holds the machine but steps out of it (the lid says "holding")
        if os.environ.get("FALCON_SHOT_PC") and not os.environ.get("FALCON_SHOT_STEPOUT"):
            QMetaObject.invokeMethod(win, "enterPc", Q_ARG("QVariant", int(os.environ["FALCON_SHOT_PC"])))
        if os.environ.get("FALCON_SHOT_INSIDE"):
            QMetaObject.invokeMethod(win, "goInside")
            # FALCON_SHOT_TAB=<key> opens that entry of the Admin's rail once inside
            if os.environ.get("FALCON_SHOT_TAB"):
                win.setProperty("view", {"tasks": 1, "flows": 2, "automation": 3, "actions": 4,
                                         "assistance": 5, "reports": 6}[os.environ["FALCON_SHOT_TAB"]])
    QTimer.singleShot(1600, later)

    def grab():
        img = win.grabWindow()
        name = f"gui-{role}" + ("-empty" if empty else "") + (f"-view{view}" if view else "")
        name += "-" + os.environ["FALCON_SHOT_OPEN"] if os.environ.get("FALCON_SHOT_OPEN") else ""
        name += f"-d{focus}" if focus else ""
        name += "-dept" + os.environ["FALCON_SHOT_DEPT"] if os.environ.get("FALCON_SHOT_DEPT") else ""
        name += "-max" if os.environ.get("FALCON_SHOT_MAX") else ""
        for flag, tag in (("FALCON_SHOT_HOLD", "-held"), ("FALCON_SHOT_ENTER", "-enter"),
                          ("FALCON_SHOT_INSIDE", "-inside")):
            name += tag if os.environ.get(flag) else ""
        name += "-" + os.environ["FALCON_SHOT_ANSWER"] if os.environ.get("FALCON_SHOT_ANSWER") else ""
        name += "-" + os.environ["FALCON_SHOT_TAB"] if os.environ.get("FALCON_SHOT_TAB") else ""
        name += "-auto" + os.environ["FALCON_SHOT_NEWAUTO"] if os.environ.get("FALCON_SHOT_NEWAUTO") else ""
        name += "-action" + os.environ["FALCON_SHOT_ACTION"] if os.environ.get("FALCON_SHOT_ACTION") else ""
        name += "-custom" if os.environ.get("FALCON_SHOT_CUSTOM") else ""
        name += "-resources" if os.environ.get("FALCON_SHOT_RESOURCES") else ""
        name += "-pc" + os.environ["FALCON_SHOT_PC"] if os.environ.get("FALCON_SHOT_PC") else ""
        name += "-out" if os.environ.get("FALCON_SHOT_STEPOUT") else ""
        name += "-blocked" if os.environ.get("FALCON_SHOT_BLOCKED") else ""
        name += "-connect-" + os.environ["FALCON_SHOT_CONNECT"] if os.environ.get("FALCON_SHOT_CONNECT") else ""
        name += "-lost" if os.environ.get("FALCON_SHOT_LOST") else ""
        name += "-renamed" if os.environ.get("FALCON_SHOT_RENAMED") else ""
        name += "-dialog-" + os.environ["FALCON_SHOT_DIALOG"] if os.environ.get("FALCON_SHOT_DIALOG") else ""
        name += "-scale" if os.environ.get("FALCON_SHOT_SCALE") else ""
        name += "-rd" + os.environ["FALCON_SHOT_ROLLOUT_DEPT"] if os.environ.get("FALCON_SHOT_ROLLOUT_DEPT") else ""
        name += "-task" + os.environ["FALCON_SHOT_TASK"] if os.environ.get("FALCON_SHOT_TASK") else ""
        name += "-new" if os.environ.get("FALCON_SHOT_NEWTASK") else ""
        name += "-flow" + os.environ["FALCON_SHOT_FLOW"] if os.environ.get("FALCON_SHOT_FLOW") else ""
        name += "-newflow" if os.environ.get("FALCON_SHOT_NEWFLOW") else ""
        path = out_dir / (name + ".png")
        img.save(str(path))
        print("saved", path, img.width(), img.height())
        app.quit()

    # the app opens maximised now that it is frameless: a shot is the design's own 1440 x 900
    QTimer.singleShot(1200, lambda: (win.showNormal(), win.setMinimumSize(QSize(0, 0)),
                                     win.setMaximumSize(QSize(16777215, 16777215)), win.resize(1440, 900)))
    QTimer.singleShot(4300, grab)
    sys.exit(app.exec())


if __name__ == "__main__":
    args = take_options(sys.argv[1:])
    main(Path(args[0]),
         args[1] if len(args) > 1 else "admin",
         int(args[2]) if len(args) > 2 else 0,
         int(args[3]) if len(args) > 3 else 0,
         int(args[4]) if len(args) > 4 else 0)
