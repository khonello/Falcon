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

from PySide6.QtCore import QCoreApplication, QMetaObject, QObject, Qt
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

REFUSED = [
    {"id": 1, "action": "auth.failed", "target_id": "abc", "occurred_at": _ago(1),
     "detail": {"reason": "challenge failed", "peer": "('10.20.9.201', 50012)"}},
    {"id": 2, "action": "auth.failed", "target_id": "abc", "occurred_at": _ago(3),
     "detail": {"reason": "challenge failed", "peer": "('10.20.9.201', 50013)"}},
    {"id": 3, "action": "auth.failed", "target_id": "zzz", "occurred_at": _ago(2),
     "detail": {"reason": "client_id is not provisioned or its account is not active", "peer": "('10.20.6.40', 1)"}},
]


ISSUE = {"id": 41, "code": "I-41", "type": "file", "severity": "critical", "title": "Restricted file copied where it isn't allowed",
         "subject": "budget-2026.xlsx", "pc_id": 1, "host": "OPS-01", "department_id": 1, "opened_at": _ago(2), "past_target": True,
         "owner": {"account_id": 7, "name": "R. Mensah", "you": True}, "state": "open", "label": "Open", "escalated": False}


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
        if type_ == "audit.deviations":
            return {"deviations": [d for d in DEVIATIONS if payload.get("include_resolved") or not d["resolved_at"]]}
        if type_ == "audit.recent":
            return {"entries": REFUSED if payload.get("prefix") == "auth.failed" else []}
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
        if type_ == "marks.get":
            return {"mark": {"id": 3}, "copies": [{"issue_id": 41, "severity": "high", "host": "OPS-01", "file": "salaries.csv",
                                                   "folder": "C:/Users/Kojo", "signed_in": "Kojo", "opened_at": _ago(2)}]}
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
    ("admin", "restricted/mark"), ("admin", "machines/OPS-01")]


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
    """The Engine logs `account_bound_to_one_pc`; the page reads it against the built-in rule it departs
    from, with what was expected beside what happened, and the open one before the one dealt with."""
    win, bridge, _ = console("super_user")
    view = await _open(win, bridge, "accountability", "accountabilityView")
    await _wait(lambda: len(prop(view, "all") or []) == 2)
    dev = prop(view, "dev")
    assert dev["rule"] == "B-4" and dev["out"] == "open"
    assert dev["expected"] == "The certificate names OPS-01"
    assert dev["happened"] == "The certificate names WS-OPS-01"
    assert [d["id"] for d in prop(view, "list")] == ["87"]          # open only, by default
    view.setProperty("oc", "all")
    assert [d["id"] for d in prop(view, "list")] == ["87", "80"]


async def test_refused_connections_are_one_row_per_key(console):
    """Every failed handshake is audited; the Registry folds them into who kept trying, and why."""
    win, bridge, _ = console("super_user")
    view = await _open(win, bridge, "registry", "registryView")
    await _wait(lambda: len(prop(view, "doors") or []) == 2)
    doors = {d["client"]: d for d in prop(view, "doors")}
    assert doors["abc"]["tries"] == 2 and doors["abc"]["why"] == "wrong key" and doors["abc"]["ip"] == "10.20.9.201"
    assert doors["zzz"]["why"] == "not registered"
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


QML_FILES = sorted(Path(QML_DIR).glob("*.qml"))


def test_nothing_clickable_uses_a_taphandler():
    """A TapHandler reacts to a press over its item even when a dialog sits on top of it (CLAUDE.md)."""
    offenders = [f.name for f in QML_FILES if re.search(r"^\s*TapHandler\s*\{", f.read_text(encoding="utf-8"), re.MULTILINE)]
    assert not offenders


def test_colours_are_named_only_in_the_theme():
    """Theme.qml is the one place a colour is named, so light and dark stay one decision."""
    pattern = re.compile(r"\"#[0-9a-fA-F]{3,8}\"|Qt\.rgba\(|'#[0-9a-fA-F]{3,8}'")
    offenders = [f.name for f in QML_FILES if f.name != "Theme.qml" and pattern.search(f.read_text(encoding="utf-8"))]
    assert not offenders
