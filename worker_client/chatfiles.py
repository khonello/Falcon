"""A file sent in a conversation, on this machine (engine/resource/chatfiles.py).

    chat.file_read    {file_id, path, max_bytes}                          -> we send chat.file_content pieces, or {file_id, error}
    chat.file_deliver {save_id, file_id, name, hash, index, total, content_b64}   -> once whole: written to Downloads\\From Falcon,
                                                                             then chat.file_saved {save_id, path, hash} (or {save_id, error})

What arrives goes into the Downloads folder of the person signed in here, in "From Falcon"; a file of the same name already there is never
overwritten (the new one is "name (2).ext"). Programs and scripts are refused here as well as on the Engine. Stdlib only.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import logging
import os
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

log = logging.getLogger(__name__)

Reporter = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]
CHUNK_BYTES = 512 * 1024
REFUSED = frozenset({".exe", ".msi", ".bat", ".cmd", ".ps1", ".py", ".vbs", ".js", ".com", ".scr", ".psm1", ".wsf", ".jar", ".lnk"})
FOLDER = "From Falcon"


def downloads() -> Path:
    """Downloads of the person signed in at this machine (the service runs as the system account, so its own home is not theirs)."""
    try:
        import psutil

        people = [u for u in psutil.users() if u.name]
        if people and os.name == "nt":
            first = min(people, key=lambda u: u.started or 0)
            home = Path(os.environ.get("SystemDrive", "C:") + os.sep) / "Users" / first.name.split("\\")[-1]
            if home.is_dir():
                return home / "Downloads"
    except (ImportError, OSError):
        pass
    return Path.home() / "Downloads"


def free_name(folder: Path, name: str) -> Path:
    target = folder / name
    stem, ext = os.path.splitext(name)
    n = 1
    while target.exists():
        n += 1
        target = folder / f"{stem} ({n}){ext}"
    return target


class ChatFiles:
    def __init__(self, report: Reporter, *, downloads_dir: Path | None = None) -> None:
        self.report = report
        self.downloads_dir = downloads_dir                       # (tests) where Downloads is; otherwise the signed-in person's
        self._arriving: dict[int, dict[int, bytes]] = {}

    async def on_read(self, payload: dict[str, Any]) -> None:
        file_id, path = int(payload["file_id"]), Path(str(payload["path"]))
        limit = int(payload.get("max_bytes") or 100 * 1024 * 1024)
        if path.suffix.lower() in REFUSED:
            await self.report("chat.file_content", {"file_id": file_id, "error": "refused"})
            return
        try:
            if path.stat().st_size > limit:
                await self.report("chat.file_content", {"file_id": file_id, "error": "too_big"})
                return
            data = await asyncio.to_thread(path.read_bytes)
        except OSError as exc:
            log.warning("chat file %s could not be read: %s", path, exc)
            await self.report("chat.file_content", {"file_id": file_id, "error": "unreadable"})
            return
        digest = hashlib.sha256(data).hexdigest()
        total = max(1, (len(data) + CHUNK_BYTES - 1) // CHUNK_BYTES)
        for index in range(total):
            await self.report("chat.file_content", {"file_id": file_id, "index": index, "total": total, "hash": digest,
                                                    "content_b64": base64.b64encode(data[index * CHUNK_BYTES:(index + 1) * CHUNK_BYTES]).decode("ascii")})

    async def on_deliver(self, payload: dict[str, Any]) -> None:
        save_id, index, total = int(payload["save_id"]), int(payload["index"]), int(payload["total"])
        parts = self._arriving.setdefault(save_id, {})
        parts[index] = base64.b64decode(str(payload.get("content_b64") or ""))
        if len(parts) < total:
            return
        data = b"".join(parts[i] for i in range(total))
        del self._arriving[save_id]
        name = os.path.basename(str(payload.get("name") or "file"))
        if os.path.splitext(name)[1].lower() in REFUSED:
            await self.report("chat.file_saved", {"save_id": save_id, "error": "programs and scripts are not saved"})
            return
        digest = hashlib.sha256(data).hexdigest()
        if payload.get("hash") and payload["hash"] != digest:
            await self.report("chat.file_saved", {"save_id": save_id, "error": "it did not arrive whole"})
            return
        try:
            folder = (self.downloads_dir or downloads()) / FOLDER
            target = await asyncio.to_thread(self._write, folder, name, data)
        except OSError as exc:
            await self.report("chat.file_saved", {"save_id": save_id, "error": f"could not be written: {exc}"})
            return
        await self.report("chat.file_saved", {"save_id": save_id, "path": str(target), "hash": digest})

    @staticmethod
    def _write(folder: Path, name: str, data: bytes) -> Path:
        folder.mkdir(parents=True, exist_ok=True)
        target = free_name(folder, name)
        target.write_bytes(data)
        return target
