"""Open the console with sample data and no Engine, to look at it.

    environ-operator\\Scripts\\python.exe scripts\\preview.py            # a window on screen
    environ-operator\\Scripts\\python.exe scripts\\preview.py --shot out.png   # offscreen, to a file

The real `FalconBridge` is used unchanged: only its connection is faked, so every screen goes through
the same `falcon.call(type, payload, cb)` path it will use against a real Engine.
"""
from __future__ import annotations

import asyncio
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

SHOT = "--shot" in sys.argv
if SHOT:
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
if os.name == "nt":
    os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")

from PySide6.QtCore import QSize, QTimer

from operator_client.core.config import LocalConfig
from operator_client.gui import app as gui_app

# --- the sample organisation ---------------------------------------------------------------------
PEOPLE = ["R. Mensah", "A. Quaye", "K. Boateng", "You", "System", "Automation"]
AUDIT = [
    ("13:11", "R. Mensah", "Left OPS-03", "OPS-03", "session.ended"),
    ("12:30", "R. Mensah", "Entered OPS-03", "OPS-03", "session.opened"),
    ("11:42", "You", "Ended A. Quaye's session", "WS-OPS-A2", "hierarchy.end_session"),
    ("11:03", "Automation", "Lock the screen ran on OPS-07", "OPS-07", "control.action_run"),
    ("10:41", "A. Quaye", "Assisting Finance, by consent", "FIN-02", "assisted_access.accepted"),
    ("10:02", "System", "budget-2026.xlsx found on a worker machine", "OPS-07", "resource.violation"),
    ("09:52", "K. Boateng", "Approved 1.4.2 for rollout", "", "updates.approve"),
    ("09:40", "Kojo", "Pinged their Admin", "OPS-01", "assistance.ping"),
    ("09:18", "R. Mensah", "Gave Ama a task: reconcile the Q3 invoices", "OPS-07", "task.create"),
    ("09:11", "System", "Hostname did not match the certificate", "OPS-05", "deviation.hostname"),
    ("08:55", "Automation", "Notify ran on OPS-03", "OPS-03", "control.action_run"),
    ("08:40", "A. Quaye", "Made a flow: Payroll to three machines", "OPS-01", "flow.create"),
    ("08:22", "System", "OPS-06 reported 1.4.1, a version behind", "OPS-06", "updates.report_status"),
    ("08:03", "Efua", "Signed in", "OPS-02", "session.native"),
    ("02:14", "A. Quaye", "Entered LOG-02, out of hours", "LOG-02", "session.opened"),
]
CLEAR_TEMP = """import os, time, shutil
cut = time.time() - 7 * 86400
root = os.environ['TEMP']
for name in os.listdir(root):
    p = os.path.join(root, name)
    if os.path.getmtime(p) < cut:
        shutil.rmtree(p, ignore_errors=True)"""

