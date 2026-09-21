# Phases

Progress tracker for building Falcon, following the build order and three-pass structure in
`implementation-spec.md` §11. Mark items `[x]` as they land; add sub-items as they surface.

Legend: `[ ]` not started · `[~]` in progress · `[x]` done

---

## Where things stand (2026-09-21) and the road to shippable

**Real, not scaffolding.** Engine: 93 message handlers, none stubbed, 157 SQL statements across 7
migrations (~7k lines). Worker Client: native file events + polling fallback, idle detection,
detached subprocess execution for 17 built-ins and Custom Actions (double validation), flow relay
(~1.6k lines). Operator Client: 88 TUI commands + the QML GUI on one shared core layer (~3.6k
lines). 93 tests green including 7 socket-level integration scenarios; live runs of Engine +
Worker + TUI + GUI; Linux/WSL Engine check. It went fast because the docs were specific and
everything was built through the TUI + tests, not through a UI.

**Not done — do not sell without these.** Worked one after the other, in this order; each is its
own phase section below. UI investment waits until Phases 5–9 are signed off, because each of them
can force behaviour changes that a rebuilt UI would have to absorb.

| # | Gap | Why it blocks a sale | Phase |
|---|-----|----------------------|-------|
| 1 | `auth.verify` accepts anyone with a client_id; no master secret, no derived keys, no TLS (dev plaintext only) | Anyone on the network can connect as the Super User | **Phase 5** (auth) — next |
| 2 | Only Claude has exercised the TUI / GUI / worker UI | Behaviour gaps a human notices are cheapest to fix before the UI is rebuilt on top | **Phase 7** (human passes) |
| 3 | Runs from source in venvs: no bundled interpreter, no installers, no frozen Worker exes, no service install, no update pipeline (`update_command` is an empty hook), no CI | Nothing can be installed on a customer PC; packaging usually forces real changes (paths, permissions) | **Phase 8** (packaging + deployment) |
| 4 | Worker Overlay/Dialog exes do not exist (the blocked-state surface is a text UI); no remote mouse/keyboard during traversal | The Client-PC experience in the Hierarchy doc is not what a worker sees | **Phase 8** (with the frozen toolchain) |
| 5 | Not hardened: no load/scale run (many departments/PCs), no security review of unsandboxed Custom Actions, no log rotation / service wrappers, Linux Engine verified but never deployed | Unknown behaviour under real load; ops story missing | **Phase 9** (hardening + ops) |
| 6 | LLM is a 0.6B model doing list-picks and verbatim extractions only (13/13 on the benchmark) | Fine as a "proposal assistant"; must not be pitched as AI understanding tasks without a bigger model behind the same graph | note for sales; revisit model size in Phase 9 |
| 7 | GUI is functional but plain: tables and buttons, no node graph for Flows, no interaction design | Not near what a private company will pay for | **Phase 10** (UI rebuild) — the QML is a thin layer over `FalconBridge`, so this does not touch the ~12k lines beneath |

---

## Phase 0 — Architecture ✅

- [x] Hierarchy System Design
- [x] Task / Flow / Resource & Assistance / Control-Events-Monitoring combo docs
- [x] System Ecosystem Synthesis
- [x] Implementation Specification
- [x] Database Schema v1
- [x] CLAUDE.md, repo initialised and pushed

---

## Phase 1 — Engine

### 1a. Scaffold (module structure, signatures, stub handlers, runs end-to-end)

- [x] Repo tooling: `pyproject.toml`, `.gitignore`, `.env.example`
- [x] `protocol/` — NDJSON envelope, request/response/push, error codes, framing
- [x] `engine/config.py` — FALCON_* settings, `DEV_BYPASS_AUTH` / `DEV_PLAINTEXT` flags
- [x] `engine/dispatch.py` — handler registry, `Context` / `Identity`
- [x] `engine/connection.py` + `engine/server.py` — asyncio server, per-connection loop, pre-auth gating, dev-flag banners, TLS fails loudly
- [x] `engine/auth.py` — challenge/response message shape wired; `verify()` stubbed to accept
- [x] `engine/database.py` — asyncpg pool + repository stubs, one per schema section
- [x] `engine/audit.py` — single `record()` path, deviation log, retention job
- [x] `engine/file_index.py` — ingest events/sweeps, subscriber fan-out, consumer queries
- [x] `engine/scheduler.py` — periodic + one-shot jobs, session expiry hook
- [x] `engine/llm.py` — local-only narrow-question interface (yes_no / choose / extract)
- [x] `engine/hierarchy/` — traversal, assisted_access, display_names, reports, alerts, accounts
- [x] `engine/task/` — tasks, verification, llm_graph (full decision graph), expectation
- [x] `engine/flow/` — flows (cycle check, failure suggestions), sync (write attribution)
- [x] `engine/resource/` — resource (tier predicate), assistance (turn lock)
- [x] `engine/control/` — actions, events (type→mechanism map), executions, custom_actions (validator)
- [x] `engine/updates.py`
- [x] Tests: protocol round-trips, socket-level smoke (handshake, dispatch of every type, bypass flag), pure-logic units
- [x] Venvs created (`environ-engine`, `environ-operator`, `environ-worker`); Engine + dev deps installed in `environ-engine`; ruff clean; 21 tests green

