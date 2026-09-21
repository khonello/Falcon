# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository state

Design docs, a working **Engine** (Phase 1), the **Operator Client TUI** (Phase 2), the **Worker Client** service + narrow TUI (Phase 3), and **full integration** (Phase 4: the three Hierarchy scenarios and the cross-combo chains, `tests/test_integration.py`). Next: Phase 5, real authentication. Progress is tracked in `PHASES.md` — update it as items land; mark done items `[x]`.

Rules from the user:
- **Never use Docker.** PostgreSQL 18 is installed locally (service `postgresql-x64-18`). Role `falcon`/`falcon`, databases `falcon` (dev) and `falcon_test` (tests wipe and re-migrate it — never point tests at `falcon`).
- The user creates virtual environments themselves, one per package, all git-ignored: `environ-engine/` (Engine + tests), `environ-operator/` (Operator Client), `environ-worker/` (Worker Client). Work from them; don't create or recreate venvs.
- **The Engine deploys on Linux** (as the predecessor did); development happens on Windows. Keep `engine/` free of Windows-only imports, path assumptions, or event-loop-policy calls. Linux-specific work (Postgres + Engine on Linux/WSL) is a deliberate later step, not something to sneak in now.
- **TUI before GUI.** The built system is exercised through `prompt_toolkit` TUIs first; the QML GUI comes later on the same connection/state layer. Don't start GUI work until the TUI phases are done.
- Package naming: `<role>_client` — `operator_client` (Super User + Admin, one codebase) and `worker_client`. "Operator" is deliberately not "admin": it covers both roles and avoids colliding with the `admin` role/tier literals. Older text saying "Worker Agent" means `worker_client`.
- The user's machine has an OpenAI Codex config (`~/.codex/`). It is unrelated to this project — ignore it and do not offer to import it.

## Commands

The pyenv-win shim on PATH (`python.bat`) corrupts inline `python -c "..."`; use the venv's `python.exe` directly or run scripts from files.

```powershell
environ-engine\Scripts\Activate.ps1
pip install -e ".[engine,dev]"             # Engine + tests
pytest                                     # all tests (asyncio_mode=auto)
pytest tests/test_engine_smoke.py -k handshake   # one test
ruff check .
$env:FALCON_TEST_DATABASE_URL="postgresql://falcon:falcon@localhost:5432/falcon_test"; pytest   # incl. DB tests (skipped without it)
$env:FALCON_DEV_PLAINTEXT=1; $env:FALCON_DEV_BYPASS_AUTH=1; python -m engine   # local dev run

environ-operator\Scripts\Activate.ps1
pip install -e ".[tui]"                    # Operator Client TUI
python -m engine bootstrap SU-PC           # (from environ-engine, once, empty DB) -> prints the Super User client_id
python -m operator_client --engine 127.0.0.1:7400 --client-id <id> --plaintext        # interactive TUI
python -m operator_client --connect --script "tree; tasks"                              # scripted, no TUI

environ-worker\Scripts\Activate.ps1
pip install -e ".[worker]"                 # Worker Client (psutil, prompt_toolkit, watchdog)
python -m worker_client --engine 127.0.0.1:7400 --client-id <id> --plaintext --watch C:\path	o\docs [--ui]
```

Engine settings are `FALCON_*` env vars (see `.env.example`, `engine/config.py`). Without `FALCON_DATABASE_URL` the Engine runs with no database (scaffold only). Without `FALCON_DEV_PLAINTEXT` it refuses to start unless TLS cert/key are set.

## Code layout

```
protocol/          NDJSON wire protocol shared by all three packages (stdlib only)
engine/            the Engine (Python, asyncio, asyncpg)
  server.py        Engine class; imports every combo package so handlers register
  connection.py    per-connection loop: challenge → gated dispatch → response/push
  dispatch.py      @handler("area.op") registry, Context, Identity, stub()
  auth.py          handshake shape; verify() stubbed to accept until Phase 5
  database.py      asyncpg pool + one Repo class per schema section (all queries live here)
  audit.py         AuditTrail.record() — the only audit write path
  file_index.py    Global File Index: ingest + subscribe() fan-out to Task/Flow/Resource
  scheduler.py     periodic/one-shot jobs on the loop (deadlines, session expiry, retention)
  llm.py           LocalLLM narrow-question interface (yes_no / choose / extract)
  hierarchy/ task/ flow/ resource/ control/   one package per combo
  updates.py       update/deployment model
  migrations/      SQL, applied by Database.migrate()
common/            code bundled by more than one package (custom_actions validator) — stdlib only
operator_client/   core/ (connection, state, config, deadlines — no UI deps) + tui/ (shell registry, commands/, app)
worker_client/     service (connect/reconnect, push dispatch), watcher (watchdog + polling + idle sweep), executor
                   (Script Execution Model), flowsync, signals, lockout, updater, ui (narrow Worker TUI), config, idle
tests/             protocol, socket smoke, units, migrations, repos, per-combo end-to-end, operator/worker clients,
                   integration scenarios (conftest: DB-backed Engine + `connect(client_id)`; pytest-timeout 180s)
```

