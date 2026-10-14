"""The console, built to the published concept: the shell at both levels, every page loading clean, and
the pages that turn what the Engine answers into something a person reads.

Runs offscreen on pytest-asyncio's loop; skipped without PySide6. The Engine is not needed -- the
bridge's connection is the only thing faked, exactly as `scripts/preview.py` does it.
"""

from __future__ import annotations

import asyncio
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
os.environ["QT_QPA_PLATFORM"] = "offscreen"

from PySide6.QtCore import Q_ARG, QCoreApplication, QMetaObject, QObject, Qt
from PySide6.QtQml import QJSValue

from operator_client.core import LocalConfig
from operator_client.gui.app import QML_DIR, create


def _ago(hours: float) -> str:
    return (datetime.now(timezone.utc) - timedelta(hours=hours)).isoformat()


TREE = [
    {"department_id": 1, "name": "Operations", "admins": [{"account_id": 7, "name": "R. Mensah", "online": True}],
     "workers": [{"pc_id": 1, "account_id": 21, "hostname": "OPS-01", "name": "Kojo", "session": {"occupied_via": "native"}},
                 {"pc_id": 2, "account_id": 22, "hostname": "OPS-02", "name": "Efua", "session": None}]},
    {"department_id": 2, "name": "Logistics", "admins": [],
     "workers": [{"pc_id": 3, "account_id": 23, "hostname": "LOG-01", "name": "Esi", "session": None}]},
]

DEVIATIONS = [
    {"id": 87, "expectation": "account_bound_to_one_pc", "observed_pc_id": 1, "observed_account_id": 21,
     "detail": {"expected_hostname": "OPS-01", "announced_hostname": "WS-OPS-01"}, "surfaced_to_account_id": 21,
     "resolved_at": None, "detected_at": _ago(2)},
    {"id": 80, "expectation": "account_bound_to_one_pc", "observed_pc_id": 2, "observed_account_id": 22,
     "detail": {"expected_hostname": "OPS-02", "announced_hostname": "OPS-02-OLD"}, "surfaced_to_account_id": 22,
     "resolved_at": _ago(20), "detected_at": _ago(30)},
]

# As `registry.refused` answers: one row per who tried and from where, with why and what to do.
REFUSED = [
    {"id": "door:10.20.9.201:abc", "address": "10.20.9.201", "client_id": "abc", "kind": "wrong_key", "why": "wrong key for OPS-01", "tone": "bad", "advice": "rekey",
     "tries": 2, "last": _ago(1), "first": _ago(3), "pc_id": 1, "machine": "OPS-01", "host": "Claims to be OPS-01", "blocked": False, "say": "Give it its key again."},
    {"id": "door:10.20.6.40:zzz", "address": "10.20.6.40", "client_id": "zzz", "kind": "unknown", "why": "not registered", "tone": "wait", "advice": "register",
     "tries": 1, "last": _ago(2), "first": _ago(2), "pc_id": None, "machine": None, "host": "zzz", "blocked": False, "say": "Register it."},
]


ISSUE = {"id": 41, "code": "I-41", "type": "file", "severity": "critical", "title": "Restricted file copied where it isn't allowed",
         "subject": "budget-2026.xlsx", "pc_id": 1, "host": "OPS-01", "department_id": 1, "opened_at": _ago(2), "past_target": True,
         "owner": {"account_id": 7, "name": "R. Mensah", "you": True}, "state": "open", "label": "Open", "escalated": False}


