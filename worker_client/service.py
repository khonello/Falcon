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
import contextlib
import logging
import time
from collections.abc import Awaitable, Callable
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

from common.connection import ConnectionError_, EngineConnection, EngineError
from common.signpipe import SignPipeServer
from worker_client import winsession
from worker_client.config import WorkerConfig
from worker_client.executor import Executor
from worker_client.flowsync import FlowSync
from worker_client.inventory import Inventory
from worker_client.isolated import IsolatedSignals, IsolatedWatcher
from worker_client.localapp import LocalApp
from worker_client.lockout import Lockout
from worker_client.ossignals import OsSignals
from worker_client.reminders import TaskReminders
from worker_client.screenstream import RemoteInput, ScreenStreamer
from worker_client.signals import Signals
from worker_client.updater import Updater
from worker_client.userhelper import HelperInput, UserHelper
from worker_client.watcher import Watcher

log = logging.getLogger(__name__)

VERSION = "0.0.1"

Notifier = Callable[[str, dict[str, Any]], Awaitable[None]]



def _iso(text: str) -> datetime:
    """A time from the Engine ("...Z" or with an offset) as an aware datetime."""
    t = datetime.fromisoformat(text.replace("Z", "+00:00"))
    return t if t.tzinfo else t.replace(tzinfo=timezone.utc)