ANSWERS = {
    "audit.recent": {"entries": [
        {"occurred_at": f"2026-09-29T{at}:00+00:00", "actor_name": who, "summary": what,
         "target_hostname": host, "action": action}
        for at, who, what, host, action in AUDIT]},
    "hierarchy.tree": {"departments": [
        {"department_id": 1, "name": "Operations",
         "admins": [{"account_id": 7, "name": "R. Mensah", "role": "admin", "status": "active"},
                   {"account_id": 9, "name": "A. Quaye", "role": "admin", "status": "active"}],
         "workers": [
             {"pc_id": 1, "hostname": "OPS-01", "name": "Kojo", "session": {"occupied_via": "native"}},
             {"pc_id": 2, "hostname": "OPS-02", "name": "Efua", "session": None},
             {"pc_id": 3, "hostname": "OPS-03", "name": "Yaw", "session": {"occupied_via": "native"}},
             {"pc_id": 4, "hostname": "OPS-04", "name": "Adjoa",
              "session": {"occupied_via": "traversal", "occupant_name": "R. Mensah"}},
             {"pc_id": 5, "hostname": "OPS-05", "name": "Nana", "session": {"occupied_via": "native"}},
             {"pc_id": 6, "hostname": "OPS-06", "name": "Kwame", "session": None},
             {"pc_id": 7, "hostname": "OPS-07", "name": "Ama", "session": {"occupied_via": "native"}}]},
        {"department_id": 2, "name": "Finance",
         "admins": [{"account_id": 8, "name": "K. Boateng", "role": "admin", "status": "active"}],
         "workers": [{"pc_id": 11, "hostname": "FIN-01", "name": "Afi", "session": {"occupied_via": "native"}},
                     {"pc_id": 12, "hostname": "FIN-02", "name": "Kofi", "session": None}]},
        {"department_id": 3, "name": "Logistics", "admins": [],
         "workers": [{"pc_id": 21, "hostname": "LOG-01", "name": "Esi", "session": None},
                     {"pc_id": 22, "hostname": "LOG-02", "name": "Abena", "session": None}]},
    ]},
    "updates.rollout_health": {
        "version": {"version_string": "1.4.2"},
        "departments": [{"department_id": 1, "name": "Operations", "on_current": 6, "total": 7},
                        {"department_id": 3, "name": "Logistics", "on_current": 1, "total": 2}],
        "pcs_behind": [{"pc_id": 6, "hostname": "OPS-06", "department_id": 1,
                        "department_name": "Operations", "escalated": False, "version": "1.4.1"},
                       {"pc_id": 22, "hostname": "LOG-02", "department_id": 3,
                        "department_name": "Logistics", "escalated": True, "version": "1.4.0"}]},
    "reports.list": {"reports": [
        {"id": 1, "category": "resource_violation", "source_table": "resource_violations",
         "source_id": 1, "generated_at": "2026-09-29T10:02:00+00:00", "addressed_at": None},
        {"id": 2, "category": "flow_failure", "source_table": "flow_destinations", "source_id": 2,
         "generated_at": "2026-09-29T08:44:00+00:00", "addressed_at": "2026-09-29T09:10:00+00:00"},
        {"id": 3, "category": "listener_report", "source_table": "message_channels", "source_id": 4,
         "generated_at": "2026-09-28T16:20:00+00:00", "addressed_at": None},
        {"id": 4, "category": "update_status", "source_table": "pc_version_status", "source_id": 9,
         "generated_at": "2026-09-28T09:05:00+00:00", "addressed_at": None},
    ]},
    "reports.addressed_view": {"views": [
        {"report_id": 2, "category": "flow_failure", "addressed_by_name": "K. Boateng",
         "department_name": "Finance", "addressed_at": "2026-09-29T09:10:00+00:00"},
    ]},
    "reports.mark": {"view_id": 1},
    "resource.shelves": {"shelves": [
        {"folder": "Resources/Admin", "tag": "admin", "files": 42},
        {"folder": "Resources/Restricted", "tag": "restricted", "files": 17},
        {"folder": "Resources/Department", "tag": "worker_dept", "files": 310},
        {"folder": "Resources/Common", "tag": "common", "files": 1204},
    ]},
    "resource.resolve": {},
    "assistance.ping_status": {"pings": [
        {"ping_id": 5, "from_name": "Kojo", "count": 2},
    ]},
    "assistance.channels": {"channels": [
        {"id": 1, "initiator_account_id": 21, "superior_account_id": 1, "turn": "superior",
         "initiator_name": "Ama", "opened_at": "2026-09-29T09:40:00+00:00", "closed_at": None},
        {"id": 2, "initiator_account_id": 22, "superior_account_id": 1, "turn": "sender",
         "initiator_name": "Efua", "opened_at": "2026-09-28T14:05:00+00:00", "closed_at": None},
        {"id": 3, "initiator_account_id": 23, "superior_account_id": 1, "turn": "sender",
         "initiator_name": "Yaw", "opened_at": "2026-09-27T11:00:00+00:00",
         "closed_at": "2026-09-27T11:40:00+00:00"},
    ]},
    "assistance.channel": {
        "channel": {"id": 1, "turn": "superior", "superior_account_id": 1},
        "superior_account_id": 1,
        "messages": [
            {"id": 1, "sender_account_id": 21, "body": "The payroll folder will not open on OPS-07."},
            {"id": 2, "sender_account_id": 1, "body": "Which error does it give you?"},
            {"id": 3, "sender_account_id": 21, "body": "Access denied, straight away."},
        ]},
    "assistance.my_listeners": {"listeners": []},
    "assistance.message": {"message_id": 9, "turn": "sender"},
    "assistance.respond": {"channel_id": 4, "opened": True},
    "assistance.close_channel": {"channel_id": 1, "closed": True},
    "control.action_list": {
        "builtin": {
            "screenshot": {"category": "control", "params": []},
            "notify": {"category": "control", "params": ["message"]},
            "lock_session": {"category": "control", "params": ["duration_s"]},
            "kill_process": {"category": "control", "params": ["name"]},
            "shutdown": {"category": "control", "params": []},
            "process_list": {"category": "monitoring", "params": []},
            "system_metrics": {"category": "monitoring", "params": []},
            "usb_contents": {"category": "monitoring", "params": []},
        },
        "actions": {
            "control": [
                {"id": 1, "action_kind": "control", "builtin_type": "lock_session",
                 "name": "Lock the screen", "timeout_seconds": 30, "params": {"duration_s": 300}},
                {"id": 2, "action_kind": "control", "builtin_type": "notify",
                 "name": "Show them a message", "timeout_seconds": 15,
                 "params": {"message": "Your machine is a version behind."}},
            ],
            "monitoring": [
                {"id": 3, "action_kind": "monitoring", "builtin_type": "usb_contents",
                 "name": "List what is on the USB", "timeout_seconds": 60, "params": {}},
            ],
            "custom": [
                {"id": 4, "action_kind": "custom", "name": "Clear the temp folder",
                 "custom_script_language": "python", "timeout_seconds": 120,
                 "description": "Empties %TEMP% of anything older than a week.",
                 "custom_script": CLEAR_TEMP},
            ],
        }},
    "control.event_list": {
        "types": {"usb.inserted": "native_pushed", "resource.violation": "native_pushed",
                  "threshold.cpu": "polled", "time.recurring": "polled",
                  "user.login": "native_pushed", "flow.failed": "native_pushed"},
        "events": [
            {"id": 1, "enabled": True, "last_fired_at": "2026-09-29T11:03:00+00:00",
             "condition_spec": {"type": "usb.inserted", "pc_ids": None, "match": {}},
             "actions": [{"id": 3, "action_kind": "monitoring", "builtin_type": "usb_contents",
                          "name": "List what is on the USB", "timeout_seconds": 60}]},
            {"id": 2, "enabled": True, "last_fired_at": "2026-09-29T10:02:00+00:00",
             "condition_spec": {"type": "resource.violation", "pc_ids": [7], "match": {}},
             "actions": [{"id": 2, "action_kind": "control", "builtin_type": "notify",
                          "name": "Show them a message", "timeout_seconds": 15},
                         {"id": 1, "action_kind": "control", "builtin_type": "lock_session",
                          "name": "Lock the screen", "timeout_seconds": 30}]},
            {"id": 3, "enabled": False, "last_fired_at": None,
             "condition_spec": {"type": "threshold.cpu", "pc_ids": [1, 3, 5],
                                "match": {"above": 90, "duration_s": 300}},
             "actions": []},
        ]},
    "control.event_history": {"firings": []},
    "control.action_run": {"execution_id": 41,
                           "executions": [{"pc_id": 1, "hostname": "OPS-01", "execution_id": 41}]},
    "control.action_create": {"action": {"id": 9}},
    "control.event_create": {"event": {"id": 9}},
    "control.event_update": {}, "control.event_delete": {},
    "flow.list": {"flows": [
        {"id": 1, "source_pc_id": 1, "source_hostname": "OPS-01", "source_path": "C:/work/payroll",
         "status": "active", "pause_reason": None, "consent_status": "not_required", "stages": [],
         "destinations": [
             {"id": 1, "destination_pc_id": 11, "destination_hostname": "FIN-01",
              "destination_path": "C:/shared/payroll", "suggestion": None,
              "last_sync": {"synced_at": "2026-09-29T12:40:00+00:00"}}]},
        {"id": 2, "source_pc_id": 7, "source_hostname": "OPS-07", "source_path": "C:/reports/weekly",
         "status": "paused", "pause_reason": "destination:path_missing", "consent_status": "granted",
         "stages": [], "suggestion": "The destination folder is gone. Make it, or point the flow somewhere else.",
         "destinations": [
             {"id": 2, "destination_pc_id": 21, "destination_hostname": "LOG-01",
              "destination_path": "D:/handover/weekly",
              "suggestion": "The destination folder is gone. Make it, or point the flow somewhere else.",
              "last_sync": None},
             {"id": 3, "destination_pc_id": None, "destination_hostname": None,
              "destination_path": "//archive/weekly", "suggestion": None, "last_sync": None}]},
        {"id": 3, "source_pc_id": 3, "source_hostname": "OPS-03", "source_path": "C:/intake",
         "status": "paused", "pause_reason": "consent:pending", "consent_status": "pending",
         "stages": [], "destinations": [
             {"id": 4, "destination_pc_id": 12, "destination_hostname": "FIN-02",
              "destination_path": "C:/intake", "suggestion": None, "last_sync": None}]},
    ]},
    "flow.pause": {}, "flow.resume": {}, "flow.delete": {},
    "flow.create": {"flow": {"id": 9}, "consent_pending": False, "collisions_confirmed": []},
    "task.list": {"tasks": [
        {"id": 1, "description_raw": "Reconcile the Q3 invoices", "assignee_name": "R. Mensah",
         "assigner_name": "You", "status": "in_progress", "verification_mode": "stack",
         "soft_deadline_at": "2026-09-28T16:00:00+00:00", "final_deadline_at": "2026-10-02T16:00:00+00:00"},
        {"id": 2, "description_raw": "Move the archive off OPS-07", "assignee_name": "A. Quaye",
         "assigner_name": "You", "status": "active", "verification_mode": "stack",
         "soft_deadline_at": None, "final_deadline_at": "2026-09-27T16:00:00+00:00"},
        {"id": 3, "description_raw": "Walk the new starter through the console", "assignee_name": "K. Boateng",
         "assigner_name": "You", "status": "active", "verification_mode": "none",
         "soft_deadline_at": None, "final_deadline_at": None},
        {"id": 4, "description_raw": "Rekey LOG-02 after the reinstall", "assignee_name": "R. Mensah",
         "assigner_name": "You", "status": "completed", "verification_mode": "stack",
         "soft_deadline_at": None, "final_deadline_at": "2026-09-20T16:00:00+00:00"},
    ]},
    "task.get": {"task": {
        "id": 1, "description_raw": "Reconcile the Q3 invoices", "verification_mode": "stack",
        "items": [
            {"target_type": "file", "intent": "update", "name": "reconciliation.xlsx",
             "path": None, "populated_by": "llm", "status": "passed"},
            {"target_type": "program", "intent": "used_with_file", "name": "Excel",
             "path": None, "populated_by": "llm", "status": "passed"},
            {"target_type": "file", "intent": "create", "name": "q3-summary.docx",
             "path": None, "populated_by": "llm", "status": "pending"},
        ]}},
    "task.propose": {
        "llm_available": True, "needs_assigner": True, "collisions": [], "proposed_split": [],
        "flags": ["deadline_ambiguous"],
        "soft_deadline": "2026-10-01T16:00:00+00:00", "final_deadline": "2026-10-03T16:00:00+00:00",
        "items": [
            {"target_type": "file", "intent": "update", "name": "reconciliation.xlsx",
             "path": None, "populated_by": "llm", "status": "pending"},
            {"target_type": "program", "intent": "used_with_file", "name": "Excel",
             "path": None, "populated_by": "llm", "status": "pending"},
        ]},
    "task.create": {"task": {"id": 5}},
    "hierarchy.pc_register": {"pc_id": 31, "client_id": "9Qv3k1sLpZ2rT8xw",
                              "client_key": "3f9c1a7e2b4d6058a1c3e5f70981b2d4"
                                            "6a8c0e2f4b6d8a0c2e4f60718293a4b5"},
    "resource.violations": {"violations": [
        {"violation_id": 1, "found_on_pc_id": 7, "hostname": "OPS-07", "filename": "budget-2026.xlsx",
         "resource_tag": "restricted", "detected_at": "2026-09-29T10:02:00+00:00", "resolved_at": None},
        {"violation_id": 2, "found_on_pc_id": 2, "hostname": "OPS-02", "filename": "salaries.csv",
         "resource_tag": "admin", "detected_at": "2026-09-26T15:12:00+00:00",
         "resolved_at": "2026-09-26T16:00:00+00:00"}]},
}