### 1b. Implementation (real logic, module by module)

- [x] `engine/migrations/001_initial.sql` from `database-schema.md` + migration runner (`Database.migrate`, `schema_migrations`), JSONB codec; 8 constraint tests green on `falcon_test`
- [x] Repositories in `database.py` — real asyncpg queries for every schema section; polymorphic-ref validation; only delete is audit purge; `Unavailable`/`Conflict`/`NotFound` mapped to typed protocol errors; 14 repo tests
- [x] Hierarchy: traversal + session blocking (vertical block-or-end-first, horizontal refusal, un-evictable Super User), native sessions on connect, time limit + extension, expiry incl. network-drop path, session pushes (blocked/ended/released)
- [x] Hierarchy: display names (top-down grant, self name, composed fallback; non-propagation tested end-to-end)
- [x] Hierarchy: report routing (additive), routed pane, mark addressed → Super-User-only View, targeted `report.new` pushes
- [x] Hierarchy: assisted access (availability, request/offer/accept/decline/close, ceiling-only narrowing, report emitted)
- [x] Hierarchy: alerts (role-gated audiences, immediate push), departments, account+PC provisioning with client_id, offboarding ends sessions
- [x] Hierarchy: scheduled alert delivery via the Scheduler (exactly once); recurrence stored, expansion deferred
- [x] Global File Index: real upsert/search/collision/hash queries; event normalisation; tier-scoped search handler
- [x] Task: propose (graph + collisions), create (explicit-None rule, collision refusal, scope), list/get/start/verify, stack evaluation per intent, expectation signals from the index stream + program signals, soft/final deadlines as scheduled Events (re-armed on start)
- [x] Task: Ollama-style local LLM client (stdlib HTTP, None-on-failure, backoff); `llm_available` surfaced to the client
- [x] Task: decision graph benchmarked with Qwen3-0.6B (Q8 GGUF, in-process llama.cpp): 13/13 realistic cases, ~2 calls/description, ~1s/call on CPU; graph restructured around what a 0.6B model does reliably (list picks + verbatim extraction; presence/count questions answered mechanically). Open item 10.3 decided: in-process default, sidecar optional
- [x] Flow: create/edit with consent (by authority; owner asked, flow paused until answered), pre-flight collision (confirm or change path), overlap-aware cycle prevention, resource-folder exclusion; propagation relayed via flow.read → flow.content → flow.apply with per-destination stage chains; write attribution vs external edits → `-modified` + re-sync; branch-scoped failure with reactive suggestion + report; resume/pause/delete/history
- [x] Resource: tags derived from tier folders, admin/restricted tracked by hash system-wide, violations logged + surfaced to the user + reported, only that file ignored (Flow skips it), resolve lifts it; explicit tagging (admin tier Super User only)
- [x] Assistance: tier-scoped search; pings between direct vertical pairs with pulsing status push; channel opens on response (sender speaks first), Engine-enforced turn lock, superior-only close; listeners per-adder, live silent pushes, listener_report
- [x] Control: `condition_spec` shape defined; native signals (worker relay, file-index stream, task/flow/resource internal) matched with pc scope + filters; polled thresholds/idle/time via worker metrics + Scheduler; actions dispatched independently with immediate/delayed timing; execution lifecycle with streamed output, timeout guard, manual terminate by id; dashboard snapshot + live `action.status`/`event.fired` pushes
- [x] Custom Actions: Admin-only, Engine-side validation on create/update (stdlib + Windows-native)
- [x] Updates: approval hard gate, department rollout push, attempt reports (running version on first failure), count-based escalation threshold (`FALCON_UPDATE_ESCALATION_FAILURES`, default 3) → Admin notice + update_status report, aggregate health, Super User prompt
- [x] Audit retention job wired to real purge (daily); scheduled alert delivery (30s); polled events (15s)
- [x] Engine test suite against a real local Postgres (Windows): 71 tests — protocol, socket smoke, units, migrations, repos, and end-to-end per combo
- [x] Linux check: Ubuntu 24.04 (WSL), Python 3.12, PostgreSQL 16, venv `~/environ-engine-wsl` — 72/72 tests, LLM benchmark 13/13 (llama.cpp built from source)

