# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**The new product** (its name is not chosen yet: work under the codename the user gives; see `docs/next-product/START-HERE.md`), forked
from Falcon on 15 Nov 2026 with its full history. Falcon itself is parked in its own repository (github.com/khonello/Falcon, tag
`falcon-parked-2026-11-15`). **Start every session at `docs/next-product/START-HERE.md`**: what the product is, what was decided, what is
next. Then `docs/to-lookat.md`: raise its open items with the user.

One product for IT Admins: it watches what happens to a company's files on its Windows machines and puts it together as cases told in plain
words, prioritising what the company marked as restricted. **One product, not features under an umbrella** (the user, 15 Nov 2026):
the cases (Falcon's "Detective") and what matters (Falcon's "Restricted") are one job in one product; neither is a page of its own.

Older text in this repository describes Falcon (Super User → Department → Admin → Client PC, Task, Flow, Automation). It is history: Task,
Flow, Automation / Custom Actions and Assistance are not part of this product, and are taken out in reviewed steps.

## Rules from the user

- **Never use Docker.** PostgreSQL 18 is installed locally (service `postgresql-x64-18`). This product has its own databases, not Falcon's
  (`falcon`, `falcon_test*`); tests wipe and re-migrate their test database, so never point tests at a working one, and a session on another
  branch gets its own test database.
- **The user creates the virtual environments**, one per package, all git-ignored (`environ-engine/`, `environ-operator/`, `environ-worker/`).
  Work from them; never create or recreate venvs.
- **Ask before any download or new dependency**: say what and how big, and wait for a yes.
- **Commit as you work**: each finished, tested piece as it lands, only your own files (`git commit --only`). **Pushing needs asking.**
  Check `grep -l gsk_` before committing: the Groq key lives only in the git-ignored `.env`, never in the repository, commits, installers or docs.
  Tests never reach Groq (`FALCON_GROQ_API_KEY=` blank).
- **Don't wait for approval on obvious steps** of agreed work; ask only for real decisions, and check a problem before raising it as one.
- **Run the full suite in batches** (`scripts/test_batches.py --skip-gui`), one pytest process at a time, never one big run (it ran out of
  memory); never run database tests beside it on the same test database. Timing tests can fail under load: rerun them alone before calling
  them real.
- **Deployment is Windows** (the Engine, the Admins, the Workers), and the Engine also runs on Linux (most servers do): its core stays
  platform-neutral, and what is per platform is kept apart and never made to serve both (Windows: `engine/winservice.py`,
  `installers/windows/`; Linux: `installers/engine/`). Both are tested for real.
- **Engine and UI are separate sessions.** An Engine session never touches QML or pages; UI needs go to `docs/UI-WORK-FROM-ENGINE.md`. A UI
  session does not change the Engine without telling the user first.
- **The UI is built concept first**: a concept design made for this product (Falcon's GUI is not carried over), approved by the user, then
  QML built to it page by page; when the concept and anything else disagree, the concept wins. Where the Engine cannot do what a page shows,
  the control is drawn disabled with the reason, never faked. The QML stays a thin layer over `FalconBridge`.
- **The TUI is the scripted test surface**: a new feature lands as an Engine handler + TUI command first (`--script`), then a GUI view.
  Power settings live in the TUI only.
- **The company chooses its features**: evidence such as screenshots and camera pictures is a choice the company turns on; no legal gates,
  no lectures; state the technical facts and list every collection in the deployment guide and the staff notice.
- The user's machine has an OpenAI Codex config (`~/.codex/`): unrelated, ignore it.

## Commands

The pyenv-win shim on PATH (`python.bat`) corrupts inline `python -c "..."`: use the venv's `python.exe` directly or run scripts from files.
Settings live in `.env`, never in the shell (`common/dotenv.py`); a variable set in the real environment still wins.

```powershell
environ-engine\Scripts\Activate.ps1
pip install -r requirements-engine.txt
python -m engine setup                     # fresh clone -> ready (dev: makes the first IT Admin by hand)
python -m engine                           # run it
python scripts/test_batches.py --skip-gui  # the full suite, in batches
pytest tests/test_seats.py                 # one file
ruff check .
```

Linux checks run in WSL (`Ubuntu-Preview`, venv `~/environ-engine-wsl`), the repository used from `/mnt/c/...`:
`FALCON_TEST_DATABASE_URL=... ~/environ-engine-wsl/bin/python -m pytest -q -p no:cacheprovider <files>`. The Linux Engine's real drill:
`scripts/linux_engine_drill.py` (root, a clean test machine); Windows' private PostgreSQL drill: `scripts/private_pg_drill.py` (elevated).

## Code layout

```
protocol/          NDJSON wire protocol (stdlib only)
engine/            the Engine (asyncio, asyncpg): handlers, database.py (all SQL), audit, file_index, scheduler, llm, detective/,
                   hierarchy/ (accounts, seats, traversal), store.py (seat grants), certs.py (renewal), migrations/
common/            bundled by every package, stdlib only (connection, signed docs + ed25519, store_keys, machine, places)
operator_client/   core/ (connection, state, config) + tui/ + gui/ (QML, to be replaced by the new concept)
worker_client/     the service: watching, knocking for a seat, the machine snapshot, places, executor, windows
installers/        payload, the Windows setups (installers/windows/), the Linux .deb (installers/engine/), store sign-in and registration
tests/             conftest: DB-backed Engine + connect(client_id); the real handshake (TEST_MASTER_SECRET, key_for)
```

Conventions: handlers are `@handler("area.op")`, roles checked with `engine.permissions`, typed errors via `ProtocolError(ErrorCode.X)`;
all SQL in `engine/database.py` repos; audit only through `engine.audit.record()`, reports only through `engine.hierarchy.reports.emit()`;
anything reacting to file activity subscribes via `engine.file_index.subscribe(...)`; TUI commands are `@command(...)` and never import
prompt_toolkit. GUI rules (MouseArea not TapHandler, paging, sizes from `Theme.qml`) are in Falcon's CLAUDE.md history and the UI memory.

## Invariants to keep

- **Propose, never silently resolve.** Model or automation output is surfaced to a person; never auto-committed.
- **Detective's case in words** (`engine/detective/telling.py`): the Engine writes every fact; a model may only rewrite the words between
  facts it sees as markers, kept only when `checked()` passes. Never let a model write a fact. No GBNF grammars forcing the model's answer.
- **One Global File Index**, one identity for a file through rename, move and edit; never per-feature bookkeeping.
- **Proactive first, reactive second**: events are the fast path, never the only one; each part reconciles by itself on start, reconnect
  and a timer, and resumes as if nothing happened after any gap. Every feature has a limit with feedback; background work goes hot first.
- **Restricted content** is never carried, read or written by anything without consent, and its status is looked up fresh every time.
- **Knocking grants nothing**: a machine is in only when an Admin gives it a seat or with a store-signed Admin claim; everything a machine
  learns about its Engine is store-signed or comes over the connection it already trusts (`docs/SEATS-AND-SETUP.md`).
- **No hard deletes** except the retention jobs; everything else is a status change.
- **Nobody owns anything between Admins**: any Admin may act, and pages say who did it.
