"""Load run (PHASES.md Phase 10): many PCs, sustained file activity, against a real Engine in its own process -- and where the Engine's time goes.

    environ-engine\\Scripts\\python.exe scripts/load_run.py [--pcs 200] [--rate 1.0] [--seconds 60] [--profile]

It uses the TEST database (FALCON_TEST_DATABASE_URL; it refuses any URL without "test" in it), which it wipes and fills with one IT Admin and
--pcs Workers in ten departments. It then starts the Engine as its own process (TLS and the real handshake, on port 7411, its own master
secret in data/load/), connects every Worker, and has each send file events (create, change, copy, move, rename, delete, now and then a
restricted file) at --rate a second on average, while an IT Admin asks two things every half second and times them.

It reports: events sent and answered a second, how long an event took to be answered (median, 99th, worst), the Admin's answers, and the
Engine's own loop lag (how late a 50 ms timer inside it ran: the measure of whether anything holds the loop). With --profile the Engine runs
under cProfile and the top of where its time went is printed (data/load/engine.prof).

The Engine side is `scripts/load_engine.py`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import random
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from common import dotenv

dotenv.load()

from common.connection import EngineConnection
from engine.auth import derive_client_key
from engine.database import Database

PORT = 7411
OUT = ROOT / "data" / "load"
FOLDERS = ["Documents", "Documents\\Finance", "Desktop", "Downloads", "Documents\\Reports", "Pictures"]
EXTS = [".docx", ".xlsx", ".pdf", ".txt", ".csv", ".png", ".zip", ".pptx"]


def pct(xs: list[float], p: float) -> float:
    if not xs:
        return float("nan")
    xs = sorted(xs)
    return xs[min(len(xs) - 1, int(len(xs) * p))]


async def seed(url: str, n: int, secret: bytes) -> tuple[str, list[str]]:
    db = Database(url)
    await db.connect()
    async with db.pool.acquire() as conn:
        await conn.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
    await db.migrate()
    acc = db.accounts
    it = await acc.create_department("IT", None)
    depts = [await acc.create_department(f"Dept {i}", None) for i in range(10)]
    adm_pc = await acc.create_pc("IT-01", it, "admin_workstation", "load-admin")
    await acc.create("admin", it, adm_pc)
    ids = []
    for i in range(n):
        cid = f"load-w{i}"
        pc = await acc.create_pc(f"WS-{i:03d}", depts[i % 10], "client_pc", cid)
        await acc.create("worker", depts[i % 10], pc)
        ids.append(cid)
    await db.close()
    return "load-admin", ids


def event(rnd: random.Random, i: int, user: str) -> dict:
    base = f"C:\\Users\\{user}\\"
    path = f"{base}{rnd.choice(FOLDERS)}\\file{rnd.randint(0, 400)}{rnd.choice(EXTS)}"
    op = rnd.choices(["create", "modify", "copy", "move", "delete"], [3, 6, 2, 2, 1])[0]
    e = {"op": op, "path": path, "name": path.rsplit("\\", 1)[-1], "witness": {"by": rnd.choice(["hand", "hand", "started", "alone"])}, "at": time.time()}
    if op != "delete":
        e["hash"] = f"{rnd.getrandbits(64):016x}{i % 7}"
    if op in ("copy", "move"):
        e["old_path"] = f"{base}{rnd.choice(FOLDERS)}\\file{rnd.randint(0, 400)}{rnd.choice(EXTS)}"
    return e


async def worker(cid: str, secret: bytes, ca: str, rate: float, until: float, lat: list[float], counts: dict[str, int], seed_: int) -> None:
    conn = EngineConnection("127.0.0.1", PORT, client_id=cid, ca_cert=ca, derived_key=derive_client_key(secret, cid), hostname=cid.replace("load-w", "WS-"),
                            request_timeout=60)
    rnd = random.Random(seed_)
    try:
        await conn.connect()
    except Exception as exc:  # noqa: BLE001
        counts["connect_failed"] += 1
        print(f"{cid}: could not connect: {exc}")
        return
    counts["connected"] += 1
    i = 0
    try:
        while time.monotonic() < until:
            await asyncio.sleep(rnd.expovariate(rate))
            i += 1
            t0 = time.perf_counter()
            try:
                await conn.call("index.event", {"event": event(rnd, i, cid)})
                lat.append(time.perf_counter() - t0)
                counts["answered"] += 1
            except Exception as exc:  # noqa: BLE001
                counts["failed"] += 1
                if counts["failed"] <= 5:
                    print(f"{cid}: {exc}")
            counts["sent"] += 1
    finally:
        await conn.close()


async def admin(cid: str, secret: bytes, ca: str, until: float, lat: dict[str, list[float]]) -> None:
    conn = EngineConnection("127.0.0.1", PORT, client_id=cid, ca_cert=ca, derived_key=derive_client_key(secret, cid), hostname="IT-01", request_timeout=60)
    await conn.connect()
    try:
        while time.monotonic() < until:
            for op, payload in (("system.health", {}), ("detective.cases", {"include_noted": True})):
                t0 = time.perf_counter()
                await conn.call(op, payload)
                lat.setdefault(op, []).append(time.perf_counter() - t0)
            await asyncio.sleep(0.5)
    finally:
        await conn.close()


async def sample_cpu(engine_pid: int, out: dict[str, list[float]]) -> None:
    """Each second, how much of one core the Engine, Detective's process, PostgreSQL (all its processes) and this load generator used."""
    import psutil

    eng = psutil.Process(engine_pid)
    me = psutil.Process()

    def procs() -> dict[str, list[psutil.Process]]:
        kids = eng.children(recursive=True)                 # (a venv's python.exe on Windows is a launcher: the Engine itself is its child)
        brain = [k for k in kids if "brain.py" in " ".join(k.cmdline())]
        return {"engine": [eng, *(k for k in kids if k not in brain)], "detective": brain,
                "postgres": [p for p in psutil.process_iter(["name"]) if (p.info["name"] or "").lower().startswith("postgres")], "load": [me]}

    def total(ps: list[psutil.Process]) -> float:
        s = 0.0
        for p in ps:
            try:
                t = p.cpu_times()
                s += t.user + t.system
            except psutil.Error:
                pass
        return s

    last = {k: total(v) for k, v in procs().items()}
    while True:
        await asyncio.sleep(1.0)
        now = {k: total(v) for k, v in procs().items()}
        for k, series in out.items():
            series.append(100.0 * (now[k] - last.get(k, now[k])))
        last = now


