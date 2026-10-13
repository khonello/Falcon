"""What each installer contains. One table; the payload builder and the installers both read it, so they cannot drift apart.

`packages` are the Python packages copied onto the machine; `extras` the pyproject.toml groups of libraries the runtime needs;
`service` whether the Worker service is installed; `console` whether the Operator Client is. Nothing here ever contains the Engine's
key, the master secret, a database, a test or a development setting: `payload.py` refuses to copy them.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class Role:
    name: str
    title: str
    packages: tuple[str, ...]
    extras: tuple[str, ...]                # the pyproject.toml extras whose libraries the runtime needs
    service: bool = False
    console: bool = False
    enroll_level: str | None = None        # what the machine asks to be registered as (None: it is given its key another way)
    serve_console: bool = False            # the console on this machine is signed in by the service (the key stays with the service)
    platform: str = "windows"


ROLES: dict[str, Role] = {
    "worker": Role("worker", "A person's PC", ("common", "protocol", "worker_client"), ("worker", "worker-ui"),
                   service=True, enroll_level="worker"),
    "admin": Role("admin", "An Admin's workstation", ("common", "protocol", "worker_client", "operator_client"),
                  ("worker", "worker-ui", "tui", "gui"), service=True, console=True, enroll_level="admin",
                  serve_console=True),
    # The Super User's own PC runs the console only: its account is made by the Engine's setup and its key is placed once. Whether that PC
    # is also a machine the hierarchy manages is an open question (installers/README.md).
    "superuser": Role("superuser", "The Super User's PC", ("common", "protocol", "operator_client"), ("tui", "gui"),
                      console=True),
    "engine": Role("engine", "The Engine (Linux)", ("common", "protocol", "engine"), ("engine",), platform="linux"),
}

# never copied into any payload, whatever a package happens to contain
FORBIDDEN_NAMES = frozenset({".env", "master.secret", "engine.key", "operator.json", "worker.json", "admin.json"})
FORBIDDEN_SUFFIXES = (".key", ".pem", ".pyc", ".pyo", ".log", ".db", ".sqlite")
SKIP_DIRS = frozenset({"__pycache__", "tests", ".git", "environ-engine", "environ-operator", "environ-worker", "data", "models",
                       ".pytest_cache", ".ruff_cache"})


def role(name: str) -> Role:
    try:
        return ROLES[name]
    except KeyError:
        raise SystemExit(f"unknown role {name!r}: one of {', '.join(ROLES)}") from None
