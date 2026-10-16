"""The installers' code: what each carries, that it is intact, and the steps that put it on a machine.

Nothing here is compiled into an executable; this is the code behind the four installers (installers/README.md). The Windows route is run
for real into temporary folders, and, from an elevated prompt, as an installed service that registers itself with an Engine.
"""

from __future__ import annotations

import asyncio
import json
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

from installers import bundle as bundle_mod
from installers import payload as payload_mod
from installers.common import InstallError, cert_fingerprint
from installers.engine import install as engine_install
from installers.engine import render
from installers.roles import FORBIDDEN_NAMES, ROLES
from installers.windows import install as win_install
from tests.conftest import requires_db

windows_only = pytest.mark.skipif(sys.platform != "win32", reason="the Windows installers")


def make_cert(folder: Path, names: str = "falcon.internal,127.0.0.1") -> str:
    from engine.tls import generate_self_signed

    cert, _key = generate_self_signed(names, folder)
    return cert.read_text(encoding="utf-8")


def built(role: str, tmp_path: Path) -> Path:
    out = tmp_path / f"payload-{role}"
    payload_mod.build(role, out)
    return out


def files_of(folder: Path) -> set[str]:
    return {str(p.relative_to(folder)).replace("\\", "/") for p in folder.rglob("*") if p.is_file()}


# --- what each installer carries -------------------------------------------------------------------------------

def test_each_role_carries_its_packages_and_nothing_else(tmp_path):
    worker, admin, su, eng = (files_of(built(r, tmp_path)) for r in ("worker", "admin", "superuser", "engine"))
    has = lambda files, pkg: any(f.startswith(f"app/{pkg}/") for f in files)
    assert has(worker, "worker_client") and has(worker, "common") and has(worker, "protocol")
    assert not has(worker, "operator_client") and not has(worker, "engine")                    # a person's PC has no console, no Engine
    assert has(admin, "worker_client") and has(admin, "operator_client") and not has(admin, "engine")
    assert has(su, "operator_client") and not has(su, "worker_client") and not has(su, "engine")
    assert has(eng, "engine") and not has(eng, "worker_client") and not has(eng, "operator_client")
    assert "app/engine/migrations/030_component_issues.sql" in eng                           # the schema goes with the Engine
    assert "app/worker_client/windows/qml/Window.qml" in worker                               # and the overlays' pictures with the Worker
    for files in (worker, admin, su, eng):
        assert "manifest.json" in files and "requirements.txt" in files and "installers/windows/install.py" in files


def test_no_payload_ever_carries_a_secret_a_test_or_a_cache(tmp_path):
    for r in ROLES:
        files = files_of(built(r, tmp_path))
        bad = [f for f in files if Path(f).name in FORBIDDEN_NAMES or f.endswith((".key", ".pem", ".pyc", ".log"))
               or "/tests/" in f or "__pycache__" in f or f.startswith(("data/", "models/")) or "/.env" in f]
        assert bad == [], f"{r} carries {bad}"


def test_the_libraries_each_role_needs_come_from_pyproject(tmp_path):
    worker = payload_mod.requirements_for("worker")
    assert "psutil" in worker and "watchdog" in worker and "PySide6-Essentials" in worker
    assert "asyncpg" not in worker and "-e " not in worker                                    # no database driver on a PC, no editable install
    eng = payload_mod.requirements_for("engine")
    assert "asyncpg" in eng and "cryptography" in eng and "--extra-index-url" in eng
    su = payload_mod.requirements_for("superuser")
    assert "qasync" in su and "psutil" not in su


