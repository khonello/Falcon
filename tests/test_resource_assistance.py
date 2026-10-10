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
    # who can be added: Admins of every department (HR's A2 too), never the parties; only a party may ask
    cands = (await w1.ok("assistance.listener_candidates", {"channel_id": chan}))["candidates"]
    assert [c["account_id"] for c in cands] == [org["a2"]] and cands[0]["department_name"] == "HR"
    assert await w2.err("assistance.listener_candidates", {"channel_id": chan}) == "forbidden"
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


async def test_a_person_can_ask_who_they_may_ask_for_help(engine, org, connect):
    w1 = await connect("cid-w1")
    a1 = await connect("cid-a1")
    su = await connect("cid-su")
    assert [a["account_id"] for a in (await w1.ok("assistance.my_admins"))["admins"]] == [org["a1"]]
    assert [a["role"] for a in (await a1.ok("assistance.my_admins"))["admins"]] == ["super_user"]
    assert (await su.ok("assistance.my_admins"))["admins"] == []
    ping = await w1.ok("assistance.ping", {"to_account_id": org["a1"]})
    assert ping["ping_id"]


async def test_a_files_journey_follows_its_content_and_stays_in_scope(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    a2 = await connect("cid-a2")
    w1 = await connect("cid-w1")
    w2 = await connect("cid-w2")
    r = await a1.ok("index.event", {"event": {"op": "create", "path": "C:/resources/restricted/salaries.xlsx", "hash": "SECRET"}})
    origin = r["file_index_id"]
    await su.ok("resource.tag", {"file_index_id": origin, "tag": "restricted"})
    copy = await w1.ok("index.event", {"event": {"op": "copy", "path": "C:/Downloads/salaries-copy.xlsx", "hash": "SECRET"}})
    violation = (await w1.ok("resource.violations"))["violations"][0]
    await w1.ok("resource.resolve", {"violation_id": violation["id"]})
    await a2.ok("index.event", {"event": {"op": "copy", "path": "C:/Users/hr/Desktop/sal.xlsx", "hash": "SECRET"}})
    # a flow carried it to FIN-02 (the sync log is what a flow writes; here it is written directly)
    pool = engine.db.pool
    flow = await pool.fetchval("INSERT INTO flows (created_by_account_id, source_pc_id, source_path, consent_status) "
                               "VALUES ($1, $2, 'C:/out', 'not_required') RETURNING id", org["a1"], org["a1_pc"])
    dest = await pool.fetchval("INSERT INTO flow_destinations (flow_id, destination_pc_id, destination_path, owner_account_id, "
                               "pre_flight_check_status) VALUES ($1, $2, 'D:/inbox', $3, 'passed') RETURNING id",
                               flow, org["w2_pc"], org["w2"])
    await pool.execute("INSERT INTO flow_sync_log (flow_destination_id, content_hash, written_by, written_path) "
                       "VALUES ($1, 'SECRET', 'flow_sync', 'D:/inbox/salaries.xlsx')", dest)

    # The Super User sees the whole journey, oldest first, from any copy of the file
    full = await su.ok("resource.journey", {"file_index_id": copy["file_index_id"]})
    kinds = [e["kind"] for e in full["events"]]
    assert kinds[0] == "first_seen" and full["events"][0]["hostname"] == "FIN-ADM"
    assert {"copied", "tagged", "flagged", "owner_told", "resolved", "synced"} <= set(kinds)
    assert kinds.index("flagged") < kinds.index("owner_told") < kinds.index("resolved")
    assert [e["at"] for e in full["events"]] == sorted(e["at"] for e in full["events"])
    assert {p["hostname"] for p in full["places"]} == {"FIN-ADM", "FIN-01", "HR-ADM"}
    tagged = next(e for e in full["events"] if e["kind"] == "tagged")
    assert tagged["who"] and "restricted" in tagged["text"]
    assert next(e for e in full["events"] if e["kind"] == "synced")["hostname"] == "FIN-02"
    assert next(e for e in full["events"] if e["kind"] == "owner_told")["who"]            # who was told, as the caller names them

    # An Admin sees only their own department's machines: Finance does not read HR's copy, HR does not read Finance's
    fin = await a1.ok("resource.journey", {"file_index_id": origin})
    assert {p["hostname"] for p in fin["places"]} == {"FIN-ADM", "FIN-01"}
    assert "HR-ADM" not in {e["hostname"] for e in fin["events"]}
    hr = await a2.ok("resource.journey", {"file_index_id": origin})
    assert {p["hostname"] for p in hr["places"]} == {"HR-ADM"} and all(e["hostname"] == "HR-ADM" for e in hr["events"])
    # a file with no place in the Admin's department is not theirs to read; a worker may not ask at all
    lone = await a1.ok("index.event", {"event": {"op": "create", "path": "C:/resources/restricted/only-fin.docx", "hash": "ONLY"}})
    assert await a2.err("resource.journey", {"file_index_id": lone["file_index_id"]}) == "not_found"
    assert await a1.err("resource.journey", {"file_index_id": 99999}) == "not_found"
    assert await w2.err("resource.journey", {"file_index_id": origin}) == "forbidden"
    assert len((await a1.ok("resource.journey", {"file_index_id": lone["file_index_id"]}))["events"]) == 1


async def test_a_files_journey_includes_renames_moves_deletes_and_what_the_os_reports_besides(engine, org, connect):
    """The Worker tells the Engine where a file was (`old_path`); the Engine records it, marks the place the file left, and the
    journey tells it: renamed, moved, edited, attributes and permissions changed, deleted -- never a ghost 'copy'."""
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    ev = lambda **e: a1.ok("index.event", {"event": e})
    first = await ev(op="create", path="C:/Finance/budget.xlsx", hash="H1")
    await ev(op="move", path="C:/Finance/budget-old.xlsx", old_path="C:/Finance/budget.xlsx", hash="H1")        # a rename
    await ev(op="modify", path="C:/Finance/budget-old.xlsx", hash="H1")
    await ev(op="attrib", path="C:/Finance/budget-old.xlsx")                                                   # read-only
    await ev(op="security", path="C:/Finance/budget-old.xlsx")                                                 # who may open it
    last = await ev(op="move", path="D:/Archive/budget-old.xlsx", old_path="C:/Finance/budget-old.xlsx", hash="H1")
    await ev(op="delete", path="D:/Archive/budget-old.xlsx")

    # a folder is history and a signal, never an index row
    folder = await ev(op="move", path="C:/Finance2", old_path="C:/Finance", is_dir=True)
    assert folder["file_index_id"] is None
    assert await engine.db.pool.fetchval("SELECT count(*) FROM file_index WHERE path LIKE 'C:/Finance2%'") == 0

    j = await su.ok("resource.journey", {"file_index_id": last["file_index_id"]})
    kinds = [e["kind"] for e in j["events"]]
    assert kinds == ["first_seen", "renamed", "edited", "attributes_changed", "permissions_changed", "moved", "deleted"], kinds
    texts = {e["kind"]: e["text"] for e in j["events"]}
    assert "budget.xlsx to budget-old.xlsx" in texts["renamed"] and "D:/Archive/budget-old.xlsx" in texts["moved"]
    assert "copied" not in kinds                                                    # the moved-to rows are not copies
    assert [p["path"] for p in j["places"]] == ["C:/Finance/budget.xlsx", "C:/Finance/budget-old.xlsx", "D:/Archive/budget-old.xlsx"]
    assert all(p["gone_at"] for p in j["places"])                                   # it has left them all (deleted last)
    # asked from the first place too: the same journey
    assert [e["kind"] for e in (await su.ok("resource.journey", {"file_index_id": first["file_index_id"]}))["events"]] == kinds

    # a place the file has left is not a file that is there: no name collision, no copy elsewhere, not found by search
    assert await engine.file_index.name_collisions("budget.xlsx") == []
    assert await engine.file_index.path_collision(org["a1_pc"], "C:/Finance/budget.xlsx") is None
    assert await engine.db.file_index.by_hash("H1") == []
    # ...and it counts again if it turns up there again (the row is the same one, no longer gone)
    await ev(op="create", path="C:/Finance/budget.xlsx", hash="H1")
    assert len(await engine.db.file_index.by_hash("H1")) == 1


async def test_automations_can_wait_on_attribute_permission_and_folder_changes(engine, org, connect):
    a1 = await connect("cid-a1")
    note = (await a1.ok("control.action_create", {"kind": "control", "builtin_type": "notify", "timeout_s": 5,
                                                  "params": {"message": "changed"}}))["action"]
    wanted = ("file.attributes_changed", "file.permissions_changed", "folder.created", "folder.moved", "folder.deleted")
    for etype in wanted:
        await a1.ok("control.event_create", {"type": etype, "pc_ids": [org["a1_pc"]], "action_ids": [note["id"]]})
    await a1.drain_pushes()
    sent = [{"op": "attrib", "path": "C:/x/a.txt"}, {"op": "security", "path": "C:/x/a.txt"},
            {"op": "create", "path": "C:/x/new", "is_dir": True},
            {"op": "move", "path": "C:/x/new2", "old_path": "C:/x/new", "is_dir": True},
            {"op": "delete", "path": "C:/x/new2", "is_dir": True}]
    for e in sent:
        await a1.ok("index.event", {"event": e})
    fired = [p.payload["type"] for p in await a1.drain_pushes() if p.type == "event.fired"]
    assert sorted(fired) == sorted(wanted)
    # an edit of attributes or permissions, or anything to a folder, does not reach Flow, Resource or Task (content only)
    assert await engine.db.pool.fetchval("SELECT count(*) FROM resource_violations") == 0
