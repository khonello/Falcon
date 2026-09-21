# Implementation Specification — Hierarchy-Based Management & Automation System

**Status:** Ready for implementation
**Timeline:** ~1 month
**Stack:** Python (Engine + backend logic), Qt Quick / QML (desktop GUIs), `prompt_toolkit` (power-user TUI, optional/later)

---

## 1. Introduction

### 1.1 Project Overview

A hierarchy-based management, automation, and monitoring system for organizations with a Super User → Department → Admin → Client PC structure. Unlike point solutions (task trackers, file sync tools, remote monitoring suites) that exist as separate, disconnected products, this system architects five feature areas — **Hierarchy** (the backbone), **Task**, **Flow**, **Resource & Assistance**, and **Control, Events & Monitoring** — into one coherent ecosystem sharing a single audit trail, a single file index, and one governing rule for every automated/LLM-assisted decision: propose and surface uncertainty, never silently resolve it.

### 1.2 Problem Statement

Organizations with a multi-tier structure (a head office overseeing departments, each department run by an administrator, each administrator overseeing a set of workstations) currently need to stitch together separate tools for task assignment, file distribution, access control, help requests, and remote monitoring/control — none of which share a permission model, an audit trail, or a file index. This creates context-switching overhead, inconsistent access boundaries, and no single source of truth for "who did what, when."

### 1.3 Solution

One system, three physically distinct deployable packages (**Engine**, **Operator Client**, **Worker Agent** — see Section 2), all governed by the same Hierarchy authority model, sharing one **Global File Index** and one **audit trail** with a flat 90-day retention policy for v1.

---

## 2. System Architecture

### 2.1 Why Three Packages, Not One

An earlier consideration was a single monolithic program that adapts its interface by role. This was reconsidered in favor of a three-package physical split, modeled on a reference lab-monitoring project, because:

- **Physical deployment reality:** a Super User, an Admin, and a Worker are on different physical machines. A Worker's PC should never contain the code paths for Custom Action authoring, Cross-Department Assisted Access initiation, or Report Routing configuration — these are Admin/Super-User-only capabilities. Shipping one monolithic binary everywhere means shipping capability surface to machines that should never have it, relying on conditional hiding rather than physical absence.
- **Traversal already implies asymmetric capability, not just asymmetric UI.** Super User traversing into an Admin's session sees "exactly what that Admin sees" — this is naturally modeled as the same GUI codebase running with different permission scope, not as a different program. But a Worker's Client Agent has no equivalent to "become an Admin" — it is traversed *into*, never traverses *out*. This asymmetry maps cleanly onto two different package types, not three, and not one.

### 2.2 The Three Packages

```
                         [ SERVER / ENGINE HOST ]
              ┌───────────────────────────────────────┐
              │                ENGINE                  │
              │        (Python, asyncio/epoll)          │
              │   Single source of truth. Owns the      │
              │   database, the Global File Index,      │
              │   the audit trail, and all Hierarchy,    │
              │   Task, Flow, Resource, and Control/     │
              │   Events/Monitoring business logic.      │
              │   Holds the master auth secret.          │
              └──────────────────┬───────────────────────┘
                                  │
                        TCP (JSON messages,
                        TLS, session auth per
                        connection — see Section 8)
                                  │
        ┌─────────────────────────┴─────────────────────────┐
        ▼                                                     ▼
 [ SUPER USER / ADMIN WORKSTATIONS ]                 [ WORKER / CLIENT PCS ]
┌───────────────────────────────┐          ┌────────────────────────────────┐
│       Operator Client          │          │         Worker Agent            │
│     (Qt 6 + QML GUI, one       │          │   (headless service, Python,    │
│   codebase for both Super      │          │   bundled runtime)               │
│   User and Admin — permission  │          │                                  │
│   scope differs by role and    │          │   Spawns on demand, not          │
│   traversal depth, not by      │          │   persistent:                    │
│   separate binaries)           │          │   ┌──────────────┐ ┌───────────┐ │
│                                 │          │   │ Overlay exe  │ │Dialog exe │ │
│   Local state only: last-      │          │   │(Session      │ │(grace     │ │
│   connected Engine address,    │          │   │ Block /      │ │ warnings, │ │
│   window prefs, cached view    │          │   │ Traversal    │ │ Ping      │ │
│   state. No database.          │          │   │ indicator)   │ │ alerts)   │ │
│                                 │          │   └──────────────┘ └───────────┘ │
│   Bundled: pinned Python for   │          │                                  │
│   Custom Action script         │          │   Bundled: pinned Python for     │
│   validation before send       │          │   Custom Action re-validation    │
└───────────────────────────────┘          │   + execution                    │
                                             │   Local state only: this        │
                                             │   client's derived auth key,     │
                                             │   locally-cached Deadline/       │
                                             │   Session state for offline      │
                                             │   resilience. No database.       │
                                             └────────────────────────────────┘
```