# A flow as `flow.list` answers it: stages and destinations point at their parent stage by id. Stage 1 is what an
# earlier edit left on record (nothing reaches it); 2 is before the split, 3 is on the branch to the archive only.
FLOW = {"id": 5, "source_pc_id": 7, "source_hostname": "OPS-07", "source_path": "C:/reports/weekly", "status": "active",
        "pause_reason": None, "consent_status": "not_required", "created_by_account_id": 7,
        "stages": [{"id": 1, "parent_stage_id": None, "stage_type": "transformation", "config": None},
                   {"id": 2, "parent_stage_id": None, "stage_type": "categorization", "config": {"op": "Sort by file type", "by": "extension"}},
                   {"id": 3, "parent_stage_id": 2, "stage_type": "transformation", "config": {"op": "Compress to ZIP"}}],
        "destinations": [{"id": 8, "destination_pc_id": 21, "destination_hostname": "LOG-01", "destination_path": "D:/weekly", "parent_stage_id": 2},
                         {"id": 9, "destination_pc_id": 22, "destination_hostname": "LOG-02", "destination_path": "D:/archive", "parent_stage_id": 3}]}


# As `assistance.ping_status` answers: one row per ping, oldest first.
PINGS = [{"id": 5, "sender_account_id": 21, "receiver_account_id": 7, "from_name": "Kojo", "sent_at": _ago(3), "addressed_at": None},
         {"id": 9, "sender_account_id": 21, "receiver_account_id": 7, "from_name": "Kojo", "sent_at": _ago(1), "addressed_at": None}]


# As `reports.board` answers: each report says whose it is.
BOARD = [{"id": 40, "category": "update_status", "label": "Update stuck", "summary": "LOG-02 past the limit", "at": _ago(5), "pc_id": 22, "host": "LOG-02",
          "department_id": 3, "department_name": "Logistics", "owner": "noadmin", "seen": False, "addressed": None},
         {"id": 41, "category": "resource_violation", "label": "Restricted file", "summary": "A copy on OPS-07", "at": _ago(2), "pc_id": 7, "host": "OPS-07",
          "department_id": 1, "department_name": "Operations", "owner": "dept", "seen": False,
          "addressed": {"by": "R. Mensah", "at": _ago(1), "took_minutes": 42}}]


def _dev(i: int, outcome: str, hours: float, expected: str, happened: str) -> dict:
    """A deviation as `deviations.list` answers it: pointed at its rule, with who or what it concerns."""
    return {"id": i, "code": f"D-{i}", "rule": {"id": 4, "code": "B-4", "name": "A machine's certificate matches its name", "locked": True},
            "severity": "medium", "kind": "pc", "kind_label": "PC", "who": "OPS-01", "who_sub": "Operations", "department_id": 1,
            "department_name": "Operations", "pc_id": 1, "host": "OPS-01", "at": _ago(hours), "short": "OPS-01 presented another name",
            "expected": expected, "happened": happened, "outcome": outcome, "note": None if outcome == "open" else "Renamed back.", "by": None, "decided_at": None}


DEVS = [_dev(87, "open", 2, "The certificate names OPS-01", "The certificate names WS-OPS-01"),
        _dev(80, "explained", 30, "The certificate names OPS-01", "The certificate names OPS-01-OLD")]


# As `rules.list` answers: an organisation-wide rule of the Super User's.
RULE = {"id": 5, "code": "O-5", "name": "Unanswered help request", "shape": "follow", "locked": False, "on": True,
        "spec": {"trigger": "help", "expect": "answer", "within": 60, "who": "admins", "depts": "all", "severity": "medium",
                 "resp": {"report": True, "admin": True, "action": False}},
        "sentence": "A worker pings for help, then an Admin answers the ping within 1 hour.", "scope": "Admins, every department",
        "set_by": "You", "since": _ago(200), "deviations_this_week": 1, "open_this_week": 1}


class _Identity:
    """What the handshake returned. The role is the whole point: the console is a different product at
    each level, so a test has to say which one it is looking at."""

    client_id, account_id, pc_id, department_id = "test", 7, 101, 1

    def __init__(self, role: str = "admin") -> None:
        self.role = role
        if role == "super_user":
            self.account_id, self.pc_id, self.department_id = 1, 100, None


