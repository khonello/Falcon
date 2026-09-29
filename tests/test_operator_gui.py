"""The console's first slice: the QML loads, the shell is there, and the Record page reads what the
Engine answers (docs/UI.md, docs/UI-COMPONENTS.md).

Runs offscreen on pytest-asyncio's loop; skipped without PySide6. The Engine is not needed — the
bridge's connection is the only thing faked, exactly as `scripts/preview.py` does it.
"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import QCoreApplication, QMetaObject, QObject, Qt
from PySide6.QtQml import QJSValue

from common.connection import EngineError
from operator_client.core import LocalConfig
from operator_client.gui.app import create

AUDIT = [
    {"occurred_at": "2026-09-29T13:11:00+00:00", "actor_name": "R. Mensah", "summary": "Left OPS-03",
     "target_hostname": "OPS-03", "action": "session.ended"},
    {"occurred_at": "2026-09-29T10:02:00+00:00", "actor_name": "System",
     "summary": "budget-2026.xlsx found on a worker machine", "target_hostname": "OPS-07",
     "action": "resource.violation"},
    {"occurred_at": "2026-09-29T09:11:00+00:00", "actor_name": "System",
     "summary": "Hostname did not match the certificate", "target_hostname": "OPS-05",
     "action": "deviation.hostname"},
]


TREE = [
    {"department_id": 1, "name": "Operations", "admins": [{"account_id": 7, "name": "R. Mensah"}],
     "workers": [{"pc_id": 1, "hostname": "OPS-01", "name": "Kojo", "session": {"occupied_via": "native"}},
                 {"pc_id": 2, "hostname": "OPS-02", "name": "Efua", "session": None}]},
    {"department_id": 2, "name": "Logistics", "admins": [], "workers": []},
]


TASKS = [
    {"id": 1, "description_raw": "Reconcile the Q3 invoices", "assignee_name": "R. Mensah",
     "assigner_name": "You", "status": "in_progress", "verification_mode": "stack",
     "soft_deadline_at": None, "final_deadline_at": "2026-09-20T16:00:00+00:00"},
    {"id": 2, "description_raw": "Walk the new starter through it", "assignee_name": "R. Mensah",
     "assigner_name": "You", "status": "active", "verification_mode": "none",
     "soft_deadline_at": None, "final_deadline_at": None},
]

PROPOSAL = {
    "llm_available": True, "needs_assigner": True, "collisions": [], "proposed_split": [],
    "flags": ["deadline_ambiguous"], "soft_deadline": None,
    "final_deadline": "2026-10-03T16:00:00+00:00",
    "items": [{"target_type": "file", "intent": "update", "name": "reconciliation.xlsx",
               "path": None, "populated_by": "llm", "status": "pending"}],
}


FLOWS = [
    {"id": 1, "source_hostname": "OPS-01", "source_path": "C:/work/payroll", "status": "active",
     "pause_reason": None, "consent_status": "not_required", "stages": [],
     "destinations": [{"id": 1, "destination_hostname": "FIN-01",
                       "destination_path": "C:/shared/payroll", "suggestion": None, "last_sync": None}]},
    {"id": 2, "source_hostname": "OPS-07", "source_path": "C:/reports", "status": "paused",
     "pause_reason": "destination:path_missing", "consent_status": "granted", "stages": [],
     "suggestion": "The destination folder is gone. Make it, or point the flow somewhere else.",
     "destinations": []},
    {"id": 3, "source_hostname": "OPS-03", "source_path": "C:/intake", "status": "paused",
     "pause_reason": "consent:pending", "consent_status": "pending", "stages": [],
     "destinations": []},
]


BUILTIN = {
    "notify": {"category": "control", "params": ["message"]},
    "lock_session": {"category": "control", "params": ["duration_s"]},
    "usb_contents": {"category": "monitoring", "params": []},
}

LIBRARY = {
    "control": [{"id": 1, "action_kind": "control", "builtin_type": "lock_session",
                 "name": "Lock the screen", "timeout_seconds": 30}],
    "monitoring": [{"id": 3, "action_kind": "monitoring", "builtin_type": "usb_contents",
                    "name": "List what is on the USB", "timeout_seconds": 60}],
    "custom": [{"id": 4, "action_kind": "custom", "name": "Clear the temp folder",
                "custom_script_language": "python", "timeout_seconds": 120,
                "custom_script": "import os\n"}],
}

EVENTS = [
    {"id": 1, "enabled": True, "last_fired_at": None,
     "condition_spec": {"type": "usb.inserted", "pc_ids": None, "match": {}},
     "actions": [{"id": 3, "action_kind": "monitoring", "builtin_type": "usb_contents",
                  "name": "List what is on the USB", "timeout_seconds": 60}]},
    {"id": 2, "enabled": False, "last_fired_at": None,
     "condition_spec": {"type": "threshold.cpu", "pc_ids": [1, 3], "match": {}},
     "actions": []},
]


CHANNELS = [
    # account 1 is the viewer (the _Identity below), and it is the superior on both
    {"id": 1, "initiator_account_id": 21, "superior_account_id": 1, "turn": "superior",
     "initiator_name": "Ama", "opened_at": "2026-09-29T09:40:00+00:00", "closed_at": None},
    {"id": 2, "initiator_account_id": 22, "superior_account_id": 1, "turn": "sender",
     "initiator_name": "Efua", "opened_at": "2026-09-28T14:05:00+00:00", "closed_at": None},
    {"id": 3, "initiator_account_id": 23, "superior_account_id": 1, "turn": "sender",
     "initiator_name": "Yaw", "opened_at": "2026-09-27T11:00:00+00:00",
     "closed_at": "2026-09-27T11:40:00+00:00"},
]

REPORTS = [
    {"id": 1, "category": "resource_violation", "source_table": "resource_violations",
     "source_id": 1, "generated_at": "2026-09-29T10:02:00+00:00", "addressed_at": None},
    {"id": 2, "category": "flow_failure", "source_table": "flow_destinations", "source_id": 2,
     "generated_at": "2026-09-29T08:44:00+00:00", "addressed_at": "2026-09-29T09:10:00+00:00"},
]


def _at(hhmm: str) -> str:
    """An ISO time on whatever day the test runs, since the timeline draws today."""
    from datetime import datetime

    return datetime.now().replace(hour=int(hhmm[:2]), minute=int(hhmm[3:]),
                                  second=0, microsecond=0).isoformat()


DAY = [
    {"session_id": 1, "pc_id": 1, "hostname": "OPS-01", "occupant_name": "Kojo",
     "occupied_via": "native", "entered_at": _at("08:12"), "ended_at": _at("17:30")},
    {"session_id": 2, "pc_id": 22, "hostname": "LOG-02", "occupant_name": "A. Quaye",
     "occupied_via": "traversal", "entered_at": _at("02:14"), "ended_at": _at("03:02")},
    {"session_id": 3, "pc_id": 11, "hostname": "FIN-02", "occupant_name": "A. Quaye",
     "occupied_via": "assisted", "entered_at": _at("10:41"), "ended_at": _at("11:20")},
]


class _Identity:
    client_id, account_id, role, pc_id, department_id = "test", 1, "super_user", 1, 1


class _Connection:
    connected = True

    def __init__(self) -> None:
        self.seen: list[tuple[str, dict]] = []

    async def call(self, type_: str, payload: dict) -> dict:
        await asyncio.sleep(0)
        self.seen.append((type_, payload))
        if type_ == "hierarchy.pc_register":
            return {"pc_id": 9, "client_id": "abc123", "client_key": "0f" * 32}
        if type_ == "task.list":
            return {"tasks": TASKS}
        if type_ == "task.propose":
            return PROPOSAL
        if type_ == "task.create":
            return {"task": {"id": 5}}
        if type_ == "flow.list":
            return {"flows": FLOWS}
        if type_ == "control.action_list":
            return {"builtin": BUILTIN, "actions": LIBRARY}
        if type_ == "control.event_list":
            return {"events": EVENTS, "types": {"usb.inserted": "native_pushed",
                                                "threshold.cpu": "polled"}}
        if type_ == "control.event_history":
            return {"firings": []}
        if type_ == "hierarchy.sessions_today":
            return {"sessions": DAY}
        if type_ == "assistance.channels":
            return {"channels": CHANNELS}
        if type_ == "assistance.ping_status":
            return {"pings": [{"ping_id": 5, "from_name": "Kojo", "count": 2}]}
        if type_ == "resource.shelves":
            return {"shelves": [{"folder": "Resources/Admin", "tag": "admin", "files": 1}]}
        if type_ == "reports.list":
            return {"reports": REPORTS}
        if type_ == "reports.addressed_view":
            return {"views": []}
        if type_ == "updates.current":
            return {}
        if type_ == "flow.create":
            # the Engine refuses a destination that already holds files, unless it is confirmed
            if not payload.get("confirm_collisions"):
                raise EngineError("conflict", "destination path collides with existing content: "
                                              "D:/handover (3 files) -- change the path or pass "
                                              "confirm_collisions=true", type_)
            return {"flow": {"id": 9}, "consent_pending": False, "collisions_confirmed": []}
        if type_ == "audit.recent":
            return {"entries": AUDIT}
        if type_ == "hierarchy.tree":
            return {"departments": TREE}
        if type_ == "updates.rollout_health":
            return {"version": {"version_string": "1.4.2"},
                    "pcs_behind": [{"pc_id": 2, "hostname": "OPS-02", "escalated": True}]}
        if type_ == "resource.violations":
            # the second one is on a PC outside this tree, so it is a Resources row and not a
            # Machines state -- which is exactly how the two pages differ
            return {"violations": [
                {"violation_id": 1, "found_on_pc_id": 1, "hostname": "OPS-01",
                 "filename": "budget-2026.xlsx", "resource_tag": "restricted",
                 "detected_at": "2026-09-29T10:02:00+00:00", "resolved_at": None},
                {"violation_id": 2, "found_on_pc_id": 99, "hostname": "OPS-09",
                 "filename": "salaries.csv", "resource_tag": "admin",
                 "detected_at": "2026-09-26T15:12:00+00:00",
                 "resolved_at": "2026-09-26T16:00:00+00:00"}]}
        return {}

    async def close(self) -> None:
        return None


@pytest.fixture
def gui(tmp_path: Path):
    """(window, bridge), connected to a stubbed Engine, torn down after."""
    cfg = LocalConfig(path=tmp_path / "cfg.json", engine_host="127.0.0.1", engine_port=1,
                      client_id="", tls=False)
    _app, qml, bridge = create(cfg)
    win = qml.rootObjects()[0]
    bridge.conn = _Connection()
    bridge.state.set_identity(_Identity(), "test")
    # `connected` is emitted by the test that wants data: the views answer it with falcon.call, which
    # needs a running asyncio loop, and a sync test has none.
    yield win, bridge
    qml.warnings.disconnect()          # teardown re-evaluates bindings against a falcon that is gone
    qml.deleteLater()


def prop(obj: QObject, name: str):
    v = obj.property(name)
    return v.toVariant() if isinstance(v, QJSValue) else v


def _spin(cond, timeout: float = 2.0) -> None:
    """Qt's own loop, turned by hand. These tests run on asyncio, so a transition only advances if
    somebody pumps the Qt events -- and a drawer sliding out is a transition."""
    import time

    app = QCoreApplication.instance()
    end = time.monotonic() + timeout
    while time.monotonic() < end:
        app.processEvents()
        if cond():
            return
    raise AssertionError("condition not met in time")


async def _wait(cond, timeout: float = 4.0) -> None:
    for _ in range(int(timeout / 0.05)):
        if cond():
            return
        await asyncio.sleep(0.05)
    raise AssertionError("condition not met in time")


def test_the_shell_is_the_console(gui):
    """Sider, header, content -- and the window's own chrome, because it is frameless: the app draws
    minimise, maximise and close itself, so it does not also wear Windows'."""
    win, _ = gui
    assert win.title() == "Falcon"
    assert bool(win.flags() & Qt.WindowType.FramelessWindowHint)

    for name in ("sideMenu", "crumb", "recordView", "recordTable",
                 "winMinimize", "winMaximize", "winClose"):
        assert win.findChild(QObject, name) is not None, name

    # the sider is the only navigation, and it names every area
    menu = win.findChild(QObject, "sideMenu")
    keys = [e["key"] for e in prop(menu, "entries")]
    assert keys[0] == "overview" and keys[-1] == "settings" and len(keys) == 14


