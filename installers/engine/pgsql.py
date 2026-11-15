"""The Engine's own PostgreSQL on Linux, private to Falcon (docs/SEATS-AND-SETUP.md section 9; the same rules as Windows).

It is never mixed with a PostgreSQL the server already has:

- its programs are in /opt/falcon/pgsql (copied at build from the build server's PostgreSQL by `assemble`, in PostgreSQL's own relative
  layout so they find their files there), never on PATH; the package depends only on the libraries they need, not on a postgresql
  package, so no cluster of the distribution's is made or touched;
- its data is /var/lib/falcon-postgres/data, owned by its own system user `falcon-pg`, mode 0700;
- it listens on localhost only, on a port of its own that is not 5432 (the first free one from 54320), with no socket file at all;
- pg_hba.conf lets in one login, the Engine's own role to its own database, from 127.0.0.1 and ::1, with a password (scram-sha-256);
- it runs as falcon-postgres.service (systemd) as `falcon-pg`;
- no firewall rule is made: nothing outside the server can reach it.

The superuser's password is made here and kept in /etc/falcon/pg-superuser (root only), for upgrades; the superuser can log in only while
this sets the cluster up. Every step looks first, so running it again repairs.
"""

from __future__ import annotations

import os
import secrets
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

from installers.common import InstallError, run_cmd, write_text
from installers.private_pg_common import KEEP_PROGRAMS, conf_text, free_port, hba_text, port_of

UNIT = "falcon-postgres"
USER = "falcon-pg"


def assemble(version: str, dest: Path, *, lib_root: Path = Path("/usr/lib/postgresql"), share_root: Path = Path("/usr/share/postgresql")) -> int:
    """At build: the PostgreSQL `version` installed on the build server, copied into `dest` in the same relative layout
    (lib/postgresql/<v>/bin, lib/postgresql/<v>/lib, share/postgresql/<v>), only the programs Falcon uses. Returns the bytes copied."""
    src_bin, src_lib, src_share = lib_root / version / "bin", lib_root / version / "lib", share_root / version
    if not (src_bin / "postgres").is_file():
        raise InstallError(f"no PostgreSQL {version} on this build machine ({src_bin / 'postgres'}): install postgresql-{version} to build")
    if dest.exists():
        shutil.rmtree(dest)
    out_bin, out_lib, out_share = dest / "lib" / "postgresql" / version / "bin", dest / "lib" / "postgresql" / version / "lib", dest / "share" / "postgresql" / version
    out_bin.mkdir(parents=True)
    total = 0
    for name in KEEP_PROGRAMS:
        if (src_bin / name).is_file():
            shutil.copy2(src_bin / name, out_bin / name)
            total += (src_bin / name).stat().st_size
    shutil.copytree(src_lib, out_lib, symlinks=True, ignore=shutil.ignore_patterns("*.bc", "bitcode", "pgxs"))
    shutil.copytree(src_share, out_share, symlinks=True, ignore=shutil.ignore_patterns("man"))
    total += sum(f.stat().st_size for d in (out_lib, out_share) for f in d.rglob("*") if f.is_file() and not f.is_symlink())
    return total


def find_bin(pgsql: Path) -> Path | None:
    """The bin folder of the PostgreSQL the package carries."""
    found = sorted(pgsql.glob("lib/postgresql/*/bin/postgres"))
    return found[-1].parent if found else None


def unit_text(bin_dir: Path, pgdata: Path) -> str:
    return f"""[Unit]
Description=Falcon Engine's own PostgreSQL (local to this server, used by Falcon only)
After=network.target

[Service]
Type=notify
User={USER}
Group={USER}
ExecStart={(bin_dir / 'postgres').as_posix()} -D {pgdata.as_posix()}
ExecReload=/bin/kill -HUP $MAINPID
KillMode=mixed
KillSignal=SIGINT
TimeoutSec=300
Restart=on-failure
RestartSec=5
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths={pgdata.as_posix()}

[Install]
WantedBy=multi-user.target
"""


