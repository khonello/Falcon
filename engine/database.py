"""Database access layer (spec 3.3): every query lives here as a function, never as raw SQL
scattered across combo modules. PostgreSQL via `asyncpg`, natively async -- calls stay on the
event loop, no thread offload.

Two rules from database-schema.md 12 are enforced *here*, not by the schema:
  * polymorphic references (`reports.source_*`, `audit_log.target_*`) have no FK -- this layer
    validates them;
  * no hard DELETE anywhere except the `audit_log` retention job.

SCAFFOLD: connection pooling is real; every repository method is a stub. Migrations live in
`engine/migrations/` and are applied by `Database.migrate()`.
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).parent / "migrations"


class Database:
    def __init__(self, url: str | None) -> None:
        self.url = url
        self.pool: Any = None  # asyncpg.Pool once connected

        self.accounts = AccountsRepo(self)
        self.sessions = SessionsRepo(self)
        self.file_index = FileIndexRepo(self)
        self.tasks = TasksRepo(self)
        self.flows = FlowsRepo(self)
        self.reports = ReportsRepo(self)
        self.assistance = AssistanceRepo(self)
        self.control = ControlRepo(self)
        self.audit = AuditRepo(self)
        self.updates = UpdatesRepo(self)

    async def connect(self) -> None:
        if not self.url:
            log.warning("FALCON_DATABASE_URL not set -- running with NO database (scaffold only)")
            return
        import asyncpg  # imported lazily so the protocol/test path has no hard dependency

        self.pool = await asyncpg.create_pool(self.url, min_size=1, max_size=4)
        log.info("database connected")

    async def close(self) -> None:
        if self.pool is not None:
            await self.pool.close()
            self.pool = None

    async def migrate(self) -> None:
        """Apply `engine/migrations/*.sql` in name order, tracked in `schema_migrations`."""
        if self.pool is None:
            return
        # SCAFFOLD: migration runner to be written alongside 001_initial.sql.
        log.info("migrate: no-op (scaffold)")


class _Repo:
    def __init__(self, db: Database) -> None:
        self.db = db


# --- Identity & Hierarchy (schema 1, 2) --------------------------------------------------------

class AccountsRepo(_Repo):
    async def by_client_id(self, client_id: str) -> dict[str, Any] | None: ...
    async def by_id(self, account_id: int) -> dict[str, Any] | None: ...
    async def list_department(self, department_id: int) -> list[dict[str, Any]]: ...
    async def offboard(self, account_id: int) -> None: ...  # status flag, never DELETE

    async def display_name_for(self, viewer_account_id: int, subject_account_id: int) -> str:
        """Resolve what `viewer` sees `subject` called.

        MUST filter `display_name_grants` by namer = viewer only, never join across other
        namers' grants (non-propagation rule). Falls back to `self_display_name`, then to the
        composed fallback built from account id + hostname + department name.
        """


class SessionsRepo(_Repo):
    async def active_for_pc(self, pc_id: int) -> dict[str, Any] | None: ...

    async def open(self, pc_id: int, occupant_account_id: int, occupied_via: str,
                   deadline_at: Any, un_evictable: bool) -> int:
        """INSERT; the partial unique index `one_active_session_per_pc` raises on an occupied PC
        and the caller translates that into block-or-end-first vs. hard refusal."""

    async def end(self, session_id: int, reason: str) -> None: ...
    async def extend(self, session_id: int, new_deadline: Any) -> None: ...
    async def list_expired(self) -> list[dict[str, Any]]: ...


# --- Global File Index (schema 3) ---------------------------------------------------------------

class FileIndexRepo(_Repo):
    async def upsert(self, pc_id: int, path: str, name: str, content_hash: str | None,
                     access_tag: str | None) -> None: ...
    async def search(self, query: str, *, allowed_tags: list[str]) -> list[dict[str, Any]]: ...
    async def by_name(self, name: str) -> list[dict[str, Any]]: ...
    async def by_hash(self, content_hash: str) -> list[dict[str, Any]]: ...


# --- Task (schema 4) ----------------------------------------------------------------------------

class TasksRepo(_Repo):
    async def create(self, task: dict[str, Any], items: list[dict[str, Any]]) -> int: ...
    async def get(self, task_id: int) -> dict[str, Any] | None: ...
    async def list_for(self, account_id: int) -> list[dict[str, Any]]: ...
    async def set_status(self, task_id: int, status: str) -> None: ...
    async def record_manual_verification(self, task_id: int, verifier_account_id: int,
                                         outcome: str) -> None: ...


# --- Flow (schema 5) ----------------------------------------------------------------------------

class FlowsRepo(_Repo):
    async def create(self, flow: dict[str, Any], destinations: list[dict[str, Any]],
                     stages: list[dict[str, Any]]) -> int: ...
    async def get(self, flow_id: int) -> dict[str, Any] | None: ...
    async def sources_for_pc(self, pc_id: int) -> list[dict[str, Any]]: ...
    async def graph_edges(self) -> list[tuple[str, str]]: ...  # for cycle prevention
    async def set_status(self, flow_id: int, status: str, branch_id: int | None = None) -> None: ...
    async def log_sync(self, entry: dict[str, Any]) -> None: ...


# --- Reports & Routing (schema 8) ---------------------------------------------------------------

class ReportsRepo(_Repo):
    async def write(self, category: str, source_table: str, source_id: int,
                    department_id: int | None, summary: str) -> int:
        """Written once; Super User always sees it; additionally visible to a department Admin
        when `report_routing_config` routes this category. `report_addressed_views` is a
        separate table and must never be written here."""

    async def visible_to(self, account_id: int) -> list[dict[str, Any]]: ...
    async def routing_config(self) -> dict[str, list[int]]: ...
    async def mark_addressed(self, report_id: int, super_user_id: int, note: str) -> None: ...


# --- Assistance (schema 7) ----------------------------------------------------------------------

class AssistanceRepo(_Repo):
    async def ping(self, from_account_id: int, to_account_id: int) -> int: ...
    async def unaddressed_ping_count(self, account_id: int) -> int: ...
    async def open_channel(self, ping_id: int) -> int: ...
    async def post_message(self, channel_id: int, author_account_id: int, body: str) -> int: ...
    async def close_channel(self, channel_id: int, superior_account_id: int) -> None: ...
    async def add_listener(self, channel_id: int, added_by: int, admin_account_id: int) -> int: ...

    async def listeners_added_by(self, channel_id: int, account_id: int) -> list[dict[str, Any]]:
        """Scoped to the requesting party's own additions only -- never a join across both."""


