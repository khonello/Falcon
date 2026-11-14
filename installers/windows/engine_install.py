"""The Engine's installer for Windows (the user, 14 Nov 2026: deployment is on Windows). Linux keeps its own: installers/engine/install.py.

    python -m installers.windows.engine_install --names falcon.internal --hostname IT-01 --admin-url-file pg.txt [--download-model] [--dry-run]
    python -m installers.windows.engine_install --uninstall [--purge-data]

Run as an administrator, from a payload folder (`python -m installers.payload engine <folder>`; `falcon-engine-setup.exe` does all of this).
PostgreSQL is installed first (the EDB installer from postgresql.org); this needs its superuser's URL once, to make the Engine's own role
(`--admin-url-file`: a file holding postgresql://postgres:<password>@localhost:5432/postgres, so the password is never on a command line). It:

     1. checks this is Windows, an administrator, and that the payload is intact
     2. stops the Engine's service if an older one is running (an upgrade)
     3. copies the code to C:\\Program Files\\Falcon Engine\\app
     4. makes its own Python runtime there, from the payload's wheels (no network needed)
     5. makes C:\\ProgramData\\Falcon Engine: settings, master secret, certificate and key, model, update packages, logs -- readable only
        by the system and administrators
     6. PostgreSQL: a `falcon` role with a password made here, and the `falcon` database
     7. writes falcon.env there (every setting, with absolute paths)
     8. runs `python -m engine setup`: certificate for --names, schema, master secret, the first IT Admin, the firewall rule, the client bundle
     9. installs and starts the FalconEngine service (starts with Windows, restarts itself) and waits for it to answer
    10. writes a receipt (install.json) the uninstall reads

Every step checks what is there first, so running it again repairs or upgrades: the master secret, the database password and the first
Admin are never made twice. The uninstall removes the service and the program and keeps the data folder (the master secret!) and the
database unless --purge-data, which still never drops the database.
"""

from __future__ import annotations

import argparse
import json
import os
import secrets
import shutil
import socket
import sys
import time
from pathlib import Path

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))              # run as a script by the uninstaller (see falcon-engine.iss)

from installers import payload as payload_mod
from installers.common import InstallError, Plan, python_ok, run_cmd, write_text
from installers.engine import render
from installers.windows.install import is_admin, lock_to_system_and_admins

HERE = Path(__file__).resolve().parent.parent.parent
SERVICE = "FalconEngine"
SETUPS_OWN = ("python", "unins000.exe", "unins000.dat", "unins000.msg")


def find_psql() -> Path | None:
    """PostgreSQL's psql.exe: on the PATH, else the newest under Program Files\\PostgreSQL."""
    found = shutil.which("psql")
    if found:
        return Path(found)
    root = Path(os.environ.get("ProgramFiles", r"C:\Program Files")) / "PostgreSQL"
    versions = sorted((p for p in root.glob("*/bin/psql.exe")), key=lambda p: [int(x) if x.isdigit() else 0 for x in p.parent.parent.name.split(".")])
    return versions[-1] if versions else None


def env_text(data: Path, database_url: str, port: int) -> str:
    """Every setting with its absolute path (a service's working folder is C:\\Windows\\System32: nothing may be relative)."""
    return "\n".join([
        "# Falcon Engine settings. Written by the installer; edit with care, then restart the FalconEngine service (services.msc).",
        "# Secrets live here and in this folder, which only the system account and administrators may read.",
        "FALCON_ENGINE_HOST=0.0.0.0",
        f"FALCON_ENGINE_PORT={port}",
        f"FALCON_DATABASE_URL={database_url}",
        f"FALCON_TLS_CERT={(data / 'engine.crt').as_posix()}",
        f"FALCON_TLS_KEY={(data / 'engine.key').as_posix()}",
        f"FALCON_SECRET_PATH={(data / 'master.secret').as_posix()}",
        f"FALCON_LLM_MODEL_PATH={(data / 'models' / 'Qwen3-1.7B-Q8_0.gguf').as_posix()}",
        "",
    ])


