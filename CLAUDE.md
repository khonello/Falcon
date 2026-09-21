# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository state

**Design-only, pre-code.** The repo currently contains eight Markdown design documents and no source, build config, tests, or commits. There are no build/lint/test commands yet. When implementation begins, add the real commands here (the spec calls for Python + PostgreSQL via Docker Compose for the Engine, PySide6/QML for GUIs).

The user's machine has an OpenAI Codex config (`~/.codex/`). It is unrelated to this project — ignore it and do not offer to import it.

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
- **Operator Client** — PySide6 + QML + `qasync`. One codebase for Super User *and* Admin; role/traversal scope is decided server-side and merely rendered. Config-file local state only.
- **Worker Agent** — headless Python service with a bundled pinned interpreter, plus two on-demand QML helper exes (Overlay, Dialog) spawned via `asyncio.create_subprocess_exec`.

Transport: TCP + TLS (self-signed pinned cert, hostname identity, fail loudly), JSON messages. Auth: master secret → per-client `HMAC(master_secret, client_id)` derived key → nonce challenge-response per session.

Build order: Engine → Operator Client → Worker Agent → full integration → real auth logic last. Auth message fields are scaffolded from the first pass with the Engine check stubbed to accept; a `DEV_BYPASS_AUTH` flag (off by default, logged loudly) skips the handshake entirely rather than silently passing validation.

## Invariants to preserve when implementing

These are load-bearing design rules that are easy to violate by accident:

- **Propose, never silently resolve.** Any LLM/automation output (Task verification structure, deadlines, multi-task splits) is surfaced to a human for confirmation; never auto-committed. The LLM is local (Ollama/llama.cpp-style small model, Qwen3 shortlisted) and called as a **decomposed question graph** of narrow yes/no or pick-from-list questions — not one open-ended structuring call.
- **One Global File Index.** Task verification, Flow collision/cycle checks, and Resource compliance all query the same `file_index` — never build per-feature bookkeeping.
- **Native OS events over polling**; polling is fallback only. Idle-time work (index sweep, update retries) must cancel the instant user input resumes.
- **Display Names never propagate across relationship layers.** Any query resolving a name must filter `display_name_grants` by the *requesting* namer — never join across other namers' grants. Flagged in the schema as the easiest rule to break; needs test coverage.
- **Session Blocking**: one active session per PC (partial unique index on `sessions(pc_id) WHERE ended_at IS NULL`). Vertical superiors may block-or-end to enter; horizontal peers are hard-refused; Super User occupancy is un-evictable. Assisted Access is a *separate* state machine — do not reuse the traversal code path.
- **Reports**: written once, always visible to Super User, additively routed to department Admins. `report_addressed_views` is Super-User-only and must never be insertable as a report row.
- **No hard deletes** except the 90-day `audit_log` retention job; everything else is a status/flag change. Polymorphic refs (`reports.source_*`, `audit_log.target_*`) have no DB-level FK — enforce in the data-access layer.
- **Actions** run independently with their own timeout (report `"timeout"`, distinct from `"error"`), keyed by execution id for manual termination; no output piping between chained Actions in v1. Custom Action scripts are validated twice (client before send, agent on arrival) via `py_compile` + AST import check.
- **Client (Worker) role** is a passive recipient except: view/start/monitor assigned Tasks (never verify), and Assistance search/Ping.

## Explicitly deferred (do not decide unilaterally)

Dashboard refresh mechanism (poll vs. push), Report-routing configuration UI, in-process vs. sidecar LLM hosting, update-escalation threshold value, CI/CD pipeline, and the JSON shapes of `condition_spec` / Flow-stage `config` / Assisted Access `access_ceiling`. Listed in spec §10 and schema §12.
