"""Entry points (settings come from `.env` -- no shell variables needed):

    python -m engine setup [--admin-url ...]  make a fresh clone ready: .env, certificate, databases, schema, secret,
                                              the first IT Admin (see engine/setup.py)
    python -m engine                          run the Engine
    python -m engine bootstrap <hostname> [department]   provision the first IT Admin (+ its workstation, in a department named
                                              IT unless one is given) on an empty database and print its client_id + key ONCE
    python -m engine gencert <names> [out_dir]  self-signed TLS certificate for the Engine (names: DNS/IP, comma-separated);
                                              ship the .crt in every client install package (pinned)
"""

from __future__ import annotations

import asyncio
import logging
import secrets
import sys

from engine.config import Settings
from engine.database import Database
from engine.server import Engine

FIRST_DEPARTMENT = "IT"


async def provision_first_admin(db: Database, secret: bytes, hostname: str, department: str = FIRST_DEPARTMENT) -> tuple[int, str, str]:
    """Version 1 (docs/design/v1-it-admin.md): the first IT Admin, its workstation and the department it sits in (a label; any Admin makes
    more). (account id, client id, hex key); the key is never stored."""
    from engine.auth import derive_client_key

    client_id = secrets.token_urlsafe(16)
    found = next((d for d in await db.accounts.list_departments() if d["name"] == department), None)
    async with db.pool.acquire() as conn, conn.transaction():
        dept_id = found["id"] if found else await conn.fetchval("INSERT INTO departments (name) VALUES ($1) RETURNING id", department)
        pc_id = await conn.fetchval(
            "INSERT INTO pcs (hostname, department_id, pc_type, client_id) VALUES ($1, $2, 'admin_workstation', $3) RETURNING id",
            hostname, dept_id, client_id)
        account_id = await conn.fetchval(
            "INSERT INTO accounts (role, department_id, bound_pc_id) VALUES ('admin', $1, $2) RETURNING id", dept_id, pc_id)
        await conn.execute("UPDATE departments SET created_by_account_id = $2 WHERE id = $1 AND created_by_account_id IS NULL", dept_id, account_id)
    await db.audit.write({"action": "bootstrap.admin", "target_type": "accounts", "target_id": str(account_id),
                          "detail": {"hostname": hostname, "pc_id": pc_id, "department_id": dept_id}})
    return account_id, client_id, derive_client_key(secret, client_id).hex()


async def first_account(db: Database, secret: bytes, settings: Settings, hostname: str, department: str = FIRST_DEPARTMENT) -> tuple[str, int, str, str] | tuple[str, int]:
    """The first account the Engine needs: the first IT Admin. Returns (who, account id, client id, key), or (who, existing account id)
    when one is already there. The full design's first account (FALCON_ADMIN_SCOPE=department) is parked (parked/engine/bootstrap.py)."""
    if settings.admin_scope != "organisation":
        raise SystemExit("FALCON_ADMIN_SCOPE=department needs the parked first account (parked/engine/bootstrap.py); this version has IT Admins only")
    existing = [a for a in await db.accounts.list_all() if a["role"] == "admin" and a["status"] == "active"]
    if existing:
        return "an Admin", existing[0]["id"]
    return ("IT Admin", *await provision_first_admin(db, secret, hostname, department))


async def bootstrap(settings: Settings, hostname: str, department: str = FIRST_DEPARTMENT) -> int:
    if not settings.database_url:
        print("FALCON_DATABASE_URL is not set (run `python -m engine setup` first)", file=sys.stderr)
        return 2
    db = Database(settings.database_url)
    await db.connect()
    try:
        await db.migrate()
        from engine.master_secret import load_or_create

        secret = settings.master_secret or load_or_create(settings.secret_path)
        made = await first_account(db, secret, settings, hostname, department)
        if len(made) == 2:
            print(f"{made[0]} already exists (account {made[1]}); bootstrap refused", file=sys.stderr)
            return 1
        who, account_id, client_id, key = made
        print(f"{who} account {account_id} ({hostname})")
        print(f"client_id:  {client_id}")
        print(f"client_key: {key}")
        print("Give both to that console's install. They are not shown again.")
        return 0
    finally:
        await db.close()


def main() -> None:
    if len(sys.argv) > 1 and sys.argv[1] == "setup":
        from engine.setup import main as setup_main

        sys.exit(setup_main(sys.argv[2:]))
    settings = Settings.from_env()
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    if len(sys.argv) > 1 and sys.argv[1] == "bootstrap":
        if len(sys.argv) < 3:
            sys.exit("usage: python -m engine bootstrap <hostname> [department]")
        sys.exit(asyncio.run(bootstrap(settings, sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else FIRST_DEPARTMENT)))
    if len(sys.argv) > 1 and sys.argv[1] == "gencert":
        if len(sys.argv) < 3:
            sys.exit("usage: python -m engine gencert <name>[,<name>,<ip>...] [out_dir]")
        from pathlib import Path

        from engine.tls import generate_self_signed

        cert, key = generate_self_signed(sys.argv[2], Path(sys.argv[3] if len(sys.argv) > 3 else "data"))
        print(f"certificate: {cert}   (ship this in every client install package; clients pin it)")
        print(f"private key: {key}    (Engine only)")
        print(f"put these in .env:  FALCON_TLS_CERT={cert}  FALCON_TLS_KEY={key}")
        return
    asyncio.run(Engine(settings).run())


if __name__ == "__main__":
    main()
