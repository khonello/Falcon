"""The Calendar page's read: what is coming, from the deadlines, the rules that run on a clock and the announcements waiting to go out."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from engine.console.calendar import occurrences
from tests.conftest import requires_db


def _utc(*a: int) -> datetime:
    return datetime(*a, tzinfo=timezone.utc)


def test_a_repeating_rule_fires_at_its_time_on_its_weekdays_and_a_scheduled_one_once():
    now, until = _utc(2026, 10, 1, 13, 20), _utc(2026, 10, 12)
    weekdays = {"type": "time.recurring", "match": {"at": "09:00", "days": [0, 1, 2, 3, 4]}}
    got = occurrences(weekdays, now, until)
    assert [(t.day, t.hour) for t in got] == [(2, 9), (5, 9), (6, 9), (7, 9), (8, 9), (9, 9)]      # not today (09:00 has passed), not the weekend
    assert [t.day for t in occurrences({"type": "time.recurring", "match": {"at": "14:00"}}, now, _utc(2026, 10, 4))] == [1, 2, 3]   # no days: every day
    once = {"type": "time.scheduled", "match": {"at": "2026-10-03T08:30:00+00:00"}}
    assert occurrences(once, now, until) == [_utc(2026, 10, 3, 8, 30)]
    assert occurrences(once, _utc(2026, 10, 4), until) == []                                       # already gone by
    assert occurrences({"type": "time.recurring", "match": {"interval_s": 3600}}, now, until) == []   # an interval has no wall-clock times
    assert occurrences({"type": "usb.inserted"}, now, until) == []
    assert occurrences({"type": "time.recurring", "match": {"at": "nine"}}, now, until) == []


pytestmark = requires_db


async def test_an_admin_sees_what_is_coming_in_their_own_department_only(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    a2 = await connect("cid-a2")
    now = datetime.now(timezone.utc)

    # a department task from the Super User (told to a1 only), a scheduled announcement, one withdrawn, one already sent
    await su.ok("task.dept_create", {"department_id": org["fin"], "title": "Prepare the stock count", "deadline_at": (now + timedelta(days=3)).isoformat()})
    out = (await a1.ok("alerts.create", {"type": "announcement", "audience": "department", "department_id": org["fin"], "title": "Fire drill",
                                          "body": "Friday", "deliver_at": (now + timedelta(days=2)).isoformat()}))["alert_id"]
    gone = (await a1.ok("alerts.create", {"type": "announcement", "audience": "department", "department_id": org["fin"], "title": "Withdrawn",
                                           "body": "x", "deliver_at": (now + timedelta(days=2)).isoformat()}))["alert_id"]
    await a1.ok("alerts.cancel", {"alert_id": gone})
    await a1.ok("alerts.create", {"type": "announcement", "audience": "department", "department_id": org["fin"], "title": "Already sent", "body": "y"})

    # a rule that runs on a clock, and one that does not
    daily = (await a1.ok("control.event_create", {"type": "time.recurring", "match": {"at": "09:00"}, "action_ids": [], "name": "Daily maintenance"}))["event"]
    await a1.ok("control.event_create", {"type": "usb.inserted", "action_ids": [], "name": "USB"})

    board = await a1.ok("calendar.board")
    items = board["items"]
    titles = {(i["kind"], i["title"]) for i in items}
    assert ("task", "Prepare the stock count") in titles and ("announcement", "Fire drill") in titles
    assert ("announcement", "Withdrawn") not in titles and ("announcement", "Already sent") not in titles
    rules = [i for i in items if i["kind"] == "rule"]
    assert rules and {i["title"] for i in rules} == {"Daily maintenance"} and all(i["to"] == ["automation", str(daily["id"])] for i in rules)
    assert [i["at"] for i in items] == sorted(i["at"] for i in items)                       # soonest first
    assert out and board["cut"] is False
    # a repeating rule is drawn to the end of next month and no further, so one daily rule does not fill the calendar
    last = datetime.fromisoformat(rules[-1]["at"])
    assert last < (now.replace(day=1) + timedelta(days=95)).replace(day=1)

    # another department sees none of it, and the Super User sees the department task and every scheduled announcement, no rules
    assert (await a2.ok("calendar.board"))["items"] == []
    su_items = (await su.ok("calendar.board"))["items"]
    assert {(i["kind"], i["title"]) for i in su_items} == {("task", "Prepare the stock count"), ("announcement", "Fire drill")}


async def test_a_task_past_its_date_is_listed_on_the_day_it_was_due_and_the_window_is_bounded(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    now = datetime.now(timezone.utc)
    await su.ok("task.dept_create", {"department_id": org["fin"], "title": "Late one", "deadline_at": (now - timedelta(days=1)).isoformat()})
    await su.ok("task.dept_create", {"department_id": org["fin"], "title": "Far away", "deadline_at": (now + timedelta(days=300)).isoformat()})
    items = (await a1.ok("calendar.board", {"days": 30}))["items"]
    assert [(i["title"], i["overdue"]) for i in items] == [("Late one", True)]
    assert await a1.err("calendar.board", {"days": "soon"}) == "invalid"
