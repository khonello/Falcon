"""Resource tiers and compliance (Resource -> Folder Structure, Access Control Rules,
Restricted File Tracking, Compliance & Enforcement).

    Super User PC   /resources/{admin,restricted,common}
    Admin PC        /resources/{restricted,workers,common}
    Worker PC       /resources/            (flat)

Tags: admin | restricted | worker-dept-<id> | common. `admin` and `restricted` files are
tracked by content hash; a copy appearing where its tier doesn't permit is a violation --
logged as a warning, that one file ignored going forward, surfaced to the affected user,
raised as a routable Report. Never auto-deleted.

Detection reuses the Global File Index event stream (native-first, polling fallback).
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler, stub

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

TIER_FOLDERS = {
    "super_user_workstation": ("admin", "restricted", "common"),
    "admin_workstation": ("restricted", "workers", "common"),
    "client_pc": (),  # flat
}


def tag_allowed_on(tag: str, pc_type: str, pc_department_id: int | None) -> bool:
    """Access Control Rules table, as a predicate."""
    if tag == "common":
        return True
    if tag == "admin":
        return pc_type == "super_user_workstation"
    if tag == "restricted":
        return pc_type in ("super_user_workstation", "admin_workstation")
    if tag.startswith("worker-dept-"):
        dept = int(tag.rsplit("-", 1)[1])
        return pc_type in ("admin_workstation", "client_pc") and pc_department_id == dept
    return False


def allowed_tags_for(role: str, department_id: int | None) -> list[str]:
    """What a caller may see in Assistance search / Task target search."""
    tags = ["common"]
    if role in ("admin", "super_user"):
        tags.append("restricted")
    if role == "super_user":
        tags.append("admin")
    if department_id is not None:
        tags.append(f"worker-dept-{department_id}")
    return tags


def install(engine: Engine) -> None:
    engine.file_index.subscribe(_on_file_event)


async def _on_file_event(event: dict[str, Any]) -> None:
    # SCAFFOLD: if event.hash matches an admin/restricted-tagged entry and
    # not tag_allowed_on(tag, pc_type, dept) -> record violation, ignore file, notify user,
    # reports.emit('resource_violation', ...).
    log.debug("resource compliance: file event %s", event.get("op"))


@handler("resource.violations")
async def violations(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    return stub("resource.violations", payload)


@handler("resource.tag")
async def tag(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    """Assign/confirm a file's access tag (derived from the folder it sits in)."""
    return stub("resource.tag", payload)
