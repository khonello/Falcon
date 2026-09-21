"""Authentication -- shape scaffolded now, cryptographic logic filled in last (spec 8.1, 8.2).

Model: one master secret on the Engine host, never transmitted. Each client holds
`derived_key = HMAC(master_secret, client_id)`. Handshake per connection:

    Engine -> client   push    auth.challenge  {"nonce": "<hex>"}
    client -> Engine   request auth.respond    {"client_id": "...", "hmac": "<HMAC(derived_key, nonce)>"}
    Engine             re-derives the key, compares, binds an Identity to the connection.

With FALCON_DEV_BYPASS_AUTH the handshake is skipped *entirely*: no challenge is sent and the
connection is treated as authenticated as whatever identity the client claims in `auth.respond`
(or anonymous). A hard, visible skip logged loudly at startup -- not a check that quietly
returns True.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
from typing import Any

from engine.dispatch import Context, Identity, handler
from protocol import ErrorCode, ProtocolError

log = logging.getLogger(__name__)


def new_nonce() -> str:
    return secrets.token_hex(32)


def derive_client_key(master_secret: bytes, client_id: str) -> bytes:
    return hmac.new(master_secret, client_id.encode("utf-8"), hashlib.sha256).digest()


def expected_response(derived_key: bytes, nonce: str) -> str:
    return hmac.new(derived_key, nonce.encode("utf-8"), hashlib.sha256).hexdigest()


def verify(master_secret: bytes | None, client_id: str, nonce: str, presented_hmac: str) -> bool:
    """SCAFFOLD: always accepts. Real implementation (last build step):

        key = derive_client_key(master_secret, client_id)
        return hmac.compare_digest(expected_response(key, nonce), presented_hmac)
    """
    log.warning("auth.verify is a SCAFFOLD stub -- accepting client_id=%r unchecked", client_id)
    return True


async def load_identity(ctx: Context, client_id: str) -> Identity:
    """Resolve a provisioned client_id to account/role/PC. SCAFFOLD: echoes the claim.

    Real: look up the account bound to this client, compare the announced PC against
    `accounts.bound_pc_id`, and write a `deviation_log` row on mismatch (database-schema.md 1).
    """
    return Identity(client_id=client_id)


@handler("auth.respond")
async def auth_respond(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    client_id = str(payload.get("client_id", ""))
    conn = ctx.connection
    if not ctx.engine.settings.dev_bypass_auth:
        if conn.pending_nonce is None:
            raise ProtocolError(ErrorCode.UNAUTHENTICATED, "no outstanding challenge")
        nonce, conn.pending_nonce = conn.pending_nonce, None
        if not verify(ctx.engine.master_secret, client_id, nonce, str(payload.get("hmac", ""))):
            raise ProtocolError(ErrorCode.UNAUTHENTICATED, "challenge failed")
    ctx.identity = await load_identity(ctx, client_id)
    conn.authenticated = True
    await ctx.engine.audit.record(ctx, "auth.connected", target_type="client", target_id=client_id)
    return {"authenticated": True, "client_id": client_id}
