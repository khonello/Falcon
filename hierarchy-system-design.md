# Hierarchy System Design

## Overview

**This hierarchy structure is the backbone of the entire system. All other features and functionality are built on top of this foundational architecture.**

A multi-level traversal architecture supporting three user types (Super User, Admin, Client) operating within a single software platform. Each user type has distinct traversal depth, operational scope, and functional responsibilities.

---

## Identity Model

**This definition underlies everything else in this document and every combo that references "who" or "which PC."**

- **Identity is the account, not the PC.** Every reference to "who" throughout this system — Display Names, audit attribution, Task assignment, Ping/Message Channel participants, Report Routing's "which Admin addressed this," Session Blocking's "who is occupying this session" — resolves to an **account**.
- **An account is bound to exactly one PC**, for the account's lifetime (until Offboarding & Deprovisioning). Not many-to-many, not roaming across machines. One account, one PC.
- **This is an enforced constraint, not a soft default.** A person attempting to use their account from a PC other than the one it's bound to, or a PC receiving a second account binding while already bound, is a **deviation from the expected shape** — this is treated as **user error**, and the system's responsibility is to **detect and clearly surface it**, not to silently accommodate or guess at intent. This is consistent with the system's general posture elsewhere: ambiguity and deviation are surfaced, never silently resolved (see Task's governing LLM principle for the same posture applied to a different kind of ambiguity).
- **This confirms, rather than changes, several things already built on this assumption implicitly:** Task's Program Intent verification (targets on "the assignee's specific PC"), Resource's per-PC folder structure, Session Blocking's PC-as-the-occupied-unit, and Offboarding's "PC is the pause boundary, not the person" were all already designed as if this binding held. This section makes that assumption explicit and authoritative rather than leaving it implicit.

---

## Traversal Path & Depth

### Organizational Hierarchy Structure

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
          ├── ADMIN
          │     ├── CLIENT PC
          │     └── CLIENT PC
          │
          └── ADMIN
                ├── CLIENT PC
                ├── CLIENT PC
                ├── CLIENT PC
                └── CLIENT PC
```

### Traversal Capabilities by User Type

**Super User Traversal Flow:**
```
SUPER USER (native level)
    ↓ (can traverse down)
DEPARTMENT (traversal point - sees all departments)
    ↓ (can traverse down)