class _Connection:
    connected = True

    def __init__(self) -> None:
        self.seen: list[tuple[str, dict]] = []

    async def call(self, type_: str, payload: dict) -> dict:
        await asyncio.sleep(0)
        self.seen.append((type_, payload))
        if type_ == "hierarchy.tree":
            return {"departments": TREE}
        if type_ == "rules.list":
            return {"rules": [RULE], "summary": {}}
        if type_ in ("rules.update", "rules.create"):
            return {"rule": RULE}
        if type_ == "deviations.list":
            return {"deviations": DEVS, "summary": {}, "by_rule": [], "per_day": []}
        if type_ == "deviations.get":
            d = next(x for x in DEVS if x["id"] == payload["deviation_id"])
            return {"deviation": d, "context": [{"at": d["at"], "who": "System", "what": "Recorded", "kind": "deviation"}],
                    "evidence": ["Kojo was signed in to OPS-01 at the time."]}
        if type_ == "deviations.outcome":
            return {"deviation": next(x for x in DEVS if x["id"] == payload["deviation_id"])}
        if type_ == "audit.deviations":
            return {"deviations": [d for d in DEVIATIONS if payload.get("include_resolved") or not d["resolved_at"]]}
        if type_ == "registry.refused":
            return {"refused": REFUSED, "summary": {}}
        if type_ == "registry.block":
            return {"address": payload["address"]}
        if type_ == "audit.recent":
            return {"entries": []}
        if type_ == "machines.list":
            return {"machines": [{"pc_id": 1, "hostname": "OPS-01", "key_generation": 2, "ip": "10.20.4.11",
                                  "owner": {"account_id": 21, "name": "Kojo"}, "version": "1.4.2"}]}
        if type_ == "issues.list":
            return {"issues": [ISSUE], "summary": {"open": 1, "waiting": 0, "past_target": 1, "done_today": 3, "mine": 1}}
        if type_ == "issues.get":
            return {"issue": ISSUE, "detail": {}, "lead": "A copy of budget-2026.xlsx is on OPS-01.", "facts": [["File", "budget-2026.xlsx"]],
                    "why": [], "timeline": [{"at": _ago(2), "who": "System", "what": "Raised", "kind": "raised", "you": False}],
                    "options": [{"key": "allow", "title": "Allow it on OPS-01 too", "desc": "", "verb": "Allow it", "done": "Resolved", "need": "reason"}]}
        if type_ == "issues.act":
            return {"issue": {**ISSUE, "state": "resolved"}, "done": "ok"}
        if type_ == "marks.list":
            return {"marks": [{"id": 3, "kind": "folder", "name": "Payroll", "pc_id": 101, "host": "WS-OPS-A1", "path": "C:/HR/Payroll", "keep": "path",
                               "files": 24, "versions": 30, "copies": 1, "by": {"account_id": 7, "you": True}}],
                    "summary": {"marks": 1, "files": 24, "copies": 1, "with_copies": 1}}
        if type_ == "marks.tree":
            files = ["C:\\Finance\\budget-2026.xlsx", "C:\\Finance\\Invoices\\q3.csv", "C:\\HR\\Payroll\\salaries.csv", "D:\\Board\\minutes.docx"]
            return {"pc_id": 101, "hostname": "WS-OPS-A1", "truncated": False,
                    "files": [{"path": f, "name": f.rsplit("\\", 1)[1], "marked": 9 if "budget" in f else None,
                               "covered_by": 3 if "Payroll" in f else None} for f in files]}
        if type_ == "marks.create":
            return {"marks": [], "copies_found": 0}
        if type_ == "marks.get":
            return {"mark": {"id": 3}, "copies": [{"issue_id": 41, "severity": "high", "host": "OPS-01", "file": "salaries.csv",
                                                   "folder": "C:/Users/Kojo", "signed_in": "Kojo", "opened_at": _ago(2)}]}
        if type_ == "reports.board":
            return {"reports": BOARD, "strip": {}, "handling": [], "categories": []}
        if type_ == "assistance.ping_status":
            return {"unaddressed": 2, "pings": PINGS}
        if type_ == "flow.list":
            return {"flows": [FLOW]}
        if type_ == "enroll.list":
            return {"requests": []}
        if type_ == "hierarchy.traverse":
            return {"session": {"session_id": 9, "pc_id": payload["pc_id"], "occupied_via": "traversal",
                                "entered_at": _ago(0), "deadline_at": (datetime.now(timezone.utc) + timedelta(minutes=30)).isoformat()}}
        return {}

    async def close(self) -> None:
        return None


