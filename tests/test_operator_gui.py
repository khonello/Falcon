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


def test_the_overview_is_four_cells_each_saying_how_it_stands(gui):
    """The Overview is one page and a perfect grid (board K01): four cells, each with a title and a
    generated state phrase beside it. No tabs, and no cell is missing its narration."""
    win, _, _ = gui
    grid = win.findChild(QObject, "mustSeeGrid")
    assert grid is not None and grid.property("columns") == 2

    titles = []
    for name in ("cellAuthority", "cellRollout", "cellToday", "cellOutOfPlace"):
        cell = win.findChild(QObject, name)
        assert cell is not None, name
        titles.append(cell.property("title"))
        # `brief` shares the title's line, so it is held to six words in core/narrate.py
        assert len(str(cell.property("brief")).split()) <= 6, (name, cell.property("brief"))
    assert titles[0] == "Authority" and titles[2] == "Today" and titles[3] == "Out of place"


def test_a_cell_opens_in_place_and_escape_restores_the_grid(gui):
    """Clicking a cell does not navigate: the page recomposes around it (board K03), and the
    composition belongs to that cell. A cell with nothing to explain does not open at all."""
    win, _, _ = gui
    view = win.findChild(QObject, "overviewView")
    cell = win.findChild(QObject, "cellAuthority")
    assert view is not None and cell is not None
    assert view.property("opened") == ""

    # nothing is loaded in this fixture, so there is no ungoverned department and nothing to open
    assert cell.property("openable") is False

    # the opened composition is built and reachable, and it is Authority's own -- a big chart, two
    # told panels beneath it, and the reading down the right
    for name in ("openedAuthority", "openedHero", "openedFleet", "openedSessions", "openedReading"):
        assert win.findChild(QObject, name) is not None, name

    view.setProperty("opened", "authority")
    assert view.property("opened") == "authority"
    view.setProperty("opened", "")
    assert view.property("opened") == ""


def test_each_cell_opens_into_its_own_composition(gui):
    """The composition belongs to the cell (board K04): Rollout's subject is a fleet, so its hero
    runs the full width with three panels beneath -- not Authority's map-and-column shape."""
    win, _, _ = gui
    view = win.findChild(QObject, "overviewView")

    for name in ("openedRollout", "rolloutHero", "rolloutByDept", "rolloutTrend", "rolloutBlocking"):
        assert win.findChild(QObject, name) is not None, name

    # the two compositions are different objects, and the breadcrumb says the cell's own title
    assert win.findChild(QObject, "openedRollout") is not win.findChild(QObject, "openedAuthority")
    view.setProperty("opened", "rollout")
    assert view.property("openedTitle") == "Rollout"
    view.setProperty("opened", "authority")
    assert view.property("openedTitle") == "Authority"
    view.setProperty("opened", "")

    # nothing is loaded in this fixture, so no version is approved and the cell has no gate to
    # explain: it stays shut, exactly as a cell with nothing to say must
    assert win.findChild(QObject, "cellRollout").property("openable") is False


def test_all_four_cells_have_their_own_composition(gui):
    """Four cells, four shapes: Authority's map with the words down the right (K03), Rollout's
    full-width fleet (K04), Today's tall lead and column (K05), and Out of place's ledger (K06).
    Two cells sharing a shape would make the page one template again, which is what was rejected."""
    win, _, _ = gui
    view = win.findChild(QObject, "overviewView")

    panels = {
        "authority": ("openedAuthority", "openedHero", "openedFleet", "openedSessions", "openedReading"),
        "rollout": ("openedRollout", "rolloutHero", "rolloutByDept", "rolloutTrend", "rolloutBlocking"),
        "today": ("openedToday", "todayLead", "todayEntered", "todayQuiet", "todayReading"),
        "place": ("openedOutOfPlace", "placeTiers", "placeDeviations", "placeReading"),
    }
    for key, names in panels.items():
        for name in names:
            assert win.findChild(QObject, name) is not None, name
        view.setProperty("opened", key)
        assert view.property("opened") == key
        assert view.property("openedTitle") != key, key        # the breadcrumb says the cell's title
    view.setProperty("opened", "")

    # with nothing loaded not one of them opens: a cell with nothing to explain stays shut
    for cell in ("cellAuthority", "cellRollout", "cellToday", "cellOutOfPlace"):
        assert win.findChild(QObject, cell).property("openable") is False, cell


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