### 2.3 Package Responsibilities

**Engine** (Section 3) — the only component holding a database. Every other package is a thin client to it.

**Operator Client** (Section 4) — one QML codebase, used by both Super User and Admin. What differs between the two is *permission scope and traversal depth*, resolved server-side by the Engine and reflected in what the client is allowed to render/do — not two separate programs. This directly implements Hierarchy's principle that Super User traversing into an Admin sees exactly what that Admin sees: it's the same client rendering the same views, gated by which session/permission context is currently active.

**Worker Agent** (Section 5) — headless. A Worker does not "log into" a GUI the way an Operator does; per Hierarchy, Client is a passive information recipient with the narrow Task-interaction exception (view, start, monitor a task — never verify). This narrow surface is a small, focused UI need (task status, alerts, Assistance ping/search) — it does not require the full Operator Client codebase, and keeping it minimal is itself a security boundary: a compromised Worker PC exposes far less capability than a compromised Operator Client would.

---

## 3. Engine — Core Backend

### 3.1 Responsibilities

- Accept and manage Operator Client and Worker Agent connections
- Own and enforce the entire Hierarchy authority model (traversal, Session Blocking, Report Routing, Display Names, Cross-Department Assisted Access)
- Own and run the Task, Flow, Resource, and Control/Events/Monitoring business logic
- Own and maintain the **Global File Index** (Section 6) and the **audit trail** (Section 8.4)
- Host or call out to the **local LLM** used for Task's natural-language verification population (Section 7.2.1) — implemented as a local, decomposed-question-graph call model, not a single all-in-one structuring call; runs on or alongside the Engine host, never an external API, given the sensitivity of what task descriptions can reference
- Route commands and data between Operator Clients and Worker Agents
- Hold the master authentication secret; never transmits it, derives per-connection session keys (Section 8.2)

### 3.2 Concurrency Model

`asyncio` with `epoll`-backed `asyncio.start_server`, multiplexing all connections on a single thread/event loop — no per-connection threads. This matches the system's own established preference for native/event-driven detection over polling wherever possible (Global File Index population, Flow's sync trigger, Resource compliance detection, Events' native/pushed category — see Section 6.2 and Section 7.5).

Threads (`asyncio.to_thread` / `run_in_executor`) are reserved for calls that cannot signal readiness and could block the loop: `psutil`-style process enumeration for Monitoring Actions, and the full-system idle-time sweep for the Global File Index (Section 6.2), which must itself be interruptible the instant user input resumes. Database access (Section 3.3) does not need this treatment — `asyncpg` is natively async, so database calls stay on the event loop rather than requiring an offload.

### 3.3 Database

**Default: PostgreSQL for v1.** Chosen over SQLite despite this system's realistic scale (a handful of departments, tens of Admins, a moderate number of Client PCs) not technically requiring it — the deciding factor is deployment credibility, not load. A company evaluating this system, and its own IT administrators, will reasonably expect a database with built-in replication, point-in-time recovery, and mature backup tooling rather than a system that asks them to trust a single file plus manually-enforced discipline (WAL mode, scheduled file-level backups) to get the same guarantees. Postgres removes that as a question entirely, at negligible technical cost given the Engine's load pattern (one process, sequential writes) doesn't stress either database differently. All access still goes through a `database.py`-style access layer (functions, not raw SQL scattered across modules), so this remains true regardless of database choice.

**Local development:** a single Postgres instance (Docker Compose is sufficient) alongside the Engine — this is the one small tax of this choice versus SQLite's zero-setup file, worth accepting deliberately rather than discovering as friction later.

**Backup and recovery** use Postgres's own tooling (`pg_dump`/`pg_basebackup`, or a managed hosting provider's built-in backup if the Engine is ever hosted rather than on-premises) — still a requirement to actually configure and test before production use, but the tooling to do so is mature and standard rather than something to hand-roll.

