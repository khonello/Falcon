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
    {"department_id": 1, "name": "Operations", "admins": [{"account_id": 7, "name": "R. Mensah", "online": True, "hostname": "WS-OPS-A1"}],
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
        "sentence": "A worker messages for help, then an Admin answers the message within 1 hour.", "scope": "Admins, every department",
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
                               "files": 24, "versions": 30, "copies": 1, "by": {"account_id": 7, "you": True}},
                              {"id": 5, "kind": "file", "name": "reviews.docx", "pc_id": 101, "host": "WS-OPS-A1", "path": "C:/HR/reviews.docx", "keep": "machine",
                               "files": 1, "versions": 1, "copies": 0, "by": {"account_id": 7, "you": True}, "protection": "private", "allow_system": True,
                               "readers": [{"account_id": 7, "name": "R. Mensah"}, {"account_id": 9, "name": "A. Quaye"}],
                               "applied": {"ok": True, "at": _ago(5), "granted": [], "missing": []},
                               "refusals": [{"who": "Kojo", "account_id": 21, "process": "WINWORD.EXE", "path": "C:/HR/reviews.docx", "at": _ago(1), "machine": "WS-OPS-A1"}]},
                              {"id": 6, "kind": "folder", "name": "Board", "pc_id": 101, "host": "WS-OPS-A1", "path": "D:/Board", "keep": "machine",
                               "files": 3, "versions": 1, "copies": 0, "by": {"account_id": 7, "you": True}, "protection": "watch", "readers": [], "refusals": []}],
                    "summary": {"marks": 3, "files": 28, "copies": 1, "with_copies": 1}}
        if type_ == "marks.readers":
            return {"mark_id": payload["mark_id"], "readers": sorted(set(payload["readers"]) | {7}), "allow_system": payload.get("allow_system", True), "applied_now": True}
        if type_ == "chat.people":
            return {"people": [{"account_id": 9, "name": "A. Quaye", "role": "admin", "pc_id": 102, "hostname": "WS-OPS-A2", "department": None, "online": True},
                               {"account_id": 27, "name": "Ama", "role": "worker", "pc_id": 7, "hostname": "OPS-07", "department": "Operations", "online": True}],
                    "admins_group": True}
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
        if type_ == "assistance.respond":
            return {"channel_id": 12, "opened": True, "turn": "sender", "superior_account_id": 7}
        if type_ == "assistance.message":
            return {"message_id": 1, "turn": "superior"}
        if type_ == "chat.list":
            return {"conversations": [{"conversation_id": 12, "kind": "direct", "title": "Kojo", "unread": 1,
                                       "members": [{"account_id": 7, "name": "R. Mensah"}, {"account_id": 21, "name": "Kojo"}],
                                       "last": {"body": "The printer is jammed.", "from_account_id": 21, "from": "Kojo", "at": _ago(1)}, "seen_by": []}], "unread": 1}
        if type_ == "chat.get":
            return {"conversation": {"conversation_id": 12, "title": "Kojo"}, "more": False, "reads": [],
                    "messages": [{"message_id": 1, "from_account_id": 21, "from": "Kojo", "body": "The printer is jammed.", "at": _ago(1), "mine": False, "file": None}]}
        if type_ == "chat.send":
            return {"message_id": 2, "at": _ago(0)}
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


ADMIN_MENU = ["overview", "messages", "announcements", "calendar", "tasks", "flows", "restricted", "detective", "machines", "departments", "actions", "automation", "issues", "audit"]


async def test_the_shell_is_the_console(console):
    """Sider, top bar, content -- and the window's own chrome, because it is frameless."""
    win, _, _ = console("admin")
    assert win.title() == "Falcon"
    assert bool(win.flags() & Qt.WindowType.FramelessWindowHint)
    for name in ("sideMenu", "crumb", "page", "themeSwitch", "winMinimize", "winMaximize", "winClose"):
        assert win.findChild(QObject, name) is not None, name
    assert prop(win, "menuKeys") == ADMIN_MENU


PAGES = [("admin", p) for p in ADMIN_MENU] + [
    ("admin", "tasks/new"), ("admin", "flows/new"), ("admin", "automation/new"), ("admin", "actions/new"),
    ("admin", "restricted/mark")]


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


