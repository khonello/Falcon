"""Reading a time a client wrote as ISO 8601.

JavaScript (the console) writes `2026-10-17T17:00:00.000Z`; Python 3.10's `datetime.fromisoformat` refuses the trailing `Z`, which made every
deadline set in the console fail with "must be ISO 8601". One reader, used wherever a client sends a time.
"""

from __future__ import annotations

from datetime import datetime


def parse_iso(raw: object) -> datetime:
    text = str(raw).strip()
    if text.endswith(("Z", "z")):
        text = text[:-1] + "+00:00"
    return datetime.fromisoformat(text)