def test_a_payload_that_was_changed_or_half_copied_is_refused(tmp_path):
    p = built("worker", tmp_path)
    assert payload_mod.verify(p) == []
    target = p / "app" / "worker_client" / "service.py"
    target.write_text(target.read_text(encoding="utf-8") + "\n# tampered\n", encoding="utf-8")
    (p / "app" / "worker_client" / "etw.py").unlink()
    (p / "app" / "worker_client" / "extra.py").write_text("x = 1\n", encoding="utf-8")
    problems = payload_mod.verify(p)
    assert "changed: app/worker_client/service.py" in problems and "missing: app/worker_client/etw.py" in problems
    assert "not in the manifest: app/worker_client/extra.py" in problems
    cache = p / "installers" / "__pycache__"
    cache.mkdir()
    (cache / "x.cpython-312.pyc").write_bytes(b"x")                                             # what running the installer from here leaves behind
    assert not any("__pycache__" in x for x in payload_mod.verify(p))
    assert payload_mod.verify(tmp_path / "nowhere") == ["manifest.json is missing or unreadable"]


def test_a_payload_is_built_into_a_fresh_folder_only(tmp_path):
    p = built("superuser", tmp_path)
    with pytest.raises(InstallError):
        payload_mod.build("superuser", p)


# --- the bundle: the Engine's address and certificate, no key ---------------------------------------------------

def test_the_bundle_holds_the_address_and_the_certificate_and_no_key(tmp_path):
    pem = make_cert(tmp_path)
    b = bundle_mod.Bundle.make("falcon.internal", 7400, pem)
    b.save(tmp_path / "falcon-client.json")
    raw = (tmp_path / "falcon-client.json").read_text(encoding="utf-8")
    assert "PRIVATE KEY" not in raw and "client_key" not in raw and "client_id" not in raw
    loaded = bundle_mod.load(tmp_path / "falcon-client.json")
    assert (loaded.engine_host, loaded.engine_port, loaded.ca_sha256) == ("falcon.internal", 7400, cert_fingerprint(pem))
    # the person reads the fingerprint out loud, in whatever form
    assert bundle_mod.load(tmp_path / "falcon-client.json", fingerprint=loaded.ca_sha256.lower().replace(":", " ")).engine_host == "falcon.internal"


def test_a_bundle_that_was_swapped_or_is_not_the_engine_expected_is_refused(tmp_path):
    pem = make_cert(tmp_path / "a")
    other = make_cert(tmp_path / "b")
    path = tmp_path / "falcon-client.json"
    bundle_mod.Bundle.make("falcon.internal", 7400, pem).save(path)
    with pytest.raises(InstallError, match="not the Engine you expected"):
        bundle_mod.load(path, fingerprint=cert_fingerprint(other))
    data = json.loads(path.read_text(encoding="utf-8"))
    data["ca_pem"] = other                                                                   # the certificate swapped, the fingerprint left
    path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(InstallError, match="was changed"):
        bundle_mod.load(path)
    path.write_text(json.dumps({"engine_host": "x"}), encoding="utf-8")
    with pytest.raises(InstallError, match="not a Falcon client bundle"):
        bundle_mod.load(path)


# --- the Engine's installer (Linux; the steps' text and their checks run anywhere) ---------------------------------

def test_the_engine_settings_name_server_paths_and_no_development_switch():
    layout = render.Layout()
    text = render.env_file(layout, "postgresql://falcon:s3cret@localhost:5432/falcon", 7400)
    for want in ("FALCON_ENGINE_HOST=0.0.0.0", "FALCON_ENGINE_PORT=7400", "FALCON_TLS_CERT=", "FALCON_SECRET_PATH=", "FALCON_DATABASE_URL=postgresql://falcon:s3cret@"):
        assert want in text
    assert "DEV_PLAINTEXT" not in text and "DEV_BYPASS_AUTH" not in text and "falcon_test" not in text
    assert all(line.split("=", 1)[1].startswith("/") for line in text.splitlines() if line.startswith(("FALCON_TLS", "FALCON_SECRET")))


