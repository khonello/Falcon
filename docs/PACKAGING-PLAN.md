# Packaging plan (agreed 13 Oct 2026; the installers' code is written and tested in `installers/` (see its README); compiling it into executables stays on hold)

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

## Decided 13 Oct 2026

- **The event tracker is its own supervised process.** The service starts it, restarts it if it dies, and reports it
  unhealthy if it keeps dying. (It already sits behind its own module.)
- **Machines register by probation.** An installer carries only the Engine's host and its certificate (or fingerprint);
  the machine connects and announces itself (PC name, account, level) and waits. This is `enroll.request / wait / list /
  confirm / refuse`, designed in `design/ENGINE-WORK.md` item 15 ("Waiting to be registered"). Rules:
  1. What a machine announces is a **claim**. It grants nothing; the approver sets the role. A claim of "Super User" is
     worth no more than any other.
  2. The approver types the **pairing code** shown on that PC's screen, so an impostor naming itself "FIN-02" cannot be
     approved by mistake.
  3. The installer carries the certificate (or its fingerprint) too, so the first connect cannot be answered by a fake
     Engine. Every installer carries the same two things; nothing is per-machine.
  4. After approval the key goes once, over the pinned connection, to the waiting connection, and is stored with
     restricted rights. Nothing is typed or copied by hand.
  5. Who approves: an Admin for worker PCs of their department; the Super User for Admin and Super User workstations; a
     command on the Engine host as the fallback and for first setup (the TUI's `enroll` commands).
  6. The probation list is reachable by anyone on the network: rate-limit requests, expire old ones, and raise a flag
     for a machine that keeps asking.

## Still to decide when packaging starts

- Bundled interpreter, signing, frozen helper windows, update pipeline (`ENGINE-GAPS.md`, `PHASES.md` Phase 9).
- What the pairing code looks like on a PC with nobody signed in (a service machine at the login screen).
