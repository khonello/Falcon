"""Action execution on this PC -- the Script Execution Model (spec 7.3).

    Engine -> action.execute {execution_id, action, timeout_s}
    we    -> control.execution_output {execution_id, chunk}     (streamed as the log grows)
    we    -> control.execution_result {execution_id, status, exit_code, output_log_path}
    Engine -> action.terminate {execution_id}                   (manual stop, by id)

Scripts (Custom Actions, and built-ins implemented as scripts) run DETACHED from the request
cycle via `asyncio.create_subprocess_exec` -- never `_shell`, always an explicit argv against
the bundled interpreter (`sys.executable` for Python; `powershell.exe -NoProfile -File` for
PowerShell). Output goes to a per-execution log file; a background task tails it by polling
on a fixed interval and only reading when the size has grown. Timeout -> the process is
killed and the status is `timeout` (distinct from `failed`); manual termination -> `terminated`.

Custom Actions are re-validated here on arrival (stdlib + Windows-native only), in case of
tampering in transit. No sandboxing: accountability is the audit trail (spec 7.3).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from common.custom_actions import validate

log = logging.getLogger(__name__)

Reporter = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]

TAIL_INTERVAL = 0.5
KILL_GRACE = 3.0

# Built-ins implemented as small Python scripts run through the same detached path, so every
# Action -- built-in or Custom -- has the same timeout/termination/output behaviour.
BUILTIN_SCRIPTS: dict[str, str] = {
    "process_list": (
        "import json, psutil\n"
        "rows=[{'pid':p.pid,'name':p.info['name'],'rss':p.info['memory_info'].rss if p.info['memory_info'] else None}"
        " for p in psutil.process_iter(['name','memory_info'])]\n"
        "print(json.dumps(sorted(rows, key=lambda r: -(r['rss'] or 0))[:50]))\n"),
    "system_metrics": (
        "import json, psutil\n"
        "print(json.dumps({'cpu': psutil.cpu_percent(interval=0.5), 'memory': psutil.virtual_memory().percent,"
        " 'disk': psutil.disk_usage('/').percent}))\n"),
    "idle_time": "from worker_client import idle\nprint(idle.idle_seconds())\n",
    "file_activity": (
        "import os, sys, json, time\np=sys.argv[1]\nout=[]\n"
        "for d,_,fs in os.walk(p):\n  for f in fs:\n    fp=os.path.join(d,f)\n"
        "    try: st=os.stat(fp)\n    except OSError: continue\n"
        "    out.append({'path':fp,'size':st.st_size,'mtime':time.strftime('%Y-%m-%d %H:%M',time.localtime(st.st_mtime))})\n"
        "print(json.dumps(sorted(out,key=lambda r:r['mtime'],reverse=True)[:100]))\n"),
    "snapshot_file": (
        "import hashlib, shutil, sys, os, json, time\np=sys.argv[1]\n"
        "h=hashlib.sha256(open(p,'rb').read()).hexdigest()\n"
        "dst=p+'.snapshot-'+time.strftime('%Y%m%d%H%M%S')\nshutil.copy2(p,dst)\n"
        "print(json.dumps({'path':p,'sha256':h,'snapshot':dst}))\n"),
    "rename_file": "import os, sys\nos.rename(sys.argv[1], os.path.join(os.path.dirname(sys.argv[1]), sys.argv[2]))\nprint('renamed')\n",
    "restore_file": (
        "import glob, shutil, sys, os\np=sys.argv[1]\nsnaps=sorted(glob.glob(p+'.snapshot-*'))\n"
        "if not snaps: sys.exit('no snapshot for '+p)\nshutil.copy2(snaps[-1], p)\nprint('restored from '+snaps[-1])\n"),
    "kill_process": (
        "import psutil, sys\nname=sys.argv[1].lower()\nn=0\n"
        "for p in psutil.process_iter(['name']):\n  if (p.info['name'] or '').lower()==name:\n    p.terminate(); n+=1\n"
        "print(f'terminated {n} process(es)')\n"),
    "start_process": "import subprocess, sys, shlex\nsubprocess.Popen(shlex.split(sys.argv[1]))\nprint('started')\n",
    "notify": "import sys\nprint('NOTIFY: ' + sys.argv[1])\n",
    "usb_contents": (
        "import json, psutil, os\nout={}\n"
        "for part in psutil.disk_partitions(all=False):\n"
        "  if 'removable' in part.opts.lower() or part.fstype=='' :\n"
        "    try: out[part.mountpoint]=os.listdir(part.mountpoint)[:200]\n    except OSError: pass\n"
        "print(json.dumps(out))\n"),
    "screenshot": (
        "import sys, subprocess, time, os\n"
        "if sys.platform!='win32': sys.exit('screenshot: unsupported on this platform in v1')\n"
        "out=os.path.join(os.environ.get('TEMP','.'), 'falcon-shot-'+time.strftime('%Y%m%d%H%M%S')+'.png')\n"
        "ps=('Add-Type -AssemblyName System.Windows.Forms,System.Drawing; '\n"
        "    '$b=[System.Windows.Forms.Screen]::PrimaryScreen.Bounds; '\n"
        "    '$bmp=New-Object System.Drawing.Bitmap $b.Width,$b.Height; '\n"
        "    '$g=[System.Drawing.Graphics]::FromImage($bmp); $g.CopyFromScreen($b.Location,[System.Drawing.Point]::Empty,$b.Size); '\n"
        "    f\"$bmp.Save('{out}')\")\n"
        "subprocess.run(['powershell','-NoProfile','-Command',ps],check=True)\nprint(out)\n"),
    "lock_session": "import sys, ctypes\nif sys.platform=='win32': ctypes.windll.user32.LockWorkStation()\nprint('locked')\n",
    "shutdown": "import sys, subprocess\nsubprocess.run(['shutdown','/s','/t','30'] if sys.platform=='win32' else ['shutdown','-h','+1'])\nprint('shutdown scheduled')\n",
    "reboot": "import sys, subprocess\nsubprocess.run(['shutdown','/r','/t','30'] if sys.platform=='win32' else ['shutdown','-r','+1'])\nprint('reboot scheduled')\n",
}
BUILTIN_ARGS: dict[str, list[str]] = {
    "file_activity": ["path"], "snapshot_file": ["path"], "rename_file": ["path", "new_name"], "restore_file": ["path"],
    "kill_process": ["name"], "start_process": ["command"], "notify": ["message"],
}


@dataclass
class Running:
    execution_id: int
    process: asyncio.subprocess.Process
    log_path: Path
    started: float = field(default_factory=time.monotonic)
    tail_task: asyncio.Task[None] | None = None
    terminated_manually: bool = False


class Executor:
    def __init__(self, report: Reporter, *, log_dir: Path | None = None, allow_power: bool = False) -> None:
        self.report = report
        self.log_dir = log_dir or Path(tempfile.gettempdir()) / "falcon-worker" / "executions"
        self.log_dir.mkdir(parents=True, exist_ok=True)
        self.allow_power = allow_power
        self.running: dict[int, Running] = {}
        self.completed: dict[int, str] = {}

    # --- entry points (called from push handlers) -----------------------------------------------

    async def execute(self, payload: dict[str, Any]) -> None:
        execution_id = int(payload["execution_id"])
        action = payload.get("action") or {}
        timeout = float(payload.get("timeout_s") or 60)
        try:
            argv, source = self._prepare(action)
        except ValueError as exc:
            await self._finish(execution_id, "failed", error=str(exc))
            return
        script_path = self.log_dir / f"{execution_id}.{'ps1' if action.get('language') == 'powershell' else 'py'}"
        script_path.write_text(source, encoding="utf-8")
        argv = [a.replace("{script}", str(script_path)) for a in argv]
        log_path = self.log_dir / f"{execution_id}.log"
        log_file = await asyncio.to_thread(open, log_path, "wb")  # handed to the subprocess
        try:
            proc = await asyncio.create_subprocess_exec(
                *argv, stdout=log_file, stderr=subprocess.STDOUT, stdin=subprocess.DEVNULL,
                cwd=str(self.log_dir), env={**os.environ, "PYTHONPATH": _repo_root(), "PYTHONIOENCODING": "utf-8"})
        except (OSError, ValueError) as exc:
            log_file.close()
            await self._finish(execution_id, "failed", error=f"could not start: {exc}")
            return
        finally:
            log_file.close()
        run = Running(execution_id=execution_id, process=proc, log_path=log_path)
        self.running[execution_id] = run
        run.tail_task = asyncio.create_task(self._tail(run))
        asyncio.create_task(self._wait(run, timeout))
        log.info("execution %s started: %s", execution_id, action.get("name") or action.get("builtin_type"))

    async def terminate(self, execution_id: int) -> bool:
        run = self.running.get(execution_id)
        if run is None:
            return False
        run.terminated_manually = True
        await self._kill(run)
        return True

    # --- internals ------------------------------------------------------------------------------

    def _prepare(self, action: dict[str, Any]) -> tuple[list[str], str]:
        kind = action.get("kind")
        if kind == "custom":
            language, source = action.get("language"), action.get("script") or ""
            result = validate(str(language), source)   # re-validate on arrival
            if not result.ok:
                raise ValueError("custom action rejected on arrival: " + "; ".join(result.problems))
            if language == "powershell":
                exe = shutil.which("powershell") or shutil.which("pwsh")
                if not exe:
                    raise ValueError("PowerShell is not available on this PC")
                return [exe, "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass", "-File", "{script}"], source
            return [sys.executable, "-u", "{script}"], source
        builtin = str(action.get("builtin_type") or "")
        if builtin in ("shutdown", "reboot", "lock_session") and not self.allow_power:
            raise ValueError(f"{builtin} is disabled on this PC (allow_power is off)")
        source = BUILTIN_SCRIPTS.get(builtin)
        if source is None:
            raise ValueError(f"unknown builtin {builtin!r}")
        params = action.get("params") or {}
        args = [str(params.get(name, "")) for name in BUILTIN_ARGS.get(builtin, [])]
        return [sys.executable, "-u", "{script}", *args], source

    async def _tail(self, run: Running) -> None:
        """Stream new output as the log grows; only read when the size changed."""
        offset = 0
        try:
            while True:
                await asyncio.sleep(TAIL_INTERVAL)
                try:
                    size = run.log_path.stat().st_size
                except OSError:
                    continue
                if size <= offset:
                    if run.process.returncode is not None:
                        return
                    continue
                with run.log_path.open("rb") as f:
                    f.seek(offset)
                    chunk = f.read(size - offset)
                offset = size
                text = chunk.decode("utf-8", errors="replace")
                for line in text.splitlines():
                    if line.strip():
                        await self.report("control.execution_output", {"execution_id": run.execution_id, "chunk": line[:2000]})
        except asyncio.CancelledError:
            pass

    async def _wait(self, run: Running, timeout: float) -> None:
        status = "success"
        try:
            await asyncio.wait_for(run.process.wait(), timeout)
        except asyncio.TimeoutError:
            await self._kill(run)
            status = "timeout"
        if run.terminated_manually:
            status = "terminated"
        elif status == "success" and run.process.returncode not in (0, None):
            status = "failed"
        # Let the tail flush the final output, then stop it.
        await asyncio.sleep(TAIL_INTERVAL * 1.5)
        if run.tail_task:
            run.tail_task.cancel()
        self.running.pop(run.execution_id, None)
        tail = ""
        try:
            tail = run.log_path.read_text(encoding="utf-8", errors="replace")[-4000:]
        except OSError:
            pass
        await self._finish(run.execution_id, status, exit_code=run.process.returncode, log_path=run.log_path, output=tail)

    async def _kill(self, run: Running) -> None:
        proc = run.process
        if proc.returncode is not None:
            return
        try:
            proc.terminate()
            try:
                await asyncio.wait_for(proc.wait(), KILL_GRACE)
            except asyncio.TimeoutError:
                proc.kill()
                await proc.wait()
        except ProcessLookupError:
            pass

    async def _finish(self, execution_id: int, status: str, *, exit_code: int | None = None,
                      log_path: Path | None = None, output: str = "", error: str | None = None) -> None:
        payload: dict[str, Any] = {"execution_id": execution_id, "status": status, "exit_code": exit_code,
                                   "output_log_path": str(log_path) if log_path else None,
                                   "output": (error or output)[-4000:] if (error or output) else None}
        try:
            await self.report("control.execution_result", payload)
        except Exception as exc:  # noqa: BLE001
            log.warning("could not report execution %s: %s", execution_id, exc)
        # Recorded only once the Engine has been told, so "completed" means "completed and reported".
        self.completed[execution_id] = status
        log.info("execution %s %s (exit %s)", execution_id, status, exit_code)

    async def shutdown(self) -> None:
        """Service stop: kill anything still running and stop tailing. Their results are not
        reported -- the Engine's own timeout guard will mark them terminated."""
        for run in list(self.running.values()):
            if run.tail_task:
                run.tail_task.cancel()
            await self._kill(run)
        self.running.clear()


def _repo_root() -> str:
    """So built-in scripts can `from worker_client import idle` under the bundled interpreter."""
    return str(Path(__file__).resolve().parent.parent)


def describe_platform() -> dict[str, Any]:
    return {"system": platform.system(), "release": platform.release(), "python": sys.version.split()[0],
            "powershell": bool(shutil.which("powershell") or shutil.which("pwsh")), "json": json.__name__}