# --- Control, Events, Monitoring, Actions (schema 9) --------------------------------------------

class ControlRepo(_Repo):
    async def event_definitions(self, *, kind: str | None = None) -> list[dict[str, Any]]: ...
    async def actions_for_event(self, event_id: int) -> list[dict[str, Any]]: ...
    async def start_execution(self, action_id: int, event_id: int | None, pc_id: int) -> int: ...
    async def finish_execution(self, execution_id: int, status: str, output_ref: str | None) -> None: ...
    async def live_executions(self) -> list[dict[str, Any]]: ...  # Dashboard operational view


# --- Audit Trail (schema 10) --------------------------------------------------------------------

class AuditRepo(_Repo):
    async def write(self, entry: dict[str, Any]) -> None: ...
    async def write_deviation(self, entry: dict[str, Any]) -> None: ...

    async def purge_older_than(self, days: int) -> int:
        """The ONE hard delete in the system: flat 90-day retention (v1)."""


# --- Update & Deployment (schema 11) ------------------------------------------------------------

class UpdatesRepo(_Repo):
    async def current_version(self) -> str | None: ...
    async def all_pcs_on(self, version: str) -> bool: ...  # hard gate for approving N+1
    async def set_pc_status(self, pc_id: int, version: str, status: str) -> None: ...
    async def rollout_health_by_department(self) -> list[dict[str, Any]]: ...