**Connection handling:** the Engine's asyncio event loop uses an async Postgres driver (`asyncpg`) rather than a synchronous one, keeping database calls non-blocking and consistent with the rest of the Engine's concurrency model (Section 3.2) — this replaces the earlier SQLite-era note about offloading synchronous writes to a thread; with `asyncpg`, that offload is unnecessary since the driver itself is natively async.

### 3.4 What the Engine Does Not Do

The Engine does not render UI and does not directly control input on a Worker PC — it authorizes and coordinates; the actual mouse/keyboard control during a traversal session, and the actual rendering of overlays/dialogs, happens client-side (Operator Client and Worker Agent respectively), driven by Engine-issued commands and Engine-enforced permission state.

---

## 4. Operator Client (Super User + Admin GUI)

### 4.1 Technology

Qt 6 + QML (PySide6, the official LGPL Qt-for-Python binding), with `qasync` to integrate `asyncio` into Qt's event loop — keeping the client single-threaded and consistent with the concurrency model used everywhere else in the system, rather than mixing Qt's own threading with a separate asyncio loop.

### 4.2 One Codebase, Two Roles

The Operator Client is not aware, at a deep architectural level, of "being" a Super User client or an Admin client — it renders whatever the current session's permission scope and traversal depth allow, as reported by the Engine. This directly implements:

- **Traversal Boundaries → Super User Exemption:** the same views render with full access when the active session is Super User, and with Conditional Rendering restrictions applied when the active session is Admin.
- **The red banner:** a simple state flag from the Engine ("this session is Super User traversed into Admin X") toggles a persistent visual element — no separate Super-User-mode build.
- **Session Blocking overlays:** when the Operator Client is itself the one being blocked out of a session it's occupying (e.g., an Admin's session being entered by Super User), the client receives an Engine-pushed "session ended/blocked" event and must gracefully exit that view — this is a state transition the same codebase handles, not a different program being killed.

### 4.3 Local State (Config Only, No Database)

