"""The Engine's Windows installer (installers/windows/engine_install.py; the user, 14 Nov 2026: deployment is Windows, Linux keeps its .deb).
What it plans, what it writes, and how it reads setup.exe's answers. The whole thing was run for real on the development PC (installers/README.md)."""

from __future__ import annotations

import json
from pathlib import Path

from installers.windows import engine_install


def _args(tmp_path: Path, *extra: str):
    return engine_install.parser().parse_args(["--target", str(tmp_path / "Program Files" / "Falcon Engine"),
                                               "--data", str(tmp_path / "ProgramData" / "Falcon Engine"), *extra])


def test_the_plan_is_the_ten_steps_in_order_and_the_uninstall_keeps_the_secret():
    inst = engine_install.EngineInstall(engine_install.parser().parse_args([]), say=lambda m: None)
    steps = [s.name for s in inst.plan().steps]
    assert steps == ["Check", "Stop the old service", "Copy the code", "The runtime", "The data folder", "PostgreSQL", "Settings", "Setup",
                     "The Engine service", "Receipt"]
    gone = [s.name for s in inst.uninstall_plan().steps]
    assert gone == ["Stop and remove the service", "Remove the program", "Data"]
    assert inst.remove_data().startswith("kept")                      # without --purge-data the master secret stays


def test_every_setting_is_an_absolute_path_because_a_service_runs_in_system32(tmp_path):
    data = tmp_path / "ProgramData" / "Falcon Engine"
    text = engine_install.env_text(data, "postgresql://falcon:pw@localhost:5432/falcon", 7400)
    paths = {k: v for k, _, v in (ln.partition("=") for ln in text.splitlines() if "=" in ln and not ln.startswith("#"))}
    for key in ("FALCON_TLS_CERT", "FALCON_TLS_KEY", "FALCON_SECRET_PATH", "FALCON_LLM_MODEL_PATH"):
        assert Path(paths[key]).is_absolute() and Path(paths[key]).is_relative_to(data), key
    assert paths["FALCON_ENGINE_HOST"] == "0.0.0.0" and paths["FALCON_ENGINE_PORT"] == "7400"


def test_setup_exe_s_answers_reach_the_installer_and_the_password_is_quoted_into_the_url(tmp_path, monkeypatch):
    answers = tmp_path / "answers.json"
    answers.write_text(json.dumps({"names": "falcon.internal,10.0.0.5", "hostname": "IT-07", "port": "7410", "pg_user": "postgres",
                                   "pg_password": "p@ss:w/rd#1", "download_model": 1}), encoding="utf-8")
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
    assert a.names == "falcon.internal,10.0.0.5" and a.hostname == "IT-07" and a.port == 7410 and a.download_model is True
    assert a.admin_url == "postgresql://postgres:p%40ss%3Aw%2Frd%231@localhost:5432/postgres"


def test_the_receipt_says_the_payload_s_version(tmp_path):
    payload = tmp_path / "payload"
    payload.mkdir()
    (payload / "manifest.json").write_text(json.dumps({"role": "engine", "version": "1.4.2", "files": {}}), encoding="utf-8")
    inst = engine_install.EngineInstall(_args(tmp_path, "--source", str(payload)), say=lambda m: None)
    inst.target.mkdir(parents=True)
    inst.receipt()
    got = json.loads((inst.target / "install.json").read_text(encoding="utf-8"))
    assert got == {"role": "engine", "version": "1.4.2", "service": "FalconEngine", "data": str(inst.data)}
