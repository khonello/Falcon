"""Local config (spec 4.3): last-connected Engine address, this client's id, window/UI
preferences, and a cache of lists for faster reopening. A JSON file, no database.

Location: %APPDATA%/Falcon/operator.json on Windows, ~/.config/falcon/operator.json elsewhere.
The derived auth key (Phase 5) is NOT stored here -- it belongs under an ACL-restricted path.
"""

from __future__ import annotations

import json
import os
from collections.abc import Callable
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


def default_path() -> Path:
    if os.name == "nt":
        base = Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming")
        return base / "Falcon" / "operator.json"
    return Path(os.environ.get("XDG_CONFIG_HOME") or Path.home() / ".config") / "falcon" / "operator.json"


def machine_defaults() -> dict[str, Any]:
    """`%PROGRAMDATA%/Falcon/console.json`: written by the installer for every person on this machine (the Engine's address and
    certificate, who signs). Nothing secret is in it."""
    if os.name != "nt":
        return {}
    path = Path(os.environ.get("PROGRAMDATA") or r"C:\ProgramData") / "Falcon" / "console.json"
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return {k: v for k, v in data.items() if k in ("engine_host", "engine_port", "client_id", "tls", "ca_cert", "signer")}


@dataclass
class LocalConfig:
    engine_host: str = "127.0.0.1"
    engine_port: int = 7400
    client_id: str = ""
    client_key: str = ""          # hex, issued once at provisioning with the client_id
    tls: bool = True
    ca_cert: str | None = None    # the Engine's pinned certificate (from the install package)
    signer: str = ""              # "pipe": no key here -- the Worker service on this machine answers the challenge (common.signpipe)
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
            data = {}
        for key, value in machine_defaults().items():          # what the installer put for everyone on this machine; the person's own file wins
            data.setdefault(key, value)
        for key in ("engine_host", "engine_port", "client_id", "client_key", "tls", "ca_cert", "signer", "prefs", "cache"):
            if key in data:
                setattr(cfg, key, data[key])
        if cfg.signer == "pipe" and not cfg.client_id:
            try:
                from common.signpipe import whoami

                cfg.client_id = whoami()
            except OSError:
                pass                                           # no service answering: the console says it is not connected
        return cfg

    def signer_fn(self) -> Callable[[str], str] | None:
        """How to answer the Engine's challenge when this machine's key is not ours to hold."""
        if self.signer != "pipe" or self.client_key:
            return None
        from common.signpipe import sign

        return sign

    def save(self) -> None:
        data = asdict(self)
        data.pop("path", None)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    @property
    def engine_address(self) -> str:
        return f"{self.engine_host}:{self.engine_port}"
