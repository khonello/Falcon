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
- [ ] Venv created, deps installed, test suite green

### 1b. Implementation (real logic, module by module)

- [ ] `engine/migrations/001_initial.sql` from `database-schema.md` + migration runner
- [ ] Repositories in `database.py` (real queries; polymorphic-ref validation; no hard deletes)
- [ ] Hierarchy: traversal + session blocking against `sessions` (partial unique index path), time limit + extension, expiry
- [ ] Hierarchy: display names query rule (+ the non-propagation test), composed fallback
- [ ] Hierarchy: report routing read/write, addressed views (Super User only)
- [ ] Hierarchy: assisted access state machine, availability query, scope intersection
- [ ] Hierarchy: alerts + scheduling, accounts/departments/PCs, offboarding
- [ ] Global File Index: real upsert/search/collision/hash queries
- [ ] Task: create/assign/start/verify/close, deadline Events, stack evaluation, expectation signals
- [ ] Task: LLM client against a local model (Ollama sidecar vs in-process — open item 10.3), graph benchmarked on real descriptions
- [ ] Flow: create with consent / collision / cycle checks, propagate, conflict rename, branch-scoped failure + resume
- [ ] Resource: violation detection from index events, ignore-that-file, user notification, report
- [ ] Assistance: ping status push, channel open/turn-lock/close, listeners (scoped query)
- [ ] Control: event matching (`condition_spec` shape), polled evaluation, execution lifecycle, terminate, dashboard query
- [ ] Custom Actions: Engine-side validation on create
- [ ] Updates: approval gate, rollout, status ingestion, escalation threshold (open item 10.4), health view
- [ ] Audit retention job wired to real purge
- [ ] Engine test suite against a real local Postgres

---

## Phase 2 — Operator Client (PySide6 / QML / qasync)

- [ ] Scaffold: connection layer, session/permission state model, view routing by role scope
- [ ] Hierarchy views: tree, traversal + red banner, session blocked/ended transitions, display names, report routing config (open item 10.2)
- [ ] Task views: propose → review/correct → create; stack status; manual verification
- [ ] Flow views: builder (stages, branches), consent, status + failure suggestions
- [ ] Resource/Assistance views: folders, search, ping indicator, message channel, listeners
- [ ] Control views: editing mode (events/actions/custom), dashboard mode (refresh mechanism — open item 10.1)
- [ ] Custom Action pre-send validation with bundled interpreter
- [ ] Local config storage (last Engine address, window prefs, cached lists)

---

## Phase 3 — Worker Agent (headless Python + Overlay/Dialog exes)

- [ ] Scaffold: persistent authenticated connection, reconnect, local cached state (deadlines, session)
- [ ] File event reporting (native OS events) + idle-time full sweep with instant cancel on input
- [ ] Session blocking: overlay exe, local input restriction
- [ ] Dialog exe: grace warnings, deadline pulses, ping alerts
- [ ] Action execution: detached subprocess, per-execution log tailing, timeout, terminate by id
- [ ] Custom Action re-validation on arrival
- [ ] Program-target expectation signals (active/idle, RSS, open files)
- [ ] Narrow Client UI: task view/start/monitor, assistance search/ping
- [ ] Update retry on idle + status reporting

---

## Phase 4 — Full Integration

- [ ] Engine + Operator Client + Worker Agent end-to-end scenarios (the three from Hierarchy → Example Scenarios)
- [ ] Cross-combo flows: Task → Flow, Task → Events, Resource → Events, Events → Control
- [ ] Network-drop mid-traversal expires via the same deadline path

---

## Phase 5 — Authentication (last, but shape present since 1a)

- [ ] Master secret generation + provisioning tool (derived keys to ACL-restricted path)
- [ ] Real `auth.verify` (HMAC compare), identity binding, bound-PC deviation check
- [ ] TLS cert generation/pinning per client install package
- [ ] Remove reliance on `DEV_BYPASS_AUTH` / `DEV_PLAINTEXT` in every test path

---

## Deferred (spec §10) — decide when reached, not before

- Dashboard refresh mechanism (poll vs push)
- Report routing configuration UI
- LLM hosting: in-process vs sidecar
- Update escalation threshold: count vs time, and value
- CI/CD, packaging, artifact signing
- JSON shapes: `condition_spec`, Flow-stage `config`, Assisted Access `access_ceiling` / `access_narrowing`
