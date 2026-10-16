"""Decomposed question graph (spec 7.2.1) -- NOT one open-ended structuring call.

The graph asks a small local model only the narrow questions it is reliably good at, and
answers the mechanical ones itself. Benchmarking small Qwen3 models on real descriptions
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

A held-out benchmark (scripts/llm_cases.py, never tuned against) drives all of this: the graph
scores 29/32 on unseen descriptions with Qwen3-1.7B, 24/32 with the 0.6B, and 13/24 with the
model removed entirely -- so both halves carry real weight. Three guards earn their keep,
each from a way a model got it confidently wrong:
  * a span the model extracts must not live inside a file name (backup-2026-09-28.bak really
    does contain a date),
  * a deadline the model finds on its own must be an unambiguous date or clock time, never a
    bare day word -- otherwise "the usual Friday things" grows a Friday deadline,
  * a lone capitalised noun is not a Program unless the text says something is done with one
    ("update the README", "into the Finance folder").
Never force an answer with a GBNF grammar: it masks the <think> token Qwen3 opens with, which
makes any model answer almost constantly. An answer that does not parse is the "unclear ->
surface to the assigner" signal; a forced well-formed guess is indistinguishable from a real
one, and the flags are what protect "propose, never silently resolve".
"""

from __future__ import annotations

import logging
import re
import time
import unicodedata
from datetime import datetime
from typing import TYPE_CHECKING

from common.when import resolve
from engine.task.hints import Hint
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
SPLIT_MARKERS = re.compile(r"\b(?:and also|as well as|plus)\b|\b(?:and\s+)?then\b|;", re.IGNORECASE)
WEEKDAYS = r"monday|tuesday|wednesday|thursday|friday|saturday|sunday"
# "deadline is 17:00" carries a deadline with no by/before in front of it, and a 24-hour
# time is as common in a workplace description as 3pm.
DEADLINE_RE = re.compile(
    r"\b(?:by|before|until|till|due|at|no later than|deadline(?:\s+is)?)\s+(?:the\s+)?"
    r"(?:end of (?:the )?(?:day|week|month)(?:\s+\w+)?"
    r"|\d{1,2}:\d{2}(?:\s*(?:am|pm))?\b(?:\s+(?:today|tomorrow|tonight|" + WEEKDAYS + r"))?"
    r"|\d{1,2}\s*(?:am|pm)\b(?:\s+(?:today|tomorrow|tonight|" + WEEKDAYS + r"))?"
    r"|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}(?:/\d{2,4})?"
    r"|(?:next\s+)?(?:" + WEEKDAYS + r")(?:\s+or\s+(?:" + WEEKDAYS + r"))?"
    r"|today|tonight|tomorrow|noon|midnight|\w+\s+\d{1,2}(?:st|nd|rd|th)?)",
    re.IGNORECASE)
TIME_WORD_RE = re.compile(r"\b(" + WEEKDAYS + r"|today|tonight|tomorrow|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}(?:/\d{2,4})?"
                          r"|\d{1,2}:\d{2}(?:\s*(?:am|pm))?|\d{1,2}\s*(?:am|pm))\b", re.IGNORECASE)
# An unambiguous point in time, with no bare day words: what the model is allowed to offer as
# a deadline it found on its own (a day word on its own is settled by position, mechanically).
HARD_TIME_RE = re.compile(r"\b(?:\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}(?:/\d{2,4})?"
                          r"|\d{1,2}:\d{2}(?:\s*(?:am|pm))?|\d{1,2}\s*(?:am|pm))\b", re.IGNORECASE)
# A bare time word is a deadline only in a deadline position: "... today", "on Monday,", "this Friday".
BARE_TIME_RE = re.compile(r"(?:\b(?:on|this|next)\s+)?\b(" + WEEKDAYS + r"|today|tonight|tomorrow)\b"
                          r"(?=\s*(?:[.,;!?]|$|or\b|whichever\b)|['’]s\s+(?:review|meeting|call|deadline|standup|presentation|session)\b)",
                          re.IGNORECASE)

# Verb cues that settle a file's Intent without asking the model (a mechanical reading).
CREATE_CUES = re.compile(r"\b(?:create[ds]?|write|written(?! to\b)|put together|makes?|made|produced?|prepared?|"
                         r"draft(?:ed)?|generate[ds]?|builds?|built|compiled?|convert(?:ed)?|"
                         r"save (?:it )?as|export(?:s|ed)?|archived?|zip(?:ped)?|back(?:s|ed)? up|backup|"
                         r"rename[ds]?\s+\S+\s+to)\b", re.IGNORECASE)
