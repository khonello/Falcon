"""Flow work on this PC (Flow -> Synchronization Mechanism, Stages, Conflict Handling).

    flow.read {transfer_id, path}                    -> we send flow.content {transfer_id, hash, content_b64}
                                                        (a big file in chunks: {..., chunk: {index, total}, content_b64})
    flow.list {request_id, path}                     -> we send flow.listing {request_id, entries: [{relative_path, hash}], done}
    flow.apply {transfer_id, destination_id, destination_path, relative_path, stages, content_b64}
                                                     -> write through the stages, then flow.sync_result
                                                        (a big file arrives in chunks, each with chunk: {index, total}; written when whole)
    flow.resolve_conflict {path, rename_to}          -> rename the externally modified copy

Stages (v1):
  * transformation {"to": "<ext>"}  -- converts when a converter is registered for the pair;
    otherwise fails with kind `unsupported_format` (the Engine surfaces the predefined suggestion)
  * categorization {"by": "extension"} -- places the file in a subfolder named by extension

Every write records its own hash so the Engine's write attribution can tell our writes from
external ones when the file event for our own write comes back through the index.
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
Converter = Callable[[bytes, str, str], bytes]  # (content, from_ext, to_ext) -> content

# Registered converters: (from, to) -> fn. v1 ships text-safe identity conversions only;
# real format conversion (docx->pdf) is a deployment concern (LibreOffice etc.) plugged in here.
CONVERTERS: dict[tuple[str, str], Converter] = {
    ("txt", "md"): lambda data, _f, _t: data,
    ("md", "txt"): lambda data, _f, _t: data,
    ("csv", "txt"): lambda data, _f, _t: data,
}


CHUNK_BYTES = 512 * 1024          # raw bytes per message: one message must stay far below what a connection reads at a time
LIST_BATCH = 200


class FlowSync:
    def __init__(self, report: Reporter, *, read_limit: int = 64 << 20, hash_limit: int = 64 << 20) -> None:
        self.report = report
        self.read_limit = read_limit
        self.hash_limit = hash_limit
        self.written_hashes: dict[str, str] = {}  # path -> sha256 of our last write
        self._arriving: dict[tuple[str, int], dict[int, bytes]] = {}      # chunks of a file on its way in
        self._hashes: dict[str, tuple[int, int, str | None]] = {}          # path -> (size, mtime_ns, hash) of what a listing last read

    async def on_read(self, payload: dict[str, Any]) -> None:
        transfer_id, path = payload["transfer_id"], Path(payload["path"])
        try:
            if path.stat().st_size > self.read_limit:
                raise OSError("file too large for relay")
            data = await asyncio.to_thread(path.read_bytes)
        except OSError as exc:
            log.warning("flow.read %s failed: %s", path, exc)
            await self.report("flow.content", {"transfer_id": transfer_id, "error": "unreadable"})
            return
        digest = hashlib.sha256(data).hexdigest()
        if len(data) <= CHUNK_BYTES:
            await self.report("flow.content", {"transfer_id": transfer_id, "hash": digest, "content_b64": base64.b64encode(data).decode("ascii")})
            return
        total = (len(data) + CHUNK_BYTES - 1) // CHUNK_BYTES
        for index in range(total):
            piece = data[index * CHUNK_BYTES:(index + 1) * CHUNK_BYTES]
            await self.report("flow.content", {"transfer_id": transfer_id, "hash": digest, "chunk": {"index": index, "total": total},
                                               "content_b64": base64.b64encode(piece).decode("ascii")})

    async def on_list(self, payload: dict[str, Any]) -> None:
        """What this folder holds now, with each file's hash, so the Engine can send a destination what it is missing."""
        request_id, root = payload["request_id"], Path(payload["path"])

        def walk() -> list[dict[str, Any]]:
            found = []
            for dirpath, _dirs, files in os.walk(root):
                for name in files:
                    f = Path(dirpath) / name
                    try:
                        st = f.stat()
                        cached = self._hashes.get(str(f))
                        if cached and cached[0] == st.st_size and cached[1] == st.st_mtime_ns:
                            digest = cached[2]                    # unchanged since it was last listed: not read again (a listing is asked for often)
                        else:
                            digest = hash_of(f, self.hash_limit)
                            if len(self._hashes) < 200_000:
                                self._hashes[str(f)] = (st.st_size, st.st_mtime_ns, digest)
                    except OSError:
                        continue                                  # locked or gone: it will come with its own event
                    found.append({"relative_path": str(f.relative_to(root)).replace("\\", "/"), "hash": digest})
            return found

        entries = await asyncio.to_thread(walk) if root.is_dir() else []
        for i in range(0, max(len(entries), 1), LIST_BATCH):
            await self.report("flow.listing", {"request_id": request_id, "entries": entries[i:i + LIST_BATCH],
                                              "done": i + LIST_BATCH >= len(entries)})

    async def on_apply(self, payload: dict[str, Any]) -> None:
        transfer_id, dest_id = payload["transfer_id"], payload["destination_id"]
        chunk = payload.get("chunk")
        piece = base64.b64decode(payload.get("content_b64") or "")
        if chunk:
            parts = self._arriving.setdefault((transfer_id, dest_id), {})
            parts[int(chunk["index"])] = piece
            if len(parts) < int(chunk["total"]):
                return                                            # the rest is on its way
            piece = b"".join(parts[i] for i in range(int(chunk["total"])))
            del self._arriving[(transfer_id, dest_id)]
        try:
            data = piece
            rel = str(payload["relative_path"]).replace("\\", "/")
            target = Path(str(payload["destination_path"])) / rel
            for stage in payload.get("stages") or []:
                target, data = self._apply_stage(stage, target, data)
            target.parent.mkdir(parents=True, exist_ok=True)
            preserved = await asyncio.to_thread(self._preserve_unknown, target, data, payload.get("previous"))
            await asyncio.to_thread(target.write_bytes, data)
        except StageError as exc:
            await self.report("flow.sync_result", {"transfer_id": transfer_id, "destination_id": dest_id,
                                                   "status": "failed", "failure": {"stage_type": exc.stage, "kind": exc.kind}})
            return
        except PermissionError:
            await self.report("flow.sync_result", {"transfer_id": transfer_id, "destination_id": dest_id,
                                                   "status": "failed",
                                                   "failure": {"stage_type": "destination", "kind": "permission_denied"}})
            return
        except OSError as exc:
            log.warning("flow.apply failed: %s", exc)
            await self.report("flow.sync_result", {"transfer_id": transfer_id, "destination_id": dest_id,
                                                   "status": "failed", "failure": {"stage_type": "destination", "kind": "unreachable"}})
            return
        digest = hashlib.sha256(data).hexdigest()
        self.written_hashes[str(target)] = digest
        result = {"transfer_id": transfer_id, "destination_id": dest_id, "status": "success", "written_hash": digest, "written_path": str(target)}
        if preserved:
            result["preserved"] = str(preserved)
        await self.report("flow.sync_result", result)

    @staticmethod
    def _preserve_unknown(target: Path, data: bytes, previous: dict[str, Any] | None) -> Path | None:
        """Whatever is already at the place a flow is about to write is either (a) what the flow wrote last time and nobody touched, (b) already
        the very content about to be written, or (c) something the flow did not write: someone's own file, or an edit. Only (c) is kept, beside the
        new file as `<name>-modified.<ext>`, so a flow can never silently overwrite a person's file. Returns where it was kept."""
        if not target.is_file():
            return None
        try:
            now = hash_of(target, 1 << 62)
        except OSError:
            return None
        if now == hashlib.sha256(data).hexdigest():
            return None                                                    # already exactly this
        if previous and previous.get("hash") and now == previous["hash"] and _same_path(str(previous.get("path") or ""), str(target)):
            return None                                                    # the flow's own earlier write, untouched since
        kept = target.with_name(f"{target.stem}-modified{target.suffix}")
        n = 2
        while kept.exists():
            kept = target.with_name(f"{target.stem}-modified-{n}{target.suffix}")
            n += 1
        os.replace(target, kept)
        return kept

    async def on_resolve_conflict(self, payload: dict[str, Any]) -> None:
        src, dst = Path(str(payload["path"])), Path(str(payload["rename_to"]))
        try:
            await asyncio.to_thread(os.replace, src, dst)
            log.info("conflict: preserved external edit as %s", dst)
        except OSError as exc:
            log.warning("could not preserve external edit %s: %s", src, exc)

    # --- stages ---------------------------------------------------------------------------------

    def _apply_stage(self, stage: dict[str, Any], target: Path, data: bytes) -> tuple[Path, bytes]:
        kind = stage.get("stage_type")
        cfg = stage.get("config") or {}
        if kind == "transformation":
            to = str(cfg.get("to", "")).lower().lstrip(".")
            frm = target.suffix.lower().lstrip(".")
            if not to or to == frm:
                return target, data
            conv = CONVERTERS.get((frm, to))
            if conv is None:
                raise StageError("transformation", "unsupported_format")
            try:
                return target.with_suffix("." + to), conv(data, frm, to)
            except Exception as exc:
                log.warning("conversion %s->%s failed: %s", frm, to, exc)
                raise StageError("transformation", "convert_failed") from exc
        if kind == "categorization":
            by = str(cfg.get("by", "extension"))
            if by != "extension":
                raise StageError("categorization", "place_failed")
            folder = target.suffix.lower().lstrip(".") or "other"
            return target.parent / folder / target.name, data
        return target, data


def _same_path(a: str, b: str) -> bool:
    return a.replace("\\", "/").lower() == b.replace("\\", "/").lower()


def hash_of(path: Path, limit: int) -> str | None:
    """sha256 of a file, or None above the size a flow relays."""
    if path.stat().st_size > limit:
        return None
    h = hashlib.sha256()
    with path.open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


class StageError(Exception):
    def __init__(self, stage: str, kind: str) -> None:
        super().__init__(f"{stage}:{kind}")
        self.stage, self.kind = stage, kind
