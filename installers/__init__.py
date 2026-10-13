"""The installers' code (not compiled into executables yet): what goes on each kind of machine, and the steps that put it there.

    roles.py     what each installer contains: packages, requirements, services
    payload.py   assemble a role's files into a folder with a manifest (sha256 of every file), and verify one
    bundle.py    the client bundle: the Engine's host and certificate, carried by every Windows installer
    common.py    steps that can be listed (dry run), run, and reported; small helpers
    engine/      Linux: the Engine on one server (user, directories, runtime, database, certificate, systemd, firewall)
    windows/     Windows: the Worker, an Admin's workstation, the Super User's console

See installers/README.md. Named `installers`, not `packaging`: `packaging` is a library the test tools import.
"""
