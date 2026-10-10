"""Database access layer (spec 3.3): every query lives here as a function, never as raw SQL
scattered across combo modules. PostgreSQL via `asyncpg`, natively async -- calls stay on the
event loop, no thread offload.

Rules from database-schema.md 12 that the schema cannot express are enforced *here*:
  * polymorphic references (`reports.source_*`, `audit_log.target_*`) are validated against
    `POLYMORPHIC_TABLES` before insert;
  * no hard DELETE anywhere except `AuditRepo.purge_older_than` -- every other "removal" is a
    status/flag column;
  * Display Names never join across namers; Listeners are listed per adder only.

Repos return plain dicts (asyncpg Records converted) so callers never depend on asyncpg types.
Migrations live in `engine/migrations/` and are applied by `Database.migrate()`.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"

# Legal targets for polymorphic references. Extend deliberately, never ad hoc.
POLYMORPHIC_TABLES = frozenset({
    "accounts", "departments", "pcs", "sessions", "assisted_access_requests", "file_index",
    "tasks", "department_tasks", "verification_items", "manual_verifications", "flows", "flow_destinations",
    "flow_sync_log", "resource_violations", "pings", "message_channels", "messages",
    "listeners", "reports", "event_definitions", "actions", "action_executions",
    "deviation_log", "versions", "pc_version_status", "system_alerts",
    # non-table targets used by the audit trail
    "client", "session", "event", "execution",
})


class NotFound(LookupError):
    pass


class Unavailable(RuntimeError):
    """The database is not connected (FALCON_DATABASE_URL unset)."""


class Conflict(RuntimeError):
    """A database-level guarantee refused the write (e.g. one active session per PC)."""


def _row(r: Any) -> dict[str, Any] | None:
    return None if r is None else dict(r)


def _rows(rs: Any) -> list[dict[str, Any]]:
    return [dict(r) for r in rs]


def _now() -> datetime:
    return datetime.now(timezone.utc)


class Database:
    def __init__(self, url: str | None) -> None:
        self.url = url
        self.pool: Any = None  # asyncpg.Pool once connected

        self.accounts = AccountsRepo(self)
        self.sessions = SessionsRepo(self)
        self.file_index = FileIndexRepo(self)
        self.tasks = TasksRepo(self)
        self.department_tasks = DepartmentTasksRepo(self)
        self.flows = FlowsRepo(self)
        self.reports = ReportsRepo(self)
        self.assistance = AssistanceRepo(self)
        self.control = ControlRepo(self)
        self.audit = AuditRepo(self)
        self.updates = UpdatesRepo(self)
        self.alerts = AlertsRepo(self)
        self.resource = ResourceRepo(self)

    @property
    def connected(self) -> bool:
        return self.pool is not None

    async def connect(self) -> None:
        if not self.url:
            log.warning("FALCON_DATABASE_URL not set -- running with NO database (scaffold only)")
            return
        import asyncpg  # imported lazily so the protocol/test path has no hard dependency

        self.pool = await asyncpg.create_pool(self.url, min_size=1, max_size=4, init=_init_connection)
        log.info("database connected")

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    # --- migrations -----------------------------------------------------------------------------

    @staticmethod
    def migration_files() -> list[Path]:
        return sorted(p for p in MIGRATIONS_DIR.glob("*.sql") if p.name[:3].isdigit())

    async def applied_migrations(self) -> list[str]:
        assert self.pool is not None
        async with self.pool.acquire() as conn:
            await conn.execute(
                "CREATE TABLE IF NOT EXISTS schema_migrations ("
                " name TEXT PRIMARY KEY, applied_at TIMESTAMPTZ NOT NULL DEFAULT now())"
            )
            rows = await conn.fetch("SELECT name FROM schema_migrations ORDER BY name")
        return [r["name"] for r in rows]

    async def migrate(self) -> list[str]:
        """Apply `engine/migrations/NNN_*.sql` in name order, each in its own transaction,
        recording every applied file in `schema_migrations`. Returns the names applied now."""
        if self.pool is None:
            return []
        applied = set(await self.applied_migrations())
        newly: list[str] = []
        for path in self.migration_files():
            if path.name in applied:
                continue
            sql = path.read_text(encoding="utf-8")
            async with self.pool.acquire() as conn, conn.transaction():
                # Files may carry their own BEGIN/COMMIT for psql use; strip them so the
                # runner's transaction is the only one.
                await conn.execute(_strip_txn_wrappers(sql))
                await conn.execute("INSERT INTO schema_migrations (name) VALUES ($1)", path.name)
            log.info("migration applied: %s", path.name)
            newly.append(path.name)
        if not newly:
            log.info("migrations: up to date (%d applied)", len(applied))
        return newly


async def _init_connection(conn: Any) -> None:
    """JSONB columns round-trip as Python objects."""
    import json

    await conn.set_type_codec("jsonb", encoder=json.dumps, decoder=json.loads, schema="pg_catalog")


def _strip_txn_wrappers(sql: str) -> str:
    lines = sql.splitlines()
    kept = [ln for ln in lines if ln.strip().upper() not in ("BEGIN;", "COMMIT;")]
    return "\n".join(kept)


class _Repo:
    def __init__(self, db: Database) -> None:
        self.db = db

    @property
    def pool(self) -> Any:
        if self.db.pool is None:
            raise Unavailable("database not connected (FALCON_DATABASE_URL unset)")
        return self.db.pool

    async def _fetch(self, sql: str, *args: Any) -> list[dict[str, Any]]:
        return _rows(await self.pool.fetch(sql, *args))

    async def _one(self, sql: str, *args: Any) -> dict[str, Any] | None:
        return _row(await self.pool.fetchrow(sql, *args))

    async def _val(self, sql: str, *args: Any) -> Any:
        return await self.pool.fetchval(sql, *args)

    async def _exec(self, sql: str, *args: Any) -> str:
        return await self.pool.execute(sql, *args)


# ============================================================================================
# 1. Identity & Hierarchy
# ============================================================================================

class AccountsRepo(_Repo):
    _ACCOUNT_COLS = ("a.id, a.role, a.department_id, a.bound_pc_id, a.self_display_name, "
                     "a.status, a.assistance_available, a.created_at, "
                     "p.hostname, p.pc_type, p.client_id, p.key_generation, p.last_seen_at, d.name AS department_name")
    _ACCOUNT_FROM = ("FROM accounts a LEFT JOIN pcs p ON p.id = a.bound_pc_id "
                     "LEFT JOIN departments d ON d.id = a.department_id")

    async def by_id(self, account_id: int) -> dict[str, Any] | None:
        return await self._one(f"SELECT {self._ACCOUNT_COLS} {self._ACCOUNT_FROM} WHERE a.id = $1", account_id)

    async def by_client_id(self, client_id: str) -> dict[str, Any] | None:
        """The active account bound to the PC provisioned with this client_id."""
        return await self._one(
            f"SELECT {self._ACCOUNT_COLS} {self._ACCOUNT_FROM} "
            "WHERE p.client_id = $1 AND a.status = 'active'", client_id)

    async def list_all(self) -> list[dict[str, Any]]:
        return await self._fetch(f"SELECT {self._ACCOUNT_COLS} {self._ACCOUNT_FROM} ORDER BY a.id")

    async def active_admins(self) -> list[dict[str, Any]]:
        """Every active Admin, in every department: who may be added as a Listener."""
        return await self._fetch(
            f"SELECT {self._ACCOUNT_COLS} {self._ACCOUNT_FROM} WHERE a.role = 'admin' AND a.status = 'active' "
            "ORDER BY d.name, a.id")

    async def list_department(self, department_id: int) -> list[dict[str, Any]]:
        return await self._fetch(
            f"SELECT {self._ACCOUNT_COLS} {self._ACCOUNT_FROM} WHERE a.department_id = $1 ORDER BY a.id",
            department_id)

    async def create(self, role: str, department_id: int | None, bound_pc_id: int | None) -> int:
        return await self._val(
            "INSERT INTO accounts (role, department_id, bound_pc_id) VALUES ($1, $2, $3) RETURNING id",
            role, department_id, bound_pc_id)

    async def offboard(self, account_id: int) -> None:
        """Status flag only -- never DELETE (Offboarding & Deprovisioning)."""
        await self._exec(
            "UPDATE accounts SET status = 'offboarded', offboarded_at = now() WHERE id = $1", account_id)

    async def set_self_name(self, account_id: int, label: str | None) -> None:
        await self._exec("UPDATE accounts SET self_display_name = $2 WHERE id = $1", account_id, label)

    async def set_assistance_available(self, account_id: int, available: bool) -> None:
        await self._exec("UPDATE accounts SET assistance_available = $2 WHERE id = $1", account_id, available)

    # -- departments / pcs -------------------------------------------------------------------

    async def create_department(self, name: str, created_by_account_id: int) -> int:
        """A new department starts with update escalations routed to it (spec 9.5): a failure past the
        threshold reaches that PC's Admins, not only the Super User. The Super User can change it later."""
        async with self.pool.acquire() as conn, conn.transaction():
            dept_id = await conn.fetchval(
                "INSERT INTO departments (name, created_by_account_id) VALUES ($1, $2) RETURNING id",
                name, created_by_account_id)
            await conn.execute(
                "INSERT INTO report_routing_config (category, routed_department_id, configured_by_account_id) "
                "VALUES ('update_status', $1, $2) ON CONFLICT DO NOTHING", dept_id, created_by_account_id)
            return dept_id

    async def list_departments(self) -> list[dict[str, Any]]:
        return await self._fetch("SELECT id, name, created_at FROM departments ORDER BY name")

    async def create_pc(self, hostname: str, department_id: int | None, pc_type: str,
                        client_id: str | None = None) -> int:
        return await self._val(
            "INSERT INTO pcs (hostname, department_id, pc_type, client_id) VALUES ($1, $2, $3, $4) RETURNING id",
            hostname, department_id, pc_type, client_id)

    async def rekey_pc(self, pc_id: int) -> int:
        """Bump the key generation: every previously issued key for this PC stops verifying."""
        return await self._val(
            "UPDATE pcs SET key_generation = key_generation + 1 WHERE id = $1 RETURNING key_generation", pc_id)

    async def pc(self, pc_id: int) -> dict[str, Any] | None:
        return await self._one(
            "SELECT p.id, p.hostname, p.department_id, p.pc_type, p.client_id, p.key_generation, p.last_seen_at, "
            "a.id AS bound_account_id, "
            "a.role AS bound_role FROM pcs p LEFT JOIN accounts a ON a.bound_pc_id = p.id AND a.status = 'active' "
            "WHERE p.id = $1", pc_id)

    async def touch_pc(self, pc_id: int) -> None:
        """The machine's client connected or dropped just now."""
        await self._exec("UPDATE pcs SET last_seen_at = now() WHERE id = $1", pc_id)

    async def pcs_in_department(self, department_id: int) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT p.id, p.hostname, p.department_id, p.pc_type, a.id AS bound_account_id, a.role AS bound_role "
            "FROM pcs p LEFT JOIN accounts a ON a.bound_pc_id = p.id AND a.status = 'active' "
            "WHERE p.department_id = $1 ORDER BY p.hostname", department_id)

    async def list_pcs(self) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT p.id, p.hostname, p.department_id, p.pc_type, a.id AS bound_account_id, a.role AS bound_role "
            "FROM pcs p LEFT JOIN accounts a ON a.bound_pc_id = p.id AND a.status = 'active' ORDER BY p.id")

    # -- display names ---------------------------------------------------------------------------

    async def grant_display_name(self, namer_account_id: int, named_account_id: int, label: str) -> None:
        await self._exec(
            "INSERT INTO display_name_grants (namer_account_id, named_account_id, label) VALUES ($1, $2, $3) "
            "ON CONFLICT (namer_account_id, named_account_id) DO UPDATE SET label = EXCLUDED.label",
            namer_account_id, named_account_id, label)

    async def display_names_for(self, viewer_account_id: int,
                                subject_account_ids: list[int]) -> dict[int, str]:
        """What `viewer` sees each subject called.

        Precedence: the viewer's OWN grant -> the subject's self_display_name -> composed
        fallback. The grants join is filtered by namer = viewer and nothing else: a label set
        at another relationship layer is never visible here (non-propagation rule)."""
        if not subject_account_ids:
            return {}
        rows = await self._fetch(
            "SELECT a.id, g.label, a.self_display_name, p.hostname, d.name AS department_name "
            "FROM accounts a "
            "LEFT JOIN display_name_grants g ON g.named_account_id = a.id AND g.namer_account_id = $1 "
            "LEFT JOIN pcs p ON p.id = a.bound_pc_id "
            "LEFT JOIN departments d ON d.id = a.department_id "
            "WHERE a.id = ANY($2::int[])", viewer_account_id, subject_account_ids)
        from engine.hierarchy.display_names import composed_fallback

        return {r["id"]: r["label"] or r["self_display_name"]
                or composed_fallback(r["id"], r["hostname"], r["department_name"]) for r in rows}

    async def display_name_for(self, viewer_account_id: int, subject_account_id: int) -> str:
        names = await self.display_names_for(viewer_account_id, [subject_account_id])
        return names.get(subject_account_id, f"account-{subject_account_id}")