@pytest.fixture
def console(tmp_path: Path):
    """A factory: `console(role)` gives (window, bridge, warnings) at that level, torn down after."""
    made = []

    def build(role: str = "admin"):
        cfg = LocalConfig(path=tmp_path / f"{role}.json", engine_host="127.0.0.1", engine_port=1,
                          client_id="", tls=False)
        _app, qml, bridge = create(cfg)
        warnings: list[str] = []
        qml.warnings.connect(lambda ws: warnings.extend(w.toString() for w in ws))
        made.append(qml)
        win = qml.rootObjects()[0]
        bridge.conn = _Connection()
        bridge.state.set_identity(_Identity(role), "test")
        return win, bridge, warnings

    yield build
    for qml in made:
        qml.warnings.disconnect()      # teardown re-evaluates bindings against a falcon that is gone
        qml.deleteLater()


def prop(obj: QObject, name: str):
    v = obj.property(name)
    return v.toVariant() if isinstance(v, QJSValue) else v


def _pump(seconds: float = 0.2) -> None:
    import time

    app = QCoreApplication.instance()
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        app.processEvents()


async def _wait(cond, timeout: float = 4.0) -> None:
    for _ in range(int(timeout / 0.05)):
        QCoreApplication.instance().processEvents()
        if cond():
            return
        await asyncio.sleep(0.05)
    raise AssertionError("condition not met in time")


async def _open(win, bridge, view: str, name: str) -> QObject:
    bridge.connected.emit()
    win.setProperty("view", view)
    await _wait(lambda: win.findChild(QObject, name) is not None)
    return win.findChild(QObject, name)


ADMIN_MENU = ["overview", "messages", "tasks", "restricted", "flows", "machines", "sessions", "issues",
              "automation", "actions", "rollout", "audit", "reports"]
SU_MENU = ["overview", "messages", "tasks", "restricted", "flows", "departments", "accountability", "access",
           "registry", "reports", "rules", "rollout", "audit"]


async def test_the_shell_is_the_console(console):
    """Sider, top bar, content -- and the window's own chrome, because it is frameless."""
    win, _, _ = console("admin")
    assert win.title() == "Falcon"
    assert bool(win.flags() & Qt.WindowType.FramelessWindowHint)
    for name in ("sideMenu", "crumb", "page", "themeSwitch", "winMinimize", "winMaximize", "winClose"):
        assert win.findChild(QObject, name) is not None, name
    assert prop(win, "menuKeys") == ADMIN_MENU


async def test_the_super_user_has_their_own_level_and_enters_an_admin_s(console):
    """The Super User's own level is the organisation; operating happens inside an Admin's console, and
    there the console IS that Admin's console, answered by the Engine as that Admin."""
    win, bridge, _ = console("super_user")
    assert prop(win, "menuKeys") == SU_MENU
    assert bridge.viewThroughSession is False

    bridge.state.set_session({"session_id": 4, "pc_id": 101, "occupied_via": "traversal", "super_user_banner": True,
                              "entered_at": _ago(0)})
    assert prop(win, "menuKeys") == ADMIN_MENU
    assert bridge.viewThroughSession is True

    # step back out from an Admin-only page: it is not a page of this level, so the Overview opens
    win.setProperty("view", "automation")
    bridge.state.set_session(None)
    assert prop(win, "menuKeys") == SU_MENU
    assert prop(win, "where") == "overview"


async def test_the_super_user_never_opens_an_admin_s_page(console):
    """A machine opens in Registry and a session in Access (docs/design/su-navigation.md)."""
    win, _, _ = console("super_user")
    win.setProperty("view", "machines/OPS-01")
    assert prop(win, "where") == "registry/OPS-01"
    win.setProperty("view", "sessions")
    assert prop(win, "where") == "access"


