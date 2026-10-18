"""A flow does not carry anything restricted -- unless the owner of the restriction has said it may.

By default a flow never touches a restricted file or folder. It does not find that out once, on the day it was made: a folder is marked later, a file is moved into a tier folder, a
copy of marked content turns up. So every step a flow takes with a file asks again, against what is true now, and nothing here is cached:

    * when a flow is made or edited: its source folder and every destination folder
    * when a change at the source is seen, and again when a file is about to be read (catch-up, a manual trigger, a retry all come through there)
    * when the file's content arrives (its content may be marked even though its name and place are not)
    * before it is written to each destination (the destination folder may have become restricted since)
    * before a copy the flow wrote is put away on a mirrored delete

What the flow meets is a BLOCKER: a mark that names the file or a folder above it, a mark whose content this is a copy of, or a restricted/admin tier. When a flow meets one that
no one has consented to, the flow is PAUSED -- not failed, not left to run -- and the owner of the restriction is asked: the person who marked it (or the Super User); for a tier with
no mark, the Super User, or the department's Admin for a department's restricted tier. A consent belongs to one flow and one mark (or tier), can expire, can be taken back, and
makes the flow's destination folders a place that content may be, so Restricted does not report the copies there. Nothing is consented to silently: "propose, never silently resolve".
The copies a consented flow makes are still marked content: a second flow carrying them onward needs its own consent.

When something turns restricted under a running flow (a mark is made), that flow is paused at once (`sweep`) and the owner asked, not left to find out file by file.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from engine.resource.resource import derive_tag

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

RESTRICTED_TAGS = ("restricted", "admin")           # the admin tier is above restricted: a flow does not touch it either, without consent
PAUSE = "restricted:consent"
REFUSED_EVERY = 600.0                               # a flow says it is waiting to the person who made it at most once in this long per file
_told: dict[tuple[int, str], float] = {}


def reset_state() -> None:
    _told.clear()


def _norm(path: str) -> str:
    return path.replace("\\", "/").rstrip("/").lower()


def _covers(mark: dict[str, Any], path: str) -> bool:
    m, p = _norm(mark["path"]), _norm(path)
    return p == m or (mark["kind"] == "folder" and p.startswith(m + "/"))


@dataclass(frozen=True)
class Blocker:
    kind: str                                       # "mark" | "tag"
    name: str
    reason: str
    mark_id: int | None = None
    tag: str | None = None
    scope_department_id: int | None = None
    owner_account_id: int | None = None             # who marked it
    where: str = ""

    def key(self) -> tuple[Any, ...]:
        return ("mark", self.mark_id) if self.kind == "mark" else ("tag", self.tag, self.scope_department_id or 0)


async def blockers(engine: Engine, pc_id: int | None, path: str, digest: str | None = None) -> list[Blocker]:
    """Everything that makes this file or folder restricted. Always asks the current state."""
    if pc_id is None or not path:
        return []
    db = engine.db
    found: dict[tuple[Any, ...], Blocker] = {}

    def add(b: Blocker) -> None:
        found.setdefault(b.key(), b)

    entry = await db.file_index.by_path(pc_id, path)
    if entry is not None and entry.get("resource_tag") in RESTRICTED_TAGS:
        add(Blocker("tag", entry["resource_tag"], f"it is tagged {entry['resource_tag']}", tag=entry["resource_tag"],
                    scope_department_id=entry.get("resource_tag_scope_department_id"), where=path))
    pc = await db.accounts.pc(pc_id) or {}
    tier = derive_tag(path, str(pc.get("pc_type") or ""), pc.get("department_id"))
    if tier is not None and tier[0] in RESTRICTED_TAGS:
        add(Blocker("tag", tier[0], f"it is in the {tier[0]} tier folder", tag=tier[0], scope_department_id=tier[1], where=path))
    for mark in await db.marks.active_on_pc(pc_id):
        if _covers(mark, path):
            what = f"{mark['name']} is marked restricted" if mark["kind"] == "file" else f"the folder {mark['name']} is marked restricted"
            add(Blocker("mark", mark["name"], what, mark_id=mark["id"], owner_account_id=mark.get("by_account_id"), where=path))
    content = digest or (entry or {}).get("content_hash")
    if content:
        for mark in await db.marks.active_with_hash(content):
            add(Blocker("mark", mark["name"], f"its content is a copy of {mark['name']}, which is marked restricted", mark_id=mark["id"],
                        owner_account_id=mark.get("by_account_id"), where=path))
    return list(found.values())


async def restricted_reason(engine: Engine, pc_id: int | None, path: str, digest: str | None = None) -> str | None:
    """Why this is restricted (the first reason), or None."""
    found = await blockers(engine, pc_id, path, digest)
    return found[0].reason if found else None


def _live(consent: dict[str, Any], now: datetime) -> bool:
    return consent["state"] == "granted" and (consent.get("expires_at") is None or consent["expires_at"] > now)


def _consented(b: Blocker, consents: list[dict[str, Any]]) -> bool:
    now = datetime.now(timezone.utc)
    for c in consents:
        if not _live(c, now):
            continue
        if b.kind == "mark" and c.get("mark_id") == b.mark_id:
            return True
        if b.kind == "tag" and c.get("tag") == b.tag and (c.get("scope_department_id") or 0) == (b.scope_department_id or 0):
            return True
    return False


async def unconsented(engine: Engine, flow_id: int, pc_id: int | None, path: str, digest: str | None = None) -> list[Blocker]:
    """What stands in the way of this flow carrying this file or folder: blockers nobody has consented to for this flow."""
    found = await blockers(engine, pc_id, path, digest)
    if not found:
        return []
    await expire(engine, flow_id)
    consents = await engine.db.flows.consents(flow_id, states=("granted",))
    return [b for b in found if not _consented(b, consents)]


async def expire(engine: Engine, flow_id: int) -> None:
    """A consent whose time has run out is taken back, and the places it allowed with it."""
    for c in await engine.db.flows.consents(flow_id, states=("granted",)):
        if c.get("expires_at") is not None and c["expires_at"] <= datetime.now(timezone.utc):
            await engine.db.flows.decide_consent(c["id"], "revoked", c["decided_by_account_id"] or 0, c["expires_at"], "it expired")
            await engine.db.resource.revoke_allowances(c["id"])
            await engine.audit.record(None, "flow.restricted_expired", target_type="flows", target_id=flow_id, detail={"consent_id": c["id"], "name": c["name"]})


async def gate(engine: Engine, flow_id: int, pc_id: int | None, path: str, digest: str | None = None, *, step: str) -> bool:
    """May the flow touch this? True when nothing restricted is in the way (or everything in the way has been consented to). Otherwise the flow is paused, the owners are asked, and
    False is returned: the flow does not go on."""
    missing = await unconsented(engine, flow_id, pc_id, path, digest)
    if not missing:
        return True
    await request(engine, flow_id, missing, path, step=step)
    return False


def deciders_text(b: Blocker) -> str:
    return "the person who marked it, or the Super User" if b.kind == "mark" else "the Super User" if b.tag == "admin" or not b.scope_department_id else "the department's Admin, or the Super User"


async def request(engine: Engine, flow_id: int, missing: list[Blocker], path: str, *, step: str) -> None:
    """Pause the flow and ask the owner(s). Asking is once per flow and thing; the audit trail has every time the flow was held."""
    flow = await engine.db.flows.get(flow_id)
    if flow is None or flow["status"] == "inactive":
        return
    if flow["status"] == "active" or flow["status"] == "paused" and flow.get("pause_reason") in (None, ""):
        await engine.db.flows.set_status(flow_id, "paused", PAUSE)
    for b in missing:
        await engine.audit.record(None, "flow.held_restricted", target_type="flows", target_id=flow_id, pc_id=flow["source_pc_id"], detail={"path": path, "why": b.reason, "at": step})
        cid, new = await engine.db.flows.ask_consent(flow_id, mark_id=b.mark_id, tag=b.tag, scope_department_id=b.scope_department_id, name=b.name, sample_path=path)
        if not new:
            continue
        await engine.audit.record(None, "flow.restricted_asked", target_type="flows", target_id=flow_id, detail={"consent_id": cid, "name": b.name, "why": b.reason, "sample": path})
        note = {"flow_id": flow_id, "consent_id": cid, "name": b.name, "why": b.reason, "sample": path, "decides": deciders_text(b)}
        from engine.console import issues

        issue_id, _ = await issues.raise_issue(
            engine, type_="flow", severity="medium", title="A flow wants to carry something restricted", subject=f"{b.name}: flow #{flow_id}", pc_id=flow["source_pc_id"],
            source_table="flow_restricted", source_id=cid, owner_account_id=b.owner_account_id, state="waiting", label="Waiting for consent",
            detail={"flow_id": flow_id, "consent_id": cid, "restricted": b.name, "why": b.reason, "sample": path, "decides": deciders_text(b)})
        await engine.db.flows.set_consent_issue(cid, issue_id)
        if b.owner_account_id is not None:
            await engine.push_to_account(b.owner_account_id, "flow.restricted_request", note)
        await engine.push_to_role("super_user", "flow.restricted_request", note)
        if b.kind == "tag" and b.scope_department_id:
            await engine.push_to_role("admin", "flow.restricted_request", note, department_id=b.scope_department_id)
    key = (flow_id, _norm(path))
    now = time.monotonic()
    if len(_told) > 5000:                                                # bounded: what was said long ago is said again if it is still true
        for k in [k for k, t in _told.items() if now - t > REFUSED_EVERY][:2500]:
            _told.pop(k, None)
    if now - _told.get(key, -1e9) >= REFUSED_EVERY:
        _told[key] = now
        await engine.push_to_account(flow["created_by_account_id"], "flow.refused",
                                     {"flow_id": flow_id, "path": path, "why": missing[0].reason, "waiting_for": deciders_text(missing[0])})


def install(engine: Engine) -> None:
    """The flow side of the spine: when something becomes restricted anywhere, every flow through it stops and asks (not a call from the Restricted code into Flow's: an event)."""
    from engine.bus import Event

    async def on_marked(event: Event) -> None:
        event.facts["flows_held"] = await sweep(engine, event.data["pc_id"])

    engine.bus.on(("mark.created", "mark.followed"), on_marked, stage="act", name="flow.marked")

    async def on_flow(event: Event) -> None:
        from engine.flow import sync

        sync._routes.clear()                               # which folders flows read from and write to has changed

    engine.bus.on("flow.*", on_flow, stage="heat", name="flow.routes")


def can_decide(ident: Any, consent: dict[str, Any]) -> bool:
    """Who may answer: the Super User always; the person who made the mark; for a department's restricted tier, that department's Admin."""
    if ident.role == "super_user":
        return True
    if consent.get("mark_id") is not None:
        return consent.get("mark_owner_account_id") == ident.account_id
    return bool(consent.get("tag") == "restricted" and consent.get("scope_department_id") and ident.role == "admin" and ident.department_id == consent["scope_department_id"])


async def sweep(engine: Engine, pc_id: int) -> int:
    """Something on this machine just became restricted (a mark): pause every flow whose source or destination folder is now restricted without consent, and ask."""
    if not engine.db.connected:
        return 0
    held = 0
    for row in await engine.db.flows.list_all():
        if row["status"] != "active":
            continue
        flow = await engine.db.flows.get(row["id"])
        if flow is None:
            continue
        ends = []
        if flow["source_pc_id"] == pc_id:
            ends.append((pc_id, flow["source_path"]))
        ends += [(d["destination_pc_id"], d["destination_path"]) for d in flow["destinations"] if d.get("destination_pc_id") == pc_id]
        stopped = False
        for pc, path in ends:
            missing = await unconsented(engine, flow["id"], pc, path)
            if missing:
                await request(engine, flow["id"], missing, path, step="when it became restricted")
                stopped = True
        held += int(stopped)
    return held
