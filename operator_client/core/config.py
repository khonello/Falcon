"""Local config (spec 4.3): last-connected Engine address, this client's id, window/UI
preferences, and a cache of lists for faster reopening. A JSON file, no database.

Location: %APPDATA%/Falcon/operator.json on Windows, ~/.config/falcon/operator.json elsewhere.
The derived auth key (Phase 5) is NOT stored here -- it belongs under an ACL-restricted path.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


def default_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        return base / "Falcon" / "operator.json"
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "falcon" / "operator.json"


@dataclass
class LocalConfig:
    engine_host: str = "127.0.0.1"
    engine_port: int = 7400
    client_id: str = ""
    tls: bool = True
    ca_cert: str | None = None
    prefs: dict[str, Any] = field(default_factory=dict)      # UI preferences
    cache: dict[str, Any] = field(default_factory=dict)      # cached lists (departments, ...)
    path: Path = field(default_factory=default_path, repr=False, compare=False)

    @classmethod
    def load(cls, path: Path | None = None) -> LocalConfig:
        p = path or default_path()
        cfg = cls(path=p)
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cfg
        for key in ("engine_host", "engine_port", "client_id", "tls", "ca_cert", "prefs", "cache"):
            if key in data:
                setattr(cfg, key, data[key])
        return cfg

    def save(self) -> None:
        data = asdict(self)
        data.pop("path", None)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @property
    def engine_address(self) -> str:
        return f"{self.engine_host}:{self.engine_port}"
