"""What Falcon's own PostgreSQL is, on every platform (docs/SEATS-AND-SETUP.md section 9): who may log in, how it is set, which port.

The service and the account it runs as are per platform and kept apart: installers/windows/private_pg.py (FalconPostgres, NT SERVICE\\
FalconPostgres) and installers/engine/pgsql.py (falcon-postgres.service, the falcon-pg user). Stdlib only.
"""

from __future__ import annotations

import socket
from pathlib import Path

from installers.common import InstallError

FIRST_PORT = 54320
KEEP_PROGRAMS = ("postgres", "initdb", "pg_ctl", "psql", "pg_isready", "pg_dump", "pg_dumpall", "pg_restore", "pg_upgrade", "pg_controldata",
                 "pg_resetwal", "pg_amcheck", "pg_checksums", "vacuumdb", "reindexdb")


def free_port(start: int = FIRST_PORT, tries: int = 50) -> int:
    for port in range(start, start + tries):
        if port == 5432:
            continue
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            try:
                s.bind(("127.0.0.1", port))
            except OSError:
                continue
            return port
    raise InstallError(f"no free port from {start} to {start + tries - 1} for Falcon's PostgreSQL")


def hba_text(db_name: str, db_role: str, *, superuser: str | None = None) -> str:
    """Who may log in: the Engine's role to its database from this machine. While setting up, the superuser too (from this machine)."""
    lines = ["# Falcon's own PostgreSQL: only the Falcon Engine logs in, from this machine. Written by the installer.",
             "# TYPE  DATABASE  USER  ADDRESS  METHOD",
             f"host    {db_name}    {db_role}    127.0.0.1/32    scram-sha-256",
             f"host    {db_name}    {db_role}    ::1/128         scram-sha-256"]
    if superuser:
        lines += [f"host    all    {superuser}    127.0.0.1/32    scram-sha-256    # only while the installer sets it up"]
    return "\n".join(lines) + "\n"


CONF_MARK = "# --- Falcon (written by the installer) ---"


def conf_text(port: int, *, unix_socket: bool = True) -> str:
    """Localhost only, its own port. `unix_socket=False` (Linux): no socket file either, so only a password login over TCP gets in."""
    return "\n".join([CONF_MARK, "listen_addresses = 'localhost'", f"port = {port}", "password_encryption = 'scram-sha-256'",
                      *([] if unix_socket else ["unix_socket_directories = ''"]),
                      "logging_collector = on", "log_directory = 'log'", "log_rotation_age = '7d'", "log_truncate_on_rotation = on",
                      "log_filename = 'postgresql-%a.log'", ""])




def port_of(pgdata: Path) -> int | None:
    """The port Falcon gave this cluster, or None if Falcon did not set it up."""
    conf = pgdata / "postgresql.conf"
    if not conf.exists():
        return None
    text = conf.read_text(encoding="utf-8", errors="replace")
    if CONF_MARK not in text:
        return None
    for line in text.split(CONF_MARK, 1)[1].splitlines():
        if line.strip().startswith("port ="):
            return int(line.split("=", 1)[1].strip())
    return None
