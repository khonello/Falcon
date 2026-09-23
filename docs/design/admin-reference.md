# Admin Reference

**What this document is:** every capability, data view, and responsibility that belongs to the Admin role, pulled from across all system design documents (Hierarchy, Task, Flow, Resource & Assistance, Control/Events/Monitoring, Implementation Spec, Database Schema) and organized by category. This is a role-facing reference, not a new design — see the source documents for full mechanism detail; this is "everything Admin can see and do," in one place.

Admin is where the system concentrates almost all day-to-day operational feature surface — this is by design (see Key Design Principle: "Feature Concentration at Admin Level").

---

## Common to All User Types

Applies identically to Super User, Admin, and Client:

- **Identity:** account bound to exactly one PC, for the account's lifetime. Using an account from an unbound PC, or a PC receiving a second binding, is a deviation — logged and surfaced, never silently accommodated.
- **Display Names:** every account/PC has an internal ID and a separate display name. Naming is top-down only — Admin does not name themself (see §1 for who names Admin, and how Admin names Workers).
- **System Expectations & Deviation Handling:** whenever any part of the system deviates from its defined expectation, the deviation is logged, the affected party is informed, and the standard is stated — never silently corrected or tolerated.
- **Audit Trail:** every traversal, action, sync, violation, and communication is logged. Flat 90-day retention, system-wide, for v1.
- **System Alerts & Announcements:** can receive alerts scoped to "all users," "Admin-only," or department-specific; can also **create** Admin-only or department-specific alerts (see §1).
- **Offboarding:** if deactivated, account history is preserved (not deleted), subject to standard 90-day retention. When Admin is offboarded, everything tied to their PC is paused (not deleted or reassigned) until a new occupant is explicitly onboarded onto it.

---

## 1. Traversal & Hierarchy Position

- **Native level:** operates within one assigned Department.
- **Traversal depth:** 1 level — down to Client PCs within their own Department only.
- **Traversal path:** sees all Client PCs in their Department → selects one → traverses in → operates it exactly as the Client/Worker would (mouse, keyboard, full control).
- **No special banner** at native Admin interface — the red "Super User in charge" banner only appears when Super User has traversed into the Admin's own view.
- **Can traverse back up** to Department-wide (their own department) view at any point.
- **Both individual and department-wide operation:** Admin can act on a single Client PC, or apply an action/policy across the whole department at once.

### Session Blocking — What Admin Can and Cannot Do

- **Can end/block a Worker's session** to begin traversal into that Client PC — same block-or-end-first rule Super User uses against Admin.
- **No authority over other Admins' sessions, ever (horizontal).** If another Admin is occupying a session Admin wants, Admin is simply refused entry (destination shown unavailable) and must wait for it to end naturally. No blocking, no ending, no escalation that shortens the wait.
- **Cannot evict Super User.** If Super User is occupying/blocking the Admin's own session, the Admin has no way to end or interrupt that.
- **Traversal Time Limit** is visible on the Admin's own interface, showing remaining duration on whatever session currently occupies the Admin's level (whether that's the Admin's own superior, or Super User passing through).
- **Traversal-Restricted Files & Folders:** when Admin traverses into a Worker's PC, certain tagged files/folders may be blocked from being opened by Admin specifically (visible in listings, but not openable) — this restriction does **not** apply to Super User traversing into the same PC.

---

## 2. Cross-Department Assisted Access

The one mechanism designed specifically for **horizontal** Admin-to-Admin help, deliberately separate from vertical Traversal (no authority relationship required):

- **Requester-initiated:** request help, optionally targeting a specific department; system matches to an available Admin there (available = not occupying a session, and opted in as reachable).
- **Helper-initiated:** proactively broadcast own availability for assistance; a requester can act on it directly.
- **No lingering requests:** if nobody's available, the requester is told to try again — never silently queued.
- **Access is narrower than ordinary Traversal, two layers:**
  1. System-defined baseline ceiling — a hard limit on what any helper can ever see/touch cross-department.
  2. Requester-configured narrowing — requester can restrict further within that ceiling, never loosen beyond it.
