"""Authentication (spec 8.1, 8.2).

Model: one master secret on the Engine host, never transmitted (`engine.master_secret`). Each
client holds `derived_key = HMAC-SHA256(master_secret, "<client_id>:<key_generation>")`, handed
to its install package once at provisioning. Handshake per connection:

    Engine -> client   push    auth.challenge  {"nonce": "<hex>"}          fresh per connection, single use
    client -> Engine   request auth.respond    {"client_id", "hmac": HMAC-SHA256(derived_key, nonce), "hostname"}
    Engine             re-derives the key, constant-time compares, binds an Identity to the connection.

`pcs.key_generation` lets a key be rotated (`hierarchy.pc_rekey`) without changing the client_id;
offboarding an account makes its client_id unresolvable, which is revocation. A failed handshake
is audited (`auth.failed`) and the connection stays unauthenticated.

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
from datetime import datetime, timezone
from typing import Any

from engine.dispatch import Context, Identity, handler
from engine.isotime import parse_iso
from protocol import ErrorCode, ProtocolError

log = logging.getLogger(__name__)


def new_nonce() -> str:
    return secrets.token_hex(32)


def derive_client_key(master_secret: bytes, client_id: str, key_generation: int = 1) -> bytes:
    return hmac.new(master_secret, f"{client_id}:{int(key_generation)}".encode(), hashlib.sha256).digest()


def expected_response(derived_key: bytes, nonce: str) -> str:
    return hmac.new(derived_key, nonce.encode("utf-8"), hashlib.sha256).hexdigest()


def verify(master_secret: bytes | None, client_id: str, nonce: str, presented_hmac: str,
           key_generation: int = 1) -> bool:
    """Constant-time check of the client's answer to this connection's nonce."""
    if master_secret is None or not nonce or not client_id:
        return False
    key = derive_client_key(master_secret, client_id, key_generation)
    return hmac.compare_digest(expected_response(key, nonce), str(presented_hmac))


async def load_identity(ctx: Context, client_id: str, announced_hostname: str | None) -> Identity:
    """Resolve a provisioned client_id to the account bound to that PC.

    The client also announces its hostname; a mismatch against the provisioned PC is a
    deviation ('account_bound_to_one_pc'): logged and surfaced, the connection still proceeds
    as the provisioned identity (never silently tolerated, never silently corrected).

    Without a database (scaffold/protocol tests) the identity is just the claimed client_id.
    """
    if not ctx.engine.db.connected:
        return Identity(client_id=client_id)
    account = await ctx.engine.db.accounts.by_client_id(client_id)
    if account is None:
        raise ProtocolError(ErrorCode.UNAUTHENTICATED, "client_id is not provisioned")
    await _announce_hostname(ctx, account, announced_hostname)
    return _identity_of(account, client_id)


def _identity_of(account: dict[str, Any], client_id: str) -> Identity:
    return Identity(account_id=account["id"], role=account["role"], pc_id=account["bound_pc_id"],
                    department_id=account["department_id"], client_id=client_id)


async def _announce_hostname(ctx: Context, account: dict[str, Any], announced_hostname: str | None) -> dict[str, str] | None:
    """Hostname mismatch is a *deviation* (hierarchy-system-design → System Expectations): logged
    and surfaced, the connection proceeds as the provisioned identity. The key proves the install
    package; the hostname says where it is being used from."""
    if announced_hostname and account["hostname"] and announced_hostname == account["hostname"] and account["bound_pc_id"]:
        from engine.console import issues

        await issues.resolve_source(ctx.engine, "hostname_mismatch", account["bound_pc_id"], "It presented its registered name again")
    if announced_hostname and account["hostname"] and announced_hostname != account["hostname"]:
        deviation_id = await ctx.engine.audit.deviation(
            "account_bound_to_one_pc", surfaced_to_account_id=account["id"],
            observed_account_id=account["id"], observed_pc_id=account["bound_pc_id"],
            detail={"expected_hostname": account["hostname"], "announced_hostname": announced_hostname})
        if account["bound_pc_id"] and deviation_id is not None:
            from engine.console import issues

            await issues.raise_issue(
                ctx.engine, type_="deviation", severity="medium", title="Machine presented another name", subject=f"presented {announced_hostname}",
                pc_id=account["bound_pc_id"], source_table="hostname_mismatch", source_id=account["bound_pc_id"],
                detail={"what": "name", "expected": account["hostname"], "presented": announced_hostname, "deviation_id": deviation_id})
            from engine.console import accountability

            await accountability.never(
                ctx.engine, "cert", kind="pc", subject_pc_id=account["bound_pc_id"], pc_id=account["bound_pc_id"],
                subject_department_id=account["department_id"], short="{who} presented another name",
                expected=f"The name {account['hostname']}", happened=f"The name {announced_hostname}",
                detail={"expected": account["hostname"], "presented": announced_hostname},
                source_key=f"cert:{account['bound_pc_id']}:{announced_hostname}:{datetime.now(timezone.utc).date().isoformat()}")
        # said back to the client too, so the person at it is told -- surfaced, never silently tolerated
        return {"expected": account["hostname"], "announced": announced_hostname}
    return None


async def _fail(ctx: Context, client_id: str, reason: str, *, kind: str = "other", claimed: str | None = None,
                account: dict[str, Any] | None = None, **more: Any) -> None:
    """Audit and refuse. The reason to the client is deliberately uniform (no oracle); the trail keeps what the Registry shows: the
    address, the name the machine claimed, which machine the client id belongs to (if any), and why (`kind`: unknown, wrong_key, old_key,
    stale)."""
    peer = ctx.connection.peer
    log.warning("auth failed for client_id=%r from %s: %s", client_id, peer, reason)
    if ctx.engine.db.connected:
        detail: dict[str, Any] = {"reason": reason, "kind": kind, "peer": str(peer), "address": str(peer[0]) if peer else None,
                                  "claimed_name": (str(claimed)[:120] if claimed else None), **more}
        if account is not None:
            detail.update(pc_id=account["bound_pc_id"], machine=account["hostname"], key_generation=account.get("key_generation") or 1)
        await ctx.engine.db.audit.write({"action": "auth.failed", "target_type": "client", "target_id": client_id, "detail": detail})
    raise ProtocolError(ErrorCode.UNAUTHENTICATED, "authentication failed")


async def _remember_agent(ctx: Context, payload: dict[str, Any]) -> None:
    """What the machine says about itself (the Worker's version, the OS, when the agent started) and the address the
    Engine saw it come from: kept on the PC so a console can show them. The client's word, the Engine's address."""
    pc_id = ctx.identity.pc_id if ctx.identity else None
    if pc_id is None or not ctx.engine.db.connected:
        return
    peer = getattr(ctx.connection, "peer", None)
    started = None
    try:
        raw = payload.get("started_at")
        started = parse_iso(str(raw)) if raw else None
    except ValueError:
        started = None
    await ctx.engine.db.accounts.set_agent(pc_id, ip=str(peer[0]) if peer else None,
                                           os=(str(payload["os"])[:120] if payload.get("os") else None),
                                           version=(str(payload["version"])[:40] if payload.get("version") else None),
                                           started_at=started)


@handler("auth.respond")
async def auth_respond(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    client_id = str(payload.get("client_id", ""))
    conn = ctx.connection
    engine = ctx.engine
    if engine.settings.dev_bypass_auth:
        ctx.identity = await load_identity(ctx, client_id, payload.get("hostname"))
    else:
        if conn.pending_nonce is None:
            await _fail(ctx, client_id, "no outstanding challenge (already used or never issued)", kind="stale", claimed=payload.get("hostname"))
        nonce, conn.pending_nonce = conn.pending_nonce, None
        if not engine.db.connected:
            # Protocol-only runs (no database): there is nobody to be, but the challenge must still be
            # answered with the key derived for the claimed client_id.
            if not verify(engine.master_secret, client_id, nonce, str(payload.get("hmac", ""))):
                await _fail(ctx, client_id, "challenge failed", kind="wrong_key", claimed=payload.get("hostname"))
            ctx.identity = Identity(client_id=client_id)
        else:
            account = await engine.db.accounts.by_client_id(client_id)
            if account is None:
                await _fail(ctx, client_id, "client_id is not provisioned or its account is not active", kind="unknown", claimed=payload.get("hostname"))
            generation = account.get("key_generation") or 1
            presented = str(payload.get("hmac", ""))
            if not verify(engine.master_secret, client_id, nonce, presented, generation):
                old = next((g for g in range(1, generation) if verify(engine.master_secret, client_id, nonce, presented, g)), None)
                pc = await engine.db.accounts.pc(account["bound_pc_id"]) if account["bound_pc_id"] else None
                address = str(conn.peer[0]) if conn.peer else None
                await _fail(ctx, client_id, "challenge failed" if old is None else f"the key replaced by no. {generation} (no. {old}) was used",
                            kind="wrong_key" if old is None else "old_key", claimed=payload.get("hostname"), account=account,
                            same_address=(pc["last_ip"] == address) if pc and pc["last_ip"] else None,
                            **({"old_generation": old} if old is not None else {}))
            mismatch = await _announce_hostname(ctx, account, payload.get("hostname"))
            ctx.identity = _identity_of(account, client_id)
    conn.authenticated = True
    await _remember_agent(ctx, payload)
    await ctx.engine.audit.record(ctx, "auth.connected", target_type="client", target_id=client_id)
    await ctx.engine.on_connected(conn)
    ident = ctx.identity
    out = {"authenticated": True, "client_id": client_id, "account_id": ident.account_id,
           "role": ident.role, "pc_id": ident.pc_id, "department_id": ident.department_id}
    if not engine.settings.dev_bypass_auth and engine.db.connected and mismatch:
        out["hostname_mismatch"] = mismatch
    return out
