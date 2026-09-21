"""Decomposed question graph (spec 7.2.1) -- NOT one open-ended structuring call.

The graph asks a small local model only the narrow questions it is reliably good at, and
answers the mechanical ones itself. Benchmarking Qwen3-0.6B on real descriptions
(scripts/llm_benchmark.py) showed that a model this size:
  * answers YES to every presence question and "one" to every count question (bias), but
  * picks correctly from a short finite list, and
  * extracts a name that is actually in the text -- while hallucinating names that appear
    as examples in the prompt.

So: file names are found by their extension (a mechanical fact) and a verb cue in the same
clause settles the Intent when there is one; otherwise the model picks the Intent from a
list. The program name is the model's extraction, accepted only if it is a standalone
capitalised token in the text (no hallucinations); the model then picks the program Intent.
Deadline phrases are found by pattern, with the model as a verbatim-checked fallback; two
candidate dates or an "or" inside the phrase is an ambiguous deadline. Several distinct file
targets joined by "and also / and then / ; / as well as" become a proposed split.

Every non-clean leaf appends a flag -- an unclear answer, a contradiction, no target at all --
and a flagged structure is surfaced to the assigner, never committed. Nothing is guessed.
"""

from __future__ import annotations

import logging
import re
from typing import TYPE_CHECKING

from engine.task.verification import ProposedStructure, VerificationItem

if TYPE_CHECKING:
    from engine.llm import LocalLLM

log = logging.getLogger(__name__)

FILE_RE = re.compile(r"(?<![\w/\\.-])([\w][\w\-.]*\.(?:[a-z][a-z0-9]{1,4}|[0-9][a-z][a-z0-9]{0,3}))(?![\w.])",
                     re.IGNORECASE)
PATH_RE = re.compile(
    r"(?:\b(?:in|into|under|to|inside)\s+(?:the\s+)?)((?:[A-Za-z]:)?[\w\-.~]+(?:[\\/][\w\-.~]+)+)", re.IGNORECASE)
FOLDER_RE = re.compile(r"\b(?:in|into|under|inside)\s+(?:the\s+)?([\w\-]+(?:[\\/][\w\-]+)*)\s+(?:folder|directory)\b",
                       re.IGNORECASE)
SPLIT_MARKERS = re.compile(r"\b(?:and also|and then|as well as|plus)\b|;", re.IGNORECASE)
WEEKDAYS = r"monday|tuesday|wednesday|thursday|friday|saturday|sunday"
DEADLINE_RE = re.compile(
    r"\b(?:by|before|until|till|due|no later than)\s+(?:the\s+)?(?:end of (?:the )?(?:day|week|month)(?:\s+\w+)?"
    r"|\d{1,2}(?::\d{2})?\s*(?:am|pm)\b(?:\s+(?:today|tomorrow|tonight|" + WEEKDAYS + r"))?"
    r"|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}(?:/\d{2,4})?"
    r"|(?:next\s+)?(?:" + WEEKDAYS + r")(?:\s+or\s+(?:" + WEEKDAYS + r"))?"
    r"|today|tonight|tomorrow|noon|midnight|\w+\s+\d{1,2}(?:st|nd|rd|th)?)",
    re.IGNORECASE)
TIME_WORD_RE = re.compile(r"\b(" + WEEKDAYS + r"|today|tonight|tomorrow|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}(?:/\d{2,4})?"
                          r"|\d{1,2}(?::\d{2})?\s*(?:am|pm))\b", re.IGNORECASE)
# A bare time word is a deadline only in a deadline position: "... today", "on Monday,", "this Friday".
BARE_TIME_RE = re.compile(r"(?:\b(?:on|this|next)\s+)?\b(" + WEEKDAYS + r"|today|tonight|tomorrow)\b"
                          r"(?=\s*(?:[.,;!?]|$|or\b|whichever\b))", re.IGNORECASE)

# Verb cues that settle a file's Intent without asking the model (a mechanical reading).
CREATE_CUES = re.compile(r"\b(?:create|write|put together|make|produce|prepare|draft|generate|build|compile|"
                         r"save (?:it )?as|export|archive|zip)\b", re.IGNORECASE)
UPDATE_CUES = re.compile(r"\b(?:update|change|edit|modify|revise|fix|correct|refresh|keep \S+ current|fill in|"
                         r"add to|append)\b", re.IGNORECASE)