class FakeIdentity:
    """What the handshake would have returned."""
    client_id = "preview"
    account_id = 1
    role = "super_user"
    pc_id = 1
    department_id = 1


class StubConnection:
    """Stands in for `EngineConnection`: the bridge above it is the real thing."""

    connected = True

    async def call(self, type_: str, payload: dict) -> dict:
        await asyncio.sleep(0)
        return ANSWERS.get(type_, {})

    async def close(self) -> None:
        return None


def main() -> int:
    import qasync

    cfg = LocalConfig(path=ROOT / "data" / "preview.json", engine_host="127.0.0.1",
                      engine_port=7400, client_id="preview", tls=False)
    app = gui_app.application()
    loop = qasync.QEventLoop(app)                 # falcon.call schedules on this
    asyncio.set_event_loop(loop)
    app, engine, bridge = gui_app.create(cfg, auto_connect=False)
    bridge.conn = StubConnection()
    bridge.state.set_identity(FakeIdentity(), "preview")     # marks the state connected, as a handshake would
    bridge.connected.emit()

    win = engine.rootObjects()[0]
    if "--view" in sys.argv:
        win.setProperty("view", sys.argv[sys.argv.index("--view") + 1])
    if "--open" in sys.argv:                      # a modal or drawer, by objectName
        name = sys.argv[sys.argv.index("--open") + 1]
        from PySide6.QtCore import QObject
        QTimer.singleShot(700, lambda: win.findChild(QObject, name).setProperty("visible", True))
    app.aboutToQuit.connect(loop.stop)       # qasync raises if the Qt loop stops under a pending await

    if not SHOT:
        print("Falcon console \u2014 sample data, no Engine. Close the window to quit.")
        with loop:
            loop.run_forever()
        return 0

    out = Path(sys.argv[sys.argv.index("--shot") + 1]) if len(sys.argv) > sys.argv.index("--shot") + 1 \
        else ROOT / "preview.png"
    def to_design_size() -> None:
        # after app.create's own fit_to_screen has maximised it: a shot is the design's 1440 x 900
        win.showNormal()
        win.setMinimumSize(QSize(0, 0))
        win.setMaximumSize(QSize(16777215, 16777215))
        win.resize(1440, 900)

    QTimer.singleShot(500, to_design_size)

    def grab() -> None:
        img = win.grabWindow()
        out.parent.mkdir(parents=True, exist_ok=True)
        img.save(str(out))
        print("saved", out, img.width(), img.height())
        loop.stop()

    QTimer.singleShot(1800, grab)
    with loop:
        loop.run_forever()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
