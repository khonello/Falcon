"""Render the Operator Client GUI offscreen with a stubbed connection, and save a PNG.

    python design/shot_gui.py <out-dir> [admin|super_user] [rail-index] [page] [focus-department-id]

The stub answers the same handlers the real views call, with a small organisation that matches the
design boards, so a screenshot of the app can be put beside a screenshot of the board.
"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
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
        {"id": 7, "resource_tag": "restricted", "filename": "budget-2026.xlsx",
         "path": "C:/Shared/workers/budget-2026.xlsx", "hostname": "OPS-07", "department_id": 1,
         "detected_at": _at(10.7), "resolved_at": None}]},
    "audit.deviations": {"deviations": [
        {"id": 3, "expectation": "account_used_from_unbound_pc", "detected_at": _at(11.1), "resolved_at": _at(11.4)},
        {"id": 2, "expectation": "hostname_did_not_match_certificate", "detected_at": _at(9.2), "resolved_at": None}]},
    "reports.routing_get": {
        "categories": ["listener_report", "resource_violation", "flow_failure",
                       "cross_department_assistance", "system_deviation"],
        "routing": [{"category": "listener_report", "routed_department_id": 1, "department_name": "Operations"},
                    {"category": "resource_violation", "routed_department_id": 1, "department_name": "Operations"},
                    {"category": "resource_violation", "routed_department_id": 2, "department_name": "Finance"}]},
    "control.action_list": {"builtin": {}, "actions": {
        "control": [{"id": 4, "name": "Lock folder", "builtin_type": "lock_folder", "timeout_seconds": 60},
                    {"id": 5, "name": "Clear temp", "builtin_type": "clear_temp", "timeout_seconds": 120}],
        "monitoring": [{"id": 6, "name": "Screenshot", "builtin_type": "screenshot", "timeout_seconds": 30}],
        "custom": [{"id": 7, "name": "Notify Admin", "custom_script_language": "python", "timeout_seconds": 30}]}},
    "control.event_list": {"types": ["file_opened", "flow_failed", "disk_low", "schedule"], "events": [
        {"id": 1, "condition_type": "native", "enabled": True, "last_fired_at": None,
         "condition_spec": {"type": "file_opened", "match": {"path_prefix": "/restricted/"}},
         "actions": [{"id": 7, "name": "Notify Admin"}, {"id": 4, "name": "Lock folder"}]},
        {"id": 2, "condition_type": "polled", "enabled": True, "last_fired_at": None,
         "condition_spec": {"type": "disk_low", "match": {"percent": 10}},
         "actions": [{"id": 5, "name": "Clear temp"}]}]},
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
    "flow.list": {"flows": [
        {"id": 1, "created_by_account_id": 3012, "source_pc_id": 21, "source_hostname": "OPS-01", "status": "active"}, {"id": 2, "created_by_account_id": 3012, "source_pc_id": 23, "source_hostname": "OPS-03", "status": "active"},
        {"id": 3, "created_by_account_id": 3012, "source_pc_id": 25, "source_hostname": "OPS-05", "status": "active"}, {"id": 4, "created_by_account_id": 3012, "source_pc_id": 27, "source_hostname": "OPS-07", "status": "paused"},
        {"id": 5, "source_pc_id": 31, "source_hostname": "FIN-01", "status": "active"}, {"id": 6, "source_pc_id": 32, "source_hostname": "FIN-02", "status": "active"},
        {"id": 7, "source_pc_id": 31, "source_hostname": "FIN-01", "status": "paused"}]},
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
            data = {"entries": _attempts()}
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
        if os.environ.get("FALCON_SHOT_INSIDE"):
            QMetaObject.invokeMethod(win, "goInside")
            # FALCON_SHOT_TAB=<key> opens that entry of the Admin's rail once inside
            if os.environ.get("FALCON_SHOT_TAB"):
                win.setProperty("view", {"tasks": 1, "flows": 2, "automation": 3, "actions": 4,
                                         "assistance": 5, "reports": 6}[os.environ["FALCON_SHOT_TAB"]])
            # FALCON_SHOT_SUBTAB=<n> picks a tab inside Automation; the events tab also selects row 1
            if os.environ.get("FALCON_SHOT_SUBTAB"):
                tabs = win.findChild(object, "automationTabs")
                tabs.setProperty("currentIndex", int(os.environ["FALCON_SHOT_SUBTAB"]))
                table = win.findChild(object, "eventTable")
                if table is not None:
                    table.setProperty("selectedIndex", 0)
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
        name += "-s" + os.environ["FALCON_SHOT_SUBTAB"] if os.environ.get("FALCON_SHOT_SUBTAB") else ""
        name += "-scale" if os.environ.get("FALCON_SHOT_SCALE") else ""
        name += "-rd" + os.environ["FALCON_SHOT_ROLLOUT_DEPT"] if os.environ.get("FALCON_SHOT_ROLLOUT_DEPT") else ""
        name += "-task" + os.environ["FALCON_SHOT_TASK"] if os.environ.get("FALCON_SHOT_TASK") else ""
        name += "-new" if os.environ.get("FALCON_SHOT_NEWTASK") else ""
        path = out_dir / (name + ".png")
        img.save(str(path))
        print("saved", path, img.width(), img.height())
        app.quit()

    QTimer.singleShot(1200, lambda: (win.setMinimumSize(QSize(0, 0)), win.resize(1440, 900)))
    QTimer.singleShot(4300, grab)
    sys.exit(app.exec())


if __name__ == "__main__":
    main(Path(sys.argv[1]),
         sys.argv[2] if len(sys.argv) > 2 else "admin",
         int(sys.argv[3]) if len(sys.argv) > 3 else 0,
         int(sys.argv[4]) if len(sys.argv) > 4 else 0,
         int(sys.argv[5]) if len(sys.argv) > 5 else 0)
