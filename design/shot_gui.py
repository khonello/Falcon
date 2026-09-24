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

from PySide6.QtCore import QTimer  # noqa: E402

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
    "task.list": {"tasks": [
        {"id": 1, "assignee_account_id": 4001, "soft_deadline_at": None, "final_deadline_at": None},
        {"id": 2, "assignee_account_id": 4003, "soft_deadline_at": None, "final_deadline_at": None},
        {"id": 3, "assignee_account_id": 4004, "soft_deadline_at": _at(9), "final_deadline_at": None},
        {"id": 4, "assignee_account_id": 4005, "soft_deadline_at": _at(9), "final_deadline_at": None},
        {"id": 5, "assignee_account_id": 4007, "soft_deadline_at": _at(8, 2), "final_deadline_at": _at(9, 1)},
        {"id": 6, "assignee_account_id": 4002, "soft_deadline_at": None, "final_deadline_at": None},
        {"id": 7, "assignee_account_id": 4006, "soft_deadline_at": None, "final_deadline_at": None},
        {"id": 8, "assignee_account_id": 4101, "soft_deadline_at": None, "final_deadline_at": None},
        {"id": 9, "assignee_account_id": 4102, "soft_deadline_at": None, "final_deadline_at": None},
        {"id": 10, "assignee_account_id": 4201, "soft_deadline_at": _at(8, 3), "final_deadline_at": _at(9, 2)},
        {"id": 11, "assignee_account_id": 4202, "soft_deadline_at": None, "final_deadline_at": None}]},
    "flow.list": {"flows": [
        {"id": 1, "source_pc_id": 21, "status": "active"}, {"id": 2, "source_pc_id": 23, "status": "active"},
        {"id": 3, "source_pc_id": 25, "status": "active"}, {"id": 4, "source_pc_id": 27, "status": "paused"},
        {"id": 5, "source_pc_id": 31, "status": "active"}, {"id": 6, "source_pc_id": 32, "status": "active"},
        {"id": 7, "source_pc_id": 31, "status": "paused"}]},
}


def main(out_dir: Path, role: str = "admin", view: int = 0, page: int = 0, focus: int = 0) -> None:
    from operator_client.core.state import Indicator

    cfg = LocalConfig.load()
    app, engine, bridge = gui_app.create(cfg, auto_connect=False)

    tree = SUPER_TREE if role == "super_user" else TREE
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
            data = {"since": _at(6), "now": _at(18), "sessions": _sessions()}
        elif type_ == "audit.recent":
            data = {"entries": _attempts()}
        else:
            data = STUB.get(type_, {})
        callback.call([bridge.js_engine.toScriptValue(True), bridge.js_engine.toScriptValue(data)])

    bridge.call = fake_call  # type: ignore[assignment]
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

    def grab():
        img = win.grabWindow()
        name = f"gui-{role}" + ("-empty" if empty else "") + (f"-view{view}" if view else "")
        name += "-" + os.environ["FALCON_SHOT_OPEN"] if os.environ.get("FALCON_SHOT_OPEN") else ""
        name += f"-d{focus}" if focus else ""
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
