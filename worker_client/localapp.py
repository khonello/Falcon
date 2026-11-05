"""The small Falcon program on a Worker's machine talks to the Worker service here, and only here.

The program (`worker_client/program`) runs as the person at their desk. It has no key and never talks to the Engine itself: the service holds the
connection. So the service listens on this machine's loopback address, and the program asks it, one JSON line at a time:

    {"token": "...", "op": "view"}                      -> {"ok": true, "view": {...}}        what is relevant to this person, right now
    {"token": "...", "op": "start_task", "id": 7}       -> {"ok": true}
    {"token": "...", "op": "ack", "ids": ["t7"]}        -> {"ok": true}                       the program showed those notes; do not show them again
    {"token": "...", "op": "talk", "line": ".."}        -> {"ok": true}                     the person asks to talk ("Ask IT")
    {"token": "...", "op": "conversation", "id": 4}     -> {"ok": true, "conversation": {...}} one conversation an Admin started, read up to now
    {"token": "...", "op": "reply", "id": 4, "body": ".."} -> {"ok": true}                     the person answers in it (they never start one)
    {"token": "...", "op": "send_file", "id": 4, "path": ".."} -> {"ok": true, "sent": {...}}  a file from this machine, in that conversation
    {"token": "...", "op": "setup", "address": "..", "code": "..", "cert": ".."} -> {"ok": true}   first run only (`firstrun.py`): the view then says how it went
    {"token": "...", "op": "save_file", "file_id": 9}   -> {"ok": true}                       a file sent there, saved to Downloads, in "From Falcon"

Where it is and what it checks:
  * 127.0.0.1 only, on a port the service picks; `app.json` beside the Worker's settings holds the port and a random token, readable by the people who
    use this machine and nobody off it (the same trust as the console's signing pipe: whoever is at the machine is its person)
  * every request carries the token; a wrong or missing one is refused and the connection is closed
  * a request is one line of at most 64 KB; anything else is refused. The service answers from what it already knows when it cannot reach the Engine,
    and says so (`connected: false`, `as_of`) so the program can tell live from remembered.
Stdlib only.
"""

from __future__ import annotations

import asyncio
import contextlib
import hmac
import json
import logging
import os
import secrets
import subprocess
import sys
from pathlib import Path
from typing import Any, Protocol

log = logging.getLogger(__name__)

MAX_LINE = 64 * 1024
IDLE_SECONDS = 15.0


class Provider(Protocol):
    async def app_view(self) -> dict[str, Any]: ...
    async def app_start_task(self, task_id: int) -> None: ...
    async def app_ack(self, ids: list[str]) -> None: ...
    async def app_talk(self, line: str) -> None: ...
    async def app_conversation(self, conversation_id: int) -> dict[str, Any]: ...
    async def app_reply(self, conversation_id: int, body: str) -> None: ...
    async def app_send_file(self, conversation_id: int, path: str) -> dict[str, Any]: ...
    async def app_save_file(self, file_id: int) -> None: ...
    async def app_setup(self, address: str, code: str, cert: str) -> None: ...


def info_path(settings_path: Path) -> Path:
    return Path(settings_path).parent / "app.json"


def read_info(settings_path: Path) -> dict[str, Any] | None:
    """What the program needs to find the service: {"port", "token"}; None when the service is not running here."""
    try:
        data = json.loads(info_path(settings_path).read_text(encoding="utf-8"))
        return data if isinstance(data.get("port"), int) and data.get("token") else None
    except (OSError, ValueError):
        return None


class LocalApp:
    def __init__(self, provider: Provider, settings_path: Path) -> None:
        self.provider = provider
        self.settings_path = Path(settings_path)
        self.token = secrets.token_urlsafe(24)
        self.port = 0
        self.served = 0
        self.refused = 0
        self._server: asyncio.AbstractServer | None = None

    async def start(self) -> int:
        self._server = await asyncio.start_server(self._client, "127.0.0.1", 0, limit=MAX_LINE)
        self.port = self._server.sockets[0].getsockname()[1]
        self._write_info()
        return self.port

    async def stop(self) -> None:
        if self._server is not None:
            self._server.close()
            with contextlib.suppress(Exception):
                await self._server.wait_closed()
        with contextlib.suppress(OSError):
            info_path(self.settings_path).unlink()

    def _write_info(self) -> None:
        path = info_path(self.settings_path)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(".tmp")
        tmp.write_text(json.dumps({"port": self.port, "token": self.token, "pid": os.getpid()}), encoding="utf-8")
        os.replace(tmp, path)
        if sys.platform == "win32" and not os.environ.get("FALCON_NO_ACL"):
            # the Worker's folder is readable by the system and administrators only; this one file is for the people who use the machine
            with contextlib.suppress(OSError):
                subprocess.run(["icacls", str(path), "/grant", "*S-1-5-32-545:(R)"], capture_output=True, check=False, timeout=15)

    async def _client(self, reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            while True:
                try:
                    line = await asyncio.wait_for(reader.readline(), IDLE_SECONDS)
                except (asyncio.TimeoutError, ValueError, asyncio.LimitOverrunError):
                    return
                if not line:
                    return
                reply = await self._answer(line)
                writer.write((json.dumps(reply) + "\n").encode("utf-8"))
                await writer.drain()
                if not reply.get("ok") and reply.get("error") == "refused":
                    return
        except (ConnectionError, OSError):
            return
        finally:
            with contextlib.suppress(Exception):
                writer.close()

    async def _answer(self, line: bytes) -> dict[str, Any]:
        try:
            msg = json.loads(line)
            if not isinstance(msg, dict):
                raise TypeError("a request is an object")
        except (ValueError, TypeError):
            return {"ok": False, "error": "bad request"}
        if not hmac.compare_digest(str(msg.get("token") or ""), self.token):
            self.refused += 1
            return {"ok": False, "error": "refused"}
        op = msg.get("op")
        try:
            if op == "view":
                return {"ok": True, "view": await self.provider.app_view()}
            if op == "start_task":
                await self.provider.app_start_task(int(msg["id"]))
            elif op == "talk":
                line = msg.get("line")
                if not isinstance(line, str) or not line.strip():
                    return {"ok": False, "error": "say what it is about"}
                await self.provider.app_talk(line)
            elif op == "conversation":
                return {"ok": True, "conversation": await self.provider.app_conversation(int(msg["id"]))}
            elif op == "reply":
                body = msg.get("body")
                if not isinstance(body, str) or not body.strip():
                    return {"ok": False, "error": "write something to send"}
                await self.provider.app_reply(int(msg["id"]), body)
            elif op == "send_file":
                return {"ok": True, "sent": await self.provider.app_send_file(int(msg["id"]), str(msg.get("path") or ""))}
            elif op == "save_file":
                await self.provider.app_save_file(int(msg["file_id"]))
            elif op == "setup":
                await self.provider.app_setup(str(msg.get("address") or ""), str(msg.get("code") or ""), str(msg.get("cert") or ""))
            elif op == "ack":
                ids = msg.get("ids")
                if not isinstance(ids, list) or not all(isinstance(i, str) for i in ids):
                    return {"ok": False, "error": "ids must be a list of text"}
                await self.provider.app_ack(ids)
            else:
                return {"ok": False, "error": "unknown op"}
        except (KeyError, TypeError, ValueError):
            return {"ok": False, "error": "bad request"}
        except Exception as exc:  # noqa: BLE001 -- the program is told, the service carries on
            log.warning("local app request %s failed: %s", op, exc)
            return {"ok": False, "error": str(exc) or "failed"}
        self.served += 1
        return {"ok": True}
