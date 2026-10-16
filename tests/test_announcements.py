"""Announcements: who may send to whom, what each person sees, a title, scheduling and withdrawing -- delivered is enough (no read tracking)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from engine.hierarchy import alerts
from tests.conftest import requires_db

pytestmark = requires_db


def _later(minutes: int) -> str:
    return (datetime.now(timezone.utc) + timedelta(minutes=minutes)).isoformat()


@requires_db
async def test_a_title_travels_with_the_message_and_the_reader_sees_who_sent_it(engine, org, connect):
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    await a1.ok("alerts.create", {"type": "announcement", "audience": "department", "department_id": org["fin"],
                                  "title": "  Month   end  ", "body": "Close your books by Friday."})
    pushed = [p for p in await w1.drain_pushes() if p.type == "alert.delivered"]
    assert pushed and pushed[0].payload["title"] == "Month end" and pushed[0].payload["body"] == "Close your books by Friday."
    (mine,) = (await w1.ok("alerts.list"))["alerts"]
    assert mine["title"] == "Month end" and mine["alert_type"] == "announcement" and mine["from_name"] is not None
    # no title is fine
    await a1.ok("alerts.create", {"type": "routine", "audience": "department", "department_id": org["fin"], "body": "no title"})
    assert [a["title"] for a in (await w1.ok("alerts.list"))["alerts"]] == [None, "Month end"]


async def test_each_sees_what_they_sent_and_the_super_user_sees_all(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    a2 = await connect("cid-a2")
    w1 = await connect("cid-w1")
    await a1.ok("alerts.create", {"type": "announcement", "audience": "department", "department_id": org["fin"], "body": "from a1"})
    await a2.ok("alerts.create", {"type": "announcement", "audience": "department", "department_id": org["hr"], "body": "from a2"})
    await su.ok("alerts.create", {"type": "emergency", "audience": "all_users", "body": "from su"})
    assert [a["body"] for a in (await a1.ok("alerts.sent"))["alerts"]] == ["from a1"]
    assert sorted(a["body"] for a in (await su.ok("alerts.sent"))["alerts"]) == ["from a1", "from a2", "from su"]
    sent = {a["body"]: a for a in (await su.ok("alerts.sent"))["alerts"]}
    assert sent["from su"]["audience_label"] == "Everyone" and sent["from a1"]["status"] == "delivered"
    assert await w1.err("alerts.sent") == "forbidden"
    assert await w1.err("alerts.cancel", {"alert_id": 1}) == "forbidden"


async def test_a_scheduled_one_can_be_withdrawn_before_it_goes_and_not_after(engine, org, connect):
    a1 = await connect("cid-a1")
    a2 = await connect("cid-a2")
    su = await connect("cid-su")
    w1 = await connect("cid-w1")
    first = (await a1.ok("alerts.create", {"type": "announcement", "audience": "department", "department_id": org["fin"],
                                           "body": "later", "deliver_at": _later(30)}))["alert_id"]
    assert (await a1.ok("alerts.sent"))["alerts"][0]["status"] == "scheduled"
    assert (await w1.ok("alerts.list"))["alerts"] == []                                          # not yet
    assert await a2.err("alerts.cancel", {"alert_id": first}) == "not_found"                      # someone else's
    assert (await a1.ok("alerts.cancel", {"alert_id": first}))["status"] == "withdrawn"
    assert (await a1.ok("alerts.sent"))["alerts"][0]["status"] == "withdrawn"
    assert await a1.err("alerts.cancel", {"alert_id": first}) == "conflict"
    assert await alerts.deliver_due(engine) == 0                                                  # withdrawn: never goes out
    sent_now = (await a1.ok("alerts.create", {"type": "announcement", "audience": "department", "department_id": org["fin"], "body": "now"}))["alert_id"]
    assert await a1.err("alerts.cancel", {"alert_id": sent_now}) == "conflict"                    # delivered stays delivered
    due = (await su.ok("alerts.create", {"type": "announcement", "audience": "all_users", "body": "due",
                                         "deliver_at": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()}))["alert_id"]
    assert await alerts.deliver_due(engine) == 1
    assert due and "due" in [a["body"] for a in (await w1.ok("alerts.list"))["alerts"]]
