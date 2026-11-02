"""Rules on the disk and the network, and a threshold replayed against the last week's readings (the concept's rule builder)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from engine.control import events
from tests.conftest import requires_db

pytestmark = requires_db


async def test_a_rule_on_the_disk_or_the_network_fires_on_the_workers_readings(engine, org, connect):
    a1, w1 = await connect("cid-a1"), await connect("cid-w1")
    disk = (await a1.ok("control.event_create", {"type": "threshold.disk", "match": {"percent": 90}, "action_ids": [], "name": "Disk nearly full"}))["event"]
    net = (await a1.ok("control.event_create", {"type": "threshold.network", "match": {"kbps": 5000}, "action_ids": [], "name": "Busy network"}))["event"]
    await w1.ok("control.metrics", {"cpu": 10, "memory": 20, "idle_s": 0, "disk": 95.0, "net_kbps": 100.0})
    await events.evaluate_polled(engine)
    fired = {r["target_id"] for r in await engine.db.pool.fetch("SELECT target_id FROM audit_log WHERE action_type = 'event.fired'")}
    assert str(disk["id"]) in fired and str(net["id"]) not in fired
    board = (await a1.ok("automation.board"))["rules"]
    assert next(r for r in board if r["event_id"] == disk["id"])["when"] == "the system drive is 90% full or more"


async def test_a_threshold_is_replayed_against_the_last_week(engine, org, connect):
    a1 = await connect("cid-a1")
    now = datetime.now(timezone.utc)
    for i, v in enumerate([50, 95, 96, 97, 40, 92, 93]):                   # ten minutes apart; two runs over 90, the second still going
        await engine.db.pool.execute("INSERT INTO metric_samples (pc_id, sampled_at, cpu, memory, idle_s, disk) VALUES ($1, $2, $3, 0, 0, $4)",
                                     org["w1_pc"], now - timedelta(minutes=10 * (7 - i)), float(v), float(v))
    one = await a1.ok("control.threshold_backtest", {"type": "threshold.cpu", "value": 90})
    assert one["total"] == 2 and sum(one["per_day"][-2:]) == 2 and one["by_machine"] == {"FIN-01": 2} and one["now"] == ["FIN-01"]
    long = await a1.ok("control.threshold_backtest", {"type": "threshold.cpu", "value": 90, "minutes": 30})
    assert long["total"] == 1 and long["now"] == []                        # only the first run lasted three readings
    net = await a1.ok("control.threshold_backtest", {"type": "threshold.network", "value": 10})
    assert net["total"] == 0 and net["unread"] == 1                         # these samples have no network reading
    assert await a1.err("control.threshold_backtest", {"type": "threshold.cpu"}) == "invalid"
    assert await a1.err("control.threshold_backtest", {"type": "usb.inserted", "value": 1}) == "invalid"


@pytest.mark.organisation
async def test_an_it_admins_rule_that_names_no_machines_covers_every_machine(engine, org, connect):
    a1 = await connect("cid-a1")
    await connect("cid-w1")
    a2 = await connect("cid-a2")                                           # HR's Admin: a machine of another department
    ev = (await a1.ok("control.event_create", {"type": "threshold.cpu", "match": {"percent": 50}, "action_ids": [], "name": "Busy"}))["event"]
    await a2.ok("control.metrics", {"cpu": 99, "memory": 20, "idle_s": 0})
    await events.evaluate_polled(engine)
    hit = await engine.db.pool.fetchval("SELECT count(*) FROM audit_log WHERE action_type = 'event.fired' AND target_id = $1 "
                                        "AND (detail->>'pc_id')::int = $2", str(ev["id"]), org["a2_pc"])
    assert hit == 1
