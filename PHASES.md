# Phases

Progress tracker for building Falcon, following the build order and three-pass structure in
`implementation-spec.md` §11. Mark items `[x]` as they land; add sub-items as they surface.

Legend: `[ ]` not started · `[~]` in progress · `[x]` done

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
- [ ] Hierarchy: scheduled/recurring alert delivery via the Scheduler
- [x] Global File Index: real upsert/search/collision/hash queries; event normalisation; tier-scoped search handler
- [ ] Task: create/assign/start/verify/close, deadline Events, stack evaluation, expectation signals
- [ ] Task: LLM client against a local model (Ollama sidecar vs in-process — open item 10.3), graph benchmarked on real descriptions
- [ ] Flow: create with consent / collision / cycle checks, propagate, conflict rename, branch-scoped failure + resume
- [ ] Resource: violation detection from index events, ignore-that-file, user notification, report
- [ ] Assistance: ping status push, channel open/turn-lock/close, listeners (scoped query)
- [ ] Control: event matching (`condition_spec` shape), polled evaluation, execution lifecycle, terminate, dashboard query
- [ ] Custom Actions: Engine-side validation on create
- [ ] Updates: approval gate, rollout, status ingestion, escalation threshold (open item 10.4), health view
- [ ] Audit retention job wired to real purge
- [~] Engine test suite against a real local Postgres (Windows) — DB fixture + migration tests in place; grows with each repo
- [ ] Linux check: Engine + Postgres inside WSL, same suite green — the deployment shape (Engine on Linux, clients on Windows)

---

## Phase 2 — Operator Client, TUI (`prompt_toolkit`, env: `environ-operator`)

The TUI is how the built system gets tested before any GUI work. It sits on a connection/state
layer the GUI will reuse unchanged.

- [ ] `operator_client/core/`: Engine connection (NDJSON over TLS, handshake), request/push
      routing, session/permission state model, local config (last Engine address, cached lists)
- [ ] `operator_client/tui/` shell: role-scoped navigation, status bar (session, deadline,
      ping indicator), push notifications surfaced live
- [ ] Hierarchy: tree, traverse / end / extend, red banner state, blocked/ended transitions,
      display names, report list/mark, routing config (open item 10.2)
- [ ] Task: propose → review/correct/resolve collision → create; list/get with stack status;
      start (as assignee); manual verify
- [ ] Flow: create (consent / collision / cycle feedback), edit, pause/resume, status +
      failure suggestion, history
- [ ] Resource/Assistance: violations, search, ping + status, message channel with turn lock,
      listeners (own additions only)
- [ ] Control: action library incl. Custom (pre-send validation via `custom_actions.validate`),
      events, run/terminate, dashboard view (refresh mechanism — open item 10.1)
- [ ] Updates: approve, rollout, health view
- [ ] Assisted Access: request / availability / accept / close

---

## Phase 3 — Worker Client (headless service, env: `environ-worker`)

- [ ] `worker_client/core/`: persistent authenticated connection, reconnect, local cached
      state (deadlines, session) under an ACL-restricted path
- [ ] File event reporting (native OS events) + idle-time full sweep with instant cancel on input
- [ ] Session blocking: local input restriction; overlay as a TUI/console surface first
- [ ] Notifications: grace warnings, deadline pulses, ping alerts (TUI/console first)
- [ ] Action execution: detached subprocess, per-execution log tailing, timeout, terminate by id
- [ ] Custom Action re-validation on arrival
- [ ] Program-target expectation signals (active/idle, RSS, open files)
- [ ] Narrow Client TUI: task view/start/monitor, assistance search/ping
- [ ] Update retry on idle + status reporting

---

## Phase 4 — Full Integration

- [ ] Engine + Operator Client + Worker Client end-to-end scenarios (the three from Hierarchy → Example Scenarios)
- [ ] Cross-combo flows: Task → Flow, Task → Events, Resource → Events, Events → Control
- [ ] Network-drop mid-traversal expires via the same deadline path
- [ ] Engine running on Linux (WSL) with Windows clients connecting over TCP

---

## Phase 5 — Authentication (last, but shape present since 1a)

- [ ] Master secret generation + provisioning tool (derived keys to ACL-restricted path)
- [ ] Real `auth.verify` (HMAC compare), identity binding, bound-PC deviation check
- [ ] TLS cert generation/pinning per client install package
- [ ] Remove reliance on `DEV_BYPASS_AUTH` / `DEV_PLAINTEXT` in every test path

---

## Phase 6 — GUI (PySide6 / QML / qasync) — only after the TUI phases are done

- [ ] `operator_client/gui/` on the same `operator_client/core/` layer as the TUI
- [ ] Views mirroring the TUI feature set (Hierarchy, Task, Flow, Resource/Assistance, Control, Updates)
- [ ] Worker Client Overlay exe + Dialog exe (QML, frozen with the same toolchain)
- [ ] Window prefs / layout persistence

---

## Deferred (spec §10) — decide when reached, not before

- Dashboard refresh mechanism (poll vs push)
- Report routing configuration UI
- LLM hosting: in-process vs sidecar
- Update escalation threshold: count vs time, and value
- CI/CD, packaging, artifact signing
- JSON shapes: `condition_spec`, Flow-stage `config`, Assisted Access `access_ceiling` / `access_narrowing`
