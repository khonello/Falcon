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
    # `create` prints QML warnings, which is what makes a bad property name findable. Tearing the
    # engine down re-evaluates bindings against a `falcon` that is already gone, so the handler is
    # dropped first: that noise is the harness's, not the app's.
    qml.warnings.disconnect()
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


def val(x):
    """A QML `property var` reaches Python as a QJSValue; one whose value came back from the bridge
    is already a dict. Read either the same way."""
    return x.toVariant() if hasattr(x, "toVariant") else x


# --- level 2: a department ------------------------------------------------------------------------

def test_the_rail_is_five_areas_not_eight_features(gui):
    """Areas, not features (design/TABS.md). The Super User rail names the question a person is
    asking; the Admin rail is deliberately left alone until level 3 is opened."""
    win, _, _ = gui
    rail = win.findChild(QObject, "iconRail")
    assert rail is not None
    keys = [e["key"] for e in val(rail.property("superNav"))]
    assert keys == ["mustsee", "authority", "rollout", "record", "work"]
    # the Admin rail is untouched: its area names wait for level 3
    assert val(rail.property("adminNav"))[0]["key"] == "hierarchy"


def test_the_crumb_moves_on_entering_a_department_and_not_on_looking(gui):
    """The one test of the gesture: a double click enters and the crumb grows; nothing a single
    click does moves it. `shell.enterDepartment` is what the map's double click calls."""
    win, _, _ = gui
    assert win.property("departmentId") == 0
    assert win.property("inDepartment") is False

    # the fixture is not connected, so the rail is still the Admin one: show() resolves the area
    # name to whichever key that rail spells it with, which is the point of having two names
    QMetaObject.invokeMethod(win, "show", Q_ARG("QVariant", "authority"))
    assert win.property("onAuthority") is True
    assert win.property("inDepartment") is False    # looking at the area is not being in a place

    QMetaObject.invokeMethod(win, "enterDepartment", Q_ARG("QVariant", 1))
    assert win.property("departmentId") == 1
    assert win.property("inDepartment") is True

    dept = win.findChild(QObject, "departmentView")
    # `visible` is not asserted: the shell's StackLayout is on the connect view in this fixture, so
    # effective visibility is false for everything behind it. What matters is that the page is bound
    # to the department that was entered.
    assert dept is not None and dept.property("departmentId") == 1
    assert win.findChild(QObject, "deptCrumbRoot").property("text") == "Authority"

    # and back out again: the crumb is the thing that returns
    QMetaObject.invokeMethod(dept, "back")
    assert win.property("departmentId") == 0
    assert win.property("inDepartment") is False


def test_a_department_draws_one_admin_and_never_says_an_admin_owns_machines(gui):
    """The boards group machines under the Admin who answers for each. The system has no such
    relationship -- `accounts` carries a department, never a supervising Admin -- so the page draws
    the department's own machines and the sentence says all its Admins govern all of them."""
    win, _, _ = gui
    dept = win.findChild(QObject, "departmentView")
    assert dept is not None
    dept.setProperty("tree", [{
        "department_id": 1, "name": "Operations",
        "admins": [{"account_id": 2, "name": "R. Mensah", "hostname": "WS-OPS-A1",
                    "session": {"occupied_via": "native"}},
                   {"account_id": 3, "name": "A. Quaye", "hostname": "WS-OPS-A2", "session": None}],
        "workers": [{"account_id": 4, "pc_id": 11, "hostname": "OPS-01"},
                    {"account_id": 5, "pc_id": 12, "hostname": "OPS-02"}],
    }])
    dept.setProperty("departmentId", 1)

    assert dept.property("deptName") == "Operations"
    assert len(val(dept.property("fleet"))) == 2
    says = val(dept.property("people"))
    assert says["sentence"] == "All 2 Admins here govern all 2 machines."
    assert not any("answers" in f["label"].lower() for f in says["facts"])

    # whoever the cell draws is whoever is selected; at rest that is the first in the stable order
    assert val(dept.property("admin"))["name"] == "R. Mensah"
    dept.setProperty("selectedAdmin", 1)
    assert val(dept.property("admin"))["name"] == "A. Quaye"
    assert val(dept.property("people"))["sentence"] == "A. Quaye is not signed in anywhere."


def test_the_fleet_changes_kind_rather_than_scrolling(gui):
    """A department was never going to stay the size of the sample: the mark shrinks while shrinking
    still says something, and past that the drawing changes kind. Mirrors slot_size() in
    design/scale.py -- never a scrollbar."""
    win, _, _ = gui
    grid = win.findChild(QObject, "deptFleet")
    assert grid is not None

    def sized(n):
        grid.setProperty("hosts", [{"hostname": f"OPS-{i:02d}", "state": "ok"} for i in range(n)])
        return grid.property("slot"), grid.property("labelled"), grid.property("asBars")

    assert sized(7) == (46, True, False)        # every hostname readable
    assert sized(24) == (30, False, False)      # countable, unlabelled
    assert sized(96) == (16, False, False)      # proportion and outliers
    assert sized(240) == (0, False, True)       # the shape of the fleet, not one mark each


