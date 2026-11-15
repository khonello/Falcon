"""The console's first run, when it is not set up.

Since 15 Nov 2026 (docs/SEATS-AND-SETUP.md) a console is set up only by the Admin setup, which signs in to the company's account in the
store and takes a free Admin seat; its Worker service then signs for it (`signer: pipe`). No licence code exists any more, and an address
and certificate typed here would be a way in nothing checks: `set_up` answers with what to do instead.
"""

from __future__ import annotations

from common.firstrun import UNKNOWN_HOST
from operator_client.core.config import LocalConfig

SET_UP_BY_THE_SETUP = "This console is set up by the Admin setup (falcon-admin-setup.exe): it signs in to your company's Falcon account and takes a free Admin seat. Run it on this PC."


def needs_setup(cfg: LocalConfig) -> bool:
    return not cfg.client_id and cfg.signer != "pipe"


def needs_certificate(cfg: LocalConfig) -> bool:
    return cfg.tls and not cfg.ca_cert


def known_address(cfg: LocalConfig) -> str:
    return "" if cfg.engine_host in UNKNOWN_HOST else cfg.engine_address


async def set_up(cfg: LocalConfig, address: str, code: str, cert: str = "") -> str:
    """What the setup modal is told: nothing joins from here (see the module's text)."""
    return SET_UP_BY_THE_SETUP
