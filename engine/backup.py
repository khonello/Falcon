"""Backing the Engine's database up, and putting it back (Phase 10, ops).

    python -m engine backup [file]          a compressed dump of the database (pg_dump, custom format) -- default data/backups/falcon-<when>.dump
    python -m engine restore <file> --yes   the database as the dump has it (pg_restore --clean): what is there now is replaced

PostgreSQL's own tools do the work (`pg_dump`, `pg_restore`, found on PATH or where PostgreSQL installs them). The connection comes from
FALCON_DATABASE_URL, the password is handed over in the environment (never on a command line). The master secret is NOT in the database
and is not in a backup: without it no machine's key can be made again, so it is backed up apart, offline (`data/master.secret`).
"""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from urllib.parse import unquote, urlsplit

WINDOWS_PLACES = [Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "PostgreSQL" / v / "bin" for v in ("18", "17", "16", "15")]


def tool(name: str) -> str | None:
    found = shutil.which(name)
    if found:
        return found
    for place in WINDOWS_PLACES:
        exe = place / f"{name}.exe"
        if exe.is_file():
            return str(exe)
    return None


def _conninfo(url: str) -> tuple[list[str], dict[str, str]]:
    """pg_dump's arguments and environment for a postgresql:// URL; the password goes in PGPASSWORD, not the arguments."""
    u = urlsplit(url)
    args = ["--host", u.hostname or "localhost", "--port", str(u.port or 5432), "--username", unquote(u.username or "postgres"),
            "--dbname", unquote(u.path.lstrip("/")) or "postgres"]
    env = dict(os.environ)
    if u.password:
        env["PGPASSWORD"] = unquote(u.password)
    return args, env


def backup(database_url: str, out: Path | None = None, *, folder: Path = Path("data/backups")) -> Path:
    exe = tool("pg_dump")
    if exe is None:
        raise RuntimeError("pg_dump is not here: install PostgreSQL's client tools, or put them on PATH")
    target = out or folder / f"falcon-{datetime.now().astimezone():%Y%m%d-%H%M%S}.dump"
    target.parent.mkdir(parents=True, exist_ok=True)
    args, env = _conninfo(database_url)
    done = subprocess.run([exe, *args, "--format=custom", "--no-owner", "--file", str(target)], env=env, capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise RuntimeError((done.stderr or done.stdout).strip()[-400:] or f"pg_dump stopped with code {done.returncode}")
    return target


def restore(database_url: str, dump: Path) -> None:
    exe = tool("pg_restore")
    if exe is None:
        raise RuntimeError("pg_restore is not here: install PostgreSQL's client tools, or put them on PATH")
    if not dump.is_file():
        raise RuntimeError(f"there is no dump at {dump}")
    args, env = _conninfo(database_url)
    done = subprocess.run([exe, *args, "--clean", "--if-exists", "--no-owner", "--single-transaction", str(dump)], env=env,
                          capture_output=True, text=True, check=False)
    if done.returncode != 0:
        raise RuntimeError((done.stderr or done.stdout).strip()[-400:] or f"pg_restore stopped with code {done.returncode}")


def main(argv: list[str], database_url: str | None) -> int:
    if not database_url:
        print("FALCON_DATABASE_URL is not set (run `python -m engine setup` first)")
        return 2
    try:
        if argv and argv[0] == "restore":
            if len(argv) < 2 or "--yes" not in argv:
                print("usage: python -m engine restore <file> --yes   (what is in the database now is replaced by the dump; stop the Engine first)")
                return 2
            restore(database_url, Path(argv[1]))
            print(f"restored from {argv[1]}. Start the Engine; machines keep their keys as long as data/master.secret is the same one.")
            return 0
        made = backup(database_url, Path(argv[1]) if len(argv) > 1 else None)
        print(f"backed up to {made} ({made.stat().st_size // 1024} KB).")
        print("The master secret is not in it: keep data/master.secret backed up apart, offline -- without it no machine's key can be made again.")
        return 0
    except RuntimeError as exc:
        print(f"not done: {exc}")
        return 1