# ============================================================================================
# 2. Traversal & Sessions
# ============================================================================================

class SessionsRepo(_Repo):
    _COLS = ("s.id, s.pc_id, s.occupant_account_id, s.occupied_via, s.entered_at, s.deadline_at, "
             "s.extended_count, s.un_evictable, s.ended_at, s.ended_reason, a.role AS occupant_role")
    _FROM = "FROM sessions s JOIN accounts a ON a.id = s.occupant_account_id"

    async def by_id(self, session_id: int) -> dict[str, Any] | None:
        return await self._one(f"SELECT {self._COLS} {self._FROM} WHERE s.id = $1", session_id)

    async def active_for_pc(self, pc_id: int) -> dict[str, Any] | None:
        return await self._one(
            f"SELECT {self._COLS} {self._FROM} WHERE s.pc_id = $1 AND s.ended_at IS NULL", pc_id)

    async def active_for_account(self, account_id: int) -> dict[str, Any] | None:
        """The session this account currently occupies (its own PC, or one traversed into)."""
        return await self._one(
            f"SELECT {self._COLS} {self._FROM} WHERE s.occupant_account_id = $1 AND s.ended_at IS NULL "
            "ORDER BY s.entered_at DESC LIMIT 1", account_id)

    async def list_active(self) -> list[dict[str, Any]]:
        return await self._fetch(f"SELECT {self._COLS} {self._FROM} WHERE s.ended_at IS NULL ORDER BY s.pc_id")

    async def list_since(self, since: datetime, *, department_id: int | None = None) -> list[dict[str, Any]]:
        """Every session that was open at any point since `since` -- ended ones included. The day's
        record: no status changes, nothing deleted, so a session read here is exactly what happened."""
        return await self._fetch(
            f"SELECT {self._COLS}, p.hostname, p.department_id {self._FROM} JOIN pcs p ON p.id = s.pc_id "
            "WHERE (s.ended_at IS NULL OR s.ended_at >= $1) AND ($2::int IS NULL OR p.department_id = $2) "
            "ORDER BY p.hostname, s.entered_at", since, department_id)

    async def open(self, pc_id: int, occupant_account_id: int, occupied_via: str,
                   deadline_at: datetime | None, un_evictable: bool) -> int:
        """INSERT; the partial unique index `one_active_session_per_pc` refuses an occupied PC.
        Raises `Conflict` so the caller can decide block-or-end-first vs. hard refusal."""
        import asyncpg

        try:
            return await self._val(
                "INSERT INTO sessions (pc_id, occupant_account_id, occupied_via, deadline_at, un_evictable) "
                "VALUES ($1, $2, $3, $4, $5) RETURNING id",
                pc_id, occupant_account_id, occupied_via, deadline_at, un_evictable)
        except asyncpg.UniqueViolationError as exc:
            raise Conflict(f"pc {pc_id} already has an active session") from exc

    async def end(self, session_id: int, reason: str) -> bool:
        status = await self._exec(
            "UPDATE sessions SET ended_at = now(), ended_reason = $2 WHERE id = $1 AND ended_at IS NULL",
            session_id, reason)
        return status.endswith("1")

    async def extend(self, session_id: int, new_deadline: datetime) -> None:
        await self._exec(
            "UPDATE sessions SET deadline_at = $2, extended_count = extended_count + 1 "
            "WHERE id = $1 AND ended_at IS NULL", session_id, new_deadline)

    async def list_expired(self) -> list[dict[str, Any]]:
        return await self._fetch(
            f"SELECT {self._COLS} {self._FROM} WHERE s.ended_at IS NULL AND s.deadline_at IS NOT NULL "
            "AND s.deadline_at < now()")

    # -- assisted access -------------------------------------------------------------------------

    async def create_assisted_request(self, requester_account_id: int, target_department_id: int | None,
                                      entry_path: str, access_ceiling: dict[str, Any],
                                      access_narrowing: dict[str, Any] | None) -> int:
        return await self._val(
            "INSERT INTO assisted_access_requests (requester_account_id, target_department_id, entry_path, "
            "access_ceiling, access_narrowing) VALUES ($1, $2, $3, $4, $5) RETURNING id",
            requester_account_id, target_department_id, entry_path, access_ceiling, access_narrowing)

    async def match_assisted_request(self, request_id: int, helper_account_id: int, session_id: int) -> None:
        await self._exec(
            "UPDATE assisted_access_requests SET helper_account_id = $2, matched_at = now(), "
            "resulting_session_id = $3 WHERE id = $1", request_id, helper_account_id, session_id)

    async def assisted_request(self, request_id: int) -> dict[str, Any] | None:
        return await self._one("SELECT * FROM assisted_access_requests WHERE id = $1", request_id)

    async def available_helpers(self, department_id: int | None, exclude_account_id: int) -> list[dict[str, Any]]:
        """Admins opted in as reachable and not currently occupying any session -- moment-in-time."""
        return await self._fetch(
            "SELECT a.id, a.department_id, d.name AS department_name FROM accounts a "
            "JOIN departments d ON d.id = a.department_id "
            "WHERE a.role = 'admin' AND a.status = 'active' AND a.assistance_available "
            "AND a.id <> $2 AND ($1::int IS NULL OR a.department_id = $1) "
            "AND NOT EXISTS (SELECT 1 FROM sessions s WHERE s.occupant_account_id = a.id AND s.ended_at IS NULL "
            "                AND s.occupied_via <> 'native') ORDER BY a.id",
            department_id, exclude_account_id)


# ============================================================================================
# 3. Global File Index
# ============================================================================================

