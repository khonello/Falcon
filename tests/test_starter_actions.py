"""The actions that come with Falcon (migration 055, engine/control/starter.py; the user, 13 Nov 2026).

A fresh install's library is not empty; Falcon's own actions are made by nobody and named "Falcon"; the Engine adds the missing ones at every
start, and one an Admin archived stays archived."""

from __future__ import annotations

from engine.control import starter
from tests.conftest import requires_db


def test_the_list_itself_is_sound():
    assert starter.problems() == []
    assert len(starter.STARTER) >= 30
    kinds = {s.kind for s in starter.STARTER}
    assert kinds == {"control", "monitoring", "custom"}


@requires_db
async def test_a_fresh_library_has_falcons_actions(engine, org, connect):
    assert await starter.ensure(engine.db) == len(starter.STARTER)          # what the Engine does at start (the test Engine leaves it out)
    a1 = await connect("cid-a1")
    lib = (await a1.ok("control.action_list"))["actions"]
    mine = [a for k in lib.values() for a in k if a.get("falcon_key")]
    assert len(mine) == len(starter.STARTER)
    assert all(a["created_by_name"] == "Falcon" and a["created_by_account_id"] is None for a in mine)
    shot = next(a for a in mine if a["falcon_key"] == "screenshot")
    assert shot["name"] == "Take a screenshot" and shot["action_kind"] == "control"
    disk = next(a for a in mine if a["falcon_key"] == "disk-space")
    assert disk["action_kind"] == "custom" and disk["output_kind"] == "list" and disk["custom_script_language"] == "powershell"
    # any Admin may change one; the change stays
    await a1.ok("control.action_update", {"action_id": disk["id"], "name": "Disk space left"})
    # archived, it stays archived when the Engine starts again; nothing else is added twice
    await a1.ok("control.action_delete", {"action_id": shot["id"]})
    assert await starter.ensure(engine.db) == 0
    lib = (await a1.ok("control.action_list"))["actions"]
    left = {a["falcon_key"]: a for k in lib.values() for a in k if a.get("falcon_key")}
    assert "screenshot" not in left and left["disk-space"]["name"] == "Disk space left"
    assert await engine.db.pool.fetchval("SELECT count(*) FROM actions WHERE falcon_key IS NOT NULL") == len(starter.STARTER)


@requires_db
async def test_nobody_but_falcon_has_no_maker(engine, org):
    import asyncpg
    import pytest

    with pytest.raises(asyncpg.CheckViolationError):
        await engine.db.control.create_action(None, "control", 30, builtin_type="screenshot", name="nobody's")