def test_the_tokens_are_the_one_place_a_colour_is_named(gui):
    """Ant Design 6's values, with Falcon's two rationed status hues (docs/UI.md)."""
    win, _ = gui
    table = win.findChild(QObject, "recordTable")
    assert table is not None
    # the page and its table exist before anything is fetched, and the table says it is loading
    assert table.property("loading") is True


async def test_the_record_reads_what_the_engine_answers(gui):
    """The Record is the most table-shaped page, and the one the idiom is proved on: rows come from
    `audit.recent`, and the kind of each is named rather than left as a handler's type."""
    win, bridge = gui
    view = win.findChild(QObject, "recordView")
    table = win.findChild(QObject, "recordTable")
    bridge.connected.emit()                      # the views refetch, now that there is a loop

    await _wait(lambda: len(prop(view, "rows") or []) == len(AUDIT))
    rows = prop(view, "rows")
    assert [r["at"] for r in rows] == ["13:11", "10:02", "09:11"]
    assert rows[0]["who"] == "R. Mensah" and rows[0]["subject"] == "OPS-03"

    # only the two that need a person carry a hue; a session is neutral
    assert [r["kind"] for r in rows] == ["session", "violation", "deviation"]
    assert table.property("loading") is False

    # the table pages, sorts and filters over those rows without touching the Engine again
    assert len(prop(table, "filtered")) == 3
    table.setProperty("activeFilters", {"kind": "violation"})
    assert [r["kind"] for r in prop(table, "filtered")] == ["violation"]


