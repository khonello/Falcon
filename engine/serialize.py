"""Turn repo rows into JSON-safe dicts for responses/pushes (datetimes -> ISO 8601)."""

from __future__ import annotations

from typing import Any


def row(r: dict[str, Any] | None) -> dict[str, Any] | None:
    if r is None:
        return None
    out: dict[str, Any] = {}
    for k, v in r.items():
        if hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        elif isinstance(v, dict):
            out[k] = row(v)
        elif isinstance(v, list):
            out[k] = [row(x) if isinstance(x, dict) else x for x in v]
        else:
            out[k] = v
    return out


def rows(rs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [row(r) for r in rs]  # type: ignore[misc]
