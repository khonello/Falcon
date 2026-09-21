"""Worker local state (spec 5.3): config only, no database.

    engine address, client id, TLS settings          -- provisioning
    watched roots                                     -- what the file watcher covers
    cached deadlines / session state                  -- offline resilience (spec 5.3)

Location: %ProgramData%/Falcon/worker.json on Windows (ACL-restricted in deployment; the
derived auth key of Phase 5 lives beside it), /etc/falcon/worker.json elsewhere -- overridable
with FALCON_WORKER_CONFIG for development.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


def default_path() -> Path:
    env = os.environ.get("FALCON_WORKER_CONFIG")
    if env:
        return Path(env)
    if os.name == "nt":
        return Path(os.environ.get("PROGRAMDATA", r"C:\ProgramData")) / "Falcon" / "worker.json"
    return Path("/etc/falcon/worker.json")


def default_roots() -> list[str]:
    home = Path.home()
    roots = [home / "Documents", home / "Desktop", home / "Downloads", home / "resources"]
    return [str(r) for r in roots if r.exists()]


@dataclass
class WorkerConfig:
    engine_host: str = "127.0.0.1"
    engine_port: int = 7400
    client_id: str = ""
    client_key: str = ""          # hex, issued once at provisioning with the client_id
    tls: bool = True
    ca_cert: str | None = None    # the Engine's pinned certificate (from the install package)
    watch_roots: list[str] = field(default_factory=default_roots)
    poll_seconds: float = 5.0            # polling fallback interval for file changes
    metrics_seconds: float = 15.0        # control.metrics cadence
    idle_sweep_after_seconds: float = 300.0   # start the full sweep after this much idle
    hash_limit_bytes: int = 64 * 1024 * 1024   # bigger files are indexed without a hash
    lock_workstation_on_block: bool = False    # Windows: LockWorkStation() when a superior enters
    update_command: str | None = None          # how to apply an update (deferred CI/CD: none yet)
    cache: dict[str, Any] = field(default_factory=dict)   # deadlines, last session state
    path: Path = field(default_factory=default_path, repr=False, compare=False)

    @classmethod
    def load(cls, path: Path | None = None) -> WorkerConfig:
        p = path or default_path()
        cfg = cls(path=p)
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            return cfg
        for key in ("engine_host", "engine_port", "client_id", "client_key", "tls", "ca_cert", "watch_roots", "poll_seconds",
                    "metrics_seconds", "idle_sweep_after_seconds", "hash_limit_bytes", "lock_workstation_on_block",
                    "update_command", "cache"):
            if key in data:
                setattr(cfg, key, data[key])
        return cfg

    def save(self) -> None:
        data = asdict(self)
        data.pop("path", None)
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(data, indent=2), encoding="utf-8")
        except OSError:
            pass  # a read-only location must never stop the service

    @property
    def engine_address(self) -> str:
        return f"{self.engine_host}:{self.engine_port}"