def test_the_service_unit_runs_as_the_falcon_user_with_only_what_it_needs():
    unit = render.systemd_unit(render.Layout())
    for want in ("User=falcon", "ExecStart=/opt/falcon/venv/bin/python -m engine", "EnvironmentFile=/etc/falcon/falcon.env", "Restart=on-failure",
                 "NoNewPrivileges=true", "ProtectSystem=strict", "ReadWritePaths=/var/lib/falcon /var/log/falcon", "WantedBy=multi-user.target"):
        assert want in unit, want


def test_the_database_statements_can_be_run_again_without_changing_a_password():
    first, second = render.postgres_role_sql("pw123")
    assert "IF NOT EXISTS" in first and "CREATE ROLE falcon LOGIN PASSWORD 'pw123'" in first and "ALTER ROLE falcon" in first
    assert "WHERE NOT EXISTS" in second and second.endswith("\\gexec")


def test_the_engine_installer_lists_its_steps_and_a_dry_run_touches_nothing(tmp_path, capsys):
    argv = ["--names", "falcon.internal", "--prefix", str(tmp_path / "opt"), "--state", str(tmp_path / "var"), "--etc", str(tmp_path / "etc"),
            "--log", str(tmp_path / "log"), "--dry-run"]
    assert engine_install.main(argv) == 0
    out = capsys.readouterr().out
    steps = re.findall(r"\[\d+/(\d+)\] ([^:]+):", out)
    assert [s for _, s in steps] == ["Check the machine", "The falcon user and folders", "Copy the code", "The runtime", "PostgreSQL", "Settings",
                                     "Setup", "Ownership", "Client bundle", "Service"]
    assert not any((tmp_path / d).exists() for d in ("opt", "var", "etc", "log"))


def test_the_engine_installer_refuses_a_machine_it_cannot_install_on(tmp_path, monkeypatch):
    args = engine_install.parser().parse_args(["--prefix", str(tmp_path)])
    inst = engine_install.EngineInstall(args, render.Layout(prefix=tmp_path), say=lambda m: None)
    monkeypatch.setattr(sys, "platform", "win32")
    with pytest.raises(InstallError, match="Linux"):
        inst.check()
    monkeypatch.setattr(sys, "platform", "linux")
    if hasattr(os, "geteuid"):
        monkeypatch.setattr(os, "geteuid", lambda: 1000, raising=False)
    else:
        monkeypatch.setattr(os, "geteuid", lambda: 1000, raising=False)
    with pytest.raises(InstallError, match="as root"):
        inst.check()


def test_the_engine_installer_copies_the_engine_and_writes_settings_and_the_bundle(tmp_path):
    layout = render.Layout(prefix=tmp_path / "opt", state=tmp_path / "var", etc=tmp_path / "etc", log=tmp_path / "log")
    args = engine_install.parser().parse_args(["--names", "falcon.internal,10.0.0.5", "--source", str(built("engine", tmp_path)),
                                               "--database-url", "postgresql://falcon:pw@localhost/falcon"])
    inst = engine_install.EngineInstall(args, layout, say=lambda m: None)
    assert "engine" in inst.copy_code()
    assert (layout.app / "engine" / "server.py").is_file() and (layout.app / "common").is_dir() and (layout.app / "protocol").is_dir()
    assert not (layout.app / "worker_client").exists()
    layout.etc.mkdir(parents=True)
    assert inst.settings().startswith("written")
    assert "FALCON_DATABASE_URL=postgresql://falcon:pw@localhost/falcon" in layout.env_file.read_text(encoding="utf-8")
    assert inst.settings().startswith("kept")                                                 # run again: nothing is rewritten
    layout.state.mkdir(parents=True)
    (layout.state / "engine.crt").write_text(make_cert(tmp_path / "c", "falcon.internal"), encoding="utf-8")
    said = inst.client_bundle()
    b = bundle_mod.load(layout.bundle)
    assert b.engine_host == "falcon.internal" and b.engine_port == 7400 and b.ca_sha256 in said


# --- the Windows installers ---------------------------------------------------------------------------------------