class EngineInstall:
    def __init__(self, args: argparse.Namespace, say=print) -> None:
        self.a = args
        self.say = say
        self.source = Path(args.source).resolve() if args.source else HERE
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        pd = os.environ.get("ProgramData", r"C:\ProgramData")
        self.target = Path(args.target) if args.target else Path(pf) / "Falcon Engine"
        self.data = Path(args.data) if args.data else Path(pd) / "Falcon Engine"
        self.service = args.service_name or SERVICE
        self.names = [n.strip() for n in (args.names or "").split(",") if n.strip()]
        self.first_admin: dict[str, str] = {}
        self.fingerprint = ""
        self._db_password = ""

    @property
    def app(self) -> Path:
        return self.target / "app"

    @property
    def python(self) -> Path:
        return self.target / "runtime" / "Scripts" / "python.exe"

    @property
    def env_file(self) -> Path:
        return self.data / "falcon.env"

    @property
    def bundle(self) -> Path:
        return self.data / "falcon-client.json"

    @property
    def first_admin_file(self) -> Path:
        return self.data / "first-admin.txt"

    def _env(self) -> dict[str, str]:
        return {**os.environ, "FALCON_ENV_FILE": str(self.env_file)}

    # --- the plan ------------------------------------------------------------------------------------------------

    def plan(self) -> Plan:
        a, p = self.a, Plan("Falcon Engine installer (Windows)", say=self.say)
        p.add("Check", self.check, "Windows, administrator, the payload's hashes")
        p.add("Stop the old service", self.stop_old, f"{self.service}, if it is there")
        p.add("Copy the code", self.copy_code, f"engine, protocol, common into {self.app}")
        p.add("The runtime", self.runtime, f"{self.target / 'runtime'} with the payload's libraries", skip="--no-runtime" if a.no_runtime else None)
        p.add("The data folder", self.folders, f"{self.data}: readable by the system and administrators only")
        p.add("PostgreSQL", self.database, "the falcon role and database, with a password made here",
              skip="--database-url given" if a.database_url else ("--no-database" if a.no_database else None))
        p.add("Settings", self.settings, str(self.env_file))
        p.add("Setup", self.setup, "certificate, schema, master secret, first IT Admin, firewall, client bundle (python -m engine setup)",
              skip="--no-setup" if a.no_setup else None)
        p.add("The Engine service", self.install_service, f"{self.service}: starts with Windows, restarts itself", skip="--no-service" if a.no_service else None)
        p.add("Receipt", self.receipt, str(self.target / "install.json"))
        return p

    # --- the steps -------------------------------------------------------------------------------------------------

    def check(self) -> str:
        if sys.platform != "win32":
            raise InstallError("this is the Engine's Windows installer; on Linux use installers.engine.install (the .deb)")
        if not is_admin():
            raise InstallError("run this as an administrator: it installs a service, a firewall rule, and sets who may read the secrets")
        if (why := python_ok()):
            raise InstallError(why)
        if (self.source / "manifest.json").exists():
            problems = payload_mod.verify(self.source)
            if problems:
                raise InstallError("the payload is not intact: " + "; ".join(problems[:5]))
            if json.loads((self.source / "manifest.json").read_text(encoding="utf-8")).get("role") != "engine":
                raise InstallError("this payload is not the Engine's")
            return f"payload {self.source} is intact"
        return f"installing from the checkout at {self.source} (no manifest to check)"

    def stop_old(self) -> str:
        if not self.python.exists():
            return "nothing installed yet"
        rc, out = run_cmd([str(self.python), "-m", "engine", "service", "stop", "--name", self.service], check=False, cwd=self.app)
        return out.strip().splitlines()[-1] if out.strip() else ("stopped" if rc == 0 else "was not running")

    def copy_code(self) -> str:
        src = self.source / "app" if (self.source / "app").is_dir() else self.source
        for pkg in ("engine", "protocol", "common"):
            if not (src / pkg).is_dir():
                raise InstallError(f"{src / pkg} is missing from the payload")
            if (self.app / pkg).exists():
                shutil.rmtree(self.app / pkg)                    # no file of an older version is left behind
            shutil.copytree(src / pkg, self.app / pkg, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))
        if (self.source / "installers").is_dir():                # the uninstall runs this installer from the program's own folder
            if (self.app / "installers").exists():
                shutil.rmtree(self.app / "installers")
            shutil.copytree(self.source / "installers", self.app / "installers", ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for name in ("requirements.txt", "pyproject.toml", ".env.example"):
            for where in (self.source, src):
                if (where / name).is_file():
                    shutil.copy2(where / name, self.app / name)
                    break
        return f"3 packages in {self.app}"

    def runtime(self) -> str:
        venv = self.target / "runtime"
        if not self.python.exists():
            run_cmd([self.a.python or sys.executable, "-m", "venv", str(venv)])
        write_text(venv / "Lib" / "site-packages" / "falcon.pth", str(self.app) + "\n")    # the runtime finds the code without installing it
        req = self.app / "requirements.txt"
        if not req.exists():
            req.write_text(payload_mod.requirements_for("engine", self.source), encoding="utf-8")
        cmd = [str(self.python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(req)]
        wheels = self.a.wheels or (str(self.source / "wheels") if (self.source / "wheels").is_dir() else None)
        if wheels:
            cmd[4:4] = ["--no-index", "--find-links", wheels]
        run_cmd(cmd)
        return f"libraries installed in {venv}" + (" from the payload's wheels (no network used)" if wheels else "")

    def folders(self) -> str:
        for d in (self.data, self.data / "models", self.data / "logs", self.data / "updates"):
            d.mkdir(parents=True, exist_ok=True)
        if not self.a.no_acl:
            lock_to_system_and_admins(self.data)
        return f"{self.data}" + ("" if self.a.no_acl else ", readable by the system and administrators only")

    def database(self) -> str:
        if self.env_file.exists() and "FALCON_DATABASE_URL=" in self.env_file.read_text(encoding="utf-8"):
            return "the settings already name a database: kept (its password is not changed)"
        admin_url = Path(self.a.admin_url_file).read_text(encoding="utf-8").strip() if self.a.admin_url_file else (self.a.admin_url or "")
        if not admin_url:
            raise InstallError("PostgreSQL's superuser is needed once, to make the Engine's role: give --admin-url-file (a file holding "
                               "postgresql://postgres:<password>@localhost:5432/postgres), or --database-url for a role and database that exist")
        psql = find_psql()
        if psql is None:
            raise InstallError("PostgreSQL is not installed (no psql.exe): install it from postgresql.org, then run this again")
        self._db_password = secrets.token_urlsafe(24)
        for sql in render.postgres_role_sql(self._db_password, self.a.db_name, self.a.db_role):
            run_cmd([str(psql), "-v", "ON_ERROR_STOP=1", "-X", "-q", "-d", admin_url], input_text=sql + "\n")
        return f"the {self.a.db_role} role and the {self.a.db_name} database are there"

    def settings(self) -> str:
        url = self.a.database_url
        if not url and self.env_file.exists():
            found = [ln for ln in self.env_file.read_text(encoding="utf-8").splitlines() if ln.startswith("FALCON_DATABASE_URL=")]
            url = found[0].split("=", 1)[1] if found else None
        if not url:
            url = (f"postgresql://{self.a.db_role}:{self._db_password}@localhost:5432/{self.a.db_name}" if self._db_password
                   else f"postgresql://{self.a.db_role}:CHANGE-ME@localhost:5432/{self.a.db_name}")
        changed = write_text(self.env_file, env_text(self.data, url, self.a.port))
        return ("written " if changed else "kept ") + str(self.env_file)

    def setup(self) -> str:
        argv = [str(self.python), "-m", "engine", "setup", "--hostname", self.a.hostname, "--no-operator-config"]
        if self.names:
            argv += ["--names", ",".join(self.names)]
        if self.a.download_model:
            argv.append("--download-model")
        rc, out = run_cmd(argv, cwd=self.app, check=False, env=self._env())
        self.say(out.rstrip())
        if rc != 0:
            raise InstallError("`engine setup` did not finish (see above); fix that and run the installer again")
        for key in ("client_id", "client_key"):
            for line in out.splitlines():
                if line.strip().startswith(key + ":"):
                    self.first_admin[key] = line.split(":", 1)[1].strip()
        if self.bundle.exists():
            self.fingerprint = json.loads(self.bundle.read_text(encoding="utf-8")).get("ca_sha256", "")
        if self.first_admin.keys() >= {"client_id", "client_key"}:
            write_text(self.first_admin_file, "The first IT Admin (printed once by the installer; delete this file after it is safely held)\n"
                       f"client_id:  {self.first_admin['client_id']}\nclient_key: {self.first_admin['client_key']}\n")
            return f"set up; the first IT Admin's id and key are in {self.first_admin_file}"
        return "set up (an Admin already existed: no new key was made)"

    def install_service(self) -> str:
        base = [str(self.python), "-m", "engine", "service"]
        run_cmd(base + ["install", "--name", self.service, "--env", str(self.env_file)], cwd=self.app)
        _rc, out = run_cmd(base + ["start", "--name", self.service, "--env", str(self.env_file)], cwd=self.app, check=False)
        end = time.monotonic() + 60
        while time.monotonic() < end:
            try:
                with socket.create_connection(("127.0.0.1", self.a.port), 1):
                    return f"{self.service} is running and answering on port {self.a.port}"
            except OSError:
                time.sleep(0.5)
        raise InstallError(f"{self.service} did not start answering ({out.strip()}); its log is {self.data / 'logs' / 'engine.log'}")

    def _version(self) -> str:
        try:
            got = json.loads((self.source / "manifest.json").read_text(encoding="utf-8")).get("version")
            if got:
                return str(got)
        except (OSError, ValueError):
            pass
        return payload_mod.project_version(self.source) if (self.source / "pyproject.toml").exists() else "0.0.0"

    def receipt(self) -> str:
        path = self.target / "install.json"
        path.write_text(json.dumps({"role": "engine", "version": self._version(), "service": self.service, "data": str(self.data)}, indent=2), encoding="utf-8")
        return str(path)

    def summary(self) -> str:
        lines = ["", "The Engine is installed.", ""]
        if self.fingerprint:
            lines += ["  Certificate fingerprint (read this out when installing a PC, to be sure it is this Engine):", f"    {self.fingerprint}", ""]
        lines += [f"  Give every PC's installer:  {self.bundle}",
                  f"  The first IT Admin's id and key:  {self.first_admin_file}  (keep them, then delete the file)",
                  f"  BACK UP, offline:  {self.data / 'master.secret'}  (every machine's key derives from it)", ""]
        return "\n".join(lines)

    # --- taking it out ----------------------------------------------------------------------------------------------

    def uninstall_plan(self) -> Plan:
        p = Plan("Falcon Engine uninstall (Windows)", say=self.say)
        p.add("Stop and remove the service", self.remove_service, self.service)
        p.add("Remove the program", self.remove_program, str(self.target))
        p.add("Data", self.remove_data, "kept unless --purge-data (the master secret: without it every machine must be registered again); "
                                         "the database is never dropped")
        return p

    def remove_service(self) -> str:
        if not self.python.exists():
            return "no service to remove"
        _rc, out = run_cmd([str(self.python), "-m", "engine", "service", "uninstall", "--name", self.service], check=False, cwd=self.app)
        return out.strip().splitlines()[-1] if out.strip() else "removed"

    def remove_program(self) -> str:
        if not self.target.exists():
            return "nothing there"
        left = []
        for item in self.target.iterdir():
            if item.name.lower() in SETUPS_OWN:
                left.append(item.name)
            elif item.is_dir():
                shutil.rmtree(item)
            else:
                item.unlink()
        if not left:
            self.target.rmdir()
            return f"removed {self.target}"
        return f"removed the program from {self.target} (Setup removes its own {', '.join(left)})"

    def remove_data(self) -> str:
        if self.a.purge_data and self.data.exists():
            shutil.rmtree(self.data)
            return f"removed {self.data} (including the master secret); the database is kept"
        return f"kept {self.data}"


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="installers.windows.engine_install", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--names", default="", help="every name and address the PCs will use to reach this Engine, comma-separated (the first goes in the bundle)")
    ap.add_argument("--hostname", default="IT-01", help="the first IT Admin's workstation name (not this machine's)")
    ap.add_argument("--port", type=int, default=7400)
    ap.add_argument("--source", help="the payload folder (default: the one this installer is in)")
    ap.add_argument("--target", help=r"where the program goes (default C:\Program Files\Falcon Engine)")
    ap.add_argument("--data", help=r"where the settings and secrets go (default C:\ProgramData\Falcon Engine)")
    ap.add_argument("--python", help="the Python the runtime is made from (setup.exe passes its own)")
    ap.add_argument("--wheels", help="a folder of wheels, to install with no network")
    ap.add_argument("--admin-url", help="PostgreSQL's superuser URL (prefer --admin-url-file: a command line is visible to others)")
    ap.add_argument("--admin-url-file", help="a file holding PostgreSQL's superuser URL, used once to make the Engine's role")
    ap.add_argument("--database-url", help="use this PostgreSQL URL (a role and database that exist) instead of making them")
    ap.add_argument("--no-database", action="store_true", help="do not touch PostgreSQL")
    ap.add_argument("--db-name", default="falcon")
    ap.add_argument("--db-role", default="falcon")
    ap.add_argument("--service-name", default=SERVICE)
    ap.add_argument("--no-runtime", action="store_true")
    ap.add_argument("--no-setup", action="store_true")
    ap.add_argument("--no-service", action="store_true")
    ap.add_argument("--no-acl", action="store_true", help="leave the data folder's permissions as they are (tests)")
    ap.add_argument("--download-model", action="store_true", help="fetch the local language model (~1.8 GB)")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--purge-data", action="store_true", help="with --uninstall: also remove the data folder (never the database)")
    ap.add_argument("--answers", help="a JSON file of these options (what falcon-engine-setup.exe's pages asked; keeps the password off the command line)")
    ap.add_argument("--dry-run", action="store_true")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    if args.answers:
        answers = json.loads(Path(args.answers).read_text(encoding="utf-8"))
        for key, value in answers.items():
            if value not in (None, "") and hasattr(args, key):
                setattr(args, key, value)
        if answers.get("pg_password") and not (args.admin_url or args.admin_url_file or args.database_url):
            from urllib.parse import quote

            args.admin_url = (f"postgresql://{quote(str(answers.get('pg_user') or 'postgres'), safe='')}:{quote(str(answers['pg_password']), safe='')}"
                              f"@localhost:{int(answers.get('pg_port') or 5432)}/postgres")       # held in memory only; nothing writes it out
    args.port = int(args.port)
    args.download_model = bool(int(args.download_model)) if isinstance(args.download_model, (str, int)) else bool(args.download_model)
    inst = EngineInstall(args)
    try:
        (inst.uninstall_plan() if args.uninstall else inst.plan()).run(dry_run=args.dry_run)
    except InstallError as exc:
        print(f"\nNot finished: {exc}\nFix that and run the installer again: every step checks what is already done.", file=sys.stderr)
        return 1
    if not args.dry_run and not args.uninstall:
        print(inst.summary())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