Last-connected Engine address, window layout/preferences, a cache of the client/department list for faster reopening, and cached Custom Action scripts pending validation. Ordinary preferences storage (a config file or Qt's own settings mechanism) — no relational or security-sensitive need that would justify a local database.

### 4.4 What Renders Here

Everything in Hierarchy that is Admin-or-above (Session Blocking initiation, Traversal, Display Names configuration, Report Routing configuration, Cross-Department Assisted Access requests), all of Task creation/verification/deadline UI, all of Flow creation/management, all of Resource's Admin-side folders and Assistance's Ping/Message Channel/Listener UI, and the entire Control/Events/Monitoring interface (Section 7.5) including the Dashboard.

---

## 5. Worker Agent (Client PC)

### 5.1 Technology

Headless Python service, bundled with its own pinned embeddable Python runtime (so Custom Action re-validation/execution never depends on a system-installed interpreter — see Section 7.3). Ships two on-demand, non-persistent helper executables, built the same way as the Engine's reference design:

- **Overlay exe** — renders the Session Blocking "inaccessible / traversal in progress" indicator (Hierarchy → Traversal Boundaries) and the Time-Based Restriction-style lockout surface if a Control Action or Event enforces one. Fullscreen or bannered depending on context; re-asserts topmost periodically; exits the moment the underlying session state clears.
- **Dialog exe** — renders grace-period warnings, Deadline pulsing-status alerts, and Assistance Ping notifications. Spawned on demand via `asyncio.create_subprocess_exec`, non-blocking to the Agent's own event loop; the user's response (or timeout) is reported back the same way Custom Action output is reported (Section 7.3).

Both helper executables are QML-based (small, frozen with the same Qt toolchain as the Operator Client) rather than a second UI toolkit — kept deliberately minimal since the Worker Agent's whole design goal is a narrow, low-footprint surface.

### 5.2 Responsibilities

- Maintain a persistent, authenticated connection to the Engine
- Enforce Session Blocking locally when a traversal begins (render the overlay, restrict local input while occupied)
- Execute Control/Monitoring Actions and Custom Actions when instructed by the Engine (Section 7)
- Surface the narrow Client-side Task interaction (view, start, watch progress — never verify) and Assistance (search, Ping) per Hierarchy's Client exception
- Report Global File Index-relevant OS events (file create/modify/move/copy) back to the Engine (Section 6.2)
- Handle reconnection gracefully; per Hierarchy's traversal/session model, a network drop during an active traversal session must fail safe (see Section 9 open item)

### 5.3 Local State (Config Only, No Database)

This client's derived auth key (Section 8.2), and a small amount of cached state needed for offline resilience — e.g., locally cached Deadline times so a pulsing alert can still fire if the Engine connection briefly drops. Not a database: read-mostly, no relational structure, security-sensitive rather than query-heavy — the same reasoning the reference project applied to its own lockout-schedule storage.

---

## 6. The Global File Index

The single most load-bearing shared mechanism in the system. Task's Verification, Flow's collision checks, and Resource's compliance detection all validate against this one index — not three separate bookkeeping systems.

### 6.1 What It Tracks

File name, location, content hash, and (where applicable) a Resource access tag (`admin`, `restricted`, `worker-dept-X`, `common`). Owned entirely by the Engine; stored in the Engine's database (Section 3.3).

### 6.2 How It's Populated

- **Event-driven baseline:** Worker Agents (and the Operator Client's own machine, where relevant) report OS file events (create, modify, move, copy) to the Engine as they occur — native OS signals, not polling, per the system's general preference (see also Flow's sync trigger and Resource's compliance detection, both of which reuse this exact mechanism rather than defining their own).
- **Opportunistic full-system sweep:** when a machine is idle (no mouse/keyboard input), the Worker Agent (or Operator Client) performs a full local file-system sweep and reports the results, extending index coverage beyond what's been event-referenced so far.
- **Self-throttling:** the moment user input resumes, the sweep stops immediately — implemented as a cancellable background task (`asyncio.to_thread` with a cooperative cancellation check), never competing with the user for resources.

### 6.3 Consumers

- **Task Verification:** File target search (scoped to the assignee's Resource access) and Create-intent name-collision checking.
- **Flow:** Pre-Flight Collision Check (destination path vs. existing indexed content) and the native-event-plus-polling-fallback sync trigger.
- **Resource:** compliance/violation detection (restricted/admin-tagged files appearing where they shouldn't) and Assistance's file search.

---

## 7. The Five Combos, Mapped to Architecture

### 7.1 Hierarchy (Engine-resident authority model)

Implemented entirely server-side in the Engine — the Operator Client never independently decides what it's allowed to see or do; it renders what the Engine's permission/session state says.

- **Traversal & Session Blocking:** the Engine holds session-occupancy state per PC/session. A traversal request checks: is the destination idle? If not, is the requester vertical-superior (block-or-end-first, then enter) or horizontal (hard refuse)? Super User occupancy is flagged un-evictable. Traversal Time Limit is a countdown the Engine tracks per Admin-level session, pushed to the Operator Client for display and extendable on request. **This same deadline is what governs a network drop mid-traversal** — no separate disconnect-handling logic is needed: the Engine-side countdown keeps running regardless of the Worker Agent's connection state, so a dropped connection simply means the session is less likely to be extended before the deadline fires. If the connection recovers before the deadline, the traverser resumes normally; if not, the session expires and the block releases exactly as it would if the traverser had simply run out of time on purpose — an indefinite lockout is structurally impossible, since no traversal session was ever unbounded to begin with.
- **Display Names:** stored per-relationship-pair in the database (Super User's private label for Admin X; Admin's own self-facing name; the composed fallback built from account/PC identifiers when unset) — never resolved or joined across relationship layers, enforced by query design, not just convention.
- **Report Routing:** every Report-category event (Resource violation, Flow failure, Listener report, Assisted Access session) is written once, always visible to Super User, and additionally flagged visible to a routed department's Admin if that category is configured as routed. The Super-User-only View (tracking what's been addressed) is a separate table, never itself insertable as a Report row — enforced at the schema/query level to prevent the infinite-regress problem discussed during design.
- **Cross-Department Assisted Access:** implemented as its own state machine, deliberately not reusing the vertical Traversal code path — entry is consent-granted, not block-or-end-first. Matching (requester-initiated or helper-broadcast) is an Engine-side availability query against Admin sessions not currently occupying anything.

### 7.2 Task

- **Verification & Intent:** the Engine calls the local LLM (see Section 7.2.1 for the call model) with the assigner's natural-language description; the resulting structured output (targets, Intent, Deadline) is returned to the Operator Client for review before being committed. The governing "propose, never silently resolve" rule is enforced by never auto-committing an LLM-populated structure without an explicit confirm action from the Operator Client.
- **Expectation:** driven by the Worker Agent's OS-event reporting (File targets) or process/activity monitoring (Program targets — active/idle, memory footprint, open file descriptors), same reporting channel as Section 6.2.
- **Deadline:** implemented as two Engine-scheduled Events (soft, final) — see Section 7.5, Events. No separate scheduler needed; Task's Deadline is just a Control/Events/Monitoring Event with a Task-specific trigger action.
- **No Task Directory:** confirmed architecturally — nothing in the Engine or either client needs to create or track a task-specific folder; all target tracking is by identity via the Global File Index.

#### 7.2.1 LLM Call Model — Decomposed Question Graph, Not One Structuring Call

**Local, not API.** Task descriptions can reference restricted files, department-sensitive projects, and other data this system is explicitly designed to keep contained (see Resource's access tiers and the whole premise of Restricted File Tracking) — sending that content to a third-party API would undermine the containment the rest of the system is built to guarantee. A local model also removes per-call cost and any dependency on external connectivity, consistent with the Worker Agent's general offline-resilience posture (Section 5.3).

**Decomposed graph of narrow questions, not one open-ended structuring call.** A single "read this description and construct the whole verification structure" call asks a model to extract, structure, and self-assess confidence all at once — exactly where small/local models degrade unpredictably, and their failure mode (a confidently wrong structure) is hard to detect from the output alone. Instead, the LLM is called repeatedly with narrow, mostly yes/no or pick-from-a-finite-list questions, structured as a decision graph — each answer determines which question fires next. This plays to what small local models are reliably good at (narrow classification, not open-ended generation), and it maps naturally onto the finite lists the rest of Task's design already establishes (Intent's fixed categories, Verification's fixed item types).

**The graph (four independent root branches, evaluated per task-creation call):**

```
ROOT — File?          Does the input mention a file target? (yes/no)
  └─ YES → FILE BRANCH:
       Q: What file name is mentioned?               → extract string
       Q: Does it already exist, or need creating?
            "exists"      → Q: changing, or just needing to be present?
                                 "changing" → Intent = Update
                                 "present"  → Intent = Exists
            "not yet"     → Intent = Create
                                 Q: Is a folder/path mentioned? (yes/no)
                                      YES → extract path
                                      NO  → path left unspecified

ROOT — Program?        Does the input mention a program target? (yes/no)
  └─ YES → PROGRAM BRANCH:
       Q: What program name is mentioned?             → extract string
       Q: Is its use tied to a specific file (e.g. "use X to update Y")? (yes/no)
            YES → Intent = Used With File → linked to FILE BRANCH's target
                  (if FILE BRANCH didn't fire, this is a contradiction → flag insufficient)
            NO  → Q: Must it be closed/not running rather than used? (yes/no)
                       YES → Intent = Closed/Not Running
                       NO  → Q: Just needs to be present, not actively used? (yes/no)
                                  YES → Intent = Installed/Available
                                  NO  → Intent = Used (default/general case)

ROOT — Deadline?        Does the input mention a deadline? (yes/no)
  └─ YES → Q: One date/time mentioned, or more than one?
                ONE  → extract → Final Deadline
                MORE → flag: ambiguous deadline → surface to assigner

ROOT — Multi-task?      Does the input describe more than one distinct piece of work? (yes/no)
  └─ YES → propose a concrete split (draft tasks sharing common fields) → surface to assigner

If both File-root and Program-root answer NO → flag: no verification target detected →
    surface an explicit "None?" confirmation to the assigner (never assumed silently)
```

**Every non-clean leaf is where "surface to assigner" fires** — an ambiguous deadline, a File/Program contradiction, no target detected at all, or a detected multi-task description. The graph's own branching structure *is* the ambiguity-detection mechanism; there's no separate confidence-scoring step bolted on afterward, because uncertainty shows up as a single unclear or contradictory answer to a single narrow question, which is cheap to detect and cheap to act on.

**Cost model:** multiple small calls per task creation rather than one large call — acceptable because each call is narrow enough to run on a smaller, less resource-intensive local model than a single all-in-one structuring call would require, which matters directly for what hardware the Engine host needs to run comfortably.

**Candidate models (v1 shortlist):** the decision graph's calls are narrow (yes/no, pick-from-a-finite-list, short span extraction) and don't require multilingual coverage or strong open-ended reasoning, so a small model is sufficient rather than a compromise:

| Candidate | Size | Why it fits |
|---|---|---|
| **Qwen3** (smallest variants) | 0.6B–4B | Top pick — strong instruction-following and classification behavior at very small sizes, Apache 2.0 (no usage caps or attribution requirements), mature Ollama/llama.cpp tooling that keeps the Engine-side integration to a local HTTP call rather than custom inference code |
| **Gemma 4** (E2B) | 2B effective | Strong second choice — purpose-built by Google for exactly this resource-constrained, narrow-task deployment profile |
| **Ministral 3** | 3.4B | Reasonable fallback if the above underperform in testing — Mistral's smallest instruct model, edge-deployment-focused, fits in ~8GB VRAM |

Final selection (and exact size within the Qwen3 family) should be decided empirically — a short benchmarking pass running real or realistic task descriptions through the actual decision graph, checked by hand — rather than fixed from general benchmarks alone, since accuracy on *this specific* narrow graph is what matters, not general leaderboard standing. This space also moves quickly; the shortlist above should be treated as a starting point for that evaluation, not a permanent commitment.

### 7.3 Flow & Custom Actions — Script Execution Model

Flow's sync/transformation/categorization pipeline and Control/Events/Monitoring's Custom Actions both execute scripted or process-driven work on a Worker Agent (or, for Admin-to-Admin flows, an Operator Client's own machine). The reference project's **Script Execution Model** is adopted directly for both:

- Scripts (Custom Actions; Flow's Transformation stage, if implemented as a script rather than a built-in converter) are launched **detached** from the response cycle via `asyncio.create_subprocess_exec` — never `_shell`, always an explicit argv against the bundled interpreter.
- Output is redirected to a per-execution log file keyed by a unique execution/command id; a background task tails it by polling on a fixed interval and only reading when file size has grown, avoiding wasted re-reads.
- Every Action's fixed **timeout** (per the Control/Events/Monitoring spec) is enforced the same way the reference project caps script runtime — a script/process that overruns is terminated, reported with a distinct `"timeout"` status (not `"error"`), consistent with Task's Action status values (Success/Failed/Pending/Terminated).
- Any running Action can also be **manually terminated** early, keyed by its execution id rather than process name, so one specific run can be stopped without ambiguity when multiple instances share an interpreter name.
- Custom Action scripts are validated twice — once by the Operator Client's bundled interpreter before sending (`python -m py_compile` equivalent, plus an `ast`-based import check restricted to standard-library-and-Windows-available modules only, per the system's no-sandboxing-but-constrained-runtime decision), and again by the Worker Agent's own bundled interpreter on arrival, in case of tampering in transit.

### 7.4 Resource & Assistance

- **Resource tiers and violation detection:** implemented as Global File Index queries (Section 6.3) plus the tag-comparison logic described in the Resource document — violations logged as warnings, only the specific violating file ignored going forward (never the whole structure), surfaced to the affected user, and written as a routable Report (Section 7.1).
- **Assistance search:** a Global File Index query scoped to the requesting user's Resource access tier.
- **Ping vs. Message Channel:** Ping is a lightweight Engine-relayed notification with no lock; the persistent pulsing status is Engine-tracked state (unaddressed-count > 0) pushed to the receiving Operator Client, using the same status-indicator mechanism Task's Deadline alerts use (shared component, not duplicated per-feature). The Message Channel's one-message-per-turn lock is Engine-enforced session state, not a client-side-only restriction (so it can't be bypassed by a modified client).
- **Listeners:** an Engine-side subscription on a Message Channel's message stream, added by either party, visible to the adding party only in their own Operator Client view — enforced by scoping the "list of Listeners you added" query to the requesting user's own additions, never a join across both parties' additions.

### 7.5 Control, Events, Monitoring & Actions

- **Events:** native/pushed events are OS signals relayed by the Worker Agent (or Operator Client) to the Engine, which matches them against registered Event definitions; polled/evaluated events (thresholds, scheduled time, idle duration) are an Engine-side scheduled check, run on the Engine's asyncio loop rather than requiring the Worker Agent to self-poll for everything.
- **Actions execute independently, no output piping (v1):** each Action attached to an Event is dispatched as its own independent task/subprocess; ordering is a display concern in the Operator Client, not a data dependency enforced by the Engine.
- **Custom Actions:** see Section 7.3.
- **Dashboard:** the Operator Client's "operational view" mode is a live query against the Engine's Action/Event execution log (itself part of the audit trail, Section 8.4) — refresh mechanism (poll vs. push) is deferred, per Section 9.

---

## 8. Security & Audit

### 8.1 Build-Order Note: Auth Is Last, Scaffolded Early, Never Optional

Following the reference project's approach directly: the message shape auth will occupy (a nonce/challenge-response handshake) is scaffolded from the very first integration pass — the fields exist on every relevant message from day one, with the Engine's check on them stubbed to always accept during development. Real cryptographic logic is filled into that already-wired stub last, after Engine, Operator Client, and Worker Agent are each independently built and tested. This is a sequencing decision, not a scoping one — the system is not safe to run on a real network until this is complete, since Session Blocking, Custom Action execution, and Report visibility all currently assume the caller's identity is trustworthy.

A `DEV_BYPASS_AUTH` flag, off by default, loud when active (logged prominently on Engine startup), skips the handshake **entirely** rather than silently passing its validation — a hard, visible skip rather than a quietly-always-true check, so an accidentally-left-on flag is obvious both in code and on the wire.

### 8.2 Authentication Model

One **master secret**, generated once on the Engine host, never transmitted. Each Worker Agent and Operator Client is issued a **derived key** at provisioning time (`HMAC(master_secret, client_id)`), stored locally under an ACL-restricted path (equivalent to `%ProgramData%` on Windows), never in a user-writable location. Session handshake: Engine issues a nonce, the client responds with `HMAC(derived_key, nonce)`, Engine independently re-derives and compares. Compromising one machine's derived key exposes only that machine — not the master secret, not other clients' keys.

This authenticates *who is allowed to act as which identity* (Super User, a specific Admin, a specific Worker) and is the foundation Session Blocking, Report visibility, and Resource access-tier enforcement all sit on top of — none of those are meaningful without this.

### 8.3 Transport Security

TLS for all Engine ↔ Operator Client and Engine ↔ Worker Agent traffic. Self-signed, pinned certificate is sufficient (one Engine, every client already receives a provisioned install package — a full CA buys nothing at this scale). Hostname-based identity (not IP) so the Engine can move without reissuing certificates. Fails loudly: a missing/invalid certificate stops the Engine starting, or stops a client connecting — never a silent plaintext fallback.

### 8.4 Audit Trail

Every traversal, Session Block/end, Task verification action, Flow sync/conflict/failure, Resource compliance check, Ping/Message Channel/Listener event, Assisted Access session, and Event/Action execution is written to one Engine-owned audit log, structured consistently (who, what, when, target) regardless of which combo generated the entry. **Retention: flat 90 days, system-wide, for v1** (per Hierarchy's Audit & Logging), with category-based tiering as an explicitly noted future option, not a v1 requirement.

---

## 9. Update & Deployment Model

### 9.1 Approval Flows Top-Down

A new version is approved by Super User, consistent with every other system-wide configuration decision in Hierarchy (Report Routing categories, System Alerts) flowing from Super User downward. **A new version (N+1) cannot be approved or begin rolling out until every PC in the system is confirmed on the current version (N).** This is a hard gate, not a soft target — the system is never meant to have more than two versions in flight (N and N+1, transiently, during a single rollout window), and never three.

### 9.2 Rollout Cascade

Once Super User approves N+1, rollout cascades through the hierarchy: Admins execute the rollout within their own departments' Client PCs. This mirrors how operational execution generally sits at the Admin level throughout the system (Task assignment, Flow creation, Control/Events/Monitoring) while Super User retains approval/oversight authority rather than operational involvement.

### 9.3 One-Step-Back Compatibility

Each version supports the immediately preceding version only (N supports N-1; N does not need to support N-2 or earlier). This is what makes a multi-day rollout survivable: during the rollout window, some PCs are on N-1 and some are on N, and this is expected, normal operation — not a fault condition. A PC on N-1 during an in-progress rollout **works normally, without restriction** — N-1 is a fully supported version, not a broken one; treating "hasn't updated yet" as equivalent to "broken" would contradict the entire reason one-step-back compatibility exists.

### 9.4 Failed Updates — Automatic Retry, Not a Stuck State

If a specific update attempt fails (network issue, or any other transient cause), this is not treated as a terminal or stuck state. The system retries automatically, using the same idle-detection mechanism already established for the Global File Index's opportunistic full-system sweep (Section 6.2): whenever the affected PC is idle and has connectivity, another update attempt is made. This is one more consumer of the "notice when idle, act then, back off the moment the user resumes" pattern already used elsewhere, not a new mechanism built specifically for updates.

### 9.5 Escalation

- **Below threshold:** repeated retry failures are expected during ordinary network flakiness and do not, on their own, require anyone's attention.
- **Past threshold** (a configurable count or time-based limit, to be tuned during implementation rather than fixed here): the failure surfaces directly to **that PC's Admin** as an actionable notice — no longer passive, since repeated failure past a reasonable threshold suggests something beyond ordinary flakiness.
- **Super User's view is aggregate, not per-incident:** a standing rollout-health view showing update status across all PCs, **grouped by department** — consistent with Super User's general design principle of high-level, non-overwhelming coverage of the whole hierarchy rather than operational detail. Super User does not receive a flood of individual per-PC failure reports.
- **Super User can still act directly:** from that aggregate, grouped view, if Super User notices a department stalled in a way that suggests the Admin has simply overlooked it, Super User can prompt that Admin directly — a deliberate second lever alongside the automatic per-PC escalation in the point above, not a replacement for it.

### 9.6 Relationship to Report Routing

The per-PC escalation (9.5) to an Admin, and the aggregate rollout-health view for Super User, both reuse the same underlying reporting infrastructure as Report Routing (Section 7.1) — update status is one more Report category Super User always has visibility into, grouped and displayed in the way most useful for this specific case (by department, aggregated) rather than as individual routed reports.

---

## 10. Explicitly Deferred / Open Items

These are known, deliberately postponed — not oversights:

1. **Dashboard refresh mechanism** (polling vs. push) — a UI-layer decision with no effect on the data model; deferred to when Operator Client UI work begins.
2. **Report category → department routing configuration UI** — the data model (Section 7.1) is resolved; the specific Operator Client screen for Super User to configure it is a UI-phase task.
3. **Local LLM hosting architecture** — a shortlist of candidate models is set (Section 7.2.1: Qwen3 small variants as top pick, Gemma 4 E2B and Ministral 3 as alternatives, final size to be chosen empirically), but whether inference runs in-process within the Engine or as a separate local sidecar process the Engine calls over a local interface (e.g., via Ollama) is not yet decided.
4. **Update escalation threshold** (Section 9.5) — whether the retry-failure threshold that triggers Admin escalation is count-based or time-based, and its exact value, is left as a tunable parameter to set during implementation rather than fixed in this document.
5. **CI/CD tooling** — the update/deployment *model* (Section 9) is resolved; the actual pipeline (build tooling, artifact signing, how an approved version is packaged and made available for Admin-executed rollout) is deliberately deferred as an infrastructure task, not a design question.

---

## 11. Implementation Phasing

Adopting the reference project's three-pass approach per component, and its component build order, adapted to three packages instead of two:

**Pass structure (applied to each component in turn):**
1. **Architecture** — already complete (this document plus the six design documents it summarizes).
2. **Scaffold** — module structure, function/class signatures, empty handlers wired into dispatch logic, so the system runs end-to-end with stub behavior before real logic is filled in. Auth's message shape is scaffolded here (Section 8.1) even though its logic comes last.
3. **Implementation** — real logic filled into the scaffold, module by module.

**Component build order:**
1. **Engine** — built and thoroughly tested first, since every other package depends on it. Covers Hierarchy's authority model, the Global File Index, Task/Flow/Resource/Control-Events-Monitoring business logic, and the database layer.
2. **Operator Client** — built and tested second, against the completed Engine.
3. **Worker Agent** — built and tested third, against the completed Engine.
4. **Full integration** (all three together) — built and tested last, once each component is independently verified, so integration bugs are isolated to genuine cross-component interaction rather than tangled with bugs still being worked out inside one component.
5. **Authentication** — implemented last per Section 8.1, but its message shape is present from the Scaffold pass onward.

Given the ~1 month timeline, this ordering is what makes the schedule realistic: a fully correct, independently-tested Engine means Operator Client and Worker Agent work can each proceed against a stable, trustworthy target rather than against a moving one.

---

## 12. Reference Documents

This specification summarizes and adapts, but does not replace, the full design documents:
- Hierarchy System Design
- Task Natural Combo
- Flow Natural Combo
- Resource & Assistance Natural Combo
- Control, Events, Monitoring & Actions Natural Combo
- System Ecosystem — Synthesis

Where this document and any of the above appear to conflict, the detailed combo document is authoritative for *what* the system does; this document is authoritative for *how it's physically built*.






