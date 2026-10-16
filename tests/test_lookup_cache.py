"""The console's local memory of lookups: per account, dated, bounded, and never an error."""

from __future__ import annotations

from pathlib import Path

from operator_client.core.lookup_cache import MAX_AGE_DAYS, MAX_ITEMS, LookupCache


def test_it_keeps_what_it_was_given_and_says_when(tmp_path: Path):
    clock = [1000.0]
    c = LookupCache(tmp_path / "c.json", now=lambda: clock[0])
    c.adopt("alice@engine")
    c.put("people", [{"name": "Kojo"}])
    assert c.get("people") == {"at": 1000.0, "items": [{"name": "Kojo"}]}
    again = LookupCache(tmp_path / "c.json", now=lambda: clock[0])             # a new run of the console finds it
    assert again.owner == "alice@engine" and again.get("people")["items"] == [{"name": "Kojo"}]


def test_another_account_never_sees_it(tmp_path: Path):
    c = LookupCache(tmp_path / "c.json")
    c.adopt("alice")
    c.put("people", [{"name": "Kojo"}])
    c.adopt("bob")
    assert c.get("people")["items"] == []
    assert LookupCache(tmp_path / "c.json").get("people")["items"] == []        # and it is gone from disk, not just hidden


def test_nothing_is_kept_before_it_is_known_whose_it_is(tmp_path: Path):
    c = LookupCache(tmp_path / "c.json")
    c.put("people", [{"name": "Kojo"}])
    assert c.get("people")["items"] == [] and not (tmp_path / "c.json").exists()


def test_old_data_is_not_offered(tmp_path: Path):
    clock = [0.0]
    c = LookupCache(tmp_path / "c.json", now=lambda: clock[0])
    c.adopt("a")
    c.put("x", [1])
    clock[0] = MAX_AGE_DAYS * 86400 + 1
    assert c.get("x")["items"] == []


def test_a_section_is_bounded(tmp_path: Path):
    c = LookupCache(tmp_path / "c.json")
    c.adopt("a")
    c.put("x", list(range(MAX_ITEMS + 500)))
    assert len(c.get("x")["items"]) == MAX_ITEMS


def test_recent_things_move_up_and_are_not_repeated(tmp_path: Path):
    c = LookupCache(tmp_path / "c.json")
    c.adopt("a")
    for name in ("a.txt", "b.txt", "c.txt", "a.txt"):
        c.remember("files", {"path": name}, "path", limit=3)
    assert [i["path"] for i in c.get("files")["items"]] == ["a.txt", "c.txt", "b.txt"]
    c.remember("files", {"path": "d.txt"}, "path", limit=3)
    assert [i["path"] for i in c.get("files")["items"]] == ["d.txt", "a.txt", "c.txt"]


def test_a_damaged_or_unwritable_file_is_an_empty_cache_not_an_error(tmp_path: Path):
    bad = tmp_path / "c.json"
    bad.write_text("{not json", encoding="utf-8")
    c = LookupCache(bad)
    assert c.get("anything")["items"] == []
    c.adopt("a")
    c.put("x", [1])                                                              # rewrites it cleanly
    assert LookupCache(bad).get("x")["items"] == [1]
    blocked = LookupCache(tmp_path / "is-a-folder" / "c.json")
    (tmp_path / "is-a-folder").write_text("a file where a folder should be", encoding="utf-8")
    blocked.adopt("a")
    blocked.put("x", [1])                                                        # cannot be written: silently fine
    assert blocked.get("x")["items"] == [1]
