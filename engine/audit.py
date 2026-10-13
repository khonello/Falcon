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
        self.engine: Any = None      # set by the Engine: lets each entry be pushed live to the consoles that may see it

    async def record(self, ctx: Context | None, action: str, *, target_type: str | None = None,
                     target_id: Any = None, detail: dict[str, Any] | None = None, pc_id: int | None = None) -> None:
        """`pc_id` is the machine the event concerns; when it is not given it is worked out from the entry (a detail
        that names a pc, a pc/session/execution target, or a Worker acting on its own machine)."""
        actor = (ctx.viewed_by or ctx.identity) if ctx else None
        entry = {
            "at": datetime.now(timezone.utc),
            # through a held session the handler sees the Admin; the act is still the Super User's
            "actor_account_id": actor.account_id if actor else None,
            "action": action,
            "target_type": target_type,
            "target_id": None if target_id is None else str(target_id),
            "detail": detail or {},
        }
        log.info("AUDIT %s actor=%s target=%s:%s", action, entry["actor_account_id"],
                 target_type, entry["target_id"])
        if self.db.connected:
            entry["pc_id"] = pc_id if pc_id is not None else await self._machine_of(entry, actor)
            if entry["pc_id"] is not None and (entry["pc_id"] <= 0 or await self.db.accounts.pc(entry["pc_id"]) is None):
                entry["pc_id"] = None                    # a time event names pc 0, a stale id names nothing: no machine
            entry["department_id"] = await self._department_of(entry, actor)
            entry["id"] = await self.db.audit.write(entry)
            await self._push(entry)

    async def _machine_of(self, entry: dict[str, Any], actor: Any) -> int | None:
        detail, ttype, tid = entry["detail"], entry["target_type"], entry["target_id"]
        try:
            if isinstance(detail.get("pc_id"), int):
                return detail["pc_id"]
            if tid is not None and ttype == "pcs":
                return int(tid)
            if tid is not None and ttype in ("sessions", "session"):
                s = await self.db.sessions.by_id(int(tid))
                return s["pc_id"] if s else None
            if tid is not None and ttype in ("action_executions", "execution"):
                e = await self.db.control.execution(int(tid))
                return e["target_pc_id"] if e else None
            if tid is not None and ttype == "file_index":
                f = await self.db.file_index.get(int(tid))
                return f["pc_id"] if f else None
            if tid is not None and ttype == "flow_destinations":
                d = await self.db.flows.destination(int(tid))
                return d["destination_pc_id"] if d else None
        except (ValueError, TypeError):
            return None
        if actor is not None and actor.role == "worker":
            return actor.pc_id                          # a Worker acts on its own machine
        return None

    async def _department_of(self, entry: dict[str, Any], actor: Any) -> int | None:
        if entry.get("pc_id") is not None:
            pc = await self.db.accounts.pc(entry["pc_id"])
            if pc and pc["department_id"] is not None:
                return pc["department_id"]
        if entry["detail"].get("department_id") is not None and isinstance(entry["detail"]["department_id"], int):
            return entry["detail"]["department_id"]
        if entry["target_type"] == "departments" and entry["target_id"] is not None:
            return int(entry["target_id"])
        return actor.department_id if actor is not None and actor.role != "super_user" else None

    async def _push(self, entry: dict[str, Any]) -> None:
        """Every event the Engine records goes to the Super User and to the Admins of the department it concerns, as it
        happens (the console's live activity). Sentence and kind are worked out here, as the log's own reader does."""
        eng = self.engine
        if eng is None or not eng.connections:
            return
        from engine.console.feed import describe_many

        dept = entry.get("department_id")
        row = {**entry, "action_type": entry["action"]}
        for conn in list(eng.connections):
            ident = conn.ctx.identity
            if not conn.authenticated or ident.role not in ("super_user", "admin"):
                continue
            if ident.role == "admin" and (dept is None or ident.department_id != dept):
                continue
            # named the way this viewer names people (Display Names never propagate between namers)
            event = (await describe_many(eng.db, [row], ident.account_id))[0]
            await conn.push("audit.event", event)

    async def deviation(self, kind: str, *, surfaced_to_account_id: int,
                        observed_account_id: int | None = None, observed_pc_id: int | None = None,
                        detail: dict[str, Any] | None = None) -> int | None:
        """System Expectations & Deviation Handling: logged, surfaced to someone, never
        auto-corrected. `surfaced_to_account_id` is mandatory -- never silently tolerated."""
        log.warning("DEVIATION %s %s", kind, detail)
        if not self.db.connected:
            return None
        deviation_id = await self.db.audit.write_deviation({
            "at": datetime.now(timezone.utc), "kind": kind, "detail": detail or {},
            "surfaced_to_account_id": surfaced_to_account_id,
            "observed_account_id": observed_account_id, "observed_pc_id": observed_pc_id,
        })
        await self.record(None, "deviation.logged", target_type="deviation_log", target_id=deviation_id,
                          detail={"kind": kind, **(detail or {})}, pc_id=observed_pc_id)
        return deviation_id

    async def run_retention(self) -> int:
        """The daily purge: audit entries, the file-event history and what runs returned, all older than the retention window. Says what it did and whether it
        worked; a failure in one part is logged and does not stop the others, and never takes the Scheduler down."""
        if not self.db.connected:
            return 0
        days = self.retention_days
        log.info("retention: starting (keeping %d days)", days)
        purged = 0
        for what, job in (("audit entries", self.db.audit.purge_older_than), ("file events", self.db.audit.purge_file_events_older_than),
                          ("run outputs", self.db.control.clear_outputs_older_than)):
            try:
                n = await job(days)
            except Exception:
                log.exception("retention: FAILED to clear %s older than %d days", what, days)
                continue
            log.info("retention: ok, %s %s older than %d days", n, what, days)
            if what == "audit entries":
                purged = n
        return purged
