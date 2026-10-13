# Packaging plan (agreed 13 Oct 2026; the building itself stays on hold)

What is installed where, and how it is split. Final packaging (Phase 9) starts only when the user gives the green flag;
the small part already built is `python -m worker_client service install|start|stop|uninstall|status`.

## The rule for splitting

Split by **where the code must run and with what rights**, not by feature.

- **Session boundary (Windows).** The service lives in session 0 with no desktop. Overlays, dialogs, screen capture and
  input injection run in the signed-in person's session, started by the service (`WTSQueryUserToken` +
  `CreateProcessAsUserW`). Already built as the helper.
- **Privilege.** The event tracker needs the system account; overlays need nothing.
- **Isolation.** The indexer scans disks: its own process, low priority, so it cannot take the connection down.
- **Not one program per feature.** Every PySide6 program carries its own Qt (100 MB+): blocked / viewing / dialog / task
  are windows of **one** UI helper. One network identity per machine: only the service holds the Engine connection and
  key; everything else talks to it over a local pipe and has no credentials.

## What runs on a Windows machine

| Piece | Runs as | Started by | Does |
|---|---|---|---|
| Worker service | system account | Windows, at boot | the Engine connection and key, event tracker (ETW), actions, updates |
| Indexer | system account, low priority | the service | file index sweep and watching; own crash boundary |
| UI helper (one program) | the signed-in person | the service, on demand | overlays (blocked, viewing, dialog, task), screen capture, input |
| Console | the person using it | the person | the Super User's and the Admin's interface (the account's role decides what it shows) |

## The four installers

| Machine | Installer | Contents |
|---|---|---|
| A person's PC | **Worker** | service, indexer, UI helper |
| An Admin's PC | **Admin** | console + the Worker pieces (an Admin's workstation is a machine the hierarchy can enter or block) |
| The Super User's PC | **Super User** | console + the Worker pieces (its occupant is unevictable) |
| The server | **Engine** (Linux) | the Engine, PostgreSQL setup, model, systemd unit; a `.deb` first |

- Each is run once by someone with administrator rights on that machine. Nobody installs pieces one by one; the
  privilege split happens at run time.
- **Levels are not separate builds.** The same Worker pieces go everywhere; the Engine switches features on per role,
  department or account (e.g. the indexer runs only where the Resource tiers need it). The Engine enforces access, so
  per-level builds would add installers and no protection.
- **The Engine installer is separate and comes first.** Different system (Linux), different owner (once, on one server),
  different contents, and `master.secret` / `engine.key` must never be on any PC. Its first run produces what the others
  need: `engine.crt` (every PC trusts it) and the first Super User's id and key.
- The Engine package wraps `python -m engine setup` (database, schema, certificate, master secret, first Super User,
  firewall step) and adds the service unit.

## Still to decide when packaging starts

- Whether the event tracker also becomes its own supervised process (today it is inside the service).
- How a machine gets its own id and key at install: typed, a file next to the installer, or the pairing code in
  `design/ENGINE-WORK.md` item 15.
- Bundled interpreter, signing, frozen helper windows, certificate and key delivery, update pipeline (all in
  `ENGINE-GAPS.md` and `PHASES.md` Phase 9).
