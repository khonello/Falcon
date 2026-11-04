"""A flow's steps as a tree (the user, 3 Nov 2026): the Engine checks each step against the catalogue (engine/flow/steps.py), Choosing is
decided on the Engine, and the Worker carries out the rest (worker_client/flowsync.py, worker_client/convert.py, worker_client/pdf.py)."""

from __future__ import annotations

import io
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from engine.flow import steps
from engine.flow.flows import _parse_structure, check_steps
from protocol import ProtocolError
from worker_client import convert, pdf
from worker_client.flowsync import FlowSync, _make_bundle

WHEN = datetime(2026, 10, 14, 9, 30, 12, tzinfo=timezone.utc)
JPEG = b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x00\x00\x01\x00\x01\x00\x00" + b"\xff\xc0\x00\x11\x08\x02\x58\x03\x20\x03" + b"\x00" * 9 + b"\xff\xd9"


def _sync() -> FlowSync:
    async def report(_t, _p):
        return {}
    return FlowSync(report)


def _stage(kind: str, op: str, **settings) -> dict:
    _dests, stages = _parse_structure({"stages": [{"step": {"kind": kind, "op": op, "settings": settings}}],
                                       "destinations": [{"destination_pc_id": 1, "destination_path": "D:/in", "parent_index": 0}]})
    return stages[0]


def _run(stage: dict, name: str, data: bytes, when: datetime = WHEN):
    made, notes = _sync()._apply_steps([stage], Path("D:/in") / name, data, when.astimezone())
    return ([made] if made else []), notes


def test_the_tree_lists_every_kind_and_each_step_is_checked_against_it():
    tree = steps.catalogue()
    kinds = {k["kind"]: [o["op"] for o in k["ops"]] for c in tree for k in c["kinds"]}
    assert kinds == {"choosing": ["by_type", "by_name", "by_size"], "conversion": ["to_pdf", "to_docx", "to_image", "zip_each"],
                     "renaming": ["add_date", "add_text", "replace_text"], "bundling": ["zip", "pdf"]}
    assert [c["category"] for c in tree] == ["per_file", "all_files"]
    st = _stage("conversion", "to_pdf")
    assert st["stage_type"] == "conversion" and st["config"]["settings"] == {"from": ["text", "images", "word", "excel", "powerpoint"], "if_not": "copy"}
    assert _stage("choosing", "by_type", types=[".PDF", "docx"])["config"]["settings"] == {"types": ["docx", "pdf"], "keep": "take"}
    for bad in ({"kind": "placing", "op": "by_month"}, {"kind": "conversion", "op": "to_pdf", "settings": {"from": ["video"]}},
                {"kind": "renaming", "op": "add_text", "settings": {"text": "a/b"}}, {"kind": "choosing", "op": "by_type"},
                {"kind": "conversion", "op": "to_image", "settings": {"quality": 400}}, {"kind": "conversion", "op": "zip_each", "settings": {"x": 1}}):
        with pytest.raises(ProtocolError):
            _parse_structure({"stages": [{"step": bad}], "destinations": [{"destination_pc_id": 1, "destination_path": "D:/in"}]})


def test_the_old_step_names_still_work_and_placing_is_refused():
    old = _parse_structure({"stages": [{"stage_type": "transformation", "config": {"op": "Rename by date"}}],
                            "destinations": [{"destination_pc_id": 1, "destination_path": "D:/in", "parent_index": 0}]})[1][0]
    assert old["stage_type"] == "renaming" and old["config"]["op"] == "add_date"
    for name, kind in (("Sort by month", "categorization"), ("Sort by file type", "categorization")):
        with pytest.raises(ProtocolError) as no:
            _parse_structure({"stages": [{"stage_type": kind, "config": {"op": name}}], "destinations": [{"destination_pc_id": 1, "destination_path": "D:/in"}]})
        assert "dropped" in str(no.value)
    # a stored step from before the tree is read in its new name; a stored placing step means nothing now
    assert steps.normal({"stage_type": "transformation", "config": {"rename": "date"}})["config"]["op"] == "add_date"
    assert steps.normal({"stage_type": "transformation", "config": {"to": "pdf"}})["config"]["op"] == "to_pdf"
    assert steps.normal({"stage_type": "categorization", "config": {"by": "month"}}) is None


