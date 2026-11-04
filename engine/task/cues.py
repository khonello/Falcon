"""What a description asks that Falcon cannot read as a target: found by pattern, said to the assigner (the user, 4 Nov 2026).

Real descriptions are not clean sentences. People write as if to a colleague, and may assume the system works the rest out ("when you finish, use it to create the
annual report, a flow will pick it up"). This does not remove a word: every word stays, and these patterns look for what would go wrong. Each finding is a flag on the
proposal, in words the assigner can act on. Nothing is guessed, and the model is not asked.

    cannot_check        a message channel, another task, a flow: Falcon checks files and programs, so this part is the assigner's to confirm
    unnamed_result      something is to be made, and nothing names it: what will it be called?
    made_from           "combine a and b": they are what it is made from, so they must exist; they are not what is made
    ambiguous_deadline  "today or a day after": two deadlines; neither is picked. Says so when one lands on a weekend (holidays need a calendar Falcon does not have)
    waits_on_event      "when the reports come in": it starts on something, not on a date
    depends_on_check    "check if .. if not ..": what is to be done depends on what is found
    folder_guess        "the document folder": a folder described, not given
    quality_unseen      "redo it", "missing key details": Falcon sees that a file changed, never whether it is better
    inside_file         "the salary column is in report.xlsx": Falcon sees the file, not what is in it; the file is checked to exist, the rest is the assigner's
    recurring           "every day": a task is done once; a repeating job is not one task
    not_a_task          a question, a test, or a request for a task: nothing to give anyone. Said at once, with an example, and the model is not asked (`not_a_task`)

Two readings are settled here too, where a pattern is surer than the model: "work on a file" means it is there already (update), and a check of what is inside a
file changes nothing (exists).
"""

from __future__ import annotations

import re
from datetime import datetime, timedelta
from typing import Any

MAKE = re.compile(r"\b(creat\w*|combin\w*|merg\w*|make|produc\w*|generat\w*|build|prepare)\b", re.IGNORECASE)
COMBINE = re.compile(r"\b(combin\w*|merg\w*|put together)\b", re.IGNORECASE)
UNNAMED = re.compile(r"\b(?:(?:a|an)\s+(?:suitable|new|single|proper)\s+\w+"
                     r"|(?:the|an?)\s+(?:annual|yearly|monthly|weekly|quarterly)\s+\w+"
                     r"|into\s+(?:an?\s+)?(?:pdf|docx|xlsx|pptx|word|excel)\b)", re.IGNORECASE)
CANNOT_CHECK = (
    (re.compile(r"\b(?:message channel|send (?:it|them|this|that) to me|message me|email (?:it|them|me)|tell me|let me know)\b", re.IGNORECASE), "sending it to someone"),
    (re.compile(r"\b(?:the|that|this) task (?:i|we) (?:gave|assigned)\b|\b(?:the|that) (?:other|earlier|last|previous) task\b", re.IGNORECASE), "another task"),
    (re.compile(r"\b(?:a|the) flow will\b|\bflow (?:will )?picks? (?:it|them) up\b", re.IGNORECASE), "a flow picking it up"),
)
TWO_DEADLINES = re.compile(r"\b(today|tonight|tomorrow|this week|(?:mon|tues|wednes|thurs|fri|satur|sun)day)\s+or\s+(a day after|the day after|the next day|tomorrow|"
                           r"(?:mon|tues|wednes|thurs|fri|satur|sun)day)\b", re.IGNORECASE)
NEXT_DAY = ("a day after", "the day after", "the next day", "tomorrow")
WAITS = re.compile(r"\b(?:when|once|as soon as|after)\s+(?:the\s+|you\s+|your\s+)?[\w-]*\s*(?:comes? in|arrives?|is ready|are ready|finish(?:es)?|is done|are done|lands?)\b", re.IGNORECASE)
QUALITY = re.compile(r"\b(redo|re-do|rewrite|missing (?:\w+ )?(?:details?|information|parts?)|improve|make it better|not good enough|garbage|fix it up)\b", re.IGNORECASE)
INSIDE = re.compile(r"\b(?:check|verify|confirm|be sure|make sure|ensure)\b.*?\b(\w+ (?:column|sheet|tab|row|section|field|paragraph|page|chapter|table))\b", re.IGNORECASE)
WORK_ON = re.compile(r"\bwork(?:ing)? on\b", re.IGNORECASE)
RECURRING = re.compile(r"\b(every\s?day|every (?:morning|evening|night|week|month|monday|tuesday|wednesday|thursday|friday)|each (?:day|morning|week)|(?:daily|weekly)(?=[.,]|$))\b", re.IGNORECASE)
QUESTION = re.compile(r"^\s*(?:how|why|what|does|is this|is it|are you|can you|could you)\b|\?\s*$", re.IGNORECASE)
TESTING = re.compile(r"^\s*(?:this is a\s+)?test(?:ing)?\b|,\s*test(?:ing)?\s*$", re.IGNORECASE)
ASKS_FOR_A_TASK = re.compile(r"\b(?:create|make|give|add|write)\b(?:\s+\w+){0,3}?\s+task\b", re.IGNORECASE)
EXAMPLE = "A task names a file or a program and what should happen to it, like “Update sales.xlsx by Friday”."
HELP: dict[str, Any] = {
    "title": "How to write a task",
    "says": "Write what should be true when the work is done. Falcon reads it, shows you what it understood, and you confirm before anyone gets it.",
    "parts": [
        {"name": "What", "says": "A file by its name (sales.xlsx) or a program by its name (Excel)."},
        {"name": "What happens to it", "says": "A file is made, changed, or checked to be there. A program is used, installed, closed or kept running."},
        {"name": "When", "says": "Optional: a day or a time, like by Friday or 5pm tomorrow."},
    ],
    "examples": ["Update sales.xlsx by Friday", "Create summary.docx in C:/Reports by 5pm tomorrow", "Make sure report.pdf is there before Monday", "Install Zoom on the new laptop"],
    "cannot": "Falcon sees files and programs. It cannot see what is inside a file, whether the work is any good, or whether something was sent to someone: you confirm those yourself when you verify the task.",
}
CHECK_THEN = re.compile(r"\bcheck (?:if|whether)\b.*?\bif not\b", re.IGNORECASE | re.DOTALL)


