"""Turning the words a person writes for "when" into a time, and saying plainly when it cannot.

One reader for every place a deadline is typed or found in a description: the console's `@` dialog, the Engine's proposal, the terminal client.
It never guesses: a phrase that could mean two different times ("3/4", "Monday or Wednesday", "next week") comes back unresolved with the
reason, so the assigner is asked instead of being given a silently chosen date.

    resolve("by 3pm tomorrow", now)   -> When(at=2026-10-17 15:00+00:00, said="Sat 17 Oct, 15:00", why="")
    resolve("3/4", now)                -> When(at=None, said="", why="3/4 could be 3 April or 4 March")

`now` carries the person's clock and zone; everything resolves in that zone. A day with no time means the end of the working day (17:00).
Stdlib only: bundled by every package.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta

WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
MONTHS = ["january", "february", "march", "april", "may", "june", "july", "august", "september", "october", "november", "december"]
END_OF_DAY = time(17, 0)
END_OF_NIGHT = time(23, 59)
MAX_PHRASE = 200

_WD = "|".join(WEEKDAYS)
_WD_SHORT = {w[:3]: w for w in WEEKDAYS} | {"tues": "tuesday", "wednes": "wednesday", "thur": "thursday", "thurs": "thursday"}
_MON = "|".join(m[:3] for m in MONTHS)

_ISO_FULL = re.compile(r"^\d{4}-\d{2}-\d{2}(?:[t ]\d{2}:\d{2}(?::\d{2}(?:\.\d+)?)?(?:z|[+-]\d{2}:?\d{2})?)?$", re.IGNORECASE)
_TIME_AMPM = re.compile(r"\b(\d{1,2})(?::(\d{2}))?\s*(a\.?m\.?|p\.?m\.?)(?![a-z])", re.IGNORECASE)
_TIME_24 = re.compile(r"(?<![\d/:.-])([01]?\d|2[0-3]):([0-5]\d)(?![\d:/])")
_OCLOCK = re.compile(r"\b(\d{1,2})\s*o'?clock\b", re.IGNORECASE)
_RELATIVE = re.compile(r"\b(?:in|within|after)\s+(?:(an?|\d+(?:\.\d+)?)\s+)?(minute|min|hour|hr|day|week|month)s?\b", re.IGNORECASE)
_NUMERIC_DATE = re.compile(r"(?<![\d.:])(\d{1,2})[/.](\d{1,2})(?:[/.](\d{2,4}))?(?![\d:])")
_DAY_MONTH = re.compile(r"\b(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)?\s+(?:of\s+)?(" + _MON + r")[a-z]*\b", re.IGNORECASE)
_MONTH_DAY = re.compile(r"\b(" + _MON + r")[a-z]*\.?\s+(\d{1,2})(?:st|nd|rd|th)?\b(?!\s*:)", re.IGNORECASE)
_ORDINAL = re.compile(r"\b(?:the\s+)?(\d{1,2})(?:st|nd|rd|th)\b", re.IGNORECASE)
_WEEKDAY = re.compile(r"\b(?:(this|next|coming|on|by|before|until)\s+)?(" + _WD + r"|mon|tues?|wed(?:nes)?|thu(?:rs?)?|fri|sat|sun)\b", re.IGNORECASE)
_DAYWORD = re.compile(r"\b(today|tonight|tomorrow|tmrw|tmr|yesterday)\b", re.IGNORECASE)
_EOD = re.compile(r"\b(?:end of (?:the )?(?:working )?day|eod|close of business|cob|end of business|eob)\b", re.IGNORECASE)
_EOW = re.compile(r"\b(?:end of (?:the )?(?:working )?week|eow)\b", re.IGNORECASE)
_EOM = re.compile(r"\b(?:end of (?:the )?month|eom)\b", re.IGNORECASE)
_NOON = re.compile(r"\b(?:noon|midday)\b", re.IGNORECASE)
_MIDNIGHT = re.compile(r"\bmidnight\b", re.IGNORECASE)
_MORNING = re.compile(r"\b(?:morning|first thing)\b", re.IGNORECASE)
_AFTERNOON = re.compile(r"\bafternoon\b", re.IGNORECASE)
_EVENING = re.compile(r"\bevening\b", re.IGNORECASE)
_VAGUE = re.compile(r"\b(?:next week|this week|next month|this month|soon|asap|sometime|whenever|later|eventually|when you can|at some point)\b", re.IGNORECASE)
_OR = re.compile(r"\b(?:or|whichever|either)\b", re.IGNORECASE)


@dataclass(frozen=True)
class When:
    at: datetime | None
    said: str = ""         # the time in words, for showing back to the person ("Sat 17 Oct, 15:00")
    why: str = ""          # when `at` is None: what is wrong, in a sentence

    def __bool__(self) -> bool:
        return self.at is not None


def _words(at: datetime) -> str:
    return f"{at.strftime('%a')} {at.day} {at.strftime('%b')}, {at:%H:%M}"


def _end(at: datetime) -> When:
    return When(at, _words(at))


def _no(why: str) -> When:
    return When(None, "", why)


def _next_weekday(today: date, weekday: int, *, after_today: bool) -> date:
    ahead = (weekday - today.weekday()) % 7
    if ahead == 0 and after_today:
        ahead = 7
    return today + timedelta(days=ahead)


def _clock(text: str) -> tuple[time | None, str]:
    """The time of day the text names, and what it consumed: '3pm', '15:30', '9 o'clock', 'noon', 'midnight', 'end of day'."""
    m = _TIME_AMPM.search(text)
    if m:
        hour, minute, mer = int(m.group(1)), int(m.group(2) or 0), m.group(3).lower().replace(".", "")
        if not 1 <= hour <= 12 or minute > 59:
            return None, "bad time"
        hour = hour % 12 + (12 if mer == "pm" else 0)
        return time(hour, minute), m.group(0)
    m = _TIME_24.search(text)
    if m:
        return time(int(m.group(1)), int(m.group(2))), m.group(0)
    m = _OCLOCK.search(text)
    if m and 1 <= int(m.group(1)) <= 12:
        h = int(m.group(1))
        return time(h + 12 if h < 8 else h, 0), m.group(0)          # "5 o'clock" means the afternoon in an office
    if _NOON.search(text):
        return time(12, 0), "noon"
    if _MIDNIGHT.search(text):
        return END_OF_NIGHT, "midnight"
    if _EOD.search(text):
        return END_OF_DAY, "end of day"
    if _MORNING.search(text):
        return time(9, 0), "morning"
    if _AFTERNOON.search(text):
        return time(15, 0), "afternoon"
    if _EVENING.search(text):
        return time(18, 0), "evening"
    return None, ""


