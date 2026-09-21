"""Plain-text rendering helpers (no UI library): tables, key/value blocks, status lines."""

from __future__ import annotations

import json
from collections.abc import Iterable
from datetime import datetime
from typing import Any


def short(value: Any, width: int = 40) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (dict, list)):
        value = json.dumps(value, separators=(",", ":"))
    s = str(value)
    if len(s) > 10 and s[4:5] == "-" and "T" in s:  # ISO timestamp -> local, short
        try:
            dt = datetime.fromisoformat(s)
            s = dt.astimezone().strftime("%Y-%m-%d %H:%M")
        except ValueError:
            pass
    return s if len(s) <= width else s[: width - 1] + "…"


def table(rows: Iterable[dict[str, Any]], columns: list[str] | None = None, *,
          width: int = 40, empty: str = "(none)") -> str:
    rows = list(rows)
    if not rows:
        return empty
    cols = columns or list(rows[0].keys())
    cells = [[short(r.get(c), width) for c in cols] for r in rows]
    widths = [max(len(c), *(len(row[i]) for row in cells)) for i, c in enumerate(cols)]
    line = "  ".join(c.ljust(widths[i]) for i, c in enumerate(cols))
    sep = "  ".join("-" * w for w in widths)
    body = "\n".join("  ".join(row[i].ljust(widths[i]) for i in range(len(cols))) for row in cells)
    return f"{line}\n{sep}\n{body}"


def kv(data: dict[str, Any], *, skip: Iterable[str] = (), width: int = 100) -> str:
    skip = set(skip)
    keys = [k for k in data if k not in skip]
    if not keys:
        return "(empty)"
    w = max(len(k) for k in keys)
    return "\n".join(f"{k.ljust(w)}  {short(data[k], width)}" for k in keys)


def pretty(data: Any) -> str:
    return json.dumps(data, indent=2, default=str)


def bullet(lines: Iterable[str]) -> str:
    return "\n".join(f"  • {ln}" for ln in lines) or "(none)"
