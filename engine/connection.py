"""One client connection: reads NDJSON requests, dispatches them, writes responses and pushes.

The first thing the Engine does on a new connection is issue the auth challenge (unless
FALCON_DEV_BYPASS_AUTH). Until `auth.respond` succeeds, only `auth.*` and `system.*` requests
are accepted.
"""

from __future__ import annotations

import asyncio
import logging
from typing import TYPE_CHECKING, Any

from engine import auth
from engine.dispatch import Context, dispatch
from protocol import (
    Envelope,
    ErrorCode,
    Kind,
    ProtocolError,
    decode,
    encode,
    error_response,
    push,
    response,
)

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

MAX_LINE_BYTES = 4 * 1024 * 1024  # generous: Custom Action scripts and file-sweep batches
PRE_AUTH_PREFIXES = ("auth.", "system.")


class Connection:
    def __init__(self, engine: Engine, reader: asyncio.StreamReader,
                 writer: asyncio.StreamWriter) -> None:
        self.engine = engine
        self.reader = reader
        self.writer = writer
        self.peer = writer.get_extra_info("peername")
        self.ctx = Context(engine=engine, connection=self)
        self.authenticated = False
        self.pending_nonce: str | None = None
        self._write_lock = asyncio.Lock()

    # --- outbound -------------------------------------------------------------------------------

    async def send(self, env: Envelope) -> None:
        async with self._write_lock:
            self.writer.write(encode(env))
            await self.writer.drain()

    async def push(self, type_: str, payload: dict[str, Any] | None = None) -> None:
        """Engine-initiated message (session ended, deadline pulse, ping, event fired...)."""
        await self.send(push(type_, payload))

    # --- lifecycle ------------------------------------------------------------------------------

    async def serve(self) -> None:
        log.info("connection from %s", self.peer)
        self.engine.connections.add(self)
        try:
            await self._start_handshake()
            while True:
                try:
                    line = await self.reader.readuntil(b"\n")
                except asyncio.IncompleteReadError:
                    break
                except asyncio.LimitOverrunError:
                    await self.send(error_response(None, ErrorCode.BAD_MESSAGE, "line too long"))
                    break
                if not line.strip():
                    continue
                await self._handle_line(line)
        except (ConnectionError, asyncio.CancelledError):
            pass
        finally:
            self.engine.connections.discard(self)
            await self.engine.on_disconnect(self)
            self.writer.close()
            log.info("connection closed %s", self.peer)

    async def _start_handshake(self) -> None:
        if self.engine.settings.dev_bypass_auth:
            log.warning("DEV_BYPASS_AUTH: skipping challenge for %s", self.peer)
            return
        self.pending_nonce = auth.new_nonce()
        await self.push("auth.challenge", {"nonce": self.pending_nonce})

    async def _handle_line(self, line: bytes) -> None:
        try:
            env = decode(line)
        except ProtocolError as exc:
            await self.send(error_response(None, exc.code, exc.message))
            return

        if env.kind is not Kind.REQUEST:
            # Clients only send requests; pushes/responses in this direction are ignored for now.
            log.debug("ignoring %s from client", env.kind.value)
            return

        assert env.id is not None and env.type is not None
        if not self.authenticated and not env.type.startswith(PRE_AUTH_PREFIXES):
            await self.send(error_response(env.id, ErrorCode.UNAUTHENTICATED))
            return

        try:
            result = await dispatch(self.ctx, env.type, env.payload)
            await self.send(response(env.id, result))
        except ProtocolError as exc:
            await self.send(error_response(env.id, exc.code, exc.message))
        except Exception:
            log.exception("handler %s failed", env.type)
            await self.send(error_response(env.id, ErrorCode.INTERNAL))
