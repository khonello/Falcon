"""The store's public keys Falcon trusts, by key id (`kid`): docs/STORE-CONTRACT.md section 2.

Every signed document the store issues names the key that signed it. A machine checks it against these keys, with no internet, so a document
that was changed, or signed by anyone else, is refused. Several keys may be trusted at once, so the store can move to a new key without
breaking machines already installed: the new key is added here first (in a release), and the store starts using it after.

The store's real key does not exist yet: the store session makes it (on its server, never in this repository) and its PUBLIC half is added to
`STORE_KEYS` below. Until then only the test key is known, and it is trusted only when `FALCON_STORE_TEST_KEY=1` (the test suite, the drills,
`scripts/store_stub.py`). Its private half is derived in the stub from a phrase anyone can read, so it must never be trusted otherwise.
"""

from __future__ import annotations

import os

# kid -> Ed25519 public key (32 bytes). The store's own keys are added here as the store session makes them.
STORE_KEYS: dict[str, bytes] = {}

TEST_KID = "test-1"
TEST_KEY = bytes.fromhex("3579e520aa01beb1f2b79030d8964da773e00977e8cb49a4be5ab659562490d3")


def trusted() -> dict[str, bytes]:
    """The keys trusted now: the store's, and the test key only when the environment asks for it."""
    keys = dict(STORE_KEYS)
    if os.environ.get("FALCON_STORE_TEST_KEY") == "1":
        keys[TEST_KID] = TEST_KEY
    return keys
