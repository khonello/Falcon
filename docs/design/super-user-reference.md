# Super User Reference

**What this document is:** every capability, data view, and responsibility that belongs to the Super User role, pulled from across all system design documents (Hierarchy, Task, Flow, Resource & Assistance, Control/Events/Monitoring, Implementation Spec, Database Schema) and organized by category. This is a role-facing reference, not a new design — see the source documents for full mechanism detail; this is "everything Super User can see and do," in one place.

---

## Common to All User Types

Applies identically to Super User, Admin, and Client:

- **Identity:** account bound to exactly one PC, for the account's lifetime. Using an account from an unbound PC, or a PC receiving a second binding, is a deviation — logged and surfaced, never silently accommodated.
- **Display Names:** every account/PC has an internal ID and a separate display name. Naming is top-down only (see Super User's own naming authority below) and never propagates beyond the relationship it was set in.
- **System Expectations & Deviation Handling:** whenever any part of the system deviates from its defined expectation, the deviation is logged, the affected party is informed, and the standard is stated — never silently corrected or tolerated.
- **Audit Trail:** every traversal, action, sync, violation, and communication is logged. Flat 90-day retention, system-wide, for v1.
- **System Alerts & Announcements:** can receive alerts scoped to "all users" or targeted specifically.
- **Offboarding:** if deactivated, account history is preserved (not deleted), subject to standard 90-day retention.

---

## 1. Traversal & Hierarchy Position

- **Native level:** top of the hierarchy — sees all Departments.
- **Traversal depth:** 3 levels — Department → Admin → Client PC.
- **Traversal path (sequential, cannot skip):**
  1. Select a Department → see all Admins in it (a Department can have multiple Admins)
  2. Select a specific Admin → interface reflects exactly what that Admin sees (logs, status, all data)
  3. From inside the Admin's session, traverse further to a specific Client PC under that Admin
  4. Interface reflects Client PC control, exactly as the Admin would use it (mouse, keyboard, full control)
- **Cannot skip levels:** Client PCs under a given Admin are not visible or selectable until Super User is already inside that Admin's session (sequential gating).
- **Interface indicator while traversed in:** red banner — "Super User in charge."
- **Bidirectional movement:** can traverse back up (Client PC → Admin → Department → Super User native view) at any point.

### Session Blocking — Super User's Entry Rights

- **Traversal can only begin into an idle session.** If the destination (an Admin's session, or that Admin's own traversal further down) is currently occupied, Super User must explicitly **block or end that session first** — this is a deliberate pre-step, never an automatic interruption.
- **Super User can end or block an Admin's session**, whether the goal is the Admin's own interface or reaching a Client PC further down through that Admin (the gating step is identical either way).
- **Un-evictable:** once Super User occupies/blocks a session, nobody — not the Admin whose session it is, not another Super User — can end or block Super User out of it. Eviction rights only flow downward.
- **Traversal Time Limit** applies to Super User the same as it would to the Admin themself — counted at the Admin level, with an extension request available as the limit nears. The Admin sees the remaining duration on their own interface regardless of who is occupying it.

### Traversal Boundaries — Super User Exemption

- **No content boundary applies to Super User.** Conditional Rendering restrictions and Traversal-Restricted Files & Folders (which apply to Admin-level traversal into a Client PC) do **not** apply when Super User is the traverser — Super User sees and accesses everything at any depth.
- **Session Blocking still applies** to Super User regardless of this exemption — the exemption is about visibility, not concurrency control.
- Every action taken while traversed in, exempted or not, is logged the same as any other traversal.

---

## 2. Department & Admin Management

- **Department creation:** Super User is the only role that creates Departments.
- **Admin assignment:** Super User assigns Admins to Departments.
- **Zero-Admin Departments are allowed** (transiently — newly created, or an offboarded Admin was the last one). Surfaced in Super User's aggregate oversight views, not treated as an error.
- **Naming authority over Admins:** Super User can assign a display name to each Admin (and their PC), purely for Super User's own identification. This name is private to the Super User↔Admin relationship — it does not propagate to that Admin's own Workers.
- **Own display name:** Super User is the only role that chooses their own display name (all other roles are named top-down).

---

## 3. Cross-Department Assisted Access — Oversight Only

Super User does not participate directly in Assisted Access (it's a peer-to-peer, consent-based mechanism between Admins), but retains full visibility:

- Every Assisted Access session generates a report under its own category ("Cross-Department Assistance"), which Super User **always** receives per the standard Report Routing model — no approval gate, but full visibility is retained.

---

## 4. Reports & Views

- **Always receives every Report**, regardless of routing configuration — routing to a department is additive, never exclusive, and never removes Super User's own copy.
- **Configures Report Routing:** can designate a Report category (e.g., "Listener Report," "Resource Violation," "Flow Failure") to also route to a specific Department. Every Admin in that Department then sees the routed report pane in addition to Super User.
- **Views/Dashboards are Super-User-only and never routable** — meta-level information about which department addressed which report, and when. This prevents infinite regress (a department's handling of a report never itself becomes a routable report).
- **Sees, specifically:**
  - Aggregated view across all Departments
  - Count of Admins per Department, count of Clients per Department
  - Full traversal audit trail (who traversed to whom, when, for how long)
  - High-level summaries (deliberately not a firehose of every operational detail — that lives at Admin level)
  - Rollout-health view for Updates, grouped by department (see §7)
  - Zero-Admin Department flags

---

## 5. Task, Flow, Resource, Control/Events — Access Model

Super User does **not** get separate, parallel tools for these combos. In every case, Super User's access is **by traversal into an Admin's interface**, not a standalone system-wide equivalent:

- **Task:** Super User *can* create tasks directly and assign them at the Department level (accountable: the Admin or Admins in that Department) — this is the one combo where Super User acts natively rather than only via traversal.
- **Flow:** Super User can create flows at the department or system level directly.
- **Resource:** Super User has their own `/resources/` structure (`/admin/`, `/restricted/`, `/common/`) and can search **all files in the system** via Assistance's File Search — the widest visibility of any role.
- **Control, Events, Monitoring, Custom Actions:** **no native interface at all.** This entire combo lives at the Admin interface only. To create or manage an automation, Super User must traverse into a specific Admin's interface and operate there exactly as that Admin would. There is no system-wide automation dashboard for Super User.

---

## 6. Assistance

- **File Search:** can search **all files in the system**, unrestricted by department or tier — the only role with this scope.
- **Message Channel / Ping:** participates as the superior in the Admin↔Super User relationship — Admins ping Super User for help; once Super User responds, a Message Channel opens under the same one-message-per-turn lock. **Only Super User can close** an Admin↔Super User channel, regardless of who initiated it.
- **Listeners:** Super User is not restricted from being added as a Listener on a channel (the Listener role requirement is simply "must be an Admin" — Super User traversing in to act as an Admin-equivalent observer would follow the same traversal rules as anything else).

---

## 7. Update & Deployment Model

- **Approves version rollouts** — the top-down cascading rollout model requires Super User approval to begin, and N+1 cannot be approved until all PCs have confirmed on N.
- **Sees aggregate rollout-health view**, grouped by department — not a per-incident flood of every individual PC's update status.
- **Manual escalation lever:** can manually "notify Admin" for a stalled or failed update rather than waiting for the automatic threshold-based escalation.
- Benefits from the one-step-back (N supports N-1) compatibility model, which makes a multi-day rollout survivable without forcing all PCs to update in lockstep.

---

## 8. Audit & Accountability (Super-User-Specific)

- **Traversal audit trail:** every traversal Super User performs is logged with who, what level, when, and duration (e.g., *"SuperUser001 traversed to Admin1 interface in Department A at 2024-01-15 10:30 UTC, duration: 12 minutes"*).
- **Access trail reconstruction:** the system supports answering "who was viewing as whom and when" specifically because Super User's traversal is logged with this level of detail.
- Super User's own actions while traversed in (control actions, monitoring actions, task/flow/report changes) are logged exactly as if the native Admin had performed them, attributed correctly to Super User as the actor.

---

## Key Takeaway

Super User's role is **governance, not operation.** Every mechanism above skews toward aggregate visibility, approval authority, and audit — not hands-on day-to-day control. Where hands-on control is genuinely needed (a specific automation, a specific flow), the design deliberately routes Super User through traversal into the Admin's own interface rather than building a second, parallel operational surface — this is a stated design principle ("Super User as Governor"), not a gap.