EXISTS_CUES = re.compile(r"\b(?:make sure|ensure|check|confirm|verify)\b.{0,60}?\b(?:present|exists?|available|there|"
                         r"on your machine|in place)\b", re.IGNORECASE)
# Standalone capitalised token (Excel, 7-Zip, Outlook): not part of a file/path token.
CAP_WORD_RE = re.compile(r"(?<![\w/\\.-])([A-Z0-9][A-Za-z0-9+#-]*[A-Za-z][A-Za-z0-9+#-]*)(?![\w/\\.])")
DAY_WORD_RE = re.compile(r"\b(" + WEEKDAYS + r"|today|tonight|tomorrow|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}(?:/\d{2,4})?)\b",
                         re.IGNORECASE)
CLAUSE_SPLIT = re.compile(r"[;,]|\band also\b|\band then\b|\bas well as\b", re.IGNORECASE)

FILE_INTENT_OPTIONS = {
    "create a new file": "create",
    "change an existing file": "update",
    "only check that it exists": "exists",
}
PROGRAM_INTENT_OPTIONS = {
    "use it": "used",
    "use it on the file": "used_with_file",
    "have it installed": "installed_available",
    "close it": "closed_not_running",
}


# --- mechanical helpers -------------------------------------------------------------------------

def _verbatim(value: str | None, text: str) -> str | None:
    """A model-extracted span counts only if it is really in the text (no hallucinations)."""
    if not value:
        return None
    v = value.strip().strip("\"'`.,;:")
    return v if v and v.lower() in text.lower() and len(v) < len(text) else None


def find_file_names(text: str) -> list[str]:
    seen: list[str] = []
    for m in FILE_RE.finditer(text):
        name = m.group(1).strip()
        if name.lower() not in (s.lower() for s in seen):
            seen.append(name)
    return seen


def find_path(text: str, filename: str) -> str | None:
    for m in PATH_RE.finditer(text):
        p = m.group(1).rstrip("/\\")
        if p.lower() != filename.lower() and not p.lower().endswith(filename.lower()):
            return p
    m = FOLDER_RE.search(text)
    return m.group(1) if m else None


def find_deadlines(text: str) -> list[str]:
    phrases = [m.group(0).strip() for m in DEADLINE_RE.finditer(text)]
    if phrases:
        return phrases
    # A bare time word still reads as a deadline when it sits where a deadline would
    # ("Close Outlook today", "hand it in on Monday.") -- not "the usual Friday things".
    return [m.group(0).strip() for m in BARE_TIME_RE.finditer(text)]


def file_intent_cue(text: str, filename: str) -> str | None:
    """The clause around the file name usually says what happens to it."""
    idx = text.lower().find(filename.lower())
    if idx < 0:
        return None
    # Only the clause the file sits in: "Update a.xlsx and also archive ... into b.zip" must not
    # read "update" for b.zip.
    before = CLAUSE_SPLIT.split(text[:idx])[-1][-80:]
    after = CLAUSE_SPLIT.split(text[idx + len(filename):])[0][:60]
    if EXISTS_CUES.search(before + filename + after):
        return "exists"
    for window in (before, after):
        if UPDATE_CUES.search(window):
            return "update"
        if CREATE_CUES.search(window):
            return "create"
    return None


def program_candidates(text: str, file_names: list[str]) -> list[str]:
    """Standalone capitalised tokens that are not the sentence start, a file, or a time word."""
    out: list[str] = []
    for m in CAP_WORD_RE.finditer(text):
        word = m.group(1)
        if m.start() == 0 or TIME_WORD_RE.fullmatch(word) or re.fullmatch(r"[A-Z]\d+", word):
            continue
        if word[0].isdigit() and not re.search(r"[A-Za-z]{2,}", word):
            continue  # a number, not a product name like 7-Zip
        if any(word.lower() in f.lower() for f in file_names):
            continue
        out.append(word)
    return out


def mentions_use_on_file(text: str) -> bool:
    return re.search(r"\b(?:use|using|open)\b", text, re.IGNORECASE) is not None


# --- the graph ----------------------------------------------------------------------------------