class FileIndexRepo(_Repo):
    _COLS = ("id, pc_id, path, filename, content_hash, resource_tag, resource_tag_scope_department_id, "
             "indexed_via, last_seen_at")

    async def upsert(self, pc_id: int, path: str, filename: str, content_hash: str | None,
                     resource_tag: str | None, scope_department_id: int | None,
                     indexed_via: str) -> int:
        return await self._val(
            "INSERT INTO file_index (pc_id, path, filename, content_hash, resource_tag, "
            "resource_tag_scope_department_id, indexed_via, last_seen_at) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, now()) "
            "ON CONFLICT (pc_id, path) DO UPDATE SET filename = EXCLUDED.filename, "
            "content_hash = COALESCE(EXCLUDED.content_hash, file_index.content_hash), "
            "resource_tag = COALESCE(EXCLUDED.resource_tag, file_index.resource_tag), "
            "resource_tag_scope_department_id = COALESCE(EXCLUDED.resource_tag_scope_department_id, "
            "                                            file_index.resource_tag_scope_department_id), "
            "indexed_via = EXCLUDED.indexed_via, last_seen_at = now() RETURNING id",
            pc_id, path, filename, content_hash, resource_tag, scope_department_id, indexed_via)

    async def get(self, file_index_id: int) -> dict[str, Any] | None:
        return await self._one(f"SELECT {self._COLS} FROM file_index WHERE id = $1", file_index_id)

    async def by_path(self, pc_id: int, path: str) -> dict[str, Any] | None:
        return await self._one(f"SELECT {self._COLS} FROM file_index WHERE pc_id = $1 AND path = $2", pc_id, path)

    async def by_name(self, filename: str, *, pc_ids: list[int] | None = None) -> list[dict[str, Any]]:
        return await self._fetch(
            f"SELECT {self._COLS} FROM file_index WHERE lower(filename) = lower($1) "
            "AND ($2::int[] IS NULL OR pc_id = ANY($2)) ORDER BY pc_id, path", filename, pc_ids)

    async def folders(self, pc_id: int, limit: int = 500) -> list[dict[str, Any]]:
        """The folders the index knows on one machine, each with how many files it holds -- what a person picks from
        instead of typing a path. Derived from indexed file paths (the index holds files, not directories)."""
        return await self._fetch(
            "SELECT regexp_replace(replace(path, chr(92), '/'), '/[^/]*$', '') AS folder, count(*) AS files "
            "FROM file_index WHERE pc_id = $1 GROUP BY 1 ORDER BY 1 LIMIT $2", pc_id, limit)

    async def tier_counts(self, department_id: int | None) -> list[dict[str, Any]]:
        """How many indexed files sit on each tier: across a department's machines, or everywhere (None)."""
        return await self._fetch(
            "SELECT f.resource_tag AS tag, count(*) AS files FROM file_index f JOIN pcs p ON p.id = f.pc_id "
            "WHERE f.resource_tag IS NOT NULL AND ($1::int IS NULL OR p.department_id = $1) GROUP BY 1",
            department_id)

    async def by_hash(self, content_hash: str) -> list[dict[str, Any]]:
        return await self._fetch(f"SELECT {self._COLS} FROM file_index WHERE content_hash = $1", content_hash)

    async def set_tag(self, file_index_id: int, resource_tag: str | None, scope_department_id: int | None) -> None:
        await self._exec(
            "UPDATE file_index SET resource_tag = $2, resource_tag_scope_department_id = $3 WHERE id = $1",
            file_index_id, resource_tag, scope_department_id)

    async def under_path(self, pc_id: int, directory: str, *, limit: int = 20) -> list[dict[str, Any]]:
        """Indexed entries below a directory on a PC (case-insensitive, slash-agnostic)."""
        prefix = directory.replace("\\", "/").rstrip("/").lower() + "/"
        return await self._fetch(
            f"SELECT {self._COLS} FROM file_index WHERE pc_id = $1 "
            "AND starts_with(lower(replace(path, '\\', '/')), $2) ORDER BY path LIMIT $3", pc_id, prefix, limit)

    async def tagged(self, tags: tuple[str, ...] = ("admin", "restricted")) -> list[dict[str, Any]]:
        return await self._fetch(
            f"SELECT {self._COLS} FROM file_index WHERE resource_tag = ANY($1::text[]) AND content_hash IS NOT NULL",
            list(tags))

    async def search(self, query: str, *, allowed_tags: list[tuple[str, int | None]],
                     limit: int = 100) -> list[dict[str, Any]]:
        """Substring match on filename, scoped to the caller's access tier: an entry is visible
        if it is untagged or its (tag, scope) pair is in `allowed_tags`."""
        tag_names = [t for t, _ in allowed_tags]
        dept_scopes = [d for t, d in allowed_tags if t == "worker_dept" and d is not None]
        return await self._fetch(
            f"SELECT {self._COLS} FROM file_index WHERE filename ILIKE '%' || $1 || '%' AND ("
            " resource_tag IS NULL"
            " OR (resource_tag <> 'worker_dept' AND resource_tag = ANY($2::text[]))"
            " OR (resource_tag = 'worker_dept' AND resource_tag_scope_department_id = ANY($3::int[]))"
            ") ORDER BY filename, pc_id LIMIT $4", query, tag_names, dept_scopes, limit)


# ============================================================================================
# 4. Task
# ============================================================================================

class TasksRepo(_Repo):
    async def create(self, task: dict[str, Any], items: list[dict[str, Any]]) -> int:
        """Task + its verification stack in one transaction. `items` are dicts with the
        verification_items columns; `linked_file_sequence` is resolved to an id here."""
        async with self.pool.acquire() as conn, conn.transaction():
            task_id = await conn.fetchval(
                "INSERT INTO tasks (assigner_account_id, assignee_account_id, description_raw, "
                "verification_mode, soft_deadline_at, final_deadline_at) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id",
                task["assigner_account_id"], task["assignee_account_id"], task["description_raw"],
                task["verification_mode"], task.get("soft_deadline_at"), task.get("final_deadline_at"))
            ids_by_seq: dict[int, int] = {}
            for item in items:  # files first so program links can resolve
                if item["target_type"] == "file":
                    ids_by_seq[item["sequence"]] = await self._insert_item(conn, task_id, item, None)
            for item in items:
                if item["target_type"] == "program":
                    link = item.get("linked_file_sequence")
                    ids_by_seq[item["sequence"]] = await self._insert_item(
                        conn, task_id, item, ids_by_seq.get(link) if link is not None else None)
            return task_id

    @staticmethod
    async def _insert_item(conn: Any, task_id: int, item: dict[str, Any], linked_id: int | None) -> int:
        return await conn.fetchval(
            "INSERT INTO verification_items (task_id, sequence, target_type, intent, file_index_id, "
            "proposed_filename, proposed_path, linked_file_verification_item_id, program_name, populated_by) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10) RETURNING id",
            task_id, item["sequence"], item["target_type"], item["intent"], item.get("file_index_id"),
            item.get("proposed_filename"), item.get("proposed_path"), linked_id,
            item.get("program_name"), item.get("populated_by", "llm"))

    # checks_passed / checks_total travel with every task row, so a list shows "2 of 3 checks passed" without a
    # task.get per task (Work's "Yours").
    _TASK_COLS = ("t.*, a.bound_pc_id AS assignee_pc_id, a.department_id AS assignee_department_id, "
                  "a.role AS assignee_role, "
                  "(SELECT count(*) FROM verification_items v WHERE v.task_id = t.id) AS checks_total, "
                  "(SELECT count(*) FROM verification_items v WHERE v.task_id = t.id AND v.status = 'passed') AS checks_passed")
    _TASK_FROM = "FROM tasks t JOIN accounts a ON a.id = t.assignee_account_id"

    async def get(self, task_id: int) -> dict[str, Any] | None:
        task = await self._one(f"SELECT {self._TASK_COLS} {self._TASK_FROM} WHERE t.id = $1", task_id)
        if task is None:
            return None
        task["items"] = await self.items(task_id)
        task["manual_verification"] = await self._one(
            "SELECT * FROM manual_verifications WHERE task_id = $1", task_id)
        return task

    async def items(self, task_id: int) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT v.*, f.path AS file_path, f.content_hash AS file_hash, f.last_seen_at AS file_last_seen_at "
            "FROM verification_items v LEFT JOIN file_index f ON f.id = v.file_index_id "
            "WHERE v.task_id = $1 ORDER BY v.sequence", task_id)

    async def item(self, item_id: int) -> dict[str, Any] | None:
        return await self._one("SELECT * FROM verification_items WHERE id = $1", item_id)

    async def list_for(self, account_id: int, *, include_completed: bool = False) -> list[dict[str, Any]]:
        """Tasks the account assigned or is assigned."""
        return await self._fetch(
            f"SELECT {self._TASK_COLS} {self._TASK_FROM} "
            "WHERE (t.assigner_account_id = $1 OR t.assignee_account_id = $1) "
            "AND ($2 OR t.status <> 'completed') ORDER BY t.created_at DESC", account_id, include_completed)

    async def list_department(self, department_id: int, *, include_completed: bool = False) -> list[dict[str, Any]]:
        return await self._fetch(
            f"SELECT {self._TASK_COLS} {self._TASK_FROM} WHERE a.department_id = $1 "
            "AND ($2 OR t.status <> 'completed') ORDER BY t.created_at DESC", department_id, include_completed)

    async def active(self) -> list[dict[str, Any]]:
        return await self._fetch(f"SELECT {self._TASK_COLS} {self._TASK_FROM} WHERE t.status <> 'completed'")

    async def list_all(self, *, include_completed: bool = False) -> list[dict[str, Any]]:
        return await self._fetch(
            f"SELECT {self._TASK_COLS} {self._TASK_FROM} WHERE ($1 OR t.status <> 'completed') "
            "ORDER BY t.created_at DESC", include_completed)

    async def active_for_pc(self, pc_id: int) -> list[dict[str, Any]]:
        """Open tasks whose assignee is bound to this PC, with their items -- what a file event
        or program signal from that PC can be matched against."""
        tasks = await self._fetch(
            f"SELECT {self._TASK_COLS} {self._TASK_FROM} WHERE a.bound_pc_id = $1 AND t.status <> 'completed'",
            pc_id)
        for t in tasks:
            t["items"] = await self.items(t["id"])
        return tasks

    async def latest_signal(self, item_id: int, signal_type: str) -> dict[str, Any] | None:
        return await self._one(
            "SELECT * FROM expectations WHERE verification_item_id = $1 AND signal_type = $2 "
            "ORDER BY observed_at DESC LIMIT 1", item_id, signal_type)

    async def mark_started(self, task_id: int) -> None:
        await self._exec(
            "UPDATE tasks SET status = 'in_progress', started_at = COALESCE(started_at, now()) "
            "WHERE id = $1 AND status = 'active'", task_id)

    async def set_item_status(self, item_id: int, status: str) -> None:
        await self._exec("UPDATE verification_items SET status = $2 WHERE id = $1", item_id, status)

    async def bind_item_file(self, item_id: int, file_index_id: int) -> None:
        await self._exec("UPDATE verification_items SET file_index_id = $2 WHERE id = $1", item_id, file_index_id)

    async def add_expectation(self, item_id: int, signal_type: str, value: dict[str, Any] | None) -> None:
        await self._exec(
            "INSERT INTO expectations (verification_item_id, signal_type, value) VALUES ($1, $2, $3)",
            item_id, signal_type, value)

    async def expectations(self, task_id: int, *, limit_per_item: int = 20) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT e.* FROM expectations e JOIN verification_items v ON v.id = e.verification_item_id "
            "WHERE v.task_id = $1 ORDER BY e.observed_at DESC LIMIT $2", task_id, limit_per_item * 10)

    async def record_manual_verification(self, task_id: int, verifier_account_id: int, outcome: str) -> None:
        """The only path to 'completed'. Caller has already checked verifier == assigner."""
        async with self.pool.acquire() as conn, conn.transaction():
            await conn.execute(
                "INSERT INTO manual_verifications (task_id, verified_by_account_id, outcome) VALUES ($1, $2, $3) "
                "ON CONFLICT (task_id) DO UPDATE SET verified_by_account_id = EXCLUDED.verified_by_account_id, "
                "outcome = EXCLUDED.outcome, verified_at = now()", task_id, verifier_account_id, outcome)
            if outcome == "complete":
                await conn.execute(
                    "UPDATE tasks SET status = 'completed', completed_at = now() WHERE id = $1", task_id)


