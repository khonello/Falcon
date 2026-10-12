"""The Registry: accounts, refused connections and blocked addresses; promoting and stopping being an Admin; a department's page (WP6)."""

from __future__ import annotations

import pytest

from common.connection import ConnectionError_, EngineConnection, EngineError
from engine.console import issues as console_issues
from tests.conftest import key_for, requires_db

pytestmark = requires_db


async def _try(engine, client_id: str, key: str, hostname: str | None = None) -> None:
    conn = EngineConnection("127.0.0.1", engine.port, client_id=client_id, tls=False, derived_key=key, hostname=hostname)
    with pytest.raises((EngineError, ConnectionError_, ConnectionError, OSError)):
        await conn.connect()
    await conn.close()


async def test_refused_connections_say_who_tried_why_and_what_to_do_and_an_address_can_be_blocked(engine, org, connect):
    su = await connect("cid-su")
    w1 = await connect("cid-w1", hostname="FIN-01")                                             # FIN-01 has been seen from this address
    rk = await su.ok("hierarchy.pc_rekey", {"pc_id": org["w2_pc"]})                              # FIN-02 is now on key no. 2
    for _ in range(3):
        await _try(engine, "cid-nobody", key_for("cid-nobody"), hostname="FIN-NEW")                # a machine nobody registered
    await _try(engine, "cid-w2", key_for("cid-w2"), hostname="FIN-02")                           # FIN-02 still using the key that was replaced
    await _try(engine, "cid-w1", "ab" * 32, hostname="FIN-01")                                    # someone with a wrong key, claiming FIN-01

    res = await su.ok("registry.refused")
    by_kind = {g["kind"]: g for g in res["refused"]}
    assert set(by_kind) == {"unknown", "old_key", "wrong_key"} and res["summary"]["tries"] == 5
    unknown = by_kind["unknown"]
    assert unknown["tries"] == 3 and unknown["why"] == "not registered" and unknown["advice"] == "register" and unknown["host"] == "FIN-NEW"
    assert unknown["address"] == "127.0.0.1" and unknown["last"] and unknown["blocked"] is False
    old = by_kind["old_key"]
    assert old["why"] == "key no. 1, replaced by no. 2" and old["advice"] == "rekey" and old["machine"] == "FIN-02" and old["tries"] == 1
    wrong = by_kind["wrong_key"]
    assert wrong["host"] == "Claims to be FIN-01" and wrong["machine"] == "FIN-01" and wrong["same_address"] is True and wrong["tone"] == "wait"
    assert await w1.err("registry.refused") == "forbidden" and rk["key_generation"] == 2

    # blocking: refused before the challenge, still counted as a try, and never your own address
    assert await su.err("registry.block", {"address": "127.0.0.1"}) == "conflict"
    assert await su.err("registry.block", {"address": "not-an-address"}) == "invalid"
    done = await su.ok("registry.block", {"address": "10.9.9.9", "reason": "keeps guessing"})
    assert done["blocked"] and (await su.ok("registry.block", {"address": "10.9.9.9"}))["was_blocked"] is True
    assert [b["address"] for b in (await su.ok("registry.blocked"))["blocked"]] == ["10.9.9.9"]
    await engine.db.registry.block("127.0.0.1", "test", org["su"])
    engine.blocked_addresses.add("127.0.0.1")
    await _try(engine, "cid-nobody", key_for("cid-nobody"), hostname="FIN-NEW")
    engine.blocked_addresses.discard("127.0.0.1")
    again = {g["kind"]: g for g in (await su.ok("registry.refused"))["refused"]}
    assert again["blocked"]["why"] == "address blocked" and again["blocked"]["blocked"] is True and again["blocked"]["advice"] == "unblock"
    assert (await su.ok("registry.unblock", {"address": "10.9.9.9"}))["was_blocked"] is True
    assert {e["action_type"] for e in (await su.ok("audit.events", {"kinds": ["admin"]}))["events"]} >= {"registry.address_blocked", "registry.address_unblocked"}


async def test_the_accounts_list_and_an_admin_who_stops_being_one(engine, org, connect):
    su = await connect("cid-su")
    a1 = await connect("cid-a1")
    res = await su.ok("registry.accounts")
    me = next(a for a in res["accounts"] if a["you"])
    assert me["name"] == "You" and me["role"] == "super_user" and me["workstation"] == "SU-PC" and me["key_generation"] == 1
    assert {a["workstation"] for a in res["accounts"] if a["role"] == "admin"} == {"FIN-ADM", "HR-ADM"}
    assert next(a for a in res["accounts"] if a["workstation"] == "FIN-ADM")["online"] is True
    assert next(a for a in res["accounts"] if a["workstation"] == "HR-ADM")["now"] == "Never signed in"
    assert {a["workstation"] for a in (await a1.ok("registry.accounts"))["accounts"]} == {"FIN-ADM", "FIN-01", "FIN-02"}     # an Admin sees their own department

    page = await su.ok("departments.get", {"department_id": org["hr"]})
    assert [a["workstation"] for a in page["admins"]] == ["HR-ADM"] and page["vacant"] is False and page["workers"] == []

    made = await su.ok("hierarchy.admin_demote", {"account_id": org["a2"]})
    assert made["role"] == "worker" and made["key_generation"] == 2 and made["client_key"] == engine.client_key("cid-a2", 2)
    page = await su.ok("departments.get", {"department_id": org["hr"]})
    assert page["vacant"] is True and [w["workstation"] for w in page["workers"]] == ["HR-ADM"]                              # a Worker now, and promotable again
    assert (await su.ok("hierarchy.account_get", {"account_id": org["a2"]}))["account"]["role"] == "worker"
    assert await su.err("hierarchy.admin_demote", {"account_id": org["a2"]}) == "not_found"                                     # no longer an Admin
    assert await a1.err("hierarchy.admin_demote", {"account_id": org["a1"]}) == "forbidden"
    assert next(d for d in (await su.ok("overview.departments"))["departments"] if d["name"] == "HR")["vacant"] is True


async def test_a_stuck_update_in_a_department_with_no_admin_can_be_answered_by_promoting_a_worker(engine, org, connect):
    su = await connect("cid-su")
    dept = (await su.ok("hierarchy.department_create", {"name": "Logistics"}))["department_id"]
    worker = await su.ok("hierarchy.account_create", {"role": "worker", "department_id": dept, "hostname": "LOG-01"})
    issue_id, _ = await console_issues.raise_issue(engine, type_="update", severity="high", title="Update past the escalation limit", subject="1.4.0 -> 1.4.3",
                                                   pc_id=worker["pc_id"], source_table="pc_version_status", source_id=worker["pc_id"],
                                                   detail={"current": "1.4.0", "target": "1.4.3", "attempts": 3})
    got = await su.ok("issues.get", {"issue_id": issue_id})
    admin_option = next(o for o in got["options"] if o["key"] == "admin")
    assert [p["value"] for p in admin_option["pick"]] == [worker["account_id"]] and "Logistics" in admin_option["title"]

    res = await su.ok("issues.act", {"issue_id": issue_id, "key": "admin", "account_id": worker["account_id"]})
    done = res["done"]
    assert done["label"] == "Assigned" and done["promoted"]["role"] == "admin" and done["promoted"]["client_key"]
    assert res["issue"]["owner"]["account_id"] == worker["account_id"]
    assert "admin" not in {o["key"] for o in (await su.ok("issues.get", {"issue_id": issue_id}))["options"]}                    # the department has an Admin now
