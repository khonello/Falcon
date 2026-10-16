"""What the person said outright, as opposed to what has to be worked out.

The console's `@` dialog lets the assigner mark a piece of the description as a file, a program, a folder or a time. Those are facts the person
stated, so the decision graph takes them as given and asks the model only about what is left. This module checks what arrives (it is client input
like any other) and turns it into `Hint`s.

    {"kind": "file",     "name": "budget.xlsx", "intent": "update"?, "file_index_id": 12?, "path": "C:/Finance"?}
    {"kind": "program",  "name": "Excel",       "intent": "used_with_file"?}
    {"kind": "folder",   "path": "C:/Finance/Minutes"}
    {"kind": "deadline", "role": "final" | "soft", "at": "<ISO 8601>" | "phrase": "by Friday"}

The person who is the assignee is not a hint: they are `assignee_account_id`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from common.when import When, resolve
from engine.isotime import parse_iso
from engine.task.verification import FILE_INTENTS, PROGRAM_INTENTS
from protocol import ErrorCode, ProtocolError

MAX_HINTS = 40
MAX_TEXT = 300
KINDS = ("file", "program", "folder", "deadline")


@dataclass(frozen=True)
class Hint:
    kind: str
    name: str = ""
    intent: str | None = None
    file_index_id: int | None = None
    path: str | None = None
    role: str | None = None
    when: When | None = None


def _text(d: dict[str, Any], key: str, *, required: bool = False) -> str:
    value = d.get(key)
    if value is None or value == "":
        if required:
            raise ProtocolError(ErrorCode.INVALID, f"a {d.get('kind', 'hint')} hint needs {key}")
        return ""
    if not isinstance(value, (str, int)) or len(str(value)) > MAX_TEXT:
        raise ProtocolError(ErrorCode.INVALID, f"hint {key} must be text of at most {MAX_TEXT} characters")
    return " ".join(str(value).split())


def parse_hints(raw: Any, now: Any) -> list[Hint]:
    """The valid hints in `raw`; anything malformed is refused outright (a hint is a statement of fact: a wrong one must not be quietly dropped)."""
    if raw is None:
        return []
    if not isinstance(raw, list) or len(raw) > MAX_HINTS:
        raise ProtocolError(ErrorCode.INVALID, f"hints must be a list of at most {MAX_HINTS}")
    out: list[Hint] = []
    for d in raw:
        if not isinstance(d, dict) or d.get("kind") not in KINDS:
            raise ProtocolError(ErrorCode.INVALID, f"a hint is an object with kind one of {', '.join(KINDS)}")
        kind = d["kind"]
        if kind == "file":
            intent = _text(d, "intent") or None
            if intent is not None and intent not in FILE_INTENTS:
                raise ProtocolError(ErrorCode.INVALID, f"file intent must be one of {', '.join(sorted(FILE_INTENTS))}")
            fid = d.get("file_index_id")
            if fid is not None and (not isinstance(fid, int) or isinstance(fid, bool)):
                raise ProtocolError(ErrorCode.INVALID, "file_index_id must be a number")
            out.append(Hint("file", name=_text(d, "name", required=True), intent=intent, file_index_id=fid, path=_text(d, "path") or None))
        elif kind == "program":
            intent = _text(d, "intent") or None
            if intent is not None and intent not in PROGRAM_INTENTS:
                raise ProtocolError(ErrorCode.INVALID, f"program intent must be one of {', '.join(sorted(PROGRAM_INTENTS))}")
            out.append(Hint("program", name=_text(d, "name", required=True), intent=intent))
        elif kind == "folder":
            out.append(Hint("folder", path=_text(d, "path", required=True)))
        else:
            role = _text(d, "role") or "final"
            if role not in ("final", "soft"):
                raise ProtocolError(ErrorCode.INVALID, "deadline role must be final or soft")
            if d.get("at"):
                try:
                    at = parse_iso(_text(d, "at"))
                except ValueError as exc:
                    raise ProtocolError(ErrorCode.INVALID, "deadline at must be ISO 8601") from exc
                if at.tzinfo is None:
                    at = at.replace(tzinfo=now.tzinfo)
                when = When(at, f"{at:%a} {at.day} {at:%b}, {at:%H:%M}")
            else:
                when = resolve(_text(d, "phrase", required=True), now)
                if not when:
                    raise ProtocolError(ErrorCode.INVALID, f"that deadline cannot be read: {when.why}")
            out.append(Hint("deadline", role=role, when=when))
    return out
