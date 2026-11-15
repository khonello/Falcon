"""The Engine's installer (Linux, run once on the server, as root). Windows keeps its own: installers/windows/engine_install.py.

    sudo falcon-engine-install --names falcon.internal,192.168.1.20 --store https://<store> [--company-name Acme] [--dry-run]

Run from a payload folder (`python -m installers.payload engine <folder>`; the .deb puts one in /opt/falcon/payload) or from a checkout. It
(docs/SEATS-AND-SETUP.md sections 4 and 9, the same as on Windows):

     1. checks this is Linux, root, and a new enough Python, and that the payload is intact
     2. makes the `falcon` user (no login), and the folders: /opt/falcon (code), /var/lib/falcon (secret, certificate, model),
        /etc/falcon (settings), /var/log/falcon
     3. copies the code and makes its own Python runtime in /opt/falcon/venv with the libraries from the payload
     4. PostgreSQL: Falcon's own (installers/engine/pgsql.py), never mixed with one the server has: its programs in /opt/falcon/pgsql,
        its data in /var/lib/falcon-postgres, its own user and service (falcon-pg, falcon-postgres.service), localhost only on its own port,
        no socket file, only the Engine's role may log in. --database-url uses a server that exists instead.
     5. writes /etc/falcon/falcon.env and links it as the app's .env
     6. runs `python -m engine setup --no-first-admin`: certificate (valid for --names), schema, master secret, the firewall
     7. registers the Engine with the store (internet required): a server has no browser, so it prints a link and a short code to open
        on any phone or computer; store.json and the company file land beside the master secret
     8. hands the folders to the falcon user, with the secrets readable by it alone
     9. installs and starts the service (systemd: starts with the server after its database, restarts itself)

No Admin is made here: the first IT Admin runs the Admin setup on their own PC and signs in to the same account. Every step checks what is
there first, so running it again repairs or upgrades. The master secret is NEVER replaced: lose it and every machine must be set up again,
so it is backed up by a person (printed at the end).
"""

from __future__ import annotations

import argparse
import os
import secrets
import shutil
import socket
import sys
import time
from pathlib import Path

from installers import payload as payload_mod
from installers.common import InstallError, Plan, python_ok, run_cmd, write_text
from installers.engine import render
from installers.engine.pgsql import LinuxPostgres, find_bin
from installers.engine.render import Layout

HERE = Path(__file__).resolve().parent.parent.parent          # the payload folder (or the checkout)