async def test_machines_names_every_state_and_only_two_carry_a_hue(gui):
    """One place decides what a machine's state is, so every page agrees: a file out of place and an
    update past the limit need somebody; free, at the PC and entered do not."""
    win, bridge = gui
    win.setProperty("view", "machines")
    view = win.findChild(QObject, "machinesView")
    bridge.connected.emit()

    await _wait(lambda: len(prop(view, "machines") or []) == 2)
    by_host = {m["host"]: m for m in prop(view, "machines")}
    assert by_host["OPS-01"]["state"] == "danger" and by_host["OPS-01"]["line"] == "a file out of place"
    assert by_host["OPS-02"]["state"] == "danger" and by_host["OPS-02"]["line"] == "update past the limit"
    assert prop(view, "needing") == 2


async def test_a_department_with_nobody_governing_it_says_so(gui):
    """The one condition on that page that needs an act, and the only red on it."""
    win, bridge = gui
    win.setProperty("view", "departments")
    view = win.findChild(QObject, "departmentsView")
    bridge.connected.emit()

    await _wait(lambda: len(prop(view, "rows") or []) == 2)
    rows = {r["name"]: r for r in prop(view, "rows")}
    assert rows["Operations"]["governed"] == "R. Mensah" and rows["Operations"]["admins"] == 1
    assert rows["Logistics"]["governed"] == "nobody" and rows["Logistics"]["stateWord"] == "nobody governs it"
    assert prop(view, "ungoverned") == 1


