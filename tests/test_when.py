"""Reading "when" from words (common/when.py): many phrasings, one fixed clock, and every ambiguity refused rather than guessed.

The clock is Wednesday 14 October 2026, 10:00, in two zones so a zone is never silently UTC.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

import pytest

from common.when import resolve

UTC = timezone.utc
GH = timezone(timedelta(hours=0))
CEST = timezone(timedelta(hours=2))
NOW = datetime(2026, 10, 14, 10, 0, tzinfo=UTC)               # a Wednesday


def at(day: int, hour: int, minute: int = 0, month: int = 10, year: int = 2026, tz=UTC) -> datetime:
    return datetime(year, month, day, hour, minute, tzinfo=tz)


# phrase -> the time it must mean (Wed 14 Oct 2026, 10:00)
RESOLVES = {
    # today and tomorrow
    "today": at(14, 17), "tonight": at(14, 23, 59), "tomorrow": at(15, 17), "tmrw": at(15, 17), "by tomorrow": at(15, 17),
    "tomorrow at 3pm": at(15, 15), "by 3pm tomorrow": at(15, 15), "tomorrow 9am": at(15, 9), "tomorrow morning": at(15, 9),
    "tomorrow afternoon": at(15, 15), "tomorrow evening": at(15, 18), "by tomorrow evening": at(15, 18),
    "today at 5pm": at(14, 17), "by 4pm today": at(14, 16), "by noon tomorrow": at(15, 12), "midnight": at(14, 23, 59),
    # clock times alone: today if still ahead, else tomorrow
    "3pm": at(14, 15), "by 3pm": at(14, 15), "15:30": at(14, 15, 30), "by 17:00": at(14, 17), "9am": at(15, 9), "9:30 am": at(15, 9, 30),
    "noon": at(14, 12), "5 o'clock": at(14, 17), "12pm": at(14, 12), "12am": at(15, 0),
    # weekdays
    "Friday": at(16, 17), "by Friday": at(16, 17), "Friday at 9am": at(16, 9), "this Friday": at(16, 17), "on Monday": at(19, 17),
    "next Monday": at(19, 17), "next Friday": at(16, 17), "by Friday 3pm": at(16, 15), "before Thursday": at(15, 17), "end of day Thursday": at(15, 17),
    "Wednesday": at(14, 17), "Wednesday 9am": at(21, 9), "next Wednesday": at(21, 17), "sun": at(18, 17), "by fri": at(16, 17), "thurs": at(15, 17),
    "Monday morning": at(19, 9), "Friday afternoon": at(16, 15), "Saturday": at(17, 17),
    # end of ...
    "end of day": at(14, 17), "EOD": at(14, 17), "close of business": at(14, 17), "cob tomorrow": at(15, 17), "end of week": at(16, 17), "EOW": at(16, 17),
    "end of the month": at(31, 17), "eom": at(31, 17), "end of business Friday": at(16, 17),
    # dates
    "15 Oct": at(15, 17), "15 October": at(15, 17), "15th October": at(15, 17), "the 15th of October": at(15, 17), "Oct 15": at(15, 17),
    "October 15th": at(15, 17), "15 Oct at 3pm": at(15, 15), "25 Dec": at(25, 17, month=12), "1 Jan": at(1, 17, month=1, year=2027),
    "2 Oct": at(2, 17, year=2027), "2026-10-20": at(20, 17), "2026-10-20 14:30": at(20, 14, 30), "2026-10-20T14:30:00Z": at(20, 14, 30),
    "2026-10-20T14:30:00.000Z": at(20, 14, 30), "2026-10-20T14:30:00+02:00": at(20, 12, 30), "20/10": at(20, 17), "20/10/2026": at(20, 17),
    "10/20": at(20, 17), "31/12": at(31, 17, month=12), "the 20th": at(20, 17), "by the 14th": at(14, 17), "the 3rd": at(3, 17, month=11),
    "5 Oct 2027": None,                                                                     # a year after a date is not read: asks
    # relative
    "in 2 hours": at(14, 12), "in an hour": at(14, 11), "in 30 minutes": at(14, 10, 30), "within 3 days": at(17, 10), "in a week": at(21, 10),
    "in 2 weeks": at(28, 10), "in 1 day": at(15, 10), "after 90 min": at(14, 11, 30),
}

# phrases that must NOT become a time, each with what the refusal must mention
REFUSED = {
    "": "nothing", "   ": "nothing", None: "nothing",
    "Monday or Wednesday": "more than one", "Friday or Saturday, whichever works": "more than one", "either Tuesday or Thursday": "more than one",
    "3/4": "could be", "05/06": "could be", "1.2": "could be",
    "next week": "not a time", "this week": "not a time", "soon": "not a time", "asap": "not a time", "sometime": "not a time", "whenever": "not a time",
    "the usual things": "no day or time", "report": "no day or time", "banana": "no day or time",
    "yesterday": "past", "32 Oct": "not a real date", "30/02": "not a real date", "31 Apr": "not a real date", "2026-13-45": "not a real date",
    "25:00": "no day or time", "13pm": "not a valid time", "0am": "not a valid time", "the 40th": "not a day",
    "in 0 hours": "not a sensible", "in 99999 days": "not a sensible", "x" * 300: "too long",
    "9am yesterday": "past",
}

# the same words in another zone mean that zone's clock
ZONED = [("by 3pm tomorrow", datetime(2026, 10, 15, 15, 0, tzinfo=CEST)), ("tomorrow", datetime(2026, 10, 15, 17, 0, tzinfo=CEST)),
         ("in 2 hours", datetime(2026, 10, 14, 12, 0, tzinfo=CEST)), ("2026-10-20T14:30:00Z", datetime(2026, 10, 20, 16, 30, tzinfo=CEST))]


@pytest.mark.parametrize(("phrase", "want"), [(k, v) for k, v in RESOLVES.items() if v is not None], ids=lambda x: str(x)[:40])
def test_a_phrase_means_one_time(phrase, want):
    got = resolve(phrase, NOW)
    assert got.at == want, f"{phrase!r}: {got}"
    assert got.said and not got.why


@pytest.mark.parametrize(("phrase", "word"), list(REFUSED.items()), ids=lambda x: str(x)[:40])
def test_a_phrase_that_is_not_one_time_is_refused_with_a_reason(phrase, word):
    got = resolve(phrase, NOW)
    assert got.at is None and not got, f"{phrase!r} should not resolve: {got}"
    assert word in got.why, f"{phrase!r}: {got.why!r}"


def test_a_year_after_a_date_is_asked_about_not_read():
    assert resolve("5 Oct 2027", NOW).at is None or resolve("5 Oct 2027", NOW).at.year == 2027       # either asks or reads the year, never another year


@pytest.mark.parametrize(("phrase", "want"), ZONED, ids=lambda x: str(x)[:30])
def test_everything_resolves_in_the_persons_zone(phrase, want):
    now = datetime(2026, 10, 14, 10, 0, tzinfo=CEST)
    assert resolve(phrase, now).at == want


def test_a_time_that_has_gone_today_means_the_next_one():
    late = datetime(2026, 10, 14, 16, 30, tzinfo=UTC)
    assert resolve("3pm", late).at == at(15, 15)                                              # 3pm has passed: tomorrow's
    assert resolve("by Wednesday", late).at == at(14, 17)                                     # 5pm today is still ahead
    after = datetime(2026, 10, 14, 17, 30, tzinfo=UTC)
    assert resolve("by Wednesday", after).at == at(21, 17)                                    # it has gone: next week's
    assert resolve("today", after).at is None                                                 # nothing of today is left
    assert "passed" in resolve("today", after).why


def test_it_never_returns_a_time_in_the_past_or_the_wrong_zone():
    import random

    words = ["today", "tomorrow", "friday", "monday", "3pm", "9am", "noon", "end of day", "next friday", "15 oct", "in 2 hours", "tonight", "eod"]
    rnd = random.Random(7)
    for _ in range(500):
        phrase = " ".join(rnd.sample(words, rnd.randint(1, 3)))
        got = resolve(phrase, NOW)
        if got:
            assert got.at >= NOW and got.at.utcoffset() == NOW.utcoffset(), phrase


def test_it_survives_anything_it_is_given():
    import random
    import string

    rnd = random.Random(11)
    alphabet = string.printable + "éß中日🙂" + chr(0x202E) + chr(0)
    for _ in range(2000):
        phrase = "".join(rnd.choice(alphabet) for _ in range(rnd.randint(0, 60)))
        got = resolve(phrase, NOW)                                                            # never raises
        assert (got.at is None) == bool(got.why)


def test_the_words_said_back_are_plain():
    assert resolve("by 3pm tomorrow", NOW).said == "Thu 15 Oct, 15:00"
    assert resolve("2026-12-25 09:00", NOW).said == "Fri 25 Dec, 09:00"