---

## Phase 2 — Operator Client, TUI (`prompt_toolkit`, env: `environ-operator`)

The TUI is how the built system gets tested before any GUI work. It sits on a connection/state
layer the GUI will reuse unchanged.

- [x] `operator_client/core/`: `EngineConnection` (NDJSON over TCP/TLS, handshake with the final auth shape, request futures, push subscribers, retry), `ClientState` (identity, session, red banner, blocked state, pulsing indicators from pushes), `LocalConfig` (JSON), `deadlines.resolve_phrase`
- [x] `operator_client/tui/` shell: command registry + `key=value` grammar, `run_line`/`run_script` (UI-free), prompt_toolkit app with completion, bottom toolbar (role, session, SUPER USER banner, BLOCKED, pulsing indicators), live push printing
- [x] Hierarchy: `tree`, `traverse`/`end`/`extend`/`session`/`claim`, `name set|self`, `names`, `dept add`, `account add|offboard`, `pc add`
- [x] Task: `task propose` (flags, collisions, split, deadline phrase → local time), `task item add|rm|file`, `task create [none]`, `tasks`, `task <id>`, `task stack|start|verify`
- [x] Flow: `flow create` (stages/branches by index, consent/collision feedback), `flow consent|edit|pause|resume|delete|history|trigger`, `flows`, `flow <id>`
- [x] Resource/Assistance: `violations`, `violation resolve`, `tag`, `search`, `ping`/`pings`/`respond`, `msg`/`channel`/`channels`, `close channel`, `listen`/`listeners`
- [x] Control: `actions`, `action add|custom|rm|run` (Custom validated locally via `common.custom_actions` before sending), `events`, `event add|enable|disable|actions`, `dashboard`, `exec`, `terminate`, `validate`
- [x] Updates: `updates`, `update approve|rollout|prompt`
- [x] Assisted Access: `assist available|helpers|request|accept|decline|close|status`
- [x] Reports/alerts: `reports`, `report mark`, `routing`, `routing set`, `addressed`, `alerts`, `alert`
- [x] `python -m engine bootstrap <hostname>` provisions the first Super User on an empty database
- [x] Verified live: Engine on the dev DB, Super User builds departments/accounts, Admin proposes with the real local LLM, edits, creates, traverses; 8 client tests in the suite (80 total)
- [ ] Interactive session pass by a human (the prompt_toolkit loop itself is not exercised by tests)

---

## Phase 3 — Worker Client (headless service, env: `environ-worker`)

- [x] `worker_client/service.py`: connect-forever with backoff, handshake, native session claim, push dispatch, reconnect (verified live), notifiers for the UI
- [x] `worker_client/config.py`: JSON under `%PROGRAMDATA%/Falcon` (or `FALCON_WORKER_CONFIG`), watched roots, cadences, cache
- [x] File events: `watchdog` native adapter (verified live) with mtime/size polling fallback; sha256 hashes off-loop; idle-time full sweep in batches that stops when input resumes (`worker_client/idle.py`: GetLastInputInfo on Windows)
- [x] Session blocking: `Lockout` state + notifier surface (+ optional `LockWorkStation`); overlay exe deferred to Phase 6
- [x] Notifications: `session.blocked/released`, deadlines, pings, alerts, violations, offers printed live in the narrow UI; Dialog exe deferred to Phase 6
- [x] Action execution: detached `create_subprocess_exec` against the bundled interpreter, per-execution log tailed by size growth and streamed, timeout → `timeout`, terminate by execution id → `terminated`, non-zero exit → `failed`; built-ins run through the same path (psutil-based monitoring, file ops, notify, screenshot via PowerShell; power actions gated by `--allow-power`)
- [x] Custom Action re-validation on arrival (shared `common.custom_actions`)
- [x] Flow on this PC: `flow.read` relay, `flow.apply` through Transformation (registered converters; unsupported → predefined suggestion) and Categorization stages, `-modified` conflict preservation; verified between two workers end to end
- [x] Program-target expectation signals (running/active/rss/open files/present) + `control.metrics`
- [x] Narrow Client TUI (`worker_client/ui.py`): status with BLOCKED surface, tasks/task/start, search, ping/pings/respond/msg/channel, alerts, violations, sweep — no verify, no Admin surface
- [x] Update attempts: pending version from `update.available`, retry when idle, pluggable `update_command` (no packaging pipeline yet → honest failure + escalation); never-confirmed PCs representable (migration 007)
- [x] Shared code moved to `common/`: `EngineConnection` (pushes now queued off the read loop — fixes a deadlock when a push handler awaits a request), CLI grammar/registry/renderers
- [x] Engine fixes found by the worker: `exit_code` stored (005), per-file write attribution via `source_relative_path`/`written_path` (006)
- [x] 7 worker tests (real subprocesses, real temp dirs, two workers relaying a flow); 87 total green; verified live with the dev Engine + Operator TUI
- [ ] Interactive pass by a human (`python -m worker_client --ui`)