def test_the_crumb_follows_the_view(gui):
    """Derived, never set: a crumb that has to be remembered gets forgotten."""
    win, _ = gui
    assert prop(win, "crumbs") == ["Falcon", "Overview"]
    win.setProperty("view", "machines")
    assert prop(win, "crumbs") == ["Falcon", "Machines"]


async def test_registering_a_machine_is_one_form(gui):
    """The form says what is missing before the Engine is asked, and the key that comes back is shown
    once -- so the modal has a second half rather than closing on success."""
    win, bridge = gui
    win.setProperty("view", "machines")
    modal = win.findChild(QObject, "registerModal")
    toast = win.findChild(QObject, "toast")
    assert modal is not None and toast is not None
    bridge.connected.emit()
    await _wait(lambda: len(prop(win.findChild(QObject, "machinesView"), "machines") or []) == 2)

    modal.setProperty("visible", True)             # opening it resets the form
    assert prop(modal, "hostname") == "" and prop(modal, "valid") is False

    # nothing entered: the form answers, and nothing is sent
    before = len(bridge.conn.seen)
    QMetaObject.invokeMethod(modal, "submit")
    assert prop(modal, "tried") is True
    assert "hostname" in prop(modal, "hostnameProblem")
    assert "department" in prop(modal, "departmentProblem")
    assert len(bridge.conn.seen) == before

    # a Super User workstation belongs to no department, so that row is not asked for
    modal.setProperty("kind", "super_user_workstation")
    assert prop(modal, "needsDepartment") is False and prop(modal, "departmentProblem") == ""
    modal.setProperty("kind", "client_pc")

    modal.setProperty("hostname", "OPS 08")
    assert "spaces" in prop(modal, "hostnameProblem")
    modal.setProperty("hostname", "OPS-08")
    modal.setProperty("departmentId", 1)
    assert prop(modal, "valid") is True

    QMetaObject.invokeMethod(modal, "submit")
    await _wait(lambda: prop(modal, "done") is not None)
    assert ("hierarchy.pc_register",
            {"hostname": "OPS-08", "pc_type": "client_pc", "department_id": 1}) in bridge.conn.seen
    assert prop(modal, "done")["client_key"] == "0f" * 32
    assert prop(modal, "busy") is False and prop(modal, "problem") == ""
    assert prop(toast, "count") == 1               # "OPS-08 registered", said once


