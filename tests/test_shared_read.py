"""The Worker reading a file never stops the person renaming or deleting it (found by the live drill, 5 Nov 2026: Windows said the file was in use)."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest

from worker_client import flowsync, watcher
from worker_client.sharedread import open_shared


def test_a_file_being_read_can_still_be_renamed_and_deleted_and_the_read_carries_on(tmp_path: Path):
    a, b = tmp_path / "report.xlsx", tmp_path / "final.xlsx"
    a.write_bytes(b"x" * 1000 + b"y" * 1000)
    with open_shared(a) as f:
        assert f.read(1000) == b"x" * 1000
        a.rename(b)                                                     # the person renames it mid-read
        assert b.exists() and not a.exists()
        assert f.read() == b"y" * 1000
        b.unlink()                                                      # and deletes it
    assert not b.exists()


def test_a_file_that_is_not_there_says_so_as_open_does(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        open_shared(tmp_path / "gone.txt")


def test_what_the_worker_hashes_it_reads_this_way(tmp_path: Path, monkeypatch):
    p = tmp_path / "a.txt"
    p.write_bytes(b"hello")
    used = []
    for module in (flowsync, watcher):
        monkeypatch.setattr(module, "open_shared", lambda path, real=open_shared: used.append(path) or real(path))
    assert flowsync.hash_of(p, 1 << 20) == hashlib.sha256(b"hello").hexdigest()
    assert watcher.hash_file(p, 1 << 20) == hashlib.sha256(b"hello").hexdigest()
    assert used == [p, p]