UPDATE_CUES = re.compile(r"\b(?:update|change|edit|modify|revise|fix|correct|refresh|keep \S+ current|fill in|"
                         r"add to|append)\b", re.IGNORECASE)
EXISTS_CUES = re.compile(r"(?:\b(?:make sure|ensure|check|confirm|verify)\b.{0,60}?\b(?:present|exists?|available|there|"
                         r"on your machine|in place|sitting|saved|filed|stored|uploaded|attached)\b)|"
                         r"(?:\b(?:must|has to|have to|should|needs? to)\s+be\s+(?:on|in|at|present|there|available|saved|stored|uploaded)\b)",
                         re.IGNORECASE)
# A file the work reads FROM is a target that must be there -- not one to produce.
# "Convert scan.tiff to scan.pdf": scan.tiff is Exists, only scan.pdf is Create.
SOURCE_CUES = re.compile(r"\b(?:convert|rename|from|out of|based on|starting from|using)\s+(?:the\s+)?$", re.IGNORECASE)
# Standalone capitalised token (Excel, 7-Zip, Outlook): not part of a file/path token.
CAP_WORD_RE = re.compile(r"(?<![\w/\\.-])([A-Z0-9][A-Za-z0-9+#-]*[A-Za-z][A-Za-z0-9+#-]*)(?![\w/\\.])")
DAY_WORD_RE = re.compile(r"\b(" + WEEKDAYS + r"|today|tonight|tomorrow|\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}(?:/\d{2,4})?)\b",
                         re.IGNORECASE)
CLAUSE_SPLIT = re.compile(r"[;,]|\band also\b|\b(?:and\s+)?then\b|\bas well as\b", re.IGNORECASE)

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
    "keep it running": "running",
}


# --- mechanical helpers -------------------------------------------------------------------------

def _verbatim(value: str | None, text: str) -> str | None:
    """A model-extracted span counts only if it is really in the text (no hallucinations)."""
    if not value:
        return None
    v = value.strip().strip("\"'`.,;:")
    return v if v and v.lower() in text.lower() and len(v) < len(text) else None


def _inside_file_name(span: str, text: str) -> bool:
    """True if `span` occurs in the text only as part of a file name."""
    if not span:
        return False
    stripped = text
    for name in find_file_names(text):
        stripped = stripped.replace(name, " ")
    return span.lower() in text.lower() and span.lower() not in stripped.lower()


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
    if SOURCE_CUES.search(before):
        return "exists"  # the file the work starts from must be there, not be produced
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
        if re.fullmatch(r"\d+(?:st|nd|rd|th)", word, re.IGNORECASE):
            continue  # "by the 14th" is a date, not a program
        if word[0].isdigit() and not re.search(r"[A-Za-z]{2,}", word):
            continue  # a number, not a product name like 7-Zip
        if any(word.lower() in f.lower() for f in file_names):
            continue
        rest = text[m.end():].lstrip()
        if any(rest.lower().startswith(f.lower()) for f in file_names):
            continue  # "the signed NDA nda-acme.pdf" -- a label on the file, not a program
        out.append(word)
    return out


INSTALL_CUES = re.compile(r"\b(?:install|installed|set up|setup|available|is there|present)\b", re.IGNORECASE)
CLOSE_CUES = re.compile(r"\b(?:close|closed|quit|exit|shut|shut down|shutdown|stop|not (?:be )?running|kill)\b",
                        re.IGNORECASE)
# A program can be named in lower case, and then the subject of a running/open predicate is
# the program: "the print spooler is still running", "the sync service stays open".
PROGRAM_SUBJECT_RE = re.compile(r"\bthe\s+((?:[\w-]+\s+){0,2}?[\w-]+?)\s+(?:is|are)\s+(?:still\s+)?"
                                r"(?:running|open)\b", re.IGNORECASE)
# "still running" / "keep it open" is the opposite check from "close it", and had no Intent
# to land on until `running` was added -- it used to come back as closed_not_running.
RUNNING_CUES = re.compile(r"\b(?:still running|is running|up and running"
                          r"|(?:keep|keeps|leave|leaves|stay|stays|remain|remains)\s+(?:\S+\s+){0,2}?"
                          r"(?:open|running))\b", re.IGNORECASE)


