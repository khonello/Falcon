"""Entry points:

    python -m engine                          run the Engine
    python -m engine bootstrap <hostname>     provision the first Super User (+ its workstation)
                                              on an empty database and print its client_id + key ONCE
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


async def bootstrap(settings: Settings, hostname: str) -> int:
    if not settings.database_url:
        print("FALCON_DATABASE_URL is not set", file=sys.stderr)
        return 2
    db = Database(settings.database_url)
    await db.connect()
    try:
        await db.migrate()
        existing = [a for a in await db.accounts.list_all() if a["role"] == "super_user" and a["status"] == "active"]
        if existing:
            print(f"a Super User already exists (account {existing[0]['id']}); bootstrap refused", file=sys.stderr)
            return 1
        client_id = secrets.token_urlsafe(16)
        pc_id = await db.accounts.create_pc(hostname, None, "super_user_workstation", client_id)
        account_id = await db.accounts.create("super_user", None, pc_id)
        await db.audit.write({"action": "bootstrap.super_user", "target_type": "accounts", "target_id": str(account_id),
                              "detail": {"hostname": hostname, "pc_id": pc_id}})
        from engine.master_secret import load_or_create

        secret = settings.master_secret or load_or_create(settings.secret_path)
        from engine.auth import derive_client_key

        print(f"Super User account {account_id} on pc {pc_id} ({hostname})")
        print(f"client_id:  {client_id}")
        print(f"client_key: {derive_client_key(secret, client_id).hex()}")
        print("Give both to the Super User's Operator Client install. They are not shown again.")
        return 0
    finally:
        await db.close()


def main() -> None:
    settings = Settings.from_env()
    logging.basicConfig(
        level=logging.DEBUG if settings.debug else logging.INFO,
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    if len(sys.argv) > 1 and sys.argv[1] == "bootstrap":
        if len(sys.argv) < 3:
            sys.exit("usage: python -m engine bootstrap <hostname>")
        sys.exit(asyncio.run(bootstrap(settings, sys.argv[2])))
    if len(sys.argv) > 1 and sys.argv[1] == "gencert":
        if len(sys.argv) < 3:
            sys.exit("usage: python -m engine gencert <name>[,<name>,<ip>...] [out_dir]")
        from pathlib import Path

        from engine.tls import generate_self_signed

        cert, key = generate_self_signed(sys.argv[2], Path(sys.argv[3] if len(sys.argv) > 3 else "data"))
        print(f"certificate: {cert}   (ship this in every client install package; clients pin it)")
        print(f"private key: {key}    (Engine only)")
        print(f"set FALCON_TLS_CERT={cert} FALCON_TLS_KEY={key}")
        return
    asyncio.run(Engine(settings).run())


if __name__ == "__main__":
    main()