async def test_restricting_finds_it_by_search_and_what_is_restricted_cannot_be_picked_again(console):
    """Restrict something searches what the index has seen on this PC, folders first; what is already restricted says so; the path goes as the index spells it."""
    win, bridge, _ = console("admin")
    page = await _open(win, bridge, "restricted/mark", "markFiles")
    await _wait(lambda: len(prop(page, "files") or []) > 0)
    page.setProperty("q", "budget")
    _pump(0.2)
    assert [h["path"] for h in prop(page, "hits")] == [r"C:\Finance\budget-2026.xlsx"]
    assert prop(page, "prob").startswith("Search for the file")                  # nothing picked: the next step is shut
    QMetaObject.invokeMethod(page, "take", Q_ARG("QVariant", r"C:\Finance"), Q_ARG("QVariant", "folder"))
    page.setProperty("step", 2)
    _pump(0.2)
    page.confirmed.emit()
    await _wait(lambda: any(t == "marks.create" for t, _ in bridge.conn.seen))
    sent = next(p for t, p in bridge.conn.seen if t == "marks.create")
    assert sent == {"paths": [r"C:\Finance"], "protection": "restricted", "keep": "path", "confirm_large": False}


async def test_protected_files_shows_each_mark_with_its_tag_and_only_a_restricted_one_looks_for_copies(console):
    """Protected files (the page's key is still "restricted"): every mark carries its tag, the list filters by it, and copies,
    allowed copies and flows are the Restricted marks' alone; the page opens where it did, on what has copies."""
    win, bridge, _ = console("admin")
    page = await _open(win, bridge, "restricted", "restrictedView")
    await _wait(lambda: len(prop(page, "marks")) == 3)
    assert {k["name"]: k["prot"] for k in prop(page, "marks")} == {"Payroll": "restricted", "reviews.docx": "private", "Board": "watch"}
    assert [k["name"] for k in prop(page, "rmarks")] == ["Payroll"]
    assert prop(page, "cur")["name"] == "Payroll"
    # always one kind on screen, never a mix (the user, 11 Nov 2026): Restricted first; a file of another kind brings its own kind
    assert prop(page, "show") == "restricted" and [k["name"] for k in prop(page, "shownMarks")] == ["Payroll"]
    page.setProperty("sel", "6")
    _pump(0.2)
    assert prop(page, "show") == "watch" and prop(page, "cur")["name"] == "Board"
    page.setProperty("sel", "")
    sit = prop(page, "situation")
    assert "3 things are protected on 1 machine: 1 restricted, 1 private and 1 watched." in sit and "Someone was refused a private file this week." in sit
    page.setProperty("show", "private")
    _pump(0.2)
    assert [k["name"] for k in prop(page, "shownMarks")] == ["reviews.docx"]
    private = next(k for k in prop(page, "marks") if k["prot"] == "private")
    assert private["readers"][1]["name"] == "A. Quaye" and private["refusals"][0]["who"] == "Kojo"


async def test_who_may_open_a_private_file_is_changed_in_place(console):
    """Change who may open it: ticked from chat.people, without the Admin at this console (the Engine always adds them), sent as marks.readers."""
    win, bridge, _ = console("admin")
    page = await _open(win, bridge, "restricted", "restrictedView")
    await _wait(lambda: len(prop(page, "marks")) == 3)
    private = next(k for k in prop(page, "marks") if k["prot"] == "private")
    QMetaObject.invokeMethod(page, "changeReaders", Q_ARG("QVariant", private))
    await _wait(lambda: len(prop(page, "people")) == 2)
    assert prop(page, "readersPick") == [9]
    page.setProperty("readersPick", [9, 27])
    page.setProperty("readersSystem", False)
    QMetaObject.invokeMethod(page, "saveReaders")
    await _wait(lambda: any(t == "marks.readers" for t, _ in bridge.conn.seen))
    assert next(p for t, p in bridge.conn.seen if t == "marks.readers") == {"mark_id": 5, "readers": [9, 27], "allow_system": False}


async def test_protecting_something_asks_how_and_a_private_one_names_who_may_open_it(console):
    """Protect something: Restricted, Private or Watch. Private sends the people named and whether backup may open it; Watch sends no place rule of its own."""
    win, bridge, _ = console("admin")
    page = await _open(win, bridge, "restricted/mark", "markFiles")
    await _wait(lambda: len(prop(page, "files") or []) > 0)
    QMetaObject.invokeMethod(page, "take", Q_ARG("QVariant", r"C:\HR\reviews.docx"), Q_ARG("QVariant", "file"))
    page.setProperty("prot", "private")
    page.setProperty("readers", [27])
    page.setProperty("step", 2)
    _pump(0.2)
    assert prop(page, "confirmText") == "Make it private"
    page.confirmed.emit()
    await _wait(lambda: any(t == "marks.create" for t, _ in bridge.conn.seen))
    assert next(p for t, p in bridge.conn.seen if t == "marks.create") == {"paths": [r"C:\HR\reviews.docx"], "protection": "private", "keep": "machine",
                                                                           "confirm_large": False, "readers": [27], "allow_system": True}