def resolve(phrase: str | None, now: datetime) -> When:
    """`phrase` as a time in `now`'s zone, or why it cannot be one."""
    if not phrase or not str(phrase).strip():
        return _no("nothing was said")
    text = " ".join(str(phrase).split())
    if len(text) > MAX_PHRASE:
        return _no("that is too long to be a time")
    low = text.lower().strip(" .,;:!?")
    if _OR.search(low):
        return _no("it names more than one time; pick one")

    # an exact ISO time passes through
    if _ISO_FULL.match(low):
        try:
            at = datetime.fromisoformat(low.replace("z", "+00:00").replace("t", "T") if "z" in low or "t" in low else low)
        except ValueError:
            return _no("that is not a real date")
        if at.tzinfo is None:
            at = (at if "t" in low or " " in low else datetime.combine(at.date(), END_OF_DAY)).replace(tzinfo=now.tzinfo)
        return _end(at.astimezone(now.tzinfo))

    # relative: in 2 hours, within 3 days, after a week
    rel = _RELATIVE.search(low)
    if rel:
        n_raw = rel.group(1)
        n = 1.0 if n_raw is None or n_raw.lower() in ("a", "an") else float(n_raw)
        unit = rel.group(2).lower()
        step = {"minute": timedelta(minutes=1), "min": timedelta(minutes=1), "hour": timedelta(hours=1), "hr": timedelta(hours=1),
                "day": timedelta(days=1), "week": timedelta(weeks=1), "month": timedelta(days=30)}[unit]
        if n <= 0 or n > 400:
            return _no("that is not a sensible length of time")
        return _end((now + n * step).replace(second=0, microsecond=0))

    clock, used = _clock(low)
    if used == "bad time":
        return _no("that is not a valid time of day")
    rest = low.replace(used, " ") if used and used not in ("noon", "midnight", "end of day", "morning", "afternoon", "evening") else low

    day: date | None = None
    today = now.date()

    nd = _NUMERIC_DATE.search(rest)
    dm = _DAY_MONTH.search(rest)
    md = _MONTH_DAY.search(rest)
    if nd:
        a, b, y = int(nd.group(1)), int(nd.group(2)), nd.group(3)
        if a > 12 and b <= 12:
            d_, m_ = a, b
        elif b > 12 and a <= 12:
            d_, m_ = b, a
        elif a == b:
            d_, m_ = a, b
        elif a <= 12 and b <= 12:
            return _no(f"{nd.group(0)} could be {a} {MONTHS[b - 1].title()} or {b} {MONTHS[a - 1].title()}")
        else:
            return _no("that is not a real date")
        year = today.year
        if y:
            year = int(y) + (2000 if int(y) < 100 else 0)
        try:
            day = date(year, m_, d_)
        except ValueError:
            return _no("that is not a real date")
        if not y and day < today:
            day = date(year + 1, m_, d_) if (m_, d_) != (2, 29) else None
    elif dm or md:
        d_, mon = (int(dm.group(1)), dm.group(2)) if dm else (int(md.group(2)), md.group(1))
        m_ = [m[:3] for m in MONTHS].index(mon.lower()[:3]) + 1
        try:
            day = date(today.year, m_, d_)
        except ValueError:
            return _no("that is not a real date")
        if day < today:
            try:
                day = date(today.year + 1, m_, d_)
            except ValueError:
                return _no("that is not a real date")
    elif (word := _DAYWORD.search(rest)):
        w = word.group(1).lower()
        if w == "yesterday":
            return _no("that is in the past")
        day = today + timedelta(days=1) if w in ("tomorrow", "tmrw", "tmr") else today
        if w == "tonight" and clock is None:
            clock = END_OF_NIGHT
    elif (wd := _WEEKDAY.search(rest)):
        qualifier, name = (wd.group(1) or "").lower(), wd.group(2).lower()
        name = _WD_SHORT.get(name[:3], name) if name not in WEEKDAYS else name
        target = WEEKDAYS.index(name)
        # "next Friday" is the first Friday after today (said on a Friday, the one a week on); a bare "Friday" is the coming one, today included
        day = _next_weekday(today, target, after_today=qualifier == "next")
    elif _EOW.search(rest):
        day = _next_weekday(today, 4, after_today=False)
        clock = clock or END_OF_DAY
    elif _EOM.search(rest):
        first_next = (today.replace(day=1) + timedelta(days=32)).replace(day=1)
        day = first_next - timedelta(days=1)
        clock = clock or END_OF_DAY
    elif (om := _ORDINAL.search(rest)):
        d_ = int(om.group(1))
        if not 1 <= d_ <= 31:
            return _no("that is not a day of the month")
        try:
            day = date(today.year, today.month, d_)
        except ValueError:
            day = None
        if day is None or day < today:
            y, m_ = (today.year + (today.month // 12), today.month % 12 + 1)
            try:
                day = date(y, m_, d_)
            except ValueError:
                return _no("that is not a real date")
    elif clock is not None:
        day = today
    else:
        if _VAGUE.search(low):
            return _no("that is not a time; say a day or a date")
        return _no("no day or time was found in it")

    at = datetime.combine(day, clock or END_OF_DAY, tzinfo=now.tzinfo)
    # "by Friday 9am" said on Friday afternoon, or "3pm" said at 4pm: today's time has gone, so the next one is meant
    if at <= now:
        if _WEEKDAY.search(rest) and not nd and not dm and not md and not _DAYWORD.search(rest) and day == today and not _ORDINAL.search(rest):
            at += timedelta(days=7)
        elif clock is not None and day == today and not _DAYWORD.search(rest) and not _WEEKDAY.search(rest) and not nd and not dm and not md:
            at += timedelta(days=1)
        else:
            return _no(f"{_words(at)} has already passed")
    return _end(at)
