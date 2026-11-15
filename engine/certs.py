"""The Engine's certificate renews itself, with a rollover, so nobody reinstalls (docs/SEATS-AND-SETUP.md section 10).

    cert.status   {}                  any Admin: the current certificate (names, end, fingerprint) and the next one, if made
    cert.renew    {names?}            any Admin: make the next certificate now (optionally with other names); machines are given it
    cert.switch   {}                  any Admin: start using the next certificate now (it must exist); machines keep trusting both

A daily check does the same by itself: **60 days before the end** the next certificate is made beside the current one (data/next/), the
store is told both (it issues a company file holding both, kept as company.falcon, for Worker setups made from then on), and every
connected machine is pushed `engine.next_certificate {pem}`; a machine that connects later is pushed it as it signs in. **30 days before
the end** the Engine switches: the current pair is kept as engine-old.*, the next becomes the current, and new connections get it. A
machine trusts every certificate in its pinned file, so it keeps working through the switch. One that was off the whole time needs the
current Worker setup zip run on it (its company file holds the new certificate).
"""

from __future__ import annotations

import asyncio
import json
import logging
import shutil
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any

from engine.dispatch import Context, handler
from engine.permissions import require_role
from protocol import ErrorCode, ProtocolError

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

RENEW_BEFORE = timedelta(days=60)
SWITCH_BEFORE = timedelta(days=30)


def describe(pem: bytes) -> dict[str, Any]:
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes

    cert = x509.load_pem_x509_certificate(pem)
    try:
        sans = cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        names = [str(n) for n in sans.get_values_for_type(x509.DNSName)] + [str(n) for n in sans.get_values_for_type(x509.IPAddress)]
    except x509.ExtensionNotFound:
        names = []
    return {"names": names, "not_after": cert.not_valid_after_utc, "sha256": cert.fingerprint(hashes.SHA256()).hex(":").upper()}