QML_FILES = sorted(Path(QML_DIR).glob("*.qml"))


async def test_a_flow_s_steps_keep_their_names_and_their_place(console):
    """The Engine holds the steps as a tree; the page draws them as the concept does, named, before the split or on
    one branch, and leaves out what an earlier edit left unreached. A placing step (Sort by file type) was dropped on 3 Nov
    2026: it is left out when the flow is read in, and saving sends back only what the Engine still takes."""
    win, bridge, _ = console("admin")
    view = await _open(win, bridge, "flows", "flowsView")
    await _wait(lambda: len(prop(view, "steps") or []) == 1)
    steps = [{"kind": "Transform", "opId": "", "op": "Compress to ZIP", "settings": {}, "scope": 1}]   # only the second destination reaches it
    assert prop(view, "steps") == steps
    win.setProperty("view", "flows/edit-5")
    await _wait(lambda: win.findChild(QObject, "newFlow") is not None)
    edit = win.findChild(QObject, "newFlow")
    await _wait(lambda: len(prop(edit, "stages") or []) == 1)
    assert prop(edit, "stages") == steps
    QMetaObject.invokeMethod(edit, "save")
    await _wait(lambda: any(t == "flow.edit" for t, _ in bridge.conn.seen))
    sent = next(p for t, p in bridge.conn.seen if t == "flow.edit")
    assert sent["stages"] == [{"stage_type": "transformation", "parent_index": None, "config": {"op": "Compress to ZIP"}}]
    assert [d["parent_index"] for d in sent["destinations"]] == [None, 0]
    assert sent["on_source_delete"] == "keep"                                    # kept as it was set


async def test_writing_in_a_conversation_sends_the_body(console):
    """Version 1's conversations (chat.*): the one picked is read, and what is written goes as `body` with chat.send. There is
    no turn lock, so the box is there for every conversation (22 Oct 2026)."""
    win, bridge, _ = console("admin")
    view = await _open(win, bridge, "messages", "messagesView")
    await _wait(lambda: [r.get("conversation_id") for r in (prop(view, "rows") or [])] == [12])
    await _wait(lambda: any(t == "chat.read" for t, _ in bridge.conn.seen))
    assert win.findChild(QObject, "msgSend") is not None
    QMetaObject.invokeMethod(view, "setDraft", Q_ARG("QVariant", "on my way"))
    QMetaObject.invokeMethod(view, "send")
    await _wait(lambda: any(t == "chat.send" for t, _ in bridge.conn.seen))
    assert next(p for t, p in bridge.conn.seen if t == "chat.send") == {"conversation_id": 12, "body": "on my way"}






def test_nothing_clickable_uses_a_taphandler():
    """A TapHandler reacts to a press over its item even when a dialog sits on top of it (CLAUDE.md)."""
    offenders = [f.name for f in QML_FILES if re.search(r"^\s*TapHandler\s*\{", f.read_text(encoding="utf-8"), re.MULTILINE)]
    assert not offenders


def test_colours_are_named_only_in_the_theme():
    """Theme.qml is the one place a colour is named, so light and dark stay one decision."""
    pattern = re.compile(r"\"#[0-9a-fA-F]{3,8}\"|Qt\.rgba\(|'#[0-9a-fA-F]{3,8}'")
    offenders = [f.name for f in QML_FILES if f.name != "Theme.qml" and pattern.search(f.read_text(encoding="utf-8"))]
    assert not offenders


async def test_departments_are_made_renamed_and_a_machine_moved_in_from_their_page(console):
    """Version 1 (docs/design/v1-it-admin.md): a department is a label any IT Admin makes and puts machines in."""
    win, bridge, _ = console("admin")
    page = await _open(win, bridge, "departments", "departmentsView")
    page.setProperty("nm", "Procurement")
    QMetaObject.invokeMethod(page, "make")
    await _wait(lambda: any(t == "hierarchy.department_create" for t, _ in bridge.conn.seen))
    assert next(p for t, p in bridge.conn.seen if t == "hierarchy.department_create") == {"name": "Procurement"}
    page.setProperty("ren", "Ops")
    QMetaObject.invokeMethod(page, "rename", Q_ARG("QVariant", {"id": 1, "name": "Operations"}))
    await _wait(lambda: any(t == "hierarchy.department_rename" for t, _ in bridge.conn.seen))
    assert next(p for t, p in bridge.conn.seen if t == "hierarchy.department_rename") == {"department_id": 1, "name": "Ops"}