def test_the_kinds_run_in_one_order_and_bundling_only_where_a_run_has_a_folder():
    def path(*kinds_ops):
        stages = [{"step": {"kind": k, "op": o, "settings": s}, "parent_index": i - 1 if i else None} for i, (k, o, s) in enumerate(kinds_ops)]
        return _parse_structure({"stages": stages, "destinations": [{"destination_pc_id": 1, "destination_path": "D:/in", "parent_index": len(stages) - 1}]})
    dests, stages = path(("choosing", "by_type", {"types": ["docx"]}), ("conversion", "to_pdf", {}), ("renaming", "add_date", {}), ("bundling", "zip", {}))
    check_steps(stages, dests, run_mode="hourly", sources=1, source_kind="folder")
    with pytest.raises(ProtocolError):
        check_steps(stages, dests, run_mode="realtime", sources=1, source_kind="folder")      # a bundle needs a run
    with pytest.raises(ProtocolError):
        check_steps(stages, dests, run_mode="manual", sources=2, source_kind="folder")        # one folder
    dests, stages = path(("renaming", "add_date", {}), ("conversion", "to_pdf", {}))
    with pytest.raises(ProtocolError):
        check_steps(stages, dests, run_mode="realtime", sources=1, source_kind="folder")      # Conversion comes before Renaming
    dests, stages = path(("bundling", "zip", {}), ("bundling", "pdf", {}))
    with pytest.raises(ProtocolError):
        check_steps(stages, dests, run_mode="hourly", sources=1, source_kind="folder")        # one bundle
    with pytest.raises(ProtocolError):
        path(("unbundling", "unzip", {}))                                                     # dropped: not a step


def test_choosing_by_type_name_and_size():
    chain = [{"stage_type": "choosing", "config": _stage("choosing", "by_type", types=["pdf", "docx"])["config"]}]
    assert steps.chosen(chain, "a/report.PDF") and not steps.chosen(chain, "a/photo.jpg")
    leave = [{"stage_type": "choosing", "config": _stage("choosing", "by_type", types=["tmp"], keep="leave")["config"]}]
    assert steps.chosen(leave, "x.docx") and not steps.chosen(leave, "x.tmp")
    named = [{"stage_type": "choosing", "config": _stage("choosing", "by_name", match="starts_with", text="Invoice")["config"]}]
    assert steps.chosen(named, "2026/invoice-031.pdf") and not steps.chosen(named, "2026/receipt.pdf")
    small = [{"stage_type": "choosing", "config": _stage("choosing", "by_size", mb=1)["config"]}]
    assert steps.chosen(small, "big.iso") and steps.chosen(small, "a.txt", 500_000) and not steps.chosen(small, "big.iso", 5_000_000)


def test_renaming_adds_a_date_or_text_or_replaces_text():
    (target, data), = _run(_stage("renaming", "add_date"), "report.txt", b"x")[0]
    assert target.name == "2026-10-14 report.txt" and data == b"x"
    (target, _), = _run(_stage("renaming", "add_date", where="after", format="yyyymmdd"), "report.txt", b"x")[0]
    assert target.name == "report 20261014.txt"
    (target, _), = _run(_stage("renaming", "add_text", text="FIN-"), "report.txt", b"x")[0]
    assert target.name == "FIN-report.txt"
    (target, _), = _run(_stage("renaming", "replace_text", find="DRAFT", **{"with": "final"}), "budget draft v2.xlsx", b"x")[0]
    assert target.name == "budget final v2.xlsx"


def test_a_new_dated_name_puts_the_older_copy_aside_unless_someone_changed_it(tmp_path):
    from worker_client.flowsync import hash_of

    old, new = tmp_path / "2026-11-03 report.docx", tmp_path / "2026-11-04 report.docx"
    old.write_bytes(b"first")
    new.write_bytes(b"second")
    previous = {"path": str(old), "hash": hash_of(old, 1 << 62)}
    assert FlowSync._replace_older(new, tmp_path, {"path": str(new), "hash": "x"}) is None          # the same place: an ordinary overwrite
    assert FlowSync._replace_older(new, tmp_path, None) is None
    done = FlowSync._replace_older(new, tmp_path, previous)
    assert not old.exists() and (tmp_path / ".falcon-removed" / old.name).read_bytes() == b"first" and done["moved_to"]
    old.write_bytes(b"edited here")                                                                # changed since the flow wrote it: theirs
    assert FlowSync._replace_older(new, tmp_path, previous) == {"path": str(old), "kept": True} and old.exists()
    elsewhere = tmp_path.parent / "someone-elses.txt"
    assert FlowSync._replace_older(new, tmp_path, {"path": str(elsewhere), "hash": "x"}) is None    # never outside the destination


def test_zip_each_packs_the_file_the_same_way_every_time():
    (target, first), = _run(_stage("conversion", "zip_each"), "report.txt", b"numbers" * 100)[0]
    (_, again), = _run(_stage("conversion", "zip_each"), "report.txt", b"numbers" * 100)[0]
    assert target.name == "report.txt.zip" and first == again
    with zipfile.ZipFile(io.BytesIO(first)) as z:
        assert z.namelist() == ["report.txt"] and z.read("report.txt") == b"numbers" * 100


