"""The Engine's own PostgreSQL on Windows, private to Falcon (docs/SEATS-AND-SETUP.md section 4; the user, 14 Nov 2026).

It is never mixed with a PostgreSQL the machine already has:

- its programs are in <Falcon Engine>\\pgsql (trimmed at build: `trim`), never on PATH, with no PGDATA or other setting in the environment
  and no entry of its own in Apps;
- its data is <ProgramData>\\Falcon Engine\\pgdata, readable only by its service account, the system and administrators;
- it listens on localhost only, on a port of its own that is not 5432 (the first free one from 54320);
- pg_hba.conf lets in one login, the Engine's own role to its own database, from 127.0.0.1 and ::1, with a password (scram-sha-256);
- it runs as the FalconPostgres service under its own virtual account (NT SERVICE\\FalconPostgres);
- no firewall rule is made: nothing outside this machine can reach it.

The superuser's password is made here and kept in the protected data folder (pg-superuser.txt), for upgrades. The superuser can log in only
while this sets the cluster up: the final pg_hba.conf has no line for it. Every step looks first, so running it again repairs.
"""

from __future__ import annotations

import os
import secrets
import shutil
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path

from installers.common import InstallError, run_cmd
from installers.private_pg_common import (
    CONF_MARK,
    KEEP_PROGRAMS,
    conf_text,
    free_port,
    hba_text,
    port_of,
)

SERVICE = "FalconPostgres"
__all__ = ["CONF_MARK", "PrivatePostgres", "conf_text", "free_port", "hba_text", "trim"]


def trim(src: Path, dest: Path) -> int:
    """At build: copy only what a running Engine needs from the EDB binaries' `pgsql` folder (no pgAdmin, StackBuilder, headers, docs or
    import libraries). Returns the bytes copied."""
    if not (src / "bin" / "postgres.exe").is_file():
        raise InstallError(f"{src} is not PostgreSQL's pgsql folder (no bin\\postgres.exe)")
    if dest.exists():
        shutil.rmtree(dest)
    total = 0
    (dest / "bin").mkdir(parents=True)
    for f in (src / "bin").iterdir():
        if f.is_file() and (f.suffix.lower() == ".dll" or (f.suffix.lower() == ".exe" and f.stem.lower() in KEEP_PROGRAMS)):
            shutil.copy2(f, dest / "bin" / f.name)
            total += f.stat().st_size
    for f in (src / "lib").rglob("*.dll"):
        out = dest / "lib" / f.relative_to(src / "lib")
        out.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, out)
        total += f.stat().st_size
    shutil.copytree(src / "share", dest / "share")
    total += sum(f.stat().st_size for f in (dest / "share").rglob("*") if f.is_file())
    return total