Conventions in the scaffold:
- Handlers: `@handler("area.op") async def fn(ctx: Context, payload: dict) -> dict`; check roles with `engine.permissions` (`require_role`, `require_department_scope`), parse fields with `int_field`/`str_field`, raise `ProtocolError(ErrorCode.X)` for typed errors, return JSON-safe dicts via `engine.serialize.row/rows`.
- All SQL lives in `engine/database.py` repos — never in handlers. In-memory registries expose `reset_state()` and are cleared in `Engine.__init__`.
- Operator Client: commands are `@command("name", "sub", usage, help)` in `operator_client/tui/commands/`, take `(ctx, args)` and return text; they must not import prompt_toolkit (only `tui/app.py` does) so `run_script` and the tests work from `environ-engine`. `ClientState.on_push` is the single place pushes update indicators/session.
- `common/` is bundled by every package and must stay stdlib-only: `connection.EngineConnection` (pushes are queued and handled by a consumer task — never handle a push inline in a read loop, a handler that awaits a request would deadlock), `cli` (grammar/registry), `render`, `custom_actions`.
- Worker Client: every Action, built-in or Custom, runs as a detached subprocess through `executor.py`; report before marking `completed`. Dev processes: kill stale `environ-*` python processes before restarting the Engine — a second Engine cannot bind 7400 and the old one keeps serving old code.
- Message types are `<area>.<op>`; only `auth.*` and `system.*` are accepted before the handshake.
- Anything reacting to file activity subscribes via `engine.file_index.subscribe(...)` — never its own detection.
- Reports are raised only through `engine.hierarchy.reports.emit()`; audit only through `engine.audit.record()`.

## Predecessor project (last resort only)

This system grew out of a smaller predecessor: **github.com/khonello/SystemMonitoring** (the "reference project" the spec cites for its Script Execution Model, auth scaffolding, helper-exe design, and three-pass build approach). This project is larger and several decisions have changed, so it is **not** authoritative. Consult it only when you hit an implementation challenge, approach, or code-organization question that the docs here genuinely leave unsolved — reserve it for when it is absolutely needed, not as a routine reference.

## What is being built

A hierarchy-based management/automation/monitoring system for organizations structured as **Super User → Department → Admin → Client PC**. Five feature areas share one authority model, one audit trail, and one file index:

- **Hierarchy** (backbone) — traversal, Session Blocking, Display Names, Report Routing, Cross-Department Assisted Access
- **Task** — LLM-populated verification targets; only manual verification by the assigner closes a task
- **Flow** — one-directional sync pipelines (Source → Branch/Transform/Categorize → Destinations)
- **Resource & Assistance** — tiered folders (`admin`/`restricted`/`workers`/`common`) as access policy; Ping → Message Channel → Listeners
- **Control, Events, Monitoring & Actions** — Admin-authored automation; Custom Actions are PowerShell/Python, stdlib + Windows-native only, unsandboxed

## Document map and authority

**Start at `hierarchy-system-design.md`.** It is the origin document — the backbone every other doc hangs off — and the point from which to navigate to the rest. The combos, schema, and spec all reference Hierarchy's concepts (traversal, Session Blocking, Display Names, Report Routing, roles) by name, so read it before any other doc.

| Document | Role |
|---|---|
| `hierarchy-system-design.md` | **Origin / backbone.** Read first; every other combo depends on it. |
| `task-natural-combo.md`, `flow-natural-combo.md`, `resource-assistance-combo.md`, `control-events-monitoring-actions-combo.md` | **What the system does.** Authoritative on behavior when they conflict with the spec. |
| `implementation-spec.md` | **How it's physically built.** Authoritative on architecture, stack, security, phasing. |
| `database-schema.md` | Engine-owned PostgreSQL schema, every column traced to a design rule. |
| `system-ecosystem-synthesis.md` | One-page overview of all combos and how they tie together. |

Conflict rule (from spec §12): combo docs win on *what*, `implementation-spec.md` wins on *how*.

## Target architecture (from implementation-spec.md)

Three deployable packages; only the Engine holds a database.

- **Engine** — Python, single-threaded `asyncio` (`asyncio.start_server`), `asyncpg` → PostgreSQL. Owns all business logic, the Global File Index, the audit trail, the master auth secret, and the local LLM call. Threads (`asyncio.to_thread`) only for blocking work: `psutil`-style process enumeration and the interruptible idle-time file sweep. All DB access goes through a `database.py`-style access layer — no raw SQL scattered across modules.
- **Operator Client** — one codebase for Super User *and* Admin; role/traversal scope is decided server-side and merely rendered. `prompt_toolkit` TUI first (used to test the built system), PySide6 + QML + `qasync` GUI later on the same connection/state layer. Config-file local state only.
- **Worker Client** — headless Python service with a bundled pinned interpreter, plus two on-demand QML helper exes (Overlay, Dialog) spawned via `asyncio.create_subprocess_exec`.

