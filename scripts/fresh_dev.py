"""Wipe the dev database and start it over with one IT Admin (the user, 13 Nov 2026: "wipe it, provide fresh data").

    environ-engine\\Scripts\\python.exe scripts\\fresh_dev.py            then: python -m engine, and scripts\\seed_dev.py

With the Engine stopped, it
  1. refuses the test databases (a URL equal to FALCON_TEST_DATABASE_URL, or with "test" in it) and a running Engine,
  2. saves the whole dev database first, with pg_dump, to data/backups/falcon-<when>.sql (git-ignored), and stops if it cannot,
  3. drops every table and migrates afresh: Falcon's own actions are in the library from the start (engine/control/starter.py),
  4. makes the first IT Admin, ADM-01 in Operations, and writes its settings to data/admin.json and to this machine's Operator Client
     settings (the keys are derived from the master secret, which is kept),
  5. forgets the drill machines (data/drill/state.json) and the seed's and the hands-on's folders, which belonged to the old database.
"""
from __future__ import annotations

import asyncio
import json
import os
import shutil
import socket
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from common import dotenv


def refuse(why: str) -> None:
    sys.exit(f"fresh_dev: {why}")


def engine_running(port: int) -> bool:
    with socket.socket() as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", port)) == 0


def backup(url: str) -> Path:
    dump = shutil.which("pg_dump")
    if not dump:
        for v in ("18", "17", "16"):
            p = Path(rf"C:\Program Files\PostgreSQL\{v}\bin\pg_dump.exe")
            if p.exists():
                dump = str(p)
                break
    if not dump:
        refuse("pg_dump was not found, so the database cannot be saved first; nothing was changed")
    out = ROOT / "data" / "backups" / f"falcon-{datetime.now(timezone.utc).astimezone():%Y%m%d-%H%M%S}.sql"
    out.parent.mkdir(parents=True, exist_ok=True)
    u = urlparse(url)
    env = {**os.environ, "PGPASSWORD": u.password or ""}
    got = subprocess.run([dump, "-h", u.hostname or "localhost", "-p", str(u.port or 5432), "-U", u.username or "falcon", "-f", str(out),
                          (u.path or "/falcon").lstrip("/")], env=env, capture_output=True, text=True, check=False)
    if got.returncode != 0 or not out.exists() or out.stat().st_size == 0:
        refuse(f"the database could not be saved first ({got.stderr.strip()[:200]}); nothing was changed")
    return out


async def wipe_and_start(url: str) -> tuple[int, str, str]:
    import asyncpg

    from engine.__main__ import provision_first_admin
    from engine.config import Settings
    from engine.control import starter
    from engine.database import Database
    from engine.master_secret import load_or_create

    conn = await asyncpg.connect(url)
    try:
        await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    finally:
        await conn.close()
    db = Database(url)
    await db.connect()
    try:
        await db.migrate()
        await starter.ensure(db)
        settings = Settings.from_env()
        secret = settings.master_secret or load_or_create(settings.secret_path)
        return await provision_first_admin(db, secret, "ADM-01", "Operations")
    finally:
        await db.close()


def write_settings(client_id: str, key: str, port: int) -> None:
    old = json.loads((ROOT / "data" / "admin.json").read_text(encoding="utf-8")) if (ROOT / "data" / "admin.json").exists() else {}
    cfg = {"engine_host": old.get("engine_host", "127.0.0.1"), "engine_port": old.get("engine_port", port), "client_id": client_id, "client_key": key,
           "tls": old.get("tls", True), "ca_cert": old.get("ca_cert", str(ROOT / "data" / "engine.crt")), "signer": "", "prefs": old.get("prefs", {}), "cache": {}}
    (ROOT / "data" / "admin.json").write_text(json.dumps(cfg, indent=2), encoding="utf-8")
    from operator_client.core.config import LocalConfig

    local = LocalConfig.load()
    local.client_id, local.client_key = client_id, key
    local.engine_host, local.engine_port, local.tls, local.ca_cert = cfg["engine_host"], cfg["engine_port"], cfg["tls"], cfg["ca_cert"]
    local.save()


def forget_old_machines() -> None:
    drill = ROOT / "data" / "drill"
    (drill / "state.json").unlink(missing_ok=True)
    if drill.exists():
        for d in drill.iterdir():
            if d.is_dir() and d.name != "shots":
                shutil.rmtree(d, ignore_errors=True)
    for d in ("seed", "hands-on"):
        shutil.rmtree(ROOT / "data" / d, ignore_errors=True)


def main() -> int:
    dotenv.load()
    url, test = os.environ.get("FALCON_DATABASE_URL"), os.environ.get("FALCON_TEST_DATABASE_URL")
    if not url:
        refuse("FALCON_DATABASE_URL is not set")
    if url == test or "test" in (urlparse(url).path or ""):
        refuse("that is a test database; this wipes only the dev one")
    port = int(os.environ.get("FALCON_PORT", "7400"))
    if engine_running(port):
        refuse(f"an Engine is running on {port}; stop it first (it would keep serving the old data)")
    saved = backup(url)
    print(f"saved the old database to {saved}")
    account_id, client_id, key = asyncio.run(wipe_and_start(url))
    write_settings(client_id, key, port)
    forget_old_machines()
    print(f"the database is fresh: ADM-01 (account {account_id}) in Operations, and Falcon's own actions")
    print("its settings are in data/admin.json and this machine's Operator Client settings")
    print("next: environ-engine\\Scripts\\python.exe -m engine, then environ-operator\\Scripts\\python.exe scripts\\seed_dev.py")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