PAGES = [("admin", p) for p in ADMIN_MENU] + [("super_user", p) for p in SU_MENU] + [
    ("admin", "tasks/new"), ("admin", "flows/new"), ("admin", "automation/new"), ("admin", "actions/new"),
    ("admin", "restricted/mark"), ("admin", "machines/OPS-01"), ("super_user", "rules/new"), ("super_user", "rules/edit-O-5"), ("super_user", "tasks/new")]


@pytest.mark.parametrize(("role", "view"), PAGES, ids=[f"{r}-{v}" for r, v in PAGES])
async def test_every_page_loads_clean(console, role, view):
    """A QML error anywhere on a page leaves the Loader empty or prints a warning; either fails here."""
    win, bridge, warnings = console(role)
    bridge.connected.emit()
    win.setProperty("view", view)
    loader = win.findChild(QObject, "page")
    await _wait(lambda: loader.property("item") is not None)
    for _ in range(6):
        await asyncio.sleep(0.05)
        _pump(0.05)
    assert loader.property("item") is not None
    assert not warnings, "\n".join(warnings)


async def test_a_department_without_an_admin_comes_first(console):
    """The one condition on Departments that needs the Super User: its reports come to them."""
    win, bridge, _ = console("super_user")
    view = await _open(win, bridge, "departments", "departmentsView")
    await _wait(lambda: len(prop(view, "all") or []) == 2)
    assert [d["name"] for d in prop(view, "all")] == ["Logistics", "Operations"]
    assert prop(view, "d")["name"] == "Logistics"


async def test_a_deviation_is_a_record_against_a_rule(console):
    """The Engine's deviations: each read against its rule, what was expected beside what happened, the open one
    before the one dealt with; the record's evidence below, and an outcome recorded with the person's note."""
    win, bridge, _ = console("super_user")
    view = await _open(win, bridge, "accountability", "accountabilityView")
    await _wait(lambda: len(prop(view, "all") or []) == 2)
    dev = prop(view, "dev")
    assert dev["rule"] == "B-4" and dev["out"] == "open" and dev["code"] == "D-87"
    assert dev["expected"] == "The certificate names OPS-01"
    assert dev["happened"] == "The certificate names WS-OPS-01"
    assert [d["id"] for d in prop(view, "list")] == ["87"]          # open only, by default
    await _wait(lambda: prop(view, "evidence") == ["Kojo was signed in to OPS-01 at the time."])
    view.setProperty("note", "A new image set the long name")
    QMetaObject.invokeMethod(view, "record", Q_ARG("QVariant", "explained"))
    await _wait(lambda: any(t == "deviations.outcome" for t, _ in bridge.conn.seen))
    sent = next(p for t, p in bridge.conn.seen if t == "deviations.outcome")
    assert sent == {"deviation_id": 87, "outcome": "explained", "note": "A new image set the long name"}
    view.setProperty("oc", "all")
    assert [d["id"] for d in prop(view, "list")] == ["87", "80"]


async def test_refused_connections_are_one_row_per_key(console):
    """registry.refused groups the refused by who tried and from where; an address is blocked at the door from the page."""
    win, bridge, _ = console("super_user")
    view = await _open(win, bridge, "registry", "registryView")
    await _wait(lambda: len(prop(view, "doors") or []) == 2)
    doors = {d["client"]: d for d in prop(view, "doors")}
    assert doors["abc"]["tries"] == 2 and doors["abc"]["why"] == "wrong key for OPS-01" and doors["abc"]["ip"] == "10.20.9.201"
    assert doors["zzz"]["why"] == "not registered" and doors["zzz"]["now"] == "Waiting to be registered"
    QMetaObject.invokeMethod(view, "block", Q_ARG("QVariant", doors["abc"]), Q_ARG("QVariant", False))     # unblocking asks nothing first
    view.setProperty("tab", "door")
    await _wait(lambda: any(t == "registry.unblock" for t, _ in bridge.conn.seen))
    assert next(p for t, p in bridge.conn.seen if t == "registry.unblock") == {"address": "10.20.9.201"}
    rows = prop(view, "rows")
    assert next(r for r in rows if r["id"] == "OPS-01")["gen"] == 2


