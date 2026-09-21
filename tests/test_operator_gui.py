"""Operator Client GUI: the QML loads, and the FalconBridge drives a real Engine (skipped without
PySide6 or FALCON_TEST_DATABASE_URL). Runs offscreen on pytest-asyncio's loop -- the bridge only
needs asyncio, and QML bindings re-evaluate synchronously on property notifies, so no Qt event
loop is required to assert view state. (qasync is what the real app uses; see gui/app.py.)"""

from __future__ import annotations

import asyncio
import os
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import Q_ARG, QMetaObject, QObject, Qt
from PySide6.QtQml import QJSValue

from operator_client.core import LocalConfig
from operator_client.gui.app import create, fit_to_screen
from tests.conftest import key_for, requires_db


@pytest.fixture
def gui(tmp_path: Path):
    """(window, engine, bridge) with a throwaway config; the QML engine is torn down after."""
    cfg = LocalConfig(path=tmp_path / "cfg.json", engine_host="127.0.0.1", engine_port=1, client_id="", tls=False)
    _app, qml, bridge = create(cfg)
    win = qml.rootObjects()[0]
    yield win, qml, bridge
    qml.deleteLater()


def test_qml_loads_and_starts_on_connect_view(gui):
    win, _, bridge = gui
    assert win.title().startswith("Falcon")
    # full screen without resize: pinned to the work area, min == max, minimize + close only
    size = fit_to_screen(win)
    avail = win.screen().availableGeometry()
    assert win.minimumSize() == win.maximumSize() == size
    assert size.width() <= avail.width() and size.height() <= avail.height() and size.width() > 0
    flags = int(win.flags())
    assert flags & int(Qt.WindowMinimizeButtonHint) and flags & int(Qt.WindowCloseButtonHint)
    assert not flags & int(Qt.WindowMaximizeButtonHint)
    assert win.findChild(QObject, "connectView") is not None
    assert not bridge.isConnected and bridge.sessionText == "no session"
    assert bridge.defaultHost == "127.0.0.1" and bridge.defaultPlaintext is True


def test_helpers_are_pure(gui):
    _, _, bridge = gui
    assert "T15:00:00" in bridge.resolveDeadline("tomorrow 3pm")
    assert bridge.resolveDeadline("gibberish") == ""
    assert bridge.validateScript("python", "import os\nprint(1)\n")["ok"]
    assert not bridge.validateScript("python", "import requests\n")["ok"]
    assert bridge.readFile("Z:/definitely/missing.txt").startswith("__error__:")
    assert bridge.pretty({"a": 1}) == '{\n  "a": 1\n}'


def prop(obj: QObject, name: str):
    """A QML `property var` as plain Python (JS arrays/objects arrive as QJSValue)."""
    v = obj.property(name)
    return v.toVariant() if isinstance(v, QJSValue) else v


async def _wait(cond, timeout: float = 5.0) -> None:
    for _ in range(int(timeout / 0.05)):
        if cond():
            return
        await asyncio.sleep(0.05)
    raise AssertionError("condition not met in time")


@requires_db
async def test_bridge_connects_and_views_populate(gui, engine, org):
    win, _, bridge = gui
    seen: list[tuple[str, object]] = []
    bridge.pushReceived.connect(lambda t, p: seen.append((t, p)))
    bridge.hostname = "SU-PC"
    bridge.connectTo("127.0.0.1", engine.port, "cid-su", key_for("cid-su"), True, "")
    await _wait(lambda: bridge.isConnected)
    assert bridge.role == "super_user" and bridge.roleLabel == "Super User" and bridge.accountId == org["su"]

    # views refresh on connect: the hierarchy tree lands in QML state
    rail = win.findChild(QObject, "hierarchyRail")
    await _wait(lambda: len(prop(rail, "tree") or []) == 2)
    depts = prop(rail, "tree")
    assert [d["name"] for d in depts] == ["Finance", "HR"]
    assert {w["hostname"] for w in depts[0]["workers"]} == {"FIN-01", "FIN-02"}

    # traversal through the bridge updates the persistent status surface
    ok, res = await bridge.request("hierarchy.traverse", {"pc_id": org["w1_pc"], "force": False})
    assert ok, res
    assert bridge.traversing and bridge.superUserBanner and "TRAVERSAL into pc" in bridge.sessionText
    ok, _ = await bridge.request("hierarchy.end_session", {"session_id": bridge.session["session_id"]})
    assert ok and not bridge.traversing and bridge.sessionText == "no session"

    # a typed error comes back as (False, {code, message}) -- never an exception into QML
    ok, err = await bridge.request("task.get", {"task_id": 999999})
    assert not ok and err["code"] and err["message"]

    # a QML-side call: TasksView.open(id) goes through falcon.call and lands in view.task
    ok, created = await bridge.request("task.create", {"assignee_account_id": org["a1"], "description": "tidy the shared drive",
                                                       "verification_mode": "none", "confirm_none": True, "items": []})
    assert ok, created
    tasks = win.findChild(QObject, "tasksView")
    QMetaObject.invokeMethod(tasks, "open", Q_ARG("QVariant", created["task"]["id"]))
    await _wait(lambda: (prop(tasks, "task") or {}).get("id") == created["task"]["id"])
    assert prop(tasks, "task")["verification_mode"] == "none"

    # the assigner verifies; then a clean disconnect
    ok, _ = await bridge.request("task.verify", {"task_id": created["task"]["id"], "outcome": "complete"})
    assert ok
    bridge.disconnect()
    await _wait(lambda: not bridge.isConnected)
    assert bridge.sessionText == "no session"