class EngineInstall:
    def __init__(self, args: argparse.Namespace, layout: Layout, say=print) -> None:
        self.a = args
        self.layout = layout
        self.say = say
        self.source = Path(args.source).resolve() if args.source else HERE
        self.names = [n.strip() for n in args.names.split(",") if n.strip()]
        self._db_password = ""
        self.registered: dict = {}
        pgsql = Path(args.pgsql) if args.pgsql else layout.prefix / "pgsql"
        self.pg = LinuxPostgres(bin=find_bin(pgsql) or pgsql / "bin")

    # --- the plan ------------------------------------------------------------------------------------------------

    def plan(self) -> Plan:
        a, p = self.a, Plan("Falcon Engine installer", say=self.say)
        p.add("Check the machine", self.check, "Linux, root, Python 3.10+, an intact payload")
        p.add("The falcon user and folders", self.users_and_folders, f"user {self.layout.user}; {self.layout.prefix}, {self.layout.state}, {self.layout.etc}, {self.layout.log}")
        p.add("Copy the code", self.copy_code, f"to {self.layout.app}")
        p.add("The runtime", self.runtime, f"{self.layout.prefix}/venv with the payload's libraries", skip="--no-runtime" if a.no_runtime else None)
        p.add("PostgreSQL", self.database, f"Falcon's own, in {self.pg.pgdata}: localhost only, only the Engine logs in ({self.pg.unit})",
              skip="--database-url given" if a.database_url else ("--no-database" if a.no_database else None))
        p.add("Settings", self.settings, f"{self.layout.env_file}, linked as the app's .env")
        p.add("Setup", self.setup, "certificate, schema, master secret, firewall (python -m engine setup --no-first-admin)", skip="--no-setup" if a.no_setup else None)
        p.add("The store", self.register, "sign in on any device with the link and code shown; this Engine is registered (internet required)",
              skip="--no-store (development only: no seats are counted)" if a.no_store else ("--no-setup" if a.no_setup else None))
        p.add("Ownership", self.ownership, "the falcon user owns its folders; secrets readable by it alone")
        p.add("Service", self.service, f"{self.layout.unit_file}: starts with the server, restarts itself",
              skip="--no-service" if a.no_service else None)
        return p

    # --- the steps -----------------------------------------------------------------------------------------------

    def check(self) -> str:
        if sys.platform != "linux":
            raise InstallError("the Engine installs on Linux; this is " + sys.platform)
        if os.geteuid() != 0:
            raise InstallError("run this as root (sudo): it makes a user, folders and a service")
        if (why := python_ok()):
            raise InstallError(why)
        if (self.source / "manifest.json").exists():
            problems = payload_mod.verify(self.source)
            if problems:
                raise InstallError("the payload is not intact: " + "; ".join(problems[:5]))
            return f"payload {self.source} is intact"
        return f"installing from the checkout at {self.source} (no manifest to check)"

    def users_and_folders(self) -> str:
        L = self.layout
        rc, _ = run_cmd(["id", "-u", L.user], check=False)
        if rc != 0:
            run_cmd(["useradd", "--system", "--home-dir", str(L.state), "--shell", "/usr/sbin/nologin", "--user-group", L.user])
        for d in (L.prefix, L.state, L.etc, L.log, L.state / "models"):
            d.mkdir(parents=True, exist_ok=True)
        return f"user {L.user} and {', '.join(str(d) for d in (L.prefix, L.state, L.etc, L.log))}"

    def copy_code(self) -> str:
        src = self.source / "app" if (self.source / "app").is_dir() else self.source
        copied = 0
        for pkg in ("engine", "protocol", "common"):
            if not (src / pkg).is_dir():
                raise InstallError(f"{src / pkg} is missing")
            shutil.copytree(src / pkg, self.layout.app / pkg, dirs_exist_ok=True,
                            ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))
            copied += 1
        for extra in ("pyproject.toml", "requirements.txt"):
            for where in (self.source, src):
                if (where / extra).is_file():
                    shutil.copy2(where / extra, self.layout.app / extra)
                    break
        return f"{copied} packages into {self.layout.app}"

    def runtime(self) -> str:
        L = self.layout
        if not L.python.exists():
            run_cmd([sys.executable, "-m", "venv", str(L.prefix / "venv")])
        req = L.app / "requirements.txt"
        if not req.exists():
            req.write_text(payload_mod.requirements_for("engine", self.source), encoding="utf-8")
        cmd = [str(L.python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(req)]
        wheels = self.a.wheels or (str(self.source / "wheels") if (self.source / "wheels").is_dir() else None)
        if wheels:
            cmd[4:4] = ["--no-index", "--find-links", wheels]
        run_cmd(cmd)
        return f"libraries installed in {L.prefix / 'venv'}" + (" from the payload's wheels" if wheels else "")

    def database(self) -> str:
        L = self.layout
        if not (self.pg.bin / "postgres").is_file():
            raise InstallError(f"Falcon's PostgreSQL is not in {self.pg.bin} (the .deb puts it in /opt/falcon/pgsql; --pgsql)")
        said = [self.pg.user(), self.pg.init(), self.pg.service()]
        if L.env_file.exists() and "FALCON_DATABASE_URL=" in L.env_file.read_text(encoding="utf-8"):
            return "; ".join([*said, "the settings already name the database: kept (its password is not changed)"])
        self._db_password = secrets.token_urlsafe(24)
        said.append(self.pg.make_role(self.a.db_name, self.a.db_role, render.postgres_role_sql(self._db_password, self.a.db_name, self.a.db_role)))
        return "; ".join(said)

    def settings(self) -> str:
        L = self.layout
        url = self.a.database_url
        if not url and L.env_file.exists():
            existing = [ln for ln in L.env_file.read_text(encoding="utf-8").splitlines() if ln.startswith("FALCON_DATABASE_URL=")]
            url = existing[0].split("=", 1)[1] if existing else None
        if not url:
            if self.a.no_database:
                url = "postgresql://falcon:CHANGE-ME@127.0.0.1:5432/falcon"
            else:
                url = self.pg.url(self.a.db_name, self.a.db_role, self._db_password)
        own_pg = None if self.a.database_url else self.pg.bin
        changed = write_text(L.env_file, render.env_file(L, url, self.a.port, own_pg), 0o640)
        link = L.app / ".env"
        if link.is_symlink() or link.exists():
            link.unlink()
        link.symlink_to(L.env_file)
        return ("written " if changed else "kept ") + str(L.env_file)

    def setup(self) -> str:
        L = self.layout
        argv = [str(L.python), "-m", "engine", "setup", "--no-first-admin", "--no-operator-config"]
        if self.names:
            argv += ["--names", ",".join(self.names)]
        if self.a.download_model:
            argv.append("--download-model")
        rc, out = run_cmd(argv, cwd=L.app, check=False)
        self.say(out.rstrip())
        if rc != 0:
            raise InstallError("`engine setup` did not finish (see above); fix that and run the installer again")
        return "set up (certificate, schema, master secret, firewall)"

    def register(self) -> str:
        from common.store_keys import STORE_URL
        from installers.store_register import register
        from installers.store_signin import sign_in_device

        L = self.layout
        cert = L.state / "engine.crt"
        if not cert.exists():
            raise InstallError(f"no certificate at {cert}: the Setup step makes it")
        opener = None
        if self.a.test_open_link:                                   # only against scripts/store_stub.py: "the person" opens the link
            import urllib.request

            opener = lambda url: urllib.request.urlopen(url, timeout=10).read()
        self.registered = register(self.a.store or STORE_URL, L.state, self.names, self.a.port, cert.read_text(encoding="utf-8"),
                                   company_name=self.a.company_name, company_id=self.a.company_id, say=self.say,
                                   sign_in=lambda store: sign_in_device(store, say=self.say, open_link=opener))
        if self.registered.get("kept"):
            return f"kept the registration ({self.registered['engine_id']})"
        return f"registered as {self.registered['engine_id']}; the company file is {L.state / 'company.falcon'}"

    def ownership(self) -> str:
        L = self.layout
        run_cmd(["chown", "-R", f"{L.user}:{L.user}", str(L.state), str(L.log)])
        run_cmd(["chown", "-R", f"root:{L.user}", str(L.etc)])
        run_cmd(["chown", "-R", f"root:{L.user}", str(L.prefix)])
        for secret in ("master.secret", "engine.key"):
            f = L.state / secret
            if f.exists():
                f.chmod(0o600)
        for secret in ("store.json",):
            f = L.state / secret
            if f.exists():
                f.chmod(0o600)
        if self.pg.password_file.exists():
            run_cmd(["chown", "root:root", str(self.pg.password_file)])               # the database superuser's: root only
            self.pg.password_file.chmod(0o600)
        L.etc.chmod(0o750)
        L.state.chmod(0o750)
        return "the falcon user owns its folders; the secret and the key are readable by it alone"

    def service(self) -> str:
        L = self.layout
        changed = write_text(L.unit_file, render.systemd_unit(L, None if self.a.database_url else self.pg.unit), 0o644)
        run_cmd(["systemctl", "daemon-reload"])
        run_cmd(["systemctl", "enable", L.unit])
        run_cmd(["systemctl", "restart" if changed else "start", L.unit])
        end = time.monotonic() + 30
        while time.monotonic() < end:
            try:
                with socket.create_connection(("127.0.0.1", self.a.port), 1):
                    return f"{L.unit} is running and answering on port {self.a.port}"
            except OSError:
                time.sleep(0.5)
        raise InstallError(f"{L.unit} did not start answering: `journalctl -u {L.unit} -n 50`")

    # --- what to tell the person -----------------------------------------------------------------------------------

    def summary(self) -> str:
        L = self.layout
        lines = ["", "The Engine is installed.", "",
                 "  Now run the Admin setup (falcon-admin-setup.exe) on your IT Admin's PC: it signs in to the same account.",
                 "  Workers: the console's Machines page gives the Worker setup, with this company's file.",
                 f"  BACK UP, offline:  {L.state / 'master.secret'}  (every machine's key derives from it)", ""]
        return "\n".join(lines)


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="installers.engine.install", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--names", default="", help="every name and address the PCs will use to reach this server, comma-separated (the first is the one PCs are given)")
    ap.add_argument("--store", help="the store's address (default: common/store_keys.STORE_URL)")
    ap.add_argument("--company-name", help="the company's name, when the account signing in has none yet")
    ap.add_argument("--company-id", help="which company, when the account belongs to several")
    ap.add_argument("--no-store", action="store_true", help="development only: do not register with the store (no seats are counted)")
    ap.add_argument("--test-open-link", action="store_true", help="testing against scripts/store_stub.py only: open the sign-in link itself")
    ap.add_argument("--pgsql", help="Falcon's PostgreSQL programs (default /opt/falcon/pgsql)")
    ap.add_argument("--port", type=int, default=7400)
    ap.add_argument("--source", help="the payload folder (default: the one this installer is in)")
    ap.add_argument("--wheels", help="a folder of wheels, to install with no network")
    ap.add_argument("--database-url", help="an IT department's own PostgreSQL (a role and database that exist) instead of Falcon's own")
    ap.add_argument("--no-database", action="store_true", help="do not touch PostgreSQL")
    ap.add_argument("--db-name", default="falcon", help="the database to make (default falcon)")
    ap.add_argument("--db-role", default="falcon", help="the PostgreSQL role to make (default falcon)")
    ap.add_argument("--no-runtime", action="store_true", help="do not make the venv (the libraries are already there)")
    ap.add_argument("--no-setup", action="store_true", help="skip `engine setup`")
    ap.add_argument("--no-service", action="store_true", help="do not install the systemd service")
    ap.add_argument("--download-model", action="store_true", help="fetch the local language model (~1.8 GB)")
    ap.add_argument("--prefix", default="/opt/falcon")
    ap.add_argument("--state", default="/var/lib/falcon")
    ap.add_argument("--etc", default="/etc/falcon")
    ap.add_argument("--log", default="/var/log/falcon")
    ap.add_argument("--dry-run", action="store_true", help="list the steps and change nothing")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    layout = Layout(prefix=Path(args.prefix), state=Path(args.state), etc=Path(args.etc), log=Path(args.log))
    inst = EngineInstall(args, layout)
    try:
        inst.plan().run(dry_run=args.dry_run)
    except InstallError as exc:
        print(f"\nNot finished: {exc}\nFix that and run the installer again: every step checks what is already done.", file=sys.stderr)
        return 1
    if not args.dry_run:
        print(inst.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
