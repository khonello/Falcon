"""Parked with the Super User (docs/design/v1-it-admin.md), 1 Nov 2026: cut from engine/__main__.py. `first_account` called it when
FALCON_ADMIN_SCOPE is "department"; reconnecting puts it back there."""

import secrets

from engine.database import Database


async def provision_super_user(db: Database, secret: bytes, hostname: str) -> tuple[int, str, str]:
    """The first Super User and its workstation: (account id, client id, hex key). The key is never stored."""
    from engine.auth import derive_client_key

    client_id = secrets.token_urlsafe(16)
    pc_id = await db.accounts.create_pc(hostname, None, "super_user_workstation", client_id)
    account_id = await db.accounts.create("super_user", None, pc_id)
    await db.audit.write({"action": "bootstrap.super_user", "target_type": "accounts", "target_id": str(account_id),
                          "detail": {"hostname": hostname, "pc_id": pc_id}})
    return account_id, client_id, derive_client_key(secret, client_id).hex()
