"""WorkerService: the persistent, authenticated connection and the dispatch of every push.

    service = WorkerService(config)
    await service.start()        # connects (retrying), starts watcher/signals, claims native session
    ...
    await service.stop()

Reconnection: on a drop, reconnect with backoff forever. A drop during someone else's
traversal into this PC changes nothing here -- the Engine's session deadline governs, and on
reconnect the handshake tells us whether we are still blocked (spec 7.1).
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Awaitable, Callable
from typing import Any

from common.connection import ConnectionError_, EngineConnection, EngineError
from worker_client.config import WorkerConfig
from worker_client.executor import Executor
from worker_client.flowsync import FlowSync
from worker_client.lockout import Lockout
from worker_client.signals import Signals
from worker_client.updater import Updater
from worker_client.watcher import Watcher

log = logging.getLogger(__name__)

VERSION = "0.0.1"

Notifier = Callable[[str, dict[str, Any]], Awaitable[None]]


class WorkerService:
    def __init__(self, config: WorkerConfig, *, native_watch: bool = True, allow_power: bool = False) -> None:
        self.config = config
        self.conn: EngineConnection | None = None
        self.identity: Any = None
        self.lockout = Lockout(lock_workstation=config.lock_workstation_on_block)
        self.executor = Executor(self.call, allow_power=allow_power)
        self.flowsync = FlowSync(self.call)
        self.signals = Signals(self.call, metrics_seconds=config.metrics_seconds)
        self.updater = Updater(self.call, running_version=VERSION, update_command=config.update_command)
        self.watcher = Watcher(config.watch_roots, self.call, poll_seconds=config.poll_seconds,
                               hash_limit=config.hash_limit_bytes, idle_after=config.idle_sweep_after_seconds,
                               native=native_watch)
        self.notifiers: list[Notifier] = []   # the narrow UI / dialogs subscribe here
        self.native_session_id: int | None = None
        self._stopping = False
        self._reconnect_task: asyncio.Task[None] | None = None
        self.pushes_handled = 0

    # --- lifecycle ------------------------------------------------------------------------------

    async def start(self) -> None:
        await self._connect(forever=True)
        await self.watcher.start()
        await self.signals.start()
        await self._refresh_tasks()
        log.info("worker service up as pc %s (account %s)", self.identity.pc_id, self.identity.account_id)

    async def stop(self) -> None:
        self._stopping = True
        if self._reconnect_task:
            self._reconnect_task.cancel()
        await self.watcher.stop()
        await self.signals.stop()
        await self.updater.stop()
        await self.executor.shutdown()
        if self.conn:
            await self.conn.close()

    def on_notify(self, fn: Notifier) -> None:
        self.notifiers.append(fn)

    async def call(self, type_: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if self.conn is None or not self.conn.connected:
            raise ConnectionError_("not connected")
        return await self.conn.call(type_, payload)

    # --- connection -----------------------------------------------------------------------------

    async def _connect(self, *, forever: bool) -> None:
        delay = 1.0
        while True:
            conn = EngineConnection(self.config.engine_host, self.config.engine_port, client_id=self.config.client_id,
                                    tls=self.config.tls, ca_cert=self.config.ca_cert)
            conn.on_push(self._on_push)
            conn.on_disconnect = self._on_disconnect
            try:
                self.identity = await conn.connect()
                self.conn = conn
                break
            except (OSError, ConnectionError_, EngineError, asyncio.TimeoutError) as exc:
                await conn.close()
                if not forever:
                    raise
                log.warning("engine unreachable (%s); retrying in %.0fs", exc, delay)
                await asyncio.sleep(delay)
                delay = min(delay * 2, 60)
        await self._after_connect()

    async def _after_connect(self) -> None:
        st = await self.call("hierarchy.session_state")
        mine = st.get("my_session")
        self.native_session_id = mine["session_id"] if mine else None
        if st.get("blocked") and st.get("pc_session"):
            self.lockout.block(st["pc_session"])
        else:
            self.lockout.release()
        cur = await self.call("updates.current")
        if cur.get("version") and cur["version"]["version_string"] != VERSION:
            self.updater.on_available({"version": cur["version"]["version_string"]})

    async def _on_disconnect(self) -> None:
        if self._stopping:
            return
        log.warning("connection to the Engine lost; reconnecting")
        self._reconnect_task = asyncio.create_task(self._connect(forever=True))

    # --- pushes ---------------------------------------------------------------------------------

    async def _on_push(self, type_: str, payload: dict[str, Any]) -> None:
        self.pushes_handled += 1
        try:
            if type_ == "session.blocked":
                if payload.get("pc_id") == self.identity.pc_id and payload.get("occupant_account_id") != self.identity.account_id:
                    self.lockout.block(payload)
            elif type_ == "session.released":
                if payload.get("pc_id") == self.identity.pc_id:
                    self.lockout.release()
                    await self._reclaim()
            elif type_ == "session.ended":
                if payload.get("session_id") == self.native_session_id:
                    self.native_session_id = None
            elif type_ == "action.execute":
                await self.executor.execute(payload)
            elif type_ == "action.terminate":
                await self.executor.terminate(int(payload["execution_id"]))
            elif type_ == "flow.read":
                await self.flowsync.on_read(payload)
            elif type_ == "flow.apply":
                await self.flowsync.on_apply(payload)
            elif type_ == "flow.resolve_conflict":
                await self.flowsync.on_resolve_conflict(payload)
            elif type_ == "update.available":
                self.updater.on_available(payload)
            elif type_ in ("task.assigned", "task.completed", "task.incomplete"):
                await self._refresh_tasks()
        except Exception:
            log.exception("push %s failed", type_)
        for fn in list(self.notifiers):
            try:
                await fn(type_, payload)
            except Exception:
                log.exception("notifier failed for %s", type_)

    async def _reclaim(self) -> None:
        try:
            res = await self.call("hierarchy.claim_native")
            self.native_session_id = res.get("session_id")
        except (EngineError, ConnectionError_) as exc:
            log.warning("could not re-claim the native session: %s", exc)

    async def _refresh_tasks(self) -> None:
        try:
            tasks = (await self.call("task.list"))["tasks"]
            detailed = []
            for t in tasks:
                if t.get("verification_mode") == "stack":
                    detailed.append((await self.call("task.get", {"task_id": t["id"]}))["task"])
            await self.signals.refresh_tasks(detailed)
        except (EngineError, ConnectionError_) as exc:
            log.debug("task refresh failed: %s", exc)
