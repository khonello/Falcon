"""Live drills: Flow, Restricted and Task tried the way a person would, against a running Engine and real Worker processes on this PC.

Nothing here is a unit test: it starts real processes, writes real files and waits real seconds, then says what happened. Every scenario prints
PASS or FAIL with what it saw; a FAIL is a finding to fix.

    environ-operator\\Scripts\\python.exe scripts\\live_drill.py flow
    environ-operator\\Scripts\\python.exe scripts\\live_drill.py restricted
    environ-operator\\Scripts\\python.exe scripts\\live_drill.py task

It uses the Engine in `.env` (start it first: `python -m engine`), the Super User saved on this machine (`python -m engine setup`) and the
Admin written by `scripts/make_org.py` (`data/admin.json`). It makes its own Workers (WS-D1, WS-D2, WS-D3) in that Admin's department the first
time, remembers them in `data/drill/state.json`, and keeps their folders under `data/drill/`.
"""
from __future__ import annotations

import asyncio
import json
import subprocess
import sys
import time
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from operator_client.core import EngineConnection, LocalConfig

DRILL = ROOT / "data" / "drill"
STATE = DRILL / "state.json"
WORKER_PY = ROOT / "environ-worker" / "Scripts" / "python.exe"
results: list[tuple[str, bool, str]] = []


def say(text: str = "") -> None:
    print(text, flush=True)


def check(name: str, ok: bool, saw: str = "") -> bool:
    results.append((name, ok, saw))
    say(f"  {'PASS' if ok else 'FAIL'}  {name}" + (f"   [{saw}]" if saw and not ok else ""))
    return ok


async def wait_for(cond, seconds: float = 20.0, step: float = 0.25) -> bool:
    end = time.monotonic() + seconds
    while time.monotonic() < end:
        res = cond()
        if asyncio.iscoroutine(res):
            res = await res
        if res:
            return True
        await asyncio.sleep(step)
    return False


async def connect(cfg: dict[str, Any]) -> EngineConnection:
    c = EngineConnection(cfg["engine_host"], cfg["engine_port"], client_id=cfg["client_id"], tls=cfg["tls"], ca_cert=cfg.get("ca_cert"),
                         derived_key=cfg.get("client_key"))
    await c.connect()
    return c


def su_config() -> dict[str, Any]:
    c = LocalConfig.load()
    return {"engine_host": c.engine_host, "engine_port": c.engine_port, "client_id": c.client_id, "client_key": c.client_key, "tls": c.tls,
            "ca_cert": c.ca_cert}


def admin_config() -> dict[str, Any]:
    return json.loads((ROOT / "data" / "admin.json").read_text(encoding="utf-8"))


class Drill:
    def __init__(self) -> None:
        self.su: EngineConnection | None = None
        self.admin: EngineConnection | None = None
        self.state: dict[str, Any] = json.loads(STATE.read_text(encoding="utf-8")) if STATE.exists() else {"workers": {}}
        self.procs: dict[str, subprocess.Popen] = {}
        self.engine_cfg = su_config()

    async def start(self) -> None:
        DRILL.mkdir(parents=True, exist_ok=True)
        self.su = await connect(self.engine_cfg)
        self.admin = await connect(admin_config())

    async def stop(self) -> None:
        for name in list(self.procs):
            self.stop_worker(name)
        for c in (self.su, self.admin):
            if c is not None:
                await c.close()
        STATE.write_text(json.dumps(self.state, indent=2), encoding="utf-8")

    # --- workers -----------------------------------------------------------------------------------------------

    async def worker_account(self, name: str) -> dict[str, Any]:
        """A Worker account in the Admin's department (made once, remembered)."""
        if name not in self.state["workers"]:
            dept = (await self.admin.call("hierarchy.tree"))["viewer"]            # type: ignore[union-attr]
            tree = await self.su.call("hierarchy.tree")                            # type: ignore[union-attr]
            admin_id = admin_config()["client_id"]
            dept_id = next(d["department_id"] for d in tree["departments"] if any(a.get("hostname") == "ADM-01" for a in d["admins"]))
            made = await self.su.call("hierarchy.account_create", {"role": "worker", "hostname": name, "department_id": dept_id})   # type: ignore[union-attr]
            self.state["workers"][name] = {"client_id": made["client_id"], "client_key": made["client_key"], "account_id": made["account_id"],
                                           "department_id": dept_id}
            STATE.write_text(json.dumps(self.state, indent=2), encoding="utf-8")
            _ = dept, admin_id
        return self.state["workers"][name]

    def folder(self, worker: str, sub: str = "") -> Path:
        p = DRILL / worker / sub
        p.mkdir(parents=True, exist_ok=True)
        return p

    def start_worker(self, name: str, watch: list[Path]) -> None:
        w = self.state["workers"][name]
        cfg = {"engine_host": self.engine_cfg["engine_host"], "engine_port": self.engine_cfg["engine_port"], "client_id": w["client_id"],
               "client_key": w["client_key"], "tls": self.engine_cfg["tls"], "ca_cert": self.engine_cfg["ca_cert"], "windows": False,
               "watch_roots": [str(p) for p in watch], "poll_seconds": 1.0, "metrics_seconds": 5, "idle_sweep_after_seconds": 999999}
        path = DRILL / name / "worker.json"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cfg, indent=2), encoding="utf-8")
        log = open(DRILL / name / "worker.log", "ab")                                           # noqa: SIM115 -- lives as long as the process
        self.procs[name] = subprocess.Popen([str(WORKER_PY), "-m", "worker_client", "--config", str(path)], cwd=ROOT, stdout=log, stderr=log)

    def stop_worker(self, name: str) -> None:
        p = self.procs.pop(name, None)
        if p is not None and p.poll() is None:
            p.terminate()
            try:
                p.wait(5)
            except subprocess.TimeoutExpired:
                p.kill()

    async def online(self, *names: str) -> bool:
        async def ready() -> bool:
            tree = await self.su.call("hierarchy.tree")                                          # type: ignore[union-attr]
            up = {w["hostname"] for d in tree["departments"] for w in d["workers"] if w["online"]}
            return all(n in up for n in names)
        return await wait_for(ready, 30)

    async def pc_id(self, hostname: str) -> int:
        tree = await self.su.call("hierarchy.tree")                                              # type: ignore[union-attr]
        for d in tree["departments"]:
            for w in d["workers"] + d["admins"]:
                if w["hostname"] == hostname:
                    return w["pc_id"]
        raise KeyError(hostname)


def report() -> int:
    bad = [r for r in results if not r[1]]
    say(f"\n{len(results) - len(bad)} passed, {len(bad)} failed")
    for name, _, saw in bad:
        say(f"  FAILED: {name}   [{saw}]")
    return 1 if bad else 0


async def main(which: str) -> int:
    from live_drills import (
        flow_drill,
        forms_drill,
        gui_drill,
        restricted_drill,
        task_drill,
    )

    d = Drill()
    await d.start()
    try:
        await {"flow": flow_drill, "restricted": restricted_drill, "task": task_drill, "gui": gui_drill, "forms": forms_drill}[which].run(d, check, say, wait_for)
    finally:
        await d.stop()
    return report()


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(asyncio.run(main(sys.argv[1] if len(sys.argv) > 1 else "flow")))
