"""The program's side of `worker_client/localapp.py`: one JSON line out, one back, over the loopback address the service wrote into `app.json`.

Synchronous on purpose (the program calls it from a worker thread): small, and easy to test. No PySide6 here.
"""

from __future__ import annotations

import json
import socket
from pathlib import Path
from typing import Any

from worker_client.config import default_path
from worker_client.localapp import MAX_LINE, read_info

TIMEOUT = 4.0


class ServiceAway(RuntimeError):
    """The Worker service is not running here (or not answering): the program shows what it last knew."""


class LocalClient:
    def __init__(self, settings_path: Path | None = None) -> None:
        self.settings_path = Path(settings_path) if settings_path else default_path()

    def call(self, op: str, **fields: Any) -> dict[str, Any]:
        info = read_info(self.settings_path)
        if info is None:
            raise ServiceAway("the Falcon service is not running on this machine")
        try:
            with socket.create_connection(("127.0.0.1", int(info["port"])), timeout=TIMEOUT) as s:
                s.settimeout(TIMEOUT)
                s.sendall((json.dumps({"token": info["token"], "op": op, **fields}) + "\n").encode("utf-8"))
                data = b""
                while not data.endswith(b"\n"):
                    chunk = s.recv(65536)
                    if not chunk:
                        break
                    data += chunk
                    if len(data) > 8 * MAX_LINE:
                        raise ServiceAway("the answer was too large")
        except OSError as exc:
            raise ServiceAway(f"the Falcon service did not answer: {exc}") from exc
        try:
            reply = json.loads(data)
        except ValueError as exc:
            raise ServiceAway("the Falcon service sent something unreadable") from exc
        if not reply.get("ok"):
            raise ServiceAway(str(reply.get("error") or "refused"))
        return reply

    def view(self) -> dict[str, Any]:
        return self.call("view")["view"]

    def start_task(self, task_id: int) -> None:
        self.call("start_task", id=task_id)

    def ask(self, to_account_id: int) -> None:
        self.call("ask", to=to_account_id)

    def ack(self, ids: list[str]) -> None:
        self.call("ack", ids=ids)
