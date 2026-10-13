"""The text files the Engine's installer writes, kept apart from the steps so they can be read and tested on their own."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class Layout:
    """Where the Engine lives on the server."""
    prefix: Path = Path("/opt/falcon")            # the code and its runtime
    state: Path = Path("/var/lib/falcon")         # what must survive: master secret, certificate and key, model, client bundle
    etc: Path = Path("/etc/falcon")               # settings
    log: Path = Path("/var/log/falcon")
    user: str = "falcon"
    unit: str = "falcon-engine"

    @property
    def app(self) -> Path:
        return self.prefix / "app"

    @property
    def python(self) -> Path:
        return self.prefix / "venv" / "bin" / "python"

    @property
    def env_file(self) -> Path:
        return self.etc / "falcon.env"

    @property
    def unit_file(self) -> Path:
        return Path("/etc/systemd/system") / f"{self.unit}.service"

    @property
    def bundle(self) -> Path:
        return self.state / "falcon-client.json"

    @property
    def first_super_user(self) -> Path:
        return self.state / "first-super-user.txt"


def env_file(layout: Layout, database_url: str, port: int = 7400) -> str:
    """Every setting with its server path. Read by the service (EnvironmentFile) and by `python -m engine setup` (through the .env link)."""
    s = layout.state
    return "\n".join([
        "# Falcon Engine settings. Written by the installer; edit with care, then `systemctl restart falcon-engine`.",
        "# Secrets live here and in the state folder: this file is readable only by root and the falcon user.",
        "FALCON_ENGINE_HOST=0.0.0.0",
        f"FALCON_ENGINE_PORT={port}",
        f"FALCON_DATABASE_URL={database_url}",
        f"FALCON_TLS_CERT={(s / 'engine.crt').as_posix()}",
        f"FALCON_TLS_KEY={(s / 'engine.key').as_posix()}",
        f"FALCON_SECRET_PATH={(s / 'master.secret').as_posix()}",
        f"FALCON_LLM_MODEL_PATH={(s / 'models' / 'Qwen3-1.7B-Q8_0.gguf').as_posix()}",
        "",
    ])


def systemd_unit(layout: Layout) -> str:
    return f"""[Unit]
Description=Falcon Engine
Documentation=file://{layout.app.as_posix()}/docs/GETTING-STARTED.md
After=network-online.target postgresql.service
Wants=network-online.target

[Service]
Type=simple
User={layout.user}
Group={layout.user}
WorkingDirectory={layout.app.as_posix()}
EnvironmentFile={layout.env_file.as_posix()}
ExecStart={layout.python.as_posix()} -m engine
Restart=on-failure
RestartSec=5

# the Engine needs its own folders and the network, nothing else
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={layout.state.as_posix()} {layout.log.as_posix()}
ProtectKernelTunables=true
ProtectControlGroups=true
RestrictSUIDSGID=true

[Install]
WantedBy=multi-user.target
"""


def postgres_role_sql(password: str, database: str = "falcon", role: str = "falcon") -> list[str]:
    """Statements to run as the PostgreSQL superuser. Reached only when the settings do not yet name a database (a first install), so the role gets
    the password made for it whether or not an older role of that name was there; the database is made only if it is missing."""
    return [
        (f"DO $$ BEGIN IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '{role}') THEN "
         f"CREATE ROLE {role} LOGIN PASSWORD '{password}'; ELSE ALTER ROLE {role} LOGIN PASSWORD '{password}'; END IF; END $$;"),
        (f"SELECT 'CREATE DATABASE {database} OWNER {role}' "
         rf"WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = '{database}')\gexec"),
    ]