class WorkerService:
    def __init__(self, config: WorkerConfig, *, native_watch: bool = True, allow_power: bool = False) -> None:
        self.config = config
        self.started_at = datetime.now(timezone.utc).isoformat()
        self.conn: EngineConnection | None = None
        self.identity: Any = None
        self.lockout = Lockout(lock_workstation=config.lock_workstation_on_block)
        self.executor = Executor(self.call, allow_power=allow_power, windows=config.windows)
        self.flowsync = FlowSync(self.call)
        self.signals = Signals(self.call, metrics_seconds=config.metrics_seconds)
        self.ossignals: Any = IsolatedSignals(self.call, self._component_changed) if config.separate_programs else OsSignals(self.call)
        # a superior who entered this machine looking at it, and in control mode using it. As a service (session 0, no screen) both are done by a helper on
        # the signed-in person's desktop; otherwise in this process.
        self.helper = UserHelper() if winsession.in_service_session() else None
        self.screens = ScreenStreamer(self.call, acapture=self.helper.capture if self.helper else None)
        self.remote_input: Any = HelperInput(self.helper) if self.helper else RemoteInput()
        self.inventory = Inventory(self.call)
        self._native_watch = native_watch
        self.signpipe: SignPipeServer | None = None
        self.updater = Updater(self.call, running_version=VERSION, update_command=config.update_command)
        state_path = Path(config.path).parent / "index-state.db" if config.index_state else None
        if config.separate_programs:
            self.watcher: Any = IsolatedWatcher(config.watch_roots, self.call, poll_seconds=config.poll_seconds,
                                                hash_limit=config.hash_limit_bytes, idle_after=config.idle_sweep_after_seconds,
                                                native=native_watch, on_unhealthy=self._component_changed,
                                                state_path=state_path, reconcile_seconds=config.reconcile_seconds)
        else:
            self.watcher = Watcher(config.watch_roots, self.call, poll_seconds=config.poll_seconds,
                                   hash_limit=config.hash_limit_bytes, idle_after=config.idle_sweep_after_seconds,
                                   native=native_watch, state_path=state_path, reconcile_seconds=config.reconcile_seconds)
        self.notifiers: list[Notifier] = []   # the narrow UI / dialogs subscribe here
        self.native_session_id: int | None = None
        self._stopping = False
        self._reconnect_task: asyncio.Task[None] | None = None
        self.pushes_handled = 0
        # the Worker's windows (WR01, TK07): the block overlay follows the lockout; a new task opens its window
        self._overlay: Any = None
        self._viewbar: Any = None
        self._program: Any = None
        self.localapp = LocalApp(self, config.path) if config.windows else None
        self._view: dict[str, Any] = {}
        self._view_at = 0.0
        self.toasts: dict[str, dict[str, Any]] = {}              # quiet notes for the program to show; they stay until it says it showed them
        self._dismissed: set[int] = {int(i) for i in config.cache.get("dismissed_alerts", [])}
        self._window_tasks: set[asyncio.Task[None]] = set()
        self.reminders = TaskReminders()                      # tasks waiting to be started, shown again until they are
        self._reminder_task: asyncio.Task[None] | None = None
        if config.windows:
            self.lockout.on_change(self._on_block_changed)
            self.lockout.on_view_change(self._on_view_changed)

    # --- lifecycle ------------------------------------------------------------------------------

    async def start(self) -> None:
        await self._connect(forever=True)
        if self.config.serve_console and self.config.client_key:
            self.signpipe = SignPipeServer(self.config.client_key, client_id=self.config.client_id)
            if not self.signpipe.start():
                log.warning("the console on this machine cannot be signed in: the signing pipe did not start")
        await self.watcher.start()
        await self.signals.start()
        await self.ossignals.start(native=self._native_watch)
        await self.inventory.start()
        await self._refresh_tasks()
        if self.config.windows:
            await self.localapp.start()
            await self._start_program()
            self._reminder_task = asyncio.create_task(self._reminder_loop())
        log.info("worker service up as pc %s (account %s)", self.identity.pc_id, self.identity.account_id)

    async def stop(self) -> None:
        self._stopping = True
        if self._reconnect_task:
            self._reconnect_task.cancel()
        if self.localapp is not None:
            await self.localapp.stop()
        if self._reminder_task:
            self._reminder_task.cancel()
        await self.screens.shutdown()
        self.remote_input.stop()
        if self.helper is not None:
            await self.helper.stop()
        if self.signpipe is not None:
            self.signpipe.stop()
        await self.watcher.stop()
        await self.signals.stop()
        await self.ossignals.stop()
        await self.inventory.stop()
        await self.updater.stop()
        await self.executor.shutdown()
        if self.conn:
            await self.conn.close()

    def hello(self) -> dict[str, Any]:
        """What this machine says about itself when it connects: the Worker's version, the OS, and when the agent started."""
        import platform

        return {"version": VERSION, "os": f"{platform.system()} {platform.release()} {platform.version()}".strip(),
                "started_at": self.started_at}

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
                                    tls=self.config.tls, ca_cert=self.config.ca_cert,
                                    derived_key=self.config.client_key or None, hello=self.hello())
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
        await self.ossignals.refresh()
        self._spawn(self._reconcile_index())          # whatever changed while the Engine was not listening is told now, in the background
        if self.config.windows:
            self._spawn(self._replay_emergencies())
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
        if self.identity is None and type_.startswith("session."):
            return                      # a push that beat the handshake: the held state is read again once connected
        try:
            if type_ == "session.blocked":
                if payload.get("pc_id") == self.identity.pc_id and payload.get("occupant_account_id") != self.identity.account_id:
                    self.lockout.block(payload)
            elif type_ == "session.viewing":
                if payload.get("pc_id") == self.identity.pc_id and payload.get("occupant_account_id") != self.identity.account_id:
                    self.lockout.view(payload)
                    self.remote_input.control(False)
            elif type_ == "session.released":
                if payload.get("pc_id") == self.identity.pc_id:
                    self.screens.stop()
                    self.remote_input.control(False)
                    self.lockout.release()
                    await self._reclaim()
            elif type_ == "screen.start":
                self.screens.start(int(payload["session_id"]), int(payload.get("width") or 1280), int(payload.get("fps") or 2))
                self.remote_input.control(payload.get("mode") == "control")
            elif type_ == "screen.stop":
                self.screens.stop(int(payload["session_id"]))
                self.remote_input.control(False)
            elif type_ == "screen.mode":
                self.remote_input.control(payload.get("mode") == "control" and bool(self.screens.active))
            elif type_ == "screen.input":
                self.remote_input.apply(list(payload.get("events") or []))
            elif type_ == "session.ended":
                if payload.get("session_id") == self.native_session_id:
                    self.native_session_id = None
            elif type_ == "action.execute":
                await self.executor.execute(payload)
            elif type_ == "action.terminate":
                await self.executor.terminate(int(payload["execution_id"]))
            elif type_ == "flow.read":
                await self.flowsync.on_read(payload)
            elif type_ == "flow.list":
                await self.flowsync.on_list(payload)
            elif type_ == "flow.apply":
                await self.flowsync.on_apply(payload)
            elif type_ == "flow.resolve_conflict":
                await self.flowsync.on_resolve_conflict(payload)
            elif type_ == "flow.remove":
                await self.flowsync.on_remove(payload)
            elif type_ == "issue.ask_delete":
                if self.config.windows:
                    self._spawn(self._ask_to_delete(payload))
            elif type_ == "control.interest_changed":
                await self.ossignals.refresh()
            elif type_ == "update.available":
                self.updater.on_available(payload)
            elif type_ == "alert.delivered":
                await self._on_alert(payload)
            elif type_ in ("task.assigned", "task.completed", "task.incomplete"):
                await self._refresh_tasks()
                if type_ == "task.assigned" and self.config.windows:
                    self._spawn(self._show_task(int(payload["task_id"])))
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

    async def _reconcile_index(self) -> None:
        try:
            await self.watcher.reconcile()
        except Exception as exc:  # noqa: BLE001 -- a look that failed is made again at the next connect and on the timer
            log.warning("could not bring the Engine's index up to date: %s", exc)

    def _component_changed(self, name: str, healthy: bool) -> None:
        """The indexer or the tracker started dying again and again, or recovered: the Engine is told, so someone can look."""
        self._spawn(self._tell_component(name, healthy))

    async def _tell_component(self, name: str, healthy: bool) -> None:
        try:
            await self.call("control.component_status", {"component": name, "healthy": healthy})
        except Exception:  # noqa: BLE001 -- not connected right now; the log has it, and the next change tells
            log.warning("could not tell the Engine that %s is %s", name, "healthy" if healthy else "unhealthy")

    # --- the Worker's windows ----------------------------------------------------------------------

    def _spawn(self, coro: Any) -> None:
        t = asyncio.ensure_future(coro)
        self._window_tasks.add(t)
        t.add_done_callback(self._window_tasks.discard)

    def _on_block_changed(self, blocked_by: dict[str, Any] | None) -> None:
        """Someone is using this machine: the overlay says who and until when, and goes when they leave."""
        if self._overlay is not None:
            self._overlay.close()
            self._overlay = None
        if blocked_by is not None:
            self._spawn(self._open_overlay(blocked_by))

    def _on_view_changed(self, viewing_by: dict[str, Any] | None) -> None:
        """Someone is looking at this machine and the person keeps working: a small bar says who, until they leave."""
        if self._viewbar is not None:
            self._viewbar.close()
            self._viewbar = None
        if viewing_by is not None:
            self._spawn(self._open_viewbar(viewing_by))

    async def _open_viewbar(self, viewing_by: dict[str, Any]) -> None:
        from worker_client.windows.spawn import open_window

        handle = await open_window("viewing", {"occupant_name": viewing_by.get("occupant_name")})
        if handle is not None and self.lockout.viewing_by is not None:
            self._viewbar = handle
        elif handle is not None:
            handle.close()

    async def _open_overlay(self, blocked_by: dict[str, Any]) -> None:
        from worker_client.windows.spawn import open_window

        handle = await open_window("blocked", {"occupant_name": blocked_by.get("occupant_name"),
                                               "deadline_at": blocked_by.get("deadline_at")})
        if handle is not None and self.lockout.is_blocked:
            self._overlay = handle
        elif handle is not None:
            handle.close()

    async def _ask_to_delete(self, payload: dict[str, Any]) -> None:
        """An Admin asks this person to delete a restricted copy: which file, where, and why. The issue closes by itself
        when the copy is gone."""
        from worker_client.windows.spawn import open_window

        text = (f"Please delete {payload.get('file')}"
                + (f" from {payload['folder']}" if payload.get("folder") else "") + f". {payload.get('why') or ''}").strip()
        handle = await open_window("message", {"text": text, "from": "your Admin"})
        if handle is not None:
            await handle.answer()

    async def _show_task(self, task_id: int) -> None:
        """A task given to this person: its window, and Start if they choose to (never Complete). Closed without starting, it is reminded about later,
        quietly (see _remind)."""
        from worker_client.windows.spawn import open_window, task_spec

        try:
            task = (await self.call("task.get", {"task_id": task_id}))["task"]
        except (EngineError, ConnectionError_) as exc:
            log.debug("task %s for its window: %s", task_id, exc)
            return
        if task.get("status") != "active" or task.get("started_at") or task.get("assignee_account_id") != self.identity.account_id:
            self.reminders.clear(task_id)                      # not waiting to be started any more (or never theirs)
            return
        handle = await open_window("task", task_spec(task))
        answer = await handle.answer() if handle is not None else None
        if answer and answer.get("start"):
            await self._start_task(task_id)
        else:
            self.reminders.track(task_id)                      # not now: it is not forgotten

    async def _start_task(self, task_id: int) -> None:
        try:
            await self.call("task.start", {"task_id": task_id})
            self.reminders.clear(task_id)
        except (EngineError, ConnectionError_) as exc:
            log.warning("starting task %s failed: %s", task_id, exc)
            self.reminders.track(task_id, in_minutes=5)

    async def _reminder_loop(self) -> None:
        """Every half minute: if a task has waited long enough for its next reminder, and nobody is using this machine, show it (one at a time)."""
        while not self._stopping:
            await asyncio.sleep(30)
            try:
                if self.lockout.blocked_by is not None or self.conn is None or not self.conn.connected:
                    continue
                for task_id in self.reminders.due()[:1]:
                    await self._remind(task_id)
            except asyncio.CancelledError:
                raise
            except Exception:
                log.exception("a task reminder failed")

    # --- the small Falcon program on this machine (worker_client/program) ------------------------------------------------------------

    async def _start_program(self) -> None:
        """The person's own program: tray icon, and a window with their tasks, announcements and help. One copy per person; a second start only
        brings the first to the front, so it is safe to ask for it whenever the service starts."""
        from worker_client.windows.spawn import open_program

        self._program = await open_program()

    async def _build_view(self) -> None:
        try:
            tasks = (await self.call("task.list"))["tasks"]
            alerts = (await self.call("alerts.list"))["alerts"]
            admins = (await self.call("assistance.my_admins"))["admins"]
        except (EngineError, ConnectionError_) as exc:
            log.debug("the program's view could not be refreshed: %s", exc)
            return
        mine = [t for t in tasks if t.get("assignee_account_id") == self.identity.account_id and t.get("status") in (None, "active")]
        rows = []
        for t in mine:
            text = str(t.get("description_raw") or "")
            rows.append({"id": t["id"], "title": text.split(".")[0].strip()[:90] or "A task", "description": text, "from": t.get("assigner_name") or "your Admin",
                         "due": t.get("final_deadline_at"), "started": bool(t.get("started_at"))})
        rows.sort(key=lambda r: (r["due"] is None, r["due"] or ""))
        notes = [{"id": a["id"], "kind": a["alert_type"], "title": a.get("title") or "", "body": a.get("body") or "", "from": a.get("from_name") or "",
                  "at": a.get("deliver_at")} for a in alerts]
        self._view = {"tasks": rows, "announcements": notes, "admins": admins, "as_of": datetime.now(timezone.utc).isoformat(), "version": VERSION}
        self._view_at = time.monotonic()

    async def app_view(self) -> dict[str, Any]:
        """What is relevant to this person, now: fresh when the Engine can be reached, what was last known (and said so) when it cannot."""
        online = self.conn is not None and self.conn.connected
        if online and time.monotonic() - self._view_at > 3:
            await self._build_view()
        held = self.lockout.blocked_by
        return {**self._view, "connected": online, "held_by": (held or {}).get("occupant_name") or ("an Admin" if held else None),
                "toasts": list(self.toasts.values())}

    async def app_start_task(self, task_id: int) -> None:
        await self._start_task(task_id)
        self._view_at = 0.0

    async def app_ask(self, to_account_id: int) -> None:
        await self.call("assistance.ping", {"to_account_id": to_account_id})

    async def app_ack(self, ids: list[str]) -> None:
        for i in ids:
            self.toasts.pop(i, None)

    async def _remind(self, task_id: int) -> None:
        """A quiet nudge for a task nobody started: a small note in the corner (the program shows it), never a window over their work."""
        try:
            task = (await self.call("task.get", {"task_id": task_id}))["task"]
        except (EngineError, ConnectionError_):
            self.reminders.postpone(task_id, 5)
            return
        if task.get("status") != "active" or task.get("started_at") or task.get("assignee_account_id") != self.identity.account_id:
            self.reminders.clear(task_id)
            return
        text = str(task.get("description_raw") or "").split(".")[0].strip()[:90] or "A task"
        self.toasts[f"t{task_id}"] = {"id": f"t{task_id}", "kind": "task", "title": text, "text": "Still waiting to be started"}
        self.reminders.track(task_id)

    async def _on_alert(self, payload: dict[str, Any]) -> None:
        self._view_at = 0.0
        if payload.get("alert_type") == "emergency":
            if self.config.windows:
                self._spawn(self._show_emergency(payload))
        elif payload.get("alert_type") != "routine":
            body = str(payload.get("body") or "")
            self.toasts[f"a{payload['id']}"] = {"id": f"a{payload['id']}", "kind": "announcement", "title": payload.get("title") or "New announcement",
                                                "text": body[:110]}

    async def _show_emergency(self, alert: dict[str, Any]) -> None:
        """An emergency covers the screen until the person says they have read it; it is also in the program's list."""
        from worker_client.windows.spawn import open_window

        alert_id = int(alert["id"])
        if alert_id in self._dismissed:
            return
        sender = ""
        try:
            sender = next((a.get("from_name") or "" for a in (await self.call("alerts.list"))["alerts"] if a["id"] == alert_id), "")
        except (EngineError, ConnectionError_):
            pass
        handle = await open_window("emergency", {"title": alert.get("title") or "An emergency announcement", "text": alert.get("body") or "", "from": sender})
        answer = await handle.answer() if handle is not None else None
        if answer and answer.get("seen"):
            self._dismissed.add(alert_id)
            self.config.cache["dismissed_alerts"] = sorted(self._dismissed)[-200:]
            with contextlib.suppress(OSError):
                self.config.save()

    async def _replay_emergencies(self) -> None:
        """An emergency delivered while this machine was off or away, and not yet dismissed here, is shown now (for a day after it was sent)."""
        try:
            alerts = (await self.call("alerts.list"))["alerts"]
        except (EngineError, ConnectionError_):
            return
        cutoff = datetime.now(timezone.utc) - timedelta(hours=24)
        for a in alerts:
            if a["alert_type"] == "emergency" and a["id"] not in self._dismissed and a.get("deliver_at") and _iso(str(a["deliver_at"])) >= cutoff:
                await self._show_emergency(a)

    async def ask_for_help(self) -> None:
        """The person chose to ask for help: say who they can ask, let them pick, send the ping. A ping carries
        no message -- whoever they ask sees it, answers, and writes first."""
        from worker_client.windows.spawn import open_window

        try:
            admins = (await self.call("assistance.my_admins"))["admins"]
            if not admins:
                handle = await open_window("message", {"text": "There is no Admin to ask yet.", "from": ""})
                if handle is not None:
                    await handle.answer()
                return
            handle = await open_window("ask", {"admins": admins})
            answer = await handle.answer() if handle is not None else None
            if not answer or answer.get("to") is None:
                return
            await self.call("assistance.ping", {"to_account_id": int(answer["to"])})
            name = next((a["name"] for a in admins if a["account_id"] == int(answer["to"])), "your Admin")
            done = await open_window("message", {"text": f"Asked {name}. They will write to you when they can.", "from": ""})
            if done is not None:
                await done.answer()
        except (EngineError, ConnectionError_) as exc:
            log.warning("asking for help failed: %s", exc)

    async def _refresh_tasks(self) -> None:
        try:
            tasks = (await self.call("task.list"))["tasks"]
            detailed = []
            for t in tasks:
                if t.get("verification_mode") == "stack":
                    detailed.append((await self.call("task.get", {"task_id": t["id"]}))["task"])
            await self.signals.refresh_tasks(detailed)
            waiting = {t["id"] for t in tasks if t.get("assignee_account_id") == self.identity.account_id
                       and t.get("status") == "active" and not t.get("started_at")}
            self.reminders.keep_only(waiting)
            for task_id in waiting:
                self.reminders.track_new(task_id)
        except (EngineError, ConnectionError_) as exc:
            log.debug("task refresh failed: %s", exc)