Transport: TCP + TLS (self-signed pinned cert, hostname identity, fail loudly), JSON messages. Auth: master secret → per-client `HMAC(master_secret, client_id)` derived key → nonce challenge-response per session.

Build order: Engine → Operator Client (TUI) → Worker Client → full integration → real auth logic last → GUI. Auth message fields are scaffolded from the first pass with the Engine check stubbed to accept; a `DEV_BYPASS_AUTH` flag (off by default, logged loudly) skips the handshake entirely rather than silently passing validation.

## Invariants to preserve when implementing

These are load-bearing design rules that are easy to violate by accident:

- **Propose, never silently resolve.** Any LLM/automation output (Task verification structure, deadlines, multi-task splits) is surfaced to a human for confirmation; never auto-committed. The LLM is local (Ollama/llama.cpp-style small model, Qwen3 shortlisted) and called as a **decomposed question graph** of narrow yes/no or pick-from-list questions — not one open-ended structuring call.
- **One Global File Index.** Task verification, Flow collision/cycle checks, and Resource compliance all query the same `file_index` — never build per-feature bookkeeping.
- **Native OS events over polling**; polling is fallback only. Idle-time work (index sweep, update retries) must cancel the instant user input resumes.
- **Display Names never propagate across relationship layers.** Any query resolving a name must filter `display_name_grants` by the *requesting* namer — never join across other namers' grants. Flagged in the schema as the easiest rule to break; needs test coverage.
- **Session Blocking**: one active session per PC (partial unique index on `sessions(pc_id) WHERE ended_at IS NULL`). Vertical superiors may block-or-end to enter; horizontal peers are hard-refused; Super User occupancy is un-evictable. Assisted Access is a *separate* state machine — do not reuse the traversal code path.
- **Reports**: written once, always visible to Super User, additively routed to department Admins. `report_addressed_views` is Super-User-only and must never be insertable as a report row.
- **No hard deletes** except the 90-day `audit_log` retention job; everything else is a status/flag change. Polymorphic refs (`reports.source_*`, `audit_log.target_*`) have no DB-level FK — enforce in the data-access layer.
- **Actions** run independently with their own timeout (report `"timeout"`, distinct from `"error"`), keyed by execution id for manual termination; no output piping between chained Actions in v1. Custom Action scripts are validated twice (client before send, worker client on arrival) via `py_compile` + AST import check.
- **Client (Worker) role** is a passive recipient except: view/start/monitor assigned Tasks (never verify), and Assistance search/Ping.

## Explicitly deferred (do not decide unilaterally)

Dashboard refresh mechanism (poll vs. push), Report-routing configuration UI, in-process vs. sidecar LLM hosting, update-escalation threshold value, CI/CD pipeline, and the JSON shapes of `condition_spec` / Flow-stage `config` / Assisted Access `access_ceiling`. Listed in spec §10 and schema §12.

## Local LLM (Task)

In-process llama.cpp by default (`llama-cpp-python`, CPU wheel), model file at `models/Qwen3-0.6B-Q8_0.gguf` (git-ignored; download from `huggingface.co/Qwen/Qwen3-0.6B-GGUF`). Sidecar alternatives via `FALCON_LLM_BACKEND=openai|ollama` — see `.env.example`. **A 0.6B model answers YES to every yes/no question and "one" to every count** — so `engine/task/llm_graph.py` asks it only list-picks and verbatim-checked extractions; presence, counting, file names, deadline phrases and multi-task splits are found mechanically. Keep it that way: any new question to the model must be a pick-from-list or an extraction validated against the text. Re-run `scripts/llm_benchmark.py` (must stay 13/13) after touching the graph or prompts.

## Linux / WSL

Verified deployment shape: Engine + PostgreSQL inside WSL (`Ubuntu-Preview`, Python 3.12, PostgreSQL 16), clients on Windows over TCP. The WSL venv is `~/environ-engine-wsl` (Linux home, not `/mnt/c` — the repo itself is used from `/mnt/c/.../Falcon`). Run there with:

```bash
cd /mnt/c/Users/Khonello/Documents/Developer/Languages/Multi/Falcon
FALCON_TEST_DATABASE_URL=postgresql://falcon:falcon@127.0.0.1:5432/falcon_test ~/environ-engine-wsl/bin/python -m pytest -q -p no:cacheprovider
~/environ-engine-wsl/bin/python scripts/llm_benchmark.py
```

`-p no:cacheprovider` avoids writing `.pytest_cache` through the mount. A from-source llama.cpp build can flip a near-tie list-pick versus the Windows wheel — that is why intent cues are settled mechanically before the model is asked; keep the benchmark green on both.