def win_args(role: str, tmp_path: Path, *extra: str) -> tuple[win_install.WindowsInstall, Path]:
    payload = built(role, tmp_path)
    cert_dir = tmp_path / "certs"
    bundle_path = tmp_path / "falcon-client.json"
    bundle_mod.Bundle.make("falcon.internal", 7400, make_cert(cert_dir)).save(bundle_path)
    argv = ["--role", role, "--bundle", str(bundle_path), "--source", str(payload), "--target", str(tmp_path / "Program Files" / "Falcon"),
            "--data", str(tmp_path / "ProgramData" / "Falcon"), "--python", sys.executable, "--reuse-python", "--no-acl", "--no-shortcuts",
            "--no-service", "--no-windows", *extra]
    return win_install.WindowsInstall(win_install.parser().parse_args(argv), say=lambda m: None), bundle_path


@windows_only
def test_a_worker_install_puts_the_code_the_address_and_the_machines_settings_in_place(tmp_path):
    inst, _ = win_args("worker", tmp_path, "--department", "3")
    done = dict(inst.plan().run())
    assert "ready" in done["Check"] and done["Stop the old service"] == "nothing installed yet" or done["Stop the old service"].startswith("skipped")
    assert (inst.app / "worker_client" / "service.py").is_file() and not (inst.app / "operator_client").exists()
    cfg = json.loads(inst.worker_json.read_text(encoding="utf-8"))
    assert (cfg["engine_host"], cfg["engine_port"], cfg["tls"], cfg["enroll_level"], cfg["enroll_department"]) == ("falcon.internal", 7400, True, "worker", 3)
    assert cfg["separate_programs"] is True and cfg["serve_console"] is False and cfg["client_id"] == "" and cfg["client_key"] == ""
    assert cfg["ca_cert"] == str(inst.cert) and inst.cert.read_text(encoding="utf-8").startswith("-----BEGIN CERTIFICATE")
    assert not (inst.data / "console.json").exists()                                           # a person's PC has no console
    assert json.loads((inst.target / "install.json").read_text(encoding="utf-8"))["role"] == "worker"


@windows_only
def test_an_admin_workstation_asks_to_be_an_admin_and_its_console_is_signed_in_by_its_service(tmp_path):
    inst, _ = win_args("admin", tmp_path)
    inst.plan().run()
    cfg = json.loads(inst.worker_json.read_text(encoding="utf-8"))
    assert cfg["enroll_level"] == "admin" and cfg["serve_console"] is True
    console = json.loads((inst.data / "console.json").read_text(encoding="utf-8"))
    assert console["signer"] == "pipe" and console["engine_host"] == "falcon.internal" and "client_key" not in console
    assert (inst.app / "operator_client").is_dir() and (inst.app / "worker_client").is_dir()


@windows_only
def test_the_super_users_console_gets_its_id_and_key_for_the_person_installing_and_no_service(tmp_path, monkeypatch):
    monkeypatch.setenv("APPDATA", str(tmp_path / "Roaming"))
    key = tmp_path / "key.txt"
    key.write_text("ab" * 32 + "\n", encoding="utf-8")
    inst, _ = win_args("superuser", tmp_path, "--client-id", "su-1", "--client-key-file", str(key))
    done = dict(inst.plan().run())
    assert done["The Worker service"].startswith("skipped") and done["This machine's settings"].startswith("skipped")
    mine = json.loads((tmp_path / "Roaming" / "Falcon" / "operator.json").read_text(encoding="utf-8"))
    assert (mine["client_id"], mine["client_key"], mine["engine_host"], mine["tls"]) == ("su-1", "ab" * 32, "falcon.internal", True)
    assert "client_key" not in json.loads((inst.data / "console.json").read_text(encoding="utf-8"))       # the key is not for everyone on the machine
    assert not inst.worker_json.exists() and not (inst.app / "worker_client").exists()


