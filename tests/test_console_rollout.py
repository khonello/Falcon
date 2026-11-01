"""The rollout gate: who holds the next version back, leaving machines out, approving with a reason, retrying, adoption (WP7)."""

from __future__ import annotations

from tests.conftest import requires_db

pytestmark = requires_db

ALL_PCS = ("su_pc", "a1_pc", "w1_pc", "w2_pc", "a2_pc")


async def _everyone_on(engine, org, version_id: int, version: str, except_: tuple[str, ...] = ()) -> None:
    for key in ALL_PCS:
        if key not in except_:
            await engine.db.updates.record_attempt(org[key], version_id, True, version_id)
            await engine.db.updates.log_version(org[key], version)


async def test_failed_installs_say_what_went_wrong_and_adoption_counts_machines_day_by_day(engine, org, connect):
    su = await connect("cid-su")
    w1 = await connect("cid-w1")
    first = await su.ok("updates.approve", {"version": "1.0"})
    await _everyone_on(engine, org, first["version_id"], "1.0")
    await su.ok("updates.approve", {"version": "1.1"})                                           # everyone runs 1.0, so 1.1 is approved: now everyone is behind it
    for _ in range(2):
        await w1.ok("updates.report_status", {"version": "1.1", "succeeded": False, "running": "1.0", "error": "A file was in use"})
    gate = await su.ok("rollout.gate")
    row = next(h for h in gate["holding"] if h["hostname"] == "FIN-01")
    assert row["attempts"] == 2 and row["last_error"] == "A file was in use" and row["last_attempt_at"] and row["should_run"] == "1.1"
    assert gate["strip"]["failed_installs"] == 2 and gate["strip"]["failed_hosts"] == [{"hostname": "FIN-01", "n": 2}]
    assert gate["strip"]["holding"] == 5 and gate["strip"]["running"] == 0

    await w1.ok("updates.report_status", {"version": "1.1", "succeeded": True, "running": "1.1"})
    second = (await su.ok("rollout.gate"))["adoption"]
    [today] = second
    assert today["n"] == 1 and today["joined"] == ["FIN-01"] and today["note"] == "1.1 approved"
    assert all(h["hostname"] != "FIN-01" for h in (await su.ok("rollout.gate"))["holding"]) and (await su.ok("rollout.gate"))["strip"]["holding"] == 4


async def test_the_file_event_history_ages_out_with_the_audit_trail_and_nothing_newer_is_touched(engine, org):
    db = engine.db
    await db.pool.execute("INSERT INTO file_events (pc_id, op, path, occurred_at) VALUES ($1, 'create', 'C:/old.txt', now() - interval '120 days')", org["w1_pc"])
    await db.pool.execute("INSERT INTO file_events (pc_id, op, path, occurred_at) VALUES ($1, 'create', 'C:/new.txt', now() - interval '10 days')", org["w1_pc"])
    await engine.audit.run_retention()
    assert [r["path"] for r in await db.pool.fetch("SELECT path FROM file_events ORDER BY id")] == ["C:/new.txt"]


async def test_retention_says_what_it_did_and_a_failing_part_does_not_stop_the_rest(engine, org, caplog):
    import logging

    caplog.set_level(logging.INFO)
    await engine.db.pool.execute("INSERT INTO file_events (pc_id, op, path, occurred_at) VALUES ($1, 'create', 'C:/old.txt', now() - interval '200 days')", org["w1_pc"])
    await engine.audit.run_retention()
    text = caplog.text
    assert "retention: starting" in text and "retention: ok, 1 file events older than" in text and "retention: ok," in text and "FAILED" not in text

    async def boom(days):
        raise RuntimeError("disk full")

    engine.db.audit.purge_file_events_older_than = boom
    caplog.clear()
    await engine.audit.run_retention()
    assert "retention: FAILED to clear file events" in caplog.text and "retention: ok" in caplog.text            # the other parts still ran
