"""A flow's steps as the Worker carries them out (worker_client/flowsync.py, worker_client/pdf.py) and as the Engine reads the console's names."""

from __future__ import annotations

import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from engine.flow.flows import _parse_structure
from protocol import ProtocolError
from worker_client import pdf
from worker_client.flowsync import FlowSync, StageError

WHEN = datetime(2026, 10, 14, 9, 30, 12, tzinfo=timezone.utc)


def _sync() -> FlowSync:
    async def report(_t, _p):
        return {}
    return FlowSync(report)


def _step(op: str, kind: str = "transformation") -> dict:
    _dests, stages = _parse_structure({"stages": [{"stage_type": kind, "config": {"op": op}}],
                                       "destinations": [{"destination_pc_id": 1, "destination_path": "D:/in", "parent_index": 0}]})
    return stages[0]


def test_the_engine_turns_a_step_name_into_what_the_worker_does_and_refuses_one_it_does_not_know():
    assert _step("Rename by date")["config"] == {"op": "Rename by date", "rename": "date"}
    assert _step("Sort by month", "categorization")["config"] == {"op": "Sort by month", "by": "month"}
    with pytest.raises(ProtocolError):
        _step("Make it pretty")
    with pytest.raises(ProtocolError):
        _step("Sort by month")                                         # a categorization step named on a transformation


def test_rename_by_date_and_sort_by_month_use_the_date_the_file_was_changed():
    s, base = _sync(), Path("D:/in/report.txt")
    target, data = s._apply_stage(_step("Rename by date"), base, b"x", WHEN.astimezone())
    assert target.name.startswith("2026-10-14 ") and target.name.endswith("report.txt") and data == b"x"
    target, _ = s._apply_stage(_step("Sort by month", "categorization"), base, b"x", WHEN.astimezone())
    assert target.parent.name == "2026-10" and target.name == "report.txt"


def test_compress_to_zip_packs_the_file_the_same_way_every_time():
    s = _sync()
    target, first = s._apply_stage(_step("Compress to ZIP"), Path("D:/in/report.txt"), b"numbers" * 100, WHEN)
    _, again = s._apply_stage(_step("Compress to ZIP"), Path("D:/in/report.txt"), b"numbers" * 100, WHEN)
    assert target.name == "report.txt.zip" and first == again
    with zipfile.ZipFile(io.BytesIO(first)) as z:
        assert z.namelist() == ["report.txt"] and z.read("report.txt") == b"numbers" * 100


def test_convert_to_pdf_makes_text_and_photos_into_pdfs_and_says_when_it_cannot():
    s = _sync()
    target, data = s._apply_stage(_step("Convert to PDF"), Path("D:/in/notes.csv"), rb"1,(2)\3" + b"\n", WHEN)
    assert target.name == "notes.pdf" and data.startswith(b"%PDF-1.4") and data.rstrip().endswith(b"%%EOF")
    assert b"/Count 1" in data and rb"(1,\(2\)\\3) Tj" in data                     # parentheses and backslashes escaped
    jpeg = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"\xff\xc0\x00\x11\x08\x02\x58\x03\x20\x03" + b"\x00" * 9 + b"\xff\xd9"
    target, data = s._apply_stage(_step("Convert to PDF"), Path("D:/in/photo.JPG"), jpeg, WHEN)
    assert target.name == "photo.pdf" and b"/Width 800 /Height 600" in data and b"/DCTDecode" in data and jpeg in data
    with pytest.raises(StageError) as no:
        s._apply_stage(_step("Convert to PDF"), Path("D:/in/budget.xlsx"), b"PK", WHEN)
    assert no.value.kind == "unsupported_format"
    with pytest.raises(StageError):
        s._apply_stage(_step("Convert to PDF"), Path("D:/in/broken.jpg"), b"not a jpeg at all", WHEN)


def test_a_long_text_breaks_into_pages_and_long_lines_wrap():
    out = pdf.to_pdf((("x" * 300) + "\n").encode() * 100, "txt")
    assert out.count(b"/Type /Page ") == -(-(100 * -(-300 // pdf.COLUMNS)) // pdf.ROWS)
