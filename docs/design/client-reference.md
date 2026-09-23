# Client (Worker) Reference

**What this document is:** every capability, data view, and responsibility that belongs to the Client/Worker role, pulled from across all system design documents (Hierarchy, Task, Flow, Resource & Assistance, Control/Events/Monitoring, Implementation Spec, Database Schema) and organized by category. This is a role-facing reference, not a new design — see the source documents for full mechanism detail; this is "everything Client can see and do," in one place.

Client is deliberately the thinnest role in the system — by design, an information consumer with one narrow, explicit exception (Task interaction). Most of this document is short precisely because most features have nothing for Client to configure.

---

## Common to All User Types

Applies identically to Super User, Admin, and Client:

- **Identity:** account bound to exactly one PC, for the account's lifetime. Using an account from an unbound PC, or a PC receiving a second binding, is a deviation — logged and surfaced, never silently accommodated. For Client specifically, this is the everyday case: one Worker, one PC, one account.
- **Display Names:** every account/PC has an internal ID and a separate display name. Client never names themself or anyone else — naming is strictly top-down (Admin names each Worker, for Admin's own identification). What Client sees when their Admin is referenced is whichever self-facing name that Admin has chosen to set — or a composed fallback (e.g., `Admin — {account-id}`) if the Admin hasn't set one.
- **System Expectations & Deviation Handling:** if something about Client's own PC or account deviates from what the system expects (e.g., the account is somehow used from an unbound PC), it's logged and surfaced to Client — never silently corrected behind the scenes.
- **Audit Trail:** Client's task starts, work activity, resource access, pings, and messages are all logged. Flat 90-day retention, system-wide, for v1.
- **System Alerts & Announcements:** can receive alerts scoped to "all users," department-specific, or targeted specifically at them.
- **Offboarding:** if Client is deactivated, their history is preserved (not deleted), subject to standard 90-day retention. The PC itself — not the person — is the pause boundary: everything tied to it (active Flows sourced from it, Resource tracking, Task activity) pauses until a new person is explicitly onboarded onto that same PC. The new occupant does **not** inherit any of it automatically.

---

## 1. Traversal & Hierarchy Position

- **No traversal capability whatsoever.** Client operates only at their own native level — there is no "traverse down" for Client, because there is nothing below Client in the hierarchy.
- **Read-only information surface**, by default — see the Task exception in §2, which is the one deliberate carve-out from this rule.
- **Can be traversed into.** An Admin (or Super User, traversing through that Admin) can enter Client's session to monitor and control it directly, using mouse/keyboard as Client would. While this is happening:
  - Client's session shows an **overlay indicator** that it's currently under traversal/inaccessible — visible to Client, without necessarily disclosing who is traversing or why.
  - Certain files/folders tagged **traversal-restricted** remain visible in listings to the traverser but cannot be opened by them while the traversal is active — this restriction does not apply if Super User is the one traversing (Super User is exempt from this specific boundary).
  - The session is fully blocked to Client (and to anyone else) for the duration of the traversal — Client simply cannot use their own PC until the session ends.
  - Every traversal into Client's PC, and every restriction it triggers, is logged as part of the standard audit trail.

---

## 2. Task — The One Exception to Read-Only

This is the single area where Client actively interacts with the software rather than just observing it.

**Client can:**
- **View assigned tasks** — whatever an Admin has assigned to their account.
- **Start/acknowledge a task** — this marks it "started" and begins Expectation tracking.
- **Monitor their own work progress** — see Expectations (soft progress signals) being tracked in real time as they work.
- **Work on the task's target file(s)/program(s)**, wherever they naturally save/use them — there's no dedicated Task Directory they're confined to. Targets are tracked by identity (via the Global File Index and OS file events), not by location.

**Client cannot:**
- **Mark a task complete.** Only the Admin who assigned it can perform Manual Verification and close it out. Client's role ends at doing and acknowledging the work — the assigner is the sole authority on whether it's actually done.

**What Client sees while working:**
- The task's Verification Stack status is visible to the assigner (Admin), not necessarily broken out item-by-item to Client — Client's own view is oriented around "here's what I'm supposed to do and how it's tracking," not the assigner's full pass/fail breakdown.
- Deadline indicators (Soft and Final) use the same shared, persistent status-indicator pattern as Help Ping's unaddressed-message signal — a bold/pulsing visual as a deadline approaches or is reached.

**Logging:** task start and all subsequent work activity on the target(s) is logged, same as everything else in the system.

---

## 3. Resource & Assistance

**Resource — own folder structure (flat, no subfolders):**
```
/resources/
(flat folder, all files here)
```
Index-driven — what appears here is determined by what the Admin has pushed to `/workers/` (their department) or `/common/` (everyone), synced in via Flow under the hood.

**File Search (Assistance):** Client can search files scoped to **their department's worker files + common files** — the narrowest search scope of any role, but sufficient to find what's actually relevant to them without needing to ask.

**Help Ping & Message Channel — Client is the subordinate in the Worker↔Admin pair:**
- **Can Ping** their Admin — a lightweight, repeatable "I need attention" signal, no lock, can be re-sent if unaddressed.
- Once Admin responds, a **Message Channel** opens: one-message-per-turn lock (Client sends → locked → Admin responds → unlocked → Client can send next).
- **Cannot close the channel** — only the Admin (the superior in the pair) can do that, regardless of who initiated.
- **Cannot see Listeners** added to a channel by the Admin side — Listener visibility is asymmetric; Client would only know about Listeners *they themselves* added (and Client cannot add a Listener at all, since a Listener must be an Admin).

---

## 4. Everything Client Does Not Have Access To

Stated explicitly, since Client's document is otherwise short — these are deliberately absent, not omissions:

- **No Department, Admin, or cross-department visibility** of any kind.
- **No Report Routing visibility** — Reports and Views are Admin/Super-User-level concepts entirely; Client never sees a routed report pane.
- **No Flow creation or management** — Flow operates on Client's files under the hood (as a destination, or as a source an Admin has configured), but Client has no interface for it.
- **No Control, Events, Monitoring, or Custom Actions interface** — this entire combo lives at the Admin level only; Client is the *subject* of monitoring/control actions (e.g., an Admin might screenshot or remote-control Client's PC), never the operator of them.
- **No Cross-Department Assisted Access** — this is an Admin-to-Admin mechanism only.
- **No Update approval authority** — Client's PC receives updates per the cascading rollout model, same as any endpoint, with no configuration role.

---

## Key Takeaway

Client's document is short because the design intends it to be: **"Client as Observer"** is a stated Key Design Principle, not an underdeveloped area. The single deliberate exception — Task interaction — exists because a Worker needs enough agency to actually do assigned work and see their own progress, without ever being handed the authority (Manual Verification) that would let them mark their own work "done." Everything else Client experiences is something happening *to* or *for* them (monitoring, control, resource distribution, alerts) rather than something they configure.