@windows_only
def test_installing_again_keeps_the_key_a_machine_was_given(tmp_path):
    inst, _ = win_args("worker", tmp_path)
    inst.plan().run()
    cfg = json.loads(inst.worker_json.read_text(encoding="utf-8"))
    cfg.update(client_id="cid-7", client_key="cd" * 32)                                        # registered, in between
    inst.worker_json.write_text(json.dumps(cfg), encoding="utf-8")
    (inst.app / "worker_client" / "stale.py").write_text("old = True\n", encoding="utf-8")
    done = dict(inst.plan().run())
    again = json.loads(inst.worker_json.read_text(encoding="utf-8"))
    assert (again["client_id"], again["client_key"]) == ("cid-7", "cd" * 32) and "keeps the key" in done["This machine's settings"]
    assert not (inst.app / "worker_client" / "stale.py").exists()                              # the upgrade leaves no old file behind


@windows_only
def test_a_wrong_payload_a_changed_payload_and_a_wrong_engine_are_each_refused(tmp_path):
    inst, _ = win_args("worker", tmp_path)
    inst.source = built("superuser", tmp_path / "other")                                       # a payload for another role
    with pytest.raises(InstallError, match="not 'worker'"):
        inst.check()
    inst2, _ = win_args("worker", tmp_path / "second")
    (inst2.source / "app" / "worker_client" / "service.py").write_text("# changed\n", encoding="utf-8")
    with pytest.raises(InstallError, match="not intact"):
        inst2.check()
    inst3, _ = win_args("worker", tmp_path / "third", "--fingerprint", cert_fingerprint(make_cert(tmp_path / "elsewhere")))
    with pytest.raises(InstallError, match="not the Engine you expected"):
        inst3.check()
    inst4, _ = win_args("worker", tmp_path / "fourth")
    inst4.a.bundle = None
    with pytest.raises(InstallError, match="--bundle"):
        inst4.check()


@windows_only
def test_uninstalling_takes_the_program_away_and_keeps_the_machines_key_unless_asked(tmp_path):
    inst, _ = win_args("worker", tmp_path)
    inst.plan().run()
    inst.uninstall_plan().run()
    assert not inst.target.exists() and inst.worker_json.exists()                              # the key stays: re-installing needs no new registration
    inst.a.purge_data = True
    inst.uninstall_plan().run()
    assert not inst.data.exists()


@windows_only
def test_the_windows_installer_lists_its_steps_and_a_dry_run_touches_nothing(tmp_path, capsys):
    inst, _ = win_args("admin", tmp_path)
    inst.plan().run(dry_run=True)
    out = capsys.readouterr().out
    assert out == ""                                                                             # say=lambda: nothing printed; the listing is in the returned steps
    assert not inst.target.exists() and not inst.data.exists()


@windows_only
def test_the_command_line_installs_and_says_what_is_left_to_do(tmp_path, monkeypatch, capsys):
    payload = built("worker", tmp_path)
    bundle_path = tmp_path / "falcon-client.json"
    bundle_mod.Bundle.make("falcon.internal", 7400, make_cert(tmp_path / "c")).save(bundle_path)
    argv = ["--role", "worker", "--bundle", str(bundle_path), "--source", str(payload), "--target", str(tmp_path / "pf"), "--data", str(tmp_path / "pd"),
            "--python", sys.executable, "--reuse-python", "--no-acl", "--no-service", "--no-windows"]
    assert win_install.main(argv) == 0
    out = capsys.readouterr().out
    assert "[1/10] Check" in out and "this machine has no key yet" in out
    assert win_install.main([*argv[:2], "--role", "worker", "--bundle", str(tmp_path / "missing.json"), *argv[4:]]) == 1


# --- for real: the installed service registers itself with an Engine (elevated prompt only) --------------------------