class Certificates:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self.ssl_context: Any = None                     # set by the server: the context new connections are served with

    @property
    def enabled(self) -> bool:
        s = self.engine.settings
        return bool(s.tls_cert and s.tls_key and not s.dev_plaintext)

    @property
    def current(self) -> tuple[Path, Path]:
        s = self.engine.settings
        assert s.tls_cert and s.tls_key
        return s.tls_cert, s.tls_key

    @property
    def next_dir(self) -> Path:
        return self.current[0].parent / "next"

    def next_pem(self) -> bytes | None:
        p = self.next_dir / "engine.crt"
        return p.read_bytes() if p.exists() else None

    def status(self) -> dict[str, Any]:
        cur = describe(self.current[0].read_bytes())
        nxt = self.next_pem()
        out: dict[str, Any] = {"current": {**cur, "not_after": cur["not_after"].isoformat()}, "next": None}
        if nxt:
            n = describe(nxt)
            out["next"] = {**n, "not_after": n["not_after"].isoformat()}
        return out

    async def renew(self, names: list[str] | None = None, *, by: Context | None = None) -> dict[str, Any]:
        """Make the next certificate (the current names unless others are given), tell the store, give it to every connected machine."""
        from engine.tls import generate_self_signed

        names = names or describe(self.current[0].read_bytes())["names"]
        if not names:
            raise ProtocolError(ErrorCode.INVALID, "the certificate needs at least one name")
        await asyncio.to_thread(generate_self_signed, ",".join(names), self.next_dir)
        pem = self.next_dir.joinpath("engine.crt").read_bytes()
        await self._tell_store()
        await self.engine.audit.record(by, "cert.next_made", target_type="certificates", target_id=describe(pem)["sha256"], detail={"names": names})
        await self.engine.broadcast("engine.next_certificate", {"pem": pem.decode("ascii")})
        log.info("the next certificate is made (%s) and given to the connected machines", ", ".join(names))
        return self.status()

    async def switch(self, *, by: Context | None = None) -> dict[str, Any]:
        """Serve the next certificate from now on; the old pair is kept beside it (engine-old.*)."""
        nxt = self.next_dir / "engine.crt"
        if not nxt.exists():
            raise ProtocolError(ErrorCode.CONFLICT, "there is no next certificate to switch to: make it first (cert renew)")
        cert, key = self.current
        for src, dst in ((cert, cert.with_name("engine-old.crt")), (key, key.with_name("engine-old.key"))):
            shutil.copy2(src, dst)
        shutil.copy2(nxt, cert)
        shutil.copy2(self.next_dir / "engine.key", key)
        shutil.rmtree(self.next_dir)
        if self.ssl_context is not None:
            self.ssl_context.load_cert_chain(certfile=str(cert), keyfile=str(key))      # new connections from now on
        await self.engine.audit.record(by, "cert.switched", target_type="certificates", target_id=describe(cert.read_bytes())["sha256"])
        log.info("switched to the next certificate")
        return self.status()

    async def _tell_store(self) -> None:
        """The store issues a company file with both certificates: Worker setups made from now on trust both."""
        store = self.engine.store
        if not store.registered:
            return
        both = [self.current[0].read_text(encoding="ascii").strip()]
        if (nxt := self.next_pem()):
            both.append(nxt.decode("ascii").strip())
        try:
            got = await asyncio.to_thread(store._call, "PUT", f"/api/engines/{store.identity['engine_id']}/certificates", {"certificates": both})  # type: ignore[index]
        except Exception as exc:                                                    # noqa: BLE001 -- the store may be away: tried again daily
            log.warning("the store could not be told the certificates (%s): asked again tomorrow", exc)
            return
        from common import signed

        try:
            signed.check(got.get("company"), "company")
        except signed.SignatureError as exc:
            log.warning("the store's company file cannot be trusted (%s): not kept", exc)
            return
        (store.path.parent / "company.falcon").write_text(json.dumps(got["company"]), encoding="utf-8")

    async def daily(self) -> None:
        if not self.enabled:
            return
        left = describe(self.current[0].read_bytes())["not_after"] - datetime.now(timezone.utc)
        if self.next_pem() is None and left <= RENEW_BEFORE:
            await self.renew()
        elif self.next_pem() is not None and left <= SWITCH_BEFORE:
            await self.switch()
        elif self.next_pem() is not None:
            await self._tell_store()                                                # healed if the store was away the day it was made

    async def on_connected(self, conn: Any) -> None:
        """A machine that was away when the next certificate was given out is given it as it signs in."""
        if self.enabled and (nxt := self.next_pem()):
            await conn.push("engine.next_certificate", {"pem": nxt.decode("ascii")})


@handler("cert.status")
async def cert_status(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    require_role(ctx, "super_user", "admin")
    if not ctx.engine.certs.enabled:
        raise ProtocolError(ErrorCode.CONFLICT, "this Engine runs without TLS (development)")
    return ctx.engine.certs.status()


@handler("cert.renew")
async def cert_renew(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    require_role(ctx, "super_user", "admin")
    if not ctx.engine.certs.enabled:
        raise ProtocolError(ErrorCode.CONFLICT, "this Engine runs without TLS (development)")
    names = payload.get("names")
    if names is not None and (not isinstance(names, list) or not all(isinstance(n, str) and n.strip() for n in names)):
        raise ProtocolError(ErrorCode.INVALID, "names is a list of host names or addresses")
    return await ctx.engine.certs.renew([n.strip() for n in names] if names else None, by=ctx)


@handler("cert.switch")
async def cert_switch(ctx: Context, payload: dict[str, Any]) -> dict[str, Any]:
    require_role(ctx, "super_user", "admin")
    if not ctx.engine.certs.enabled:
        raise ProtocolError(ErrorCode.CONFLICT, "this Engine runs without TLS (development)")
    return await ctx.engine.certs.switch(by=ctx)
