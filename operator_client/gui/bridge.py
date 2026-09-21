"""FalconBridge -- the single object QML talks to.

    falcon.connectTo(host, port, clientId, plaintext)      -> connected / connectionFailed(message)
    falcon.call("hierarchy.tree", {}, function(ok, result) { ... })
    falcon.pushReceived.connect(function(type, payload) { ... })

State properties mirror `ClientState` and change with pushes, so the status bar and views bind
to them directly. Errors from the Engine come back to the callback as ok=false with
result = {code, message}; they are rendered, never thrown into QML.
"""

from __future__ import annotations

import asyncio
import json
import logging
import socket
from typing import Any

from PySide6.QtCore import Property, QObject, Signal, Slot
from PySide6.QtQml import QJSValue

from common.connection import ConnectionError_, EngineConnection, EngineError
from operator_client.core.config import LocalConfig
from operator_client.core.deadlines import resolve_phrase
from operator_client.core.state import ClientState
from operator_client.tui.push_format import describe_push

log = logging.getLogger(__name__)


class FalconBridge(QObject):
    stateChanged = Signal()
    pushReceived = Signal(str, "QVariant")
    pushText = Signal(str, bool)            # (line, is_alert) for the live feed
    connected = Signal()
    connectionFailed = Signal(str)
    disconnected = Signal()

    def __init__(self, config: LocalConfig, parent: QObject | None = None) -> None:
        super().__init__(parent)
        self.config = config
        self.state = ClientState()
        self.state.subscribe(self.stateChanged.emit)
        self.conn: EngineConnection | None = None
        self.js_engine: Any = None          # the QQmlEngine, set by app.create(); converts results for callbacks
        self.hostname = socket.gethostname()

    # --- properties (read by QML bindings) -----------------------------------------------------

    @Property(bool, notify=stateChanged)
    def isConnected(self) -> bool:
        return self.state.connected

    @Property(str, notify=stateChanged)
    def role(self) -> str:
        return self.state.role or ""

    @Property(str, notify=stateChanged)
    def roleLabel(self) -> str:
        return self.state.role_label if self.state.connected else "not connected"

    @Property(int, notify=stateChanged)
    def accountId(self) -> int:
        return self.state.account_id or 0

    @Property(int, notify=stateChanged)
    def pcId(self) -> int:
        return self.state.pc_id or 0

    @Property(int, notify=stateChanged)
    def departmentId(self) -> int:
        return self.state.department_id or 0

    @Property(str, notify=stateChanged)
    def engineAddress(self) -> str:
        return self.state.engine or self.config.engine_address

    @Property("QVariant", notify=stateChanged)
    def session(self) -> Any:
        return self.state.session or {}

    @Property(str, notify=stateChanged)
    def sessionText(self) -> str:
        s = self.state.session
        if not s:
            return "no session"
        if s.get("occupied_via") == "native":
            return "native session on your PC"
        until = f" until {str(s.get('deadline_at', ''))[11:16]}" if s.get("deadline_at") else ""
        return f"{str(s.get('occupied_via', '')).upper()} into pc {s.get('pc_id')}{until}"

    @Property(bool, notify=stateChanged)
    def superUserBanner(self) -> bool:
        return self.state.super_user_banner

    @Property(bool, notify=stateChanged)
    def traversing(self) -> bool:
        return self.state.traversing

    @Property(bool, notify=stateChanged)
    def blocked(self) -> bool:
        return self.state.blocked_by is not None

    @Property(str, notify=stateChanged)
    def blockedBy(self) -> str:
        b = self.state.blocked_by
        return str(b.get("occupant_name") or "") if b else ""

    @Property("QVariant", notify=stateChanged)
    def indicators(self) -> Any:
        return [{"kind": i.kind, "text": i.text, "key": i.key or ""} for i in self.state.indicators]

    @Property(int, notify=stateChanged)
    def unaddressedPings(self) -> int:
        return self.state.unaddressed_pings

    @Property(str, constant=True)
    def defaultHost(self) -> str:
        return self.config.engine_host

    @Property(int, constant=True)
    def defaultPort(self) -> int:
        return self.config.engine_port

    @Property(str, constant=True)
    def defaultClientId(self) -> str:
        return self.config.client_id

    @Property(bool, constant=True)
    def defaultPlaintext(self) -> bool:
        return not self.config.tls

    # --- connection -----------------------------------------------------------------------------

    @Slot(str, int, str, bool)
    def connectTo(self, host: str, port: int, client_id: str, plaintext: bool) -> None:
        asyncio.ensure_future(self._connect(host, port, client_id, plaintext))

    async def _connect(self, host: str, port: int, client_id: str, plaintext: bool) -> None:
        cfg = self.config
        cfg.engine_host, cfg.engine_port, cfg.client_id, cfg.tls = host or cfg.engine_host, int(port), client_id, not plaintext
        if self.conn is not None:
            await self.conn.close()
        conn = EngineConnection(cfg.engine_host, cfg.engine_port, client_id=cfg.client_id, tls=cfg.tls,
                                ca_cert=cfg.ca_cert, hostname=self.hostname)
        conn.on_push(self.state.on_push)
        conn.on_push(self._on_push)
        conn.on_disconnect = self._on_disconnect
        try:
            ident = await conn.connect()
        except (OSError, ConnectionError_, EngineError, asyncio.TimeoutError) as exc:
            await conn.close()
            self.connectionFailed.emit(str(exc))
            return
        self.conn = conn
        self.state.set_identity(ident, cfg.engine_address)
        self.state.clear_indicator("conn")
        cfg.save()
        try:
            st = await conn.call("hierarchy.session_state")
            self.state.set_session(st.get("my_session"))
            if st.get("blocked"):
                self.state.blocked_by = st.get("pc_session")
            ps = await conn.call("assistance.ping_status")
            await self.state.on_push("assistance.ping_status", {"unaddressed": ps.get("unaddressed", 0)})
        except (EngineError, ConnectionError_) as exc:
            log.warning("post-connect state failed: %s", exc)
        self.stateChanged.emit()
        self.connected.emit()

    async def _on_disconnect(self) -> None:
        self.state.connected = False
        self.state.session = None
        self.state.add_indicator("session", "connection to Engine lost", key="conn")
        self.disconnected.emit()

    @Slot()
    def disconnect(self) -> None:
        asyncio.ensure_future(self._disconnect())

    async def _disconnect(self) -> None:
        if self.conn is not None:
            await self.conn.close()
            self.conn = None
        self.state.connected = False
        self.state.session = None
        self.stateChanged.emit()
        self.disconnected.emit()

    async def _on_push(self, type_: str, payload: dict[str, Any]) -> None:
        self.pushReceived.emit(type_, payload)
        text, alert = describe_push(type_, payload)
        if text:
            self.pushText.emit(text, alert)

    # --- generic request ------------------------------------------------------------------------

    @Slot(str, "QVariant", QJSValue)
    def call(self, type_: str, payload: Any, callback: QJSValue) -> None:
        """QML: falcon.call("task.list", {include_completed: true}, function(ok, result) {...})"""
        data = _to_python(payload)
        asyncio.ensure_future(self._call(type_, data, callback))

    async def _call(self, type_: str, payload: dict[str, Any], callback: QJSValue) -> None:
        ok, result = await self.request(type_, payload)
        if callback.isCallable():
            callback.call([QJSValue(ok), _to_js(self.js_engine, result)])

    async def request(self, type_: str, payload: dict[str, Any] | None = None) -> tuple[bool, Any]:
        """Python-side entry (tests, helpers): (ok, result | {code, message})."""
        if self.conn is None or not self.conn.connected:
            return False, {"code": "connection", "message": "not connected"}
        try:
            result = await self.conn.call(type_, payload or {})
        except EngineError as exc:
            return False, {"code": exc.code, "message": exc.message}
        except ConnectionError_ as exc:
            return False, {"code": "connection", "message": str(exc)}
        if type_ == "hierarchy.traverse":
            self.state.set_session(result.get("session"))
        elif type_ == "hierarchy.end_session" and self.state.session:
            if (payload or {}).get("session_id") == self.state.session.get("session_id"):
                self.state.set_session(None)
        elif type_ == "hierarchy.extend_session" and self.state.session:
            self.state.session["deadline_at"] = result.get("deadline_at")
            self.state.set_session(self.state.session)
        elif type_ == "hierarchy.claim_native":
            self.state.blocked_by = None
            self.state.clear_indicator("blocked")
            self.stateChanged.emit()
        return True, result

    # --- small helpers QML needs --------------------------------------------------------------

    @Slot(str, result=str)
    def resolveDeadline(self, phrase: str) -> str:
        """A deadline phrase -> ISO timestamp, or "" when it cannot be resolved mechanically."""
        dt = resolve_phrase(phrase)
        return dt.isoformat() if dt else ""

    @Slot(str, result=str)
    def readFile(self, path: str) -> str:
        try:
            return open(path, encoding="utf-8").read()
        except OSError as exc:
            return f"__error__:{exc}"

    @Slot(str, str, result="QVariant")
    def validateScript(self, language: str, source: str) -> Any:
        from common.custom_actions import validate

        r = validate(language, source)
        return {"ok": r.ok, "problems": r.problems}

    @Slot("QVariant", result=str)
    def pretty(self, value: Any) -> str:
        return json.dumps(_to_python(value), indent=2, default=str)


def _to_python(value: Any) -> Any:
    if isinstance(value, QJSValue):
        value = value.toVariant()
    if isinstance(value, dict):
        return {str(k): _to_python(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_to_python(v) for v in value]
    return value


def _to_js(engine: Any, value: Any) -> QJSValue:
    """A Python result -> a JS object/array the callback can index (dicts stay dicts, not QVariantMap wrappers)."""
    if engine is None:
        return QJSValue()
    return engine.toScriptValue(value)
