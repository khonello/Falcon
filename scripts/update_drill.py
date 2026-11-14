"""A machine updating itself, end to end, on this PC (PHASES.md Phase 9: "a machine updating itself"). Run elevated, from the repository root:

    environ-engine\\Scripts\\python.exe scripts/update_drill.py C:\\b\\dist\\falcon-worker-setup.exe [--keep]

The setup.exe must be built for 127.0.0.1:7400 with data/engine.crt (build_setup's --bundle). On the TEST database (it is wiped), it:

  1. starts an Engine on 127.0.0.1:7400 (its own master secret and update folder in data/update-drill/), with one IT Admin;
  2. installs the Worker with setup.exe, silently; its service asks to be registered, and the drill confirms it with the code the Engine
     holds (a person would read it off the PC's screen);
  3. makes version 0.0.2 of the Worker's package (the same code, saying 0.0.2) and puts it where the Engine serves updates from;
  4. approves 0.0.2 and says "Update now" for the machine, as an Admin would;
  5. waits for the machine to fetch it, check it, upgrade itself, restart and say it is on 0.0.2;
  6. uninstalls, stops the Engine, and puts C:\\ProgramData\\Falcon back as it was (unless --keep).
"""

from __future__ import annotations

import asyncio
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import dotenv

dotenv.load()

from common.connection import EngineConnection
from engine.auth import derive_client_key
from engine.database import Database
from installers import payload as payload_mod

OUT = ROOT / "data" / "update-drill"
PROGRAM = Path(r"C:\Program Files\Falcon")
DATA = Path(r"C:\ProgramData\Falcon")
NEW = "0.0.2"


def say(text: str) -> None:
    print(time.strftime("%H:%M:%S"), text, flush=True)


async def seed(url: str) -> None:
    db = Database(url)
    await db.connect()
    async with db.pool.acquire() as conn:
        await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    await db.migrate()
    it = await db.accounts.create_department("IT", None)
    pc = await db.accounts.create_pc("IT-01", it, "admin_workstation", "drill-admin")
    await db.accounts.create("admin", it, pc)
    await db.close()


