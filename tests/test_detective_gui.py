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
from PySide6.QtCore import Q_ARG, QMetaObject, QObject

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
    assert [c["id"] for c in prop(page, "cases")] == [1, 2] and "caseList" in names                      # both cases are rows of the standard list, the first one picked
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


async def test_marking_says_what_it_costs_before_it_is_done_and_a_huge_folder_cannot_be_ticked_through(console):
    win, bridge, _ = console("admin")
    page = await _open(win, bridge, "restricted/mark", "markFiles")
    box = win.findChild(QObject, "markAssess")
    assert box is not None and box.property("visible") is False                                   # nothing ticked yet: nothing to say
    page.setProperty("assessed", [{"path": "C:/proj", "verdict": "large", "tracked": 4200, "junk": 60000, "seconds": 130, "reasons": ["4,200 files to track will take about 2 minutes"],
                                   "basis": "measured over 3 earlier jobs on this Engine", "capacity": {"state": "quiet"}}])
    _pump(0.3)
    assert box.property("visible") is True and prop(page, "large") is True and prop(page, "tooLarge") is False
    assert win.findChild(QObject, "markConfirmLarge").property("visible") is True                  # a large one has to be agreed to
    page.setProperty("assessed", [{"path": "C:/huge", "verdict": "too_large", "tracked": 90000, "junk": 0, "seconds": 1800, "reasons": ["90,000 files is more than one mark can hold (20,000)"],
                                   "basis": "assumed (nothing measured yet)", "capacity": None}])
    _pump(0.3)
    assert prop(page, "tooLarge") is True and win.findChild(QObject, "markConfirmLarge").property("visible") is False


async def test_a_flow_waiting_for_a_restricted_owner_is_answered_on_the_flows_page(console):
    win, bridge, _ = console("super_user")
    page = await _open(win, bridge, "flows", "flowsView")
    page.setProperty("rAsks", [{"id": 5, "flow_id": 9, "name": "Payroll", "state": "asked", "sample_path": "C:/Finance/Payroll/p.xlsx", "flow": {"id": 9}}])
    _pump(0.4)
    assert "restrictedAsk_5" in _names(win.contentItem())                                       # (a delegate of the list, found through the visual tree)
    QMetaObject.invokeMethod(page, "answerRestricted", Q_ARG("QVariant", {"id": 5}), Q_ARG("QVariant", True))
    await _wait(lambda: any(t == "flow.restricted_consent" for t, _ in bridge.conn.seen))
    sent = next(p for t, p in bridge.conn.seen if t == "flow.restricted_consent")
    assert sent == {"consent_id": 5, "grant": True}


async def test_the_super_user_can_open_a_move_to_another_machine_from_the_registry(console):
    win, bridge, _ = console("super_user")
    page = await _open(win, bridge, "registry", "registryView")
    assert win.findChild(QObject, "handoverCard") is not None and win.findChild(QObject, "handoverCard").property("visible") is True
    QMetaObject.invokeMethod(page, "openHandover", Q_ARG("QVariant", True))
    await _wait(lambda: any(t == "handover.open" for t, _ in bridge.conn.seen))
    QMetaObject.invokeMethod(page, "openHandover", Q_ARG("QVariant", False))
    await _wait(lambda: any(t == "handover.cancel" for t, _ in bridge.conn.seen))


async def test_an_admin_does_not_see_the_move_of_the_super_user(console):
    win, bridge, _ = console("admin")
    bridge.connected.emit()
    win.setProperty("view", "machines")
    _pump(0.3)
    assert win.findChild(QObject, "handoverCard") is None


async def test_what_detective_suggests_is_shown_for_a_person_to_accept_or_dismiss_and_the_rules_can_be_taken_back(console):
    win, bridge, page = await _page(console)
    page.setProperty("proposals", [{"id": 4, "kind": "pause_flow", "title": "Pause flow #3? Its source machine FIN-01 is under an urgent case"},
                                   {"id": 5, "kind": "mark_folder", "title": r"Mark C:\Data\Reports as restricted?"}])
    page.setProperty("rules", [{"id": 8, "graph": "to_drive", "kind": "folder", "value": "E:", "host": "FIN-01"}])
    _pump(0.4)
    names = _names(win.contentItem())
    assert {"suggestions", "proposal_4", "proposal_5", "proposalYes_4", "proposalNo_5", "writtenRules", "rule_8", "ruleBack_8"} <= names
    QMetaObject.invokeMethod(page, "decide", Q_ARG("QVariant", {"id": 4}), Q_ARG("QVariant", True))
    await _wait(lambda: any(t == "proposals.decide" for t, _ in bridge.conn.seen))
    assert next(p for t, p in bridge.conn.seen if t == "proposals.decide") == {"proposal_id": 4, "accept": True}
    QMetaObject.invokeMethod(page, "takeBack", Q_ARG("QVariant", {"id": 8}))
    await _wait(lambda: any(t == "detective.rule_revoke" for t, _ in bridge.conn.seen))
    assert next(p for t, p in bridge.conn.seen if t == "detective.rule_revoke") == {"rule_id": 8}


