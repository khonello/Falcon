"""Render the Operator Client GUI offscreen with a stubbed connection, and save a PNG.

VIEW_INDEX: optional third argument picks a rail entry."""
import os
import sys
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
     "workers": [{"account_id": 4201, "name": "Esi", "pc_id": 41, "hostname": "LOG-01", "role": "worker", "session": None}]},
]


def main(out_dir: Path, role: str = "admin", view: int = 0) -> None:
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

    def fake_call(type_, payload, callback):
        data = {"departments": tree} if type_ == "hierarchy.tree" else {}
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

    if view:
        win.setProperty("view", view)

    def grab():
        img = win.grabWindow()
        path = out_dir / (f"gui-{role}.png" if not view else f"gui-{role}-view{view}.png")
        img.save(str(path))
        print("saved", path, img.width(), img.height())
        app.quit()

    QTimer.singleShot(1200, lambda: (win.setMinimumSize(QSize(0, 0)), win.resize(1440, 900)))
    QTimer.singleShot(2600, grab)
    sys.exit(app.exec())


if __name__ == "__main__":
    main(Path(sys.argv[1]), sys.argv[2] if len(sys.argv) > 2 else "admin", int(sys.argv[3]) if len(sys.argv) > 3 else 0)
