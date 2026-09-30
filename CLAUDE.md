# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository state

Design docs, a working **Engine** (Phase 1), the **Operator Client TUI** (Phase 2), the **Worker Client** service + narrow TUI (Phase 3), **full integration** (Phase 4: the three Hierarchy scenarios and the cross-combo chains, `tests/test_integration.py`), and the **Operator Client GUI** (Phase 6, pulled ahead: PySide6/QML on the same core layer, `python -m operator_client --gui`). **The order from here is fixed and sequential** (see `START-HERE.md`, then `PHASES.md`): Phase 5 authentication (done) → Phase 7 UI/UX (**done 28 Sep 2026**: the design was approved and every page is built to it) → Phase 9 packaging/deployment, which is now the blocker for a sale → Phase 8 human passes on the installed thing → Phase 10 hardening. Each phase leaves its area usable, not perfect; UI refinement continues through 8–10. Progress is tracked in `PHASES.md` — update it as items land; mark done items `[x]`.

Rules from the user:
- **Never use Docker.** PostgreSQL 18 is installed locally (service `postgresql-x64-18`). Role `falcon`/`falcon`, databases `falcon` (dev) and `falcon_test` (tests wipe and re-migrate it — never point tests at `falcon`).
- The user creates virtual environments themselves, one per package, all git-ignored: `environ-engine/` (Engine + tests), `environ-operator/` (Operator Client), `environ-worker/` (Worker Client). Work from them; don't create or recreate venvs.
- **The Engine deploys on Linux** (as the predecessor did); development happens on Windows. Keep `engine/` free of Windows-only imports, path assumptions, or event-loop-policy calls. Linux-specific work (Postgres + Engine on Linux/WSL) is a deliberate later step, not something to sneak in now.
- **The TUI is the working surface while the console is rebuilt.** TUI before GUI (done: the TUI phases are complete and the GUI now exists on the same connection/state layer). Any new feature still lands as an Engine handler + TUI command first, then a GUI view — the TUI is the scripted test surface (`--script`).
- **The console is being rebuilt in the Ant Design idiom (Route B, 29 Sep 2026).** `docs/UI.md` is what we are building and the rules that govern it; `docs/UI-COMPONENTS.md` is the build list in priority order. The bespoke design and all 64 of its QML files are deleted — do not resurrect them, and do not start a bespoke design pass: look the answer up in the idiom instead. The QML must stay a thin layer over `FalconBridge`.
- Package naming: `<role>_client` — `operator_client` (Super User + Admin, one codebase) and `worker_client`. "Operator" is deliberately not "admin": it covers both roles and avoids colliding with the `admin` role/tier literals. Older text saying "Worker Agent" means `worker_client`.
- The user's machine has an OpenAI Codex config (`~/.codex/`). It is unrelated to this project — ignore it and do not offer to import it.

## Commands

The pyenv-win shim on PATH (`python.bat`) corrupts inline `python -c "..."`; use the venv's `python.exe` directly or run scripts from files.

**New machine or a real network: `docs/GETTING-STARTED.md`.** **Settings live in `.env`, never in the shell.** The Engine, the tests and the scripts load it themselves
(`common/dotenv.py`); a variable set in the real environment still wins. `python -m engine setup` makes a fresh clone
ready in one step and is safe to run again: it writes `.env`, makes the certificate, creates the databases (given
`--admin-url postgresql://postgres:<pw>@localhost:5432/postgres`, else it prints the SQL), migrates, creates the master
secret, bootstraps the first Super User (id + key printed once and written into this machine's Operator Client
settings), and checks the model (`--download-model` fetches it).

```powershell
environ-engine\Scripts\Activate.ps1
pip install -r requirements-engine.txt     # Engine + tests + the GUI tests (extras: engine,dev,gui)
python -m engine setup                     # fresh clone -> ready: .env, cert, databases, schema, secret, Super User
python -m engine                           # run it (real auth + TLS, from .env)
pytest                                     # all tests, DB tests included (FALCON_TEST_DATABASE_URL comes from .env)
pytest tests/test_engine_smoke.py -k handshake   # one test
ruff check .
python -m engine gencert 127.0.0.1,localhost,<hostname> data   # a certificate by hand (setup does this)
python -m engine bootstrap SU-PC           # a first Super User by hand (setup does this)
# dev switches (no TLS, no handshake -- loud): uncomment FALCON_DEV_PLAINTEXT / FALCON_DEV_BYPASS_AUTH in .env

environ-operator\Scripts\Activate.ps1
pip install -r requirements-operator.txt    # Operator Client TUI + GUI (PySide6, qasync)
python -m operator_client --gui            # after setup on this machine: connects as the Super User, nothing to type
python -m operator_client --engine 127.0.0.1:7400 --client-id <id> --client-key <hex> --ca data/engine.crt   # interactive TUI (TLS)
python -m operator_client --engine 127.0.0.1:7400 --client-id <id> --client-key <hex> --plaintext           # against a DEV_PLAINTEXT Engine
python -m operator_client --connect --script "tree; tasks"                              # scripted, no TUI (remembered settings)
python -m operator_client --gui --engine 127.0.0.1:7400 --client-id <id> --client-key <hex> --ca data/engine.crt   # QML GUI
```