async def test_a_task_that_is_past_its_deadline_says_so(gui):
    """One place decides a task's state, and the only red on the page is a deadline that went by."""
    win, bridge = gui
    win.setProperty("view", "tasks")
    view = win.findChild(QObject, "tasksView")
    bridge.connected.emit()

    await _wait(lambda: len(prop(view, "rows") or []) == 2)
    rows = {r["what"]: r for r in prop(view, "rows")}
    assert rows["Reconcile the Q3 invoices"]["stateWord"] == "late"
    assert rows["Reconcile the Q3 invoices"]["stateTone"] == "danger"
    assert rows["Walk the new starter through it"]["stateWord"] == "not started"
    assert rows["Walk the new starter through it"]["checks"] == "nothing to check"
    assert prop(view, "late") == 1


async def test_a_proposal_is_read_before_it_is_committed(gui):
    """Propose, never silently resolve: task.propose commits nothing, and the modal will not send
    task.create until the assigner has seen what came back."""
    win, bridge = gui
    win.setProperty("view", "tasks")
    modal = win.findChild(QObject, "newTaskModal")
    assert modal is not None
    bridge.connected.emit()

    modal.setProperty("visible", True)
    QMetaObject.invokeMethod(modal, "propose")          # nothing entered
    assert prop(modal, "proposal") is None
    assert "who" in prop(modal, "whoProblem")

    modal.setProperty("assigneeId", 7)
    modal.setProperty("description", "Reconcile the Q3 invoices in reconciliation.xlsx")
    QMetaObject.invokeMethod(modal, "propose")
    await _wait(lambda: prop(modal, "proposal") is not None)

    sent = [t for t, _ in bridge.conn.seen]
    assert "task.propose" in sent and "task.create" not in sent    # read first, commit second
    assert prop(modal, "keepStack") is True

    QMetaObject.invokeMethod(modal, "commit")
    await _wait(lambda: any(t == "task.create" for t, _ in bridge.conn.seen))
    payload = [p for t, p in bridge.conn.seen if t == "task.create"][-1]
    assert payload["verification_mode"] == "stack" and len(payload["items"]) == 1
    assert payload["final_deadline_at"] == "2026-10-03T16:00:00+00:00"
    assert "confirm_none" not in payload


async def test_nothing_to_check_has_to_be_said_on_purpose(gui):
    """The Engine refuses verification_mode 'none' without an explicit confirm, and the console sends
    that confirm only because a person picked it from the list."""
    win, bridge = gui
    win.setProperty("view", "tasks")
    modal = win.findChild(QObject, "newTaskModal")
    bridge.connected.emit()

    modal.setProperty("visible", True)
    modal.setProperty("assigneeId", 7)
    modal.setProperty("description", "Walk the new starter through the console")
    QMetaObject.invokeMethod(modal, "propose")
    await _wait(lambda: prop(modal, "proposal") is not None)

    modal.setProperty("keepStack", False)
    modal.setProperty("keepFinal", False)
    QMetaObject.invokeMethod(modal, "commit")
    await _wait(lambda: any(t == "task.create" for t, _ in bridge.conn.seen))
    payload = [p for t, p in bridge.conn.seen if t == "task.create"][-1]
    assert payload["verification_mode"] == "none" and payload["confirm_none"] is True
    assert "items" not in payload and "final_deadline_at" not in payload


