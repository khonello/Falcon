"""The Engine process: one asyncio event loop multiplexing every connection (spec 3.2).

No per-connection threads. `asyncio.to_thread` is reserved for the two things that cannot
signal readiness: psutil-style process enumeration (Monitoring) and the interruptible idle-time
file sweep (Global File Index) -- both live in their own modules, not here.
"""

from __future__ import annotations

import asyncio
import logging
import ssl
from typing import Any

from engine.audit import AuditTrail
from engine.config import Settings
from engine.connection import Connection
from engine.database import Database
from engine.dispatch import Context, handler, registered_types
from engine.file_index import FileIndex
from engine.llm import LocalLLM
from engine.scheduler import Scheduler

# Importing the combo packages registers their handlers.
import engine.auth  # noqa: F401
import engine.control  # noqa: F401
import engine.flow  # noqa: F401
import engine.hierarchy  # noqa: F401
import engine.resource  # noqa: F401
import engine.task  # noqa: F401
import engine.updates  # noqa: F401

log = logging.getLogger(__name__)


class Engine:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.db = Database(settings.database_url)
        self.audit = AuditTrail(self.db, settings.audit_retention_days)
        self.file_index = FileIndex(self.db)
        self.scheduler = Scheduler(self)
        self.llm = LocalLLM()
        self.connections: set[Connection] = set()
        # Generated once on the Engine host, never transmitted (spec 8.2). SCAFFOLD: None until
        # provisioning tooling exists; `auth.verify` does not read it yet.
        self.master_secret: bytes | None = None
        self._server: asyncio.base_events.Server | None = None

        # Every consumer of file events subscribes to the one index -- no per-combo detection.
        from engine.flow import sync as flow_sync
        from engine.resource import resource as resource_tiers
        from engine.task import expectation

        expectation.install(self)
        flow_sync.install(self)
        resource_tiers.install(self)

    # --- lifecycle ------------------------------------------------------------------------------

    async def start(self) -> None:
        self._announce_dev_flags()
        await self.db.connect()
        await self.db.migrate()
        await self.scheduler.start()
        self._server = await asyncio.start_server(
            self._on_connection, self.settings.host, self.settings.port, ssl=self._ssl_context(),
            limit=4 * 1024 * 1024,
        )
        addrs = ", ".join(str(s.getsockname()) for s in self._server.sockets or [])
        log.info("Engine listening on %s (%d message types)", addrs, len(registered_types()))

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            await self._server.wait_closed()
        await self.scheduler.stop()
        await self.db.close()

    async def run(self) -> None:
        await self.start()
        try:
            assert self._server is not None
            await self._server.serve_forever()
        finally:
            await self.stop()

    @property
    def port(self) -> int:
        assert self._server is not None and self._server.sockets
        return self._server.sockets[0].getsockname()[1]

    # --- connections ----------------------------------------------------------------------------

    async def _on_connection(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        await Connection(self, reader, writer).serve()

    async def on_disconnect(self, conn: Connection) -> None:
        """A dropped connection mid-traversal is NOT special-cased: the Engine-side session
        deadline keeps running and releases the block when it fires (spec 7.1)."""
        if conn.ctx.identity.account_id is not None:
            await self.audit.record(conn.ctx, "auth.disconnected")

    async def broadcast(self, type_: str, payload: dict[str, Any] | None = None, *,
                        predicate: Any = None) -> None:
        for conn in list(self.connections):
            if conn.authenticated and (predicate is None or predicate(conn)):
                await conn.push(type_, payload)

    # --- helpers --------------------------------------------------------------------------------

    def _announce_dev_flags(self) -> None:
        s = self.settings
        if s.dev_bypass_auth:
            log.warning("=" * 72)
            log.warning("  FALCON_DEV_BYPASS_AUTH IS ON -- auth handshake SKIPPED ENTIRELY")
            log.warning("  This Engine is NOT safe on a real network.")
            log.warning("=" * 72)
        if s.dev_plaintext:
            log.warning("=" * 72)
            log.warning("  FALCON_DEV_PLAINTEXT IS ON -- TLS DISABLED, traffic is plaintext")
            log.warning("=" * 72)

    def _ssl_context(self) -> ssl.SSLContext | None:
        """Fails loudly: no cert -> no Engine (spec 8.3). Only DEV_PLAINTEXT opts out."""
        s = self.settings
        if s.dev_plaintext:
            return None
        if not s.tls_cert or not s.tls_key:
            raise SystemExit("TLS certificate/key not configured (FALCON_TLS_CERT / FALCON_TLS_KEY). "
                             "Set FALCON_DEV_PLAINTEXT=1 only for local development.")
        ctx = ssl.create_default_context(ssl.Purpose.CLIENT_AUTH)
        ctx.load_cert_chain(certfile=str(s.tls_cert), keyfile=str(s.tls_key))
        return ctx


# --- system.* handlers (pre-auth allowed) -------------------------------------------------------

@handler("system.ping")
async def system_ping(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    return {"pong": True, "authenticated": ctx.connection.authenticated}


@handler("system.capabilities")
async def system_capabilities(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    return {"message_types": registered_types(), "version": "0.0.1"}