async def test_the_built_in_rules_are_listed_and_locked(console):
    """Every deviation points to a rule; the ones Falcon enforces are listed, and none can be edited."""
    win, bridge, _ = console("super_user")
    view = await _open(win, bridge, "rules", "rulesView")
    rules = prop(view, "all")
    assert [r["id"] for r in rules] == ["B-1", "B-2", "B-3", "B-4"]
    assert all(r["locked"] for r in rules)


async def test_entering_a_worker_s_machine_opens_its_session_window(console):
    """One window over the console; Back to the console keeps the session, the window comes back with the
    next entry."""
    win, bridge, _ = console("admin")
    bridge.connected.emit()
    window = win.findChild(QObject, "sessionWindow")
    assert window.property("visible") is False
    ok, _ = await bridge.request("hierarchy.traverse", {"pc_id": 1})
    assert ok
    await _wait(lambda: window.property("visible") is True)
    # the picture is asked for as the window opens, and a frame from the machine is drawn
    await _wait(lambda: any(t == "session.screen" and p.get("action") == "start" for t, p in bridge.conn.seen))
    png = "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNk+M9QDwADhgGAWjR9awAAAABJRU5ErkJggg=="
    bridge.pushReceived.emit("session.frame", {"session_id": 9, "seq": 1, "w": 1, "h": 1, "png_b64": png})
    await _wait(lambda: str(window.property("frame")).startswith("data:image/png;base64,"))
    # in control mode a click on the picture goes back to the machine
    QMetaObject.invokeMethod(window, "push", Q_ARG("QVariant", {"t": "down", "button": "left", "x": 0.5, "y": 0.5}))
    await _wait(lambda: any(t == "session.input" for t, _ in bridge.conn.seen))
    sent = next(p for t, p in bridge.conn.seen if t == "session.input")
    assert sent["session_id"] == 9 and sent["events"][0]["t"] == "down"


async def test_the_engine_s_issues_are_the_issues_and_a_choice_is_its_act(console):
    """issues.list replaces the issues the console used to read from the records; what an issue means and what can be
    done about it are issues.get's answer, and choosing is issues.act -- with the reason the option asks for."""
    win, bridge, _ = console("admin")
    view = await _open(win, bridge, "issues", "issuesView")
    await _wait(lambda: [r.get("iid") for r in prop(view, "rows") or []] == [41])
    await _wait(lambda: (prop(view, "play") or {}).get("lead") == "A copy of budget-2026.xlsx is on OPS-01.")
    assert [o["key"] for o in prop(view, "play")["options"]] == ["allow"]
    assert prop(view, "missing") == "Write a reason first."
    view.setProperty("input", {"I-41allow": "Approved for the audit"})
    assert prop(view, "missing") == ""
    QMetaObject.invokeMethod(view, "act")
    await _wait(lambda: any(t == "issues.act" for t, _ in bridge.conn.seen))
    sent = next(p for t, p in bridge.conn.seen if t == "issues.act")
    assert sent == {"issue_id": 41, "key": "allow", "reason": "Approved for the audit"}


async def test_marks_are_the_person_s_own_and_their_copies_are_issues(console):
    """marks.list is what you marked; marks.get gives a mark's copies, each an issue to deal with."""
    win, bridge, _ = console("admin")
    view = await _open(win, bridge, "restricted", "restrictedView")
    await _wait(lambda: len((prop(view, "cur") or {}).get("copies") or []) == 1)
    cur = prop(view, "cur")
    assert cur["name"] == "Payroll" and cur["keep"] == "path" and cur["files"] == 24
    assert cur["copies"][0]["iid"] == 41 and cur["copies"][0]["user"] == "Kojo"
    assert prop(view, "copiesN") == 1