async def test_restricted_draws_every_machine_the_admins_apart_at_the_top_then_each_department(console):
    win, bridge, _ = console("admin")
    page = await _open(win, bridge, "restricted", "restrictedView")
    await _wait(lambda: len(prop(page, "mapDepts")) == 3)
    assert [(g["name"], g["hs"]) for g in prop(page, "mapDepts")] == [("Admins", ["WS-OPS-A1"]), ("Operations", ["OPS-01", "OPS-02"]), ("Logistics", ["LOG-01"])]


async def test_editing_a_flow_keeps_its_steps_and_a_destination_still_waiting_on_its_admin(console):
    from PySide6.QtCore import Q_ARG, QMetaObject

    win, bridge, _ = console("admin")
    page = await _open(win, bridge, "flows/new", "newFlow")
    _pump(0.3)
    flow = {"id": 40, "name": "ops-pack", "source_pc_id": 1, "source_path": "/reports/",
            "stages": [{"id": 1, "parent_stage_id": None, "stage_type": "bundling", "config": {"kind": "bundling", "op": "zip_one", "label": "Into one ZIP", "settings": {}}}],
            "destinations": [{"id": 2, "destination_pc_id": 3, "destination_path": None, "let_them_choose": True, "owner_account_id": 7, "parent_stage_id": 1}]}
    QMetaObject.invokeMethod(page, "fill", Q_ARG("QVariant", flow), Q_ARG("QVariant", False))
    stage, dest = prop(page, "stages")[0], prop(page, "dests")[0]
    assert (stage["kind"], stage["opId"], stage["op"]) == ("bundling", "zip_one", "Into one ZIP")   # as the Engine stores a step
    assert dest["mode"] == "ask" and dest["who"] == 7                                               # they still pick the folder


async def test_making_a_new_key_is_not_in_the_console(console):
    root = Path(__file__).parents[1] / "operator_client/gui/qml"
    assert not (root / "KeyDrawer.qml").exists()
    assert not any("pc_rekey" in p.read_text(encoding="utf8") for p in root.glob("*.qml"))   # a power setting: the TUI's `machine newkey`


async def test_a_rule_is_tried_on_one_machine_and_nothing_is_saved(console):
    win, bridge, _ = console("admin")
    page = await _open(win, bridge, "automation/new", "newRule")
    page.setProperty("acts", [{"id": 4, "name": "Take a screenshot", "limit": 30}])
    page.setProperty("tryOn", 2)
    QMetaObject.invokeMethod(page, "tryIt")
    await _wait(lambda: any(t == "control.rule_try" for t, _ in bridge.conn.seen))
    sent = next(p for t, p in bridge.conn.seen if t == "control.rule_try")
    assert sent["pc_id"] == 2 and sent["action_ids"] == [4] and sent["type"]
    assert not any(t in ("control.event_create", "control.event_update") for t, _ in bridge.conn.seen)


async def test_a_console_that_is_not_set_up_asks_in_the_middle_and_nothing_else(console):
    win, bridge, _ = console("admin")
    modal = win.findChild(QObject, "setupModal")
    bridge.state.connected = True
    bridge.stateChanged.emit()
    await _wait(lambda: prop(modal, "visible") is False)                                  # connected: there is nothing to ask
    bridge.state.connected = False
    bridge.stateChanged.emit()
    await _wait(lambda: prop(modal, "visible") is True)
    assert prop(bridge, "needsSetup") is True
    assert prop(modal, "problem") == ""                                                   # Connect waits for the address and the code
    modal.setProperty("address", "192.168.1.20")
    modal.setProperty("code", "ADMN-1111")
    modal.setProperty("cert", "C:/engine.crt")
    assert prop(modal, "problem") == "ready"


async def test_the_sider_names_the_admins_workstation_never_an_id(console):
    win, bridge, _ = console("admin")
    await _open(win, bridge, "overview", "overviewView")
    text = (Path(__file__).parents[1] / "operator_client/gui/qml/Sider.qml").read_text(encoding="utf8")
    assert "defaultClientId" not in text and "clientId" not in text                     # a client id is internal: no page shows it


