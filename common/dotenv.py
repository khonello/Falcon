"""`.env` loading, stdlib only: one file of FALCON_* settings instead of shell variables.

The Engine, the test suite and the scripts call `load()` at start. It finds `.env` -- next to the current directory
or any parent, else at the repository root -- and sets each KEY=VALUE it holds, **without overriding** a variable
that is already set, so the real environment (a service manager, a CI job, a one-off shell) still wins.

Format: `KEY=VALUE` per line; blank lines and `#` comments ignored; `export KEY=...` accepted; values may be quoted
('...' or "..."); a trailing ` # comment` after an unquoted value is dropped. No interpolation.
"""

from __future__ import annotations

import os
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]


def find(start: Path | None = None) -> Path | None:
    """The `.env` that applies: the nearest one at or above `start` (default: the cwd), else the repository's."""
    here = (start or Path.cwd()).resolve()
    for d in (here, *here.parents):
        candidate = d / ".env"
        if candidate.is_file():
            return candidate
    candidate = REPO_ROOT / ".env"
    return candidate if candidate.is_file() else None


def parse(text: str) -> dict[str, str]:
    out: dict[str, str] = {}
    for raw in text.splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):].lstrip()
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip()
        if not key.replace("_", "").isalnum():
            continue
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "'\"":
            value = value[1:-1]
        elif " #" in value:
            value = value.split(" #", 1)[0].rstrip()
        out[key] = value
    return out


def load(path: Path | None = None, *, override: bool = False) -> Path | None:
    """Load `.env` into os.environ; returns the file used, or None when there is none (not an error)."""
    p = path or find()
    if p is None or not p.is_file():
        return None
    for key, value in parse(p.read_text(encoding="utf-8")).items():
        if override or key not in os.environ:
            os.environ[key] = value
    return p
