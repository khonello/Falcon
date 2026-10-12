"""Rules (the standard) and deviations (departures from it), recorded by the three shapes: never, follow, limit (WP4)."""

from __future__ import annotations

import asyncio
import dataclasses
from datetime import datetime, timedelta, timezone

from engine.console import accountability
from protocol import encode, request
from tests.conftest import requires_db

pytestmark = requires_db


def _later(**kw):
    return datetime.now(timezone.utc) + timedelta(**kw)


async def test_the_standard_has_locked_built_in_rules_and_the_super_users_patterns(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    listing = await a1.ok("rules.list")                                     # an Admin reads the same standard
    assert [r["code"] for r in listing["rules"]] == ["B-1", "B-2", "B-3", "B-4"] and all(r["locked"] and r["on"] for r in listing["rules"])
    assert listing["rules"][0]["sentence"] == "A copy of a restricted file appears where it is not allowed: always a deviation."
    assert "within 2 days" in listing["rules"][2]["sentence"] and listing["rules"][0]["set_by"] == "Falcon"
    assert await a1.err("rules.create", {"name": "x", "shape": "never", "trigger": "file"}) == "forbidden"
    assert await a1.err("rules.library") == "forbidden"

    lib = await su.ok("rules.library")
    assert {p["key"] for p in lib["patterns"]} >= {"restricted-leaves", "unanswered-help", "past-update-limit", "admin-outside", "out-of-hours"}
    assert "answer" in lib["follow"]["help"] and set(lib["periods"]) == {"hour", "day", "week"}

    for bad in ({"shape": "never", "trigger": "help"}, {"shape": "follow", "trigger": "help", "expect": "seen", "within": 5},
                {"shape": "follow", "trigger": "help", "expect": "answer", "within": 0}, {"shape": "limit", "reading": "nonsense", "limit": {"n": 1, "per": "day"}},
                {"shape": "limit", "reading": "outhours", "limit": {"n": -1, "per": "day"}}, {"shape": "limit", "reading": "outhours", "limit": {"n": 1, "per": "year"}},
                {"shape": "never", "trigger": "file", "who": "aliens"}, {"shape": "never", "trigger": "file", "depts": [999]},
                {"shape": "never", "trigger": "file", "resp": {"action": True}}, {"shape": "poem"}):
        assert (await su.call("rules.create", {"name": "bad", **bad})).error["code"] in ("invalid", "not_found"), bad
    made = (await su.ok("rules.create", {"name": "Help requests are answered", "shape": "follow", "trigger": "help", "expect": "answer", "within": 60,
                                         "who": "admins", "resp": {"report": True, "admin": True}}))["rule"]
    assert made["code"] == "O-1" and made["locked"] is False and made["set_by"] == "You" and "within 1 hour" in made["sentence"]
    assert (await a1.ok("rules.list"))["rules"][-1]["set_by"] != "You"                       # "set by the Super User" in the Admin's console
    assert await a1.err("rules.switch", {"rule_id": made["id"], "on": False}) == "forbidden"

    builtin = listing["rules"][0]["id"]
    assert await su.err("rules.switch", {"rule_id": builtin, "on": False}) == "forbidden"         # built into Falcon
    assert await su.err("rules.update", {"rule_id": builtin, "within": 5}) == "forbidden"
    updated = (await su.ok("rules.update", {"rule_id": made["id"], "within": 120, "name": "Help requests are answered in two hours"}))["rule"]
    assert updated["spec"]["within"] == 120 and "within 2 hours" in updated["sentence"] and updated["name"].endswith("two hours")
    assert (await su.err("rules.update", {"rule_id": made["id"], "within": 0})) == "invalid"
    off = (await su.ok("rules.switch", {"rule_id": made["id"], "on": False}))["rule"]
    assert off["on"] is False and (await su.ok("rules.list"))["summary"] == {"rules": 5, "on": 4, "broken_this_week": 0, "kept": 4}
    assert await su.err("rules.switch", {"rule_id": made["id"], "on": "yes"}) == "invalid"
    assert {e["action_type"] for e in (await su.ok("audit.events", {"kinds": ["admin"]}))["events"]} >= {"rule.created", "rule.updated", "rule.switched"}


async def test_a_never_rule_records_a_deviation_with_its_context_and_evidence_and_a_person_gives_it_an_outcome(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    a2 = await connect("cid-a2")
    w1 = await connect("cid-w1")
    await su.drain_pushes()
    await a1.ok("index.event", {"event": {"op": "create", "path": "C:/resources/restricted/salaries.xlsx", "hash": "SECRET"}})
    await a1.ok("hierarchy.traverse", {"pc_id": org["w1_pc"], "force": True})                  # an Admin in the machine around that time
    await w1.ok("index.event", {"event": {"op": "copy", "path": "C:/Users/ama/Downloads/salaries-copy.xlsx", "hash": "SECRET"}})

    res = await su.ok("deviations.list")
    [dev] = res["deviations"]
    assert dev["code"].startswith("D-") and dev["rule"]["code"] == "B-1" and dev["rule"]["locked"] and dev["kind"] == "worker"
    assert dev["severity"] == "high" and dev["host"] == "FIN-01" and dev["short"] == "Copy of salaries-copy.xlsx on FIN-01"
    assert dev["expected"] == "Stay where a restricted file is allowed" and dev["happened"].startswith("A copy in ") and dev["outcome"] == "open"
    assert dev["who"] and dev["who_sub"] == "FIN-01 · Finance"
    assert res["summary"] == {"total": 1, "open": 1, "by_kind": {"pc": 0, "worker": 1, "admin": 0, "dept": 0}}
    assert res["by_rule"][0]["code"] == "B-1" and res["per_day"][0]["open"] == 1 and res["per_day"][0]["by_severity"] == {"high": 1}
    assert {"deviation.raised", "report.new"} <= set(su.push_types(await su.drain_pushes()))
    assert await a1.err("deviations.list") == "forbidden" and await a2.err("deviations.get", {"deviation_id": dev["id"]}) == "forbidden"

    page = await su.ok("deviations.get", {"deviation_id": dev["id"]})
    assert any("Recorded: Restricted files stay where they are" in c["what"] for c in page["context"])
    assert any("Entered FIN-01" in c["what"] for c in page["context"])
    ev = page["evidence"]
    assert any("was signed in to FIN-01 at the time" in e for e in ev)
    assert any("entered FIN-01" in e and "before it" in e for e in ev)                           # the Admin who went in a moment earlier: a fact
    assert any("issue was open on FIN-01" in e for e in ev)
    assert not any("because" in e.lower() or "reason" in e.lower() for e in ev)                  # the system never states a cause

    # a person's own words are the only explanation
    assert await su.err("deviations.outcome", {"deviation_id": dev["id"], "outcome": "explained"}) == "invalid"
    assert await su.err("deviations.outcome", {"deviation_id": dev["id"], "outcome": "accepted", "note": "  "}) == "invalid"
    assert await su.err("deviations.outcome", {"deviation_id": dev["id"], "outcome": "forgiven"}) == "invalid"
    done = (await su.ok("deviations.outcome", {"deviation_id": dev["id"], "outcome": "explained", "note": "Approved by the finance lead for the audit."}))["deviation"]
    assert done["outcome"] == "explained" and done["note"].startswith("Approved") and done["by"] and done["decided_at"]
    after = await su.ok("deviations.list")
    assert after["summary"]["open"] == 0 and after["summary"]["total"] == 1 and after["per_day"][0]["dealt"] == 1
    assert (await su.ok("deviations.list", {"outcome": "open"}))["deviations"] == []
    reopened = (await su.ok("deviations.outcome", {"deviation_id": dev["id"], "outcome": "open"}))["deviation"]
    assert reopened["outcome"] == "open" and reopened["note"] is None
    assert (await su.ok("deviations.outcome", {"deviation_id": dev["id"], "outcome": "dismissed"}))["deviation"]["outcome_label"] == "Dismissed"

    # the record keeps the rule as it was; an organisation rule on the same trigger adds its own deviation (once per violation)
    org_rule = (await su.ok("rules.create", {"name": "Restricted copies are locked down", "shape": "never", "trigger": "file", "severity": "critical",
                                             "resp": {"report": False, "admin": True}}))["rule"]
    await w1.ok("index.event", {"event": {"op": "copy", "path": "C:/Users/ama/Desktop/again.xlsx", "hash": "SECRET"}})
    grouped = await su.ok("deviations.list", {"group": "rule"})
    assert {g["key"]: g["n"] for g in grouped["groups"]} == {"B-1": 2, "O-1": 1}
    assert grouped["deviations"][0]["severity"] in ("critical", "high")
    assert (await su.ok("deviations.list", {"rule_id": org_rule["id"]}))["deviations"][0]["rule"]["code"] == "O-1"
    assert "deviation.raised" in a1.push_types(await a1.drain_pushes())                          # resp.admin: the department's Admin is told
    assert len((await su.ok("deviations.list", {"group": "department"}))["groups"]) == 1
    assert (await su.ok("deviations.list", {"kind": "pc"}))["deviations"] == []
    assert await su.err("deviations.list", {"kind": "alien"}) == "invalid"


async def test_a_follow_rule_is_watched_and_a_deviation_is_recorded_only_when_it_is_not_kept_in_time(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    w2 = await connect("cid-w2")
    await su.ok("rules.create", {"name": "Help requests are answered", "shape": "follow", "trigger": "help", "expect": "answer", "within": 60,
                                 "who": "admins", "resp": {"report": True, "admin": True}})
    first = await w1.ok("assistance.ping", {"to_account_id": org["a1"]})
    await w1.ok("assistance.ping", {"to_account_id": org["a1"]})                                      # a second ping is the same request
    await w2.ok("assistance.ping", {"to_account_id": org["a1"]})
    assert await engine.db.pool.fetchval("SELECT count(*) FROM rule_watches WHERE state = 'open'") == 2
    await a1.ok("assistance.respond", {"ping_id": first["ping_id"]})                                  # w1's is answered in time

    assert await accountability.sweep(engine, _later(minutes=30)) == 0                                # not due yet
    assert await accountability.sweep(engine, _later(minutes=90)) == 1                                # w2's was not answered
    [dev] = (await su.ok("deviations.list"))["deviations"]
    assert dev["rule"]["code"] == "O-1" and dev["kind"] == "admin" and dev["short"].startswith("Help request from FIN-02")
    assert dev["expected"] == "An Admin answers the ping within 1 hour" and dev["happened"].startswith("Still not done after 90 minutes")
    assert dev["value"] >= 60 and dev["who_sub"] == "Finance Admin"
    assert await accountability.sweep(engine, _later(minutes=95)) == 0                                # once
    assert await engine.db.pool.fetchval("SELECT count(*) FROM rule_watches WHERE state = 'open'") == 0
    assert "report.new" in su.push_types(await su.drain_pushes())
    assert [r for r in (await su.ok("reports.list"))["reports"] if r["category"] == "about_admin"]    # about an Admin: the Super User only
    assert "deviation.raised" not in a1.push_types(await a1.drain_pushes())                          # an Admin is never told of a deviation about them

    # answered, but late, is still a departure; a switched-off rule records nothing
    third = await w1.ok("assistance.ping", {"to_account_id": org["a1"]})
    await a1.ok("assistance.respond", {"ping_id": third["ping_id"]})
    assert await accountability.sweep(engine, _later(hours=5)) == 0                                   # answered before it was due: kept
    rule = (await su.ok("rules.list"))["rules"][-1]
    await su.ok("rules.switch", {"rule_id": rule["id"], "on": False})
    await w2.ok("assistance.ping", {"to_account_id": org["a1"]})
    assert await accountability.sweep(engine, _later(hours=5)) == 0


async def test_every_machine_must_run_the_approved_version_in_time_and_a_department_must_have_an_admin(engine, org, connect):
    su = await connect("cid-su")
    w1 = await connect("cid-w1")
    await su.ok("rules.create", {"name": "Every department has an Admin", "shape": "follow", "trigger": "seat", "expect": "appoint", "within": 10080,
                                 "who": "depts", "resp": {"report": True, "admin": False}})
    await su.ok("updates.approve", {"version": "1.0.0"})
    await w1.ok("updates.report_status", {"version": "1.0.0", "succeeded": True, "running": "1.0.0"})            # one machine is on it
    legal = (await su.ok("hierarchy.department_create", {"name": "Legal"}))["department_id"]

    assert await accountability.sweep(engine, _later(days=1)) == 0
    assert await accountability.sweep(engine, _later(days=3)) == 3                                    # FIN-ADM, FIN-02, HR-ADM: not on 1.0.0 (B-3: two days)
    pcs = (await su.ok("deviations.list", {"kind": "pc"}))["deviations"]
    assert {d["host"] for d in pcs} == {"FIN-ADM", "FIN-02", "HR-ADM"} and all(d["rule"]["code"] == "B-3" and d["severity"] == "high" for d in pcs)
    assert all(d["expected"] == "The machine runs that version within 2 days" and d["who"] == d["host"] for d in pcs)

    assert await accountability.sweep(engine, _later(days=8)) == 1                                    # Legal still has no Admin after a week
    [seat] = (await su.ok("deviations.list", {"kind": "dept"}))["deviations"]
    assert seat["who"] == "Legal" and seat["department_id"] == legal and seat["rule"]["code"] == "O-1" and seat["value"] >= 10080

    # offboarding a department's last Admin starts the same watch
    await su.ok("hierarchy.account_offboard", {"account_id": org["a2"]})
    assert await engine.db.pool.fetchval("SELECT count(*) FROM rule_watches WHERE state = 'open' AND target_table = $1", f"seat:{org['hr']}") == 1


async def test_a_limit_rule_counts_what_the_audit_trail_shows_and_a_never_rule_catches_a_second_session(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    await connect("cid-w1")
    await connect("cid-w2")
    engine.settings = dataclasses.replace(engine.settings, working_hours="00:00-00:00")                 # always outside working hours
    await su.ok("rules.create", {"name": "Admins stay out of machines at night", "shape": "limit", "reading": "outhours",
                                 "limit": {"n": 0, "per": "week"}, "who": "admins", "resp": {"report": True, "admin": False}})
    await su.ok("rules.create", {"name": "Failed sign-ins stay rare", "shape": "limit", "reading": "failedauth", "limit": {"n": 1, "per": "hour"},
                                 "who": "everyone", "severity": "high"})
    await a1.ok("hierarchy.traverse", {"pc_id": org["w1_pc"], "force": True})

    assert await accountability.sweep(engine) == 1
    [night] = [d for d in (await su.ok("deviations.list"))["deviations"] if d["rule"]["code"] == "O-1"]
    assert night["kind"] == "admin" and night["value"] == 1.0 and night["happened"] == "1 in the last week" and night["who_sub"] == "Finance Admin"
    assert night["expected"] == "Admin entries outside working hours: none per week"
    assert await accountability.sweep(engine) == 0                                                    # once per period

    # failed sign-ins on one machine: two refused answers, over a line of one an hour
    for _ in range(2):
        reader, writer = await asyncio.open_connection("127.0.0.1", engine.port)
        assert b"auth.challenge" in await reader.readuntil(b"\n")
        writer.write(encode(request("auth.respond", {"client_id": "cid-w1", "hmac": "00" * 32, "hostname": "FIN-01"})))
        await writer.drain()
        await reader.readuntil(b"\n")
        writer.close()
    assert await accountability.sweep(engine) == 1
    [bad] = [d for d in (await su.ok("deviations.list", {"kind": "pc"}))["deviations"] if d["rule"]["code"] == "O-2"]
    assert bad["host"] == "FIN-01" and bad["value"] == 2.0 and bad["severity"] == "high" and "2 in the last hour" in bad["happened"]

    # a second session on a held machine is refused for good, and the refusal is the deviation (B-2 only records it)
    await su.ok("hierarchy.traverse", {"pc_id": org["w2_pc"], "force": True})
    assert await a1.err("hierarchy.traverse", {"pc_id": org["w2_pc"], "force": True}) == "conflict"
    second = [d for d in (await su.ok("deviations.list"))["deviations"] if d["rule"]["code"] == "B-2"]
    assert len(second) == 1 and second[0]["kind"] == "admin" and "tried to enter FIN-02" in second[0]["short"]

    # a machine presenting another name breaks B-4
    await connect("cid-w1", hostname="LOBBY-PC")
    [cert] = [d for d in (await su.ok("deviations.list", {"kind": "pc"}))["deviations"] if d["rule"]["code"] == "B-4"]
    assert cert["expected"] == "The name FIN-01" and cert["happened"] == "The name LOBBY-PC" and cert["who"] == "FIN-01"


async def test_changing_a_rule_is_tried_against_the_past_and_never_rewrites_it(engine, org, connect):
    su = await connect("cid-su")
    w1 = await connect("cid-w1")
    w2 = await connect("cid-w2")
    rule = (await su.ok("rules.create", {"name": "Help requests are answered", "shape": "follow", "trigger": "help", "expect": "answer", "within": 60,
                                         "who": "admins"}))["rule"]
    await w1.ok("assistance.ping", {"to_account_id": org["a1"]})
    await w2.ok("assistance.ping", {"to_account_id": org["a1"]})
    assert await accountability.sweep(engine, _later(minutes=80)) == 2                               # both late: 80 minutes
    assert (await su.ok("rules.try", {"rule_id": rule["id"], "within": 120}))["would_clear"] == 2
    tried = await su.ok("rules.try", {"rule_id": rule["id"], "within": 70})
    assert (tried["deviations"], tried["would_clear"], tried["would_remain"]) == (2, 0, 2)
    assert await su.err("rules.try", {"rule_id": rule["id"]}) == "invalid"
    # raising the limit changes the rule; last week's deviations still say what the rule was
    await su.ok("rules.update", {"rule_id": rule["id"], "within": 240, "name": "Help requests are answered in four hours"})
    old = (await su.ok("deviations.list"))["deviations"][0]
    assert old["rule"]["name"] == "Help requests are answered" and old["expected"] == "An Admin answers the ping within 1 hour"
    listing = (await su.ok("rules.list"))["rules"]
    mine = next(r for r in listing if r["id"] == rule["id"])
    assert mine["deviations_this_week"] == 2 and mine["open_this_week"] == 2
    assert (await su.ok("rules.list"))["summary"]["broken_this_week"] == 1


async def test_what_a_rule_says_to_do_is_all_the_system_does(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    lock = (await su.ok("control.action_create", {"kind": "control", "builtin_type": "notify", "timeout_s": 5, "params": {"message": "Stay out of restricted files"}}))["action"]
    await su.ok("rules.create", {"name": "Tell them straight away", "shape": "never", "trigger": "file", "resp": {"report": False, "admin": False, "action": True, "action_id": lock["id"]}})
    assert await su.err("rules.create", {"name": "x", "shape": "never", "trigger": "file", "resp": {"action": True, "action_id": 999}}) == "not_found"
    await a1.ok("index.event", {"event": {"op": "create", "path": "C:/resources/restricted/s.xlsx", "hash": "S"}})
    await w1.drain_pushes()
    await w1.ok("index.event", {"event": {"op": "copy", "path": "C:/Users/ama/s-copy.xlsx", "hash": "S"}})
    run = next(p for p in await w1.drain_pushes() if p.type == "action.execute").payload
    assert run["action"]["builtin_type"] == "notify" and run["action"]["params"]["message"] == "Stay out of restricted files"
