"""Signed documents from the store (docs/STORE-CONTRACT.md section 2): reading one, and refusing anything that is not exactly what was signed.

    canonical(doc) -> bytes                       what is signed: UTF-8 JSON, keys sorted, no spaces, integers and strings only
    check(envelope, kind, keys=None) -> doc       the document, if `envelope` = {"doc", "kid", "sig"} is a good signature of the right kind
    SignatureError                                why one was refused, in words

Stdlib only (`common/`): the signature itself is checked by `common.ed25519`.
"""

from __future__ import annotations

import base64
import binascii
import json
from typing import Any

from common import ed25519, store_keys

KINDS = ("company", "grant", "admin_claim")


class SignatureError(ValueError):
    """A signed document that cannot be trusted."""


def _no_floats(value: Any, where: str = "doc") -> None:
    if isinstance(value, float):
        raise SignatureError(f"{where} holds a number with a fraction: a signed document holds integers and strings only")
    if isinstance(value, dict):
        for k, v in value.items():
            if not isinstance(k, str):
                raise SignatureError(f"{where} has a key that is not a string")
            _no_floats(v, f"{where}.{k}")
    elif isinstance(value, list):
        for i, v in enumerate(value):
            _no_floats(v, f"{where}[{i}]")


def canonical(doc: dict[str, Any]) -> bytes:
    """The exact bytes the store signs and Falcon checks."""
    _no_floats(doc)
    return json.dumps(doc, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def check(envelope: Any, kind: str, keys: dict[str, bytes] | None = None) -> dict[str, Any]:
    """The document inside `envelope`, if it is of `kind` and carries a good signature by a key Falcon trusts. Raises SignatureError otherwise."""
    if kind not in KINDS:
        raise SignatureError(f"no such kind of document: {kind!r}")
    if not isinstance(envelope, dict) or not isinstance(envelope.get("doc"), dict):
        raise SignatureError("not a signed document")
    doc, kid, sig = envelope["doc"], envelope.get("kid"), envelope.get("sig")
    if doc.get("kind") != kind:
        raise SignatureError(f"this is a {doc.get('kind')!r} document, not a {kind!r} one")
    trusted = store_keys.trusted() if keys is None else keys
    if not isinstance(kid, str) or kid not in trusted:
        raise SignatureError(f"signed by a key Falcon does not know ({kid!r})")
    try:
        raw = base64.b64decode(str(sig), validate=True)
    except (binascii.Error, ValueError) as exc:
        raise SignatureError("the signature is not readable") from exc
    if not ed25519.verify(trusted[kid], canonical(doc), raw):
        raise SignatureError("the signature does not match: the document was changed, or not signed by the store")
    return doc


def load(path: Any, kind: str) -> dict[str, Any]:
    """A signed document from a file (a company file, `<company>.falcon`)."""
    from pathlib import Path

    try:
        envelope = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise SignatureError(f"{path} could not be read as a signed document ({exc})") from exc
    return check(envelope, kind)
