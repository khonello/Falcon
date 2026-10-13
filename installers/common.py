"""Steps that can be listed before they are run, and run one at a time with each result said.

An installer builds a `Plan`: an ordered list of `Step`s, each a plain function that does one thing and returns a line saying what it did
(or None). `plan.run(dry_run=True)` only lists them, touching nothing; a real run stops at the first step that fails and says which, so
running the installer again picks up where it stopped (every step checks what is already there before it changes anything).
"""

from __future__ import annotations

import hashlib
import ssl
import subprocess
import sys
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path


class InstallError(RuntimeError):
    """A step could not do its job; the message says what to fix."""


@dataclass
class Step:
    name: str
    run: Callable[[], str | None]
    why: str = ""                          # one line, shown in the listing
    skip: str | None = None                # set when this run does not need the step ("--no-service")


@dataclass
class Plan:
    title: str
    steps: list[Step] = field(default_factory=list)
    say: Callable[[str], None] = print

    def add(self, name: str, run: Callable[[], str | None], why: str = "", skip: str | None = None) -> None:
        self.steps.append(Step(name, run, why, skip))

    def run(self, dry_run: bool = False) -> list[tuple[str, str]]:
        """[(step, what happened)]. Raises InstallError at the first step that fails."""
        self.say(f"{self.title}{'  (dry run: nothing is changed)' if dry_run else ''}")
        done: list[tuple[str, str]] = []
        for n, step in enumerate(self.steps, 1):
            label = f"[{n}/{len(self.steps)}] {step.name}"
            if step.skip:
                self.say(f"{label}: skipped ({step.skip})")
                done.append((step.name, f"skipped: {step.skip}"))
                continue
            if dry_run:
                self.say(f"{label}: {step.why}" if step.why else label)
                done.append((step.name, "would run"))
                continue
            try:
                result = step.run() or "done"
            except InstallError:
                raise
            except Exception as exc:
                raise InstallError(f"{step.name} failed: {exc}") from exc
            self.say(f"{label}: {result}")
            done.append((step.name, result))
        return done


def run_cmd(argv: list[str], *, check: bool = True, input_text: str | None = None, env: dict[str, str] | None = None,
            cwd: str | Path | None = None) -> tuple[int, str]:
    """Run a program, return (exit code, its output). With `check`, a failure raises InstallError carrying the output."""
    proc = subprocess.run(argv, input=input_text, capture_output=True, text=True, env=env, cwd=str(cwd) if cwd else None, check=False)
    out = (proc.stdout or "") + (proc.stderr or "")
    if check and proc.returncode != 0:
        raise InstallError(f"`{' '.join(argv[:3])} ...` exited {proc.returncode}: {out.strip()[-600:]}")
    return proc.returncode, out


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def cert_fingerprint(pem: str) -> str:
    """SHA-256 of a certificate's DER form, as the colon-separated hex a person can read out and compare."""
    der = ssl.PEM_cert_to_DER_cert(pem.strip())
    digest = hashlib.sha256(der).hexdigest().upper()
    return ":".join(digest[i:i + 2] for i in range(0, len(digest), 2))


def python_ok(minimum: tuple[int, int] = (3, 10)) -> str | None:
    """None when this Python is new enough, else what to do about it."""
    if sys.version_info[:2] < minimum:
        return f"Python {minimum[0]}.{minimum[1]} or newer is needed (this is {sys.version_info.major}.{sys.version_info.minor})"
    return None


def write_text(path: Path, text: str, mode: int | None = None) -> bool:
    """Write a file; False (and no write) when it already holds exactly this."""
    if path.exists() and path.read_text(encoding="utf-8") == text:
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    if mode is not None:
        path.chmod(mode)
    return True
