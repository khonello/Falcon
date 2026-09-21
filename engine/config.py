"""Engine settings, read from FALCON_* environment variables (see .env.example)."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

_TRUTHY = {"1", "true", "yes", "on"}


def _flag(name: str) -> bool:
    return os.environ.get(name, "").strip().lower() in _TRUTHY


@dataclass(frozen=True)
class Settings:
    host: str = "0.0.0.0"
    port: int = 7400
    database_url: str | None = None
    tls_cert: Path | None = None
    tls_key: Path | None = None
    # Retention is flat 90 days system-wide for v1 (hierarchy-system-design.md → Audit & Logging).
    audit_retention_days: int = 90
    # Traversal Time Limit (Hierarchy -> Session Blocking): fixed, extendable on request.
    traversal_limit_minutes: int = 30
    traversal_extension_minutes: int = 15
    # Update escalation threshold (open item 10.4): count-based, tunable.
    update_escalation_failures: int = 3
    # Polled/evaluated Events (thresholds, idle, time) are checked on this interval.
    control_poll_seconds: int = 15
    # Local LLM sidecar (spec 7.2.1). Never an external API.
    llm_endpoint: str = "http://127.0.0.1:11434"
    llm_model: str = "qwen3:0.6b"
    debug: bool = False

    # Development-only. Both are hard, visible skips — never a quietly-always-true check (spec §8.1).
    dev_bypass_auth: bool = False
    dev_plaintext: bool = False

    @classmethod
    def from_env(cls) -> Settings:
        cert = os.environ.get("FALCON_TLS_CERT")
        key = os.environ.get("FALCON_TLS_KEY")
        return cls(
            host=os.environ.get("FALCON_ENGINE_HOST", cls.host),
            port=int(os.environ.get("FALCON_ENGINE_PORT", cls.port)),
            database_url=os.environ.get("FALCON_DATABASE_URL") or None,
            tls_cert=Path(cert) if cert else None,
            tls_key=Path(key) if key else None,
            audit_retention_days=int(
                os.environ.get("FALCON_AUDIT_RETENTION_DAYS", cls.audit_retention_days)
            ),
            traversal_limit_minutes=int(os.environ.get("FALCON_TRAVERSAL_LIMIT_MINUTES", cls.traversal_limit_minutes)),
            traversal_extension_minutes=int(
                os.environ.get("FALCON_TRAVERSAL_EXTENSION_MINUTES", cls.traversal_extension_minutes)
            ),
            update_escalation_failures=int(
                os.environ.get("FALCON_UPDATE_ESCALATION_FAILURES", cls.update_escalation_failures)
            ),
            control_poll_seconds=int(os.environ.get("FALCON_CONTROL_POLL_SECONDS", cls.control_poll_seconds)),
            llm_endpoint=os.environ.get("FALCON_LLM_ENDPOINT", cls.llm_endpoint),
            llm_model=os.environ.get("FALCON_LLM_MODEL", cls.llm_model),
            debug=_flag("FALCON_DEBUG"),
            dev_bypass_auth=_flag("FALCON_DEV_BYPASS_AUTH"),
            dev_plaintext=_flag("FALCON_DEV_PLAINTEXT"),
        )
