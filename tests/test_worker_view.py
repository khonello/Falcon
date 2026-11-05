"""What the Worker's program is told (ENGINE-GAPS 24, 26) and what Announcements shows every Admin (25)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from tests.conftest import requires_db
from tests.test_worker_client import _admin, _start

pytestmark = requires_db


async def test_a_task_says_when_it_was_given_started_and_what_shows_it_and_a_closed_one_says_who_closed_it(engine, org, tmp_path: Path):
    svc = await _start(engine, tmp_path, "cid-w1", [])
    admin = await _admin(engine)
    try:
        made = await admin.call("task.create", {"assignee_account_id": org["w1"], "description": "Update sales.xlsx.", "verification_mode": "stack",
                                                "items": [{"target_type": "file", "intent": "create", "name": "sales.xlsx"}]})
        tid = made["task"]["id"]
        await svc.call("task.start", {"task_id": tid})
        svc._view_at = 0.0
        [task] = (await svc.app_view())["tasks"]
        assert task["given"] and task["started_at"] and task["started"] is True
        assert [s["name"] for s in task["signs"]] == ["sales.xlsx"] and task["signs"][0]["program"] is False and task["signs"][0]["seen"] is None
        item = (await engine.db.tasks.items(tid))[0]
        await engine.db.pool.execute("INSERT INTO expectations (verification_item_id, signal_type) VALUES ($1, 'file_changed')", item["id"])
        svc._view_at = 0.0
        assert (await svc.app_view())["tasks"][0]["signs"][0]["seen"]                       # a sign of the work, with when
        await admin.call("task.verify", {"task_id": tid, "outcome": "complete"})
        svc._view_at = 0.0
        v = await svc.app_view()
        assert v["tasks"] == [] and [c["id"] for c in v["closed"]] == [tid]
        assert v["closed"][0]["title"] == "Update sales.xlsx" and v["closed"][0]["closed_by"] and v["closed"][0]["closed_at"]
    finally:
        await admin.close()
        await svc.stop()


async def test_a_task_closed_last_month_is_not_on_the_list(engine, org, tmp_path: Path):
    svc = await _start(engine, tmp_path, "cid-w1", [])
    admin = await _admin(engine)
    try:
        tid = (await admin.call("task.create", {"assignee_account_id": org["w1"], "description": "Old work.", "verification_mode": "none", "confirm_none": True}))["task"]["id"]
        await admin.call("task.verify", {"task_id": tid, "outcome": "complete"})
        await engine.db.pool.execute("UPDATE tasks SET completed_at = $2 WHERE id = $1", tid, datetime.now(timezone.utc) - timedelta(days=40))
        svc._view_at = 0.0
        assert (await svc.app_view())["closed"] == []
    finally:
        await admin.close()
        await svc.stop()


async def test_a_waiting_request_survives_a_restart_and_the_conversation_says_it_began_with_one(engine, org, tmp_path: Path):
    svc = await _start(engine, tmp_path, "cid-w1", [])
    admin = await _admin(engine)
    try:
        await svc.app_talk("My printer is stuck")
        svc._view_at = 0.0
        waiting = (await svc.app_view())["request"]
        assert waiting["line"] == "My printer is stuck" and waiting["at"]
        [req] = (await admin.call("chat.requests"))["requests"]
        await admin.call("chat.request_accept", {"request_id": req["id"]})
        svc._view_at = 0.0
        v = await svc.app_view()
        assert v["request"] is None
        [talk] = v["messages"]
        assert talk["from_request"] is True and talk["from"] == "You" and talk["last"] == "My printer is stuck"
        await admin.call("chat.send", {"conversation_id": talk["id"], "body": "On my way"})
        svc._view_at = 0.0
        assert (await svc.app_view())["messages"][0]["from"] != "You"
    finally:
        await admin.close()
        await svc.stop()


async def test_my_machine_says_its_department_whether_it_is_up_to_date_and_since_when_it_is_connected(engine, org, tmp_path: Path):
    svc = await _start(engine, tmp_path, "cid-w1", [])
    try:
        m = (await svc.app_view())["machine"]
        assert m["department"] == "Finance" and m["up_to_date"] is None and m["connected_since"]
        await engine.db.pool.execute("UPDATE pcs SET agent_version = '1.0' WHERE id = $1", org["w1_pc"])
        await engine.db.pool.execute("INSERT INTO versions (version_string, approved_by_account_id) VALUES ('1.0', $1)", org["a1"])
        assert (await svc.call("machines.mine"))["up_to_date"] is True
        await engine.db.pool.execute("UPDATE pcs SET agent_version = '0.9' WHERE id = $1", org["w1_pc"])
        assert (await svc.call("machines.mine"))["up_to_date"] is False
    finally:
        await svc.stop()


async def test_an_emergency_says_when_it_was_read_here(engine, org, tmp_path: Path, monkeypatch):
    from worker_client.windows import spawn

    class Seen:
        async def answer(self):
            return {"seen": True}

        def close(self):
            pass

    async def fake_open(kind, spec):
        return Seen()

    monkeypatch.setattr(spawn, "open_window", fake_open)
    svc = await _start(engine, tmp_path, "cid-w1", [])
    admin = await _admin(engine)
    try:
        made = await admin.call("alerts.create", {"type": "emergency", "audience": "department", "department_id": org["fin"], "title": "Fire", "body": "Leave the building."})
        await svc._show_emergency({"id": made["alert_id"], "title": "Fire", "body": "Leave the building."})
        svc._view_at = 0.0
        [note] = (await svc.app_view())["announcements"]
        assert note["read_at"]
    finally:
        await admin.close()
        await svc.stop()


@pytest.mark.organisation
async def test_every_admin_sees_every_announcement_with_who_sent_it_and_any_may_withdraw_it(engine, org, connect):
    a1, a2 = await connect("cid-a1"), await connect("cid-a2")
    later = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    made = await a1.ok("alerts.create", {"type": "announcement", "audience": "all_users", "title": "Fire drill", "body": "Friday.", "deliver_at": later})
    [seen] = (await a2.ok("alerts.sent"))["alerts"]
    assert seen["id"] == made["alert_id"] and seen["from_name"] and seen["status"] == "scheduled"
    board = await a2.ok("calendar.board", {})
    assert next(i for i in board["items"] if i["kind"] == "announcement")["to"] == ["announcements", None]
    await a2.ok("alerts.cancel", {"alert_id": made["alert_id"]})
    assert (await a1.ok("alerts.sent"))["alerts"][0]["status"] == "withdrawn"
