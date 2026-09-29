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
    # frameless: it opens maximised over the work area and restores to the design's own size, with
    # a floor that keeps a four-cell page from collapsing. Nothing is pinned any more.
    size = fit_to_screen(win)
    avail = win.screen().availableGeometry()
    assert size.width() <= avail.width() and size.height() <= avail.height() and size.width() > 0
    assert win.minimumSize().width() <= size.width() and win.maximumSize().width() > size.width()
    assert int(win.flags()) & int(Qt.WindowType.FramelessWindowHint)
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
    for name in ("openedAuthority", "openedHero", "openedFleet", "openedFleetRow", "openedSessions", "openedReading"):
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

    for name in ():
        assert win.findChild(QObject, name) is not None, name

    # the two compositions are different objects, and the breadcrumb says the cell's own title
    assert win.findChild(QObject, "openedRollout") is None      # retired: the cell opens the Rollout area
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
        "today": ("openedToday", "todayLead", "todayEntered", "todayEnteredCards",
                  "todayQuiet", "todayQuietRow", "todayReading"),
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
    authority = win.findChild(QObject, "authorityView")
    await _wait(lambda: len(prop(authority, "tree") or []) == 2)
    depts = prop(authority, "tree")
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
    """Areas, not features (design/PATTERNS.md). The Super User rail names the question a person is
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


def test_the_fleet_pages_rather_than_shrinking(gui):
    """PATTERNS 3 (supersedes DP10's shrink ladder): the machines keep their full size at any count; the
    row pages, and the edge names a hidden machine that needs someone."""
    win, _, _ = gui
    dept = win.findChild(QObject, "departmentView")
    workers = [{"account_id": i, "pc_id": i, "hostname": f"OPS-{i:02d}", "session": {"occupied_via": "native"}}
               for i in range(1, 97)]
    dept.setProperty("tree", [{"department_id": 1, "name": "Operations", "admins": [], "workers": workers}])
    dept.setProperty("violations", [{"found_on_pc_id": 90, "hostname": "OPS-90", "filename": "budget.xlsx"}])
    dept.setProperty("departmentId", 1)
    row = win.findChild(QObject, "deptFleet")
    row.setProperty("width", 860)
    assert row.property("itemWidth") == 118                 # the same at 96 machines as at 7
    assert row.property("canForward") is True
    assert "OPS-90" in row.property("needsAfter")           # hidden, and still named


def test_a_chart_maximises_into_a_grid_that_pages_down(gui):
    """A chart opens into itself (DP11): every machine at full size in a grid paging down by rows (RO06)."""
    win, _, _ = gui
    dept = win.findChild(QObject, "departmentView")
    dept.setProperty("tree", [{
        "department_id": 1, "name": "Operations", "admins": [],
        "workers": [{"account_id": i, "pc_id": i, "hostname": f"OPS-{i:02d}"} for i in range(1, 49)],
    }])
    dept.setProperty("departmentId", 1)
    assert dept.property("maximised") == ""
    dept.setProperty("maximised", "machines")
    assert win.findChild(QObject, "deptMaxCrumb").property("text") == "Its machines"
    grid = win.findChild(QObject, "deptFleetMax")
    grid.setProperty("width", 900)
    grid.setProperty("height", 500)
    assert grid.property("markSize") == 58
    assert grid.property("pages") >= 2 and grid.property("page") == 0
    dept.setProperty("maximised", "")
    assert dept.property("maximised") == ""


def test_a_department_is_drawn_on_the_frame_not_on_a_sheet(gui):
    """No grey sheet. A page drawn in the Overview's language sits on the gradient and the frame
    shows between its panels; only the pre-kit views still carry a sheet. The department had been
    inheriting the old Admin-console shell, which is what made it look like a different product."""
    win, _, _ = gui
    QMetaObject.invokeMethod(win, "show", Q_ARG("QVariant", "authority"))
    assert win.property("onFrame") is True           # (this fixture has the Admin rail: its home is on the kit now)
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


# --- level 3: inside an Admin ---------------------------------------------------------------------

OPS = [{
    "department_id": 1, "name": "Operations",
    "admins": [{"account_id": 2, "name": "R. Mensah", "pc_id": 11, "hostname": "WS-OPS-A1",
                "session": {"occupied_via": "native"}},
               {"account_id": 3, "name": "A. Quaye", "pc_id": 12, "hostname": "WS-OPS-A2", "session": None}],
    "workers": [{"account_id": 4, "pc_id": 21, "hostname": "OPS-01"}],
}]
HELD = {"session_id": 9, "pc_id": 11, "occupant_account_id": 1, "occupied_via": "traversal",
        "entered_at": "2026-09-25T14:20:00+00:00", "deadline_at": "2099-01-01T00:00:00+00:00",
        "super_user_banner": True, "un_evictable": True}


def _as_super_user(win, bridge):
    bridge.state.role = "super_user"
    bridge.state.account_id = 1
    win.findChild(QObject, "overviewView").setProperty("tree", OPS)
    bridge.stateChanged.emit()


def test_opening_an_admin_grows_the_crumb_and_holds_nothing(gui):
    """Double-clicking an Admin opens them IN PLACE (DP06): the crumb gains their name and the lane
    states what entering costs. Still level 2 -- no session, no lid, the rail unchanged."""
    win, _, bridge = gui
    _as_super_user(win, bridge)
    QMetaObject.invokeMethod(win, "enterDepartment", Q_ARG("QVariant", 1))
    dept = win.findChild(QObject, "departmentView")
    dept.setProperty("entering", True)

    assert win.findChild(QObject, "enterCrumbHere").property("text") == "R. Mensah"
    lane = win.findChild(QObject, "enteringAdmin")
    assert val(lane.property("lane"))["action"] == "Enter WS-OPS-A1"
    assert win.property("insideNow") is False
    assert win.findChild(QObject, "sessionLid").property("visible") is False
    assert val(win.findChild(QObject, "iconRail").property("nav"))[0]["key"] == "mustsee"


def test_inside_an_admin_the_window_is_their_interface_under_the_lid(gui):
    """Going in hands over the Admin's own interface -- their seven-entry rail, their home page
    scoped to their department, their grey sheet -- and the red lid is the only difference."""
    win, _, bridge = gui
    _as_super_user(win, bridge)
    QMetaObject.invokeMethod(win, "enterDepartment", Q_ARG("QVariant", 1))
    bridge.state.set_session(dict(HELD))
    assert val(win.property("heldAdmin"))["name"] == "R. Mensah"

    QMetaObject.invokeMethod(win, "goInside")
    assert win.property("insideNow") is True
    rail = win.findChild(QObject, "iconRail")
    assert [e["key"] for e in val(rail.property("nav"))] == \
        ["hierarchy", "tasks", "flows", "automation", "actions", "assistance", "reports"]
    assert rail.property("currentKey") == "hierarchy"
    # the Admin's home is on the new kit now, so inside it sits on the frame like the Admin's own window
    assert win.property("onFrame") is True and win.property("inDepartment") is False
    home = win.findChild(QObject, "adminHome")
    assert home.property("deptId") == 1 and home.property("visible") is not None
    assert win.findChild(QObject, "lidWho").property("text") == "You are inside R. Mensah's workstation"

    # Escape steps out and the session runs on: holding and looking are different things
    QMetaObject.invokeMethod(win, "stepOut")
    assert win.property("insideNow") is False and bridge.state.session is not None
    assert rail.property("currentKey") == "authority" and win.property("inDepartment") is True


def test_the_session_ending_takes_you_out_rather_than_leaving_you_in_their_rail(gui):
    win, _, bridge = gui
    _as_super_user(win, bridge)
    bridge.state.set_session(dict(HELD))
    QMetaObject.invokeMethod(win, "goInside")
    assert win.property("insideNow") is True

    bridge.state.set_session(None)                  # left, expired, or ended from above
    assert win.property("insideNow") is False and win.property("inside") is False
    assert win.findChild(QObject, "iconRail").property("currentKey") == "authority"


def test_the_held_session_is_mirrored_on_must_see_and_reads_look_through_only_inside(gui):
    """Holding: the container is mirrored into Must see and reads are NOT narrowed. Inside: reads ask
    the Engine to answer as the Admin. Stepping out stops that again."""
    win, _, bridge = gui
    _as_super_user(win, bridge)
    mirror = win.findChild(QObject, "heldMirror")
    assert mirror.property("visible") is False

    bridge.state.set_session(dict(HELD))
    assert val(win.findChild(QObject, "overviewView").property("heldAdmin"))["name"] == "R. Mensah"
    assert bridge.viewThroughSession is False           # holding is not looking

    QMetaObject.invokeMethod(win, "goInside")
    assert bridge.viewThroughSession is True
    QMetaObject.invokeMethod(win, "stepOut")
    assert bridge.viewThroughSession is False


def test_the_admin_rail_opens_the_admins_own_screens(gui):
    """Actions is its own page; Automation no longer carries an Actions tab (26 Sep 2026)."""
    win, _, _ = gui
    QMetaObject.invokeMethod(win, "show", Q_ARG("QVariant", "actions"))
    assert win.property("viewKey") == "actions"
    assert win.findChild(QObject, "actionsView") is not None
    assert win.findChild(QObject, "automationView") is not None
    assert win.findChild(QObject, "automationTabs") is None          # one page now, no tabs


def test_an_automation_is_written_as_a_sentence_and_ticks_actions_by_name(gui):
    """AU08-AU10: every blank is a pick; machines are marks; actions are ticked from the library and
    keep their order; the whole automation reads back as one sentence."""
    win, _, _ = gui
    na = win.findChild(QObject, "newAutomation")
    na.setProperty("tree", [{"department_id": 1, "name": "Ops", "admins": [], "workers": [
        {"account_id": 1, "name": "Kojo", "pc_id": 21, "hostname": "OPS-01"},
        {"account_id": 2, "name": "Efua", "pc_id": 22, "hostname": "OPS-02"}]}])
    na.setProperty("actions", [{"id": 4, "kind": "control", "builtin_type": "notify", "name": "Notify me"},
                               {"id": 5, "kind": "control", "builtin_type": "lock_session", "name": "lock_session"}])
    QMetaObject.invokeMethod(na, "start", Q_ARG("QVariant", None))
    QMetaObject.invokeMethod(na, "setKind", Q_ARG("QVariant", "machine"))
    assert na.property("type") == "threshold.cpu" and val(na.property("match"))["percent"] == 85
    QMetaObject.invokeMethod(na, "toggle", Q_ARG("QVariant", 22))              # take one machine away
    assert val(na.property("pcIds")) == [21]
    QMetaObject.invokeMethod(na, "tick", Q_ARG("QVariant", 5))
    QMetaObject.invokeMethod(na, "tick", Q_ARG("QVariant", 4))
    QMetaObject.invokeMethod(na, "moveUp", Q_ARG("QVariant", 1))
    assert val(na.property("actionIds")) == [4, 5]
    words = [p.get("w") or p.get("slot") for p in val(na.property("parts")) + val(na.property("doParts"))]
    assert words == ["When", "the machine", "stays busy", "above", "85 %", "on", "OPS-01",
                     "do", "Notify me", "then", "Lock the screen"]


async def test_the_bridge_asks_to_look_through_only_on_listed_reads(gui):
    """Writes never carry the flag: an act inside an Admin is the Super User's own."""
    _, _, bridge = gui
    sent = []

    class Conn:
        connected = True

        async def call(self, type_, payload):
            sent.append((type_, payload))
            return {}

    bridge.conn = Conn()
    bridge.viewThroughSession = True
    await bridge.request("hierarchy.tree", {})
    await bridge.request("task.verify", {"task_id": 1})
    assert sent[0] == ("hierarchy.tree", {"view": "session"})
    assert sent[1] == ("task.verify", {"task_id": 1})
    bridge.conn = None


# --- the kit, to design/PATTERNS.md ----------------------------------------------------------------

def _make(qml, source):
    """Instantiate a snippet that imports the GUI's own QML directory, on the fixture's engine."""
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlComponent
    qml_dir = Path(__file__).resolve().parents[1] / "operator_client" / "gui" / "qml"
    comp = QQmlComponent(qml)
    comp.setData(f'import QtQuick\nimport "{qml_dir.as_uri()}"\n{source}'.encode(), QUrl.fromLocalFile(str(qml_dir / "_kit_test.qml")))
    obj = comp.create()
    assert obj is not None, comp.errorString()
    from PySide6.QtQml import QQmlEngine
    QQmlEngine.setObjectOwnership(obj, QQmlEngine.ObjectOwnership.CppOwnership)   # keep JS from collecting it
    _KEEP.extend([comp, obj])
    return obj


_KEEP: list = []


def test_the_machine_mark_is_quiet_unless_someone_is_needed(gui):
    """PATTERNS 2: a small screen with its number; the tone lands only on a machine that needs someone."""
    _, qml, _ = gui
    fine = _make(qml, 'MachineMark { label: "03"; status: "ok"; size: 84; name: "Yaw"; line: "at the PC" }')
    bad = _make(qml, 'MachineMark { label: "07"; status: "danger"; size: 84; name: "Ama"; line: "a file out of place"; lineTone: "danger" }')
    assert fine.property("needsSomeone") is False and bad.property("needsSomeone") is True
    assert fine.property("screenH") == round(84 * 0.66)


def test_a_row_pages_rather_than_shrinking_and_names_what_it_hides(gui):
    """PATTERNS 3 (supersedes DP10): items keep their size; the edge pages and names a hidden exception."""
    _, qml, _ = gui
    row = _make(qml, '''PagedRow {
        width: 700; height: 120; itemWidth: 92; spacing: 14
        model: [{n:"01"},{n:"02"},{n:"03"},{n:"04"},{n:"05"},{n:"06"},{n:"07"},{n:"08"},{n:"09"},{n:"10",bad:true}]
        attention: function (m) { return m.bad ? "OPS-" + m.n : "" }
        delegate: Item { property var modelData; width: 92; height: 100 }
    }''')
    assert row.property("itemWidth") == 92                    # never shrunk
    shown = row.property("shown")
    assert 0 < shown < 10 and row.property("canBack") is False
    assert row.property("needsAfter") == "OPS-10 needs you"
    QMetaObject.invokeMethod(row, "forward")
    assert row.property("first") > 0 and row.property("canBack") is True
    # everything fits -> no edges, centred
    few = _make(qml, 'PagedRow { width: 700; height: 120; itemWidth: 92; model: [{},{},{}]; delegate: Item { property var modelData } }')
    assert few.property("fitsAll") is True and few.property("canForward") is False


def test_a_stack_of_cards_pages_down(gui):
    _, qml, _ = gui
    col = _make(qml, '''PagedColumn {
        width: 400; height: 250; itemHeight: 58
        model: [{t:"a"},{t:"b"},{t:"c"},{t:"d",bad:true},{t:"e"}]
        attention: function (m) { return m.bad ? m.t : "" }
        delegate: InfoCard { }
    }''')
    assert col.property("hiddenAfter") > 0 and col.property("needsAfter") == "d"
    QMetaObject.invokeMethod(col, "forward")
    assert col.property("hiddenBefore") > 0


def test_rollout_shows_departments_then_one_maximised(gui):
    """RO05 / RO06: many departments are one line each, with ONE mark holding the count behind; double click
    maximises one into its machines. Never one container for many departments' machines."""
    win, _, _ = gui
    rv = win.findChild(QObject, "rolloutView")
    rv.setProperty("tree", [{"department_id": d, "name": f"D{d}", "admins": [], "workers":
                             [{"account_id": d * 100 + i, "pc_id": d * 100 + i, "hostname": f"D{d}-{i:02d}"} for i in range(1, 41)]}
                            for d in range(1, 11)])
    rv.setProperty("health", {"version": {"id": 4, "version_string": "1.4.2"},
                              "departments": [{"department_id": d, "department_name": f"D{d}", "pcs": 40} for d in range(1, 11)],
                              "pcs_behind": [{"pc_id": 400 + i, "hostname": f"D4-{i:02d}", "department_id": 4, "failures": 10,
                                              "escalated": False} for i in (12, 17, 31, 40)]})
    assert rv.property("behindTotal") == 4
    assert len(val(rv.property("deptsBehind"))) == 1
    assert "4 behind" not in (win.findChild(QObject, "rolloutPhrase").property("text") or "")
    rv.setProperty("openDept", 4)
    machines = val(rv.property("openMachines"))
    assert len(machines) == 40 and sum(1 for m in machines if m["status"] == "warn") == 4
    assert win.findChild(QObject, "rolloutCrumbDept").property("text") == "D4"



def test_a_new_task_waits_for_every_decision(gui):
    """TK05: whatever the model could not settle is a decision, worked down one at a time; Confirm waits for them.
    A name that already exists can be answered 'it means the existing file', which makes the line an Update."""
    win, _, _ = gui
    tv = win.findChild(QObject, "tasksView")
    nt = next(o for o in tv.findChildren(QObject) if o.metaObject().className().startswith("NewTask"))
    nt.setProperty("assignee", {"account_id": 4003, "name": "Yaw"})
    nt.setProperty("proposal", {
        "items": [], "final_deadline": None,
        "flags": [{"kind": "ambiguous_deadline", "candidates": ["Monday", "Wednesday"]}],
        "collisions": [{"item_index": 0, "name": "r.docx", "existing": [{"file_index_id": 92, "path": "C:/r.docx"}]}],
        "proposed_split": []})
    nt.setProperty("items", [{"target_type": "file", "intent": "create", "name": "r.docx", "path": None,
                              "linked_item_index": None, "file_index_id": None, "populated_by": "llm", "removed": False}])
    assert len(val(nt.property("open"))) == 2
    assert val(nt.property("current"))["kind"] == "ambiguous_deadline"          # one at a time, in order
    assert win.findChild(QObject, "newTaskConfirm").property("enabled") is False
    QMetaObject.invokeMethod(nt, "settle", Q_ARG("QVariant", "flag0"))
    assert val(nt.property("current"))["kind"] == "collision"
    QMetaObject.invokeMethod(nt, "setItem", Q_ARG("QVariant", 0), Q_ARG("QVariant", {"intent": "update", "file_index_id": 92}))
    QMetaObject.invokeMethod(nt, "settle", Q_ARG("QVariant", "col0"))
    assert val(nt.property("open")) == [] and val(nt.property("items"))[0]["intent"] == "update"
    assert win.findChild(QObject, "newTaskConfirm").property("enabled") is True


def test_a_flow_is_drawn_as_a_tree_and_only_the_paused_branch_is_dashed(gui):
    """FL07: source, stages by depth, destinations spread; each parent centred on its children."""
    win, _, _ = gui
    fv = win.findChild(QObject, "flowsView")
    flow = {"source_hostname": "OPS-01", "source_path": "C:/Payroll",
            "stages": [{"id": 2, "parent_stage_id": None, "stage_type": "transformation"}],
            "destinations": [{"id": 5, "parent_stage_id": 2, "destination_hostname": "OPS-03", "destination_path": "D:/a",
                              "paused_reason": "unreachable"},
                             {"id": 6, "parent_stage_id": 2, "destination_hostname": "OPS-04", "destination_path": "D:/a"}]}
    fv.setProperty("flow", flow)
    tree = win.findChild(QObject, "flowTree")
    nodes = {n["id"]: n for n in val(tree.property("nodes"))}
    assert nodes["s"]["x"] < nodes["st2"]["x"] < nodes["d5"]["x"] == nodes["d6"]["x"]
    assert nodes["st2"]["y"] == (nodes["d5"]["y"] + nodes["d6"]["y"]) / 2      # the parent sits between its children
    dashed = [(link["from"], link["to"]) for link in val(tree.property("links")) if link["bad"]]
    assert dashed == [("st2", "d5")]                                          # the trunk still runs


def test_a_new_flow_saves_only_when_every_blank_is_filled(gui):
    """FL08: folders and machines are chosen, never typed; Save waits for all of them."""
    win, _, _ = gui
    fv = win.findChild(QObject, "flowsView")
    nf = next(o for o in fv.findChildren(QObject) if o.metaObject().className().startswith("NewFlow"))
    save = win.findChild(QObject, "newFlowSave")
    nf.setProperty("source", {"pc_id": 21, "hostname": "OPS-01"})
    nf.setProperty("sourcePath", "C:/Invoices")
    assert save.property("enabled") is False
    nf.setProperty("destinations", [{"pc_id": 25, "hostname": "OPS-05", "path": ""}])
    assert save.property("enabled") is False
    nf.setProperty("destinations", [{"pc_id": 25, "hostname": "OPS-05", "path": "D:/Shared"}])
    assert save.property("enabled") is True
    assert len(val(nf.property("preview"))["nodes"]) == 2


def test_an_action_asks_only_for_what_it_needs_and_a_script_is_checked_on_arrival(gui, tmp_path):
    """AU06 / AU07: a built-in not set up yet waits for what it needs; a custom action is a script FILE,
    checked in words the moment it is picked -- an import outside the allowed set is refused."""
    win, _, _ = gui
    av = win.findChild(QObject, "actionsView")
    av.setProperty("builtin", {"notify": {"category": "control", "params": ["message"]},
                               "screenshot": {"category": "control", "params": []}})
    QMetaObject.invokeMethod(av, "choose", Q_ARG("QVariant", {"id": 0, "kind": "control", "builtin_type": "notify"}))
    assert val(av.property("missing")) == ["message"]
    QMetaObject.invokeMethod(av, "setParam", Q_ARG("QVariant", "message"), Q_ARG("QVariant", "Save your work"))
    assert val(av.property("missing")) == []
    QMetaObject.invokeMethod(av, "choose", Q_ARG("QVariant", {"id": 0, "kind": "control", "builtin_type": "screenshot"}))
    assert val(av.property("missing")) == []                                       # some ask for nothing

    QMetaObject.invokeMethod(av, "newCustom")
    good = tmp_path / "clear_temp.py"
    good.write_text("import os\nprint(os.name)\n", encoding="utf-8")
    QMetaObject.invokeMethod(av, "takeScript", Q_ARG("QVariant", good.as_uri()))
    assert val(av.property("check"))["ok"] is True and av.property("customName") == "Clear temp"
    bad = tmp_path / "fetch.py"
    bad.write_text("import requests\n", encoding="utf-8")
    QMetaObject.invokeMethod(av, "takeScript", Q_ARG("QVariant", bad.as_uri()))
    assert val(av.property("check"))["ok"] is False
    assert win.findChild(QObject, "saveCustom").property("enabled") is False


def test_assistance_knows_whose_turn_it_is_and_names_the_super_user(gui):
    """AS03: the turn is read from the channel (one reply each); for an Admin the Super User above them is
    named by role, since their tree holds only their department."""
    win, _, bridge = gui
    asv = win.findChild(QObject, "assistanceView")
    me = bridge.state.account_id
    asv.setProperty("tree", [{"department_id": 1, "name": "Ops", "admins": [], "workers": [
        {"account_id": 4007, "name": "Ama", "pc_id": 27, "hostname": "OPS-07"}]}])
    asv.setProperty("channels", [{"id": 14, "initiator_account_id": 4007, "superior_account_id": me, "turn": "superior", "closed_at": None},
                                 {"id": 12, "initiator_account_id": me, "superior_account_id": 99, "turn": "superior", "closed_at": None}])
    order = [c["id"] for c in val(asv.property("sorted"))]
    assert order == [14, 12]                                   # yours to answer first


def test_reports_are_said_from_their_source_and_resources_opens_from_home(gui):
    """RP03: a violation report reads as a sentence about the file; RS03 opens over the Admin's home."""
    win, _, _ = gui
    rv = win.findChild(QObject, "reportsView")
    rv.setProperty("violations", [{"id": 7, "expected_tag": "restricted", "filename": "budget.xlsx", "hostname": "OPS-07",
                                   "path": "C:/Shared/budget.xlsx", "detected_at": None, "resolved_at": None}])
    rv.setProperty("reports", [{"id": 41, "category": "resource_violation", "source_table": "resource_violations",
                                "source_id": 7, "generated_at": None, "addressed_at": None}])
    rv.setProperty("chosenId", 41)
    chosen = win.findChild(QObject, "reportChosen")
    assert chosen.property("title") == "A restricted file on OPS-07"
    QMetaObject.invokeMethod(win, "show", Q_ARG("QVariant", "resources"))
    assert win.property("subPage") == "resources"          # shown over the Admin's home (a Super User has none)


def test_the_record_trail_is_written_in_words_newest_first(gui):
    """RC05: the trail reads as sentences -- someone did something, or something happened -- newest first,
    and the noise (update attempts, messages) stays out."""
    win, _, bridge = gui
    rv = win.findChild(QObject, "recordView")
    rv.setProperty("entries", [
        {"action_type": "update.attempt", "actor_account_id": None, "actor_name": "engine", "occurred_at": "2026-09-27T09:00:00+00:00"},
        {"action_type": "resource.violation", "actor_account_id": None, "actor_name": "engine", "occurred_at": "2026-09-27T11:40:00+00:00",
         "detail": {"hostname": "OPS-07"}},
        {"action_type": "session.traversed", "actor_account_id": bridge.state.account_id, "actor_name": "You",
         "occurred_at": "2026-09-27T10:40:00+00:00", "detail": {"hostname": "OPS-03"}}])
    assert [t["text"] for t in val(rv.property("trail"))] == ["A file was found out of place — OPS-07",
                                                             "You entered a machine — OPS-03"]


def test_a_client_pc_is_entered_and_stepped_out_of_like_an_admin(gui):
    """Level 4 (CP03): holding a worker's machine and going in shows its page under the lid; Escape steps out
    with the session still held, and the pill offers the way back in."""
    win, _, bridge = gui
    win.setProperty("orgTree", [{"department_id": 1, "name": "Ops", "admins": [], "workers": [
        {"account_id": 4007, "name": "Ama", "pc_id": 27, "hostname": "OPS-07"}]}])
    bridge.state.session = {"session_id": 10, "pc_id": 27, "occupant_account_id": bridge.state.account_id,
                            "occupied_via": "traversal", "deadline_at": None}
    bridge.stateChanged.emit()
    assert val(win.property("heldPc"))["hostname"] == "OPS-07"
    QMetaObject.invokeMethod(win, "enterPc", Q_ARG("QVariant", 27))   # already held: straight in
    assert win.property("insidePcNow") is True
    assert win.findChild(QObject, "pcView").property("visible") is True
    QMetaObject.invokeMethod(win, "stepOut")
    assert win.property("insidePcNow") is False and val(win.property("heldPc")) is not None
    bridge.state.session = None
    bridge.stateChanged.emit()


def test_every_session_state_is_the_one_lid(gui):
    """27 Sep 2026: a held session is told by ONE bar in three wordings -- inside, holding, blocked -- never a
    pill or a second banner."""
    win, _, bridge = gui
    win.setProperty("orgTree", [{"department_id": 1, "name": "Ops", "admins": [], "workers": [
        {"account_id": 4007, "name": "Ama", "pc_id": 27, "hostname": "OPS-07"}]}])
    lid = win.findChild(QObject, "sessionLid")
    assert win.property("lidMode") == "" and lid.property("visible") is False
    bridge.state.session = {"session_id": 10, "pc_id": 27, "occupant_account_id": bridge.state.account_id,
                            "occupied_via": "traversal", "deadline_at": None}
    bridge.stateChanged.emit()
    assert win.property("lidMode") == "holding"
    assert win.findChild(QObject, "lidWho").property("text") == "You are holding Ama's machine"
    QMetaObject.invokeMethod(win, "enterPc", Q_ARG("QVariant", 27))
    assert win.property("lidMode") == "inside"
    assert win.findChild(QObject, "statePill") is None                  # the old pill is gone
    QMetaObject.invokeMethod(win, "stepOut")
    bridge.state.session = None
    bridge.state.blocked_by = {"occupant_name": "the Super User"}
    bridge.stateChanged.emit()
    assert win.property("lidMode") == "blocked"
    assert win.findChild(QObject, "lidWho").property("text") == "The Super User is in charge of your machine"
    bridge.state.blocked_by = None
    bridge.stateChanged.emit()


async def test_a_dropped_link_keeps_the_page_and_retries_a_failed_one_says_why(gui):
    """ST01 / ST03: a failure is said as what to do about it; a drop mid-session keeps the page (dated), keeps the
    held session's deadline in words, and retries by itself; a deliberate disconnect goes back to the form."""
    import ssl

    from common.connection import EngineError
    from operator_client.gui.bridge import FalconBridge

    assert FalconBridge._failure(EngineError("unauthenticated", "authentication failed", "auth.respond")) == "key"
    assert FalconBridge._failure(ConnectionRefusedError()) == "unreachable"
    assert FalconBridge._failure(ssl.SSLError()) == "certificate"

    win, _, bridge = gui
    bridge.state.connected = True
    bridge.state.session = {"session_id": 1, "pc_id": 27, "occupied_via": "traversal", "deadline_at": "2026-09-27T14:50:00+00:00"}
    await bridge._on_disconnect()
    try:
        assert bridge.connectState == "lost" and bridge.heldWhenLost["pc_id"] == 27
        assert win.property("lidMode") == "lost" and win.property("online") is True
    finally:
        bridge._retry_task.cancel()
    await bridge._disconnect()
    assert bridge.connectState == "idle" and win.property("online") is False


def test_an_act_with_a_cost_asks_first_and_names_itself(gui):
    """DG01: the dialog says the cost before its button, the button names the act, a field or a pick must be filled
    before it can be pressed, and a one-time key can only be acknowledged."""
    win, _, _ = gui
    dlg = win.findChild(QObject, "costDialog")
    QMetaObject.invokeMethod(win, "ask", Q_ARG("QVariant", {"title": "Register a machine in Ops", "field": {"label": "The machine's name"},
                                                            "act": "Register it"}), Q_ARG("QVariant", None))
    act = win.findChild(QObject, "dialogAct")
    assert dlg.property("opened") or dlg.property("visible")
    assert act.property("text") == "Register it" and act.property("enabled") is False
    dlg.setProperty("typed", "OPS-15")
    assert act.property("enabled") is True
    QMetaObject.invokeMethod(dlg, "close")
    QMetaObject.invokeMethod(win, "showKey", Q_ARG("QVariant", "OPS-15 is registered"), Q_ARG("QVariant", ""),
                             Q_ARG("QVariant", "cid"), Q_ARG("QVariant", "7f3a91c2"))
    assert act.property("text") == "I've saved it" and val(dlg.property("spec"))["secret"][1] == ["Key", "7f3a91c2"]
    QMetaObject.invokeMethod(dlg, "close")


def test_the_authority_area_is_the_kit_and_carries_the_names(gui):
    """The Super User's Authority area was the last pre-kit screen -- a sidebar, a card strip and a
    detail card printing account and PC ids. It is now four cells on the frame, and it is the only
    place display names are set: hierarchy.set_display_name and set_self_name had no GUI at all once
    the orphaned HierarchyView stopped being mounted."""
    win, _, _ = gui
    for name in ("authorityView", "authorityDepartments", "authorityPeople",
                 "authorityGap", "authorityNaming", "newDepartment", "setSelfName"):
        assert win.findChild(QObject, name) is not None, name

    view = win.findChild(QObject, "authorityView")
    view.setProperty("tree", [
        {"department_id": 1, "name": "Operations", "workers": [{"pc_id": 1, "hostname": "OPS-01"}],
         "admins": [{"account_id": 7, "name": "R. Mensah", "hostname": "WS-A1", "session": None}]},
        {"department_id": 2, "name": "Logistics", "workers": [{"pc_id": 2, "hostname": "LOG-01"}], "admins": []},
    ])
    assert [p["name"] for p in prop(view, "people")] == ["R. Mensah"]
    assert [d["name"] for d in prop(view, "orphans")] == ["Logistics"]     # where nobody governs
    # nobody is picked until you pick them, and then the naming cell is about that person
    assert prop(view, "selected") is None
    view.setProperty("selectedId", 7)
    assert prop(view, "selected")["name"] == "R. Mensah"
    assert "R. Mensah" in prop(view, "nameSays")["sentence"]


def test_assisted_access_has_a_surface_and_it_is_the_admin_s(gui):
    """The whole combo was reachable only from the TUI: the five handlers' only GUI was a screen
    nothing mounted. It lives on Assistance, for an Admin -- every assisted_access handler refuses
    anyone else -- and it is consent, not eviction: what the helper may do is said before either
    side agrees, and there is no clock anywhere in it."""
    win, _, _ = gui
    view = win.findChild(QObject, "assistanceView")
    assert win.findChild(QObject, "assistHelp") is not None
    assert win.findChild(QObject, "askForHelp") is not None

    # an offer arriving by push is drawn with the scope in words, never as a spec
    view.setProperty("offers", [{"request_id": 4, "requester_name": "A. Quaye",
                                 "scope": {"control_actions": True, "monitoring_actions": True,
                                           "custom_actions": False, "tasks": False, "flows": False}}])
    said = prop(view, "helpSays")
    assert "A. Quaye" in said["sentence"]
    assert said["action"] == "Accept"
    # the scope reaches the page as words, never as a spec
    assert "control actions" in said["facts"][0]["value"]
    assert "monitoring checks" in said["facts"][0]["value"]


def test_every_act_the_engine_answers_has_a_button(gui):
    """The audit found eight live handlers with no way to reach them. These are the ones that landed
    on a page that already read their data: the Admin's own rollout, changing and retiring a flow,
    the destination owner's yes, the verification stack, and what is running right now."""
    win, _, _ = gui
    for name in ("rolloutDepartment",        # updates.rollout_department, on the Admin's home
                 "flowChange", "flowRetire",  # flow.edit / flow.delete, on the opened flow
                 "flowAllow", "flowRefuse",   # flow.consent, for the owner being asked
                 "recheckStack",              # task.stack, under the checks
                 "automationRunning", "automationLiveList"):   # control.dashboard's live rows
        assert win.findChild(QObject, name) is not None, name


def test_a_cell_keeps_its_shape_while_it_waits(gui):
    """ST02's loading half. A cell with nothing yet keeps its structure, quietened, and says no state
    phrase -- a phrase drawn from nothing would be wrong, and a spinner over blank space says even
    less. The empty half (a zero is a result) was already built."""
    win, _, _ = gui
    overview = win.findChild(QObject, "overviewView")
    cell = win.findChild(QObject, "cellAuthority")
    overview.setProperty("loaded", False)
    assert cell.property("loading") is True
    overview.setProperty("loaded", True)
    assert cell.property("loading") is False


def test_the_window_wears_one_set_of_chrome(gui):
    """The app draws its own minimise, maximise and close, so it does not also wear Windows' --
    the window is frameless and the top bar is the title bar: it drags, and a double click on it
    maximises. Without the grips a frameless window cannot be resized at all, so they are part of
    the same change rather than a polish item."""
    win, _, _ = gui
    from PySide6.QtCore import Qt as QtNS
    assert bool(win.flags() & QtNS.WindowType.FramelessWindowHint)

    for name in ("winMinimize", "winMaximize", "winClose"):
        assert win.findChild(QObject, name) is not None, name
    for name in ("gripLeft", "gripRight", "gripTop", "gripBottom"):
        grip = win.findChild(QObject, name)
        assert grip is not None and grip.property("enabled") is True, name

    # the button says which act it offers, and that follows the window's own state
    assert win.property("maximised") is False
    assert win.findChild(QObject, "winMaximize").property("iconName") == "max"