async def test_a_live_row_is_built_from_the_audit_push_with_its_person_and_machine(console):
    win, bridge, _ = console("admin")
    page = await _open(win, bridge, "overview", "overviewView")
    bridge.pushReceived.emit("audit.event", {"id": 99, "at": "2026-11-10T00:30:00+00:00", "kind": "session", "actor": "A. Quaye",
                                             "what": "Entered OPS-04", "host": "OPS-04", "action_type": "session.traverse"})
    await _wait(lambda: (prop(page, "live") or [{}])[0].get("id") == 99)
    row = prop(page, "live")[0]
    assert (row["actor"], row["what"], row["host"], row["kind"]) == ("A. Quaye", "Entered OPS-04", "OPS-04", "session")


async def test_a_file_is_sent_from_this_machine_in_a_conversation(console):
    win, bridge, _ = console("admin")
    view = await _open(win, bridge, "messages", "messagesView")
    await _wait(lambda: prop(view, "c") is not None)
    view.setProperty("filePath", "C:/Users/Admin/Documents/report.pdf")
    QMetaObject.invokeMethod(view, "sendTheFile")
    await _wait(lambda: any(t == "chat.send_file" for t, _ in bridge.conn.seen))
    sent = next(p for t, p in bridge.conn.seen if t == "chat.send_file")
    assert sent == {"conversation_id": 12, "path": "C:/Users/Admin/Documents/report.pdf"}


async def test_a_dropped_placing_step_is_left_out_when_a_flow_is_read_in(console):
    from PySide6.QtCore import Q_ARG

    win, bridge, _ = console("admin")
    page = await _open(win, bridge, "flows/new", "newFlow")
    _pump(0.3)
    flow = {"id": 41, "name": "old", "source_pc_id": 1, "source_path": "/in/",
            "stages": [{"id": 1, "parent_stage_id": None, "stage_type": "categorization", "config": {"op": "Sort by file type", "by": "extension"}},
                       {"id": 2, "parent_stage_id": 1, "stage_type": "renaming", "config": {"kind": "renaming", "op": "add_date", "label": "Add a date", "settings": {}}}],
            "destinations": [{"id": 3, "destination_pc_id": 2, "destination_path": "/out/", "parent_stage_id": 2}]}
    QMetaObject.invokeMethod(page, "fill", Q_ARG("QVariant", flow), Q_ARG("QVariant", False))
    assert [s["op"] for s in prop(page, "stages")] == ["Add a date"]                     # sent back, the Engine would refuse the placing step


async def test_a_restricted_file_waiting_for_a_yes_is_answered_from_messages(console):
    win, bridge, _ = console("admin")
    view = await _open(win, bridge, "messages", "messagesView")
    bridge.pushReceived.emit("chat.file_consent_request", {"file_id": 77, "name": "budget.xlsx", "from_account_id": 21, "from": "Kojo", "why": ["restricted on OPS-01"]})
    await _wait(lambda: len(prop(view, "asks") or []) == 1)
    bridge.pushReceived.emit("chat.file_consent_request", {"file_id": 77, "name": "budget.xlsx", "from": "Kojo"})
    _pump(0.2)
    assert len(prop(view, "asks")) == 1                                                   # the same file asked twice is one request
    view.setProperty("sel", "f77")
    await _wait(lambda: prop(view, "curAsk") is not None)
    assert prop(view, "c") is None                                                        # the request is what is open, not a conversation
    QMetaObject.invokeMethod(view, "answer", Q_ARG("QVariant", prop(view, "curAsk")), Q_ARG("QVariant", True))
    await _wait(lambda: any(t == "chat.file_consent" for t, _ in bridge.conn.seen))
    assert next(p for t, p in bridge.conn.seen if t == "chat.file_consent") == {"file_id": 77, "grant": True}
    await _wait(lambda: prop(view, "asks") == [])


async def test_a_flow_that_copies_only_when_run_can_be_run_now(console):
    win, bridge, _ = console("admin")
    view = await _open(win, bridge, "flows", "flowsView")
    await _wait(lambda: prop(view, "cur") is not None)
    run = win.findChild(QObject, "flowRunNow")
    assert prop(run, "visible") is False                                                  # a real-time flow needs no button
    view.setProperty("flows", [{**FLOW, "run_mode": "manual"}])
    await _wait(lambda: prop(run, "visible") is True)
    run.clicked.emit()
    await _wait(lambda: any(t == "flow.run" for t, _ in bridge.conn.seen))
    assert next(p for t, p in bridge.conn.seen if t == "flow.run") == {"flow_id": 5}