# ============================================================================================
# 5. Flow
# ============================================================================================

class DepartmentTasksRepo(_Repo):
    """Tasks the Super User gives a department (migration 017): no checks, one deadline, a state per Admin told."""

    async def create(self, department_id: int, assigner_id: int, title: str, deadline_at: datetime,
                     admin_ids: list[int]) -> int:
        async with self.pool.acquire() as conn, conn.transaction():
            task_id = await conn.fetchval(
                "INSERT INTO department_tasks (department_id, assigner_account_id, title, deadline_at) "
                "VALUES ($1, $2, $3, $4) RETURNING id", department_id, assigner_id, title, deadline_at)
            for admin_id in admin_ids:
                await conn.execute(
                    "INSERT INTO department_task_admins (task_id, account_id) VALUES ($1, $2)", task_id, admin_id)
            return task_id

    async def get(self, task_id: int) -> dict[str, Any] | None:
        return await self._one(
            "SELECT t.*, d.name AS department_name FROM department_tasks t "
            "JOIN departments d ON d.id = t.department_id WHERE t.id = $1", task_id)

    async def list(self, *, department_id: int | None = None, account_id: int | None = None,
                   include_completed: bool = False) -> list[dict[str, Any]]:
        """Newest first. `account_id` limits to the tasks that Admin was told."""
        return await self._fetch(
            "SELECT t.*, d.name AS department_name FROM department_tasks t "
            "JOIN departments d ON d.id = t.department_id "
            "WHERE ($1::int IS NULL OR t.department_id = $1) "
            "AND ($2::int IS NULL OR EXISTS (SELECT 1 FROM department_task_admins a "
            "                                WHERE a.task_id = t.id AND a.account_id = $2)) "
            "AND ($3 OR t.completed_at IS NULL) ORDER BY t.created_at DESC, t.id DESC",
            department_id, account_id, include_completed)

    async def admins(self, task_ids: list[int]) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT a.task_id, a.account_id, a.state, a.state_at, a.seen_at FROM department_task_admins a "
            "WHERE a.task_id = ANY($1::int[]) ORDER BY a.task_id, a.account_id", task_ids)

    async def mark(self, task_id: int, account_id: int, state: str) -> bool:
        """The Admin's own row only. First `seen` is remembered. False if that Admin was not told."""
        status = await self._exec(
            "UPDATE department_task_admins SET state = $3, state_at = now(), seen_at = COALESCE(seen_at, now()) "
            "WHERE task_id = $1 AND account_id = $2", task_id, account_id, state)
        return status.endswith("1")

    async def complete(self, task_id: int) -> None:
        await self._exec("UPDATE department_tasks SET completed_at = now() WHERE id = $1", task_id)

    async def send_back(self, task_id: int, by_account_id: int, note: str) -> None:
        """Open again (if it was completed), every Admin who had finished is ongoing again, and the note is kept."""
        async with self.pool.acquire() as conn, conn.transaction():
            await conn.execute("UPDATE department_tasks SET completed_at = NULL WHERE id = $1", task_id)
            await conn.execute(
                "UPDATE department_task_admins SET state = 'ongoing', state_at = now() "
                "WHERE task_id = $1 AND state = 'done'", task_id)
            await conn.execute(
                "INSERT INTO department_task_notes (task_id, by_account_id, text) VALUES ($1, $2, $3)",
                task_id, by_account_id, note)

    async def notes(self, task_ids: list[int]) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT id, task_id, by_account_id, text, at FROM department_task_notes "
            "WHERE task_id = ANY($1::int[]) ORDER BY at, id", task_ids)

    async def open_tasks(self) -> list[dict[str, Any]]:
        return await self._fetch("SELECT * FROM department_tasks WHERE completed_at IS NULL")