def program_intent_cue(text: str, program: str) -> str | None:
    """The clause around the program name usually says what happens with it; 'use' is the
    default the model is asked about, so only the unambiguous verbs are settled here."""
    idx = text.lower().find(program.lower())
    if idx < 0:
        return None
    before = CLAUSE_SPLIT.split(text[:idx])[-1][-60:]
    after = CLAUSE_SPLIT.split(text[idx + len(program):])[0][:60]
    clause = before + program + after
    if RUNNING_CUES.search(clause):
        return "running"  # checked first: "not running" would otherwise read as Close
    if CLOSE_CUES.search(before) or CLOSE_CUES.search(after[:20]):
        return "closed_not_running"
    if INSTALL_CUES.search(clause):
        return "installed_available"
    return None


# The lone-candidate fallback below only fires when the text says something is done with a
# program at all; otherwise any capitalised noun ("the README", "the Finance folder") would
# become a Program target on its own.
PROGRAM_VERBS = re.compile(r"\b(?:use|using|used|open|opens?|opened|run|runs?|running|launch|launche[ds]?|start|"
                           r"started|install|installed|close|closed|quit|exit|shut|shutdown|kill|stop|"
                           r"keep|leave|program|application|app)\b", re.IGNORECASE)


def mentions_use_on_file(text: str) -> bool:
    return re.search(r"\b(?:use|using|open)\b", text, re.IGNORECASE) is not None


# --- the graph ----------------------------------------------------------------------------------

MAX_DESCRIPTION = 2000          # characters read; the rest is said to have been left out, never silently dropped
MODEL_BUDGET_SECONDS = 75.0     # one proposal never keeps a person waiting longer than this on the model; the rest is flagged as unclear
_CONTROL = re.compile(r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f\u202a-\u202e\u2066-\u2069\u200b-\u200f\ufeff]")


def normalize(description: str) -> tuple[str, bool]:
    """The description as it is read: one Unicode form, no control or direction-changing characters, tidy spacing, a length the model can take.
    Returns (text, was_shortened)."""
    text = unicodedata.normalize("NFC", str(description or ""))
    text = _CONTROL.sub("", text).replace("\r\n", "\n").replace("\r", "\n")
    text = "\n".join(" ".join(line.split()) for line in text.split("\n"))
    text = re.sub(r"\n{3,}", "\n\n", text).strip()
    if len(text) > MAX_DESCRIPTION:
        cut = text[:MAX_DESCRIPTION]
        return (cut[:cut.rfind(" ")] if " " in cut[-60:] else cut).rstrip(), True
    return text, False


class _Budgeted:
    """The model for one proposal: when its time is used up, every further question comes back unclear and the graph flags it."""

    def __init__(self, llm: LocalLLM, seconds: float) -> None:
        self._llm, self._until = llm, time.monotonic() + seconds
        self.out_of_time = False

    @property
    def available(self) -> bool:
        return self._llm.available

    def _spent(self) -> bool:
        if time.monotonic() >= self._until:
            self.out_of_time = True
        return self.out_of_time

    async def yes_no(self, question: str, text: str) -> bool | None:
        return None if self._spent() else await self._llm.yes_no(question, text)

    async def choose(self, question: str, text: str, options: list[str]) -> str | None:
        return None if self._spent() else await self._llm.choose(question, text, options)

    async def extract(self, what: str, text: str) -> str | None:
        return None if self._spent() else await self._llm.extract(what, text)


