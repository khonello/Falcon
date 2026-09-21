"""The master secret: one random value on the Engine host, never transmitted (spec 8.2).

Every client's key is derived from it (`auth.derive_client_key`), so the Engine stores no per-client
keys -- provisioning hands the derived key to the install package once, and the Engine re-derives
it at every handshake. Losing this file invalidates every client key; back it up like a CA key.

Created on first start at `Settings.secret_path` (FALCON_SECRET_PATH, default `data/master.secret`)
with owner-only permissions. Tests pass the secret in memory instead (`Settings.master_secret`).
"""

from __future__ import annotations

import logging
import os
import secrets
from pathlib import Path

log = logging.getLogger(__name__)

SECRET_BYTES = 32


def load_or_create(path: Path) -> bytes:
    if path.exists():
        data = bytes.fromhex(path.read_text(encoding="ascii").strip())
        if len(data) < SECRET_BYTES:
            raise SystemExit(f"master secret at {path} is too short -- refusing to start")
        return data
    path.parent.mkdir(parents=True, exist_ok=True)
    secret = secrets.token_bytes(SECRET_BYTES)
    fd = os.open(str(path), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="ascii") as fh:
        fh.write(secret.hex() + "\n")
    try:
        os.chmod(path, 0o600)   # no-op on Windows ACLs; owner-only on Linux where the Engine deploys
    except OSError:
        pass
    log.warning("generated a new master secret at %s -- back it up; every client key derives from it", path)
    return secret