class FlowsRepo(_Repo):
    async def create(self, flow: dict[str, Any], destinations: list[dict[str, Any]],
                     stages: list[dict[str, Any]]) -> int:
        """Stages reference each other by list index in `parent_index`; destinations reference
        a stage the same way. Resolved to ids inside one transaction."""
        async with self.pool.acquire() as conn, conn.transaction():
            flow_id = await conn.fetchval(
                "INSERT INTO flows (created_by_account_id, source_pc_id, source_path, consent_status) "
                "VALUES ($1, $2, $3, $4) RETURNING id",
                flow["created_by_account_id"], flow["source_pc_id"], flow["source_path"], flow["consent_status"])
            stage_ids: list[int] = []
            for st in stages:
                parent = stage_ids[st["parent_index"]] if st.get("parent_index") is not None else None
                stage_ids.append(await conn.fetchval(
                    "INSERT INTO flow_stages (flow_id, parent_stage_id, stage_type, config) "
                    "VALUES ($1, $2, $3, $4) RETURNING id", flow_id, parent, st["stage_type"], st.get("config")))
            for d in destinations:
                parent = stage_ids[d["parent_index"]] if d.get("parent_index") is not None else None
                await conn.execute(
                    "INSERT INTO flow_destinations (flow_id, parent_stage_id, destination_pc_id, destination_path, "
                    "owner_account_id, pre_flight_check_status) VALUES ($1, $2, $3, $4, $5, $6)",
                    flow_id, parent, d.get("destination_pc_id"), d["destination_path"], d["owner_account_id"],
                    d.get("pre_flight_check_status", "passed"))
            return flow_id

    async def get(self, flow_id: int) -> dict[str, Any] | None:
        flow = await self._one("SELECT * FROM flows WHERE id = $1", flow_id)
        if flow is None:
            return None
        flow["stages"] = await self._fetch("SELECT * FROM flow_stages WHERE flow_id = $1 ORDER BY id", flow_id)
        flow["destinations"] = await self._fetch(
            "SELECT * FROM flow_destinations WHERE flow_id = $1 AND removed_at IS NULL ORDER BY id", flow_id)
        return flow

    async def destination(self, destination_id: int) -> dict[str, Any] | None:
        return await self._one("SELECT * FROM flow_destinations WHERE id = $1", destination_id)

    async def list_for(self, account_id: int, *, department_id: int | None) -> list[dict[str, Any]]:
        """Flows the account created, owns a destination of, or whose endpoints sit in their department."""
        return await self._fetch(
            # the source's hostname rides along: a flow is read as "from OPS-02", never as an id
            "SELECT DISTINCT f.*, sp.hostname AS source_hostname FROM flows f "
            "LEFT JOIN pcs sp ON sp.id = f.source_pc_id "
            "LEFT JOIN flow_destinations fd ON fd.flow_id = f.id AND fd.removed_at IS NULL "
            "LEFT JOIN pcs dp ON dp.id = fd.destination_pc_id "
            "WHERE f.status <> 'inactive' AND (f.created_by_account_id = $1 OR fd.owner_account_id = $1 "
            "   OR ($2::int IS NOT NULL AND (sp.department_id = $2 OR dp.department_id = $2))) "
            "ORDER BY f.id", account_id, department_id)

    async def list_all(self) -> list[dict[str, Any]]:
        return await self._fetch("SELECT f.*, sp.hostname AS source_hostname FROM flows f "
                                 "LEFT JOIN pcs sp ON sp.id = f.source_pc_id WHERE f.status <> 'inactive' ORDER BY f.id")

    async def sources_for_pc(self, pc_id: int) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT id, source_path FROM flows WHERE source_pc_id = $1 AND status = 'active'", pc_id)

    async def destinations_for_pc(self, pc_id: int) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT d.*, f.status AS flow_status FROM flow_destinations d JOIN flows f ON f.id = d.flow_id "
            "WHERE d.destination_pc_id = $1 AND d.removed_at IS NULL AND f.status <> 'inactive'", pc_id)

    async def graph_edges(self) -> list[tuple[str, str]]:
        """(source, destination) as 'pc_id:path' nodes, for cycle prevention. Remote-storage
        destinations use 'remote:path'."""
        rows = await self._fetch(
            "SELECT f.source_pc_id, f.source_path, d.destination_pc_id, d.destination_path "
            "FROM flows f JOIN flow_destinations d ON d.flow_id = f.id "
            "WHERE f.status <> 'inactive' AND d.removed_at IS NULL")
        return [(f"{r['source_pc_id']}:{r['source_path']}",
                 f"{r['destination_pc_id'] if r['destination_pc_id'] is not None else 'remote'}:{r['destination_path']}")
                for r in rows]

    async def set_destination_pause(self, destination_id: int, reason: str | None) -> None:
        await self._exec("UPDATE flow_destinations SET paused_reason = $2 WHERE id = $1", destination_id, reason)

    async def replace_structure(self, flow_id: int, destinations: list[dict[str, Any]],
                                stages: list[dict[str, Any]]) -> None:
        """Edit: old destinations are soft-removed (sync history keeps its references), stages
        and destinations are re-created from the new definition."""
        async with self.pool.acquire() as conn, conn.transaction():
            await conn.execute(
                "UPDATE flow_destinations SET removed_at = now() WHERE flow_id = $1 AND removed_at IS NULL", flow_id)
            stage_ids: list[int] = []
            for st in stages:
                parent = stage_ids[st["parent_index"]] if st.get("parent_index") is not None else None
                stage_ids.append(await conn.fetchval(
                    "INSERT INTO flow_stages (flow_id, parent_stage_id, stage_type, config) "
                    "VALUES ($1, $2, $3, $4) RETURNING id", flow_id, parent, st["stage_type"], st.get("config")))
            for d in destinations:
                parent = stage_ids[d["parent_index"]] if d.get("parent_index") is not None else None
                await conn.execute(
                    "INSERT INTO flow_destinations (flow_id, parent_stage_id, destination_pc_id, destination_path, "
                    "owner_account_id, pre_flight_check_status) VALUES ($1, $2, $3, $4, $5, $6)",
                    flow_id, parent, d.get("destination_pc_id"), d["destination_path"], d["owner_account_id"],
                    d.get("pre_flight_check_status", "passed"))

    async def set_status(self, flow_id: int, status: str, pause_reason: str | None = None) -> None:
        await self._exec(
            "UPDATE flows SET status = $2, pause_reason = $3 WHERE id = $1", flow_id, status, pause_reason)

    async def set_consent(self, flow_id: int, consent_status: str) -> None:
        await self._exec("UPDATE flows SET consent_status = $2 WHERE id = $1", flow_id, consent_status)

    async def set_destination_check(self, destination_id: int, status: str) -> None:
        await self._exec(
            "UPDATE flow_destinations SET pre_flight_check_status = $2 WHERE id = $1", destination_id, status)

    async def log_sync(self, destination_id: int, content_hash: str, written_by: str,
                       written_by_account_id: int | None, conflict_resolved: bool = False, *,
                       source_relative_path: str | None = None, written_path: str | None = None) -> int:
        return await self._val(
            "INSERT INTO flow_sync_log (flow_destination_id, content_hash, written_by, written_by_account_id, "
            "conflict_resolved, source_relative_path, written_path) VALUES ($1, $2, $3, $4, $5, $6, $7) RETURNING id",
            destination_id, content_hash, written_by, written_by_account_id, conflict_resolved,
            source_relative_path, written_path)

    async def last_sync(self, destination_id: int) -> dict[str, Any] | None:
        return await self._one(
            "SELECT * FROM flow_sync_log WHERE flow_destination_id = $1 ORDER BY occurred_at DESC, id DESC LIMIT 1",
            destination_id)

    async def last_flow_write_at(self, destination_id: int, written_path: str) -> dict[str, Any] | None:
        """The flow's own most recent write to this destination path (slash/case-agnostic)."""
        return await self._one(
            "SELECT * FROM flow_sync_log WHERE flow_destination_id = $1 AND written_by = 'flow_sync' "
            "AND lower(replace(written_path, '\\', '/')) = lower(replace($2, '\\', '/')) "
            "ORDER BY occurred_at DESC, id DESC LIMIT 1", destination_id, written_path)

    async def shapes(self, flow_ids: list[int]) -> dict[int, dict[str, list[dict[str, Any]]]]:
        """Every listed flow's stages and live destinations, in two queries rather than two per flow -- what a page
        drawing all flows at once (the Flows map) needs. Destinations carry their machine's hostname."""
        out: dict[int, dict[str, list[dict[str, Any]]]] = {i: {"stages": [], "destinations": []} for i in flow_ids}
        if not flow_ids:
            return out
        for st in await self._fetch("SELECT id, flow_id, parent_stage_id, stage_type, config FROM flow_stages "
                                    "WHERE flow_id = ANY($1::int[]) ORDER BY id", flow_ids):
            out[st["flow_id"]]["stages"].append(st)
        for d in await self._fetch(
                "SELECT d.id, d.flow_id, d.parent_stage_id, d.destination_pc_id, d.destination_path, d.owner_account_id, "
                "d.paused_reason, p.hostname AS destination_hostname FROM flow_destinations d "
                "LEFT JOIN pcs p ON p.id = d.destination_pc_id "
                "WHERE d.flow_id = ANY($1::int[]) AND d.removed_at IS NULL ORDER BY d.id", flow_ids):
            out[d["flow_id"]]["destinations"].append(d)
        return out

    async def hostnames(self, pc_ids: list[int]) -> dict[int, str]:
        if not pc_ids:
            return {}
        return {r["id"]: r["hostname"] for r in await self._fetch("SELECT id, hostname FROM pcs WHERE id = ANY($1::int[])", pc_ids)}

    async def history(self, flow_id: int, limit: int = 200) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT l.*, d.destination_path FROM flow_sync_log l "
            "JOIN flow_destinations d ON d.id = l.flow_destination_id "
            "WHERE d.flow_id = $1 ORDER BY l.occurred_at DESC LIMIT $2", flow_id, limit)


# ============================================================================================
# 8. Reports & Routing
# ============================================================================================

class ReportsRepo(_Repo):
    async def write(self, category: str, source_table: str, source_id: int, summary: str = "") -> int:
        """Written once, with its sentence. Visibility is decided at read time. Never touches
        report_addressed_views."""
        if source_table not in POLYMORPHIC_TABLES:
            raise ValueError(f"unknown report source table {source_table!r}")
        return await self._val(
            "INSERT INTO reports (category, source_table, source_id, summary) VALUES ($1, $2, $3, $4) RETURNING id",
            category, source_table, source_id, summary)

    # Per reader: when this reader first opened the report, and when anyone addressed it.
    _READER_COLS = (
        "(SELECT s.seen_at FROM report_seen s WHERE s.report_id = r.id AND s.account_id = $1) AS seen_at, "
        "(SELECT max(v.addressed_at) FROM report_addressed_views v WHERE v.report_id = r.id) AS addressed_at")

    async def all(self, reader_id: int | None = None, limit: int = 500) -> list[dict[str, Any]]:
        """Super User's view: everything, unconditionally, never filtered by routing."""
        return await self._fetch(
            f"SELECT r.*, {self._READER_COLS} FROM reports r ORDER BY r.generated_at DESC LIMIT $2",
            reader_id, limit)

    async def routed_to_department(self, department_id: int, reader_id: int | None = None,
                                   limit: int = 500) -> list[dict[str, Any]]:
        """An Admin's pane: only categories routed to their department, with addressed state. A
        department routed without the earlier reports sees only those written since it was routed."""
        return await self._fetch(
            f"SELECT r.*, {self._READER_COLS} "
            "FROM reports r JOIN report_routing_config c ON c.category = r.category "
            "WHERE c.routed_department_id = $2 AND (c.includes_earlier OR r.generated_at >= c.configured_at) "
            "ORDER BY r.generated_at DESC LIMIT $3", reader_id, department_id, limit)

    async def mark_seen(self, report_ids: list[int], account_id: int) -> list[int]:
        """First open only: a report already seen keeps its first time. Returns the ids newly seen."""
        rows = await self._fetch(
            "INSERT INTO report_seen (report_id, account_id) SELECT unnest($1::int[]), $2 "
            "ON CONFLICT DO NOTHING RETURNING report_id", report_ids, account_id)
        return sorted(r["report_id"] for r in rows)

    async def routing_config(self) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT c.*, d.name AS department_name FROM report_routing_config c "
            "JOIN departments d ON d.id = c.routed_department_id ORDER BY c.category, d.name")

    async def set_routing(self, category: str, department_ids: list[int], configured_by: int,
                          includes_earlier: bool = True) -> dict[str, list[int]]:
        """Set the routed departments for a category (additive to Super User's view). Departments
        already routed keep their row, so when they were routed and whether they see earlier reports
        stay as they were; `includes_earlier` applies to departments added now. Returns what changed."""
        async with self.pool.acquire() as conn, conn.transaction():
            before = {r["routed_department_id"] for r in await conn.fetch(
                "SELECT routed_department_id FROM report_routing_config WHERE category = $1", category)}
            wanted = set(department_ids)
            added, removed = sorted(wanted - before), sorted(before - wanted)
            # Routing config is configuration, not history: removing a row is not a "removal" of
            # a system record, so a DELETE here is acceptable and the change is audited.
            if removed:
                await conn.execute(
                    "DELETE FROM report_routing_config WHERE category = $1 AND routed_department_id = ANY($2::int[])",
                    category, removed)
            for dept in added:
                await conn.execute(
                    "INSERT INTO report_routing_config (category, routed_department_id, configured_by_account_id, "
                    "includes_earlier) VALUES ($1, $2, $3, $4)", category, dept, configured_by, includes_earlier)
            return {"added": added, "removed": removed}

    async def earlier_unaddressed(self, category: str) -> int:
        """Reports of a category written so far that nobody has marked addressed: what adding a
        department with its earlier reports hands to that department's Admins."""
        return await self._val(
            "SELECT count(*) FROM reports r WHERE r.category = $1 AND NOT EXISTS "
            "(SELECT 1 FROM report_addressed_views v WHERE v.report_id = r.id)", category)

    async def departments_for_category(self, category: str) -> list[int]:
        rows = await self._fetch(
            "SELECT routed_department_id FROM report_routing_config WHERE category = $1", category)
        return [r["routed_department_id"] for r in rows]

    async def mark_addressed(self, report_id: int, addressed_by_account_id: int) -> int:
        """Writes the Super-User-only View row. The report itself is untouched."""
        return await self._val(
            "INSERT INTO report_addressed_views (report_id, addressed_by_account_id) VALUES ($1, $2) RETURNING id",
            report_id, addressed_by_account_id)

    async def addressed_views(self, limit: int = 500) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT v.*, r.category, a.department_id AS addressed_by_department_id "
            "FROM report_addressed_views v JOIN reports r ON r.id = v.report_id "
            "JOIN accounts a ON a.id = v.addressed_by_account_id ORDER BY v.addressed_at DESC LIMIT $1", limit)


