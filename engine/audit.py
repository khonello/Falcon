"""Audit trail (spec 8.4): one Engine-owned log, one shape -- who, what, when, target --
regardless of which combo generated the entry. Retention: flat 90 days for v1.

Every traversal, Session Block/end, Task verification, Flow sync/conflict/failure, Resource
compliance check, Ping/Message Channel/Listener event, Assisted Access session, and Event/Action
execution goes through `AuditTrail.record`. Combo modules never write `audit_log` directly.

Without a connected database (scaffold runs, protocol tests) entries are logged only.
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from engine.database import Database
    from engine.dispatch import Context

log = logging.getLogger(__name__)


class AuditTrail:
    def __init__(self, db: Database, retention_days: int) -> None:
        self.db = db
        self.retention_days = retention_days

    async def record(self, ctx: Context | None, action: str, *, target_type: str | None = None,
                     target_id: Any = None, detail: dict[str, Any] | None = None) -> None:
        entry = {
            "at": datetime.now(timezone.utc),
            "actor_account_id": ctx.identity.account_id if ctx else None,
            "action": action,
            "target_type": target_type,
            "target_id": None if target_id is None else str(target_id),
            "detail": detail or {},
        }
        log.info("AUDIT %s actor=%s target=%s:%s", action, entry["actor_account_id"],
                 target_type, entry["target_id"])
        if self.db.connected:
            await self.db.audit.write(entry)

    async def deviation(self, kind: str, *, surfaced_to_account_id: int,
                        observed_account_id: int | None = None, observed_pc_id: int | None = None,
                        detail: dict[str, Any] | None = None) -> int | None:
        """System Expectations & Deviation Handling: logged, surfaced to someone, never
        auto-corrected. `surfaced_to_account_id` is mandatory -- never silently tolerated."""
        log.warning("DEVIATION %s %s", kind, detail)
        if not self.db.connected:
            return None
        return await self.db.audit.write_deviation({
            "at": datetime.now(timezone.utc), "kind": kind, "detail": detail or {},
            "surfaced_to_account_id": surfaced_to_account_id,
            "observed_account_id": observed_account_id, "observed_pc_id": observed_pc_id,
        })

    async def run_retention(self) -> int:
        if not self.db.connected:
            return 0
        purged = await self.db.audit.purge_older_than(self.retention_days)
        log.info("audit retention: purged %s entries older than %sd", purged, self.retention_days)
        return purged
