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

from PySide6.QtCore import QMetaObject, QObject, Qt
from PySide6.QtQml import QJSValue

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
        if type_ == "audit.recent":
            return {"entries": AUDIT}
        if type_ == "hierarchy.tree":
            return {"departments": TREE}
        if type_ == "updates.rollout_health":
            return {"version": {"version_string": "1.4.2"},
                    "pcs_behind": [{"pc_id": 2, "hostname": "OPS-02", "escalated": True}]}
        if type_ == "resource.violations":
            return {"violations": [{"found_on_pc_id": 1, "hostname": "OPS-01"}]}
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
    assert keys[0] == "overview" and "record" in keys and len(keys) == 13


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
    assert prop(win, "crumbs") == ["Falcon", "Record"]
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