# ============================================================================================
# 7. Assistance
# ============================================================================================

class AssistanceRepo(_Repo):
    async def ping(self, sender_account_id: int, receiver_account_id: int) -> int:
        return await self._val(
            "INSERT INTO pings (sender_account_id, receiver_account_id) VALUES ($1, $2) RETURNING id",
            sender_account_id, receiver_account_id)

    async def get_ping(self, ping_id: int) -> dict[str, Any] | None:
        return await self._one("SELECT * FROM pings WHERE id = $1", ping_id)

    async def unaddressed_pings(self, receiver_account_id: int) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT * FROM pings WHERE receiver_account_id = $1 AND addressed_at IS NULL ORDER BY sent_at",
            receiver_account_id)

    async def unaddressed_ping_count(self, receiver_account_id: int) -> int:
        return await self._val(
            "SELECT count(*) FROM pings WHERE receiver_account_id = $1 AND addressed_at IS NULL",
            receiver_account_id)

    async def address_pings(self, receiver_account_id: int, sender_account_id: int) -> None:
        await self._exec(
            "UPDATE pings SET addressed_at = now() WHERE receiver_account_id = $1 AND sender_account_id = $2 "
            "AND addressed_at IS NULL", receiver_account_id, sender_account_id)

    async def open_channel(self, ping_id: int, initiator_account_id: int, superior_account_id: int,
                           first_turn: str = "sender") -> int:
        return await self._val(
            "INSERT INTO message_channels (opened_via_ping_id, initiator_account_id, superior_account_id, turn) "
            "VALUES ($1, $2, $3, $4) RETURNING id", ping_id, initiator_account_id, superior_account_id, first_turn)

    async def channel(self, channel_id: int) -> dict[str, Any] | None:
        return await self._one("SELECT * FROM message_channels WHERE id = $1", channel_id)

    async def open_channel_between(self, a: int, b: int) -> dict[str, Any] | None:
        return await self._one(
            "SELECT * FROM message_channels WHERE closed_at IS NULL AND "
            "((initiator_account_id = $1 AND superior_account_id = $2) OR "
            " (initiator_account_id = $2 AND superior_account_id = $1)) ORDER BY opened_at DESC LIMIT 1", a, b)

    async def channels_for(self, account_id: int) -> list[dict[str, Any]]:
        """Channels the account is a party to, plus those it listens on."""
        return await self._fetch(
            "SELECT DISTINCT c.* FROM message_channels c "
            "LEFT JOIN listeners l ON l.message_channel_id = c.id "
            "WHERE c.initiator_account_id = $1 OR c.superior_account_id = $1 OR l.listener_account_id = $1 "
            "ORDER BY c.opened_at DESC", account_id)

    async def post_message(self, channel_id: int, sender_account_id: int, body: str, next_turn: str) -> int:
        async with self.pool.acquire() as conn, conn.transaction():
            msg_id = await conn.fetchval(
                "INSERT INTO messages (message_channel_id, sender_account_id, body) VALUES ($1, $2, $3) RETURNING id",
                channel_id, sender_account_id, body)
            await conn.execute("UPDATE message_channels SET turn = $2 WHERE id = $1", channel_id, next_turn)
            return msg_id

    async def messages(self, channel_id: int) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT * FROM messages WHERE message_channel_id = $1 ORDER BY sent_at", channel_id)

    async def close_channel(self, channel_id: int) -> None:
        await self._exec("UPDATE message_channels SET closed_at = now() WHERE id = $1 AND closed_at IS NULL",
                         channel_id)

    async def add_listener(self, channel_id: int, listener_account_id: int, added_by_account_id: int) -> bool:
        """Dedup by UNIQUE(channel, listener): a second add is a no-op. Returns True if inserted."""
        status = await self._exec(
            "INSERT INTO listeners (message_channel_id, listener_account_id, added_by_account_id) "
            "VALUES ($1, $2, $3) ON CONFLICT DO NOTHING", channel_id, listener_account_id, added_by_account_id)
        return status.endswith("1")

    async def listeners_added_by(self, channel_id: int, added_by_account_id: int) -> list[dict[str, Any]]:
        """Scoped to the requesting party's own additions only -- never a join across both."""
        return await self._fetch(
            "SELECT * FROM listeners WHERE message_channel_id = $1 AND added_by_account_id = $2 ORDER BY added_at",
            channel_id, added_by_account_id)

    async def listener_account_ids(self, channel_id: int) -> list[int]:
        """Engine-internal: who to push real-time messages to. Not exposed to either party."""
        rows = await self._fetch("SELECT listener_account_id FROM listeners WHERE message_channel_id = $1", channel_id)
        return [r["listener_account_id"] for r in rows]


# ============================================================================================
# 9. Control, Events, Monitoring, Actions
# ============================================================================================

# A run that kept a picture still in retention (migration 014).
_HAS_IMAGE = "EXISTS (SELECT 1 FROM execution_images i WHERE i.execution_id = e.id AND i.data IS NOT NULL) AS has_image"