GUI tests (`tests/test_operator_gui.py`) need PySide6 in `environ-engine` too (`requirements-engine.txt` includes it); they skip otherwise. The screenshot scripts set Qt's offscreen platform and Windows font folder themselves, and take their state as options (`design/shot_gui.py design/shots admin 2 --flow=4`; `design/shot_board.py <BOARD>` for design boards).

```powershell
environ-worker\Scripts\Activate.ps1
pip install -r requirements-worker.txt      # Worker Client + its windows (psutil, watchdog, prompt_toolkit, PySide6)
# headless, without the windows: pip install -e ".[worker]"   -- windows: python -m worker_client.windows <kind> '<json>'
python -m worker_client --engine 127.0.0.1:7400 --client-id <id> --client-key <hex> --ca data/engine.crt --watch C:\docs [--ui]
```

Engine settings are `FALCON_*` keys in `.env` (see `.env.example`, `engine/config.py`); the suite refuses a test URL that points at the working database. Without `FALCON_DATABASE_URL` the Engine runs with no database (scaffold only). Without `FALCON_DEV_PLAINTEXT` it refuses to start unless TLS cert/key are set. The master secret lives at `FALCON_SECRET_PATH` (default `data/master.secret`, created on first start, git-ignored); every client key is `HMAC(master_secret, "<client_id>:<key_generation>")` and is printed once at provisioning (`bootstrap`, `hierarchy.account_create`, `hierarchy.pc_register`, `hierarchy.pc_rekey`). Clients that were provisioned before Phase 5 have no key on record — derive theirs from the secret with `engine.auth.derive_client_key`.

## Code layout

```
protocol/          NDJSON wire protocol shared by all three packages (stdlib only)
engine/            the Engine (Python, asyncio, asyncpg)
  server.py        Engine class; imports every combo package so handlers register
  connection.py    per-connection loop: challenge → gated dispatch → response/push
  dispatch.py      @handler("area.op") registry, Context, Identity, stub()
  auth.py          nonce challenge / HMAC response, key derivation, auth.failed audit; master_secret.py, tls.py (gencert)
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
                   + gui/ (bridge.py FalconBridge → QML as `falcon`; app.py qasync loop; qml/ one file per view)
worker_client/     service (connect/reconnect, push dispatch), watcher (watchdog + polling + idle sweep), executor
                   (Script Execution Model), flowsync, signals, lockout, updater, ui (narrow Worker TUI), config, idle
tests/             protocol, socket smoke, units, migrations, repos, per-combo end-to-end, operator/worker clients,
                   integration scenarios (conftest: DB-backed Engine + `connect(client_id)`; pytest-timeout 180s)
```

Conventions in the scaffold:
- Handlers: `@handler("area.op") async def fn(ctx: Context, payload: dict) -> dict`; check roles with `engine.permissions` (`require_role`, `require_department_scope`), parse fields with `int_field`/`str_field`, raise `ProtocolError(ErrorCode.X)` for typed errors, return JSON-safe dicts via `engine.serialize.row/rows`.
- All SQL lives in `engine/database.py` repos — never in handlers. In-memory registries expose `reset_state()` and are cleared in `Engine.__init__`.
- Operator Client: commands are `@command("name", "sub", usage, help)` in `operator_client/tui/commands/`, take `(ctx, args)` and return text; they must not import prompt_toolkit (only `tui/app.py` does) so `run_script` and the tests work from `environ-engine`. `ClientState.on_push` is the single place pushes update indicators/session.
- GUI: QML never talks to the socket — everything goes through `falcon.call(type, payload, function(ok, result))` on `FalconBridge`, which returns typed errors as `(false, {code, message})`, never exceptions; state-changing replies (traverse/end/extend/claim) update `ClientState` inside `bridge.request`. Views refresh on `connected` and on relevant `pushReceived` types; keep `Component.onCompleted` guarded by `falcon.isConnected`. Colours, sizes and durations are named only in `Theme.qml` — nothing else names one. Views carry `objectName`s so tests can `findChild` them; read `property var` values with `.toVariant()`. **Anything clickable uses a `MouseArea`, never a `TapHandler`**: a TapHandler reacts to any press over its item, including one that landed on a dialog on top of it, so a table row would open its drawer when you clicked a dropdown in a modal above it (fixed 30 Sep 2026). A MouseArea only hears the press when it is the topmost thing under the cursor. Popups and dialogs also carry one across their own background, so a press in a gap never reaches the page behind.
- `common/` is bundled by every package and must stay stdlib-only: `connection.EngineConnection` (pushes are queued and handled by a consumer task — never handle a push inline in a read loop, a handler that awaits a request would deadlock), `cli` (grammar/registry), `render`, `custom_actions`.
- Worker Client: every Action, built-in or Custom, runs as a detached subprocess through `executor.py`; report before marking `completed`. Dev processes: kill stale `environ-*` python processes before restarting the Engine — a second Engine cannot bind 7400 and the old one keeps serving old code.
- Message types are `<area>.<op>`; only `auth.*` and `system.*` are accepted before the handshake. Tests run the REAL handshake: `tests/conftest.py` fixes `TEST_MASTER_SECRET` and `key_for(client_id)` gives the key a test client presents (pass it as `derived_key=` / `client_key=`); only `FALCON_DEV_BYPASS_AUTH` skips it, and only `tests/test_auth.py` exercises TLS (everything else stays plaintext for speed). A hostname mismatch at connect is a *deviation* (logged + surfaced), not a refusal — the design says so.
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

