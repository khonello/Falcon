"""The Engine's Windows installer (installers/windows/engine_install.py; the user, 14 Nov 2026: deployment is Windows, Linux keeps its .deb).
What it plans, what it writes, and how it reads setup.exe's answers. The whole thing was run for real on the development PC (installers/README.md)."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from installers.windows import engine_install


def _args(tmp_path: Path, *extra: str):
    return engine_install.parser().parse_args(["--target", str(tmp_path / "Program Files" / "Falcon Engine"),
                                               "--data", str(tmp_path / "ProgramData" / "Falcon Engine"), *extra])


def test_the_plan_is_the_eleven_steps_in_order_and_the_uninstall_keeps_the_secret():
    inst = engine_install.EngineInstall(engine_install.parser().parse_args([]), say=lambda m: None)
    steps = [s.name for s in inst.plan().steps]
    assert steps == ["Check", "Stop the old service", "Copy the code", "The runtime", "The data folder", "PostgreSQL", "Settings", "Setup",
                     "The store", "The Engine service", "Receipt"]
    assert inst.pg.bin == inst.target / "pgsql" / "bin" and inst.pg.pgdata == inst.data / "pgdata"     # its own, under the program and the data
    gone = [s.name for s in inst.uninstall_plan().steps]
    assert gone == ["Stop and remove the service", "Stop and remove its PostgreSQL", "Remove the program", "Data"]
    assert inst.remove_data().startswith("kept")                      # without --purge-data the master secret stays


def test_every_setting_is_an_absolute_path_because_a_service_runs_in_system32(tmp_path):
    data = tmp_path / "ProgramData" / "Falcon Engine"
    text = engine_install.env_text(data, "postgresql://falcon:pw@localhost:5432/falcon", 7400)
    paths = {k: v for k, _, v in (ln.partition("=") for ln in text.splitlines() if "=" in ln and not ln.startswith("#"))}
    for key in ("FALCON_TLS_CERT", "FALCON_TLS_KEY", "FALCON_SECRET_PATH", "FALCON_LLM_MODEL_PATH"):
        assert Path(paths[key]).is_absolute() and Path(paths[key]).is_relative_to(data), key
    assert paths["FALCON_ENGINE_HOST"] == "0.0.0.0" and paths["FALCON_ENGINE_PORT"] == "7400" and "FALCON_PG_BIN" not in paths
    own = engine_install.env_text(data, "postgresql://falcon:pw@127.0.0.1:54320/falcon", 7400, tmp_path / "Falcon Engine" / "pgsql" / "bin")
    assert "FALCON_PG_BIN=" + (tmp_path / "Falcon Engine" / "pgsql" / "bin").as_posix() in own.splitlines()   # backups use its own tools


def test_setup_exe_s_answers_reach_the_installer(tmp_path, monkeypatch):
    answers = tmp_path / "answers.json"
    answers.write_text(json.dumps({"names": "falcon.internal,10.0.0.5", "port": "7410", "company_name": "Acme Ltd", "download_model": 1}),
                       encoding="utf-8")
    seen = {}

    class Fake:
        def __init__(self, args, say=print):
            seen["args"] = args

        def plan(self):
            class P:
                def run(self, dry_run=False):
                    return []
            return P()

        def summary(self):
            return ""

    monkeypatch.setattr(engine_install, "EngineInstall", Fake)
    assert engine_install.main(["--answers", str(answers), "--dry-run"]) == 0
    a = seen["args"]
    assert a.names == "falcon.internal,10.0.0.5" and a.port == 7410 and a.download_model is True and a.company_name == "Acme Ltd"
    assert not hasattr(a, "admin_url") and not hasattr(a, "hostname")        # no PostgreSQL password is asked, and no first Admin is made


def test_the_receipt_says_the_payload_s_version(tmp_path):
    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "manifest.json").write_text(json.dumps({"role": "engine", "version": "1.4.2", "files": {}}), encoding="utf-8")
    inst = engine_install.EngineInstall(_args(tmp_path, "--source", str(payload)), say=lambda m: None)
    inst.target.mkdir(parents=True)
    inst.receipt()
    got = json.loads((inst.target / "install.json").read_text(encoding="utf-8"))
    assert got == {"role": "engine", "version": "1.4.2", "service": "FalconEngine", "data": str(inst.data)}


def test_its_postgresql_lets_in_only_the_engine_from_this_machine_on_a_port_of_its_own(tmp_path):
    from installers.windows import private_pg

    final = private_pg.hba_text("falcon", "falcon")
    rules = [ln.split() for ln in final.splitlines() if ln and not ln.startswith("#")]
    assert rules == [["host", "falcon", "falcon", "127.0.0.1/32", "scram-sha-256"], ["host", "falcon", "falcon", "::1/128", "scram-sha-256"]]
    assert "postgres" in private_pg.hba_text("falcon", "falcon", superuser="postgres") and "postgres" not in final
    conf = private_pg.conf_text(54321)
    assert "listen_addresses = 'localhost'" in conf and "port = 54321" in conf
    assert private_pg.free_port() != 5432
    pg = private_pg.PrivatePostgres(bin=tmp_path / "bin", pgdata=tmp_path / "pgdata", secrets_dir=tmp_path)
    (tmp_path / "pgdata").mkdir()
    (tmp_path / "pgdata" / "postgresql.conf").write_text("port = 5432\n" + conf, encoding="utf-8")
    assert pg.port() == 54321 and pg.url("falcon", "falcon", "pw") == "postgresql://falcon:pw@127.0.0.1:54321/falcon"
    (tmp_path / "pgdata" / "PG_VERSION").write_text("18", encoding="utf-8")
    (tmp_path / "pgdata" / "postgresql.conf").write_text("port = 5432\n", encoding="utf-8")
    with pytest.raises(engine_install.InstallError, match="did not set up"):
        pg.init()                                                           # a cluster that is not Falcon's own is left alone


def test_trimming_keeps_what_a_running_engine_needs_and_nothing_else(tmp_path):
    from installers.windows import private_pg

    src = tmp_path / "pgsql"
    for rel in ("bin/postgres.exe", "bin/psql.exe", "bin/pg_dump.exe", "bin/libpq.dll", "bin/stackbuilder.exe", "bin/pgbench.exe",
                "lib/plpgsql.dll", "lib/libpq.lib", "share/timezone/UTC", "include/libpq-fe.h", "pgAdmin 4/x.exe", "doc/a.html"):
        (src / rel).parent.mkdir(parents=True, exist_ok=True)
        (src / rel).write_bytes(b"x")
    private_pg.trim(src, tmp_path / "out")
    got = sorted(p.relative_to(tmp_path / "out").as_posix() for p in (tmp_path / "out").rglob("*") if p.is_file())
    assert got == ["bin/libpq.dll", "bin/pg_dump.exe", "bin/postgres.exe", "bin/psql.exe", "lib/plpgsql.dll", "share/timezone/UTC"]
    with pytest.raises(engine_install.InstallError, match="not PostgreSQL"):
        private_pg.trim(tmp_path / "out" / "share", tmp_path / "again")
