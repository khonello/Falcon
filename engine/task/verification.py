"""Verification items and Intent (Task -> Verification, Intent, Verification Stack).

Each item targets a File or a Program; its check is defined by the target's Intent:

    File:    create | update | exists
    Program: used | used_with_file | installed_available | closed_not_running

A Create-intent File target is name-first (path optional); its name is checked against the
Global File Index scoped to the assignee, and any collision is surfaced to the assigner --
never silently accepted, never guessed around.

The stack is transparency only: pass/fail per item is displayed, but the task is verified as a
whole unit by the assigner, never per item.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import PurePath
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from engine.server import Engine

TARGET_TYPES = ("file", "program")
FILE_INTENTS = ("create", "update", "exists")
PROGRAM_INTENTS = ("used", "used_with_file", "installed_available", "closed_not_running")
ITEM_STATUS = ("pending", "passed", "failed")


@dataclass
class VerificationItem:
    target_type: str            # 'file' | 'program'
    intent: str
    name: str                   # file name or program name (primary field, always required)
    path: str | None = None     # only if the assigner specified one
    linked_item_index: int | None = None  # used_with_file -> index of the File item it ties to
    file_index_id: int | None = None      # exists/update: the indexed file chosen by the assigner
    populated_by: str = "llm"
    status: str = "pending"

    def validate(self) -> list[str]:
        problems: list[str] = []
        if self.target_type not in TARGET_TYPES:
            problems.append(f"unknown target type {self.target_type!r}")
            return problems
        allowed = FILE_INTENTS if self.target_type == "file" else PROGRAM_INTENTS
        if self.intent not in allowed:
            problems.append(f"intent {self.intent!r} not valid for {self.target_type}")
        if not self.name:
            problems.append("name is required")
        if self.intent == "used_with_file" and self.linked_item_index is None:
            problems.append("used_with_file needs a linked File item")
        if self.populated_by not in ("llm", "manual"):
            problems.append("populated_by must be llm or manual")
        return problems

    @classmethod
    def from_payload(cls, d: dict[str, Any]) -> VerificationItem:
        return cls(
            target_type=str(d.get("target_type", "")),
            intent=str(d.get("intent", "")),
            name=str(d.get("name") or d.get("proposed_filename") or d.get("program_name") or "").strip(),
            path=(str(d["path"]).strip() or None) if d.get("path") else None,
            linked_item_index=d.get("linked_item_index"),
            file_index_id=d.get("file_index_id"),
            populated_by=str(d.get("populated_by", "manual")),
        )

    def to_row(self, sequence: int) -> dict[str, Any]:
        """The verification_items columns for TasksRepo.create."""
        row: dict[str, Any] = {"sequence": sequence, "target_type": self.target_type, "intent": self.intent,
                               "populated_by": self.populated_by}
        if self.target_type == "file":
            row.update(proposed_filename=self.name, proposed_path=self.path, file_index_id=self.file_index_id)
        else:
            row.update(program_name=self.name)
            if self.linked_item_index is not None:
                row["linked_file_sequence"] = self.linked_item_index + 1
        return row


@dataclass
class ProposedStructure:
    """What the LLM graph produces for the assigner to review. `flags` are the places where
    'surface to assigner' fired; a structure with flags cannot be committed as-is."""
    items: list[VerificationItem] = field(default_factory=list)
    final_deadline: str | None = None
    soft_deadline: str | None = None
    flags: list[dict[str, Any]] = field(default_factory=list)
    proposed_split: list[dict[str, Any]] | None = None  # multi-task detection

    def needs_assigner(self) -> bool:
        return bool(self.flags or self.proposed_split)


def validate_stack(items: list[VerificationItem]) -> list[str]:
    problems: list[str] = []
    for idx, item in enumerate(items):
        for p in item.validate():
            problems.append(f"item {idx + 1}: {p}")
        if item.intent == "used_with_file":
            link = item.linked_item_index
            if link is None or not (0 <= link < len(items)) or items[link].target_type != "file":
                problems.append(f"item {idx + 1}: linked_item_index must point at a File item")
    return problems


async def check_create_collisions(engine: Engine, items: list[VerificationItem],
                                  assignee_pc_id: int | None) -> list[dict[str, Any]]:
    """Name-first collision check for every Create-intent File item, scoped to the assignee's
    PC. A collision is resolved by the assigner supplying a path that does not collide, or a
    new name. May also reveal that Create was really Update."""
    collisions: list[dict[str, Any]] = []
    pc_ids = [assignee_pc_id] if assignee_pc_id is not None else None
    for idx, item in enumerate(items):
        if item.target_type != "file" or item.intent != "create":
            continue
        hits = await engine.file_index.name_collisions(item.name, pc_ids=pc_ids)
        if item.path:
            wanted = str(PurePath(item.path) / item.name).replace("\\", "/").lower()
            hits = [h for h in hits if h["path"].replace("\\", "/").lower() == wanted]
        if hits:
            collisions.append({"item_index": idx, "name": item.name, "path": item.path,
                               "existing": [{"path": h["path"], "pc_id": h["pc_id"]} for h in hits],
                               "hint": "a file with this name already exists -- give a path or a new name, "
                                       "or did you mean Update?"})
    return collisions


# --- stack evaluation ---------------------------------------------------------------------------

async def evaluate_item(engine: Engine, task: dict[str, Any], item: dict[str, Any]) -> str:
    """Derive pass/fail/pending for one item from index state and recorded signals.
    Display only -- never closes a task."""
    db = engine.db
    intent = item["intent"]
    if item["target_type"] == "file":
        if intent == "exists":
            return "passed" if item.get("file_index_id") and item.get("file_last_seen_at") else "pending"
        if intent == "create":
            return "passed" if item.get("file_index_id") else "pending"
        if intent == "update":
            sig = await db.tasks.latest_signal(item["id"], "file_modified")
            baseline = task.get("started_at") or task["created_at"]
            return "passed" if sig and sig["observed_at"] > baseline else "pending"
        return "pending"

    state = await db.tasks.latest_signal(item["id"], "process_state")
    if intent == "installed_available":
        present = await db.tasks.latest_signal(item["id"], "program_present")
        return "passed" if present and (present["value"] or {}).get("present") else "pending"
    if state is None:
        return "pending"
    value = state["value"] or {}
    if intent == "closed_not_running":
        return "passed" if not value.get("running") else "failed"
    if intent == "used":
        active = await db.tasks.latest_signal(item["id"], "process_active")
        return "passed" if active else "pending"
    if intent == "used_with_file":
        linked = await db.tasks.item(item["linked_file_verification_item_id"]) if item.get(
            "linked_file_verification_item_id") else None
        opened = await db.tasks.latest_signal(item["id"], "open_file_descriptor")
        if linked and opened:
            files = [str(f).replace("\\", "/").lower() for f in (opened["value"] or {}).get("open_files", [])]
            name = (linked.get("proposed_filename") or "").lower()
            if any(f.endswith("/" + name) or f == name for f in files):
                return "passed"
        return "pending"
    return "pending"


async def evaluate_stack(engine: Engine, task_id: int) -> list[dict[str, Any]]:
    """Recompute every item's status, persist changes, return the stack."""
    task = await engine.db.tasks.get(task_id)
    if task is None:
        return []
    for item in task["items"]:
        status = await evaluate_item(engine, task, item)
        if status != item["status"]:
            await engine.db.tasks.set_item_status(item["id"], status)
            item["status"] = status
    return task["items"]
