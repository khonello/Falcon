"""Backing the database up and putting it back (engine/backup.py, Phase 10)."""

from __future__ import annotations

from pathlib import Path

import pytest

from engine import backup
from tests.conftest import TEST_DB_URL, requires_db

pytestmark = [requires_db, pytest.mark.skipif(backup.tool("pg_dump") is None, reason="PostgreSQL's client tools are not here")]


async def test_a_backup_is_made_and_put_back_with_what_was_in_it(engine, org, tmp_path: Path):
    import asyncio

    await engine.db.pool.execute("INSERT INTO departments (name) VALUES ('Backed up')")
    dump = await asyncio.to_thread(backup.backup, TEST_DB_URL, tmp_path / "f.dump")
    assert dump.stat().st_size > 1000
    await engine.db.pool.execute("UPDATE departments SET name = 'Changed after' WHERE name = 'Backed up'")
    await engine.db.close()                                              # (the Engine is stopped before a restore)
    await asyncio.to_thread(backup.restore, TEST_DB_URL, dump)
    await engine.db.connect()
    names = {r["name"] for r in await engine.db.pool.fetch("SELECT name FROM departments")}
    assert "Backed up" in names and "Changed after" not in names


def test_the_password_never_goes_on_a_command_line():
    args, env = backup._conninfo("postgresql://falcon:s3cr%40t@db.internal:5433/falcon")
    assert args == ["--host", "db.internal", "--port", "5433", "--username", "falcon", "--dbname", "falcon"]
    assert env["PGPASSWORD"] == "s3cr@t" and "s3cr" not in " ".join(args)


def test_a_restore_needs_to_be_meant(capsys):
    assert backup.main(["restore", "x.dump"], "postgresql://x@localhost/x") == 2
    assert "--yes" in capsys.readouterr().out
