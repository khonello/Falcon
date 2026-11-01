"""An Admin's conversations without the Super User (ENGINE-GAPS #17): two people, or every Admin; no request first; read times per person."""

from __future__ import annotations

from tests.conftest import requires_db

pytestmark = requires_db


async def test_admins_talk_to_each_other_and_to_a_machines_person_with_no_request_first(engine, org, connect):
    a1, a2, w1, w2 = await connect("cid-a1"), await connect("cid-a2"), await connect("cid-w1"), await connect("cid-w2")
    su = await connect("cid-su")

    people = await a1.ok("chat.people")
    assert people["admins_group"] is True
    by = {p["account_id"]: p for p in people["people"]}
    assert set(by) == {org["a2"], org["w1"], org["w2"]}                          # the other Admins and each machine's person (version 1: every department)
    assert by[org["a2"]]["role"] == "admin" and by[org["w1"]]["hostname"] == "FIN-01" and by[org["w1"]]["online"] is True
    assert await w1.err("chat.people") == "forbidden" and await w1.err("chat.open", {"account_id": org["a1"]}) == "forbidden"
    assert await a1.err("chat.open", {"account_id": org["su"]}) == "not_found"   # the Super User is set aside in version 1
    assert await a1.err("chat.open", {"account_id": org["a1"]}) == "invalid"

    # Writing to someone opens the one conversation with them; writing again reuses it; by machine is its person.
    talk = (await a1.ok("chat.open", {"pc_id": org["w1_pc"]}))["conversation"]
    assert talk["kind"] == "pair" and talk["title"] and [m["account_id"] for m in talk["members"]] == sorted([org["a1"], org["w1"]])
    assert (await a1.ok("chat.open", {"account_id": org["w1"]}))["conversation"]["conversation_id"] == talk["conversation_id"]
    cid = talk["conversation_id"]
    await w1.drain_pushes()
    await a1.ok("chat.send", {"conversation_id": cid, "body": "Your disk is nearly full; may I clear the temp folder?"})
    pushed = [p.payload for p in await w1.drain_pushes() if p.type == "chat.message"]
    assert pushed and pushed[0]["conversation_id"] == cid and pushed[0]["body"].startswith("Your disk")
    assert w2.push_types(await w2.drain_pushes()).count("chat.message") == 0

    # The person answers in it; unread and seen are per person.
    mine = await w1.ok("chat.list")
    assert mine["unread"] == 1 and [c["conversation_id"] for c in mine["conversations"]] == [cid]   # a Worker is in no group
    await w1.ok("chat.read", {"conversation_id": cid})
    assert "chat.read" in a1.push_types(await a1.drain_pushes())
    listed = {c["conversation_id"]: c for c in (await a1.ok("chat.list"))["conversations"]}
    assert [s["account_id"] for s in listed[cid]["seen_by"]] == [org["w1"]] and listed[cid]["unread"] == 0
    await w1.ok("chat.send", {"conversation_id": cid, "body": "Yes, go ahead."})
    got = await a1.ok("chat.get", {"conversation_id": cid})
    assert [m["body"] for m in got["messages"]] == ["Your disk is nearly full; may I clear the temp folder?", "Yes, go ahead."]
    assert [m["mine"] for m in got["messages"]] == [True, False] and (await a1.ok("chat.list"))["unread"] == 1

    # Nobody outside it can read or write in it.
    for outsider in (w2, a2, su):
        assert await outsider.err("chat.get", {"conversation_id": cid}) == "not_found"
        assert await outsider.err("chat.send", {"conversation_id": cid, "body": "hi"}) == "not_found"
    assert await a1.err("chat.send", {"conversation_id": cid, "body": "   "}) == "invalid"
    assert await a1.err("chat.send", {"conversation_id": cid, "body": "x" * 4001}) == "invalid"

    # The group of every Admin: there for both Admins, its members follow the accounts.
    group = (await a2.ok("chat.open", {"admins": True}))["conversation"]
    assert group["kind"] == "admins" and group["title"] == "Every Admin" and {m["account_id"] for m in group["members"]} == {org["a1"], org["a2"]}
    await a2.ok("chat.send", {"conversation_id": group["conversation_id"], "body": "Patch night is Thursday."})
    assert "chat.message" in a1.push_types(await a1.drain_pushes())
    assert group["conversation_id"] in {c["conversation_id"] for c in (await a1.ok("chat.list"))["conversations"]}
    assert await w1.err("chat.get", {"conversation_id": group["conversation_id"]}) == "not_found"
    await engine.db.pool.execute("UPDATE accounts SET status = 'offboarded' WHERE id = $1", org["a2"])
    assert await a1.err("chat.open", {"admins": True}) == "conflict"               # one Admin left: no group to write in
    assert group["conversation_id"] not in {c["conversation_id"] for c in (await a1.ok("chat.list"))["conversations"]}
