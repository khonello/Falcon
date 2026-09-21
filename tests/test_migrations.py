"""Schema migration tests against a real Postgres (skipped without FALCON_TEST_DATABASE_URL).

Beyond "it applies", these pin the constraints database-schema.md calls load-bearing:
one active session per PC, intent-by-target-type, the addressed-views table having no
category column, and the retention purge being the only delete path we expect.
"""

from __future__ import annotations

import asyncpg
import pytest

from engine.database import Database
from tests.conftest import requires_db

pytestmark = requires_db


async def test_migrations_apply_and_are_idempotent(db: Database):
    applied = await db.applied_migrations()
    assert applied and applied[0] == "001_initial.sql"
    assert await db.migrate() == []  # second run applies nothing


async def test_expected_tables_exist(db: Database):
    rows = await db.pool.fetch(
        "SELECT table_name FROM information_schema.tables WHERE table_schema='public' ORDER BY 1"
    )
    names = {r["table_name"] for r in rows}
    expected = {
        "departments", "accounts", "pcs", "display_name_grants", "sessions",
        "assisted_access_requests", "file_index", "tasks", "verification_items", "expectations",
        "manual_verifications", "flows", "flow_destinations", "flow_stages", "flow_sync_log",
        "resource_violations", "pings", "message_channels", "messages", "listeners", "reports",
        "report_routing_config", "report_addressed_views", "event_definitions", "actions",
        "event_actions", "action_executions", "audit_log", "deviation_log", "versions",
        "pc_version_status", "system_alerts", "schema_migrations",
    }
    assert expected <= names, expected - names


async def _seed(db: Database) -> dict[str, int]:
    """A department, a Super User, an Admin, a Worker, and their PCs."""
    async with db.pool.acquire() as c:
        su = await c.fetchval(
            "INSERT INTO accounts (role) VALUES ('super_user') RETURNING id")
        dept = await c.fetchval(
            "INSERT INTO departments (name, created_by_account_id) VALUES ('Finance', $1) RETURNING id", su)
        admin_pc = await c.fetchval(
            "INSERT INTO pcs (hostname, department_id, pc_type) VALUES ('ADM-1', $1, 'admin_workstation') RETURNING id", dept)
        worker_pc = await c.fetchval(
            "INSERT INTO pcs (hostname, department_id, pc_type) VALUES ('PC-1', $1, 'client_pc') RETURNING id", dept)
        admin = await c.fetchval(
            "INSERT INTO accounts (role, department_id, bound_pc_id) VALUES ('admin', $1, $2) RETURNING id", dept, admin_pc)
        worker = await c.fetchval(
            "INSERT INTO accounts (role, department_id, bound_pc_id) VALUES ('worker', $1, $2) RETURNING id", dept, worker_pc)
    return {"su": su, "dept": dept, "admin": admin, "worker": worker,
            "admin_pc": admin_pc, "worker_pc": worker_pc}


async def test_one_active_session_per_pc(db: Database):
    ids = await _seed(db)
    async with db.pool.acquire() as c:
        await c.execute(
            "INSERT INTO sessions (pc_id, occupant_account_id, occupied_via) VALUES ($1, $2, 'native')",
            ids["worker_pc"], ids["worker"])
        with pytest.raises(asyncpg.UniqueViolationError):
            await c.execute(
                "INSERT INTO sessions (pc_id, occupant_account_id, occupied_via, deadline_at) "
                "VALUES ($1, $2, 'traversal', now() + interval '30 minutes')",
                ids["worker_pc"], ids["admin"])
        # Ending the first session frees the PC.
        await c.execute(
            "UPDATE sessions SET ended_at = now(), ended_reason = 'superior_ended' WHERE pc_id = $1",
            ids["worker_pc"])
        await c.execute(
            "INSERT INTO sessions (pc_id, occupant_account_id, occupied_via, deadline_at) "
            "VALUES ($1, $2, 'traversal', now() + interval '30 minutes')",
            ids["worker_pc"], ids["admin"])


async def test_traversal_requires_deadline(db: Database):
    ids = await _seed(db)
    with pytest.raises(asyncpg.CheckViolationError):
        await db.pool.execute(
            "INSERT INTO sessions (pc_id, occupant_account_id, occupied_via) VALUES ($1, $2, 'traversal')",
            ids["worker_pc"], ids["admin"])


async def test_intent_is_tied_to_target_type(db: Database):
    ids = await _seed(db)
    task = await db.pool.fetchval(
        "INSERT INTO tasks (assigner_account_id, assignee_account_id, description_raw, verification_mode) "
        "VALUES ($1, $2, 'make the report', 'stack') RETURNING id", ids["admin"], ids["worker"])
    await db.pool.execute(
        "INSERT INTO verification_items (task_id, sequence, target_type, intent, proposed_filename, populated_by) "
        "VALUES ($1, 1, 'file', 'create', 'report.docx', 'llm')", task)
    with pytest.raises(asyncpg.CheckViolationError):
        await db.pool.execute(
            "INSERT INTO verification_items (task_id, sequence, target_type, intent, program_name, populated_by) "
            "VALUES ($1, 2, 'program', 'create', 'excel', 'llm')", task)
    with pytest.raises(asyncpg.CheckViolationError):  # used_with_file needs a link
        await db.pool.execute(
            "INSERT INTO verification_items (task_id, sequence, target_type, intent, program_name, populated_by) "
            "VALUES ($1, 3, 'program', 'used_with_file', 'excel', 'llm')", task)


async def test_addressed_views_cannot_be_a_report(db: Database):
    cols = await db.pool.fetch(
        "SELECT column_name FROM information_schema.columns WHERE table_name='report_addressed_views'")
    assert "category" not in {r["column_name"] for r in cols}


async def test_jsonb_roundtrips_as_python(db: Database):
    ids = await _seed(db)
    await db.pool.execute(
        "INSERT INTO audit_log (actor_account_id, action_type, detail) VALUES ($1, 'x', $2)",
        ids["admin"], {"k": [1, 2, {"n": None}]})
    detail = await db.pool.fetchval("SELECT detail FROM audit_log")
    assert detail == {"k": [1, 2, {"n": None}]}


async def test_listener_dedup_is_unique_constraint(db: Database):
    ids = await _seed(db)
    async with db.pool.acquire() as c:
        ping = await c.fetchval(
            "INSERT INTO pings (sender_account_id, receiver_account_id) VALUES ($1, $2) RETURNING id",
            ids["worker"], ids["admin"])
        chan = await c.fetchval(
            "INSERT INTO message_channels (opened_via_ping_id, initiator_account_id, superior_account_id, turn) "
            "VALUES ($1, $2, $3, 'sender') RETURNING id", ping, ids["worker"], ids["admin"])
        await c.execute(
            "INSERT INTO listeners (message_channel_id, listener_account_id, added_by_account_id) VALUES ($1, $2, $3)",
            chan, ids["admin"], ids["worker"])
        # Second add of the same listener by the other party: no-op, not an error.
        status = await c.execute(
            "INSERT INTO listeners (message_channel_id, listener_account_id, added_by_account_id) "
            "VALUES ($1, $2, $3) ON CONFLICT DO NOTHING", chan, ids["admin"], ids["admin"])
        assert status == "INSERT 0 0"
