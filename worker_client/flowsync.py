"""Flow work on this PC (Flow -> Synchronization Mechanism, Stages, Conflict Handling).

    flow.read {transfer_id, path}                    -> we send flow.content {transfer_id, hash, content_b64}
                                                        (a big file in chunks: {..., chunk: {index, total}, content_b64})
    flow.list {request_id, path}                     -> we send flow.listing {request_id, entries: [{relative_path, hash}], done}
    flow.apply {transfer_id, destination_id, destination_path, relative_path, stages, content_b64}
                                                     -> write through the stages, then flow.sync_result
                                                        (a big file arrives in chunks, each with chunk: {index, total}; written when whole)
    flow.resolve_conflict {path, rename_to}          -> rename the externally modified copy
    flow.remove {destination_id, relative_path, path, hash, root}
                                                     -> the source deleted it and the flow mirrors deletions: move our own, unedited copy aside
                                                        (into `.falcon-removed`), then flow.remove_result {status: removed|kept|missing}

Steps (engine/flow/steps.py has the tree; the Engine sends each destination's path in order, Choosing already done):
  * conversion  to_pdf, to_docx, to_image, zip_each   -- worker_client/convert.py; a file a step cannot have is copied as it is or left
                                                         out (its `if_not`), never a reason to stop the flow
  * renaming    add_date, add_text, replace_text
  * bundling    a file of a bundle's run (`bundle` in flow.apply) is kept aside, not written: flow.bundle_close makes the one ZIP
                from what was kept, flow.bundle_drop throws it away
The source's modified time comes with the content (`modified`, ISO 8601); a copy that does not have it uses the day it is written.

Every write records its own hash so the Engine's write attribution can tell our writes from
external ones when the file event for our own write comes back through the index.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import logging
import os
import re
import shutil
import tempfile
import zipfile
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import Any

from worker_client import convert
from worker_client.sharedread import open_shared

log = logging.getLogger(__name__)

Reporter = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]

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
        self._bundles: dict[str, Path] = {}                                 # a bundle's run -> where its files are kept aside

    async def on_read(self, payload: dict[str, Any]) -> None:
        transfer_id, path = payload["transfer_id"], Path(payload["path"])
        try:
            if path.stat().st_size > self.read_limit:
                raise OSError("file too large for relay")
            data = await asyncio.to_thread(path.read_bytes)
            modified = datetime.fromtimestamp(path.stat().st_mtime).astimezone().isoformat(timespec="seconds")
        except OSError as exc:
            log.warning("flow.read %s failed: %s", path, exc)
            await self.report("flow.content", {"transfer_id": transfer_id, "error": "unreadable"})
            return
        digest = hashlib.sha256(data).hexdigest()
        if len(data) <= CHUNK_BYTES:
            await self.report("flow.content", {"transfer_id": transfer_id, "hash": digest, "modified": modified,
                                               "content_b64": base64.b64encode(data).decode("ascii")})
            return
        total = (len(data) + CHUNK_BYTES - 1) // CHUNK_BYTES
        for index in range(total):
            piece = data[index * CHUNK_BYTES:(index + 1) * CHUNK_BYTES]
            await self.report("flow.content", {"transfer_id": transfer_id, "hash": digest, "modified": modified, "chunk": {"index": index, "total": total},
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
        rel = str(payload["relative_path"]).replace("\\", "/")
        root = Path(str(payload["destination_path"]))
        when = _when(payload.get("modified"))
        bundle = payload.get("bundle")
        try:
            made, notes = await asyncio.to_thread(self._apply_steps, payload.get("stages") or [], root / rel, piece, when)
            if made is None:
                await self.report("flow.sync_result", {"transfer_id": transfer_id, "destination_id": dest_id, "status": "left_out",
                                                       "why": "; ".join(n["why"] for n in notes if n.get("left_out")) or "a step left it out"})
                return
            target, data = made
            if bundle:                                            # a file of a bundle's run: kept aside until the bundle is made
                await asyncio.to_thread(self._keep_aside, str(bundle), root, target, data)
                reply: dict[str, Any] = {"transfer_id": transfer_id, "destination_id": dest_id, "status": "kept_aside"}
                if notes:
                    reply["as_is"] = notes
                await self.report("flow.sync_result", reply)
                return
            target.parent.mkdir(parents=True, exist_ok=True)
            size_before = target.stat().st_size if target.is_file() else None
            preserved = await asyncio.to_thread(self._preserve_unknown, target, data, payload.get("previous"))
            await asyncio.to_thread(target.write_bytes, data)
            replaced = await asyncio.to_thread(self._replace_older, target, root, payload.get("previous"))
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
        result: dict[str, Any] = {"transfer_id": transfer_id, "destination_id": dest_id, "status": "success", "written_hash": digest,
                                  "written_path": str(target), "size_before": size_before, "size_after": len(data)}
        if preserved:
            result["preserved"] = str(preserved)
        if notes:
            result["as_is"] = notes
        if replaced:
            result["replaced"] = replaced
        await self.report("flow.sync_result", result)

    # --- a Bundling step's run ------------------------------------------------------------------------------------------------

    def _bundle_dir(self, bundle_id: str) -> Path:
        if bundle_id not in self._bundles:
            self._bundles[bundle_id] = Path(tempfile.mkdtemp(prefix="falcon-bundle-"))
        return self._bundles[bundle_id]

    def _keep_aside(self, bundle_id: str, root: Path, target: Path, data: bytes) -> None:
        try:
            rel = target.relative_to(root)
        except ValueError:
            rel = Path(target.name)
        place = self._bundle_dir(bundle_id) / rel
        place.parent.mkdir(parents=True, exist_ok=True)
        place.write_bytes(data)

    async def on_bundle_close(self, payload: dict[str, Any]) -> None:
        """Make the one file from what this run kept aside, write it where the flow writes, and say how it went."""
        bundle_id = str(payload["bundle_id"])
        reply: dict[str, Any] = {"bundle_id": bundle_id}
        base = self._bundles.pop(bundle_id, None)
        try:
            if base is None:
                raise OSError("nothing was kept aside for this bundle")
            data, files = await asyncio.to_thread(_make_bundle, base, str(payload.get("folders") or "keep"))
            target = Path(str(payload["destination_path"])) / str(payload["name"])
            target.parent.mkdir(parents=True, exist_ok=True)
            before = target.stat().st_size if target.is_file() else None
            kept = await asyncio.to_thread(self._preserve_unknown, target, data, payload.get("previous"))
            await asyncio.to_thread(target.write_bytes, data)
            digest = hashlib.sha256(data).hexdigest()
            self.written_hashes[str(target)] = digest
            reply.update({"status": "success", "written_path": str(target), "written_hash": digest, "files": files,
                          "size_before": before, "size_after": len(data)})
            if kept:
                reply["preserved"] = str(kept)
        except (OSError, zipfile.BadZipFile) as exc:
            log.warning("flow bundle %s failed: %s", bundle_id, exc)
            reply.update({"status": "failed", "why": str(exc)[:200]})
        finally:
            if base is not None:
                shutil.rmtree(base, ignore_errors=True)
        await self.report("flow.bundle_result", reply)

    async def on_bundle_drop(self, payload: dict[str, Any]) -> None:
        base = self._bundles.pop(str(payload.get("bundle_id")), None)
        if base is not None:
            await asyncio.to_thread(shutil.rmtree, base, True)

    @classmethod
    def _replace_older(cls, target: Path, root: Path, previous: dict[str, Any] | None) -> dict[str, Any] | None:
        """One file in, one file out: when a step gave this version a new name (Add a date, after an edit), the copy the flow wrote under the
        old name is put aside, as a removal is. A copy someone changed since is theirs, and stays. Returns what was done, or None."""
        path = str((previous or {}).get("path") or "")
        if not path or _same_path(path, str(target)):
            return None
        older = Path(path)
        try:
            older.relative_to(root)
            if not older.is_file():
                return None
            if hash_of(older, 1 << 62) != previous.get("hash"):
                return {"path": path, "kept": True}
            return {"path": path, "moved_to": str(cls._put_away(older, root))}
        except (ValueError, OSError) as exc:
            log.warning("could not put aside the older copy %s: %s", path, exc)
            return None

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

    async def on_remove(self, payload: dict[str, Any]) -> None:
        """The source deleted a file and the flow mirrors deletions: put away the copy it wrote. Moved into `.falcon-removed` under the destination
        (never destroyed), and only if it is still exactly what the flow wrote -- anything edited since is kept and said so."""
        path = Path(str(payload["path"]))
        root = Path(str(payload["root"]))
        rel = str(payload["relative_path"])
        reply = {"destination_id": payload["destination_id"], "relative_path": rel, "path": str(path)}
        try:
            if not path.is_file():
                reply["status"] = "missing"
            elif not payload.get("settled") and await asyncio.to_thread(hash_of, path, 1 << 62) != payload.get("hash"):      # (settled: an Admin chose)
                reply["status"] = "kept"                                       # changed since the flow wrote it: not ours to remove
            else:
                aside = await asyncio.to_thread(self._put_away, path, root)
                reply["status"], reply["moved_to"] = "removed", str(aside)
        except OSError as exc:
            log.warning("flow.remove failed for %s: %s", path, exc)
            reply["status"] = "kept"
        await self.report("flow.remove_result", reply)

    @staticmethod
    def _put_away(path: Path, root: Path) -> Path:
        try:
            inside = path.relative_to(root)
        except ValueError:
            inside = Path(path.name)
        target = root / ".falcon-removed" / inside
        target.parent.mkdir(parents=True, exist_ok=True)
        n = 1
        while target.exists():
            n += 1
            target = target.with_name(f"{inside.stem}-{n}{inside.suffix}")
        os.replace(path, target)
        return target

    async def on_resolve_conflict(self, payload: dict[str, Any]) -> None:
        src, dst = Path(str(payload["path"])), Path(str(payload["rename_to"]))
        try:
            await asyncio.to_thread(os.replace, src, dst)
            log.info("conflict: preserved external edit as %s", dst)
        except OSError as exc:
            log.warning("could not preserve external edit %s: %s", src, exc)

    # --- steps --------------------------------------------------------------------------------------------------------------

    def _apply_steps(self, stages: list[dict[str, Any]], target: Path, data: bytes,
                     when: datetime | None) -> tuple[tuple[Path, bytes] | None, list[dict[str, Any]]]:
        """Each step on the file, in order. Returns the file to write (None when a Conversion left it out) and what could not be done
        ({step, file, why, left_out?})."""
        notes: list[dict[str, Any]] = []
        copied = datetime.now().astimezone()
        changed = when or copied
        for stage in stages:
            cfg = stage.get("config") or {}
            kind, op, s = stage.get("stage_type"), cfg.get("op"), cfg.get("settings") or {}
            if kind == "conversion":
                made = self._convert(op, s, target, data, changed)
                if isinstance(made, str):
                    leave = s.get("if_not") == "leave_out"
                    notes.append({"step": cfg.get("label") or op, "file": target.name, "why": made, "left_out": leave})
                    if leave:
                        return None, notes
                else:
                    target, data = made
            elif kind == "renaming":
                target = _renamed(op, s, target, changed if s.get("date", "changed") == "changed" else copied)
        return (target, data), notes

    @staticmethod
    def _convert(op: str | None, s: dict[str, Any], target: Path, data: bytes, when: datetime) -> tuple[Path, bytes] | str:
        """One Conversion on one file: (its new place, its new content); the file as it is when the step is not for its type; or why it could not."""
        frm = target.suffix.lower().lstrip(".")
        if op == "zip_each":
            return target.with_name(target.name + ".zip"), _zip_one(target.name, data, when)
        groups = set(s.get("from") or [])
        try:
            if op == "to_pdf":
                if frm == "pdf" or not any(frm in CONVERT_GROUPS[g] for g in groups):
                    return target, data
                return target.with_suffix(".pdf"), convert.to_pdf(data, frm)
            if op == "to_docx":
                if frm == "docx" or not any(frm in CONVERT_GROUPS[g] for g in groups):
                    return target, data
                return target.with_suffix(".docx"), convert.to_docx(data, frm)
            if op == "to_image":
                to = str(s.get("to") or "jpg")
                if frm not in convert.IMAGES or frm == to or (to == "jpg" and frm == "jpeg"):
                    return target, data
                return target.with_suffix("." + to), convert.image(data, frm, to, int(s.get("quality") or 85))
        except convert.Unconvertible as exc:
            return str(exc)[:160]
        return target, data


CONVERT_GROUPS: dict[str, tuple[str, ...]] = {"text": convert.TEXT, "images": convert.IMAGES, "word": convert.WORD, "excel": convert.EXCEL,
                                              "powerpoint": convert.POWERPOINT, "pdf": ("pdf",)}
DATE_FORMATS = {"yyyy-mm-dd": "%Y-%m-%d", "dd-mm-yyyy": "%d-%m-%Y", "yyyymmdd": "%Y%m%d"}


def _renamed(op: str | None, s: dict[str, Any], target: Path, when: datetime) -> Path:
    stem, suffix = target.stem, target.suffix
    if op == "add_date":
        day = when.strftime(DATE_FORMATS.get(str(s.get("format")), "%Y-%m-%d"))
        return target.with_name(f"{day} {target.name}" if s.get("where", "before") == "before" else f"{stem} {day}{suffix}")
    if op == "add_text":
        text = str(s.get("text") or "")
        return target.with_name(f"{text}{target.name}" if s.get("where", "before") == "before" else f"{stem}{text}{suffix}")
    if op == "replace_text":
        find = str(s.get("find") or "")
        if not find:
            return target
        new = re.sub(re.escape(find), lambda _m: str(s.get("with") or ""), stem, flags=re.IGNORECASE).strip()
        return target.with_name(f"{new}{suffix}") if new else target
    return target


def _make_bundle(base: Path, folders: str) -> tuple[bytes, int]:
    """(the ZIP, how many files are in it) from what a run kept aside."""
    found = sorted((p for p in base.rglob("*") if p.is_file()), key=lambda p: p.relative_to(base).as_posix().lower())
    out = io.BytesIO()
    used: set[str] = set()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in found:
            name = p.relative_to(base).as_posix() if folders == "keep" else p.name
            stem, dot, ext = name.rpartition(".")
            n = 2
            while name.lower() in used:                       # flattened, two files of one name: the second is "name (2)"
                name = f"{stem} ({n}).{ext}" if dot else f"{name} ({n})"
                n += 1
            used.add(name.lower())
            z.write(p, name)
    return out.getvalue(), len(found)


def _when(raw: Any) -> datetime | None:
    """The source's modified time from flow.apply, or None (then the step uses the day it writes)."""
    if not raw:
        return None
    try:
        when = datetime.fromisoformat(str(raw).replace("Z", "+00:00"))
    except ValueError:
        return None
    return when.astimezone() if when.tzinfo else when


def _zip_one(name: str, data: bytes, when: datetime) -> bytes:
    """One file in a ZIP. Its date inside is the file's own, so the same file packs to the same bytes and is not sent again for nothing."""
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", compression=zipfile.ZIP_DEFLATED) as z:
        info = zipfile.ZipInfo(name, date_time=(max(when.year, 1980), when.month, when.day, when.hour, when.minute, when.second - when.second % 2))
        info.compress_type = zipfile.ZIP_DEFLATED
        info.external_attr = 0o644 << 16
        z.writestr(info, data)
    return out.getvalue()


def _same_path(a: str, b: str) -> bool:
    return a.replace("\\", "/").lower() == b.replace("\\", "/").lower()


def hash_of(path: Path, limit: int) -> str | None:
    """sha256 of a file, or None above the size a flow relays."""
    if path.stat().st_size > limit:
        return None
    h = hashlib.sha256()
    with open_shared(path) as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()
