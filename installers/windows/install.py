"""The Windows installers: a person's PC (worker), an Admin's workstation (admin), the Super User's PC (superuser).

    python -m installers.windows.install --role worker --bundle falcon-client.json [--fingerprint AB:CD:..] [--department 3]
    python -m installers.windows.install --role admin  --bundle falcon-client.json [--department 3]
    python -m installers.windows.install --role superuser --bundle falcon-client.json --client-id <id> --client-key-file key.txt
    python -m installers.windows.install --role worker --uninstall [--purge-data]

Run from a payload folder (`python -m installers.payload <role> <folder>`), as an administrator. Each run lists what it does as it goes, checks
what is already there before changing it, and can be run again to repair or upgrade. `--dry-run` lists the steps and changes nothing.

What it does:
  1. checks Windows, administrator rights, the payload (every file against its hash) and the bundle (and its certificate against --fingerprint)
  2. stops an earlier Worker service, if there is one
  3. copies the code into <target>\\app and makes the runtime (<target>\\runtime) with the libraries the payload names
  4. writes what everyone on the machine may read (<data>\\engine.crt, console.json: the Engine's address and certificate, no key) and what only
     the system and administrators may read (<data>\\private\\worker.json: this machine's settings and, once it is registered, its key)
  5. installs the Worker service (starts with Windows, restarts itself) and starts it. With no key of its own it asks the Engine to register
     it: a code appears on the screen, and an Admin or the Super User confirms it. Nothing is typed or copied by hand.
  6. Start-menu shortcut for the console (Admin, Super User). On an Admin's workstation the console is signed in by the service; the Super
     User's own console takes the id and key the Engine's installer printed (`--client-id`, `--client-key-file`), written for the person who ran this
  7. writes a receipt (<target>\\install.json) so the uninstall knows what to remove
"""

from __future__ import annotations

import argparse
import getpass
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

from installers import bundle as bundle_mod
from installers import payload as payload_mod
from installers.common import InstallError, Plan, python_ok, run_cmd, write_text
from installers.roles import Role, role

HERE = Path(__file__).resolve().parent.parent.parent
SYSTEM_SID, ADMINS_SID, USERS_SID = "*S-1-5-18", "*S-1-5-32-544", "*S-1-5-32-545"
DEFAULT_SERVICE = "FalconWorker"


def is_admin() -> bool:
    if sys.platform != "win32":
        return False
    import ctypes

    return bool(ctypes.windll.shell32.IsUserAnAdmin())


def lock_to_system_and_admins(folder: Path) -> None:
    """Only the system account and administrators may read this folder: no inheritance from its parent, no one else listed."""
    run_cmd(["icacls", str(folder), "/inheritance:r", "/grant:r", f"{SYSTEM_SID}:(OI)(CI)F", f"{ADMINS_SID}:(OI)(CI)F"])


def readable_by_everyone(folder: Path) -> None:
    run_cmd(["icacls", str(folder), "/grant", f"{USERS_SID}:(OI)(CI)RX"])