- **Fully self-service** — no Super User approval needed to start or accept a session. Ends when either party closes it (no eviction mechanic needed, since access was never seized by authority).
- **Reported automatically** under its own category; Super User always sees it, without gating the interaction.

---

## 3. Department & Naming

- **Cannot create Departments or self-assign** — this is Super User's authority only.
- **Naming authority over Workers:** Admin assigns a display name to each Worker (and their PC), purely for Admin's own identification.
- **Admin's own self-facing name:** Admin can set a name that Workers see when Admin is referenced to them — separate from whatever name Super User privately uses for that Admin. If Admin hasn't set one, Workers see a composed fallback (e.g., `Admin — {account-id}`), **never** the name Super User uses internally.

---

## 4. Reports & Views

- **Sees Reports routed to their Department** — if Super User has configured a Report category (e.g., "Listener Report," "Resource Violation," "Flow Failure") to route to Admin's Department, **every Admin in that Department** sees the routed pane (not just one designated contact).
- **Can mark a routed report "seen" or "addressed"** — this updates a Super-User-only View tracking who addressed what and when; it does not modify or remove Super User's own copy of the original report.
- **Does not see reports outside their own routed categories/department** — routing is scoped; an unrouted category simply isn't visible to Admin at all (it still reaches Super User by default).
- **Cannot see or access Views** — those are Super-User-only, by design (prevents infinite regress).

---

## 5. Task (Full Creation & Verification Authority)

- **Creates tasks**, assigned to a Client PC (specific user account on that PC is accountable).
- **Primary creation path:** describes the task in natural language; a local LLM populates Verification targets (File/Program), Intent, item types, Expectations, and Deadline automatically.
- **Reviews LLM-populated structure:** confirms if sufficient; corrects/adds via manual `[+ item]` editor if not; must explicitly confirm "None" if no verification applies (never a silent LLM default).
- **Resolves ambiguity the LLM surfaces:** unclear verification target, ambiguous deadline (e.g., "by Monday or Wednesday"), a name collision on a Create-intent target, or a description that looks like multiple tasks (accept the proposed split, or keep as one task) — the LLM always proposes, Admin always decides.
- **Sets Deadline:** Soft (early nudge) and Final, extracted from natural language or edited directly; implemented as scheduled Events.
- **Monitors Expectations in real time** as the assigned Worker works — File targets (create/modify signals via OS events) or Program targets (activity, memory footprint, open file descriptors) — always a soft signal, never proof of completion.
- **Manual Verification — Admin-only authority:** reviews verification stack status (per-item pass/fail) plus the actual work at each target's location, then marks the **entire task** complete or incomplete as one unit. The assigned Worker cannot close their own task.
- **No Task Directory to manage** — targets are tracked by identity via the Global File Index and OS events, wherever the Worker actually saves them.

---

## 6. Flow (Full Creation & Management Authority, Within Department)