async def populate(llm: LocalLLM, description: str, hints: list[Hint] | tuple[Hint, ...] = (), now: datetime | None = None) -> ProposedStructure:
    """Read a description into targets and a deadline. What the person marked outright (`hints`) is taken as given; patterns settle what they can;
    the model is asked only about what is left, within a time budget. Nothing is guessed: whatever is still unclear is a flag."""
    out = ProposedStructure()
    text, shortened = normalize(description)
    if shortened:
        out.flags.append({"kind": "too_long", "limit": MAX_DESCRIPTION, "detail": f"Only the first {MAX_DESCRIPTION} characters were read."})
        out.notes.append("the description was longer than could be read; the rest was left out")
    model = _Budgeted(llm, MODEL_BUDGET_SECONDS)
    if not llm.available:
        out.notes.append("the local model is not available: only what patterns and your marks settle was read")
    files = [h for h in hints if h.kind == "file"]
    programs = [h for h in hints if h.kind == "program"]
    folders = [h for h in hints if h.kind == "folder"]
    deadlines = [h for h in hints if h.kind == "deadline"]
    file_items = await _file_branch(model, text, out, files, folders)
    await _program_branch(model, text, out, file_items[0] if file_items else None, programs)
    await _deadline_branch(model, text, out, deadlines, now)
    if model.out_of_time:
        out.notes.append("the model ran out of time for this reading; what it did not answer is marked unclear")
    _multitask_branch(text, out, file_items)
    # A target whose Intent could not be settled is still a target -- "nothing was found" would
    # be a different and wrong thing to tell the assigner.
    if not out.items and not any(f["kind"] == "no_target" or f.get("target") for f in out.flags):
        out.flags.append({"kind": "no_target", "ask": "No verification target detected -- None?"})
    return out


def _unclear(out: ProposedStructure, question: str, *, target: str | None = None,
             options: list[str] | None = None) -> None:
    """The target is named on the flag so the assigner sees what was found but not understood."""
    flag: dict[str, object] = {"kind": "unclear", "question": question}
    if target:
        flag["target"] = target
    if options:
        flag["options"] = options
    out.flags.append(flag)


async def _file_branch(llm: LocalLLM, text: str, out: ProposedStructure, hints: list[Hint] = (),
                       folders: list[Hint] = ()) -> list[VerificationItem]:  # type: ignore[assignment]
    by_hint = {h.name.lower(): h for h in hints}
    names = [h.name for h in hints]                                   # what the person marked is a target, whether or not a pattern would have found it
    found_by = {n.lower(): "hint" for n in names}
    for n in find_file_names(text):
        if n.lower() not in found_by:
            names.append(n)
            found_by[n.lower()] = "rule"
    if not names:
        # Fallback: ask, but accept only a real file token that is in the text.
        guess = _verbatim(await llm.extract("the file name that the task is about", text), text)
        if guess and FILE_RE.fullmatch(guess):
            names = [guess]
            found_by[guess.lower()] = "model"
    items: list[VerificationItem] = []
    for name in names:
        hint = by_hint.get(name.lower())
        intent, intent_by = (hint.intent, "hint") if hint and hint.intent else (None, "")
        if intent is None:
            intent = file_intent_cue(text, name)
            intent_by = "rule"
        if intent is None:
            q = f"For the file {name}, does the task ask to:"
            choice = await llm.choose(q, text, list(FILE_INTENT_OPTIONS))
            if choice is None:
                _unclear(out, f"{q} {' / '.join(FILE_INTENT_OPTIONS)}",
                         target=name, options=list(FILE_INTENT_OPTIONS.values()))
                continue
            intent, intent_by = FILE_INTENT_OPTIONS[choice], "model"
        path = (hint.path if hint and hint.path else None)
        if path is None and intent == "create":
            path = find_path(text, name) or (folders[0].path if folders else None)
        item = VerificationItem(target_type="file", intent=intent, name=name, path=path, file_index_id=hint.file_index_id if hint else None,
                                source=found_by[name.lower()], intent_by=intent_by)
        out.items.append(item)
        items.append(item)
    return items


async def _program_branch(llm: LocalLLM, text: str, out: ProposedStructure,
                          file_item: VerificationItem | None, hints: list[Hint] = ()) -> None:  # type: ignore[assignment]
    if hints:                                                       # the person named the programs: nothing to find, and the model is not asked to
        for h in hints:
            await _one_program(llm, text, out, file_item, h.name, forced=h.intent, source="hint")
        return
    for name in await _program_names(llm, text, out):
        await _one_program(llm, text, out, file_item, name)


