"""Resource & Assistance end-to-end (skipped without FALCON_TEST_DATABASE_URL).

Pins resource-assistance-combo.md: tags from tier folders, restricted files tracked by hash,
violations logged + surfaced + reported + that one file ignored (never deleted); tier-scoped
search; ping repeatable with a pulsing status; channel opens on response with the
one-message-per-turn lock; only the superior closes; listeners are per-adder and silent.
"""

from __future__ import annotations

from tests.conftest import requires_db

pytestmark = requires_db


async def test_tags_tracking_violation_and_ignore(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    # A file in the Admin's /resources/restricted/ gets tagged from its folder.
    r = await a1.ok("index.event", {"event": {"op": "create", "path": "C:/resources/restricted/salaries.xlsx",
                                              "hash": "SECRET"}})
    entry = await engine.db.file_index.get(r["file_index_id"])
    assert entry["resource_tag"] == "restricted"
    # /resources/workers/ on an Admin PC -> worker_dept scoped to that department.
    r2 = await a1.ok("index.event", {"event": {"op": "create", "path": "C:/resources/workers/plan.docx", "hash": "P"}})
    e2 = await engine.db.file_index.get(r2["file_index_id"])
    assert (e2["resource_tag"], e2["resource_tag_scope_department_id"]) == ("worker_dept", org["fin"])

    # The same content (by hash) shows up on a Worker PC under a different name -> violation.
    v = await w1.ok("index.event", {"event": {"op": "copy", "path": "C:/Downloads/totally-not-salaries.xlsx",
                                              "hash": "SECRET"}})
    pushed = next(p for p in await w1.drain_pushes() if p.type == "resource.violation")
    assert pushed.payload["tag"] == "restricted" and "ignored" in pushed.payload["message"]
    assert su.push_types(await su.drain_pushes()) == ["report.new"]
    viol = (await w1.ok("resource.violations"))["violations"]
    assert len(viol) == 1 and viol[0]["file_index_id"] == v["file_index_id"] and viol[0]["report_id"]
    assert len((await a1.ok("resource.violations"))["violations"]) == 1            # own department
    assert (await su.ok("reports.list"))["reports"][0]["category"] == "resource_violation"
    # The file is still indexed (never deleted) but ignored; a repeat event does not re-flag.
    assert await engine.db.file_index.get(v["file_index_id"]) is not None
    await w1.ok("index.event", {"event": {"op": "modify", "path": "C:/Downloads/totally-not-salaries.xlsx", "hash": "SECRET"}})
    assert len((await w1.ok("resource.violations"))["violations"]) == 1
    assert await engine.db.resource.ignored_file_ids(org["w1_pc"]) == {v["file_index_id"]}
    # The affected user resolves it; the ignore lifts.
    await w1.ok("resource.resolve", {"violation_id": viol[0]["id"]})
    assert (await w1.ok("resource.violations"))["violations"] == []
    assert await engine.db.resource.ignored_file_ids(org["w1_pc"]) == set()
    # Worker-dept content is fine on a worker PC of that department; admin tier is Super User only.
    await w1.ok("index.event", {"event": {"op": "copy", "path": "C:/resources/plan.docx", "hash": "P"}})
    assert (await w1.ok("resource.violations"))["violations"] == []
    assert await a1.err("resource.tag", {"file_index_id": r2["file_index_id"], "tag": "admin"}) == "forbidden"
    await su.ok("resource.tag", {"file_index_id": r2["file_index_id"], "tag": "common"})


async def test_search_is_tier_scoped(engine, org, connect):
    a1 = await connect("cid-a1")
    w1 = await connect("cid-w1")
    su = await connect("cid-su")
    await a1.ok("index.event", {"event": {"op": "create", "path": "C:/resources/restricted/budget-secret.xlsx", "hash": "1"}})
    await a1.ok("index.event", {"event": {"op": "create", "path": "C:/resources/workers/budget-plan.docx", "hash": "2"}})
    await a1.ok("index.event", {"event": {"op": "create", "path": "C:/resources/common/budget-template.docx", "hash": "3"}})
    names = lambda res: sorted(r["filename"] for r in res["results"])
    assert names(await w1.ok("assistance.search", {"query": "budget"})) == ["budget-plan.docx", "budget-template.docx"]
    assert names(await a1.ok("assistance.search", {"query": "budget"})) == ["budget-plan.docx", "budget-secret.xlsx",
                                                                             "budget-template.docx"]
    assert names(await su.ok("assistance.search", {"query": "budget"})) == ["budget-secret.xlsx", "budget-template.docx"]


async def test_ping_channel_lock_close_and_listeners(engine, org, connect):
    a1 = await connect("cid-a1")
    a2 = await connect("cid-a2")
    w1 = await connect("cid-w1")
    w2 = await connect("cid-w2")
    su = await connect("cid-su")
    # Pings only between direct vertical pairs.
    assert await w1.err("assistance.ping", {"to_account_id": org["w2"]}) == "forbidden"
    assert await w1.err("assistance.ping", {"to_account_id": org["a2"]}) == "forbidden"
    assert await w1.err("assistance.ping", {"to_account_id": org["su"]}) == "forbidden"
    p1 = await w1.ok("assistance.ping", {"to_account_id": org["a1"]})
    await w1.ok("assistance.ping", {"to_account_id": org["a1"]})                    # repeatable
    kinds = a1.push_types(await a1.drain_pushes())
    assert kinds.count("assistance.ping") == 2 and "assistance.ping_status" in kinds
    st = await a1.ok("assistance.ping_status")
    assert st["unaddressed"] == 2 and st["indicator"] == "unaddressed_ping"

    # Nobody but the receiver responds; responding addresses all of that sender's pings.
    assert await w1.err("assistance.respond", {"ping_id": p1["ping_id"]}) == "not_found"
    opened = await a1.ok("assistance.respond", {"ping_id": p1["ping_id"]})
    chan = opened["channel_id"]
    assert opened["opened"] is True and opened["turn"] == "sender"
    assert (await a1.ok("assistance.ping_status"))["unaddressed"] == 0
    assert "assistance.channel_opened" in w1.push_types(await w1.drain_pushes())

    # Turn lock: the sender speaks first; the superior must wait, then it flips.
    assert await a1.err("assistance.message", {"channel_id": chan, "body": "too early"}) == "conflict"
    await w1.ok("assistance.message", {"channel_id": chan, "body": "printer is down"})
    assert await w1.err("assistance.message", {"channel_id": chan, "body": "and also..."}) == "conflict"
    msg = next(p for p in await a1.drain_pushes() if p.type == "assistance.message")
    assert msg.payload["body"] == "printer is down" and msg.payload["turn"] == "superior"
    await a1.ok("assistance.message", {"channel_id": chan, "body": "restart it"})
    view = await w1.ok("assistance.channel", {"channel_id": chan})
    assert [m["body"] for m in view["messages"]] == ["printer is down", "restart it"] and view["channel"]["my_turn"]
    assert await w2.err("assistance.channel", {"channel_id": chan}) == "forbidden"

    # Listeners: W1 adds A2 (HR); A1 cannot see W1's listener; A2 hears messages live.
    assert await w1.err("assistance.add_listener", {"channel_id": chan, "admin_account_id": org["w2"]}) == "invalid"
    assert await w1.err("assistance.add_listener", {"channel_id": chan, "admin_account_id": org["a1"]}) == "invalid"
    added = await w1.ok("assistance.add_listener", {"channel_id": chan, "admin_account_id": org["a2"]})
    assert added["added"] is True
    assert su.push_types(await su.drain_pushes()) == ["report.new"]                # listener_report
    assert "assistance.listening" in a2.push_types(await a2.drain_pushes())
    again = await a1.ok("assistance.add_listener", {"channel_id": chan, "admin_account_id": org["a2"]})
    assert again["added"] is False                                                  # dedup
    assert [l["listener_account_id"] for l in (await w1.ok("assistance.my_listeners", {"channel_id": chan}))["listeners"]] == [org["a2"]]
    assert (await a1.ok("assistance.my_listeners", {"channel_id": chan}))["listeners"] == []
    await w1.ok("assistance.message", {"channel_id": chan, "body": "done, thanks"})
    assert "assistance.message" in a2.push_types(await a2.drain_pushes())
    assert [c["id"] for c in (await a2.ok("assistance.channels"))["channels"]] == [chan]
    assert len((await a2.ok("assistance.channel", {"channel_id": chan}))["messages"]) == 3

    # Only the superior closes.
    assert await w1.err("assistance.close_channel", {"channel_id": chan}) == "forbidden"
    await a1.ok("assistance.close_channel", {"channel_id": chan})
    assert "assistance.channel_closed" in w1.push_types(await w1.drain_pushes())
    assert await a1.err("assistance.message", {"channel_id": chan, "body": "x"}) == "conflict"

    # Superior-initiated: Admin pings Worker; Worker responds; Admin speaks first; Admin still closes.
    p2 = await a1.ok("assistance.ping", {"to_account_id": org["w1"]})
    opened2 = await w1.ok("assistance.respond", {"ping_id": p2["ping_id"]})
    assert opened2["turn"] == "superior" and opened2["superior_account_id"] == org["a1"]
    assert await w1.err("assistance.message", {"channel_id": opened2["channel_id"], "body": "?"}) == "conflict"
    await a1.ok("assistance.message", {"channel_id": opened2["channel_id"], "body": "status?"})
    assert await w1.err("assistance.close_channel", {"channel_id": opened2["channel_id"]}) == "forbidden"
    await a1.ok("assistance.close_channel", {"channel_id": opened2["channel_id"]})