- **Creates flows within their Department** — source and destination on Admin/Client PCs they have authority over.
- **Destination Consent:** no approval needed when Admin already has authority over the destination (e.g., flow into a Worker's PC in their own department). Approval **is** required when the destination is lateral (another Admin's space, cross-department) or upward (into Super User's space).
- **Pre-Flight checks before a flow is accepted:**
  - **Cycle Prevention** — validated automatically; a cycle-causing change is rejected until resolved.
  - **Collision Check** — proposed destination path checked against the Global File Index; an existing unrelated file there is surfaced to Admin, who must choose a different path or confirm the overwrite is intentional.
- **Configures Stages:** Branch (new destinations), Transformation (format conversion, mid-flow only), Categorization (destination-side organization by type) — placement before/after a Branch determines shared vs. per-destination scope.
- **Handles Conflicts:** when a destination file is modified externally (not by the flow's own sync write, per write-attribution check), the modified file is renamed `-modified` and a fresh synced copy takes its place — both preserved.
- **Handles Failures:** sees a persistent failure status (scoped only to the affected flow/branch — unaffected branches keep running) that doesn't clear on its own; clicking it surfaces a predefined, reactive fix suggestion; the flow/branch resumes automatically once resolved.
- **Full flow operations:** create, edit stages/destinations, pause/resume, monitor sync status, view sync history/conflicts, delete.

---

## 7. Resource & Assistance

**Resource — Own folder structure:**
```
/resources/
├── /restricted/   (admin-only, own PC, no propagation)
├── /workers/      (all workers in Admin's department)
└── /common/       (everyone)
```

- **Places files** in `/workers/` or `/common/` to distribute to their department — indexed automatically, synced out via Flow under the hood.
- **Restricted file tracking:** files tagged `restricted` are tracked by content hash; if one appears somewhere its tier doesn't permit, it's logged as a warning, only that specific file is ignored going forward, and it's surfaced to the affected user to fix.

**Assistance — File Search visibility:** their own restricted files + worker files + common files + all admin-tier files (the broadest search scope below Super User).

**Help Ping & Message Channel — Admin is the superior in the Worker↔Admin pair:**
- Receives Pings from Workers (persistent, bold/pulsing status until all are addressed).
- Once Admin responds, a Message Channel opens (one-message-per-turn lock).
- **Only Admin can close** a Worker↔Admin channel, even if Admin was the one who pinged first.
- Admin is also the **subordinate** in the Admin↔Super User pair — can Ping Super User, but only Super User can close that channel.

**Listeners:**
- Admin can be **added as a Listener** on a Worker↔Admin (or any) Message Channel by either party in that channel, for oversight purposes (e.g., HR-style routing) — must be an Admin to qualify.
- Sees the full real-time content of any channel Admin is added to as a Listener.
- Can see the list of Listeners **they themselves added** to a channel; has no visibility into Listeners the *other* party added.
- Can observe multiple channels simultaneously.

---

## 8. Control, Events, Monitoring & Custom Actions — Admin's Primary Domain

**This entire combo lives at the Admin interface only** — there is no parallel Super User tool; Super User must traverse into Admin's interface to touch any of this.

- **Creates and manages Events** (native/pushed — OS-emitted signals like file changes, USB, login/logout; or polled/evaluated — thresholds, idle duration, schedules).
- **Attaches Actions to Events** — Control (mouse/keyboard control, shutdown/reboot, run script, process control, config change, file operations) or Monitoring (screenshots, system metrics, file/program "stalking," pattern-matched keylogging, network activity, process monitoring).
- **Actions execute independently** when attached to the same event — no output piping between them (v1); listed order is display-only; one action's failure doesn't block another.
- **Every Action has a timeout**, and can be **manually terminated** once started, independent of that timeout.
- **Authors Custom Actions** — arbitrary PowerShell or Python, standard-library + Windows-native modules only (no external packages), no sandboxing (accountability comes from the audit trail since only trusted Admins can author them). Listed under their own **Custom** tab.
- **Toggles Dashboard mode** (live view of running automations and outputs) vs. **Editing mode** (Events/Control/Monitoring/Custom tabs, building and configuring).
- **Views all output:** screenshots, metrics/data, logs, status messages, timestamps — filterable and sortable.

---

## 9. Update & Deployment

- **N-1 PCs continue working normally** while a rollout is in progress — not blocked.
- **Failed updates auto-retry** on idle + connectivity (reusing the Global File Index's idle-detection pattern).
- **Escalation:** if a PC's update keeps failing past a threshold, Admin is automatically escalated to.
- Super User can also manually trigger a "notify Admin" for a stalled update, independent of the automatic threshold.

---

## Key Takeaway

Admin is the **operational center of gravity** for the entire system. Nearly every hands-on feature — Task creation and verification, Flow configuration, Resource distribution, Control/Events/Monitoring automation, Message Channel handling — lives here, scoped to Admin's own Department. Where Admin needs help outside their normal authority (a peer's technical problem), Cross-Department Assisted Access exists specifically to cover that gap without borrowing from vertical Traversal's authority model.
