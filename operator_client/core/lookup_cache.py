"""A small local memory of what the console looks things up in (people, machines, recent files), so pickers are instant and still say something when
the Engine cannot be reached.

The Engine stays the only source of truth: this is read-only convenience, never an authority.
  * it is kept per signed-in account (what a console shows depends on the role); a different account, or a different Engine, starts from nothing
  * every section says when it was fetched, so the screen can say "as of ..." and never pass old data off as live
  * one JSON file next to the settings, written atomically; a missing, unreadable or damaged file is an empty cache, never an error
  * bounded: a section keeps at most MAX_ITEMS items, and a stale section is dropped after MAX_AGE_DAYS
No UI dependencies.
"""

from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any

MAX_ITEMS = 2000
MAX_AGE_DAYS = 30


class LookupCache:
    def __init__(self, path: Path, now=time.time) -> None:
        self.path = path
        self._now = now
        self.owner = ""
        self._sections: dict[str, dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
            if isinstance(data, dict) and isinstance(data.get("sections"), dict):
                self.owner = str(data.get("owner") or "")
                self._sections = {k: v for k, v in data["sections"].items() if isinstance(v, dict) and isinstance(v.get("items"), list)}
        except (OSError, ValueError):
            self.owner, self._sections = "", {}

    def adopt(self, owner: str) -> None:
        """This is who the console is signed in as: what was kept for anyone else is forgotten."""
        if owner != self.owner:
            self.owner, self._sections = owner, {}
            self._save()

    def get(self, name: str) -> dict[str, Any]:
        """{"at": seconds, "items": [...]}; empty when there is nothing, it is too old, or it belongs to someone else."""
        section = self._sections.get(name)
        if not section or not self.owner:
            return {"at": 0, "items": []}
        at = float(section.get("at") or 0)
        if self._now() - at > MAX_AGE_DAYS * 86400:
            return {"at": 0, "items": []}
        return {"at": at, "items": section["items"]}

    def put(self, name: str, items: list[Any]) -> None:
        if not self.owner or not isinstance(items, list):
            return
        self._sections[name] = {"at": self._now(), "items": items[:MAX_ITEMS]}
        self._save()

    def remember(self, name: str, item: dict[str, Any], key: str, limit: int = 50) -> None:
        """Add one item to the front of a short list of recent things (the same `key` is moved up, not repeated)."""
        have = [i for i in self.get(name)["items"] if isinstance(i, dict) and i.get(key) != item.get(key)]
        self.put(name, ([item] + have)[:limit])

    def clear(self) -> None:
        self._sections = {}
        self._save()

    def _save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            tmp = self.path.with_suffix(self.path.suffix + ".tmp")
            tmp.write_text(json.dumps({"owner": self.owner, "sections": self._sections}), encoding="utf-8")
            os.replace(tmp, self.path)
        except OSError:
            pass                                   # a cache that cannot be written is just a cache that is empty next time
