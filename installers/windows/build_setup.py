"""Build one setup.exe for a role: the payload, its libraries as wheels (so the install needs no network), a Python, and Inno Setup.

    python -m installers.windows.build_setup worker --python <folder> --bundle falcon-client.json [--out dist] [--iscc ISCC.exe] [--no-wheels]

--python is python.org's full Windows layout (the `tools` folder of its NuGet package, https://www.nuget.org/packages/python): it goes
into the setup and is installed under the program, and the runtime venv is made from it. Its version is the Python the wheels are fetched
for, so they match. --bundle is the Engine's falcon-client.json (its address and certificate, no key), written by the Engine's installer:
a setup.exe is made for one Engine. What it writes: <out>/falcon-<role>-setup.exe, and the payload beside it.

Run on Windows from the repository root. The admin role carries the console; build it when the console is ready (the user, 1 Nov 2026).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from installers import bundle as bundle_mod
from installers import payload as payload_mod
from installers.common import InstallError

REPO = Path(__file__).resolve().parent.parent.parent
ISCC = Path(r"C:\Program Files (x86)\Inno Setup 6\ISCC.exe")


def python_version(python: Path) -> str:
    out = subprocess.run([str(python), "-I", "-c", "import sys; print('%d.%d.%d' % sys.version_info[:3])"],
                         capture_output=True, text=True, check=True)
    return out.stdout.strip()


def fetch_wheels(python: Path, requirements: str, dest: Path) -> int:
    """The role's libraries as wheels for this Python and Windows, fetched by that Python's own pip (binary only: nothing is built on a PC)."""
    dest.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory() as tmp:
        req = Path(tmp) / "requirements.txt"
        req.write_text(requirements, encoding="utf-8")
        subprocess.run([str(python), "-I", "-m", "pip", "download", "--disable-pip-version-check", "--only-binary=:all:",
                        "-r", str(req), "-d", str(dest)], check=True)
    return len(list(dest.glob("*.whl")))


def build(role: str, python_dir: Path, bundle_path: Path, out: Path, *, iscc: Path = ISCC, wheels: bool = True) -> Path:
    python = python_dir / "python.exe"
    if not python.is_file():
        raise InstallError(f"{python_dir} has no python.exe: give the tools folder of python.org's NuGet package")
    bundle_mod.load(bundle_path)                                   # refuses anything that is not a whole bundle
    if not iscc.is_file():
        raise InstallError(f"Inno Setup's compiler is not at {iscc} (--iscc)")
    out.mkdir(parents=True, exist_ok=True)
    payload = out / f"falcon-{role}"
    if payload.exists():
        shutil.rmtree(payload)
    with tempfile.TemporaryDirectory() as tmp:
        wheel_dir = None
        if wheels:
            wheel_dir = Path(tmp) / "wheels"
            n = fetch_wheels(python, payload_mod.requirements_for(role), wheel_dir)
            print(f"{n} wheels for Python {python_version(python)}")
        payload_mod.build(role, payload, wheels=wheel_dir)
    problems = payload_mod.verify(payload)
    if problems:
        raise InstallError("the payload is not whole: " + "; ".join(problems[:5]))
    subprocess.run([str(iscc), f"/DRole={role}", f"/DPayload={payload}", f"/DBundle={bundle_path.resolve()}", f"/DPython={python_dir.resolve()}",
                    f"/DVersion={payload_mod.project_version()}", f"/O{out.resolve()}", "/Q", str(REPO / "installers" / "windows" / "falcon.iss")],
                   check=True)
    made = out / f"falcon-{role}-setup.exe"
    print(f"built {made} ({made.stat().st_size >> 20} MB)")
    return made


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="installers.windows.build_setup", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("role", choices=("worker", "admin"))
    ap.add_argument("--python", required=True, type=Path, help="python.org's full Windows layout (the NuGet package's tools folder)")
    ap.add_argument("--bundle", required=True, type=Path, help="the Engine's falcon-client.json")
    ap.add_argument("--out", type=Path, default=Path("dist"))
    ap.add_argument("--iscc", type=Path, default=ISCC)
    ap.add_argument("--no-wheels", action="store_true", help="the install fetches the libraries itself (needs the network)")
    a = ap.parse_args(argv)
    try:
        build(a.role, a.python, a.bundle, a.out, iscc=a.iscc, wheels=not a.no_wheels)
    except (InstallError, subprocess.CalledProcessError) as exc:
        print(f"Not built: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
