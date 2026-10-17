# ruff: noqa: F811, RUF059

from __future__ import annotations

import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from detective_scenarios import SCENARIOS, play
from PySide6.QtCore import QMetaObject, QObject

from common.detective import rule_options
from tests.test_operator_gui import _open, _pump, _wait, console, prop  # noqa: F401


def _names(root) -> set[str]:
    """Every named thing drawn, delegates of a Repeater included (they hang off the visual tree, not the object tree)."""
    import shiboken6

    seen, names, stack = set(), set(), [root]
    while stack:
        o = stack.pop()
        key = shiboken6.getCppPointer(o)[0]
        if key in seen:
            continue
        seen.add(key)
        if o.objectName():
            names.add(o.objectName())
        stack.extend(o.children())
        if hasattr(o, "childItems"):
            stack.extend(o.childItems())
    return names


def _iso(t: float) -> str:
    return datetime.fromtimestamp(t, timezone.utc).isoformat()


def sample():
    det, _ = play(SCENARIOS["leak"]())
    c = det.open_cases()[0]
    n, latest, nxt = c.stage
    case = {"id": 1, "host": "FIN-07", "intent": c.intent, "level": c.level, "weight": c.weight, "stage_count": n, "stage_name": latest, "next_stage": nxt,
            "not_yet": c.not_yet(), "behaviours": sorted(c.behaviours), "headline": c.headline(), "story": c.story(), "status": "open", "note": None,
            "first_at": _iso(c.first_at), "last_at": _iso(c.last_at)}
    findings = [{"behaviour": f.behaviour, "graph": f.graph, "weight": f.weight, "summary": f.summary, "innocent": f.innocent, "why": f.why} for f in c.findings]
    # a second, quieter case beside it
    quiet = {**case, "id": 2, "host": "FIN-02", "intent": "Hiding something", "level": "noted", "weight": 0.38, "stage_count": 1, "stage_name": "Hiding", "next_stage": "Taking out",
             "not_yet": None, "behaviours": ["concealment"], "headline": "Hiding something. birthday-plans.docx was hidden.", "story": ["11:00  hid birthday-plans.docx"]}
    return case, quiet, {"case": {**case, "reviewed_by": None}, "findings": findings, "graph": c.graph(), "rule_options": rule_options(c.findings), "board": c.board()}


async def _page(console, role="super_user"):
    win, bridge, _ = console(role)
    page = await _open(win, bridge, "detective", "detectiveView")
    win.showNormal()
    win.resize(1440, 1500)
    case, quiet, det = sample()
    page.setProperty("ov", {"by_level": {"noted": 1, "case": 0, "urgent": 1}, "by_intent": {"Taking data out": 1}, "reviewed": 3})
    page.setProperty("cases", [case, quiet])
    page.setProperty("sel", 1)
    page.setProperty("det", det)
    _pump(0.8)
    return win, bridge, page


async def test_a_case_reads_as_a_story_a_picture_and_a_question(console):
    win, bridge, page = await _page(console)
    assert prop(page, "cur")["id"] == 1
    names = _names(win.contentItem())
    assert {"case_1", "case_2"} <= names
    assert "Taking data out" in win.findChild(QObject, "caseHeadline").property("text")
    graph = win.findChild(QObject, "caseGraph")
    assert graph is not None
    ids = {n for n in names if n.startswith("node_")}
    assert any("dev:" in i for i in ids) and any("dir:" in i for i in ids) and len(ids) >= 6                  # the drive, the bursts, the archive, the hidden file
    assert win.findChild(QObject, "detExplained") is not None and win.findChild(QObject, "detNote") is not None
    assert {"cover_exfiltration", "area_Gather", "area_Transfer", "area_Transform"} <= names                    # the areas, covered or not: coverage, not steps


async def test_what_a_person_makes_of_it_is_sent_with_their_note(console):
    win, bridge, page = await _page(console)
    page.setProperty("note", "It was the Q3 close")
    from PySide6.QtCore import Q_ARG

    QMetaObject.invokeMethod(page, "review", Q_ARG("QVariant", "explained"), Q_ARG("QVariant", ""))
    await _wait(lambda: any(t == "detective.review" for t, _ in bridge.conn.seen))
    sent = next(p for t, p in bridge.conn.seen if t == "detective.review")
    assert sent == {"case_id": 1, "outcome": "explained", "note": "It was the Q3 close"}


async def test_only_an_admin_can_send_it_up_and_the_super_user_sees_every_machine(console):
    win, bridge, page = await _page(console, "admin")
    assert win.findChild(QObject, "detEscalate").property("visible") is True
    win2, bridge2, page2 = await _page(console, "super_user")
    assert win2.findChild(QObject, "detEscalate").property("visible") is False


async def test_a_dismissal_can_be_remembered_for_a_folder_or_a_drive_the_case_involves(console):
    from PySide6.QtCore import Q_ARG

    win, bridge, page = await _page(console)
    assert win.findChild(QObject, "detRememberFolder").property("visible") is True and win.findChild(QObject, "detRememberDrive").property("visible") is True
    QMetaObject.invokeMethod(page, "review", Q_ARG("QVariant", "dismissed"), Q_ARG("QVariant", "folder"))
    await _wait(lambda: any(t == "detective.review" for t, _ in bridge.conn.seen))
    sent = next(p for t, p in bridge.conn.seen if t == "detective.review")
    assert sent["outcome"] == "dismissed" and sent["remember"] == {"kind": "folder"}