def test_a_chart_maximises_into_itself_and_escape_restores_the_cells(gui):
    """An area recomposes into several panels; a CHART opens into itself (board DP11). What explains
    a chart is more of that chart -- so the hostnames the cell had to drop at scale come back, and
    nothing else is on the page."""
    win, _, _ = gui
    dept = win.findChild(QObject, "departmentView")
    dept.setProperty("tree", [{
        "department_id": 1, "name": "Operations", "admins": [],
        "workers": [{"account_id": i, "pc_id": i, "hostname": f"OPS-{i:02d}"} for i in range(1, 25)],
    }])
    dept.setProperty("departmentId", 1)

    # in the cell, 24 machines have dropped their hostnames to fit
    cell = win.findChild(QObject, "deptFleet")
    assert cell.property("slot") == 30 and cell.property("labelled") is False

    assert dept.property("maximised") == ""
    dept.setProperty("maximised", "machines")
    assert win.findChild(QObject, "deptMaxCrumb").property("text") == "Its machines"

    # maximised, every mark is back to full size and carries its name again
    big = win.findChild(QObject, "deptFleetMax")
    assert big.property("slot") == 46 and big.property("labelled") is True
    assert big.property("asBars") is False

    dept.setProperty("maximised", "")          # Escape restores the four cells exactly
    assert dept.property("maximised") == ""


def test_a_department_is_drawn_on_the_frame_not_on_a_sheet(gui):
    """No grey sheet. A page drawn in the Overview's language sits on the gradient and the frame
    shows between its panels; only the pre-kit views still carry a sheet. The department had been
    inheriting the old Admin-console shell, which is what made it look like a different product."""
    win, _, _ = gui
    QMetaObject.invokeMethod(win, "show", Q_ARG("QVariant", "authority"))
    assert win.property("onFrame") is False          # the area itself still uses the old HomeView
    QMetaObject.invokeMethod(win, "enterDepartment", Q_ARG("QVariant", 1))
    assert win.property("onFrame") is True           # the department page does not


def test_the_fleet_reads_the_fields_the_handlers_actually_return(gui):
    """`updates.rollout_health` returns `pcs_behind` (not `pcs`) whose rows say `escalated`, and a
    violation row carries `found_on_pc_id` and `hostname`. Reading the wrong names drew every machine
    green while the page named a violation beside it -- the page contradicting itself."""
    win, _, _ = gui
    dept = win.findChild(QObject, "departmentView")
    dept.setProperty("tree", [{
        "department_id": 1, "name": "Operations", "admins": [],
        "workers": [{"pc_id": 11, "hostname": "OPS-01"}, {"pc_id": 12, "hostname": "OPS-06"},
                    {"pc_id": 13, "hostname": "OPS-07"}],
    }])
    dept.setProperty("departmentId", 1)
    dept.setProperty("rollout", {"pcs_behind": [{"pc_id": 12, "escalated": False}]})
    dept.setProperty("violations", [{"found_on_pc_id": 13, "hostname": "OPS-07"}])

    state = {h["hostname"]: h["state"] for h in val(dept.property("fleet"))}
    assert state == {"OPS-01": "ok", "OPS-06": "warn", "OPS-07": "danger"}

    # a violation that arrives with only a hostname still marks its machine
    dept.setProperty("violations", [{"hostname": "OPS-01"}])
    assert {h["hostname"]: h["state"] for h in val(dept.property("fleet"))}["OPS-01"] == "danger"


def test_a_count_is_drawn_against_the_largest_department_not_itself(gui):
    """"7 of 7" compared a department with itself and said nothing. The brief reads against the
    biggest department there is, which is the settled rule for any count of one member of a set."""
    win, _, _ = gui
    dept = win.findChild(QObject, "departmentView")
    dept.setProperty("tree", [
        {"department_id": 1, "name": "Logistics", "admins": [],
         "workers": [{"pc_id": 1, "hostname": "LOG-01"}, {"pc_id": 2, "hostname": "LOG-02"}]},
        {"department_id": 2, "name": "Operations", "admins": [],
         "workers": [{"pc_id": i, "hostname": f"OPS-{i:02d}"} for i in range(10, 17)]},
    ])
    dept.setProperty("departmentId", 1)
    assert dept.property("biggestDept") == 7
    assert val(dept.property("fleetSays"))["brief"] == "2 of 7"
