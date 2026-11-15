"""Build one setup.exe for a role: the payload, its libraries as wheels (so the install needs no network), a Python, and Inno Setup.

    python -m installers.windows.build_setup worker --python <folder> [--out dist] [--iscc ISCC.exe] [--no-wheels]
    python -m installers.windows.build_setup admin --python <folder> [--store https://<store>] [--out dist]
    python -m installers.windows.build_setup engine --python <folder> --pgsql <EDB pgsql folder> [--store https://<store>] [--out dist]

--python is python.org's full Windows layout (the `tools` folder of its NuGet package, https://www.nuget.org/packages/python): it goes
into the setup and is installed under the program, and the runtime venv is made from it. Its version is the Python the wheels are fetched
for, so they match. A setup carries no Engine and is the same for every customer (docs/SEATS-AND-SETUP.md): a Worker's is told where its
Engine is by the store-signed company file beside it; an Admin's signs in to the store (--store, or common/store_keys.STORE_URL) and learns it
there. The Engine's carries Falcon's own PostgreSQL: --pgsql is the `pgsql` folder of EnterpriseDB's Windows binaries zip
(https://www.enterprisedb.com/download-postgresql-binaries), trimmed here to what a running Engine needs (installers/windows/private_pg.py).
What it writes: <out>/falcon-<role>-setup.exe, and the payload beside it.

Run on Windows from the repository root. The admin role carries the console; build it when the console is ready (the user, 1 Nov 2026).
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

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


def build(role: str, python_dir: Path, out: Path, *, store: str | None = None, pgsql: Path | None = None, iscc: Path = ISCC,
          wheels: bool = True) -> Path:
    """One setup for every customer: nothing in it names an Engine."""
    from common.store_keys import STORE_URL

    python = python_dir / "python.exe"
    if not python.is_file():
        raise InstallError(f"{python_dir} has no python.exe: give the tools folder of python.org's NuGet package")
    store = store or STORE_URL
    if role in ("admin", "engine") and not store.startswith(("https://", "http://127.0.0.1", "http://localhost")):
        raise InstallError(f"the {role.title()} setup signs in to the store: give its address (--store https://...)")
    if role == "engine" and (pgsql is None or not (pgsql / "bin" / "postgres.exe").is_file()):
        raise InstallError("the Engine setup carries Falcon's own PostgreSQL: --pgsql <the pgsql folder of the EDB Windows binaries>")
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
    if role == "engine":
        from installers.windows.private_pg import trim

        assert pgsql is not None
        pg = out / "pgsql"
        print(f"PostgreSQL trimmed to {trim(pgsql, pg) >> 20} MB")
        cmd = [str(iscc), f"/DPayload={payload}", f"/DPython={python_dir.resolve()}", f"/DPgSql={pg.resolve()}", f"/DStore={store}",
               f"/DVersion={payload_mod.project_version()}", f"/O{out.resolve()}", "/Q", str(REPO / "installers" / "windows" / "falcon-engine.iss")]
    else:
        extra = [f"/DStore={store}"] if role == "admin" else []
        cmd = [str(iscc), f"/DRole={role}", f"/DPayload={payload}", *extra, f"/DPython={python_dir.resolve()}",
               f"/DVersion={payload_mod.project_version()}", f"/O{out.resolve()}", "/Q", str(REPO / "installers" / "windows" / "falcon.iss")]
    subprocess.run(cmd, check=True)
    made = out / f"falcon-{role}-setup.exe"
    print(f"built {made} ({made.stat().st_size >> 20} MB)")
    return made


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="installers.windows.build_setup", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("role", choices=("worker", "admin", "engine"))
    ap.add_argument("--python", required=True, type=Path, help="python.org's full Windows layout (the NuGet package's tools folder)")
    ap.add_argument("--store", help="the store's address, for the admin and engine roles (default: common/store_keys.STORE_URL)")
    ap.add_argument("--pgsql", type=Path, help="engine: the pgsql folder of EnterpriseDB's PostgreSQL Windows binaries")
    ap.add_argument("--out", type=Path, default=Path("dist"))
    ap.add_argument("--iscc", type=Path, default=ISCC)
    ap.add_argument("--no-wheels", action="store_true", help="the install fetches the libraries itself (needs the network)")
    a = ap.parse_args(argv)
    try:
        build(a.role, a.python, a.out, store=a.store, pgsql=a.pgsql, iscc=a.iscc, wheels=not a.no_wheels)
    except (InstallError, subprocess.CalledProcessError) as exc:
        print(f"Not built: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
