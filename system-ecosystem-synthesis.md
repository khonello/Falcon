# System Ecosystem — Synthesis

## Overview

This is not a collection of independent tools bolted together. It's a single ecosystem built on one backbone (Hierarchy) with five natural feature combos that share the same structure, the same audit trail, and the same underlying mechanisms — native OS events over polling, a single system-wide file index, and one governing rule for every LLM-assisted decision: propose and surface uncertainty, never silently resolve it. The value isn't any one combo — it's that they all speak the same language and work together seamlessly.

A company doesn't need Jira for tasks, Synology for sync, a separate ticketing tool for help requests, and a separate monitoring suite — all disconnected, all requiring context-switching. Here, one hierarchy governs all of it.

Each section below corresponds to one full document. What follows after is how they tie together as a system.

---

## Hierarchy

*Full document: Hierarchy System Design*

The backbone. Three user types, distinct traversal depth, one software.

```
SUPER USER
    │
    └── DEPARTMENT
          │
          ├── ADMIN
          │     ├── CLIENT PC
          │     ├── CLIENT PC
          │     └── CLIENT PC
          │
          └── ADMIN
                ├── CLIENT PC
                └── CLIENT PC
```

- **Super User** — traverses Department → Admin → Client PC; sees reports, audits, hierarchy-wide status. Red banner marks traversal into another user's view. Exempt from content-restriction boundaries (Conditional Rendering, Traversal-Restricted Files) at any depth — sees everything, always logged.
- **Admin** — traverses to Client PC only; the operational center, where control and management concentrate.
- **Client** — no traversal; passive information recipient, with the exception of interacting with assigned Tasks (view, start, monitor — never verify).
- **Session Blocking:** occupying a session (Admin's own, or a Client PC) blocks it to everyone else. Vertical relationships (Super User→Admin, Admin→Worker) can block-or-end an occupied session to enter; horizontal relationships (Admin↔Admin) have no such rights — simply refused until the session frees naturally. A Super User occupying a session is un-evictable. Traversal has a fixed, extendable time limit, counted at the Admin level regardless of who's occupying it.
- **Cross-Department Assisted Access:** a separate, consent-based mechanism (not Traversal) letting an Admin request or offer peer-to-peer technical help across (or within) departments, scoped by a system-defined ceiling the requester can further narrow. Self-service; reported to Super User.
- **Display Names:** naming is strictly top-down and never propagates between relationship layers — what Super User privately calls an Admin is invisible to that Admin's Workers, who see only what the Admin sets for themselves (or a composed fallback built from existing identifiers).
- **Report Routing:** Super User always receives every report; routing is additive, letting a report category (Resource violations, Listener reports, Flow failures, etc.) also reach a responsible department's Admin. A separate, Super-User-only View tracks what's been addressed — never itself a routable report.
- **System Alerts** ride on top — emergency, warning, announcement, or routine — filtered by role, scheduled or immediate.
- **Retention:** flat 90 days, system-wide, for v1.

Every traversal and action is logged: who, what, when.

---

## Task

*Full document: Task Natural Combo*

A unit of work, assigned to a user account. No auto-created workspace directory — targets are tracked by identity via the Global File Index and OS events, wherever they actually live.

- **Verification is the anchor:** defines the end outcome first. A local LLM turns a plain-language description into a populated structure — verification targets, Intent, and Deadline — that the assigner reviews and can correct.
- **Intent governs the check:** File targets get Create / Update / Exists; Program targets get Used / Used With File / Installed-Available / Closed-Not Running. A Create-intent target is name-first, with collisions against the Global File Index surfaced for resolution.
- **Expectation:** soft signals derived from each target's Intent (file events for File; activity, memory footprint, open file descriptors for Program) — shows work is happening, never proves completion.
- **Deadline:** one soft and one final deadline per task, both implemented as scheduled Events, surfaced via the same pulsing status-indicator pattern used elsewhere.
- **Completion:** only manual verification by the assigner closes a task — never automated, never per-item.
- **Governing principle:** the LLM proposes and surfaces ambiguity — an unclear target, an ambiguous deadline, a description covering multiple tasks — it never silently decides.

Client exception: can view, start, and watch progress — cannot verify.

---

## Flow

*Full document: Flow Natural Combo*

A one-directional sync pipeline, so changes never conflict.

- **Source → Destination(s):** one-directional, branches like a river. Placement of Transformation/Categorization before or after a Branch determines whether it's shared across destinations or specific to one.
- **Destination Consent:** created without approval only when the creator already outranks the destination owner; lateral flows and flows into a superior's space need explicit consent.
- **Pre-Flight Collision Check & Cycle Prevention:** both validated against the Global File Index / flow graph before a flow is accepted, never silently overwritten or allowed to loop.
- **Change detection:** native OS file events filtered against registered flow sources, polling as fallback; conflict detection uses write attribution (hash + who + hierarchy level) so a flow never mistakes its own write for an external one.
- **Failure handling:** a failure pauses only the affected flow/branch, persists as a status until resolved, and surfaces a predefined fix suggestion reactively — never configured upfront.

---

## Resource & Assistance

*Full document: Resource & Assistance Natural Combo*

The resource folder structure *is* the access policy, built on the system-wide Global File Index.

- **Resource:** tiered folders (`admin`, `restricted`, `workers`, `common`); the Global File Index is built via event-driven indexing plus opportunistic full sweeps during idle time, self-throttling the moment input resumes. Restricted files tracked by content hash system-wide; violations reported, never silently deleted.
- **Assistance:** search the index (filtered by role) instead of asking around.
- **Ping vs. Message Channel:** a Ping is a repeatable, lock-free attention signal with a persistent pulsing status in place of a timeout; the Message Channel (one-message-per-turn) opens only once the superior responds, and only the superior can close it.
- **Listeners:** either party can silently add an Admin as a real-time observer on a Message Channel (e.g., HR oversight) — awareness is asymmetric, but the full flow is audited.
- Resource can't be a direct Flow source/destination — Flow moves resource files under the hood instead, respecting the same access tiers.

---

## Control, Events & Monitoring

*Full document: Control, Events, Monitoring & Actions Natural Combo*

The automation and intelligence layer — lives at the Admin interface only; Super User traverses in rather than getting a parallel tool.

- **Actions:** atomic operations — **Control** (do something) or **Monitoring** (observe something) — each with its own timeout and manual termination, independent of others in the same chain (no output piping between them in v1).
- **Events:** native/pushed for OS-emitted conditions, polled for state/threshold/scheduled conditions — the mechanism follows what's actually being watched.
- **Custom Actions:** Admin-authored PowerShell/Python, standard-library-plus-Windows-native only, no sandboxing — accountability comes from the audit trail rather than execution isolation.
- **Dashboard:** toggles between editing (build events/actions in tabs, including Custom) and an operational view showing live status and outputs of everything running.

---

## How They Tie Together

Individually, each section above is a self-contained system. What makes this a product rather than five products is how they reinforce each other, and how much of that reinforcement comes from reusing the *same underlying mechanisms* rather than inventing a new one per combo:

| From → To | What happens |
|---|---|
| **Task → Flow** | Once a Task's target file exists (tracked by identity, not location), a Flow can source from wherever it lives and distribute it onward |
| **Task → Events** | "Verification target file appears," "task started," or a deadline Event can trigger Monitoring/Control actions (screenshot, notify admin) |
| **Resource → Flow** | Flow moves resource files under the hood, but only within the access tiers Resource defines, checked against the same Global File Index |
| **Resource → Events** | Unauthorized access to a restricted file can trigger an Event (log, alert, snapshot), detected the same native-event-plus-polling way Flow's sync trigger works |
| **Events → Control** | A detected Flow failure, Resource violation, or missed deadline can trigger a Control action (rename, restore, revoke, notify) automatically |
| **Task/Flow/Resource → Global File Index** | Verification targets, collision checks, and compliance detection all validate against one shared index, not three separate ones |
| **Any Combo → Report Routing** | Flow failures, Resource violations, Listener reports, and Assisted Access sessions are all Report categories — Super User always sees them, and each can additionally route to a responsible department |
| **Everything → Hierarchy** | Every action, traversal, sync, verification, ping, and report is logged under the same audit trail, retained 90 days, filtered by the same role structure |

**The pattern:** Hierarchy defines who can see, do, and traverse what — including the fine-grained mechanics of who can block or evict whom, and how peers can still consensually help each other outside that authority chain. Task, Flow, and Resource define what gets done and how it moves, all grounded in one shared file index instead of separate bookkeeping. Events + Actions make the system respond on its own, without a person watching every file. Nothing in any of this operates outside the audit trail — one log, one hierarchy, one system.

**The pitch, in one line:** not "we invented task management" — it's "we architected an ecosystem where task management, sync, access control, and automation are one coherent system instead of five disconnected tools."

**Where this stands:** the architecture is no longer just conceptually cohesive — Task, Flow, Resource & Assistance, and Control/Events/Monitoring have each been stress-tested against real implementation questions (concurrency, collision handling, ambiguity resolution, execution trust), and Hierarchy has absorbed the mechanics (Session Blocking, Routing, Assisted Access) that the other four turned out to depend on. What's still open: the Dashboard's refresh mechanism (deferred to UI work), and whatever surfaces once actual implementation begins.

