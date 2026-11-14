"""Ed25519 signature verification, in the standard library only (`common/` must stay stdlib: docs/SEATS-AND-SETUP.md step 1).

    verify(public_key: bytes, message: bytes, signature: bytes) -> bool

The arithmetic of RFC 8032, section 5.1 (twisted Edwards curve edwards25519, extended coordinates), checked against the RFC's own test vectors
(tests/test_signed_docs.py). Falcon only ever VERIFIES here: what the store signs is signed on the store's server, with its private key, and
never on a Falcon machine. It is slow by the standards of a C library (a few milliseconds a signature), which is nothing for the few documents
a machine checks: the company file at setup, the seat grants, an Admin claim.
"""

from __future__ import annotations

import hashlib

P = 2**255 - 19                                               # the field
L = 2**252 + 27742317777372353535851937790883648493          # the order of the base point
D = -121665 * pow(121666, P - 2, P) % P
SQRT_M1 = pow(2, (P - 1) // 4, P)

Point = tuple[int, int, int, int]                              # extended coordinates (X, Y, Z, T), x = X/Z, y = Y/Z, x*y = T/Z


def _add(a: Point, b: Point) -> Point:
    x1, y1, z1, t1 = a
    x2, y2, z2, t2 = b
    aa = (y1 - x1) * (y2 - x2) % P
    bb = (y1 + x1) * (y2 + x2) % P
    cc = 2 * t1 * t2 * D % P
    dd = 2 * z1 * z2 % P
    e, f, g, h = bb - aa, dd - cc, dd + cc, bb + aa
    return (e * f % P, g * h % P, f * g % P, e * h % P)


def _mul(s: int, a: Point) -> Point:
    q: Point = (0, 1, 1, 0)                                    # the neutral element
    while s > 0:
        if s & 1:
            q = _add(q, a)
        a = _add(a, a)
        s >>= 1
    return q


def _equal(a: Point, b: Point) -> bool:
    return (a[0] * b[2] - b[0] * a[2]) % P == 0 and (a[1] * b[2] - b[1] * a[2]) % P == 0


def _recover_x(y: int, sign: int) -> int | None:
    if y >= P:
        return None
    x2 = (y * y - 1) * pow(D * y * y + 1, P - 2, P) % P
    if x2 == 0:
        return None if sign else 0
    x = pow(x2, (P + 3) // 8, P)
    if (x * x - x2) % P != 0:
        x = x * SQRT_M1 % P
    if (x * x - x2) % P != 0:
        return None
    if (x & 1) != sign:
        x = P - x
    return x


def _decompress(b: bytes) -> Point | None:
    if len(b) != 32:
        return None
    y = int.from_bytes(b, "little")
    sign = y >> 255
    y &= (1 << 255) - 1
    x = _recover_x(y, sign)
    if x is None:
        return None
    return (x, y, 1, x * y % P)


_GY = 4 * pow(5, P - 2, P) % P
_GX = _recover_x(_GY, 0)
assert _GX is not None
G: Point = (_GX, _GY, 1, _GX * _GY % P)


def verify(public_key: bytes, message: bytes, signature: bytes) -> bool:
    """Is `signature` the Ed25519 signature of `message` by the holder of `public_key`? Never raises for bad input: it is just not valid."""
    if len(public_key) != 32 or len(signature) != 64:
        return False
    a = _decompress(public_key)
    if a is None:
        return False
    r_bytes = signature[:32]
    r = _decompress(r_bytes)
    if r is None:
        return False
    s = int.from_bytes(signature[32:], "little")
    if s >= L:
        return False                                           # (a signature must not be malleable: RFC 8032 5.1.7)
    h = int.from_bytes(hashlib.sha512(r_bytes + public_key + message).digest(), "little") % L
    return _equal(_mul(s, G), _add(r, _mul(h, a)))
