"""Update attempts on this PC (spec 9.4): retry when idle, never a stuck state.

`update.available {version}` marks a pending update. An attempt either runs `config.update_command` (a deployment's own command, with
`{version}` substituted), or -- on a machine Falcon's installer installed, with no command of its own -- Falcon's own pipeline:

  1. the version's package for this machine's role is fetched from the Engine in pieces (`update.fetch`), over the machine's own connection,
     and its SHA-256 checked against what the Engine said;
  2. it is unpacked (never outside its folder) and the payload's own manifest is checked (`installers.payload verify`);
  3. the installer's upgrade is started from the new payload, detached: it stops this service, replaces the code, and starts it again;
  4. the new service finds the note left in step 3 (`update-pending.json`) and says whether it is now running that version -- succeeded --
     or not, with the last line of the installer's log.
Nothing that fails is left half done: the installer is the same one that repairs an install, and it checks before it changes anything.

Retries happen only when the machine is idle and connected -- the same "notice when idle,
act then" pattern the index sweep uses.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import io
import json
import logging
import os
import shlex
import shutil
import ssl
import subprocess
import sys
import time
import zipfile
from collections.abc import Awaitable, Callable
from pathlib import Path
from typing import Any

from worker_client import idle
from worker_client.stopping import stop_tasks

log = logging.getLogger(__name__)

Reporter = Callable[[str, dict[str, Any]], Awaitable[dict[str, Any]]]


class Updater:
    def __init__(self, report: Reporter, *, running_version: str, update_command: str | None,
                 idle_after: float = 120.0, retry_seconds: float = 60.0, config: Any = None) -> None:
        self.report = report
        self.config = config                          # the Worker's settings: its role, the Engine's address and certificate, where to keep things
        self.running_version = running_version
        self.update_command = update_command
        self.idle_after = idle_after
        self.retry_seconds = retry_seconds
        self.pending: str | None = None
        self.attempts = 0
        self.last_error: str | None = None            # what the last failed attempt said, for the Engine to show
        self._task: asyncio.Task[None] | None = None

    def on_available(self, payload: dict[str, Any]) -> None:
        """An update is waiting. `now` (an Admin chose *Retry now*) tries at once instead of waiting for an idle moment."""
        version = str(payload.get("version", ""))
        if version and version != self.running_version:
            self.pending = version
            log.info("update %s available; will attempt %s", version, "now" if payload.get("now") else "when idle")
            if payload.get("now"):
                asyncio.create_task(self.attempt(force=True))
            elif self._task is None or self._task.done():
                self._task = asyncio.create_task(self._loop())

    async def stop(self) -> None:
        if self._task:
            await stop_tasks([self._task])

    async def _loop(self) -> None:
        while self.pending:
            if idle.is_idle(self.idle_after):
                await self.attempt()
            await asyncio.sleep(self.retry_seconds)

    async def attempt(self, *, force: bool = False) -> bool:
        version = self.pending
        if not version:
            return False
        self.attempts += 1
        if not self.update_command and self.installed_here() is not None:
            started = await self._own_pipeline(version)
            if started:
                return True                                   # the new service says how it went (check_pending)
            ok = False
        else:
            ok = await asyncio.to_thread(self._apply, version)
        payload = {"version": version, "succeeded": ok, "running": self.running_version}
        if not ok and self.last_error:
            payload["error"] = self.last_error
        try:
            await self.report("updates.report_status", payload)
        except Exception as exc:  # noqa: BLE001
            log.warning("could not report update attempt: %s", exc)
        if ok:
            self.running_version = version
            self.pending = None
        return ok

    # --- Falcon's own pipeline ----------------------------------------------------------------------------------------

    def installed_here(self) -> Path | None:
        """Where Falcon's installer put this program (the folder holding install.json), or None when it was not installed that way."""
        target = Path(sys.executable).resolve().parents[2] if len(Path(sys.executable).resolve().parents) > 2 else None
        return target if target is not None and (target / "install.json").is_file() and self.config is not None else None

    def _work(self) -> Path:
        return Path(self.config.path).parent / "updates"

    async def _own_pipeline(self, version: str) -> bool:
        role = "admin" if getattr(self.config, "serve_console", False) else "worker"
        try:
            first = await self.report("update.fetch", {"version": version, "role": role, "index": 0})
            total, digest = int(first["total"]), str(first["sha256"])
            pieces = [base64.b64decode(first["content_b64"])]
            for index in range(1, total):
                got = await self.report("update.fetch", {"version": version, "role": role, "index": index})
                pieces.append(base64.b64decode(got["content_b64"]))
        except Exception as exc:  # noqa: BLE001  (the Engine refused, or the connection went: a retry comes when idle)
            self.last_error = f"The package could not be fetched: {exc}"[:160]
            return False
        data = b"".join(pieces)
        if hashlib.sha256(data).hexdigest() != digest:
            self.last_error = "The package did not arrive whole"
            return False
        try:
            return await asyncio.to_thread(self._unpack_and_start, version, role, data)
        except (OSError, ValueError, zipfile.BadZipFile, subprocess.SubprocessError) as exc:
            self.last_error = f"The update could not be started: {exc}"[:160]
            return False

    def _unpack_and_start(self, version: str, role: str, data: bytes) -> bool:
        target = self.installed_here()
        assert target is not None
        work = self._work() / version
        if work.exists():
            shutil.rmtree(work)
        work.mkdir(parents=True)
        with zipfile.ZipFile(io.BytesIO(data)) as z:
            for name in z.namelist():
                dest = (work / name).resolve()
                if work.resolve() not in dest.parents and dest != work.resolve():
                    raise ValueError(f"the package names a place outside its folder: {name}")
            z.extractall(work)
        root = work if (work / "manifest.json").is_file() else next((p for p in work.iterdir() if (p / "manifest.json").is_file()), None)
        if root is None:
            raise ValueError("the package holds no payload (no manifest.json)")
        base = target / "python" / "python.exe"
        python = str(base) if base.is_file() else sys.executable
        checked = subprocess.run([python, "-m", "installers.payload", "verify", str(root)], cwd=str(root), capture_output=True, text=True, check=False)
        if checked.returncode != 0:
            self.last_error = ("The package is not whole: " + (checked.stdout + checked.stderr).strip().splitlines()[-1])[:160] \
                if (checked.stdout + checked.stderr).strip() else "The package is not whole"
            return False
        bundle = root / "falcon-client.json"
        pem = Path(self.config.ca_cert).read_text(encoding="utf-8") if self.config.ca_cert else ""
        der = ssl.PEM_cert_to_DER_cert(pem.strip()) if pem else b""
        fp = hashlib.sha256(der).hexdigest().upper()
        bundle.write_text(json.dumps({"engine_host": self.config.engine_host, "engine_port": int(self.config.engine_port), "ca_pem": pem.strip() + "\n",
                                      "ca_sha256": ":".join(fp[i:i + 2] for i in range(0, len(fp), 2))}), encoding="utf-8")
        log_path = self._work() / f"update-{version}.log"
        argv = [python, "-m", "installers.windows.install", "--role", role, "--bundle", str(bundle), "--source", str(root), "--target", str(target),
                "--python", python] + ([] if getattr(self.config, "windows", True) else ["--no-windows"])
        self._note({"version": version, "from": self.running_version, "started": time.time(), "log": str(log_path)})
        flags = 0
        if os.name == "nt":
            flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP | 0x01000000          # (CREATE_BREAKAWAY_FROM_JOB)
        with open(log_path, "wb") as out:
            self._launch(argv, root, out, flags)
        log.info("update %s: the installer was started; this service will be stopped and started again", version)
        return True

    def _launch(self, argv: list[str], cwd: Path, out: Any, flags: int) -> None:
        """Start the installer on its own: it outlives this service, which it stops and starts again."""
        subprocess.Popen(argv, cwd=str(cwd), stdout=out, stderr=subprocess.STDOUT, creationflags=flags, close_fds=True)

    def _marker(self) -> Path:
        return Path(self.config.path).parent / "update-pending.json"

    def _note(self, what: dict[str, Any]) -> None:
        self._marker().write_text(json.dumps(what), encoding="utf-8")

    async def check_pending(self, *, stale_after: float = 1800.0) -> None:
        """After a start: did the update this service began (before it was stopped) leave it on the new version? Said once, then forgotten."""
        if self.config is None or not self._marker().is_file():
            return
        try:
            note = json.loads(self._marker().read_text(encoding="utf-8"))
        except (OSError, ValueError):
            self._marker().unlink(missing_ok=True)
            return
        version = str(note.get("version") or "")
        done = version == self.running_version
        if not done and time.time() - float(note.get("started") or 0) < stale_after:
            return                                            # (still installing, or about to be stopped for it)
        payload: dict[str, Any] = {"version": version, "succeeded": done, "running": self.running_version}
        if not done:
            tail = ""
            try:
                tail = Path(str(note.get("log"))).read_text(encoding="utf-8", errors="replace").strip().splitlines()[-1]
            except (OSError, IndexError):
                pass
            payload["error"] = (tail or "The installer did not finish")[:160]
        try:
            await self.report("updates.report_status", payload)
        except Exception as exc:  # noqa: BLE001
            log.warning("could not report how the update went: %s", exc)
            return
        self._marker().unlink(missing_ok=True)
        if done:
            self.pending = None

    def _apply(self, version: str) -> bool:
        self.last_error = None
        if not self.update_command:
            log.warning("no update_command configured; update to %s cannot be applied on this PC", version)
            self.last_error = "No way to update has been set up on this machine"
            return False
        argv = [a.replace("{version}", version) for a in shlex.split(self.update_command)]
        try:
            result = subprocess.run(argv, check=False, timeout=600, capture_output=True)
        except (OSError, subprocess.TimeoutExpired) as exc:
            log.warning("update command failed: %s", exc)
            self.last_error = "The update took too long" if isinstance(exc, subprocess.TimeoutExpired) else f"The update could not start ({exc.__class__.__name__})"
            return False
        if result.returncode != 0:
            log.warning("update command exited %s: %s", result.returncode, result.stderr[-500:])
            tail = result.stderr.decode("utf-8", "replace").strip().splitlines()
            self.last_error = (tail[-1][:160] if tail else f"The update stopped with code {result.returncode}")
            return False
        return True
