"""Drill: Falcon's own PostgreSQL, set up for real on this PC and taken out again (installers/windows/private_pg.py).

    python scripts/private_pg_drill.py <EDB pgsql folder> [--root C:\\FalconPgDrill] [--keep]

Run as an administrator. It uses its own service name (FalconPostgresDrill) and folder, so the machine's own PostgreSQL is never touched.
It checks: the cluster answers on localhost only, on a port that is not 5432; the Engine's role logs in; the superuser cannot; nothing went
on PATH; the uninstall removes the service.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import secrets
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from installers.engine import render
from installers.windows.private_pg import PrivatePostgres, _service_exists, trim


async def _login(url: str) -> str:
    import asyncpg

    conn = await asyncpg.connect(url, timeout=10)
    try:
        return str(await conn.fetchval("SELECT current_user || '@' || current_database()"))
    finally:
        await conn.close()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("pgsql", type=Path)
    ap.add_argument("--root", type=Path, default=Path(r"C:\FalconPgDrill"))
    ap.add_argument("--keep", action="store_true")
    a = ap.parse_args()
    ok = True

    def check(what: str, good: bool) -> None:
        nonlocal ok
        ok &= good
        print(f"  [{'ok' if good else 'FAIL'}] {what}", flush=True)

    size = trim(a.pgsql, a.root / "pgsql")
    print(f"trimmed: {size >> 20} MB")
    pg = PrivatePostgres(bin=a.root / "pgsql" / "bin", pgdata=a.root / "data" / "pgdata", secrets_dir=a.root / "data", service="FalconPostgresDrill")
    (a.root / "data").mkdir(parents=True, exist_ok=True)
    try:
        for step in (pg.init, pg.register, pg.lock, pg.start):
            print(step.__name__ + ":", step(), flush=True)
        password = secrets.token_urlsafe(24)
        print("role:", pg.make_role("falcon", "falcon", render.postgres_role_sql(password)))
        port = pg.port()
        check(f"its own port ({port}), not 5432", port is not None and port != 5432)
        check("the Engine's role logs in", asyncio.run(_login(pg.url("falcon", "falcon", password))) == "falcon@falcon")
        su = pg.password_file.read_text(encoding="utf-8").strip()
        try:
            asyncio.run(_login(f"postgresql://postgres:{su}@127.0.0.1:{port}/postgres"))
            check("the superuser is refused", False)
        except Exception as exc:                                                   # noqa: BLE001
            check(f"the superuser is refused ({type(exc).__name__})", "pg_hba" in str(exc) or "no pg_hba.conf entry" in str(exc))
        try:
            asyncio.run(_login(f"postgresql://falcon:{password}@127.0.0.1:{port}/postgres"))
            check("the Engine's role reaches no other database", False)
        except Exception as exc:                                                   # noqa: BLE001
            check("the Engine's role reaches no other database", "pg_hba" in str(exc))
        net = subprocess.run(["netstat", "-ano", "-p", "TCP"], capture_output=True, text=True, check=False).stdout
        listening = [ln.split()[1] for ln in net.splitlines() if ln.strip().startswith("TCP") and f":{port} " in ln and "LISTENING" in ln]
        check(f"listens on this machine only ({', '.join(listening)})", bool(listening) and all(x.startswith("127.0.0.1:") for x in listening))
        check("nothing on PATH", str(a.root).lower() not in os.environ.get("PATH", "").lower())
        q = subprocess.run(["sc.exe", "qc", pg.service], capture_output=True, text=True, check=False).stdout
        check("runs as its own virtual account", "NT SERVICE\\FalconPostgresDrill" in q)
        acl = subprocess.run(["icacls", str(pg.pgdata)], capture_output=True, text=True, check=False).stdout
        check("pgdata: no Users, no Everyone", "BUILTIN\\Users" not in acl and "Everyone" not in acl and "Authenticated Users" not in acl)
        print("again (repair):", pg.init(), "/", pg.register())
    finally:
        if not a.keep:
            print("unregister:", pg.unregister())
            check("the service is gone", not _service_exists(pg.service))
            shutil.rmtree(a.root, ignore_errors=True)
    print("drill passed" if ok else "drill FAILED")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