class ControlRepo(_Repo):
    # -- installed programs (migration 016) --------------------------------------------------------

    async def save_programs(self, pc_id: int, programs: list[dict[str, Any]]) -> None:
        await self._exec(
            "INSERT INTO pc_programs (pc_id, programs) VALUES ($1, $2) "
            "ON CONFLICT (pc_id) DO UPDATE SET programs = EXCLUDED.programs, reported_at = now()", pc_id, programs)

    async def programs_for(self, pc_ids: list[int]) -> list[dict[str, Any]]:
        return await self._fetch("SELECT pc_id, programs, reported_at FROM pc_programs WHERE pc_id = ANY($1::int[])", pc_ids)

    # -- levels over time --------------------------------------------------------------------------

    async def add_metric_sample(self, pc_id: int, cpu: float, memory: float, idle_s: float) -> None:
        await self._exec(
            "INSERT INTO metric_samples (pc_id, cpu, memory, idle_s) VALUES ($1, $2, $3, $4) "
            "ON CONFLICT DO NOTHING", pc_id, cpu, memory, idle_s)

    async def typical_levels(self, pc_ids: list[int] | None, days: int = 7) -> dict[str, Any]:
        """The p10-p90 of each metric over the last `days`, across the given machines (None: all)."""
        row = await self._one(
            "SELECT count(*) AS samples, count(DISTINCT pc_id) AS machines, min(sampled_at) AS since, "
            "percentile_cont(ARRAY[0.1, 0.9]) WITHIN GROUP (ORDER BY cpu) AS cpu, "
            "percentile_cont(ARRAY[0.1, 0.9]) WITHIN GROUP (ORDER BY memory) AS memory, "
            "percentile_cont(ARRAY[0.1, 0.9]) WITHIN GROUP (ORDER BY idle_s) AS idle_s "
            "FROM metric_samples WHERE sampled_at >= now() - make_interval(days => $1) "
            "AND ($2::int[] IS NULL OR pc_id = ANY($2::int[]))", days, pc_ids)
        return row or {"samples": 0}

    # -- events ----------------------------------------------------------------------------------

    async def create_event(self, created_by: int, condition_type: str, condition_spec: dict[str, Any]) -> int:
        return await self._val(
            "INSERT INTO event_definitions (created_by_account_id, condition_type, condition_spec) "
            "VALUES ($1, $2, $3) RETURNING id", created_by, condition_type, condition_spec)

    async def update_event(self, event_id: int, *, condition_spec: dict[str, Any] | None = None,
                           enabled: bool | None = None) -> None:
        await self._exec(
            "UPDATE event_definitions SET condition_spec = COALESCE($2, condition_spec), "
            "enabled = COALESCE($3, enabled) WHERE id = $1", event_id, condition_spec, enabled)

    async def event(self, event_id: int) -> dict[str, Any] | None:
        ev = await self._one("SELECT * FROM event_definitions WHERE id = $1", event_id)
        if ev is not None:
            ev["actions"] = await self.actions_for_event(event_id)
        return ev

    async def event_definitions(self, *, condition_type: str | None = None, event_type: str | None = None,
                                created_by: int | None = None, enabled_only: bool = True) -> list[dict[str, Any]]:
        """`event_type` filters on condition_spec->>'type' (e.g. 'usb.inserted')."""
        return await self._fetch(
            "SELECT e.*, EXISTS (SELECT 1 FROM accounts c WHERE c.id = e.created_by_account_id "
            "AND c.role = 'super_user') AS org_wide FROM event_definitions e "
            "WHERE ($1::text IS NULL OR condition_type = $1) "
            "AND ($2::text IS NULL OR condition_spec->>'type' = $2) "
            "AND ($3::int IS NULL OR created_by_account_id = $3) AND (NOT $4 OR enabled) ORDER BY id",
            condition_type, event_type, created_by, enabled_only)

    async def attach_action(self, event_id: int, action_id: int, display_sequence: int) -> None:
        await self._exec(
            "INSERT INTO event_actions (event_definition_id, action_id, display_sequence) VALUES ($1, $2, $3) "
            "ON CONFLICT (event_definition_id, action_id) DO UPDATE SET display_sequence = EXCLUDED.display_sequence",
            event_id, action_id, display_sequence)

    async def detach_action(self, event_id: int, action_id: int) -> None:
        # A join-table row is configuration, not a system record: removing it is fine.
        await self._exec(
            "DELETE FROM event_actions WHERE event_definition_id = $1 AND action_id = $2", event_id, action_id)

    async def actions_for_event(self, event_id: int) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT a.*, ea.display_sequence FROM event_actions ea JOIN actions a ON a.id = ea.action_id "
            "WHERE ea.event_definition_id = $1 AND a.archived_at IS NULL ORDER BY ea.display_sequence", event_id)

    # -- actions ---------------------------------------------------------------------------------

    async def create_action(self, created_by: int, action_kind: str, timeout_seconds: int, *,
                            builtin_type: str | None = None, custom_script: str | None = None,
                            custom_script_language: str | None = None, name: str | None = None,
                            description: str | None = None, params: dict[str, Any] | None = None,
                            timing: dict[str, Any] | None = None) -> int:
        return await self._val(
            "INSERT INTO actions (created_by_account_id, action_kind, builtin_type, custom_script, "
            "custom_script_language, timeout_seconds, name, description, params, timing) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10) RETURNING id",
            created_by, action_kind, builtin_type, custom_script, custom_script_language, timeout_seconds,
            name, description, params, timing)

    async def update_action(self, action_id: int, *, timeout_seconds: int | None = None,
                            custom_script: str | None = None, name: str | None = None,
                            description: str | None = None, params: dict[str, Any] | None = None,
                            timing: dict[str, Any] | None = None) -> None:
        await self._exec(
            "UPDATE actions SET timeout_seconds = COALESCE($2, timeout_seconds), "
            "custom_script = COALESCE($3, custom_script), name = COALESCE($4, name), "
            "description = COALESCE($5, description), params = COALESCE($6, params), "
            "timing = COALESCE($7, timing) WHERE id = $1",
            action_id, timeout_seconds, custom_script, name, description, params, timing)

    async def actions_in_department(self, department_id: int) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT a.* FROM actions a JOIN accounts c ON c.id = a.created_by_account_id "
            "WHERE a.archived_at IS NULL AND c.department_id = $1 ORDER BY a.action_kind, a.id", department_id)

    async def events_in_department(self, department_id: int, *, enabled_only: bool = False) -> list[dict[str, Any]]:
        """The department's own automations, and the Super User's organisation-wide ones that reach
        it: no machine list (every PC), or a list naming at least one of its machines. `org_wide`
        marks the Super User's, which the department may see but not change."""
        return await self._fetch(
            "SELECT e.*, (c.role = 'super_user') AS org_wide FROM event_definitions e "
            "JOIN accounts c ON c.id = e.created_by_account_id "
            "WHERE (NOT $2 OR e.enabled) AND (c.department_id = $1 OR (c.role = 'super_user' AND ("
            "  jsonb_typeof(e.condition_spec->'pc_ids') IS DISTINCT FROM 'array' OR EXISTS ("
            "    SELECT 1 FROM jsonb_array_elements_text(e.condition_spec->'pc_ids') x "
            "    JOIN pcs p ON p.id = x::int WHERE p.department_id = $1)))) "
            "ORDER BY e.id", department_id, enabled_only)

    async def last_executions_for_action(self, action_id: int, limit: int = 5) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT e.*, " + _HAS_IMAGE + " FROM action_executions e WHERE e.action_id = $1 "
            "ORDER BY e.started_at DESC LIMIT $2", action_id, limit)

    async def pending_executions(self) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT e.*, a.timeout_seconds FROM action_executions e JOIN actions a ON a.id = e.action_id "
            "WHERE e.status = 'pending'")

    async def archive_action(self, action_id: int) -> None:
        await self._exec("UPDATE actions SET archived_at = now() WHERE id = $1", action_id)

    async def action(self, action_id: int) -> dict[str, Any] | None:
        return await self._one("SELECT * FROM actions WHERE id = $1", action_id)

    async def actions(self, *, created_by: int | None = None) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT * FROM actions WHERE archived_at IS NULL AND ($1::int IS NULL OR created_by_account_id = $1) "
            "ORDER BY action_kind, id", created_by)

    # -- executions ------------------------------------------------------------------------------

    async def start_execution(self, action_id: int, event_id: int | None, pc_id: int) -> int:
        return await self._val(
            "INSERT INTO action_executions (action_id, triggered_by_event_definition_id, target_pc_id) "
            "VALUES ($1, $2, $3) RETURNING id", action_id, event_id, pc_id)

    async def finish_execution(self, execution_id: int, status: str, *, terminated_reason: str | None = None,
                               output_log_path: str | None = None, exit_code: int | None = None,
                               summary: str | None = None) -> None:
        await self._exec(
            "UPDATE action_executions SET status = $2, terminated_reason = $3, "
            "output_log_path = COALESCE($4, output_log_path), exit_code = $5, summary = $6, ended_at = now() "
            "WHERE id = $1 AND status = 'pending'",
            execution_id, status, terminated_reason, output_log_path, exit_code, summary)

    async def execution(self, execution_id: int) -> dict[str, Any] | None:
        return await self._one("SELECT e.*, " + _HAS_IMAGE + " FROM action_executions e WHERE e.id = $1",
                               execution_id)

    # -- what a run returned (migration 014) -----------------------------------------------------

    async def save_output(self, execution_id: int, output: str | None, result: Any) -> None:
        await self._exec(
            "INSERT INTO execution_outputs (execution_id, output, result) VALUES ($1, $2, $3) "
            "ON CONFLICT (execution_id) DO UPDATE SET output = EXCLUDED.output, result = EXCLUDED.result, "
            "recorded_at = now()", execution_id, output, result)

    async def output(self, execution_id: int) -> dict[str, Any] | None:
        return await self._one("SELECT * FROM execution_outputs WHERE execution_id = $1", execution_id)

    async def save_image(self, execution_id: int, mime: str, data: bytes) -> None:
        await self._exec(
            "INSERT INTO execution_images (execution_id, mime, data, bytes) VALUES ($1, $2, $3, $4) "
            "ON CONFLICT (execution_id) DO UPDATE SET mime = EXCLUDED.mime, data = EXCLUDED.data, "
            "bytes = EXCLUDED.bytes, captured_at = now(), cleared_at = NULL", execution_id, mime, data, len(data))

    async def image(self, execution_id: int) -> dict[str, Any] | None:
        return await self._one("SELECT * FROM execution_images WHERE execution_id = $1", execution_id)

    async def clear_outputs_older_than(self, days: int) -> int:
        """Retention for what runs returned: the text, rows and picture are cleared (set to NULL);
        the run rows and these rows stay, so a run still says it had output that has expired."""
        async with self.pool.acquire() as conn, conn.transaction():
            a = await conn.execute(
                "UPDATE execution_outputs SET output = NULL, result = NULL, cleared_at = now() "
                "WHERE cleared_at IS NULL AND recorded_at < now() - make_interval(days => $1)", days)
            b = await conn.execute(
                "UPDATE execution_images SET data = NULL, cleared_at = now() "
                "WHERE cleared_at IS NULL AND captured_at < now() - make_interval(days => $1)", days)
        return int(a.split()[-1]) + int(b.split()[-1])

    async def live_executions(self) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT e.*, a.action_kind, a.builtin_type FROM action_executions e JOIN actions a ON a.id = e.action_id "
            "WHERE e.status = 'pending' ORDER BY e.started_at DESC")

    async def executions_for_event(self, event_id: int, limit: int = 120) -> list[dict[str, Any]]:
        """What one automation's actions did, newest first, named for reading: the action's name and
        type, the machine's hostname."""
        return await self._fetch(
            "SELECT e.*, a.name AS action_name, a.builtin_type, a.action_kind, p.hostname, "
            + _HAS_IMAGE + " "
            "FROM action_executions e JOIN actions a ON a.id = e.action_id LEFT JOIN pcs p ON p.id = e.target_pc_id "
            "WHERE e.triggered_by_event_definition_id = $1 ORDER BY e.started_at DESC LIMIT $2", event_id, limit)

    async def event_firings(self, event_id: int, limit: int = 30) -> list[dict[str, Any]]:
        """Each time the automation fired, from the audit trail (the one place it is written)."""
        return await self._fetch(
            "SELECT l.occurred_at, l.detail, p.hostname FROM audit_log l "
            "LEFT JOIN pcs p ON p.id = NULLIF(l.detail->>'pc_id', '')::int "
            "WHERE l.action_type = 'event.fired' AND l.target_type = 'event' AND l.target_id = $1 "
            "ORDER BY l.occurred_at DESC LIMIT $2", str(event_id), limit)

    async def recent_executions(self, limit: int = 100) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT e.*, a.action_kind, a.builtin_type FROM action_executions e JOIN actions a ON a.id = e.action_id "
            "ORDER BY e.started_at DESC LIMIT $1", limit)


# ============================================================================================
# 10. Audit Trail
# ============================================================================================

