"""The update pipeline (Phase 9): a machine fetches its role's package of an approved version from the Engine, checks it, and starts the
installer's upgrade; the new service says how it went (engine/updates.py update.fetch, worker_client/updater.py)."""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

from tests.conftest import requires_db


def _zipped(folder: Path) -> bytes:
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for p in folder.rglob("*"):
            if p.is_file():
                z.write(p, p.relative_to(folder).as_posix())
    return out.getvalue()


@requires_db
async def test_a_machine_fetches_only_an_approved_versions_package_in_pieces(engine, org, connect, tmp_path, monkeypatch):
    from engine import updates

    monkeypatch.setattr(updates, "packages_dir", lambda e: tmp_path / "updates")
    monkeypatch.setattr(updates, "FETCH_CHUNK", 1000)
    data = bytes(range(256)) * 10                                                   # 2560 bytes: three pieces
    (tmp_path / "updates" / "1.2.0").mkdir(parents=True)
    (tmp_path / "updates" / "1.2.0" / "worker.zip").write_bytes(data)
    w1 = await connect("cid-w1")
    assert await w1.err("update.fetch", {"version": "1.2.0", "role": "worker"}) == "not_found"          # not approved yet
    await engine.db.updates.approve_version("1.2.0", org["su"])
    first = await w1.ok("update.fetch", {"version": "1.2.0", "role": "worker", "index": 0})
    assert first["total"] == 3 and first["sha256"] == hashlib.sha256(data).hexdigest()
    got = b""
    for i in range(3):
        got += base64.b64decode((await w1.ok("update.fetch", {"version": "1.2.0", "role": "worker", "index": i}))["content_b64"])
    assert got == data
    assert await w1.err("update.fetch", {"version": "1.2.0", "role": "admin"}) == "not_found"           # no admin package was put there
    assert await w1.err("update.fetch", {"version": "../../etc", "role": "worker"}) == "not_found"


def test_the_worker_checks_the_package_starts_the_installer_and_the_new_service_says_how_it_went(tmp_path: Path, monkeypatch):
    from installers import payload as payload_mod
    from worker_client.updater import Updater

    built = tmp_path / "built"
    payload_mod.build("worker", built)
    package = _zipped(built)
    digest = hashlib.sha256(package).hexdigest()
    asked: list[tuple[str, dict]] = []

    async def report(type_, payload):
        asked.append((type_, payload))
        if type_ == "update.fetch":
            return {"total": 1, "sha256": digest, "index": 0, "content_b64": base64.b64encode(package).decode("ascii")}
        return {}

    cert = tmp_path / "engine.crt"
    import ssl

    from installers.common import (
        cert_fingerprint,  # noqa: F401  (the bundle written carries the same fingerprint)
    )
    cert.write_text(ssl.DER_cert_to_PEM_cert(b"0\x03\x02\x01\x00"), encoding="utf-8")       # any certificate-shaped thing: only its form is used here
    settings = tmp_path / "data" / "worker.json"
    settings.parent.mkdir()
    config = SimpleNamespace(path=settings, serve_console=False, windows=True, engine_host="falcon.internal", engine_port=7400, ca_cert=str(cert))
    target = tmp_path / "Program Files" / "Falcon"
    target.mkdir(parents=True)
    (target / "install.json").write_text("{}", encoding="utf-8")
    u = Updater(report, running_version="1.1.0", update_command=None, config=config)
    monkeypatch.setattr(u, "installed_here", lambda: target)
    launched: list[list[str]] = []
    monkeypatch.setattr(u, "_launch", lambda argv, cwd, out, flags: launched.append(argv))
    u.pending = "1.2.0"
    assert asyncio.run(u.attempt(force=True)) is True
    argv = launched[0]
    assert argv[1:4] == ["-m", "installers.windows.install", "--role"] and argv[4] == "worker" and argv[argv.index("--target") + 1] == str(target)
    bundle = json.loads(Path(argv[argv.index("--bundle") + 1]).read_text(encoding="utf-8"))
    assert bundle["engine_host"] == "falcon.internal" and bundle["ca_pem"].startswith("-----BEGIN CERTIFICATE-----")
    assert not any(t == "updates.report_status" for t, _ in asked)               # not yet: the new service says how it went
    note = json.loads((settings.parent / "update-pending.json").read_text(encoding="utf-8"))
    assert note["version"] == "1.2.0" and note["from"] == "1.1.0"

    # the service, started again on the new version, says it worked
    after = Updater(report, running_version="1.2.0", update_command=None, config=config)
    asyncio.run(after.check_pending())
    assert asked[-1] == ("updates.report_status", {"version": "1.2.0", "succeeded": True, "running": "1.2.0"})
    assert not (settings.parent / "update-pending.json").exists()

    # a package that did not arrive whole is never unpacked
    bad = Updater(lambda t, p: _bad(t, p), running_version="1.1.0", update_command=None, config=config)
    monkeypatch.setattr(bad, "installed_here", lambda: target)
    bad.pending = "1.3.0"
    assert asyncio.run(bad.attempt(force=True)) is False and bad.last_error == "The package did not arrive whole"


async def _bad(type_, payload):
    if type_ == "update.fetch":
        return {"total": 1, "sha256": "0" * 64, "index": 0, "content_b64": base64.b64encode(b"not the package").decode("ascii")}
    return {}