async def populate(llm: LocalLLM, description: str) -> ProposedStructure:
    out = ProposedStructure()
    text = description.strip()
    file_items = await _file_branch(llm, text, out)
    await _program_branch(llm, text, out, file_items[0] if file_items else None)
    await _deadline_branch(llm, text, out)
    _multitask_branch(text, out, file_items)
    if not out.items and not any(f["kind"] == "no_target" for f in out.flags):
        out.flags.append({"kind": "no_target", "ask": "No verification target detected -- None?"})
    return out


def _unclear(out: ProposedStructure, question: str) -> None:
    out.flags.append({"kind": "unclear", "question": question})


async def _file_branch(llm: LocalLLM, text: str, out: ProposedStructure) -> list[VerificationItem]:
    names = find_file_names(text)
    if not names:
        # Fallback: ask, but accept only a real file token that is in the text.
        guess = _verbatim(await llm.extract("the file name that the task is about", text), text)
        if guess and FILE_RE.fullmatch(guess):
            names = [guess]
    items: list[VerificationItem] = []
    for name in names:
        intent = file_intent_cue(text, name)
        if intent is None:
            q = f"For the file {name}, does the task ask to:"
            choice = await llm.choose(q, text, list(FILE_INTENT_OPTIONS))
            if choice is None:
                _unclear(out, f"{q} {' / '.join(FILE_INTENT_OPTIONS)}")
                continue
            intent = FILE_INTENT_OPTIONS[choice]
        path = find_path(text, name) if intent == "create" else None
        item = VerificationItem(target_type="file", intent=intent, name=name, path=path)
        out.items.append(item)
        items.append(item)
    return items


async def _program_branch(llm: LocalLLM, text: str, out: ProposedStructure,
                          file_item: VerificationItem | None) -> None:
    file_names = [i.name for i in out.items if i.target_type == "file"]
    candidates = program_candidates(text, file_names)
    name = _verbatim(await llm.extract("the name of the software program or application mentioned", text), text)
    if name is None or name.lower() not in (c.lower() for c in candidates):
        # The model's answer must be a standalone capitalised token in the text (Excel, 7-Zip,
        # Acrobat Reader) -- otherwise fall back to the only such token, if there is exactly one.
        name = candidates[0] if len(candidates) == 1 else None
    if not name:
        return  # no program target -- silence here is fine; the file branch carries the task
    q = f"What should happen with the program {name}?"
    choice = await llm.choose(q, text, list(PROGRAM_INTENT_OPTIONS))
    if choice is None:
        _unclear(out, f"{q} {' / '.join(PROGRAM_INTENT_OPTIONS)}")
        return
    intent = PROGRAM_INTENT_OPTIONS[choice]
    if intent == "used" and file_item is not None and mentions_use_on_file(text):
        intent = "used_with_file"  # "use X to update Y" ties the program to the file
    if intent == "used_with_file":
        if file_item is None:
            out.flags.append({"kind": "contradiction",
                              "detail": f"{name} is to be used on a file, but no file target was found"})
            return
        out.items.append(VerificationItem(target_type="program", intent=intent, name=name,
                                          linked_item_index=out.items.index(file_item)))
        return
    out.items.append(VerificationItem(target_type="program", intent=intent, name=name))


async def _deadline_branch(llm: LocalLLM, text: str, out: ProposedStructure) -> None:
    phrases = find_deadlines(text)
    if not phrases:
        guess = _verbatim(await llm.extract("the deadline phrase saying when the task must be done", text), text)
        phrases = [guess] if guess and TIME_WORD_RE.search(guess) else []
    if not phrases:
        return
    day_words = {w.lower() for p in phrases for w in DAY_WORD_RE.findall(p)}
    if len(phrases) > 1 or len(day_words) > 1 or re.search(r"\bor\b", phrases[0], re.IGNORECASE):
        out.flags.append({"kind": "ambiguous_deadline", "candidates": phrases})
        return
    out.final_deadline = phrases[0]


def _multitask_branch(text: str, out: ProposedStructure, file_items: list[VerificationItem]) -> None:
    if len(file_items) >= 2 and SPLIT_MARKERS.search(text):
        parts = [p.strip(" ,.") for p in SPLIT_MARKERS.split(text) if p and p.strip(" ,.")]
        split = [{"description": part, "targets": [i.name for i in file_items if i.name.lower() in part.lower()]}
                 for part in parts]
        out.proposed_split = split if len(split) >= 2 else [{"description": text,
                                                             "targets": [i.name for i in file_items]}]
