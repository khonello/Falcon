"""Resolve a deadline phrase from a task description into a concrete local datetime.

The Engine's decision graph extracts the phrase verbatim ("by Friday", "before end of day Thursday", "by 3pm tomorrow"); turning it into a
timestamp needs the assigner's local clock and calendar, so it happens on the assigner's side and the result is shown for review before the
task is created. The reading itself lives in `common/when.py`, shared with the Engine and the console's `@` dialog, so every place agrees.

Returns None for anything not mechanically resolvable -- never a guess.
"""

from __future__ import annotations

from datetime import datetime

from common.when import resolve


def resolve_phrase(phrase: str | None, now: datetime | None = None) -> datetime | None:
    return resolve(phrase, now or datetime.now().astimezone()).at
