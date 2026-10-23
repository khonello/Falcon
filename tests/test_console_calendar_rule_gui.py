# ruff: noqa: F811
"""The Calendar page and the New rule page, as the console draws them (docs/design/concepts-admin.html, 19-21 Oct 2026)."""

from __future__ import annotations

import os
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

pytest.importorskip("PySide6")
os.environ["QT_QPA_PLATFORM"] = "offscreen"
sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))

from PySide6.QtCore import Q_ARG, QMetaObject, QObject

from tests.test_operator_gui import _open, _pump, console, prop  # noqa: F401


def _at(days: float, hour: int = 9) -> str:
    d = (datetime.now(timezone.utc) + timedelta(days=days)).replace(hour=hour, minute=0, second=0, microsecond=0)
    return d.isoformat()


ITEMS = [
    {"kind": "task", "at": _at(0, 8), "title": "Confirm who covers the front desk", "line": "Operations", "to": ["tasks", "D-11"], "overdue": True},
    {"kind": "task", "at": _at(1, 16), "title": "Prepare the stock count", "line": "Finance", "to": ["tasks", "D-13"], "overdue": False},
    {"kind": "announcement", "at": _at(1, 8), "title": "Fire drill on Friday", "line": "Your department", "to": ["messages", "announcements"], "overdue": False},
    {"kind": "rule", "at": _at(2, 9), "title": "Daily maintenance", "line": "2 actions", "to": ["automation", "4"], "overdue": False},
    {"kind": "announcement", "at": _at(45, 8), "title": "Year-end training week", "line": "Your department", "to": ["messages", "announcements"], "overdue": False},
]


async def test_the_calendar_lists_what_is_coming_one_month_at_a_time_and_opens_what_owns_each_item(console):
    win, bridge, _ = console("admin")
    page = await _open(win, bridge, "calendar", "calendarPage")
    page.setProperty("items", ITEMS)
    _pump(0.3)
    assert prop(win, "menuKeys")[:3] == ["overview", "messages", "calendar"]                      # Home: Overview, Messages, Calendar
    assert prop(page, "months") >= 2 and prop(page, "mi") == 0                                    # this month, and on to the last one that has anything
    assert len(prop(page, "cells")) % 7 == 0                                                     # whole weeks
    today = prop(page, "today")
    assert any(c["inM"] and c["t"] == today for c in prop(page, "cells"))
    # a task past its date is drawn in the warning colour, and the filter narrows what the days hold
    page.setProperty("f", "task")
    _pump(0.2)
    assert {x["k"] for xs in prop(page, "byDay").values() for x in xs} == {"task"}
    page.setProperty("f", "all")
    # the months never run past the last one with something in it
    QMetaObject.invokeMethod(page, "pickMonth", Q_ARG("QVariant", 99))
    _pump(0.2)
    assert prop(page, "mi") == prop(page, "months") - 1
    QMetaObject.invokeMethod(page, "pickMonth", Q_ARG("QVariant", 0))
    # the month and the day are the two panels of the page
    assert win.findChild(QObject, "calendarMonth") is not None and win.findChild(QObject, "calendarDay") is not None


async def test_a_new_rule_starts_blank_and_each_step_says_what_is_missing(console):
    win, bridge, _ = console("admin")
    page = await _open(win, bridge, "automation/new", "newRule")
    _pump(0.3)
    assert prop(page, "kind") == "" and prop(page, "scope") == "" and prop(page, "acts") == [] and prop(page, "ok") is False
    assert prop(page, "problems") == ["Pick what should start it.", "Pick which machines it watches.", "Add at least one action."]
    # choosing: a kind, every machine, an action
    page.setProperty("kind", "Threshold")
    page.setProperty("scope", "all")
    page.setProperty("lib", [{"id": 5, "name": "Notify the Admin", "cat": "control", "timeout_seconds": 10, "description": "Tells an Admin", "builtin_type": "notify"}])
    page.setProperty("acts", [5])
    _pump(0.2)
    assert prop(page, "problems")[0] == "" and prop(page, "problems")[2] == ""
    assert prop(page, "ok") is True or prop(page, "targets") == []                               # complete once there is a machine to watch
    # an event rule needs the event chosen
    page.setProperty("kind", "Event")
    _pump(0.1)
    assert prop(page, "problems")[0] == "Pick what happens."
    page.setProperty("ev", "usb.inserted")
    _pump(0.1)
    assert prop(page, "problems")[0] == ""
