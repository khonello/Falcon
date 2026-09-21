"""Decomposed question graph (spec 7.2.1) -- NOT one open-ended structuring call.

Four independent root branches, each a chain of narrow yes/no / pick-from-list / short-extract
questions. The graph's branching IS the ambiguity detector: every non-clean leaf appends a flag,
and a flagged structure is surfaced to the assigner rather than committed.

    ROOT File?      -> name -> exists|not yet -> changing|present -> Intent -> path?
    ROOT Program?   -> name -> tied to file? -> closed? -> present-only? -> Intent
    ROOT Deadline?  -> one|more -> Final Deadline | flag ambiguous
    ROOT Multi-task -> propose split -> surface
    File=NO and Program=NO -> flag no target -> explicit "None?" confirmation

Every `LocalLLM` call may return None ("unclear"); that is treated as a flag, not an error.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from engine.task.verification import ProposedStructure, VerificationItem

if TYPE_CHECKING:
    from engine.llm import LocalLLM

log = logging.getLogger(__name__)


async def populate(llm: "LocalLLM", description: str) -> ProposedStructure:
    out = ProposedStructure()
    file_item = await _file_branch(llm, description, out)
    await _program_branch(llm, description, out, file_item)
    await _deadline_branch(llm, description, out)
    await _multitask_branch(llm, description, out)
    if not out.items and not any(f["kind"] == "no_target" for f in out.flags):
        out.flags.append({"kind": "no_target", "ask": "No verification target detected -- None?"})
    return out


def _unclear(out: ProposedStructure, question: str) -> None:
    out.flags.append({"kind": "unclear", "question": question})


# --- branches -----------------------------------------------------------------------------------

async def _file_branch(llm: "LocalLLM", text: str, out: ProposedStructure) -> VerificationItem | None:
    q = "Does the input mention a file target?"
    mentions = await llm.yes_no(q, text)
    if mentions is None:
        _unclear(out, q)
        return None
    if not mentions:
        return None
    name = await llm.extract("the file name mentioned", text)
    if not name:
        _unclear(out, "What file name is mentioned?")
        return None
    q = "Does the file already exist, or does it need creating?"
    state = await llm.choose(q, text, ["exists", "not yet"])
    if state == "exists":
        q = "Is the file being changed, or does it just need to be present?"
        mode = await llm.choose(q, text, ["changing", "present"])
        if mode == "changing":
            intent = "update"
        elif mode == "present":
            intent = "exists"
        else:
            _unclear(out, q)
            return None
        path = None
    elif state == "not yet":
        intent = "create"
        has_path = await llm.yes_no("Is a folder/path mentioned?", text)
        path = await llm.extract("the folder path mentioned", text) if has_path else None
    else:
        _unclear(out, q)
        return None
    item = VerificationItem(target_type="file", intent=intent, name=name, path=path)
    out.items.append(item)
    return item


async def _program_branch(llm: "LocalLLM", text: str, out: ProposedStructure,
                          file_item: VerificationItem | None) -> None:
    q = "Does the input mention a program target?"
    mentions = await llm.yes_no(q, text)
    if mentions is None:
        _unclear(out, q)
        return
    if not mentions:
        return
    name = await llm.extract("the program name mentioned", text)
    if not name:
        _unclear(out, "What program name is mentioned?")
        return
    tied = await llm.yes_no("Is its use tied to a specific file (e.g. 'use X to update Y')?", text)
    if tied:
        if file_item is None:
            out.flags.append({"kind": "contradiction",
                              "detail": "program is used with a file, but no file target was found"})
            return
        out.items.append(VerificationItem(target_type="program", intent="used_with_file", name=name,
                                          linked_item_index=out.items.index(file_item)))
        return
    closed = await llm.yes_no("Must it be closed / not running rather than used?", text)
    if closed:
        intent = "closed_not_running"
    else:
        present_only = await llm.yes_no("Does it just need to be present, not actively used?", text)
        intent = "installed_available" if present_only else "used"
    out.items.append(VerificationItem(target_type="program", intent=intent, name=name))


async def _deadline_branch(llm: "LocalLLM", text: str, out: ProposedStructure) -> None:
    q = "Does the input mention a deadline?"
    mentions = await llm.yes_no(q, text)
    if mentions is None:
        _unclear(out, q)
        return
    if not mentions:
        return
    count = await llm.choose("One date/time mentioned, or more than one?", text, ["one", "more"])
    if count == "one":
        out.final_deadline = await llm.extract("the deadline date/time", text)
    else:
        out.flags.append({"kind": "ambiguous_deadline"})


async def _multitask_branch(llm: "LocalLLM", text: str, out: ProposedStructure) -> None:
    multi = await llm.yes_no("Does the input describe more than one distinct piece of work?", text)
    if multi:
        # SCAFFOLD: propose a concrete split (draft tasks sharing common fields) and surface it.
        out.proposed_split = [{"description": text, "note": "split proposal not yet implemented"}]