async def test_marking_picks_from_the_index_as_a_tree_of_files_and_folders(console):
    """marks.tree's files become drives, folders and files; what is marked, or covered by a marked folder, cannot be
    ticked; a ticked folder is sent by the path its files have, so the Engine finds it in the index."""
    win, bridge, _ = console("admin")
    page = await _open(win, bridge, "restricted/mark", "markFiles")
    await _wait(lambda: any(r["name"] == "Payroll" and r["own"] for r in prop(page, "rows") or []))
    rows = {r["name"]: r for r in prop(page, "rows")}
    assert [r["name"] for r in prop(page, "rows")][:4] == ["C:", "Finance", "budget-2026.xlsx", "Invoices"]
    assert rows["C:"]["n"] == 3 and rows["Finance"]["n"] == 2
    assert rows["budget-2026.xlsx"]["own"] and rows["Payroll"]["own"]
    assert "q3.csv" not in rows                      # a second-level folder starts closed
    QMetaObject.invokeMethod(page, "toggle", Q_ARG("QVariant", rows["Finance"]["key"]))
    QMetaObject.invokeMethod(page, "mark")
    await _wait(lambda: any(t == "marks.create" for t, _ in bridge.conn.seen))
    sent = next(p for t, p in bridge.conn.seen if t == "marks.create")
    assert sent == {"paths": ["C:\\Finance"], "keep": "machine"}


QML_FILES = sorted(Path(QML_DIR).glob("*.qml"))


async def test_a_flow_s_steps_keep_their_names_and_their_place(console):
    """The Engine holds the steps as a tree; the page draws them as the concept does, named, before the split or on
    one branch, and leaves out what an earlier edit left unreached. Saving an edit sends the same tree back."""
    win, bridge, _ = console("admin")
    view = await _open(win, bridge, "flows", "flowsView")
    await _wait(lambda: len(prop(view, "steps") or []) == 2)
    steps = [{"kind": "Categorize", "op": "Sort by file type", "scope": "all"}, {"kind": "Transform", "op": "Compress to ZIP", "scope": 1}]
    assert prop(view, "steps") == steps
    win.setProperty("view", "flows/edit-5")
    await _wait(lambda: win.findChild(QObject, "newFlow") is not None)
    edit = win.findChild(QObject, "newFlow")
    await _wait(lambda: len(prop(edit, "stages") or []) == 2)
    assert prop(edit, "stages") == steps
    # the three stage columns share one height, the tallest one's, whatever each holds (side by side from 900 wide;
    # the offscreen test window is narrower, so the shared height is read rather than drawn)
    needs = [win.findChild(QObject, n).property("need") for n in ("nfSources", "nfSteps", "nfDests")]
    assert edit.property("colH") == max(needs) > min(needs)
    QMetaObject.invokeMethod(edit, "save")
    await _wait(lambda: any(t == "flow.edit" for t, _ in bridge.conn.seen))
    sent = next(p for t, p in bridge.conn.seen if t == "flow.edit")
    assert sent["stages"] == [{"stage_type": "categorization", "parent_index": None, "config": {"op": "Sort by file type", "by": "extension"}},
                              {"stage_type": "transformation", "parent_index": 0, "config": {"op": "Compress to ZIP"}}]
    assert [d["parent_index"] for d in sent["destinations"]] == [0, 1]



async def test_the_super_user_gives_a_task_on_its_own_page(console):
    """New task at the Super User's level is a page, not a drawer over the list: it holds Give back until the work and
    a department with an Admin are set, shows who is told, and sends task.dept_create, then opens the list."""
    win, bridge, _ = console("super_user")
    page = await _open(win, bridge, "tasks/new", "giveTask")
    assert prop(page, "problem") == "Say what needs doing."
    page.setProperty("text", "Collect the signed leave forms")
    assert prop(page, "problem") == "Pick a department."
    page.setProperty("dept", 1)
    await _wait(lambda: prop(page, "problem") == "")
    assert [a["name"] for a in prop(page, "told")] == ["R. Mensah"]
    QMetaObject.invokeMethod(page, "save")
    await _wait(lambda: any(t == "task.dept_create" for t, _ in bridge.conn.seen))
    sent = next(p for t, p in bridge.conn.seen if t == "task.dept_create")
    assert sent["department_id"] == 1 and sent["title"] == "Collect the signed leave forms" and "admin_ids" not in sent
    await _wait(lambda: prop(win, "where") == "tasks")