**Start at `START-HERE.md`** for where the work stands and what is next. For the product itself, start at `hierarchy-system-design.md`. It is the origin document — the backbone every other doc hangs off — and the point from which to navigate to the rest. The combos, schema, and spec all reference Hierarchy's concepts (traversal, Session Blocking, Display Names, Report Routing, roles) by name, so read it before any other doc.

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

Build order was: Engine → Operator Client (TUI) → Worker Client → full integration → GUI → real auth (done). `DEV_BYPASS_AUTH` (off by default, logged loudly) skips the handshake entirely rather than silently passing validation.

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

In-process llama.cpp by default (`llama-cpp-python`, CPU wheel). Default model `models/Qwen3-1.7B-Q8_0.gguf` (1.8GB, git-ignored; `huggingface.co/Qwen/Qwen3-1.7B-GGUF`); `Qwen3-0.6B-Q8_0.gguf` is kept as the fast-but-weaker option. Sidecar alternatives via `FALCON_LLM_BACKEND=openai|ollama` — see `.env.example`.

The graph asks the model only **pick-from-list** and **verbatim-checked extraction** questions; presence, counting, file names, deadline phrases and multi-task splits are found mechanically. Keep it that way. Two hard-won guards: a model-extracted span is rejected if it occurs only inside a file name (`backup-2026-09-28.bak` really does contain a date), and a deadline the model finds on its own must be an unambiguous date or clock time — a bare day word is settled by position, or "the usual Friday things" becomes a Friday deadline.

**Do not force the model's answer with a GBNF grammar.** It looks like free accuracy and is a downgrade: the grammar constrains from the first token, Qwen3 wants to emit `<think>` there, and masking it makes both models answer almost constantly — which reads like a model with no signal and is really a broken measurement. An unparsed answer is the "unclear → surface to the assigner" signal the design wants; a well-formed guess is one the graph cannot tell from a real answer.

Two benchmark suites in `scripts/llm_cases.py`, and the split is the point: `tuned` is a regression guard the code has seen the answers to and must stay perfect; `heldout` is the real measurement and must **never be tuned against** — fix only defects that are wrong by the system's own rules, then move the case that exposed one into `tuned` and add fresh held-out cases. `scripts/llm_probe.py` is the 20-second gate before trying any new model: 8 unmistakable cases, and it says `COLLAPSED` if the model answers the same thing regardless of the text (Qwen3-0.6B 6/8, Qwen3-1.7B 8/8). `scripts/llm_benchmark.py --no-model` answers nothing, to show how much the model contributes at all. Held-out scores: **29/32 with the 1.7B, 24/32 with the 0.6B, 13/24 with no model** — the model matters, and so does the mechanical graph. The 1.7B costs ~5s per call against ~1.4s, so a task proposal takes ~10-20s.

## Linux / WSL

Verified deployment shape: Engine + PostgreSQL inside WSL (`Ubuntu-Preview`, Python 3.12, PostgreSQL 16), clients on Windows over TCP. The WSL venv is `~/environ-engine-wsl` (Linux home, not `/mnt/c` — the repo itself is used from `/mnt/c/.../Falcon`). Run there with:

```bash
cd /mnt/c/Users/Khonello/Documents/Developer/Languages/Multi/Falcon
FALCON_TEST_DATABASE_URL=postgresql://falcon:falcon@127.0.0.1:5432/falcon_test ~/environ-engine-wsl/bin/python -m pytest -q -p no:cacheprovider
~/environ-engine-wsl/bin/python scripts/llm_benchmark.py
```

`-p no:cacheprovider` avoids writing `.pytest_cache` through the mount. A from-source llama.cpp build can flip a near-tie list-pick versus the Windows wheel — that is why intent cues are settled mechanically before the model is asked; keep the benchmark green on both.
