"""Search (Ctrl K): what each kind finds, and what an Admin is not shown."""

from __future__ import annotations

from tests.conftest import requires_db

pytestmark = requires_db


async def test_search_finds_machines_people_rules_and_departments_within_what_the_caller_may_see(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    await engine.db.pool.execute("UPDATE accounts SET self_display_name = 'Ama Boateng' WHERE id = $1", org["w1"])
    assert (await su.ok("search.find", {"q": "x"}))["results"] == []                      # too short to mean anything

    res = (await su.ok("search.find", {"q": "fin"}))["results"]
    kinds = {(r["kind"], r["title"]) for r in res}
    assert ("machine", "FIN-01") in kinds and ("machine", "FIN-ADM") in kinds and ("department", "Finance") in kinds
    assert all(r["page"] for r in res)
    mine = (await a1.ok("search.find", {"q": "hr"}))["results"]
    assert mine == []                                                                    # HR is another department: nothing of it is shown
    assert {r["title"] for r in (await su.ok("search.find", {"q": "hr", "kinds": ["machine", "department"]}))["results"]} == {"HR-ADM", "HR"}

    assert [(r["kind"], r["title"]) for r in (await su.ok("search.find", {"q": "boateng", "kinds": ["person"]}))["results"]] == [("person", "Ama Boateng")]
    rules = (await a1.ok("search.find", {"q": "restricted", "kinds": ["rule"]}))["results"]
    assert rules and rules[0]["kind"] == "rule"
    assert await su.err("search.find", {"q": "fin", "kinds": ["nonsense"]}) == "invalid"
    assert await (await connect("cid-w1")).err("search.find", {"q": "fin"}) == "forbidden"