async def test_a_stopped_flow_says_the_engine_s_own_sentence(gui):
    """The Engine already writes the suggestion for a failure; the console never invents its own, and
    a flow still waiting on consent is amber, not red -- nobody has done anything wrong."""
    win, bridge = gui
    win.setProperty("view", "flows")
    view = win.findChild(QObject, "flowsView")
    bridge.connected.emit()

    await _wait(lambda: len(prop(view, "rows") or []) == 3)
    rows = {r["flow_id"]: r for r in prop(view, "rows")}
    assert rows[1]["stateWord"] == "running" and rows[1]["stateTone"] == ""
    assert rows[2]["stateWord"] == "stopped" and rows[2]["stateTone"] == "danger"
    assert rows[2]["line"] == FLOWS[1]["suggestion"]
    assert rows[3]["stateWord"] == "waiting" and rows[3]["stateTone"] == "warn"
    assert prop(view, "stopped") == 1


async def test_a_destination_that_already_holds_files_is_a_question(gui):
    """The Engine refuses that once and says so; the console turns the refusal into the cost, and only
    a person's answer sends it again with the confirm."""
    win, bridge = gui
    win.setProperty("view", "flows")
    modal = win.findChild(QObject, "newFlowModal")
    confirm = win.findChild(QObject, "collisionConfirm")
    assert modal is not None and confirm is not None
    bridge.connected.emit()

    modal.setProperty("visible", True)
    modal.setProperty("sourcePcId", 1)
    modal.setProperty("sourcePath", "C:/work/payroll")
    modal.setProperty("targets", [{"pc_id": 21, "path": "D:/handover"}])
    assert prop(modal, "valid") is True

    QMetaObject.invokeMethod(modal, "create")
    await _wait(lambda: confirm.property("visible") is True)
    assert "not backed up" in prop(confirm, "cost") or "files in that folder" in prop(confirm, "cost")
    sent = [p for t, p in bridge.conn.seen if t == "flow.create"]
    assert len(sent) == 1 and "confirm_collisions" not in sent[0]   # refused, and not retried on its own

    QMetaObject.invokeMethod(modal, "createAnyway")   # what the confirm does
    await _wait(lambda: len([p for t, p in bridge.conn.seen if t == "flow.create"]) == 2)
    assert [p for t, p in bridge.conn.seen if t == "flow.create"][-1]["confirm_collisions"] is True


async def test_an_action_is_named_the_way_a_person_says_it(gui):
    """`lock_session` is a wire identifier. One place turns it into words, so the library, the drawer
    and an automation's sentence cannot drift apart."""
    win, bridge = gui
    win.setProperty("view", "actions")
    view = win.findChild(QObject, "actionsView")
    bridge.connected.emit()

    await _wait(lambda: len(prop(view, "rows") or []) == 3)
    rows = {r["name"]: r for r in prop(view, "rows")}
    assert rows["Lock the screen"]["kind"] == "control"
    assert rows["Clear the temp folder"]["kind"] == "custom"
    assert rows["List what is on the USB"]["timeout"] == "60s"


async def test_an_automation_reads_as_one_sentence(gui):
    """When something happens, on these machines, run these -- and a rule with nothing attached says
    so in amber, because it notices and then does nothing."""
    win, bridge = gui
    win.setProperty("view", "automation")
    view = win.findChild(QObject, "automationView")
    bridge.connected.emit()

    await _wait(lambda: len(prop(view, "rows") or []) == 2)
    rows = {r["event_id"]: r for r in prop(view, "rows")}
    assert rows[1]["when"] == "a USB goes in" and rows[1]["where"] == "every machine"
    assert rows[1]["then"] == "List what is on the USB" and rows[1]["stateWord"] == "on"
    assert rows[2]["where"] == "2 machines" and rows[2]["then"] == "nothing yet"
    assert rows[2]["stateTone"] == "warn" and rows[2]["polled"] is True
    assert prop(view, "idle") == 1


async def test_a_script_is_read_before_it_is_sent(gui):
    """Custom Actions are validated three times -- here, at the Engine, and again on the worker. The
    first one is so the refusal reads as a review rather than a rejection."""
    win, bridge = gui
    win.setProperty("view", "actions")
    modal = win.findChild(QObject, "newActionModal")
    bridge.connected.emit()

    modal.setProperty("visible", True)
    modal.setProperty("kind", "custom")
    modal.setProperty("actionName", "Fetch the thing")
    modal.setProperty("script", "import requests\nrequests.get('http://example.com')\n")
    QMetaObject.invokeMethod(modal, "check")
    assert prop(modal, "scriptProblems"), "a third-party import should not pass"
    assert prop(modal, "valid") is False

    modal.setProperty("script", "import os\nprint(os.getcwd())\n")
    QMetaObject.invokeMethod(modal, "check")
    assert prop(modal, "scriptProblems") == []
    assert prop(modal, "valid") is True


