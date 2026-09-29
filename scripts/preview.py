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
ANSWERS = {
    "audit.recent": {"entries": [
        {"occurred_at": f"2026-09-29T{at}:00+00:00", "actor_name": who, "summary": what,
         "target_hostname": host, "action": action}
        for at, who, what, host, action in AUDIT]},
    "hierarchy.tree": {"departments": [
        {"department_id": 1, "name": "Operations",
         "admins": [{"account_id": 7, "name": "R. Mensah"}, {"account_id": 9, "name": "A. Quaye"}],
         "workers": [
             {"pc_id": 1, "hostname": "OPS-01", "name": "Kojo", "session": {"occupied_via": "native"}},
             {"pc_id": 2, "hostname": "OPS-02", "name": "Efua", "session": None},
             {"pc_id": 3, "hostname": "OPS-03", "name": "Yaw", "session": {"occupied_via": "native"}},
             {"pc_id": 4, "hostname": "OPS-04", "name": "Adjoa",
              "session": {"occupied_via": "traversal", "occupant_name": "R. Mensah"}},
             {"pc_id": 5, "hostname": "OPS-05", "name": "Nana", "session": {"occupied_via": "native"}},
             {"pc_id": 6, "hostname": "OPS-06", "name": "Kwame", "session": None},
             {"pc_id": 7, "hostname": "OPS-07", "name": "Ama", "session": {"occupied_via": "native"}}]},
        {"department_id": 2, "name": "Finance", "admins": [{"account_id": 8, "name": "K. Boateng"}],
         "workers": [{"pc_id": 11, "hostname": "FIN-01", "name": "Afi", "session": {"occupied_via": "native"}},
                     {"pc_id": 12, "hostname": "FIN-02", "name": "Kofi", "session": None}]},
        {"department_id": 3, "name": "Logistics", "admins": [],
         "workers": [{"pc_id": 21, "hostname": "LOG-01", "name": "Esi", "session": None},
                     {"pc_id": 22, "hostname": "LOG-02", "name": "Abena", "session": None}]},
    ]},
    "updates.rollout_health": {
        "version": {"version_string": "1.4.2"},
        "pcs_behind": [{"pc_id": 6, "hostname": "OPS-06", "escalated": False, "version": "1.4.1"},
                       {"pc_id": 22, "hostname": "LOG-02", "escalated": True, "version": "1.4.0"}]},
    "hierarchy.pc_register": {"pc_id": 31, "client_id": "9Qv3k1sLpZ2rT8xw",
                              "client_key": "3f9c1a7e2b4d6058a1c3e5f70981b2d4"
                                            "6a8c0e2f4b6d8a0c2e4f60718293a4b5"},
    "resource.violations": {"violations": [
        {"violation_id": 1, "found_on_pc_id": 7, "hostname": "OPS-07", "filename": "budget-2026.xlsx",
         "resource_tag": "restricted"}]},
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