async def test_a_long_list_pages_in_place_and_keeps_the_picked_one_on_screen(console):
    """Paging is native to anything list-like (the user, 11 Nov 2026): a PagedList, and a Group given its items, draw `per` at a
    time with the pager under them, step through the pages, and show the page that holds the item picked."""
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlComponent, QQmlEngine

    win, _bridge, _ = console("admin")
    qml = QQmlEngine.contextForObject(win).engine()
    for kind in ("PagedList", "Group"):
        comp = QQmlComponent(qml)
        comp.setData(("import QtQuick\nimport \".\"\n" + kind + " { width: 400; items: [0,1,2,3,4,5,6,7,8,9,10,11]; per: 5\n"
                      "  delegate: Item { required property var modelData; width: 10; height: 10 } }").encode(), QUrl.fromLocalFile(str(Path(QML_DIR) / "_paged_test.qml")))
        obj = comp.create()
        assert obj is not None, [e.toString() for e in comp.errors()]
        assert prop(obj, "shown") == [0, 1, 2, 3, 4]
        pager = next(c for c in obj.findChildren(QObject) if c.metaObject().className().startswith("StepPager"))
        assert pager.property("visible") and pager.property("total") == 12 and pager.property("pages") == 3
        pager.step.emit(1)
        assert prop(obj, "shown") == [5, 6, 7, 8, 9]
        obj.setProperty("keep", 11)                                    # the item picked is on the last page: that page is shown
        assert prop(obj, "shown") == [10, 11]
        obj.setProperty("items", [0, 1, 2])
        assert prop(obj, "shown") == [0, 1, 2] and not pager.property("visible")   # one page: no pager
        obj.deleteLater()


async def test_a_page_holds_four_on_every_screen(console):
    """Exactly four a page, then the pager, whatever the screen (the user, 13 Nov 2026: a tall window had made it five)."""
    from PySide6.QtCore import QUrl
    from PySide6.QtQml import QQmlComponent, QQmlEngine

    win, _bridge, _ = console("admin")
    qml = QQmlEngine.contextForObject(win).engine()
    comp = QQmlComponent(qml)
    comp.setData(b'import QtQuick\nimport "."\nItem { function tall(h) { Theme.viewH = h }\n'
                 b'  PagedList { objectName: "pl"; width: 400; items: [0,1,2,3,4,5,6,7,8,9,10,11]\n'
                 b'    delegate: Item { required property var modelData; width: 10; height: 10 } } }', QUrl.fromLocalFile(str(Path(QML_DIR) / "_tall_test.qml")))
    obj = comp.create()
    assert obj is not None, [e.toString() for e in comp.errors()]
    pl = obj.findChild(QObject, "pl")
    try:
        for h in (450, 900, 1040, 1800):
            QMetaObject.invokeMethod(obj, "tall", Q_ARG("QVariant", h))
            assert len(prop(pl, "shown")) == 4, h
    finally:
        QMetaObject.invokeMethod(obj, "tall", Q_ARG("QVariant", win.property("height")))
        obj.deleteLater()


async def test_machines_are_moved_into_a_department_from_a_window_of_their_own(console):
    """Departments (the user, 12 Nov 2026): the department on the right is only itself; Move machines here opens a window where machines from
    elsewhere are found and ticked, and each one ticked is moved in (hierarchy.pc_move)."""
    win, bridge, _ = console("admin")
    page = await _open(win, bridge, "departments", "departmentsView")
    await _wait(lambda: prop(page, "cur") is not None and len(prop(page, "elsewhere") or []) > 0)
    dept = prop(page, "cur")["id"]
    QMetaObject.invokeMethod(page, "openMove")
    _pump(0.2)
    assert win.findChild(QObject, "deptMoveModal").property("visible")
    pcs = [m["pc_id"] for m in prop(page, "elsewhere")][:2]
    page.setProperty("ticked", pcs)
    QMetaObject.invokeMethod(page, "moveTicked")
    await _wait(lambda: len([p for t, p in bridge.conn.seen if t == "hierarchy.pc_move"]) == len(pcs))
    assert sorted(p["pc_id"] for t, p in bridge.conn.seen if t == "hierarchy.pc_move") == sorted(pcs)
    assert all(p["department_id"] == dept for t, p in bridge.conn.seen if t == "hierarchy.pc_move")
