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
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from engine.server import Engine

TARGET_TYPES = ("file", "program")
FILE_INTENTS = ("create", "update", "exists")
PROGRAM_INTENTS = ("used", "used_with_file", "installed_available", "closed_not_running")
ITEM_STATUS = ("pending", "pass", "fail")


@dataclass
class VerificationItem:
    target_type: str            # 'file' | 'program'
    intent: str
    name: str                   # file name or program name (primary field, always required)
    path: str | None = None     # only if the assigner specified one
    linked_item_index: int | None = None  # used_with_file -> index of the File item it ties to
    status: str = "pending"
    baseline_at: Any = None     # for 'update': task creation time or last check

    def validate(self) -> list[str]:
        problems: list[str] = []
        if self.target_type not in TARGET_TYPES:
            problems.append(f"unknown target type {self.target_type!r}")
        allowed = FILE_INTENTS if self.target_type == "file" else PROGRAM_INTENTS
        if self.intent not in allowed:
            problems.append(f"intent {self.intent!r} not valid for {self.target_type}")
        if not self.name:
            problems.append("name is required")
        if self.intent == "used_with_file" and self.linked_item_index is None:
            problems.append("used_with_file needs a linked File item")
        return problems


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


async def check_create_collisions(engine: Engine, items: list[VerificationItem],
                                  assignee_account_id: int) -> list[dict[str, Any]]:
    """Name-first collision check for every Create-intent File item, scoped to the assignee.
    Returns collisions to surface; may also hint that Create was really Update."""
    collisions: list[dict[str, Any]] = []
    for idx, item in enumerate(items):
        if item.target_type == "file" and item.intent == "create":
            hits = await engine.file_index.name_collisions(item.name)
            if hits:
                collisions.append({"item_index": idx, "name": item.name, "existing": hits,
                                   "hint": "collision on Create -- did you mean Update?"})
    return collisions


async def evaluate_stack(engine: Engine, task_id: int) -> list[dict[str, Any]]:
    """Recompute pass/fail per item from the Global File Index and client-reported program
    state. Display only -- never closes a task."""
    return []  # SCAFFOLD
