"""The Engine's link to the store (docs/STORE-CONTRACT.md): who it is there, and the seat grants the store has signed for it.

    StoreLink(engine).identity      {store_url, engine_id, engine_token} from store.json beside the master secret, or None (not registered)
    await link.fetch_grants()       ask the store for its grants and keep the new ones (never re-checks one it has)
    await link.report_usage()       tell the store how many seats are in use (counts only)
    await add_grants(engine, envs)  keep the grants in `envs` that are good: signed by the store, for this Engine; returns how many were new

`store.json` is written when the Engine registers with the store (its setup, docs/SEATS-AND-SETUP.md section 4). An Engine that is not
registered (a development checkout, the test suite) has no seat limit: nothing is ever taken back for want of a grant.
"""

from __future__ import annotations

import asyncio
import json
import logging
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

from common import signed

if TYPE_CHECKING:
    from engine.server import Engine

log = logging.getLogger(__name__)

TIMEOUT = 20.0
ROLES = ("admin", "worker")


def parse_time(text: str) -> datetime:
    return datetime.fromisoformat(str(text).replace("Z", "+00:00"))


class StoreLink:
    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        self._identity: dict[str, Any] | None = None
        self._loaded = False

    @property
    def path(self) -> Path:
        return Path(self.engine.settings.secret_path).parent / "store.json"

    @property
    def identity(self) -> dict[str, Any] | None:
        if not self._loaded:
            self._loaded = True
            try:
                got = json.loads(self.path.read_text(encoding="utf-8"))
                if all(got.get(k) for k in ("store_url", "engine_id", "engine_token")):
                    self._identity = got
            except (OSError, ValueError):
                self._identity = None
        return self._identity

    @identity.setter
    def identity(self, value: dict[str, Any] | None) -> None:
        self._identity, self._loaded = value, True

    @property
    def registered(self) -> bool:
        return self.identity is not None

    def _call(self, method: str, path: str, body: dict[str, Any] | None = None) -> dict[str, Any]:
        ident = self.identity
        assert ident is not None
        req = urllib.request.Request(ident["store_url"].rstrip("/") + path, method=method,
                                     data=None if body is None else json.dumps(body).encode("utf-8"),
                                     headers={"Authorization": f"Bearer {ident['engine_token']}", "Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=TIMEOUT) as r:          # (the store's own address, from store.json)
            raw = r.read()
        return json.loads(raw) if raw else {}

    async def fetch_grants(self) -> int:
        """New grants from the store, kept; how many. Not registered, or the store not reachable: 0 (and it is asked again tomorrow)."""
        if not self.registered:
            return 0
        try:
            got = await asyncio.to_thread(self._call, "GET", f"/api/engines/{self.identity['engine_id']}/grants")   # type: ignore[index]
        except (OSError, urllib.error.URLError, ValueError) as exc:
            log.warning("the store could not be asked for seat grants: %s", exc)
            return 0
        return await add_grants(self.engine, got.get("grants") or [])

    async def report_usage(self) -> None:
        if not self.registered:
            return
        db = self.engine.db
        body = {"admin_in_use": await db.seats.in_use("admin"), "worker_in_use": await db.seats.in_use("worker")}
        try:
            await asyncio.to_thread(self._call, "POST", f"/api/engines/{self.identity['engine_id']}/usage", body)   # type: ignore[index]
        except (OSError, urllib.error.URLError, ValueError) as exc:
            log.info("the store could not be told the seats in use: %s", exc)


def good_grant(engine: Engine, envelope: Any) -> dict[str, Any] | None:
    """The grant inside `envelope` when it is signed by the store, for this Engine, and well formed; None (and a line in the log) otherwise."""
    try:
        doc = signed.check(envelope, "grant")
    except signed.SignatureError as exc:
        log.warning("a seat grant was refused: %s", exc)
        return None
    ident = engine.store.identity
    if ident is None or doc.get("engine_id") != ident.get("engine_id"):
        log.warning("a seat grant for another Engine (%s) was refused", doc.get("engine_id"))
        return None
    if doc.get("role") not in ROLES or not isinstance(doc.get("seats"), int) or doc["seats"] <= 0:
        log.warning("a seat grant that is not well formed was refused: %s", doc.get("grant_id"))
        return None
    try:
        parse_time(doc["valid_from"]), parse_time(doc["valid_until"])
    except (KeyError, ValueError):
        log.warning("a seat grant with unreadable dates was refused: %s", doc.get("grant_id"))
        return None
    return doc


async def add_grants(engine: Engine, envelopes: list[Any]) -> int:
    added = 0
    for env in envelopes:
        doc = good_grant(engine, env)
        if doc is None:
            continue
        if await engine.db.seats.add_grant(str(doc["grant_id"]), doc["role"], doc["seats"], parse_time(doc["valid_from"]),
                                           parse_time(doc["valid_until"]), env):
            added += 1
            await engine.audit.record(None, "seats.granted", target_type="seat_grants", target_id=str(doc["grant_id"]),
                                      detail={"role": doc["role"], "seats": doc["seats"], "valid_until": doc["valid_until"]})
    return added
