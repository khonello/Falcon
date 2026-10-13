"""A role's files, assembled into one folder an installer can carry: the code, what the runtime needs, and a manifest of hashes.

    python -m installers.payload worker out\\falcon-worker [--wheels wheels\\]
    python -m installers.payload verify out\\falcon-worker

    out/
      app/<package>/...          only the packages this role needs (installers.roles), no tests, no caches, no secrets
      requirements.txt           the libraries the role's extras name in pyproject.toml, plain (no editable install)
      wheels/                    optional: those libraries as wheels, so the install needs no network
      installers/                the installer itself
      manifest.json              {role, version, files: {path: sha256}} -- checked before anything is installed

`verify` is run by every installer first: a payload that was altered or half-copied is refused, naming the files.
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

from installers.common import InstallError, sha256_file
from installers.roles import FORBIDDEN_NAMES, FORBIDDEN_SUFFIXES, ROLES, SKIP_DIRS, role

REPO = Path(__file__).resolve().parent.parent
LLAMA_INDEX = "https://abetlen.github.io/llama-cpp-python/whl/cpu"


def project_version(repo: Path = REPO) -> str:
    m = re.search(r'^version\s*=\s*"([^"]+)"', (repo / "pyproject.toml").read_text(encoding="utf-8"), re.MULTILINE)
    return m.group(1) if m else "0.0.0"


def extras_of(repo: Path = REPO) -> dict[str, list[str]]:
    """The `[project.optional-dependencies]` groups of pyproject.toml, read plainly (tomllib arrives only in Python 3.11)."""
    text = (repo / "pyproject.toml").read_text(encoding="utf-8")
    block = text.split("[project.optional-dependencies]", 1)[1].split("\n[", 1)[0]
    out: dict[str, list[str]] = {}
    for m in re.finditer(r"^([A-Za-z0-9_-]+)\s*=\s*\[(.*?)\]", block, re.MULTILINE | re.DOTALL):
        out[m.group(1)] = re.findall(r'"([^"]+)"', re.sub(r"#[^\n]*", "", m.group(2)))
    return out


def requirements_for(role_name: str, repo: Path = REPO) -> str:
    r = role(role_name)
    groups = extras_of(repo)
    wanted: list[str] = []
    for extra in r.extras:
        if extra not in groups:
            raise InstallError(f"pyproject.toml has no extra named {extra!r}")
        wanted += [d for d in groups[extra] if d not in wanted]
    lines = [f"# the libraries the {r.title} needs (pyproject.toml extras: {', '.join(r.extras)})"]
    if any(d.startswith("llama-cpp-python") for d in wanted):
        lines.append(f"--extra-index-url {LLAMA_INDEX}")
    return "\n".join(lines + wanted) + "\n"


def _wanted(path: Path) -> bool:
    return (path.name not in FORBIDDEN_NAMES and not path.name.endswith(FORBIDDEN_SUFFIXES)
            and not any(part in SKIP_DIRS for part in path.parts))


def _copy_tree(src: Path, dst: Path) -> int:
    n = 0
    for f in sorted(src.rglob("*")):
        rel = f.relative_to(src)
        if f.is_dir() or not _wanted(rel):
            continue
        target = dst / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(f, target)
        n += 1
    return n


def build(role_name: str, out: Path, *, repo: Path = REPO, wheels: Path | None = None) -> dict:
    r = role(role_name)
    if out.exists() and any(out.iterdir()):
        raise InstallError(f"{out} is not empty; the payload is built into a fresh folder")
    for pkg in r.packages:
        if not (repo / pkg).is_dir():
            raise InstallError(f"the package {pkg!r} is not in {repo}")
        _copy_tree(repo / pkg, out / "app" / pkg)
    _copy_tree(repo / "installers", out / "installers")
    (out / "requirements.txt").write_text(requirements_for(role_name, repo), encoding="utf-8")
    if wheels is not None:
        shutil.copytree(wheels, out / "wheels")
    manifest = {"role": r.name, "version": project_version(repo),
                "files": {str(p.relative_to(out)).replace("\\", "/"): sha256_file(p)
                          for p in sorted(out.rglob("*")) if p.is_file() and p.name != "manifest.json"}}
    leaked = [f for f in manifest["files"] if not _wanted(Path(f)) and not f.endswith(".whl")]
    if leaked:
        raise InstallError(f"refusing to build a payload with {', '.join(leaked)}")
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


def verify(payload: Path) -> list[str]:
    """What is wrong with a payload folder (an empty list: nothing)."""
    try:
        manifest = json.loads((payload / "manifest.json").read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return ["manifest.json is missing or unreadable"]
    problems = []
    if manifest.get("role") not in ROLES:
        problems.append(f"manifest names an unknown role {manifest.get('role')!r}")
    for rel, digest in manifest.get("files", {}).items():
        f = payload / rel
        if not f.is_file():
            problems.append(f"missing: {rel}")
        elif sha256_file(f) != digest:
            problems.append(f"changed: {rel}")
    listed = set(manifest.get("files", {}))
    for f in payload.rglob("*"):
        rel = str(f.relative_to(payload)).replace("\\", "/")
        if "__pycache__" in f.parts or f.suffix in (".pyc", ".pyo"):
            continue                                      # Python writes these itself the first time it runs the installer from here
        if f.is_file() and rel != "manifest.json" and rel not in listed:
            problems.append(f"not in the manifest: {rel}")
    return problems


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(prog="installers.payload", description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("what", help="a role (worker, admin, superuser, engine) to build, or `verify`")
    ap.add_argument("folder", type=Path)
    ap.add_argument("--wheels", type=Path, help="a folder of wheels for the role's libraries (so the install needs no network)")
    args = ap.parse_args(argv)
    if args.what == "verify":
        problems = verify(args.folder)
        print("\n".join(problems) if problems else "payload is intact")
        return 1 if problems else 0
    manifest = build(args.what, args.folder, wheels=args.wheels)
    print(f"{args.what} payload {manifest['version']}: {len(manifest['files'])} files in {args.folder}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