@dataclass
class LinuxPostgres:
    bin: Path                                          # /opt/falcon/pgsql/lib/postgresql/<v>/bin
    pgdata: Path = Path("/var/lib/falcon-postgres/data")
    password_file: Path = Path("/etc/falcon/pg-superuser")
    unit: str = UNIT
    superuser: str = "postgres"

    @property
    def unit_file(self) -> Path:
        return Path("/etc/systemd/system") / f"{self.unit}.service"

    def exe(self, name: str) -> str:
        return str(self.bin / name)

    def port(self) -> int | None:
        return port_of(self.pgdata)

    def _superuser_password(self) -> str:
        if self.password_file.exists():
            return self.password_file.read_text(encoding="utf-8").strip()
        pw = secrets.token_urlsafe(32)
        write_text(self.password_file, pw + "\n", 0o600)
        os.chown(self.password_file, 0, 0)
        return pw

    def user(self) -> str:
        rc, _ = run_cmd(["id", "-u", USER], check=False)
        if rc != 0:
            run_cmd(["useradd", "--system", "--home-dir", str(self.pgdata.parent), "--shell", "/usr/sbin/nologin", "--user-group", USER])
        self.pgdata.parent.mkdir(parents=True, exist_ok=True)
        run_cmd(["chown", f"{USER}:{USER}", str(self.pgdata.parent)])
        self.pgdata.parent.chmod(0o700)
        return f"user {USER}, {self.pgdata.parent} (0700)"

    def init(self) -> str:
        if (self.pgdata / "PG_VERSION").exists():
            port = self.port()
            if port is None:
                raise InstallError(f"{self.pgdata} holds a PostgreSQL cluster Falcon did not set up: it is left alone")
            return f"kept the cluster in {self.pgdata} (port {port})"
        pw = self._superuser_password()
        with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8") as f:
            f.write(pw + "\n")
            pwfile = Path(f.name)
        try:
            run_cmd(["chown", USER, str(pwfile)])
            pwfile.chmod(0o600)
            self.pgdata.mkdir(parents=True, exist_ok=True)
            run_cmd(["chown", f"{USER}:{USER}", str(self.pgdata)])
            self.pgdata.chmod(0o700)
            run_cmd(["runuser", "-u", USER, "--", self.exe("initdb"), "-D", str(self.pgdata), "-U", self.superuser, f"--pwfile={pwfile}",
                     "-A", "scram-sha-256", "-E", "UTF8", "--locale=C.UTF-8", "--no-instructions"])
        finally:
            pwfile.unlink(missing_ok=True)
        port = free_port()
        with (self.pgdata / "postgresql.conf").open("a", encoding="utf-8") as f:
            f.write("\n" + conf_text(port, unix_socket=False))
        return f"made the cluster in {self.pgdata}, port {port}, localhost only, no socket"

    def service(self, wait: float = 60.0) -> str:
        changed = write_text(self.unit_file, unit_text(self.bin, self.pgdata), 0o644)
        run_cmd(["systemctl", "daemon-reload"])
        run_cmd(["systemctl", "enable", self.unit])
        run_cmd(["systemctl", "restart" if changed else "start", self.unit])
        port = self.port()
        end = time.monotonic() + wait
        while time.monotonic() < end:
            if subprocess.run([self.exe("pg_isready"), "-h", "127.0.0.1", "-p", str(port), "-q"], check=False).returncode == 0:
                return f"{self.unit} is answering on 127.0.0.1:{port}"
            time.sleep(0.5)
        raise InstallError(f"{self.unit} did not start answering: `journalctl -u {self.unit} -n 50`")

    def make_role(self, db_name: str, db_role: str, role_sql: list[str]) -> str:
        """The Engine's role and database, made as the superuser; then pg_hba.conf is closed to everyone but the Engine's role."""
        port = self.port()
        hba = self.pgdata / "pg_hba.conf"
        env = {**os.environ, "PGPASSWORD": self._superuser_password()}
        base = [self.exe("psql"), "-X", "-q", "-v", "ON_ERROR_STOP=1", "-h", "127.0.0.1", "-p", str(port), "-U", self.superuser, "-d", "postgres"]
        hba.write_text(hba_text(db_name, db_role, superuser=self.superuser), encoding="utf-8")
        self._reload()
        try:
            for sql in role_sql:
                run_cmd(base, input_text=sql + "\n", env=env)
        finally:
            hba.write_text(hba_text(db_name, db_role), encoding="utf-8")
            self._reload()
        return f"the {db_role} role and the {db_name} database; only {db_role} may log in, from this server"

    def _reload(self) -> None:
        run_cmd(["systemctl", "reload", self.unit], check=False)
        time.sleep(0.5)

    def url(self, db_name: str, db_role: str, password: str) -> str:
        return f"postgresql://{db_role}:{password}@127.0.0.1:{self.port()}/{db_name}"
