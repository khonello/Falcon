"""The installers' code (not compiled into executables yet): what goes on each kind of machine, and the steps that put it there.

    roles.py     what each installer contains: packages, requirements, services
    payload.py   assemble a role's files into a folder with a manifest (sha256 of every file), and verify one
    bundle.py    the client bundle: the Engine's host and certificate, carried by every Windows installer
    common.py    steps that can be listed (dry run), run, and reported; small helpers
    engine/      Linux: the Engine on one server (user, directories, runtime, database, certificate, systemd, firewall)
    windows/     Windows: the Worker and an IT Admin's workstation

See installers/README.md. Named `installers`, not `packaging`: `packaging` is a library the test tools import.
"""

import sys as _sys
from pathlib import Path as _Path

# Run from a payload (`<payload>/installers` beside `<payload>/app`), the installers reach the code packages they use (`common`: the store's
# signatures, the machine's identity) from the payload's app folder. Appended, so a checkout's own packages always win.
_app = _Path(__file__).resolve().parent.parent / "app"
if (_app / "common").is_dir() and str(_app) not in _sys.path:
    _sys.path.append(str(_app))