def start_engine(cmd: list[str], env: dict[str, str]) -> subprocess.Popen[bytes]:
    with open(OUT / "engine.log", "wb") as log:
        return subprocess.Popen(cmd, cwd=ROOT, env=env, stdout=log, stderr=log)


async def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    ap.add_argument("--pcs", type=int, default=200)
    ap.add_argument("--rate", type=float, default=1.0, help="file events a second per PC, on average")
    ap.add_argument("--seconds", type=float, default=60)
    ap.add_argument("--profile", action="store_true")
    ap.add_argument("--no-event-reads", action="store_true", help="every stage reads the database itself (to measure what event_reads saves)")
    ap.add_argument("--slow", action="store_true", help="the Engine names every step that held its loop for 100 ms or more (in data/load/engine.log)")
    a = ap.parse_args()
    url = os.environ.get("FALCON_TEST_DATABASE_URL", "")
    if "test" not in url:
        print("FALCON_TEST_DATABASE_URL must be a test database (its name must say test): this wipes it")
        return 2
    OUT.mkdir(parents=True, exist_ok=True)
    secret = os.urandom(32)
    (OUT / "master.secret").write_bytes(secret.hex().encode())
    admin_id, ids = await seed(url, a.pcs, secret)
    ca = str(ROOT / "data" / "engine.crt")
    env = {**os.environ, "FALCON_DATABASE_URL": url, "FALCON_ENGINE_PORT": str(PORT), "FALCON_ENGINE_HOST": "127.0.0.1", "FALCON_SECRET_PATH": str(OUT / "master.secret"),
           "FALCON_ADMIN_SCOPE": "organisation", "FALCON_GROQ_API_KEY": "", "FALCON_LLM_MODEL_PATH": str(OUT / "no-model.gguf")}         # the model is measured on its own (llm_benchmark)
    stop = OUT / "stop"
    stop.unlink(missing_ok=True)
    cmd = [sys.executable, str(ROOT / "scripts" / "load_engine.py"), str(OUT)] + (["--profile"] if a.profile else []) + (["--slow"] if a.slow else []) + (["--no-event-reads"] if a.no_event_reads else [])
    proc = start_engine(cmd, env)
    for _ in range(60):
        await asyncio.sleep(0.5)
        if b"Engine listening on" in (OUT / "engine.log").read_bytes():
            break
    else:
        print("the Engine did not start; see data/load/engine.log")
        proc.kill()
        return 1
    counts = {"connected": 0, "connect_failed": 0, "sent": 0, "answered": 0, "failed": 0}
    lat: list[float] = []
    admin_lat: dict[str, list[float]] = {}
    t_start = time.monotonic()
    until = t_start + a.seconds
    jobs = [worker(cid, secret, ca, a.rate, until, lat, counts, k) for k, cid in enumerate(ids)]
    print(f"{a.pcs} PCs, {a.rate} events/s each on average, for {a.seconds:.0f} s ...", flush=True)
    cpu: dict[str, list[float]] = {"engine": [], "detective": [], "postgres": [], "load": []}
    sampler = asyncio.ensure_future(sample_cpu(proc.pid, cpu))
    await asyncio.gather(admin(admin_id, secret, ca, until, admin_lat), *jobs)
    sampler.cancel()
    took = time.monotonic() - t_start
    stop.write_text("stop")
    try:
        proc.wait(timeout=120)
    except subprocess.TimeoutExpired:
        proc.kill()
    lag = json.loads((OUT / "lag.json").read_text()) if (OUT / "lag.json").exists() else {}
    ms = 1000.0
    print(f"\nconnected {counts['connected']}/{a.pcs} (failed {counts['connect_failed']}); events sent {counts['sent']}, answered {counts['answered']}, "
          f"failed {counts['failed']}; {counts['answered'] / took:.0f} answered a second")
    print(f"an event's answer: median {pct(lat, .5) * ms:.1f} ms, 99th {pct(lat, .99) * ms:.1f} ms, worst {max(lat or [0]) * ms:.0f} ms")
    for op, xs in admin_lat.items():
        print(f"Admin {op}: median {pct(xs, .5) * ms:.1f} ms, 99th {pct(xs, .99) * ms:.1f} ms, worst {max(xs) * ms:.0f} ms ({len(xs)} asked)")
    busy = {k: sorted(v[3:]) for k, v in cpu.items() if len(v) > 3}            # (after the first seconds of signing in)
    if busy:
        print("CPU, % of one core (median / highest): " + ", ".join(f"{k} {v[len(v) // 2]:.0f} / {v[-1]:.0f}" for k, v in busy.items()))
    if lag:
        print(f"Engine loop lag: median {lag['p50'] * ms:.1f} ms, 99th {lag['p99'] * ms:.1f} ms, worst {lag['max'] * ms:.0f} ms ({lag.get('max_settled', 0) * ms:.0f} ms once every machine had signed in); over 100 ms {lag['over100']} times")
    if (OUT / "queries.txt").exists():
        q = (OUT / "queries.txt").read_text(encoding="utf-8").splitlines()
        total = int(q[0].split()[0])
        print(f"\nPostgreSQL statements: {total}, {total / max(1, counts['answered']):.1f} per event answered; the most asked:")
        print("\n".join(q[1:16]))
    if a.profile and (OUT / "engine.top.txt").exists():
        print("\nwhere the Engine's time went (own time):\n" + (OUT / "engine.top.txt").read_text())
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
