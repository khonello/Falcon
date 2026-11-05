"""The console's first run: not set up yet, so it asks for the Engine's address and an admin licence code, and joins.

A console on an Admin's workstation signs through the Worker service there (`signer: pipe`): that service is what joins, and asks
in the Falcon program, so this console has nothing to ask.
"""

from __future__ import annotations

from common.firstrun import (
    UNKNOWN_HOST,
    join_with_licence,
    keep_certificate,
    parse_address,
    plain_reason,
)
from operator_client.core.config import LocalConfig


def needs_setup(cfg: LocalConfig) -> bool:
    return not cfg.client_id and cfg.signer != "pipe"


def needs_certificate(cfg: LocalConfig) -> bool:
    return cfg.tls and not cfg.ca_cert


def known_address(cfg: LocalConfig) -> str:
    return "" if cfg.engine_host in UNKNOWN_HOST else cfg.engine_address


async def set_up(cfg: LocalConfig, address: str, code: str, cert: str = "") -> str:
    """Join and remember it. Answers what went wrong, or "" when this console is set up."""
    try:
        host, port = parse_address(address)
        if not code.strip():
            raise ValueError("Type the licence code.")
        if cert.strip():
            cfg.ca_cert = keep_certificate(cert, cfg.path.parent)
        if needs_certificate(cfg):
            raise ValueError("Choose the Engine's certificate.")
        got = await join_with_licence(host, port, tls=cfg.tls, ca_cert=cfg.ca_cert, code=code.strip(), level="admin")
    except Exception as exc:  # noqa: BLE001 -- everything here ends as words on the modal
        return plain_reason(exc, address.strip())
    cfg.engine_host, cfg.engine_port = host, port
    cfg.client_id, cfg.client_key = got["client_id"], got["client_key"]
    cfg.save()
    return ""