class WindowsInstall:
    def __init__(self, args: argparse.Namespace, say=print) -> None:
        self.a = args
        self.say = say
        self.role: Role = role(args.role)
        self.source = Path(args.source).resolve() if args.source else HERE
        pf = os.environ.get("ProgramFiles", r"C:\Program Files")
        pd = os.environ.get("ProgramData", r"C:\ProgramData")
        self.target = Path(args.target) if args.target else Path(pf) / "Falcon"
        self.data = Path(args.data) if args.data else Path(pd) / "Falcon"
        self.private = self.data / "private"
        self.bundle: bundle_mod.Bundle | None = None
        self.service = args.service_name or DEFAULT_SERVICE

    # --- where things are ----------------------------------------------------------------------------------------

    @property
    def app(self) -> Path:
        return self.target / "app"

    @property
    def runtime_python(self) -> Path:
        return Path(self.a.python) if self.a.reuse_python else self.target / "runtime" / "Scripts" / "python.exe"

    @property
    def worker_json(self) -> Path:
        return self.private / "worker.json"

    @property
    def cert(self) -> Path:
        return self.data / "engine.crt"

    def shortcut(self) -> Path:
        return Path(os.environ.get("ProgramData", r"C:\ProgramData")) / "Microsoft" / "Windows" / "Start Menu" / "Programs" / "Falcon" / "Falcon Console.lnk"

    # --- the plan --------------------------------------------------------------------------------------------------

    def plan(self) -> Plan:
        a, r = self.a, self.role
        p = Plan(f"Falcon installer: {r.title}", say=self.say)
        p.add("Check", self.check, "Windows, administrator, the payload's hashes, the bundle")
        p.add("Stop the old service", self.stop_old, f"{self.service}, if it is there", skip=None if r.service else "this role has no service")
        p.add("Copy the code", self.copy_code, f"{', '.join(r.packages)} into {self.app}")
        p.add("The runtime", self.runtime, f"{self.target / 'runtime'} with the payload's libraries",
              skip="--reuse-python" if a.reuse_python else ("--no-runtime" if a.no_runtime else None))
        p.add("The Engine's address and certificate", self.public_files, f"{self.cert}" + (f" and {self.data / 'console.json'}" if r.console else ""))
        p.add("This machine's settings", self.private_files, f"{self.worker_json}, readable by the system and administrators only",
              skip=None if r.service else "this role has no service")
        p.add("The Worker service", self.install_service, f"{self.service}: starts with Windows, restarts itself",
              skip=None if r.service and not a.no_service else ("--no-service" if r.service else "this role has no service"))
        p.add("The console", self.console, "Start-menu shortcut" + ("; the Super User's id and key for the person installing" if r.name == "superuser" else ""),
              skip=None if r.console else "this role has no console")
        p.add("Become the Super User's machine", self.handover, "ask the Engine, show a code; the current Super User confirms it (opened with `handover open`)",
              skip=None if a.handover else "--handover not given")
        p.add("Receipt", self.receipt, f"{self.target / 'install.json'}")
        return p

    # --- the steps -------------------------------------------------------------------------------------------------

    def check(self) -> str:
        if sys.platform != "win32":
            raise InstallError("this installer is for Windows; the Engine's is installers.engine.install")
        if not is_admin() and not self.a.no_acl:
            raise InstallError("run this as an administrator: it installs a service and sets who may read what")
        if (why := python_ok()):
            raise InstallError(why)
        if (self.source / "manifest.json").exists():
            problems = payload_mod.verify(self.source)
            if problems:
                raise InstallError("the payload is not intact: " + "; ".join(problems[:5]))
            manifest = json.loads((self.source / "manifest.json").read_text(encoding="utf-8"))
            if manifest["role"] != self.role.name:
                raise InstallError(f"this payload is for the {manifest['role']!r} role, not {self.role.name!r}")
        if not self.a.bundle:
            raise InstallError("--bundle falcon-client.json is needed: the Engine's installer writes it, and every PC is given the same one")
        self.bundle = bundle_mod.load(Path(self.a.bundle), self.a.fingerprint)
        who = f"certificate {self.bundle.ca_sha256}" + ("" if self.a.fingerprint else " (compare it with the one the Engine's installer printed)")
        return f"ready: the Engine is {self.bundle.engine_host}:{self.bundle.engine_port}, {who}"

    def stop_old(self) -> str:
        if not self.runtime_python.exists() or not self.app.exists():
            return "nothing installed yet"
        rc, _ = run_cmd([str(self.runtime_python), "-m", "worker_client", "service", "stop", "--name", self.service], check=False,
                          cwd=self.app)
        return "stopped" if rc == 0 else "was not running"

    def copy_code(self) -> str:
        src = self.source / "app" if (self.source / "app").is_dir() else self.source
        for pkg in self.role.packages:
            if not (src / pkg).is_dir():
                raise InstallError(f"{src / pkg} is missing from the payload")
            if (self.app / pkg).exists():
                shutil.rmtree(self.app / pkg)                    # no file of an older version is left behind
            shutil.copytree(src / pkg, self.app / pkg, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "tests"))
        for name in ("requirements.txt", "pyproject.toml"):
            for where in (self.source, src):
                if (where / name).is_file():
                    shutil.copy2(where / name, self.app / name)
                    break
        return f"{len(self.role.packages)} packages in {self.app}"

    def runtime(self) -> str:
        venv = self.target / "runtime"
        if not self.runtime_python.exists():
            run_cmd([self.a.python or sys.executable, "-m", "venv", str(venv)])
        site = venv / "Lib" / "site-packages"
        write_text(site / "falcon.pth", str(self.app) + "\n")      # the runtime finds the code without it being installed as a library
        req = self.app / "requirements.txt"
        if not req.exists():
            req.write_text(payload_mod.requirements_for(self.role.name, self.source), encoding="utf-8")
        cmd = [str(self.runtime_python), "-m", "pip", "install", "--disable-pip-version-check", "-r", str(req)]
        wheels = self.a.wheels or (str(self.source / "wheels") if (self.source / "wheels").is_dir() else None)
        if wheels:
            cmd[4:4] = ["--no-index", "--find-links", wheels]
        run_cmd(cmd)
        return f"libraries installed in {venv}" + (" from the payload's wheels (no network used)" if wheels else "")

    def public_files(self) -> str:
        assert self.bundle is not None
        self.data.mkdir(parents=True, exist_ok=True)
        changed = write_text(self.cert, self.bundle.ca_pem)
        if self.role.console:
            console = {"engine_host": self.bundle.engine_host, "engine_port": self.bundle.engine_port, "tls": True, "ca_cert": str(self.cert)}
            if self.role.serve_console:
                console["signer"] = "pipe"                      # no key for the person to hold: the service on this machine answers for it
            write_text(self.data / "console.json", json.dumps(console, indent=2))
        if not self.a.no_acl:
            readable_by_everyone(self.data)
        return ("written " if changed else "kept ") + str(self.cert) + (" (anyone on this machine may read it: it is public)" if not self.a.no_acl else "")

    def private_files(self) -> str:
        assert self.bundle is not None
        self.private.mkdir(parents=True, exist_ok=True)
        if not self.a.no_acl:
            lock_to_system_and_admins(self.private)
        cfg: dict = {}
        if self.worker_json.exists():
            try:
                cfg = json.loads(self.worker_json.read_text(encoding="utf-8"))
            except ValueError:
                cfg = {}
        kept_key = bool(cfg.get("client_id") and cfg.get("client_key"))
        cfg.update({"engine_host": self.bundle.engine_host, "engine_port": self.bundle.engine_port, "tls": True, "ca_cert": str(self.cert),
                    "separate_programs": True, "windows": not self.a.no_windows, "serve_console": self.role.serve_console,
                    "enroll_level": self.role.enroll_level or "worker", "enroll_department": self.a.department,
                    "watch_roots": cfg.get("watch_roots") or self.a.watch or [r"C:\Users"]})
        cfg.setdefault("client_id", "")
        cfg.setdefault("client_key", "")
        self.worker_json.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        return ("settings updated; this machine keeps the key it already has" if kept_key
                else "settings written; this machine has no key yet: it will ask the Engine to register it when the service starts")

    def install_service(self) -> str:
        cfg = ["--name", self.service, "--config", str(self.worker_json)]
        base = [str(self.runtime_python), "-m", "worker_client", "service"]
        _, out = run_cmd(base + ["install"] + cfg, cwd=self.app)
        said = out.strip().splitlines()[-1] if out.strip() else "installed"
        if self.a.no_start:
            return said + "; not started (--no-start)"
        run_cmd(base + ["start", "--name", self.service], cwd=self.app)
        return said + "; started"

    def console(self) -> str:
        lnk = self.shortcut()
        if not self.a.no_shortcuts:
            lnk.parent.mkdir(parents=True, exist_ok=True)
            pythonw = self.runtime_python.with_name("pythonw.exe")
            ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut($args[0]);$s.TargetPath=$args[1];$s.Arguments='-m operator_client --gui';"
                  "$s.WorkingDirectory=$args[2];$s.Description='Falcon console';$s.Save()")
            run_cmd(["powershell", "-NoProfile", "-Command", ps, str(lnk), str(pythonw if pythonw.exists() else self.runtime_python), str(self.app)])
        said = [f"shortcut {lnk}" if not self.a.no_shortcuts else "no shortcut (--no-shortcuts)"]
        if self.role.name == "superuser":
            said.append(self._super_user_settings())
        elif self.role.serve_console:
            said.append("signed in by this machine's service once it is registered")
        return "; ".join(said)

    def _super_user_settings(self) -> str:
        """The Super User's console needs the id and key the Engine's installer printed. They go into the settings of the person running this."""
        assert self.bundle is not None
        if self.a.handover:
            return self._write_super_user_settings("", "", "this machine will ask to become the Super User's (next step)")
        if not self.a.client_id:
            return "no --client-id given: put the Super User's id and key in the console's settings yourself (the Engine's installer printed them)"
        key = self.a.client_key or (Path(self.a.client_key_file).read_text(encoding="utf-8").strip() if self.a.client_key_file else "")
        if not key and sys.stdin.isatty():
            key = getpass.getpass("The Super User's client key (typed here, not shown): ").strip()
        if not key:
            raise InstallError("--client-id needs the key: --client-key-file <file> (or type it when asked)")
        return self._write_super_user_settings(self.a.client_id, key, "")

    def _write_super_user_settings(self, client_id: str, key: str, note: str) -> str:
        assert self.bundle is not None
        path = self.operator_json()
        path.parent.mkdir(parents=True, exist_ok=True)
        cfg = {"engine_host": self.bundle.engine_host, "engine_port": self.bundle.engine_port, "client_id": client_id, "client_key": key,
               "tls": True, "ca_cert": str(self.cert), "prefs": {}, "cache": {}}
        path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        return f"the Super User's settings are in {path} (readable by this person only)" + (f"; {note}" if note else "")

    def operator_json(self) -> Path:
        return Path(os.environ.get("APPDATA") or Path.home() / "AppData" / "Roaming") / "Falcon" / "operator.json"

    def handover(self) -> str:
        """Ask the Engine to make this machine the Super User's. The code is shown here, in this window, and the person at the CURRENT Super User
        console types it there. Nothing is moved until they do."""
        argv = [str(self.runtime_python), "-m", "operator_client", "--handover-join", "--config", str(self.operator_json())]
        proc = subprocess.run(argv, cwd=str(self.app), check=False)             # not captured: the person has to read the code
        if proc.returncode != 0:
            raise InstallError("the handover was not confirmed. On the current Super User's console type `handover open`, then run this installer again.")
        return "this machine is now the Super User's console"

    def receipt(self) -> str:
        path = self.target / "install.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps({"role": self.role.name, "version": payload_mod.project_version(self.source if (self.source / "pyproject.toml").exists() else HERE),
                                    "service": self.service if self.role.service else None, "data": str(self.data),
                                    "shortcut": str(self.shortcut()) if self.role.console and not self.a.no_shortcuts else None}, indent=2),
                        encoding="utf-8")
        return str(path)

    # --- taking it out ----------------------------------------------------------------------------------------------

    def uninstall_plan(self) -> Plan:
        p = Plan(f"Falcon uninstall ({self.role.title})", say=self.say)
        p.add("Stop and remove the service", self.remove_service, self.service)
        p.add("Remove the shortcut", self.remove_shortcut, str(self.shortcut()))
        p.add("Remove the program", self.remove_program, str(self.target))
        p.add("Settings and key", self.remove_data, "kept unless --purge-data: without its key this machine must be registered again")
        return p

    def remove_service(self) -> str:
        if not self.runtime_python.exists() or not self.app.exists():
            return "no service to remove"
        base = [str(self.runtime_python), "-m", "worker_client", "service"]
        run_cmd(base + ["stop", "--name", self.service], check=False, cwd=self.app)
        rc, out = run_cmd(base + ["uninstall", "--name", self.service], check=False, cwd=self.app)
        return out.strip().splitlines()[-1] if out.strip() else ("removed" if rc == 0 else "was not installed")

    def remove_shortcut(self) -> str:
        lnk = self.shortcut()
        if lnk.exists():
            lnk.unlink()
            try:
                lnk.parent.rmdir()
            except OSError:
                pass
            return "removed"
        return "none"

    def remove_program(self) -> str:
        if self.target.exists():
            shutil.rmtree(self.target)
            return f"removed {self.target}"
        return "nothing there"

    def remove_data(self) -> str:
        if self.a.purge_data and self.data.exists():
            shutil.rmtree(self.data)
            return f"removed {self.data} (including this machine's key)"
        return f"kept {self.data}"


def parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="installers.windows.install", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--role", required=True, choices=("worker", "admin", "superuser"))
    ap.add_argument("--bundle", help="falcon-client.json from the Engine's installer")
    ap.add_argument("--fingerprint", help="the certificate's fingerprint the Engine's installer printed: refuse any other")
    ap.add_argument("--department", type=int, help="the department this machine asks to join (otherwise the person confirming chooses)")
    ap.add_argument("--handover", action="store_true",
                    help="superuser: this is the Super User's NEW machine; no id or key is given, it asks the Engine and the current Super User confirms with the code shown")
    ap.add_argument("--client-id", help="superuser: the Super User's client id")
    ap.add_argument("--client-key", help="superuser: the key (prefer --client-key-file: a command line is remembered)")
    ap.add_argument("--client-key-file", help="superuser: a file holding the key")
    ap.add_argument("--watch", action="append", help=r"a folder to watch (repeatable; default C:\Users)")
    ap.add_argument("--source", help="the payload folder (default: the one this installer is in)")
    ap.add_argument("--target", help=r"where the program goes (default C:\Program Files\Falcon)")
    ap.add_argument("--data", help=r"settings and the certificate (default C:\ProgramData\Falcon)")
    ap.add_argument("--python", help="the Python the runtime is made from (default: this one)")
    ap.add_argument("--wheels", help="a folder of wheels, to install with no network")
    ap.add_argument("--service-name", help=f"default {DEFAULT_SERVICE}")
    ap.add_argument("--no-runtime", action="store_true", help="do not make the runtime (the libraries are already there)")
    ap.add_argument("--reuse-python", action="store_true", help="run from --python itself instead of making a runtime (testing)")
    ap.add_argument("--no-service", action="store_true")
    ap.add_argument("--no-start", action="store_true", help="install the service but do not start it")
    ap.add_argument("--no-acl", action="store_true", help="do not set who may read what (testing)")
    ap.add_argument("--no-shortcuts", action="store_true")
    ap.add_argument("--no-windows", action="store_true", help="the Worker shows no windows (a server, or testing)")
    ap.add_argument("--uninstall", action="store_true")
    ap.add_argument("--purge-data", action="store_true", help="with --uninstall: also remove the settings and this machine's key")
    ap.add_argument("--dry-run", action="store_true", help="list the steps and change nothing")
    return ap


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    inst = WindowsInstall(args)
    try:
        (inst.uninstall_plan() if args.uninstall else inst.plan()).run(dry_run=args.dry_run)
    except InstallError as exc:
        print(f"\nNot finished: {exc}\nFix that and run the installer again: every step checks what is already done.", file=sys.stderr)
        return 1
    if not args.dry_run and not args.uninstall and inst.role.service:
        print("\nInstalled. This machine now asks the Engine to register it: a code appears on its screen; give it to an Admin"
              + (" (the Super User, for an Admin's workstation)" if inst.role.name == "admin" else "") + " to confirm.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