async def test_one_person_s_pings_are_one_row_with_every_time(console):
    """The Engine answers a row per ping; two pings from Kojo are one row that says twice, answered as the first."""
    win, bridge, _ = console("admin")
    view = await _open(win, bridge, "messages", "messagesView")
    await _wait(lambda: any(r.get("kind") == "ping" for r in (prop(view, "rows") or [])))
    pings = [r for r in prop(view, "rows") if r["kind"] == "ping"]
    assert len(pings) == 1
    assert pings[0]["pings"] == 2 and pings[0]["pid"] == 5 and pings[0]["st"][0] == "Pinged you 2 times"
    assert len(pings[0]["times"]) == 2


async def test_a_report_says_whose_it_is_as_the_engine_decides(console):
    """reports.board's owner decides the wording: a department without an Admin keeps its reports with the Super User."""
    win, bridge, _ = console("super_user")
    view = await _open(win, bridge, "reports", "reportsView")
    await _wait(lambda: len(prop(view, "rows") or []) == 2)
    rows = {r["id"]: r for r in prop(view, "rows")}
    assert rows[40]["st"] == "you" and rows[41]["st"] == "done"
    from PySide6.QtCore import Q_RETURN_ARG
    for rid, want in ((40, "You only · Logistics has no Admin"), (41, "You and Operations")):
        out = QMetaObject.invokeMethod(view, "goesTo", Q_RETURN_ARG("QVariant"), Q_ARG("QVariant", rows[rid]))
        assert out == want


async def test_a_rule_is_edited_in_the_engine_s_rule_store(console):
    """The Super User's rule from rules.list opens in the builder as it was saved, and saving sends the changed
    line to rules.update in the Engine's spec: minutes, the response, the scope."""
    win, bridge, _ = console("super_user")
    bridge.connected.emit()
    win.setProperty("view", "rules/edit-O-5")
    await _wait(lambda: win.findChild(QObject, "ruleBuilder") is not None)
    page = win.findChild(QObject, "ruleBuilder")
    await _wait(lambda: (prop(page, "s") or {}).get("name") == "Unanswered help request")
    s = prop(page, "s")
    assert s["shape"] == "follow" and s["within"] == {"n": 1, "unit": "hours"} and s["resp"]["admin"] is True
    QMetaObject.invokeMethod(page, "set", Q_ARG("QVariant", "within"), Q_ARG("QVariant", {"n": 2, "unit": "hours"}))
    QMetaObject.invokeMethod(page, "save")
    await _wait(lambda: any(t == "rules.update" for t, _ in bridge.conn.seen))
    sent = next(p for t, p in bridge.conn.seen if t == "rules.update")
    assert sent["rule_id"] == 5 and sent["within"] == 120 and sent["trigger"] == "help" and sent["expect"] == "answer"
    assert sent["resp"] == {"report": True, "admin": True, "action": False} and sent["who"] == "admins" and sent["depts"] == "all"


def test_nothing_clickable_uses_a_taphandler():
    """A TapHandler reacts to a press over its item even when a dialog sits on top of it (CLAUDE.md)."""
    offenders = [f.name for f in QML_FILES if re.search(r"^\s*TapHandler\s*\{", f.read_text(encoding="utf-8"), re.MULTILINE)]
    assert not offenders


def test_colours_are_named_only_in_the_theme():
    """Theme.qml is the one place a colour is named, so light and dark stay one decision."""
    pattern = re.compile(r"\"#[0-9a-fA-F]{3,8}\"|Qt\.rgba\(|'#[0-9a-fA-F]{3,8}'")
    offenders = [f.name for f in QML_FILES if f.name != "Theme.qml" and pattern.search(f.read_text(encoding="utf-8"))]
    assert not offenders
