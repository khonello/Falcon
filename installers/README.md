# Installers

The code behind the four installers (decided in `docs/PACKAGING-PLAN.md`). It is written and tested; it is **not compiled into executables
yet** (see "Still to do"). Nothing here is run by the Engine or the clients.

| Machine | Command | Where |
|---|---|---|
| The server | `sudo python3 -m installers.engine.install --names falcon.internal,192.168.1.20 --hostname IT-01` | Linux, once |
| A person's PC | `python -m installers.windows.install --role worker --bundle falcon-client.json` | Windows, as administrator |
| The first IT Admin's workstation | `... --role admin --bundle falcon-client.json --client-id <id> --client-key-file key.txt` | Windows, as administrator |
| Another IT Admin's workstation | `... --role admin --bundle falcon-client.json` | Windows, as administrator |

Each is run from a **payload folder**: `python -m installers.payload <role> <folder> [--wheels <folder>]` assembles the role's packages (and
only those), the libraries it needs (read from `pyproject.toml`), this installer, and a `manifest.json` of the SHA-256 of every file. Every
installer checks the manifest first and refuses a payload that was changed or half-copied. A payload never carries a secret (`.env`,
`master.secret`, `engine.key`, a settings file with a key), a test, or a cache: the builder refuses.

## The order

1. **The Engine's installer, on the server.** It makes the `falcon` user and folders, the runtime, a PostgreSQL role with a made-up password, the
   settings (`/etc/falcon/falcon.env`), runs `python -m engine setup` (certificate for `--names`, schema, master secret, the first IT Admin, the
   firewall), and installs the systemd service. It writes **`falcon-client.json`**, the bundle every PC is given: the Engine's address and its
   certificate, **no key**, and prints the certificate's **fingerprint**. The first IT Admin's id and key are in
   `/var/lib/falcon/first-admin.txt` (root only). Back up `/var/lib/falcon/master.secret` offline.
2. **The first IT Admin's workstation.** `--role admin` with the id and key from step 1: the console, and the person's own settings.
**With a licence code (2 Nov 2026):** every installer takes `--code` (or `--code-file`; `setup.exe` asks for it on a page of its own). An admin
code with the admin installer, a worker code with the worker one: the machine joins the Engine at once, as what the code is for, and nobody
confirms it. The code is kept only in the machine's private settings until it is used, then dropped. Without one, the steps below.

3. **Another IT Admin's workstation.** `--role admin`. The installed service asks the Engine to register the machine as an Admin's
   workstation and a code appears on the screen. Making a person an Admin is never one click in the console (docs/design/v1-it-admin.md):
   it is finished from the TUI or a setup utility, and those steps are still to be designed. The console on that machine is signed in by the service.
4. **A person's PC.** `--role worker`. The same, as a worker; the department's Admin confirms the code.

Compare `--fingerprint` (what the Engine's installer printed, read out or sent another way) on every installer: it refuses a bundle whose
certificate is not that one.

## What a Windows machine ends up with

```
C:\Program Files\Falcon\app\          the code (only this role's packages)
C:\Program Files\Falcon\runtime\      its own Python and libraries (the payload's wheels: no network needed)
C:\Program Files\Falcon\install.json  the receipt the uninstall reads
C:\ProgramData\Falcon\engine.crt      the Engine's certificate   (anyone may read: it is public)
C:\ProgramData\Falcon\console.json    the Engine's address, who signs the console in   (public; no key)
C:\ProgramData\Falcon\private\        only the system and administrators:
    worker.json                       this machine's settings and, once registered, its key
    worker.log
service FalconWorker                  starts with Windows, restarts itself; its indexer and event tracker are their own programs
Start menu > Falcon > Falcon Console  (IT Admins)
```

The key never reaches a person: on an Admin's workstation the console asks the service (a named pipe open to signed-in users only) to answer the
Engine's challenge (`common/signpipe.py`), so the key stays in the closed folder.

Run it again to repair or upgrade: every step checks what is there first, keeps the key a machine was given, and removes the files of the old
version. `--uninstall` removes the service, the shortcut and the program, and **keeps** the settings and key unless `--purge-data`
(without its key a machine must be registered again). `--dry-run` lists the steps and changes nothing.

## The Linux package

`sh installers/engine/build_deb.sh [out] [wheels]` builds `falcon-engine_<version>_all.deb` (needs `dpkg-deb`): the Engine's payload under
`/opt/falcon/payload` and the command `falcon-engine-install`. A first install says what to run; installing a newer package upgrades in place
with the same settings. Removing the package never deletes `/var/lib/falcon` (the master secret), `/etc/falcon` or the database.

## Tested

`tests/test_installers.py`: what each role carries and never carries; a changed payload, a swapped bundle, a wrong Engine and a wrong role are each
refused; the Engine's settings and unit; the Windows route into temporary folders for each role (settings, the first IT Admin's own file, keeping a
key on upgrade, no leftover files, uninstall keeps the key); and, from an elevated prompt, the real thing: an Admin workstation installed as a
service, which asks to be registered, is confirmed with the code it logs, is handed its key into a folder only the system and
administrators can read, comes online, and its keyless console is signed in by the service. `tests/test_signpipe.py`, `tests/test_enrollment.py`
cover the pipe and the first-start registration. **Run for real on Linux (WSL Ubuntu, throwaway names, then removed):** the Engine's installer, all ten steps, twice: the user and folders, the
runtime from the payload's requirements, a PostgreSQL role and database with a made password, the certificate, schema, master secret and first account, the bundle and
its fingerprint, and a systemd service answering as the `falcon` user; the secret and key are `600` and the settings `640 root:falcon`; a Windows client then connected to
it over TLS pinned to the bundle's certificate with the first account's key, and a wrong certificate was refused; the second run kept the password, the secret and the
first account and issued nothing new. **Not run for real yet:** the Windows installer's own runtime venv with real wheels (the VM) and the `.deb` build (`dpkg-deb`).

## setup.exe (built 1 Nov 2026)

`python -m installers.windows.build_setup worker --python <folder> --bundle falcon-client.json --out <short folder>` makes
`falcon-worker-setup.exe` (93 MB): the payload, the role's libraries as wheels (no network at install), and Python. The Python is
python.org's full Windows layout, the `tools` folder of its NuGet package (`https://www.nuget.org/api/v2/package/python/3.10.11`; decided
by the user, 1 Nov 2026). It is installed under the program (`<target>\python`), because the runtime is a venv made from it. Build into a
short path (`C:b\dist`): a deep one passes Windows' 260-character limit and Inno Setup says "cannot find the path". One setup.exe is
made per Engine, since it carries that Engine's bundle. Needs Inno Setup 6. The admin role waits for the console (the user, 1 Nov 2026).
**Not run for real yet:** installing it (an elevated `falcon-worker-setup.exe /VERYSILENT /DIR=...`), then uninstalling from Apps.

## Still to do (final packaging; on hold)

- Freezing the helper windows (they run from the bundled Python today).
- Signing the executables and the packages.
- The update pipeline (a new payload to a machine that already has the service).