def _flag(kind: str, detail: str, **more: Any) -> dict[str, Any]:
    return {"kind": kind, "detail": detail, **more}


def _weekend_note(first: str, second: str, now: datetime | None) -> str:
    if now is None or second.lower() not in NEXT_DAY:
        return ""
    base = now + timedelta(days=1) if first.lower() in ("today", "tonight") else now + timedelta(days=2)
    return f" The later one is a {base:%A}." if base.weekday() >= 5 else ""


def not_a_task(text: str) -> dict[str, Any] | None:
    """Nothing here is work to give anyone (the caller has found no file named): a question, a test, or a request for a task. None when it may be a task."""
    if ASKS_FOR_A_TASK.search(text):
        return _flag("not_a_task", f"This asks for a task but does not say what it is. {EXAMPLE}", help=HELP)
    if QUESTION.search(text) or TESTING.search(text):
        return _flag("not_a_task", f"This reads like a question or a test, not work for someone to do. {EXAMPLE}", help=HELP)
    return None


def read(text: str, out: Any, now: datetime | None = None) -> None:
    """Add what the patterns find to a proposal. `out` is the ProposedStructure, with its targets and deadline already read."""
    what = [said for pattern, said in CANNOT_CHECK if pattern.search(text)]
    if what:
        out.flags.append(_flag("cannot_check", f"Falcon checks files and programs. It cannot check {' or '.join(what)}: you confirm that part yourself.", what=what))
    creating = any(i.intent == "create" for i in out.items if i.target_type == "file")
    named = UNNAMED.search(text)
    if MAKE.search(text) and named and not creating:
        out.flags.append(_flag("unnamed_result", f"Something is to be made (“{named.group(0)}”) but no file is named. What will it be called?", phrase=named.group(0)))
    if COMBINE.search(text) and not creating:
        made_from = [i for i in out.items if i.target_type == "file"]
        for i in made_from:
            i.intent, i.intent_by = "exists", "rule"
        if made_from:
            out.flags.append(_flag("made_from", f"{' and '.join(i.name for i in made_from)} read as what it is made from: they must exist. The result is not one of them."))
    two = TWO_DEADLINES.search(text)
    if two and out.deadline_source != "hint":                 # (a time the person marked themselves is the deadline, whatever the words say)
        out.final_deadline, out.final_deadline_at, out.final_said = None, None, None
        out.flags = [f for f in out.flags if f["kind"] not in ("ambiguous_deadline", "unresolved_deadline")]
        out.flags.append(_flag("ambiguous_deadline", f"“{two.group(0)}” gives two deadlines. Which one?" + _weekend_note(two.group(1), two.group(2), now),
                               candidates=[two.group(1), two.group(2)]))
    wait = WAITS.search(text)
    if wait:
        out.flags.append(_flag("waits_on_event", f"It starts “{wait.group(0)}”, which is not a date. Give a deadline, or say it can wait for that.", phrase=wait.group(0)))
    if CHECK_THEN.search(text):
        out.flags.append(_flag("depends_on_check", "What is to be done depends on what is found: if it is there, nothing; if not, it is made. The check will be that the files exist."))
    files = [i for i in out.items if i.target_type == "file"]
    if WORK_ON.search(text):
        for i in files:
            if i.source != "hint" and i.intent == "create":
                i.intent, i.intent_by = "update", "rule"
    inside = INSIDE.search(text)
    if inside and files:
        for i in files:
            if i.source != "hint":
                i.intent, i.intent_by = "exists", "rule"
        out.flags.append(_flag("inside_file", f"Falcon sees the file, not what is in it. It will check {files[0].name} is there; “{inside.group(1)}” is yours to confirm.", phrase=inside.group(1)))
    if QUALITY.search(text):
        out.flags.append(_flag("quality_unseen", "Falcon can see that a file changed, not whether it is any better. Only you can judge that when you verify it."))
    again = RECURRING.search(text)
    if again:
        out.flags.append(_flag("recurring", f"“{again.group(0)}”: a task is done once. For work that repeats, give it again each time, or make a rule.", phrase=again.group(0)))
    for i in out.items:
        path = str(i.path or "")
        if path and i.source != "hint" and not re.search(r"[/\\:]", path):
            out.flags.append(_flag("folder_guess", f"“{path}” was taken as the folder for {i.name}. Which folder is meant?", target=i.name))