@dataclass
class PrivatePostgres:
    bin: Path                       # <Falcon Engine>\pgsql\bin
    pgdata: Path                    # <ProgramData>\Falcon Engine\pgdata
    secrets_dir: Path               # the protected data folder: pg-superuser.txt
    service: str = SERVICE
    superuser: str = "postgres"
    acl: bool = True

    def exe(self, name: str) -> str:
        return str(self.bin / f"{name}.exe")

    @property
    def password_file(self) -> Path:
        return self.secrets_dir / "pg-superuser.txt"

    @property
    def account(self) -> str:
        return f"NT SERVICE\\{self.service}"

    def port(self) -> int | None:
        return port_of(self.pgdata)

    def _superuser_password(self) -> str:
        if self.password_file.exists():
            return self.password_file.read_text(encoding="utf-8").strip()
        pw = secrets.token_urlsafe(32)
        self.password_file.write_text(pw + "\n", encoding="utf-8")
        return pw

    # --- the steps ----------------------------------------------------------------------------------------------------------------------

    def init(self) -> str:
        """The cluster, once: a superuser password made here, UTF-8, scram-sha-256, localhost only, a port of its own."""
        if (self.pgdata / "PG_VERSION").exists():
            port = self.port()
            if port is None:
                raise InstallError(f"{self.pgdata} holds a PostgreSQL cluster Falcon did not set up: it is left alone")
            return f"kept the cluster in {self.pgdata} (port {port})"
        self.pgdata.parent.mkdir(parents=True, exist_ok=True)
        pw = self._superuser_password()
        pwfile = self.secrets_dir / "pg-initdb.tmp"
        pwfile.write_text(pw + "\n", encoding="utf-8")
        try:
            run_cmd([self.exe("initdb"), "-D", str(self.pgdata), "-U", self.superuser, f"--pwfile={pwfile}", "-A", "scram-sha-256",
                     "-E", "UTF8", "--locale-provider=builtin", "--builtin-locale=C.UTF-8", "--no-instructions"])
        finally:
            pwfile.unlink(missing_ok=True)
        port = free_port()
        with (self.pgdata / "postgresql.conf").open("a", encoding="utf-8") as f:
            f.write("\n" + conf_text(port))
        return f"made the cluster in {self.pgdata}, port {port}, localhost only"

    def lock(self) -> str:
        """pgdata: its service account, the system and administrators only (nothing inherited). After `register`: the virtual account
        exists only once its service does."""
        if not self.acl:
            return "skipped (--no-acl)"
        run_cmd(["icacls", str(self.pgdata), "/inheritance:r", "/grant:r", "*S-1-5-18:(OI)(CI)F", "*S-1-5-32-544:(OI)(CI)F",
                 f"{self.account}:(OI)(CI)F", "/Q"])
        # everything inside inherits exactly that (with /T the folder-only grants never reached a file, which was left with no access at all)
        run_cmd(["icacls", str(self.pgdata / "*"), "/reset", "/T", "/Q"])
        return f"{self.pgdata}: {self.account}, the system and administrators only"

    def register(self) -> str:
        """The FalconPostgres service, under its own virtual account, started with Windows."""
        if _service_exists(self.service):
            return f"kept the {self.service} service"
        run_cmd([self.exe("pg_ctl"), "register", "-N", self.service, "-U", self.account, "-D", str(self.pgdata), "-S", "auto", "-w"])
        run_cmd(["sc.exe", "description", self.service, "Falcon Engine's own PostgreSQL: local to this machine, used by Falcon only"], check=False)
        run_cmd(["sc.exe", "failure", self.service, "reset=", "86400", "actions=", "restart/5000/restart/15000/restart/60000"], check=False)
        return f"registered {self.service} as {self.account}"

    def start(self, wait: float = 60.0) -> str:
        run_cmd(["sc.exe", "start", self.service], check=False)
        port = self.port()
        end = time.monotonic() + wait
        while time.monotonic() < end:
            rc = subprocess.run([self.exe("pg_isready"), "-h", "127.0.0.1", "-p", str(port), "-q"], check=False).returncode
            if rc == 0:
                return f"{self.service} is answering on 127.0.0.1:{port}"
            time.sleep(0.5)
        raise InstallError(f"{self.service} did not start answering; its log is in {self.pgdata / 'log'}")

    def make_role(self, db_name: str, db_role: str, role_sql: list[str]) -> str:
        """The Engine's role and database, made as the superuser; then pg_hba.conf is closed to everyone but the Engine's role."""
        port = self.port()
        hba = self.pgdata / "pg_hba.conf"
        hba.write_text(hba_text(db_name, db_role, superuser=self.superuser), encoding="utf-8")
        env = {**os.environ, "PGPASSWORD": self._superuser_password()}
        base = [self.exe("psql"), "-X", "-q", "-v", "ON_ERROR_STOP=1", "-h", "127.0.0.1", "-p", str(port), "-U", self.superuser, "-d", "postgres"]
        try:
            self._reload(base, env)
            for sql in role_sql:
                run_cmd(base, input_text=sql + "\n", env=env)
        finally:
            hba.write_text(hba_text(db_name, db_role), encoding="utf-8")
            self._reload(base, env)
        return f"the {db_role} role and the {db_name} database; only {db_role} may log in, from this machine"

    def _reload(self, base: list[str], env: dict[str, str]) -> None:
        rc, _ = run_cmd([self.exe("pg_ctl"), "reload", "-D", str(self.pgdata), "-s"], check=False)
        if rc != 0:
            run_cmd(base, input_text="SELECT pg_reload_conf();\n", env=env, check=False)
        time.sleep(0.5)

    def url(self, db_name: str, db_role: str, password: str) -> str:
        return f"postgresql://{db_role}:{password}@127.0.0.1:{self.port()}/{db_name}"

    # --- taking it out -------------------------------------------------------------------------------------------------------------------

    def unregister(self) -> str:
        if not _service_exists(self.service):
            return f"no {self.service} service"
        run_cmd(["sc.exe", "stop", self.service], check=False)
        end = time.monotonic() + 30
        while time.monotonic() < end and _service_running(self.service):
            time.sleep(0.5)
        run_cmd([self.exe("pg_ctl"), "unregister", "-N", self.service], check=False)
        if _service_exists(self.service):
            run_cmd(["sc.exe", "delete", self.service], check=False)
        return f"stopped and removed {self.service}"


def _service_exists(name: str) -> bool:
    return subprocess.run(["sc.exe", "query", name], capture_output=True, check=False).returncode == 0


def _service_running(name: str) -> bool:
    out = subprocess.run(["sc.exe", "query", name], capture_output=True, text=True, check=False).stdout
    return "RUNNING" in out or "STOP_PENDING" in out