---

## Phase 4 — Full Integration

- [x] Scenario 1 (Super User audits a department): tree → traverse into an Admin workstation with the red banner and no Conditional Rendering → `audit actor=<admin>` review (itself audited) → end; the `session.ended` audit entry carries who/where/`duration_seconds`
- [x] Scenario 2 (Admin manages a Client PC): traverse (worker blocked, then released) → department-wide policy update as one Custom Action run on every PC independently (`control.action_run department_id=`), each audited
- [x] Scenario 3 (Client receives an alert): department alert with action link reaches the worker live and in `alerts`; the worker UI has no control surface at all
- [x] Task → Global File Index → Flow → Events → Control: a Create-intent target appears wherever the worker saves it, binds by identity, flows to a second PC, fires `task.target_appeared`, whose Action runs on the assignee's PC; only manual verification completes
- [x] Resource → Events → Control + Flow: a restricted hash on a worker PC is a violation → report, event, action on that PC; Flow moves everything except that one file; resolve lifts the ignore
- [x] Events → Control on a Flow failure: unsupported Transformation pauses the branch, routes a report to the department, fires the event; edit + resume + trigger recovers
- [x] Network drop mid-traversal with real clients: the worker stays blocked after the Admin's connection drops; the same deadline releases it (`network_drop_deadline_expired`)
- [x] Engine on Linux (WSL) with a Windows client over TCP (Phase 1)
- [x] Found and fixed by integration: Resource compliance now runs before Flow on file events (Flow could copy a file a moment before it became a violation); `common.cli` keeps backslashes (Windows paths were mangled); `EngineConnection.close()` cancels the reader before closing the transport and bounds every await (a Windows Proactor hang); `audit.recent`/`audit.deviations` handlers + TUI `audit`/`deviations`
- [ ] Deferred to Phase 6: remote mouse/keyboard control during traversal (scenario 2 step 4) needs an input channel no phase has built; the Overlay/Dialog exes

---

## Phase 5 — Authentication (shape present since Phase 1; the logic is what is missing) — NEXT

- [ ] Master secret generated on the Engine host (never transmitted); derived key `HMAC(master_secret, client_id)` per provisioned client
- [ ] Provisioning: `hierarchy.account_create` / `python -m engine bootstrap` issue the derived key once, to be written to an ACL-restricted path on the client (install-package input)
- [ ] Real `auth.verify`: nonce challenge → client HMAC response → constant-time compare; replace the `"stub"` HMAC in `common/connection.py`
- [ ] Identity binding: reject (not just flag) a client_id from an unexpected hostname where the design says so; keep the deviation audit entry
- [ ] TLS: self-signed Engine cert generation, pinned cert shipped in each client install, `--ca` honoured by both clients; fail loudly on mismatch
- [ ] Rotation/revocation: offboarding an account invalidates its key; re-provisioning issues a new one
- [ ] Remove reliance on `DEV_BYPASS_AUTH` / `DEV_PLAINTEXT` in every test path (tests provision real keys against the test DB); the flags stay as loud dev switches only
---

## Phase 6 — GUI (PySide6 / QML / qasync) — pulled ahead of Phase 5 by agreement (TUI phases done)