def package(version: str, wheels: Path, dest: Path) -> Path:
    """The Worker's payload as it would be published for `version`: this checkout's code, saying that version, zipped."""
    with tempfile.TemporaryDirectory() as tmp:
        repo = Path(tmp) / "repo"
        for name in ("common", "protocol", "worker_client", "installers"):
            shutil.copytree(ROOT / name, repo / name, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        for name in ("pyproject.toml", "requirements-worker.txt"):
            if (ROOT / name).exists():
                shutil.copy2(ROOT / name, repo / name)
        svc = repo / "worker_client" / "service.py"
        svc.write_text(svc.read_text(encoding="utf-8").replace('VERSION = "0.0.1"', f'VERSION = "{version}"', 1), encoding="utf-8")
        py = repo / "pyproject.toml"
        py.write_text(py.read_text(encoding="utf-8").replace('version = "0.0.1"', f'version = "{version}"', 1), encoding="utf-8")
        built = Path(tmp) / "payload"
        payload_mod.build("worker", built, repo=repo, wheels=wheels)
        dest.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(dest, "w", zipfile.ZIP_DEFLATED) as z:
            for f in sorted(built.rglob("*")):
                if f.is_file():
                    z.write(f, f.relative_to(built).as_posix())
    return dest


def wheels_for(dest: Path) -> Path:
    from installers.windows.build_setup import fetch_wheels

    python = PROGRAM / "python" / "python.exe"
    fetch_wheels(python, payload_mod.requirements_for("worker"), dest)
    return dest


def run(argv: list[str], **kw) -> subprocess.CompletedProcess:
    return subprocess.run(argv, capture_output=True, text=True, check=False, **kw)


def service_state() -> str:
    got = run(["sc.exe", "query", "FalconWorker"]).stdout
    return "RUNNING" if "RUNNING" in got else "STOPPED" if "STOPPED" in got else "absent"


async def wait_for(what: str, check, seconds: float, every: float = 2.0):
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        got = await check()
        if got:
            return got
        await asyncio.sleep(every)
    raise TimeoutError(f"{what}: not within {seconds:.0f} s")


async def main() -> int:
    setup = Path(sys.argv[1])
    keep = "--keep" in sys.argv
    url = os.environ.get("FALCON_TEST_DATABASE_URL", "")
    if "test" not in url:
        print("FALCON_TEST_DATABASE_URL must be a test database: this wipes it")
        return 2
    if PROGRAM.exists():
        print(f"{PROGRAM} is there already: uninstall it first")
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    backup = OUT / "programdata-before"
    if backup.exists():
        shutil.rmtree(backup)
    if DATA.exists():
        shutil.copytree(DATA, backup)
    secret = os.urandom(32)
    (OUT / "master.secret").write_text(secret.hex())
    await seed(url)
    env = {**os.environ, "FALCON_DATABASE_URL": url, "FALCON_ENGINE_PORT": "7400", "FALCON_ENGINE_HOST": "127.0.0.1",
           "FALCON_SECRET_PATH": str(OUT / "master.secret"), "FALCON_ADMIN_SCOPE": "organisation", "FALCON_GROQ_API_KEY": "",
           "FALCON_LLM_MODEL_PATH": str(OUT / "no-model.gguf")}
    (OUT / "stop").unlink(missing_ok=True)
    engine = start_engine(env)
    ok = False
    try:
        await wait_for("the Engine", lambda: _true(b"Engine listening on" in (OUT / "engine.log").read_bytes()), 60, 0.5)
        say("1. Engine up on 127.0.0.1:7400 (test database)")
        p = run([str(setup), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"])
        say(f"2. setup.exe exit {p.returncode}; service {service_state()}")
        db = Database(url)
        await db.connect()
        enr = await wait_for("the request to be registered", lambda: db.pool.fetchrow("SELECT id, code, hostname FROM enrollments WHERE status = 'pending'"), 120)
        admin = EngineConnection("127.0.0.1", 7400, client_id="drill-admin", ca_cert=str(ROOT / "data" / "engine.crt"),
                                 derived_key=derive_client_key(secret, "drill-admin"), hostname="IT-01")
        await admin.connect()
        it = (await db.pool.fetchrow("SELECT id FROM departments WHERE name = 'IT'"))["id"]
        await admin.call("enroll.confirm", {"enrollment_id": enr["id"], "code": enr["code"], "department_id": it})
        say(f"   registered {enr['hostname']} with its code {enr['code']}")
        pc = await wait_for("the machine to come online", lambda: db.pool.fetchrow(
            "SELECT id, hostname, agent_version FROM pcs WHERE pc_type = 'client_pc' AND agent_version IS NOT NULL"), 120)
        say(f"   online: {pc['hostname']} (pc {pc['id']}) on {pc['agent_version']}")
        with tempfile.TemporaryDirectory() as tmp:
            pkg = package(NEW, wheels_for(Path(tmp) / "wheels"), OUT / "updates" / NEW / "worker.zip")
        say(f"3. published {NEW}: {pkg} ({pkg.stat().st_size / 1e6:.1f} MB)")
        await admin.call("updates.approve", {"version": NEW})
        await admin.call("update.now", {"pc_id": pc["id"]})
        say(f"4. approved {NEW}; Update now sent to {pc['hostname']}")
        t0 = time.monotonic()
        row = await wait_for(f"the machine to be on {NEW}", lambda: db.pool.fetchrow(
            "SELECT agent_version FROM pcs WHERE id = $1 AND agent_version = $2", pc["id"], NEW), 600, 3)
        async def receipt_new():                             # (the installer writes its receipt last, after it has started the service again)
            got = json.loads((PROGRAM / "install.json").read_text(encoding="utf-8"))
            return got if got.get("version") == NEW else None

        try:
            receipt = await wait_for("the receipt", receipt_new, 60, 1)
        except TimeoutError:
            receipt = json.loads((PROGRAM / "install.json").read_text(encoding="utf-8"))
        statuses = await db.pool.fetch("SELECT action_type, detail FROM audit_log WHERE action_type LIKE 'update.%' ORDER BY id")
        say(f"5. {pc['hostname']} is on {row['agent_version']} after {time.monotonic() - t0:.0f} s; receipt says {receipt.get('version')}; "
            f"service {service_state()}")
        for s in statuses:
            say(f"   audit {s['action_type']}: {json.dumps(s['detail'])[:140]}")
        await admin.close()
        await db.close()
        ok = row["agent_version"] == NEW and receipt.get("version") == NEW
    finally:
        if not keep:
            uninst = PROGRAM / "unins000.exe"
            if uninst.exists():
                run([str(uninst), "/VERYSILENT", "/SUPPRESSMSGBOXES", "/NORESTART"])
                for _ in range(30):                          # (Setup's uninstaller finishes from a copy of itself, a moment later)
                    if not PROGRAM.exists():
                        break
                    await asyncio.sleep(1)
                ok = ok and not PROGRAM.exists()
            if DATA.exists():
                shutil.rmtree(DATA, ignore_errors=True)
            if backup.exists():
                shutil.copytree(backup, DATA)
            say(f"6. uninstalled (program there: {PROGRAM.exists()}); {DATA} put back")
        (OUT / "stop").write_text("stop")
        try:
            engine.wait(timeout=60)
        except subprocess.TimeoutExpired:
            engine.kill()
    say("PASSED" if ok else "FAILED")
    return 0 if ok else 1


async def _true(value):
    return value


def start_engine(env: dict[str, str]) -> subprocess.Popen[bytes]:
    with open(OUT / "engine.log", "wb") as log:
        return subprocess.Popen([sys.executable, str(ROOT / "scripts" / "load_engine.py"), str(OUT)], cwd=ROOT, env=env, stdout=log, stderr=log)


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