async def test_a_flow_shows_what_restricted_material_it_waits_for_or_carries_and_who_can_take_it_back(console):
    win, bridge, _ = console("super_user")
    page = await _open(win, bridge, "flows", "flowsView")
    page.setProperty("flows", [{"id": 9, "source_hostname": "FIN-01", "source_path": "C:/out", "status": "paused", "pause_reason": "restricted:consent", "consent_status": "not_required",
                                "created_by_account_id": 2, "destinations": [{"id": 1, "destination_hostname": "FIN-02", "destination_path": "C:/in"}], "stages": [], "created_at": "2026-10-18T10:00:00Z"}])
    _pump(0.4)
    assert prop(page, "cur")["st"][0].startswith("Waiting for consent")                              # the list says why it is not copying
    page.setProperty("consents", [{"id": 5, "name": "Payroll", "state": "granted", "expires_at": None}, {"id": 6, "name": "Board", "state": "asked"}])
    page.setProperty("canDecide", [5])
    _pump(0.4)
    names = _names(win.contentItem())
    assert {"flowRestricted", "consent_5", "consent_6", "takeBack_5"} <= names and "takeBack_6" in names     # (an unanswered one has no button to show: the button is hidden, not absent)
    QMetaObject.invokeMethod(page, "takeBack", Q_ARG("QVariant", {"id": 5}))
    await _wait(lambda: any(t == "flow.restricted_revoke" for t, _ in bridge.conn.seen))
    assert next(p for t, p in bridge.conn.seen if t == "flow.restricted_revoke") == {"consent_id": 5}


async def test_what_waits_on_the_super_user_includes_suggestions_flows_to_allow_and_a_machine_asking_to_take_over(console):
    win, bridge, _ = console("super_user")
    real = bridge.conn.call

    async def call(type_, payload=None):
        if type_ == "proposals.list":
            return {"proposals": [{"id": 4, "kind": "pause_flow", "title": "Pause flow #3? Its source machine FIN-01 is under an urgent case", "created_at": "2026-10-18T10:00:00Z"}]}
        if type_ == "flow.restricted_waiting":
            return {"waiting": [{"id": 5, "flow_id": 9, "name": "Payroll", "sample_path": "C:/Finance/Payroll/p.xlsx", "asked_at": "2026-10-18T10:05:00Z"}]}
        if type_ == "handover.status":
            return {"open": True, "waiting": [{"id": 7, "hostname": "SU-NEW", "created_at": "2026-10-18T10:10:00Z"}]}
        return await real(type_, payload or {})

    bridge.conn.call = call
    await _open(win, bridge, "overview", "overviewView")
    loader = win.findChild(QObject, "page")                 # (a page that was left is still around a moment: the loader holds the one on show)
    await _wait(lambda: loader.property("item") is not None and loader.property("item").metaObject().className().startswith("SuOverviewPage"))
    page = loader.property("item")
    await _wait(lambda: {x["kind"] for x in prop(page, "q") or []} >= {"proposal", "restricted", "handover"})
    q = {x["kind"]: x for x in prop(page, "q")}
    assert q["handover"]["title"] == "SU-NEW is asking to become your machine" and q["handover"]["options"][0]["go"] == ["registry", "ask"]
    assert [o["key"] for o in q["proposal"]["options"]] == ["yes", "no"] and q["restricted"]["title"].startswith("Flow 9 wants to carry Payroll")


async def test_an_admin_s_waiting_count_includes_what_detective_suggests_and_the_flows_they_may_allow(console):
    win, bridge, _ = console("admin")
    real = bridge.conn.call

    async def call(type_, payload=None):
        if type_ == "overview.admin":
            return {"waiting": {"total": 3, "suggestions": 2, "flows_to_allow": 1}}
        return await real(type_, payload or {})

    bridge.conn.call = call
    page = await _open(win, bridge, "overview", "overviewView")
    await _wait(lambda: prop(page, "suggestions") == 2 and prop(page, "toAllow") == 1)


async def test_the_super_user_s_overview_is_the_four_core_features_two_by_two_with_what_waits_above_them(console):
    win, bridge, _ = console("super_user")
    real = bridge.conn.call

    async def call(type_, payload=None):
        if type_ == "detective.overview":
            return {"by_level": {"urgent": 2, "case": 1, "noted": 0}, "by_intent": {}, "reviewed": 0}
        if type_ == "detective.cases":
            return {"cases": [{"id": 1, "intent": "Taking data out", "host": "FIN-02", "level": "urgent"}]}
        if type_ == "flow.list":
            return {"flows": [{"id": 1, "status": "active", "source_hostname": "A", "destinations": []},
                              {"id": 2, "status": "paused", "pause_reason": "restricted:consent", "source_hostname": "B", "destinations": [{"destination_hostname": "C"}]}]}
        if type_ == "marks.list":
            return {"marks": [{"id": 1, "name": "Payroll", "host": "FIN-02", "copies": 2, "carried_by": [2]}]}
        return await real(type_, payload or {})

    bridge.conn.call = call
    await _open(win, bridge, "overview", "overviewView")
    loader = win.findChild(QObject, "page")
    await _wait(lambda: loader.property("item") is not None and loader.property("item").metaObject().className().startswith("SuOverviewPage"))
    page = loader.property("item")
    await _wait(lambda: prop(page, "ov")["by_level"]["urgent"] == 2 and len(prop(page, "flows")) == 2 and len(prop(page, "marks")) == 1)
    for name in ("waitingBand", "quadTasks", "quadFlows", "quadRestricted", "quadDetective", "orgStrip"):
        assert page.findChild(QObject, name) is not None, name
    h = lambda n: page.findChild(QObject, n).property("height")          
    assert h("quadTasks") == h("quadFlows") and h("quadRestricted") == h("quadDetective")          # side by side, one height
    assert prop(page, "carried") == 1 and prop(page, "copies") == 2 and len(prop(page, "asking")) == 1