async def test_a_drawer_leaves_with_the_page_that_opened_it(gui):
    """A popup lives in the window's overlay, not in the page that declared it, so leaving the page
    used to leave the drawer sitting over the next one."""
    win, bridge = gui
    win.setProperty("view", "machines")
    view = win.findChild(QObject, "machinesView")
    drawer = win.findChild(QObject, "machineDrawer")
    bridge.connected.emit()

    await _wait(lambda: len(prop(view, "machines") or []) == 2)
    drawer.setProperty("visible", True)
    assert drawer.property("visible") is True

    win.setProperty("view", "tasks")
    _spin(lambda: drawer.property("visible") is False)     # it slides out, so turn the loop


async def test_a_channel_says_whose_turn_it_is(gui):
    """A Message Channel takes turns, and the Engine sends the turn as a word plus the two parties --
    the console works out whose it is rather than waiting for a field that does not exist."""
    win, bridge = gui
    win.setProperty("view", "assistance")
    view = win.findChild(QObject, "assistanceView")
    reply = win.findChild(QObject, "replyBox")
    bridge.connected.emit()

    await _wait(lambda: len(prop(view, "rows") or []) == 3)
    rows = {r["channel_id"]: r for r in prop(view, "rows")}
    assert rows[1]["stateWord"] == "your turn" and rows[1]["stateTone"] == "warn"
    assert rows[2]["stateWord"] == "waiting on them" and rows[2]["mineNow"] is False
    assert rows[3]["stateWord"] == "closed" and rows[3]["open"] is False
    assert prop(view, "waiting") == 1

    # the turn is the state of the box, not a sentence about a rule
    view.setProperty("chosen", rows[2])
    assert reply.property("enabled") is False
    view.setProperty("chosen", rows[1])
    assert reply.property("enabled") is True


async def test_a_file_on_the_wrong_shelf_is_the_only_red_on_resources(gui):
    """Which shelf a file sits on is who may have it, so a violation is a file on the wrong shelf --
    and one already sorted is neutral, because nobody has to do anything about it."""
    win, bridge = gui
    win.setProperty("view", "resources")
    view = win.findChild(QObject, "resourcesView")
    bridge.connected.emit()

    await _wait(lambda: len(prop(view, "rows") or []) == 2)
    rows = {r["file"]: r for r in prop(view, "rows")}
    assert rows["budget-2026.xlsx"]["stateTone"] == "danger"
    assert rows["budget-2026.xlsx"]["tier"] == "Named people only"
    assert rows["salaries.csv"]["stateTone"] == "" and rows["salaries.csv"]["resolved"] is True
    assert prop(view, "loose") == 1


async def test_the_super_user_gets_no_addressed_column(gui):
    """`addressed` is written to a separate table and is an Admin's act. The Super User sees every
    report regardless of routing, so a state column there would always read "open" and mean nothing."""
    win, bridge = gui
    win.setProperty("view", "reports")
    view = win.findChild(QObject, "reportsView")
    table = win.findChild(QObject, "reportsTable")
    bridge.connected.emit()

    await _wait(lambda: len(prop(view, "rows") or []) == 2)
    assert prop(view, "boss") is True
    assert [c["title"] for c in prop(table, "columns")] == ["What", "Written from", "When"]
    assert prop(view, "rows")[0]["what"] == "A file turned up where it should not"


async def test_the_gate_holds_while_anything_is_behind(gui):
    """N and N+1, never more: the next version cannot be approved while a machine is still behind, so
    the button is off and the page says why rather than letting the Engine refuse it."""
    win, bridge = gui
    win.setProperty("view", "rollout")
    view = win.findChild(QObject, "rolloutView")
    approve = win.findChild(QObject, "approveVersion")
    bridge.connected.emit()

    await _wait(lambda: len(prop(view, "rows") or []) == 1)
    assert prop(view, "clear") is False
    assert approve.property("enabled") is False
    row = prop(view, "rows")[0]
    assert row["stateWord"] == "past the limit" and row["stateTone"] == "danger"