ADMIN (traversal point - sees specific admin's view with red banner)
    ↓ (can traverse down)
CLIENT PC (traversal endpoint - can control as client would)
    ↓ (back)
ADMIN → DEPARTMENT → SUPER USER (can traverse back up)
```

**Admin Traversal Flow:**
```
ADMIN (native level)
    ↓ (can traverse down)
CLIENT PC (traversal endpoint - monitor and control as client would)
    ↓ (back)
ADMIN (can traverse back up)
```

**Client Flow:**
```
CLIENT PC (no traversal - read-only information surface)
```

---

## Traversal Boundaries

Traversal grants control, but not unconditional or unlimited control. Three boundaries apply whenever a traversal session is active, all enforced through the same permission-based approach used elsewhere in the system (Resource's access tiers) rather than through any content-invisibility mechanism.

**Super User Exemption:** Conditional Rendering and Traversal-Restricted Files & Folders (below) do not apply when the traverser is Super User. Super User sees and can access everything at any depth of traversal — into an Admin's interface, or straight through to a Client PC — consistent with how Super User's traversed view already mirrors exactly what the traversed-into level sees. Super User sits above the rest of the hierarchy, so no content boundary applies to them; the only safeguard is that every action is logged, same as any other traversal. **Session Blocking still applies** to Super User traversal — that mechanism governs concurrent control, not visibility, and holds regardless of who is traversing (see Session Blocking During Traversal below for the full model, including how Super User can end or block an Admin's session to enter it).

### Session Blocking During Traversal

Traversal concurrency is governed by a small set of rules that together define exactly one thing: **who can enter an occupied session, and how.**

**Session, not traversal, is the unit that gets blocked.** When a session is occupied — whether that's a Worker's native use of their own PC, an Admin's own interface, or a session currently itself mid-traversal into something deeper — the whole session is blocked to anyone else, not just the specific traversal action happening inside it. A block persists for as long as the occupying session continues, and lifts only when that session ends.

**Sequential gating — you cannot see or target what's beyond a session until you're inside it.** Super User's path down the hierarchy is strictly sequential: to reach a Client PC under a given Admin, Super User must first occupy that Admin's own session. The specific Client PCs under that Admin aren't visible or selectable until Super User is already inside the Admin's session — there is no way to bypass the Admin and reach a Client PC directly, even though the traversal path conceptually runs Department → Admin → Client PC.

**Traversal can only begin when the destination session is idle.** This is the precondition for starting any traversal, at any level.

**Vertical relationships — block-or-end-first, then enter:**
- If the destination session is not idle (someone is actively working in it, or it is itself mid-traversal into something deeper), the party wanting to enter **must first explicitly block or end that session** before their own traversal can begin. This is a deliberate, explicit pre-step — not an automatic side effect of attempting entry. There is no scenario where a session is silently interrupted mid-action; blocking/ending always happens first, and only then does the new traversal start.
- **Super User can end an Admin's session** (or block it) to take control. This applies whether Super User's ultimate goal is the Admin's own interface, or reaching a Client PC further down through that Admin — the gating step is identical either way, since the Admin's session must be entered first regardless of Super User's ultimate destination.
- **Admin can end/block a Worker's session** the same way, to begin traversal into that Client PC.
- Once the superior's traversal has begun, the block on the session they now occupy **remains in place for as long as their own session there continues.**

**Horizontal relationships — no blocking or ending rights, ever:**
- An Admin has **no authority to block or end another Admin's session**, under any circumstance. If Admin A is occupying a Client PC (or otherwise has an active session Admin B wants), Admin B is simply **refused entry** — shown as the destination being unavailable — and must wait until Admin A's session ends naturally. There is no mechanism, deadline, or escalation that shortens this wait horizontally.

**Un-evictable at the top:** A Super User currently occupying/blocking an Admin's session cannot be ended or blocked by anyone — not the Admin whose session it is, and not another Super User. Eviction rights only ever flow downward.

**Traversal Time Limit:** Every traversal into or through an Admin has a fixed duration limit, with the option to request an extension as the limit nears. This limit is counted **at the Admin level**, regardless of whether the party currently occupying that level is the Admin's own superior traversing in, or Super User traversing further down through that Admin — from a timing perspective, Super User occupying that position is treated the same as an Admin would be. The remaining duration is displayed on the Admin's own interface, so the Admin always has visibility into how much time remains on the session currently occupying their level.

**Overlay Indicator:** While a session is blocked (traversal ongoing, at any level), an overlay is shown on that destination indicating it is currently inaccessible / under traversal — visible to whoever would otherwise be using it, without necessarily disclosing who is traversing or why.

### Conditional Rendering During Active Traversal

Certain program elements check whether a traversal is currently active into a given PC, and render differently for the traverser when it is (hidden, restricted, or altered). This is a standard permission check evaluated at render time — `if traversal_active: apply restriction` — using the same tag/permission infrastructure as Resource's access tiers, not a separate rendering-layer mechanism. There is no content that is invisible to the system itself; restricted elements are governed by a permission check like everything else, and their state is logged the same way.

### Traversal-Restricted Files & Folders

Specific files or folders can be tagged as **traversal-restricted** — normally accessible to their owner (e.g., a Worker on their own PC), but blocked from being opened by the traverser specifically while an active traversal session is in control. This reuses the same tagging/permission mechanism already established in Resource for tiered access, with `traversal_active` as the trigger condition rather than a fixed role tier.

**Visible, not hidden:** a traversal-restricted folder or file remains **visible** in listings during traversal — it is not hidden from view. Attempting to open it is blocked, consistent with the permission-based approach (a denied action, logged) rather than making it disappear from the traverser's view entirely. This keeps the boundary transparent rather than covert.

**Audit:** every traversal session, and every restriction it triggers (a blocked render, a blocked file/folder open), is logged as part of the same traversal audit trail described under Audit & Logging.

---

## Cross-Department Assisted Access

**Definition:** A consent-based, temporary, peer-to-peer access relationship between Admins — distinct from the vertical Traversal system described above, not an extension of it. This exists to solve a real gap the hierarchy's authority-based Traversal has no answer for: an Admin needing hands-on technical help from a peer (e.g., an Admin in Finance needing IT's help with a PC issue), where neither Admin outranks the other.

**Why this is a separate mechanism, not Traversal:** Traversal is authority-based and permanent (a superior always outranks their subordinate) and, for horizontal relationships, explicitly grants **no** blocking or eviction rights (see Traversal Boundaries → Session Blocking During Traversal). Assisted Access is the deliberate exception to that horizontal "no rights" rule — but it works entirely differently: access here is **granted by consent**, not seized by authority, so it does not use the block-or-end-first mechanic Traversal requires. Keeping this as its own named mechanism, rather than quietly loosening the horizontal rule, keeps Traversal's authority model clean.

**Scope:** Works both across departments (the primary case — Admin in one department getting help from an Admin in another) and within the same department (an Admin helping a peer in their own department).

### Two Entry Paths

- **Requester-initiated:** An Admin needing help requests assistance, optionally targeting a specific department. The system matches to an available Admin in that department — available meaning not currently occupying a session (per Session Blocking) and opted in as reachable for assistance.
- **Helper-initiated:** An Admin can proactively broadcast their availability for assistance, which a requester can then act on directly.

Both paths are active simultaneously — this isn't an either/or choice between two designs, but two ways into the same mechanism.

### No Lingering Requests

If no Admin is available at the moment a request is made, the requester is simply told to try again — the request is never queued waiting for someone to eventually become free. Availability is a moment-in-time thing on both sides: the helper's availability can change, but so can the requester's own situation (issue resolved, no longer needing help), so a stale match made later is more likely to be wrong than useful.

### Access Limitations — Two Layers

Because this crosses departmental boundaries, access is deliberately narrower than what a superior would see in ordinary vertical Traversal:

1. **System-defined baseline ceiling:** a hard limit on what a helper can ever see or touch, fixed per department/Admin regardless of configuration (e.g., a helper never sees Resource files or Message Channels beyond what's strictly necessary for the kind of assistance being given).
2. **Requester-configured narrowing:** the requester can further restrict what the helper can access, within that ceiling — they can narrow it further, but never loosen it beyond the system-defined baseline.

### Session Behavior

Once a helper is matched and access is granted, the session behaves like an ordinary occupied session (overlay shown, session blocked to others, per Session Blocking During Traversal) — the difference is entirely in *how access begins*: by consent here, versus block-or-end-first authority in vertical Traversal. There is no eviction mechanic needed for Assisted Access, since it was never seized by authority in the first place — it ends when the assistance session is closed by either party.

### Reporting

Fully self-service — no Super User approval is required to initiate or accept an assistance session. However, every instance generates a report under its own category (e.g., "Cross-Department Assistance"), which Super User always receives per the standard Report Routing model (see Report Routing) — Super User retains full visibility without gating the interaction itself.

---

## User Types Summary

| User Type | Traversal Depth | Role | Primary Function |
|-----------|---|---|---|
| **Super User** | 3 levels | Oversight & Governance | Monitor hierarchy health, audit operations, maintain system integrity |
| **Admin** | 1 level | Operational Control | Day-to-day monitoring and control of client PCs within department |
| **Client** | None | Information Consumer | Receive alerts and information; no active control of software |

---

## Department Creation & Assignment

**Creation:** Departments are created by **Super User**, consistent with every other system-wide structural decision in this design (Report Routing categories, System Alerts, version approval) flowing from Super User downward.

**Admin Assignment:** An Admin is assigned to a Department by Super User — the same authority that creates the Department also populates it, and this pairs naturally with Display Names, since Super User is already the one who labels each Admin for their own identification.

**Zero-Admin Departments:** A Department can transiently have zero Admins — either because it was just created and hasn't had one assigned yet, or because an offboarded Admin was its only one (see Offboarding & Deprovisioning). This is **allowed, not disallowed** — disallowing it would force awkward ordering constraints (blocking Department creation until an Admin is ready, or blocking Admin removal if they're the last one in that Department). A zero-Admin Department is instead **surfaced** in Super User's aggregate oversight views, the same way Update & Deployment's rollout-health view surfaces a stalled department — visible, not hidden, but not a hard error state either.

---

## Super User

**Traversal Capability:**
- Sees all Departments
- Selects a Department
- Views Admins within that Department (a Department can have multiple Admins)
- Selects a specific Admin
- Interface reflects exactly what that Admin sees (logs, status, all data)
- Can further traverse to view Client PCs under that Admin
- Can traverse into Client PC control as if they were the Admin

**Interface Indicator:**
- Red banner displayed: "Super User in charge" (indicates traversal status)

**Operational Focus:**
- Reports (departments, admins, clients across hierarchy)
- Audit logs (who did what, when)
- System status (aggregated health across all levels)
- High-level summaries (not overwhelming, comprehensive coverage)

**Data Visibility:**
- Aggregated view of all departments
- Count of Admin users per department
- Count of Client users per department
- Traversal audit trail

---

## Admin

**Traversal Capability:**
- Views all Client PCs within their assigned Department
- Selects a specific Client PC
- Traverses into Client PC to monitor and control
- Uses the Client PC interface as the client would (mouse, keyboard, full control)
- Can perform individual PC monitoring and control or department-wide monitoring and control

**Interface Indicator:**
- Operates at Admin interface (standard operation, no special banner unless Super User has traversed into their view)

**Operational Focus:**
- Source of all monitoring and control operations
- All features concentrated at this level to apply to clients
- Individual PC operations
- Department-wide operations
- Client monitoring and control
- Policy enforcement and task assignment

**Data Visibility:**
- Full logs of client activity
- Client PC status and health
- Client alerts and notifications
- Audit trail of admin actions

---

## Client

**No Traversal**

**Operational Focus:**
- Passive information consumer
- Surfaces relevant alerts and notifications
- Displays system status and information
- No active control of the software system itself

**Special Case: Task Interaction**
- **Exception to read-only rule:** When tasks are assigned to a Client, they can:
  - View assigned tasks
  - Start/acknowledge a task (marks task as "started")
  - Monitor work progress (see expectations being tracked in real-time)
  - Work on the task's target file(s)/program(s)
- **Cannot:** Mark tasks as complete — only the assigner can perform manual verification
- **Logging:** Task start action and all work activity is logged

**Data Visibility:**
- Information and alerts only
- System notifications
- Status updates relevant to their PC
- Assigned tasks and progress signals

---

## Audit & Logging

**Traversal Logging:**
- Every traversal is logged with:
  - **Who:** User performing traversal (Super User or Admin)
  - **What:** Which level they traversed to (Department, Admin, Client PC)
  - **When:** Timestamp of traversal action
  - **Duration:** How long they operated at that level

**Operational Logging:**
- All monitoring and control actions at Admin level are logged
- Actions on Client PCs are logged by Admin
- Provides complete audit trail for compliance and accountability

**Access Trail:**
- Super User traversals into Admin interfaces are tracked
- Allows reconstruction of "who was viewing as whom and when"

**Retention:**
- **Flat 90-day retention, system-wide, for v1.** All audit log entries (traversals, operational actions, alerts, resource violations, task verification history, event/action executions, Assisted Access and Listener reports, etc.) are kept for 90 days from creation, then purged. One flat window across every category, rather than tiered retention by category — 90 days comfortably covers a full business quarter, which is long enough for accountability disputes, compliance investigations, and HR-relevant matters (Listener reports, Cross-Department Assistance) to surface without needing a longer-retained category, while remaining simple to build and reason about within the v1 timeline.
- **Revisit later:** if usage shows specific categories genuinely need shorter or longer retention (e.g., routine Flow sync logs vs. long-term compliance records), retention can be split by Report category at that point, reusing the categorization already established in Report Routing — but this is not required for v1.
- Every combo's document that references logging (Task, Flow, Resource & Assistance, Control/Events/Monitoring) defers to this section rather than defining its own retention rule.

---

## Offboarding & Deprovisioning

**Definition:** What happens when a person (Admin or Worker) is removed from the hierarchy — the account is deactivated, not deleted.

**Records Preserved:** Audit history, task verification history, and past reports attributed to the offboarded person remain intact and attributable — nothing is retroactively erased. These records still expire naturally under the standard 90-day Retention policy above, the same as any other audit entry; offboarding does not trigger early deletion, and it does not extend retention either.

**The PC, Not the Person, Is the Pause Boundary:** Everything associated with the offboarded person's PC — active Flows sourced from it, Resource tracking on it, Task activity tied to it — is **paused**, not deleted or silently reassigned. Flow's existing Failure Handling pause mechanism (see Flow Natural Combo) is reused here rather than inventing a separate pause behavior: the reasoning is the same either way — nothing meaningful can change on a PC that's genuinely not in use, so pausing rather than continuing to track/sync is both correct and cheaper.

**Resuming After a New Onboarding:** When a new person is onboarded onto that same physical PC, the previously paused Flows, Resource tracking, and Task associations **do not silently resume or transfer** to the new occupant. The new person does not inherit the prior occupant's context — anything relevant (a Flow sourcing from that PC, Resource tier assignment, task assignment) must be explicitly re-established for them. This prevents a new hire's account from accidentally becoming attributed to work, sync history, or access tiers that were actually configured for someone else entirely.

---

## System Expectations & Deviation Handling

**Principle:** Throughout this system, specific expectations define what a correct, well-formed state looks like — an account bound to one PC, a restricted file confined to one machine, a flow moving in one direction only. When reality deviates from an expectation, this is treated uniformly: **the deviation is logged, the affected party is informed, and the system's standard is stated alongside it** — never silently corrected, never silently tolerated, and never allowed to quietly cascade into other behavior as if it were valid. This is the same posture already used for Task's LLM-surfaced ambiguity and Resource's violation reporting, generalized here as one system-wide rule rather than left as several independently-invented local rules that happen to agree.

**What counts as a deviation, and what standard it's measured against, is defined per feature — this section does not introduce new rules, it names the pattern already present throughout the design and lists where it currently applies:**

| Expectation | Where Defined | What a Deviation Looks Like |
|---|---|---|
| One account is bound to exactly one PC | Identity Model | Account used from an unbound PC, or a PC receiving a second binding |
| A restricted/admin-tagged file exists only where its tier permits | Resource & Assistance | The tagged file (by content hash) detected on an unauthorized PC |
| A directory/file structure matches what the hierarchy defines for that level | Directory Structure Conflicts (below) | An Admin-scoped structure appearing where Worker-scoped is expected, or vice versa |
| Flow moves data one-directionally, source to destination | Flow Natural Combo | A destination file modified by anything other than the flow's own sync write |
| A task's verification target/deadline/scope is unambiguous | Task Natural Combo | The LLM's decision graph reaches an unclear or contradictory leaf |
| A Report is never itself generated as a routable Report | Report Routing | N/A by construction — enforced at the schema/query level (see Implementation Specification), not a runtime deviation to detect |
| A new PC occupant does not inherit the prior occupant's paused state | Offboarding & Deprovisioning | A Flow, Resource tracking entry, or Task silently resuming under a new account without explicit re-establishment |

**Consequence, uniformly:** every row above already specifies, in its own section, that a deviation is logged and surfaced rather than silently handled — this section exists to make that a named, recognizable pattern rather than something a reader has to notice independently in each combo. Any future expectation added to any combo should follow this same shape: state the expectation, log the deviation when it occurs, inform the affected party, and never silently resolve it on the system's own authority.

---

## Key Design Principles

1. **One Software, Three Views** — Single platform adapts its interface based on user type and traversal depth

2. **Feature Concentration at Admin Level** — All monitoring and control features live at the Admin interface because Admins are the operational authority over Clients

3. **Super User as Governor** — Observes hierarchy health, performs audits, maintains oversight; does not perform day-to-day operations

4. **Client as Observer** — Receives information and alerts; does not actively use the software for management

5. **Traversal Transparency** — Red banner on Super User traversals ensures everyone understands who is "in control" when operating through another user's interface

6. **Complete Audit Coverage** — Every traversal and every action is logged for compliance, accountability, and security

7. **Bidirectional Movement** — Users can traverse down to deeper levels and back up to their native level seamlessly

---

## Example Scenarios

### Scenario 1: Super User Auditing Department Operations
1. Super User logs in → sees all Departments
2. Selects "Department A"
3. Sees Admin1 and Admin2 managing Department A
4. Selects "Admin1"
5. Interfaces reflects Admin1's view (logs, status, client list)
6. Red banner: "Super User in charge"
7. Reviews Admin1's recent actions and client status
8. Traverses back to Department view, then back to Super User dashboard

**Audit Log Entry:** "SuperUser001 traversed to Admin1 interface in Department A at 2024-01-15 10:30 UTC, duration: 12 minutes"

### Scenario 2: Admin Managing a Specific Client PC
1. Admin1 logs in → sees all Client PCs in Department A
2. Selects "Client PC-047" (a computer lab machine)
3. Interface shows Client PC-047's view
4. Remotely controls the PC using mouse and keyboard
5. Applies department-wide policy update to all PCs
6. Traverses back to Department view

**Audit Log Entry:** "Admin1 accessed Client PC-047 in Department A at 2024-01-15 10:45 UTC, performed: [policy update, access duration: 25 minutes]"

### Scenario 3: Client Receives Alert
1. Client user at Client PC-047
2. Software surfaces alert: "Department policy update applied - restart required by end of day"
3. Client views system status
4. No active software control available to client

---

## Auto-Created Directory Structure (Resource)

Each user level has its own local, auto-created Resource directories, scoped to what that level needs:

```
Super User:
resource/
  restricted/
  admin/

Admin:
resource/
  restricted/
  workers/

Worker:
resource/
```

**Resource scoping:** see Resource & Assistance Natural Combo for full access-tier rules.

**Note on Task:** Tasks do not have an auto-created directory structure — targets (files or programs) are tracked by identity via the Global File Index and OS events, wherever they actually live, not by a task-specific location. See Task Natural Combo for full detail.

### Directory Structure Conflicts

This scoping applies system-wide — not just to Resource, but to any other hierarchy-defined structure. If a directory or file structure exists on a PC that doesn't match what the hierarchy says should be there for that user's level (e.g., an Admin-scoped structure appearing where a Worker-scoped one is expected, or vice versa):

- The conflict is **logged as a warning**, not silently corrected or auto-deleted
- Only the **specific part that violates the rule** is ignored by the system going forward (not synced, not treated as valid) — the rest of the structure around it is unaffected
- The violation is **surfaced to the affected user** so they can rectify it themselves

This mirrors the same non-destructive, report-don't-delete principle used for Resource violations, generalized to any structure the hierarchy governs.

---

## Display Names

**Definition:** Every account and PC has an underlying ID (used internally for paths, indexing, and audit logs) and, separately, a human-recognizable **display name**. Display names exist so users aren't shown cold, opaque identifiers when referring to each other — but naming authority is strictly top-down, and naming visibility does not propagate beyond the relationship it was set in.

### Naming Authority (Top-Down Only)

- **Super User:** the only user who chooses their **own** display name. Whatever Super User sets is what **Admins** see when Super User is referenced to them.
- **Super User → Admin:** Super User can assign a display name to each Admin (and their PC), purely for **Super User's own identification**.
- **Admin → Worker:** Admin can assign a display name to each Worker (and their PC), purely for **Admin's own identification**.

Nobody names themselves except Super User. Everyone else is named by the level directly above them.

### Naming Visibility Does Not Propagate

Each naming relationship is **private to that pair** — it does not carry down to the next level:

- The name **Super User sets for an Admin** is visible only to Super User. It is never what that Admin's Workers see when referring to that Admin.
- What a **Worker sees**, when their Admin is referenced (e.g., "Admin X assigned you this task"), is whichever name the **Admin has set for themselves** — a separate, self-facing name, distinct from whatever Super User privately calls that Admin.
- If the Admin has **not** set a self-facing name, the Worker sees the **composed fallback name** (built from account/PC identifiers, e.g., `Admin — {account-id}`) — never the name Super User uses for that Admin internally, even if one exists.

**In short:** naming is scoped per relationship, not global. An Admin could be clearly named in Super User's view while still appearing under a composed fallback name to their own Workers, if the Admin never set a name facing their Workers.

### Fallback Naming

If no display name has been set for a given relationship, the system does not fall back to an arbitrary or opaque code — it composes a fallback from the same identifying components already used elsewhere in the hierarchy (department, account name/id, PC id), so the relationship is still inferable at a glance even without a chosen name.

- **Worker's view of an unnamed Admin:** composed from Admin's account identifier (e.g., `Admin — {account-id}`)
- **Admin's view of an unnamed Worker:** composed from whatever disambiguates at that level (e.g., `{account-id}` or `{pc-id} + {account-name}`)
- **Super User always self-names**, so this case doesn't arise at that level

This is not an error state — it's simply less friendly than a chosen name, and nudges toward setting one. Fallback composition applies independently per relationship, following the same non-propagation rule above — it never borrows a name or label set for a different relationship layer.

---

## System Alerts & Announcements

**Definition:** System-wide or role-specific messages that inform users of important information, from emergencies to routine notifications.

**Types:**
- **Emergency Alerts:** Critical system issues, immediate action required
- **Warnings:** Important changes or conditions to be aware of
- **Announcements:** Scheduled updates, policy changes, general information
- **Routine Alerts:** Regular notifications (reminders, status updates)

**Filtering & Distribution:**

| Alert Type | Recipients | Created By |
|-----------|-----------|-----------|
| Admin-only | All Admins, Super User | Super User or Admin |
| Department-specific | Admins & workers in that department | Super User or Department Admin |
| All-users | All users in system | Super User |
| Specific-user | Individual user(s) | Super User or Admin |

**Scheduling:**
- Immediate delivery
- Scheduled for future date/time
- Recurring (daily, weekly, etc.)

**Delivery:**
- Alert surface in user interface based on their role
- Logged in system for audit trail
- Can include action links (e.g., "Update required by X date")

**Purpose:**
- Maintains cohesion across hierarchy
- Ensures critical information reaches appropriate users
- Supports system-wide coordination without requiring direct communication
- Provides audit trail of all alerts sent

---

## Report Routing

**Definition:** A Super User-configured feature that additionally routes categories of system-generated reports to specific departments, so the responsible department's Admin(s) can act on them — without ever removing Super User's own visibility.

### Two Distinct Categories

This feature depends on a strict distinction between two kinds of system output:

- **Reports (routable):** system-generated output describing an event that occurred — Resource violations, Directory Structure Conflicts, Flow failures, Listener reports from Message Channels, compliance issues, and similar. Reports are auto-categorized by type as they're generated, since the system already knows a report's origin (e.g., "Resource violation," "Flow failure," "Listener report").
- **Views/Dashboards (never routable, Super User-only):** meta-level information *about* reports and routing itself — for example, which reports have been marked addressed, by which department, and when. Because a View is a distinct category from Report, it can never be routed away from Super User; this also avoids an infinite-regress problem where "a department addressed a report" would itself need to be a routable report.

### How Routing Works

- **Super User always receives every report**, regardless of routing configuration. Routing is **additive, not exclusive** — it never removes Super User's visibility into anything.
- Super User can configure a **report category** to also route to a specific department. Once a category is routed, every report generated under that category goes to both Super User (always) and the routed department.
- **A department can have more than one Admin** (per the hierarchy tree). Routing targets the department as a whole, not one designated contact within it — **every Admin in the routed department sees the routed report pane.** No separate "which specific Admin is the routing contact" concept exists; introducing one would add a layer of configuration this design doesn't otherwise need, since Admins within one department already share operational visibility over the same Client PCs.
- Only departments configured as receivers for a given category have that report pane appear in their interface — an unrouted category simply isn't routed anywhere beyond Super User, who already sees it by default.
- Within a routed department, **any Admin** in that department (not Workers) sees the routed report pane and can mark individual reports as **seen** or **addressed**.
- An Admin marking a report addressed does not modify or remove Super User's own copy of that report. Instead, it generates/updates a **Super User-only View** — tracking which department (and which Admin within it) addressed which report, and when — entirely separate from the routable Report category.

### Example

```
Report Category: "Listener Report" (from Message Channel oversight)
Routed to: HR Department

New Listener report generated:
  → Super User sees it (always)
  → Every Admin in HR Department also sees it (because this category is routed to HR)

An HR Admin marks it "addressed":
  → HR's shared pane updates to reflect addressed status for every HR Admin
  → Super User's View (meta-level, Super-User-only) updates to show
    "Listener report X — addressed by [that HR Admin] — [timestamp]"
  → Super User's original copy of the report itself is untouched
```

**Why this matters:** without routing, every report generated anywhere in the system would default to sitting only with Super User — which contradicts the design principle that Super User's interface should stay high-level and uncluttered (see Super User's Operational Focus). Routing lets the department actually responsible for a category of issue (HR for interpersonal oversight, IT for sync/technical failures, etc.) act on it directly, while Super User retains full, permanent visibility as the system's ultimate auditor.