@windows_only
@requires_db
async def test_an_installed_admin_workstation_registers_itself_and_its_console_is_signed_in_by_its_service(engine, org, connect, tmp_path):
    """The whole route: the installer lays an Admin workstation down and installs its service; Windows starts it as the system account; with no key
    it asks the Engine, the Super User confirms with the code it logs, it is handed its key (kept where only the system and administrators can read
    it) and comes online; and a console on the machine, with no key, is signed in by the service through the pipe. Removed afterwards."""
    if not win_install.is_admin():
        pytest.skip("needs an elevated prompt")
    from common import signpipe
    from common.connection import EngineConnection
    from worker_client import winservice

    name = "FalconWorkerTestInstall"
    inst, _ = win_args("admin", tmp_path, "--service-name", name)
    inst.a.no_service = False
    inst.a.no_acl = False
    inst.a.no_start = True
    su = await connect("cid-su")
    try:
        inst.plan().run()
        cfg = json.loads(inst.worker_json.read_text(encoding="utf-8"))
        cfg.update(engine_host="127.0.0.1", engine_port=engine.port, tls=False, ca_cert=None)    # this Engine speaks plaintext (tests); TLS is test_auth's
        inst.worker_json.write_text(json.dumps(cfg), encoding="utf-8")
        acl = (await asyncio.to_thread(subprocess.run, ["icacls", str(inst.private)], capture_output=True, text=True, check=False)).stdout
        assert r"BUILTIN\Users" not in acl and "Everyone" not in acl and r"NT AUTHORITY\SYSTEM" in acl and r"BUILTIN\Administrators" in acl   # closed to people
        assert winservice.start(name).endswith("running")

        log = inst.private / "worker.log"
        code = None
        for _ in range(150):
            if log.exists():
                found = re.findall(r"Code ((?:\d ?){4})", log.read_text(encoding="utf-8", errors="replace"))
                if found:
                    code = found[-1].replace(" ", "")
                    break
            await asyncio.sleep(0.2)
        assert code and len(code) == 4, "the service did not ask to be registered"
        waiting = (await su.ok("enroll.list"))["requests"]
        assert len(waiting) == 1 and waiting[0]["requested_level"] == "admin"
        await su.ok("enroll.confirm", {"enrollment_id": waiting[0]["id"], "code": code, "department_id": org["fin"]})

        for _ in range(150):
            saved = json.loads(inst.worker_json.read_text(encoding="utf-8"))
            if saved.get("client_id") and saved.get("client_key"):
                break
            await asyncio.sleep(0.2)
        assert saved["client_id"] and saved["client_key"]                                       # handed once, kept in the private folder
        pc_id = (await engine.db.pool.fetchrow("SELECT id FROM pcs WHERE client_id = $1", saved["client_id"]))["id"]
        for _ in range(150):
            if pc_id in engine.online_pc_ids():
                break
            await asyncio.sleep(0.2)
        assert pc_id in engine.online_pc_ids()                                                  # the registered machine is online

        # the console on this machine holds no key and is signed in by the service
        for _ in range(100):
            if signpipe.available():
                break
            await asyncio.sleep(0.1)
        assert signpipe.whoami() == saved["client_id"]
        console = EngineConnection("127.0.0.1", engine.port, client_id=saved["client_id"], tls=False, derived_key=None, signer=signpipe.sign)
        ident = await console.connect()
        assert ident.role == "admin" and ident.department_id == org["fin"]
        await console.close()
    finally:
        winservice.stop(name)
        winservice.uninstall(name)


def test_a_new_super_user_machine_is_installed_without_an_id_and_asks_to_take_over(tmp_path, capsys):
    """`--handover`: no client id or key is given; the plan has a step that asks the Engine, and without the flag that step is skipped."""
    for flags, shown in (([], False), (["--handover"], True)):
        assert win_install.main(["--role", "superuser", "--bundle", str(tmp_path / "b.json"), "--target", str(tmp_path / "pf"), "--data", str(tmp_path / "pd"),
                                 "--dry-run", *flags]) == 0
        out = capsys.readouterr().out
        step = next(line for line in out.splitlines() if "Become the Super User's machine" in line)
        assert ("--handover not given" in step) is (not shown)
