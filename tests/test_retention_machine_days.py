"""Old machine days are asked about on the Issues page, never deleted by themselves (the user, 3 Nov 2026; engine/console/retention.py)."""

from __future__ import annotations

from datetime import date, datetime, timedelta, timezone

import pytest

from engine.console import retention
from tests.conftest import requires_db

pytestmark = [requires_db, pytest.mark.organisation]


async def _days(engine, pc_id: int, *ages: int) -> None:
    today = datetime.now().astimezone().date()
    for age in ages:
        await engine.db.accounts.check_in(pc_id, today - timedelta(days=age))


async def _rows(engine, org) -> list[date]:
    """The Workers' machine days (an Admin's own machine checks in today when it connects)."""
    return [r["day"] for r in await engine.db.pool.fetch("SELECT day FROM pc_days WHERE pc_id = ANY($1::int[]) ORDER BY day", [org["w1_pc"], org["w2_pc"]])]


async def test_old_machine_days_raise_one_issue_and_an_admin_deletes_them(engine, org, connect):
    a1, a2 = await connect("cid-a1"), await connect("cid-a2")
    assert await retention.ask_about_machine_days(engine) is None                       # nothing old: nothing asked
    await _days(engine, org["w1_pc"], 1, 5, 120, 200)
    await _days(engine, org["w2_pc"], 95)
    issue_id = await retention.ask_about_machine_days(engine)
    assert issue_id is not None and await retention.ask_about_machine_days(engine) == issue_id      # one open issue, brought up to date
    assert "issue.raised" in a2.push_types(await a2.drain_pushes())                                 # every Admin hears of it (version 1)
    got = await a1.ok("issues.get", {"issue_id": issue_id})
    assert got["issue"]["type"] == "retention" and got["issue"]["subject"] == "3 days of records on 2 machines"
    assert {o["key"] for o in got["options"]} == {"delete_old", "keep_old"}
    assert len(await _rows(engine, org)) == 5                                                            # nothing is deleted until someone chooses
    await a1.ok("issues.act", {"issue_id": issue_id, "key": "delete_old"})
    today = datetime.now().astimezone().date()
    assert await _rows(engine, org) == [today - timedelta(days=5), today - timedelta(days=1)]
    assert (await a1.ok("issues.get", {"issue_id": issue_id}))["issue"]["state"] == "resolved"
    audited = await engine.db.pool.fetchrow("SELECT detail FROM audit_log WHERE action_type = 'retention.deleted'")
    assert audited["detail"]["rows"] == 3


async def test_kept_days_are_asked_about_again_when_the_cycle_comes_round(engine, org, connect):
    a1 = await connect("cid-a1")
    await _days(engine, org["w1_pc"], 100)
    issue_id = await retention.ask_about_machine_days(engine)
    await a1.ok("issues.act", {"issue_id": issue_id, "key": "keep_old"})
    assert len(await _rows(engine, org)) == 1
    assert await retention.ask_about_machine_days(engine) is None                                   # kept lately: not asked again tomorrow
    later = datetime.now(timezone.utc) + timedelta(days=retention.ASK_AGAIN_DAYS + 1)
    again = await retention.ask_about_machine_days(engine, now=later)
    assert again is not None and again != issue_id
