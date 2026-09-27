"""Open the Operator Client GUI on screen, against the same stub `shot_gui.py` renders with.

    environ-operator\\Scripts\\python.exe design\\run_gui.py [admin|super_user] [--empty] [--option[=value] ...]
    --empty                                      a system with no data, for the never-blank rule
    (every --option is shot_gui.py's, e.g. --scale)

No Engine and no database: every request is answered from `shot_gui`'s sample organisation, so the
dashboards can be clicked through -- the pills, the department descent on the map, the rail -- while
the design is being judged. Actions report that they are not wired; this is for looking, not doing.

To drive the real thing instead:

    python -m operator_client --gui --engine 127.0.0.1:7400 --client-id <id> --client-key <hex> --ca data/engine.crt
"""
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path

# must beat shot_gui's own setdefault, which is offscreen
os.environ["QT_QPA_PLATFORM"] = "windows" if sys.platform == "win32" else ""
if os.name == "nt":
    os.environ.setdefault("QT_QPA_FONTDIR", r"C:\Windows\Fonts")
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import shot_gui  # noqa: E402  (design/ is not a package; run from the repo root)

from operator_client.core.config import LocalConfig  # noqa: E402
from operator_client.core.state import Indicator  # noqa: E402
from operator_client.gui import app as gui_app  # noqa: E402


def main(role: str = "super_user") -> None:
    cfg = LocalConfig.load()
    app, engine, bridge = gui_app.create(cfg, auto_connect=False)

    tree = shot_gui.SUPER_TREE if role == "super_user" else shot_gui.TREE
    empty = os.environ.get("FALCON_SHOT_EMPTY") == "1"

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

    def reply(callback, ok, data):
        callback.call([bridge.js_engine.toScriptValue(ok), bridge.js_engine.toScriptValue(data)])

    def sessions(type_, payload, callback) -> bool:
        """A stand-in for the Engine's session rules, enough to walk level 3: an Admin at their
        workstation needs `force`, anyone else is free; leave and extend do what the Engine does."""
        now = datetime.now().astimezone()
        p = payload.toVariant() if hasattr(payload, "toVariant") else (payload or {})
        if type_ == "hierarchy.traverse":
            host = next((a for d in tree for a in d["admins"] if a["pc_id"] == p.get("pc_id")), None)
            working = host and (host.get("session") or {}).get("occupied_via") == "native"
            if working and not p.get("force"):
                reply(callback, False, {"code": "conflict", "message":
                      f"occupied by {host['name']}; pass force=true to block-or-end first"})
                return True
            session = {"session_id": 9, "pc_id": p.get("pc_id"), "occupant_account_id": 1,
                       "occupant_role": "super_user", "occupied_via": "traversal",
                       "entered_at": now.isoformat(), "deadline_at": (now + timedelta(minutes=30)).isoformat(),
                       "extended_count": 0, "un_evictable": True, "super_user_banner": True}
            bridge.state.set_session(session)
            reply(callback, True, {"session": session, "already_occupying": False})
        elif type_ == "hierarchy.end_session":
            bridge.state.set_session(None)
            reply(callback, True, {"ended": True, "reason": "voluntary"})
        elif type_ == "hierarchy.extend_session" and bridge.state.session:
            s = dict(bridge.state.session)
            s["deadline_at"] = (datetime.fromisoformat(s["deadline_at"]) + timedelta(minutes=15)).isoformat()
            bridge.state.set_session(s)
            reply(callback, True, {"deadline_at": s["deadline_at"]})
        else:
            return False
        return True

    def fake_call(type_, payload, callback):
        if sessions(type_, payload, callback):
            return
        if empty:
            data = {"departments": [], "sessions": [], "entries": [], "violations": [], "deviations": [],
                    "tasks": [], "flows": [], "categories": [], "routing": [], "version": None,
                    "pcs_behind": []}
        elif type_ == "hierarchy.tree":
            data = {"departments": tree}
        elif type_ == "hierarchy.sessions_today":
            data = {"since": shot_gui._at(6), "now": shot_gui._at(18), "sessions": shot_gui._sessions()}
        elif type_ == "audit.recent":
            data = {"entries": shot_gui._attempts()}
        else:
            data = shot_gui.STUB.get(type_, {})
        callback.call([bridge.js_engine.toScriptValue(True), bridge.js_engine.toScriptValue(data)])

    bridge.call = fake_call  # type: ignore[assignment]
    bridge.stateChanged.emit()
    bridge.connected.emit()

    print(f"Operator Client open as {role}" + (" (no data)" if empty else "") + " — stubbed, no Engine.")
    sys.exit(app.exec())


if __name__ == "__main__":
    args = shot_gui.take_options(sys.argv[1:])
    main(args[0] if args else "super_user")
