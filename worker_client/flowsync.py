"""Flow work on this PC (Flow -> Synchronization Mechanism, Stages, Conflict Handling).

    flow.read {transfer_id, path}                    -> we send flow.content {transfer_id, hash, content_b64}
    flow.apply {transfer_id, destination_id, destination_path, relative_path, stages, content_b64}
                                                     -> write through the stages, then flow.sync_result
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


class FlowSync:
    def __init__(self, report: Reporter, *, read_limit: int = 64 << 20) -> None:
        self.report = report
        self.read_limit = read_limit
        self.written_hashes: dict[str, str] = {}  # path -> sha256 of our last write

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
        await self.report("flow.content", {"transfer_id": transfer_id, "hash": hashlib.sha256(data).hexdigest(),
                                           "content_b64": base64.b64encode(data).decode("ascii")})

    async def on_apply(self, payload: dict[str, Any]) -> None:
        transfer_id, dest_id = payload["transfer_id"], payload["destination_id"]
        try:
            data = base64.b64decode(payload.get("content_b64") or "")
            rel = str(payload["relative_path"]).replace("\\", "/")
            target = Path(str(payload["destination_path"])) / rel
            for stage in payload.get("stages") or []:
                target, data = self._apply_stage(stage, target, data)
            target.parent.mkdir(parents=True, exist_ok=True)
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
        await self.report("flow.sync_result", {"transfer_id": transfer_id, "destination_id": dest_id,
                                               "status": "success", "written_hash": digest, "written_path": str(target)})

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


class StageError(Exception):
    def __init__(self, stage: str, kind: str) -> None:
        super().__init__(f"{stage}:{kind}")
        self.stage, self.kind = stage, kind
