"""Resolve a deadline phrase from a task description into a concrete local datetime.

The Engine's decision graph extracts the phrase verbatim ("by Friday", "before end of day
Thursday", "by 3pm tomorrow"); turning it into a timestamp needs the assigner's local clock and
calendar, so it happens here, client-side, and the result is shown for review before the task
is created (Task -> Deadline: natural language populates the field, the assigner adjusts it).

Returns None for anything not mechanically resolvable -- never a guess.
"""

from __future__ import annotations

import re
from datetime import datetime, time, timedelta

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
END_OF_DAY = time(17, 0)
END_OF_NIGHT = time(23, 59)

_TIME = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", re.IGNORECASE)
_DAY = re.compile(r"\b(" + "|".join(WEEKDAYS) + r"|today|tonight|tomorrow)\b", re.IGNORECASE)
_NEXT = re.compile(r"\bnext\s+(" + "|".join(WEEKDAYS) + r")\b", re.IGNORECASE)
_EOD = re.compile(r"\bend of (?:the )?day\b", re.IGNORECASE)
_EOW = re.compile(r"\bend of (?:the )?week\b", re.IGNORECASE)
_EOM = re.compile(r"\bend of (?:the )?month\b", re.IGNORECASE)
_NOON = re.compile(r"\bnoon\b", re.IGNORECASE)
_MIDNIGHT = re.compile(r"\bmidnight\b", re.IGNORECASE)


def resolve_phrase(phrase: str | None, now: datetime | None = None) -> datetime | None:
    if not phrase:
        return None
    text = phrase.strip()
    now = now or datetime.now().astimezone()
    # ISO 8601 passes through.
    try:
        dt = datetime.fromisoformat(text)
        return dt if dt.tzinfo else dt.replace(tzinfo=now.tzinfo)
    except ValueError:
        pass
    if re.search(r"\bor\b", text, re.IGNORECASE):
        return None  # ambiguous: the assigner picks

    # Day part.
    day: datetime | None = None
    m_next = _NEXT.search(text)
    m_day = _DAY.search(text)
    if m_next:
        day = _next_weekday(now, WEEKDAYS.index(m_next.group(1).lower()), skip_this_week=True)
    elif m_day:
        word = m_day.group(1).lower()
        if word == "today" or word == "tonight":
            day = now
        elif word == "tomorrow":
            day = now + timedelta(days=1)
        else:
            day = _next_weekday(now, WEEKDAYS.index(word), skip_this_week=False)
    elif _EOW.search(text):
        day = _next_weekday(now, 4, skip_this_week=False)  # Friday
    elif _EOM.search(text):
        first_next = (now.replace(day=1) + timedelta(days=32)).replace(day=1)
        day = first_next - timedelta(days=1)
    elif _EOD.search(text) or _TIME.search(text) or _NOON.search(text) or _MIDNIGHT.search(text):
        day = now
    if day is None:
        return None

    # Time part.
    clock = END_OF_DAY
    m_time = _TIME.search(text)
    if m_time:
        hour, minute, ampm = int(m_time.group(1)), int(m_time.group(2) or 0), m_time.group(3).lower()
        if ampm == "pm" and hour != 12:
            hour += 12
        if ampm == "am" and hour == 12:
            hour = 0
        clock = time(hour, minute)
    elif _NOON.search(text):
        clock = time(12, 0)
    elif _MIDNIGHT.search(text) or (m_day and m_day.group(1).lower() == "tonight"):
        clock = END_OF_NIGHT
    resolved = datetime.combine(day.date(), clock, tzinfo=now.tzinfo)
    if resolved <= now and not m_next and m_day and m_day.group(1).lower() in WEEKDAYS:
        resolved += timedelta(days=7)  # "by Friday" said on Friday evening means next Friday
    return resolved


def _next_weekday(now: datetime, weekday: int, *, skip_this_week: bool) -> datetime:
    """The coming occurrence of `weekday` (today counts, unless `skip_this_week`)."""
    ahead = (weekday - now.weekday()) % 7
    if ahead == 0 and skip_this_week:
        ahead = 7
    return now + timedelta(days=ahead)
