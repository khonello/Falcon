"""Engine connection for clients (Operator Client; the Worker Client reuses the same shape).

    conn = EngineConnection("engine-host", 7400, client_id="...", tls=True)
    conn.on_push(callback)              # async callback(type, payload)
    await conn.connect()                # TCP/TLS + auth handshake -> Identity in conn.identity
    result = await conn.call("hierarchy.tree")
    await conn.close()

Auth handshake (spec 8.2): the Engine pushes `auth.challenge {nonce}`; we answer `auth.respond`
with our client_id, hostname and HMAC(derived_key, nonce). Until Phase 5 the Engine's check is
a stub and there is no derived key yet, so the HMAC field is sent as "stub" -- the *shape* is
final, the secret is not.

TLS (spec 8.3): certificate pinning against the provisioned Engine certificate; hostname
identity. `tls=False` is development only and mirrors the Engine's FALCON_DEV_PLAINTEXT.
"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import logging
import socket
import ssl
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from protocol import Envelope, Kind, ProtocolError, decode, encode, request

log = logging.getLogger(__name__)

PushHandler = Callable[[str, dict[str, Any]], Awaitable[None]]


class EngineError(Exception):
    """A typed error response from the Engine."""

    def __init__(self, code: str, message: str, request_type: str) -> None:
        super().__init__(f"{request_type}: {code}: {message}")
        self.code = code
        self.message = message
        self.request_type = request_type


class ConnectionError_(Exception):
    """Not connected / connection lost."""


@dataclass
class Identity:
    client_id: str
    account_id: int | None = None
    role: str | None = None
    pc_id: int | None = None
    department_id: int | None = None


class EngineConnection:
    def __init__(self, host: str, port: int, *, client_id: str, tls: bool = True,
                 ca_cert: str | Path | None = None, derived_key: bytes | str | None = None,
                 hostname: str | None = None, request_timeout: float = 30.0) -> None:
        self.host = host
        self.port = port
        self.client_id = client_id
        self.tls = tls
        self.ca_cert = Path(ca_cert) if ca_cert else None
        # The provisioned client key (hex from the install package, or raw bytes).
        self.derived_key = bytes.fromhex(derived_key) if isinstance(derived_key, str) and derived_key else (derived_key or None)
        self.hostname = hostname or socket.gethostname()
        self.request_timeout = request_timeout
        self.identity: Identity | None = None
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._pending: dict[str, asyncio.Future[Envelope]] = {}
        self._push_handlers: list[PushHandler] = []
        self._reader_task: asyncio.Task[None] | None = None
        self._push_task: asyncio.Task[None] | None = None
        self._push_queue: asyncio.Queue[tuple[str, dict[str, Any]] | None] | None = None
        self._challenge: asyncio.Future[str] | None = None
        self._closed = True
        self.on_disconnect: Callable[[], Awaitable[None]] | None = None

    # --- public ---------------------------------------------------------------------------------

    @property
    def connected(self) -> bool:
        return not self._closed and self._writer is not None

    def on_push(self, handler: PushHandler) -> None:
        self._push_handlers.append(handler)

    async def connect(self) -> Identity:
        ssl_ctx = self._ssl_context()
        self._reader, self._writer = await asyncio.open_connection(
            self.host, self.port, ssl=ssl_ctx, server_hostname=self.host if ssl_ctx else None)
        self._closed = False
        loop = asyncio.get_running_loop()
        self._challenge = loop.create_future()
        self._push_queue = asyncio.Queue()
        self._push_task = asyncio.create_task(self._push_loop())
        self._reader_task = asyncio.create_task(self._read_loop())
        try:
            nonce = await asyncio.wait_for(self._challenge, self.request_timeout)
        except asyncio.TimeoutError:
            # The Engine may run with DEV_BYPASS_AUTH and send no challenge at all.
            nonce = ""
        answer = self._answer(nonce)
        result = await self.call("auth.respond", {"client_id": self.client_id, "hmac": answer,
                                                  "hostname": self.hostname})
        self.identity = Identity(client_id=self.client_id, account_id=result.get("account_id"),
                                 role=result.get("role"), pc_id=result.get("pc_id"),
                                 department_id=result.get("department_id"))
        return self.identity

    async def call(self, type_: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
        if not self.connected or self._writer is None:
            raise ConnectionError_("not connected")
        env = request(type_, payload)
        fut: asyncio.Future[Envelope] = asyncio.get_running_loop().create_future()
        assert env.id is not None
        self._pending[env.id] = fut
        try:
            self._writer.write(encode(env))
            await self._writer.drain()
            resp = await asyncio.wait_for(fut, self.request_timeout)
        except asyncio.TimeoutError as exc:
            self._pending.pop(env.id, None)
            raise ConnectionError_(f"{type_}: no response within {self.request_timeout:.0f}s") from exc
        except (ConnectionError, OSError) as exc:
            self._pending.pop(env.id, None)
            raise ConnectionError_(f"{type_}: {exc}") from exc
        if resp.ok:
            return resp.result or {}
        err = resp.error or {}
        raise EngineError(str(err.get("code", "internal")), str(err.get("message", "")), type_)

    async def close(self) -> None:
        self._closed = True
        log.debug("close: cancelling tasks")
        # Stop the reader BEFORE closing the transport: on Windows' Proactor loop, closing a
        # StreamWriter while a readuntil() is pending can leave wait_closed() waiting forever.
        for task in (self._reader_task, self._push_task):
            if task is None:
                continue
            if log.isEnabledFor(logging.DEBUG):
                frames = task.get_stack(limit=6)
                log.debug("close: task %s at %s", task.get_name(),
                          " <- ".join(f"{f.f_code.co_name}:{f.f_lineno}" for f in reversed(frames)))
            task.cancel()
            try:
                await asyncio.wait_for(task, 5)
            except asyncio.CancelledError:
                pass  # expected: we cancelled it
            except asyncio.TimeoutError:
                log.warning("connection task %s did not stop within 5s; abandoning it", task.get_name())
            except Exception as exc:  # noqa: BLE001
                log.debug("connection task ended with %s", exc)
        self._push_task = None
        self._reader_task = None
        log.debug("close: closing transport")
        if self._writer is not None:
            self._writer.close()
            try:
                await asyncio.wait_for(self._writer.wait_closed(), 3)
            except (ConnectionError, OSError, asyncio.TimeoutError):
                pass
        log.debug("close: done")
        self._writer = None
        self._reader = None

    # --- internals ------------------------------------------------------------------------------

    def _ssl_context(self) -> ssl.SSLContext | None:
        if not self.tls:
            return None
        ctx = ssl.create_default_context()
        if self.ca_cert:
            # Pinned, self-signed Engine certificate: trust exactly this one.
            ctx.load_verify_locations(cafile=str(self.ca_cert))
        return ctx

    def _answer(self, nonce: str) -> str:
        """HMAC(derived_key, nonce). Without a key or a nonce (Engine in DEV_BYPASS_AUTH) the field is
        still present so the message shape never changes; a real Engine rejects it."""
        if self.derived_key is None or not nonce:
            return ""
        return hmac.new(self.derived_key, nonce.encode("utf-8"), hashlib.sha256).hexdigest()

    async def _read_loop(self) -> None:
        assert self._reader is not None
        try:
            while not self._closed:
                try:
                    line = await self._reader.readuntil(b"\n")
                except (asyncio.IncompleteReadError, ConnectionError, OSError):
                    break
                try:
                    env = decode(line)
                except ProtocolError as exc:
                    log.warning("bad message from Engine: %s", exc)
                    continue
                if env.kind is Kind.RESPONSE and env.id in self._pending:
                    self._pending.pop(env.id).set_result(env)
                elif env.kind is Kind.PUSH and env.type:
                    if env.type == "auth.challenge" and self._challenge and not self._challenge.done():
                        self._challenge.set_result(str(env.payload.get("nonce", "")))
                        continue
                    # Never handle pushes inline: a handler that awaits a request would block
                    # the very loop that has to read the response. Queue them; one consumer
                    # keeps push order.
                    if self._push_queue is not None:
                        self._push_queue.put_nowait((env.type, env.payload))
        finally:
            was_open = not self._closed
            self._closed = True
            for fut in self._pending.values():
                if not fut.done():
                    fut.set_exception(ConnectionError_("connection closed"))
            self._pending.clear()
            if was_open and self.on_disconnect is not None:
                await self.on_disconnect()


    async def _push_loop(self) -> None:
        assert self._push_queue is not None
        while True:
            item = await self._push_queue.get()
            if item is None:
                return
            type_, payload = item
            for handler in list(self._push_handlers):
                try:
                    await handler(type_, payload)
                except Exception:
                    log.exception("push handler failed for %s", type_)


async def connect_with_retry(conn: EngineConnection, *, attempts: int = 5, base_delay: float = 1.0) -> Identity:
    """Exponential backoff for a flaky link; raises the last error when out of attempts."""
    delay = base_delay
    last: Exception | None = None
    for i in range(attempts):
        try:
            return await conn.connect()
        except (OSError, ConnectionError_, EngineError, asyncio.TimeoutError) as exc:
            last = exc
            await conn.close()
            if i == attempts - 1:
                break
            log.warning("connect attempt %d failed (%s); retrying in %.0fs", i + 1, exc, delay)
            await asyncio.sleep(delay)
            delay = min(delay * 2, 30)
    assert last is not None
    raise last