async def _program_names(llm: LocalLLM, text: str, out: ProposedStructure) -> list[str]:
    """Which programs the description is about. Several only when the text says mechanically
    what happens to each of them ("Shut Slack and Discord down") -- otherwise one at most,
    because every extra capitalised noun would become a Program target of its own."""
    file_names = [i.name for i in out.items if i.target_type == "file"]
    candidates = program_candidates(text, file_names)
    cued = [c for c in candidates if program_intent_cue(text, c) is not None]
    if len(cued) > 1:
        return cued
    name = _verbatim(await llm.extract("the name of the software program or application mentioned", text), text)
    if name is not None and name.lower() in (c.lower() for c in candidates):
        return [name]
    if not PROGRAM_VERBS.search(text):
        return []  # "update the README", "into the Finance folder" -- a capitalised word on its
        #            own is not a program unless the text says something is done with one
    # The model's answer must be a standalone capitalised token in the text (Excel, 7-Zip,
    # Acrobat Reader) -- otherwise fall back to the only such token, if there is exactly one.
    if len(candidates) == 1:
        return candidates
    # Nothing capitalised: a program can still be named in lower case ("the print spooler is
    # still running"), and the subject of a running/open predicate is the program.
    subject = PROGRAM_SUBJECT_RE.search(text)
    return [subject.group(1)] if subject else []


async def _one_program(llm: LocalLLM, text: str, out: ProposedStructure,
                       file_item: VerificationItem | None, name: str, *, forced: str | None = None, source: str = "rule") -> None:
    intent = forced or program_intent_cue(text, name)
    intent_by = "hint" if forced else "rule"
    if intent is None:
        q = f"What should happen with the program {name}?"
        choice = await llm.choose(q, text, list(PROGRAM_INTENT_OPTIONS))
        if choice is None:
            _unclear(out, f"{q} {' / '.join(PROGRAM_INTENT_OPTIONS)}",
                     target=name, options=list(PROGRAM_INTENT_OPTIONS.values()))
            return
        intent = PROGRAM_INTENT_OPTIONS[choice]
        intent_by = "model"
    if intent == "used" and file_item is not None and mentions_use_on_file(text) and not forced:
        intent = "used_with_file"  # "use X to update Y" ties the program to the file
    if intent == "used_with_file":
        if file_item is None:
            out.flags.append({"kind": "contradiction",
                              "detail": f"{name} is to be used on a file, but no file target was found"})
            return
        out.items.append(VerificationItem(target_type="program", intent=intent, name=name,
                                          linked_item_index=out.items.index(file_item), source=source, intent_by=intent_by))
        return
    out.items.append(VerificationItem(target_type="program", intent=intent, name=name, source=source, intent_by=intent_by))


def _set_deadline(out: ProposedStructure, role: str, phrase: str, at: str | None, said: str | None) -> None:
    if role == "soft":
        out.soft_deadline, out.soft_deadline_at, out.soft_said = phrase, at, said
    else:
        out.final_deadline, out.final_deadline_at, out.final_said = phrase, at, said


async def _deadline_branch(llm: LocalLLM, text: str, out: ProposedStructure, hints: list[Hint] = (),  # type: ignore[assignment]
                           now: datetime | None = None) -> None:
    for h in hints:                                              # a time the person set is the deadline: no finding, no flag
        _set_deadline(out, h.role or "final", h.when.said, h.when.at.isoformat(), h.when.said)  # type: ignore[union-attr]
        out.deadline_source = "hint"
    if any(h.role in (None, "final") for h in hints):
        return
    await _found_deadline(llm, text, out, now)


async def _found_deadline(llm: LocalLLM, text: str, out: ProposedStructure, now: datetime | None) -> None:
    await _deadline_phrase(llm, text, out)
    phrase = out.final_deadline
    if phrase and now is not None:
        when = resolve(phrase, now)
        if when:
            out.final_deadline_at, out.final_said = when.at.isoformat(), when.said
        else:
            out.flags.append({"kind": "unresolved_deadline", "phrase": phrase, "detail": f"“{phrase}” — {when.why}."})
    if phrase:
        out.deadline_source = out.deadline_source or "rule"


async def _deadline_phrase(llm: LocalLLM, text: str, out: ProposedStructure) -> None:
    phrases = find_deadlines(text)
    if not phrases:
        guess = _verbatim(await llm.extract("the deadline phrase saying when the task must be done", text), text)
        # backup-2026-09-28.bak really does contain "2026-09-28", so being verbatim is not
        # enough: a date living inside a file name is part of the name, not a deadline.
        if guess and _inside_file_name(guess, text):
            guess = None
        # And the model must produce an unambiguous date or clock time, not a bare day word:
        # "the usual Friday things" names no deadline, but a model will happily offer "Friday".
        # A day word in a real deadline position is found mechanically above, not here.
        phrases = [guess] if guess and HARD_TIME_RE.search(guess) else []
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