class AuditRepo(_Repo):
    async def write(self, entry: dict[str, Any]) -> None:
        target_type = entry.get("target_type")
        if target_type is not None and target_type not in POLYMORPHIC_TABLES:
            raise ValueError(f"unknown audit target type {target_type!r}")
        await self._exec(
            "INSERT INTO audit_log (actor_account_id, action_type, target_type, target_id, detail, occurred_at) "
            "VALUES ($1, $2, $3, $4, $5, $6)",
            entry.get("actor_account_id"), entry["action"], target_type, entry.get("target_id"),
            entry.get("detail") or {}, entry.get("at") or _now())

    async def recent(self, *, limit: int = 200, actor_account_id: int | None = None,
                     action_prefix: str | None = None) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT * FROM audit_log WHERE ($2::int IS NULL OR actor_account_id = $2) "
            "AND ($3::text IS NULL OR action_type LIKE $3 || '%') ORDER BY occurred_at DESC LIMIT $1",
            limit, actor_account_id, action_prefix)

    async def write_deviation(self, entry: dict[str, Any]) -> int:
        return await self._val(
            "INSERT INTO deviation_log (expectation, observed_account_id, observed_pc_id, detail, "
            "surfaced_to_account_id, detected_at) VALUES ($1, $2, $3, $4, $5, $6) RETURNING id",
            entry["kind"], entry.get("observed_account_id"), entry.get("observed_pc_id"),
            entry.get("detail") or {}, entry["surfaced_to_account_id"], entry.get("at") or _now())

    async def deviations(self, *, unresolved_only: bool = True) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT * FROM deviation_log WHERE (NOT $1 OR resolved_at IS NULL) ORDER BY detected_at DESC",
            unresolved_only)

    async def purge_older_than(self, days: int) -> int:
        """The ONE hard delete in the system: flat retention, every action_type alike."""
        status = await self._exec(
            "DELETE FROM audit_log WHERE occurred_at < now() - make_interval(days => $1)", days)
        return int(status.split()[-1])


# ============================================================================================
# 11. Update & Deployment
# ============================================================================================

class UpdatesRepo(_Repo):
    async def current_version(self) -> dict[str, Any] | None:
        return await self._one("SELECT * FROM versions ORDER BY approved_at DESC LIMIT 1")

    async def version_by_string(self, version_string: str) -> dict[str, Any] | None:
        return await self._one("SELECT * FROM versions WHERE version_string = $1", version_string)

    async def pcs_behind(self, version_id: int) -> list[dict[str, Any]]:
        """PCs not confirmed on `version_id` -- the hard gate for approving N+1."""
        return await self._fetch(
            "SELECT p.id, p.hostname, p.department_id, s.current_version_id, s.escalated_at, "
            " s.attempt_failure_count, s.last_attempt_at FROM pcs p "
            "LEFT JOIN pc_version_status s ON s.pc_id = p.id "
            "WHERE s.current_version_id IS DISTINCT FROM $1 ORDER BY p.department_id, p.hostname", version_id)

    async def approve_version(self, version_string: str, approved_by: int) -> int:
        return await self._val(
            "INSERT INTO versions (version_string, approved_by_account_id) VALUES ($1, $2) RETURNING id",
            version_string, approved_by)

    async def set_target(self, pc_ids: list[int], target_version_id: int) -> None:
        await self._exec(
            "UPDATE pc_version_status SET target_version_id = $2 WHERE pc_id = ANY($1::int[])",
            pc_ids, target_version_id)

    async def record_attempt(self, pc_id: int, version_id: int, succeeded: bool,
                             running_version_id: int | None = None) -> dict[str, Any]:
        """Upsert a PC's status after an update attempt; failure count resets on success.
        `running_version_id` (what the PC is actually on) is needed for a failed first report,
        since a status row must always carry a current version."""
        return _row(await self.pool.fetchrow(
            "INSERT INTO pc_version_status (pc_id, current_version_id, target_version_id, last_attempt_at, "
            "attempt_failure_count) VALUES ($1, CASE WHEN $3::boolean THEN $2::int ELSE $4::int END, "
            "CASE WHEN $3::boolean THEN NULL ELSE $2::int END, now(), CASE WHEN $3::boolean THEN 0 ELSE 1 END) "
            "ON CONFLICT (pc_id) DO UPDATE SET "
            " current_version_id = CASE WHEN $3::boolean THEN $2::int ELSE pc_version_status.current_version_id END, "
            " target_version_id = CASE WHEN $3::boolean THEN NULL ELSE $2::int END, last_attempt_at = now(), "
            " attempt_failure_count = CASE WHEN $3::boolean THEN 0 ELSE pc_version_status.attempt_failure_count + 1 END, "
            " escalated_at = CASE WHEN $3::boolean THEN NULL ELSE pc_version_status.escalated_at END RETURNING *",
            pc_id, version_id, succeeded, running_version_id)) or {}

    async def status_for_pc(self, pc_id: int) -> dict[str, Any] | None:
        return await self._one("SELECT * FROM pc_version_status WHERE pc_id = $1", pc_id)

    async def mark_escalated(self, pc_id: int) -> None:
        await self._exec("UPDATE pc_version_status SET escalated_at = now() WHERE pc_id = $1", pc_id)

    async def rollout_health_by_department(self) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT d.id AS department_id, d.name AS department_name, count(p.id) AS pcs, "
            " count(s.pc_id) FILTER (WHERE s.target_version_id IS NULL) AS current, "
            " count(s.pc_id) FILTER (WHERE s.target_version_id IS NOT NULL) AS pending, "
            " count(s.pc_id) FILTER (WHERE s.escalated_at IS NOT NULL) AS escalated "
            "FROM departments d LEFT JOIN pcs p ON p.department_id = d.id "
            "LEFT JOIN pc_version_status s ON s.pc_id = p.id GROUP BY d.id, d.name ORDER BY d.name")


# ============================================================================================
# 13. System Alerts
# ============================================================================================

class AlertsRepo(_Repo):
    async def create(self, created_by: int, alert_type: str, audience: str, body: str, *,
                     department_id: int | None = None, recipient_account_ids: list[int] | None = None,
                     action_link: str | None = None, deliver_at: datetime | None = None,
                     recurrence: dict[str, Any] | None = None) -> int:
        return await self._val(
            "INSERT INTO system_alerts (created_by_account_id, alert_type, audience, department_id, "
            "recipient_account_ids, body, action_link, deliver_at, recurrence) "
            "VALUES ($1, $2, $3, $4, $5, $6, $7, COALESCE($8, now()), $9) RETURNING id",
            created_by, alert_type, audience, department_id, recipient_account_ids, body, action_link,
            deliver_at, recurrence)

    async def for_account(self, account_id: int, role: str, department_id: int | None,
                          limit: int = 100) -> list[dict[str, Any]]:
        """Alerts addressed to this account, delivered (deliver_at <= now)."""
        return await self._fetch(
            "SELECT * FROM system_alerts WHERE deliver_at <= now() AND ("
            " audience = 'all_users'"
            " OR (audience = 'admin_only' AND $2 IN ('admin', 'super_user'))"
            " OR (audience = 'department' AND department_id = $3)"
            " OR (audience = 'specific_users' AND $1 = ANY(recipient_account_ids))"
            ") ORDER BY deliver_at DESC LIMIT $4", account_id, role, department_id, limit)

    async def pending(self) -> list[dict[str, Any]]:
        return await self._fetch("SELECT * FROM system_alerts WHERE deliver_at > now() ORDER BY deliver_at")

    async def due_undelivered(self) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT * FROM system_alerts WHERE deliver_at <= now() AND delivered_at IS NULL ORDER BY deliver_at")

    async def mark_delivered(self, alert_id: int) -> None:
        await self._exec("UPDATE system_alerts SET delivered_at = now() WHERE id = $1", alert_id)


# ============================================================================================
# 6. Resource
# ============================================================================================

class ResourceRepo(_Repo):
    async def record_violation(self, file_index_id: int, expected_tag: str, found_on_pc_id: int,
                               detected_via: str, surfaced_to_account_id: int) -> int:
        return await self._val(
            "INSERT INTO resource_violations (file_index_id, expected_tag, found_on_pc_id, detected_via, "
            "surfaced_to_account_id) VALUES ($1, $2, $3, $4, $5) RETURNING id",
            file_index_id, expected_tag, found_on_pc_id, detected_via, surfaced_to_account_id)

    async def attach_report(self, violation_id: int, report_id: int) -> None:
        await self._exec("UPDATE resource_violations SET report_id = $2 WHERE id = $1", violation_id, report_id)

    async def open_violation_for_file(self, file_index_id: int) -> dict[str, Any] | None:
        return await self._one(
            "SELECT * FROM resource_violations WHERE file_index_id = $1 AND resolved_at IS NULL", file_index_id)

    async def violation(self, violation_id: int) -> dict[str, Any] | None:
        return await self._one(
            "SELECT v.*, f.path, f.filename, p.department_id FROM resource_violations v "
            "JOIN file_index f ON f.id = v.file_index_id JOIN pcs p ON p.id = v.found_on_pc_id WHERE v.id = $1",
            violation_id)

    async def list_violations(self, *, department_id: int | None = None, account_id: int | None = None,
                              unresolved_only: bool = True) -> list[dict[str, Any]]:
        return await self._fetch(
            "SELECT v.*, f.path, f.filename, p.hostname, p.department_id FROM resource_violations v "
            "JOIN file_index f ON f.id = v.file_index_id JOIN pcs p ON p.id = v.found_on_pc_id "
            "WHERE ($1::int IS NULL OR p.department_id = $1) AND ($2::int IS NULL OR v.surfaced_to_account_id = $2) "
            "AND (NOT $3 OR v.resolved_at IS NULL) ORDER BY v.detected_at DESC",
            department_id, account_id, unresolved_only)

    async def resolve(self, violation_id: int) -> None:
        await self._exec("UPDATE resource_violations SET resolved_at = now() WHERE id = $1 AND resolved_at IS NULL",
                         violation_id)

    async def ignored_file_ids(self, pc_id: int) -> set[int]:
        """Files on a PC currently ignored by the system: unresolved violations."""
        rows = await self._fetch(
            "SELECT file_index_id FROM resource_violations WHERE found_on_pc_id = $1 AND resolved_at IS NULL", pc_id)
        return {r["file_index_id"] for r in rows}