def test_to_pdf_converts_what_it_can_and_copies_or_leaves_out_what_it_cannot(monkeypatch):
    items, notes = _run(_stage("conversion", "to_pdf"), "notes.csv", rb"1,(2)\3" + b"\n")
    (target, data), = items
    assert target.name == "notes.pdf" and data.startswith(b"%PDF-1.4") and rb"(1,\(2\)\\3) Tj" in data and notes == []
    (target, data), = _run(_stage("conversion", "to_pdf"), "photo.JPG", JPEG)[0]
    assert target.name == "photo.pdf" and b"/Width 800 /Height 600" in data and JPEG in data
    monkeypatch.setattr(convert, "office_tool", lambda: None)
    items, notes = _run(_stage("conversion", "to_pdf"), "budget.xlsx", b"PK")
    assert items == [(Path("D:/in/budget.xlsx"), b"PK")] and notes[0]["why"] == "there is no Office or LibreOffice on this machine"
    items, notes = _run(_stage("conversion", "to_pdf", if_not="leave_out"), "budget.xlsx", b"PK")
    assert items == [] and notes[0]["left_out"] is True
    items, _ = _run(_stage("conversion", "to_pdf", **{"from": ["text"]}), "photo.jpg", JPEG)        # not one of its types: untouched
    assert items == [(Path("D:/in/photo.jpg"), JPEG)]
    items, notes = _run(_stage("conversion", "to_pdf"), "broken.jpg", b"not a jpeg at all")
    assert items[0][1] == b"not a jpeg at all" and "damaged" in notes[0]["why"]


def test_office_files_go_through_the_machine_s_own_office_or_libreoffice(monkeypatch):
    seen = []
    monkeypatch.setattr(convert, "office", lambda data, frm, to: seen.append((frm, to)) or b"%PDF-made")
    (target, data), = _run(_stage("conversion", "to_pdf"), "budget.xlsx", b"PK")[0]
    assert target.name == "budget.pdf" and data == b"%PDF-made" and seen == [("xlsx", "pdf")]
    (target, data), = _run(_stage("conversion", "to_docx"), "scan.pdf", b"%PDF")[0]
    assert target.name == "scan.docx" and seen[-1] == ("pdf", "docx")


def test_text_becomes_a_word_document():
    (target, data), = _run(_stage("conversion", "to_docx"), "minutes.txt", b"First line\nSecond & last")[0]
    assert target.name == "minutes.docx"
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        body = z.read("word/document.xml").decode()
    assert "<w:t xml:space=\"preserve\">First line</w:t>" in body and "Second &amp; last" in body


@pytest.mark.skipif(__import__("os").name != "nt", reason="Windows' own image library")
def test_an_image_changes_type_with_windows_own_image_library(tmp_path):
    png = convert.image(JPEG_REAL, "jpg", "png")
    assert png.startswith(b"\x89PNG")
    (target, data), = _run(_stage("conversion", "to_image", to="jpg", quality=70), "shot.png", png)[0]
    assert target.name == "shot.jpg" and data[:2] == b"\xff\xd8"


def test_a_bundle_is_made_from_what_was_kept_aside(tmp_path):
    # a bundle's run: files kept aside, then one ZIP (folders kept or flattened) or one PDF
    (tmp_path / "sub").mkdir()
    (tmp_path / "a.pdf").write_bytes(pdf.to_pdf(b"a", "txt"))
    (tmp_path / "sub" / "a.pdf").write_bytes(pdf.to_pdf(b"b", "txt"))
    (tmp_path / "note.txt").write_text("n")
    data, files, left = _make_bundle(tmp_path, "zip", "keep")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert sorted(z.namelist()) == ["a.pdf", "note.txt", "sub/a.pdf"] and files == 3 and left == []
    data, _, _ = _make_bundle(tmp_path, "zip", "flatten")
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        assert sorted(z.namelist()) == ["a (2).pdf", "a.pdf", "note.txt"]
    data, files, left = _make_bundle(tmp_path, "pdf", "keep")
    assert data.startswith(b"%PDF") and files == 2 and left == ["note.txt"]
    assert steps.bundle_name({"op": "zip", "settings": {"dated": True}}, "Month end", "2026-11-03") == "Month end 2026-11-03.zip"


def test_a_long_text_breaks_into_pages_and_long_lines_wrap():
    out = pdf.to_pdf((("x" * 300) + "\n").encode() * 100, "txt")
    assert out.count(b"/Type /Page ") == -(-(100 * -(-300 // pdf.COLUMNS)) // pdf.ROWS)


JPEG_REAL = bytes.fromhex(
    "ffd8ffe000104a46494600010100000100010000ffdb004300080606070605080707070909080a0c140d0c0b0b0c1912130f141d1a1f1e1d1a1c1c20242e2720"
    "222c231c1c2837292c30313434341f27393d38323c2e333432ffc0000b080001000101011100ffc4001f0000010501010101010100000000000000000102030405"
    "060708090a0bffc400b5100002010303020403050504040000017d01020300041105122131410613516107227114328191a1082342b1c11552d1f02433627282"
    "090a161718191a25262728292a3435363738393a434445464748494a535455565758595a636465666768696a737475767778797a838485868788898a92939495"
    "969798999aa2a3a4a5a6a7a8a9aab2b3b4b5b6b7b8b9bac2c3c4c5c6c7c8c9cad2d3d4d5d6d7d8d9dae1e2e3e4e5e6e7e8e9eaf1f2f3f4f5f6f7f8f9faffda0008"
    "010100003f00fbd3ffd9")