async def test_the_overview_is_a_list_of_acts(gui):
    """Not a dashboard. Every line is something a person has to do, said in the words of what it is,
    and it opens the page where it gets done. Nothing counts a number that is already fine."""
    win, bridge = gui
    win.setProperty("view", "overview")
    view = win.findChild(QObject, "overviewView")
    bridge.connected.emit()

    await _wait(lambda: len(prop(view, "needs") or []) >= 5)
    needs = prop(view, "needs")
    assert [n["where"] for n in needs][:4] == ["assistance", "resources", "flows", "tasks"]
    assert needs[0]["what"] == "1 person asked for you"
    assert [n["where"] for n in needs].count("rollout") >= 1
    assert all(n["why"] for n in needs), "every line says why it matters"
    # the ones that can wait are amber, the ones that cannot are red
    assert {n["tone"] for n in needs} <= {"danger", "warn"}


async def test_a_person_without_a_status_has_not_left(gui):
    """A row that does not carry a status is not evidence that somebody was offboarded -- only an
    explicit non-active status is."""
    win, bridge = gui
    win.setProperty("view", "people")
    view = win.findChild(QObject, "peopleView")
    bridge.connected.emit()

    await _wait(lambda: len(prop(view, "rows") or []) == 3)
    rows = {r["name"]: r for r in prop(view, "rows")}
    assert rows["R. Mensah"]["role"] == "Admin" and rows["R. Mensah"]["department"] == "Operations"
    assert rows["Kojo"]["stateWord"] == "signed in"        # it has a session
    assert rows["Efua"]["stateWord"] == "not signed in"    # no session, but not gone either


async def test_the_night_is_shaded_and_never_cropped(gui):
    """24 hours is the default span, on purpose: an entry at 02:14 is exactly the thing somebody is
    looking for, and a 6-to-6 chart would simply not draw it. 6 to 6 is a switch, and it does crop --
    which is the point of making it a choice rather than the default."""
    win, bridge = gui
    win.setProperty("view", "machines")
    view = win.findChild(QObject, "machinesView")
    day = win.findChild(QObject, "machinesDay")
    assert day is not None
    bridge.connected.emit()

    view.setProperty("look", "day")
    await _wait(lambda: len(prop(day, "lanes") or []) == 3)
    hosts = [lane["host"] for lane in prop(day, "lanes")]
    assert hosts == ["FIN-02", "LOG-02", "OPS-01"]          # sorted, one lane per machine
    assert prop(day, "fromHour") == 0 and prop(day, "toHour") == 24

    night = [lane for lane in prop(day, "lanes") if lane["host"] == "LOG-02"][0]
    assert round(night["bars"][0]["from"], 1) == 2.2 and night["bars"][0]["via"] == "traversal"

    # the working-day window drops it, and that is the switch saying so
    view.setProperty("fromHour", 6)
    await _wait(lambda: len(prop(day, "lanes") or []) == 2)
    assert "LOG-02" not in [lane["host"] for lane in prop(day, "lanes")]
    assert prop(day, "toHour") == 18

    # a bar that starts before the window is clipped to it, not dropped
    view.setProperty("fromHour", 0)
    await _wait(lambda: len(prop(day, "lanes") or []) == 3)


async def test_the_fleet_grid_groups_by_department(gui):
    """The table is the default answer; the grid is for when a table stops being scannable, and it
    says one thing per machine because that is all that survives at this size."""
    win, bridge = gui
    win.setProperty("view", "machines")
    view = win.findChild(QObject, "machinesView")
    grid = win.findChild(QObject, "machinesGrid")
    bridge.connected.emit()

    await _wait(lambda: len(prop(view, "machines") or []) == 2)
    view.setProperty("look", "grid")
    groups = prop(grid, "groups")
    assert [g["name"] for g in groups] == ["Operations"]
    assert [m["host"] for m in groups[0]["machines"]] == ["OPS-01", "OPS-02"]


def test_the_session_banner_empties_as_the_clock_runs(gui):
    """One row, only when you are actually inside somebody's machine, with a real bar for the clock --
    not a stripe, and not a picture of one moment."""
    win, _ = gui
    banner = win.findChild(QObject, "sessionBanner")
    assert banner is not None
    assert banner.property("visible") is False          # nothing is held, so it is not there

    from datetime import datetime, timedelta

    now = datetime.now()
    banner.setProperty("since", (now - timedelta(minutes=10)).isoformat())
    banner.setProperty("until", (now + timedelta(minutes=10)).isoformat())
    assert 0.4 < prop(banner, "remaining") < 0.6       # halfway through
    assert 9 <= prop(banner, "minutes") <= 11