- [x] `operator_client/gui/` on the same `operator_client/core/` layer as the TUI: `bridge.py` (`FalconBridge` QObject exposed to QML as `falcon` — state properties, `connectTo`/`disconnect`, one generic `call(type, payload, callback)`, `resolveDeadline`/`readFile`/`validateScript`/`pretty` helpers), `app.py` (qasync loop set *before* the QML loads so `Component.onCompleted` calls are scheduled on it), `python -m operator_client --gui`
- [x] Persistent status surface on every screen (`StatusBar.qml`): role, account/pc/dept, session, pulsing indicators, RED BANNER (Super User inside another view), BLOCKED marker; live push feed (`PushFeed.qml`)
- [x] Views mirroring the TUI feature set: Hierarchy (tree + sessions, traverse/block-or-end/end/extend, display + self names, assisted access), Tasks (list/detail/stack, propose → review items/flags/collisions/split → create, start/verify), Flows (list/status/history, consent/pause/resume/delete/trigger, builder with stages + destinations), Automation (dashboard, action library + built-in/custom creation with local script validation, run on pc/department, events, executions + terminate), Assistance (pings → channels with turn-taking, listeners, file search + tagging, violations), Reports (reports + routing, alerts, updates rollout, audit + deviations, department/account provisioning)
- [x] Verified offscreen against the dev Engine (every view screenshotted with real data; traverse shows the banner) and live (`--gui` window on the qasync loop); 3 GUI tests (`tests/test_operator_gui.py`, skipped without PySide6) — 97 total green
- [x] Window opens full screen (pinned to the work area, `app.fit_to_screen`); title bar has minimize + close only, no resize frame or maximize — verified against the native window style
- [ ] Interactive pass by a human (`python -m operator_client --gui ...` from `environ-operator`); visual polish deferred until the behaviour is signed off
- [ ] Worker Client Overlay exe + Dialog exe (QML, frozen with the same toolchain)
- [ ] Window prefs / layout persistence (`LocalConfig.prefs` is there; nothing written yet)
- [ ] Remote mouse/keyboard during traversal (needs an input channel; deferred from Phase 4)

---

## Phase 7 — Human interactive passes (after Phase 5)

- [ ] Operator TUI pass (`python -m operator_client ...` from `environ-operator`): Hierarchy scenarios 1–3, a Task from propose to verify, a Flow between two PCs, an Action + Event, a Ping → channel
- [ ] Worker narrow UI pass (`python -m worker_client --ui`): blocked/released, assigned task, alert, violation
- [ ] Operator GUI pass (`--gui`): the same walks; note behaviour gaps only — visual polish belongs to Phase 10
- [ ] Every gap found becomes an item here with its fix; full suite re-run after

---

## Phase 8 — Packaging and deployment (after Phase 7)

- [ ] Worker Client: bundled pinned interpreter + frozen service (spec 4.3), installed as a Windows service; the install package carries the derived key + pinned cert from Phase 5
- [ ] Worker Overlay exe + Dialog exe (QML, frozen with the same toolchain); the blocked-state surface and notifications move from the text UI to them
- [ ] Remote mouse/keyboard during traversal (input channel Engine ↔ Worker; deferred from Phase 4)
- [ ] Operator Client installer (TUI + GUI in one package)
- [ ] Engine on Linux: install script / systemd unit, config file, PostgreSQL setup, log rotation
- [ ] Update pipeline: a real `update_command` (download → verify → swap → restart → `updates.report_status`); approval → rollout → escalation exercised end to end with real packages
- [ ] CI: lint + full suite on push (Windows clients, Linux Engine), artifact build, signing

---

## Phase 9 — Hardening and operations (after Phase 8)

- [ ] Load/scale run: many departments and PCs, sustained file activity, deadlines and pushes under load; fix what breaks
- [ ] Security review of Custom Actions (unsandboxed by design): who can author, what is audited, kill switch
- [ ] Failure drills: Engine restart mid-session, DB outage, worker offline for days, clock skew
- [ ] Ops: health endpoint, PostgreSQL backup/restore, audit retention verified, runbook
- [ ] Revisit LLM model size behind the same question graph (benchmark must stay green); decide what sales may claim
- [ ] Decide the deferred items below that hardening forces (dashboard refresh, escalation threshold)

---

## Phase 10 — UI rebuild (after Phase 9 is signed off)

- [ ] Interaction design for the Operator GUI: information architecture, navigation, states (blocked, banner, restricted view)
- [ ] Node-graph editor for Flows (Source → stages → Destinations) with consent/collision/cycle feedback inline
- [ ] Hierarchy as a live tree/graph with session state; Task editor as a guided review of the proposal; Automation dashboard as a real dashboard
- [ ] Worker Overlay/Dialog visual design
- [ ] Window prefs / layout persistence (`LocalConfig.prefs`)
- [ ] Constraint: keep the QML a thin layer over `FalconBridge` — no business logic moves into the UI

---

## Deferred (spec §10) — decide when reached, not before

- Dashboard refresh mechanism (poll vs push)
- Report routing configuration UI
- ~~LLM hosting: in-process vs sidecar~~ — decided: in-process llama.cpp by default (`FALCON_LLM_BACKEND=llamacpp`), `openai`/`ollama` sidecars available
- Update escalation threshold: count vs time, and value
- CI/CD, packaging, artifact signing
- JSON shapes: `condition_spec`, Flow-stage `config`, Assisted Access `access_ceiling` / `access_narrowing`
