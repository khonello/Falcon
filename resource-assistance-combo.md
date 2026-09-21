# Resource & Assistance Natural Combo

## Overview

Resource and Assistance work together to ensure workers have access to what they need and can easily find help. Resource establishes a distributed access control system built on the system-wide Global File Index, while Assistance provides file search and structured help communication. Together, they reduce friction in finding information and getting support.

---

## Resource

**Definition:** A system-wide library of allowed company files and resources organized by access tier, with a centralized index that determines what should exist on each PC.

**Core Principle:** The resource folder structure and index serve as the **source of truth** for file distribution and access control across all PCs in the system.

### Folder Structure

**Super User PC:**
```
/resources/
├── /admin/        (files all admins should have access to)
├── /restricted/   (super-user-only, cannot exist anywhere else in system)
└── /common/       (available to all users)
```

**Admin PC:**
```
/resources/
├── /restricted/   (admin-only for that specific PC, cannot propagate)
├── /workers/      (files for all workers in that department)
└── /common/       (available to all users)
```

**Worker PC:**
```
/resources/        (flat folder, all files here)
```

### Global File Index

**Important:** This index is a **system-wide concept**, not something owned by or scoped to Resource. Resource is one consumer of it — Task's Verification and Flow's collision checks also rely on the same index. It's documented here because Resource's compliance/access-tier tracking was the first feature to need it, but its scope is the whole system.

**Purpose:** A single, system-wide index of files, used for search, access-tier compliance, verification target selection, and collision detection across the whole system.

**Tracks:**
- File name and location
- Access tag, where applicable: `admin`, `restricted`, `worker-dept-X`, `common` (Resource-specific; not every indexed file has one)
- Content hash (for tracking restricted files, and for detecting collisions elsewhere in the system)
- File metadata

**How Files Get Indexed:**
- **Event-driven baseline:** files are indexed as they're referenced or touched, via the same OS file events used throughout the system (create, modify, move, copy)
- **Opportunistic full-system indexing:** when a machine is idle (no mouse or keyboard input), the system performs a full file-system sweep to index beyond just what's been event-referenced
- **Self-throttling:** the moment user input resumes, full-sweep indexing stops immediately, so it never competes with the user for resources — consistent with the system's general preference for native events over polling, and for not burdening the user's machine

**Resource's Usage of the Index (Access Tiers):**
- Determines what tagged files should exist on which PCs
- Validates compliance across all PCs
- Tracks restricted file propagation

### Access Control Rules

| File Tag | Super User PC | Admin PC | Worker PC | Notes |
|----------|---|---|---|---|
| `admin` | ✓ in /admin/ | ✗ Cannot exist | ✗ Cannot exist | Only admins; tracked for violations |
| `restricted` | ✓ in /restricted/ | ✓ in /restricted/ (own PC only) | ✗ Cannot exist | Admin-specific; no propagation; tracked by hash |
| `worker-dept-X` | — | ✓ in /workers/ | ✓ in /resources/ (dept X only) | Department-specific workers only |
| `common` | ✓ in /common/ | ✓ in /common/ | ✓ in /resources/ | Everyone can have |

### Restricted File Tracking

**For files tagged `admin` or `restricted`:**
- Tracked by **content hash** (survives renames, copies, moves)
- **Detection mechanism:** Native OS file events (create, move, copy) fire on a PC and are filtered against the Global File Index. If a file matching a restricted/admin-tagged hash appears somewhere its tier doesn't permit, this is detected essentially in real time rather than waiting for a scheduled sweep. **Fallback:** where native event filtering isn't practical, periodic polling of the Global File Index against that PC's filesystem serves the same purpose. This reuses the same detection pattern used for Flow's sync trigger and Task's Expectation tracking, rather than a separate mechanism.
- **Offline PCs:** since detection is event-driven or interval-based, an offline PC simply isn't producing events or being reached by polling. Nothing needs to be specially retried — once the PC reconnects, either its queued OS events are evaluated or the next poll cycle picks up its current state.
- If restricted file detected on unauthorized PC:
  - Violation **logged as a warning** (not auto-deleted)
  - Only **that specific file** is ignored by the system going forward (not synced, not treated as valid) — it doesn't affect the rest of the resource structure on that PC
  - **Surfaced to the affected user** so they can rectify it themselves
  - Audit trail created

**Purpose:** Prevent sensitive files from bleeding across the system while maintaining audit trail. This follows the same general directory structure conflict handling described in the Hierarchy document, applied here to Resource specifically.

### Compliance & Enforcement

**System Validation:**
- Same native-event-first, polling-fallback mechanism as Restricted File Tracking above — not a separate scanning schedule
- Checks:
  - Do authorized files exist on authorized PCs?
  - Are restricted files contained?
  - Are admin files isolated to admins only?
- Reports violations (file exists where it shouldn't, or missing where it should)
- Does not auto-delete; preserves for audit

**Security Isolation:**
- Resource folder cannot be direct source or destination for **Flow** (security boundary)
- But Flow operates under the hood to sync resource files respecting these rules
- Ensures resource files never propagate via system mechanisms to unauthorized PCs

---

## Assistance

**Definition:** Dual-feature support system combining searchable resource discovery and structured help communication.

### File Search

**Purpose:** Help users find resources available to them without asking around.

**How It Works:**
- Users search the Global File Index
- Results filtered by user's access level and role
- Instant access to files they're allowed to use

**Search Visibility:**

| User Type | Can Search |
|-----------|-----------|
| **Worker** | Their department's worker files + common files |
| **Admin** | Their restricted files + worker files + common files + all admin files |
| **Super User** | All files in system |

**Benefit:** Reduces interruptions; users find files independently.

### Help Ping & Message Channel

**Purpose:** Structured help requests up the hierarchy, with two distinct parts — an attention-getting Ping, and a Message Channel that opens once the receiver responds.

**Applies symmetrically at both levels:** Worker↔Admin and Admin↔Super User.

#### Ping

- A ping is a lightweight "I want your attention" signal — like a notification, not a message
- **Repeatable:** if unaddressed, the sender can ping again; there's no lock on pinging itself
- The receiving superior sees a **persistent, unmistakable status** (bright, bold, pulsing) showing unaddressed pings
- This status is the accountability mechanism in place of a timeout: it makes non-response visibly a choice rather than silently disappearing, so there's no need to badger the receiver further beyond re-pinging
- The status clears only when **all** pending pings/messages are addressed

#### Message Channel (opens once the receiver responds)

Once the superior responds to a ping, a Message Channel opens between sender and receiver, governed by the same **one-message-per-turn lock** as before:

```
User: [sends message] → LOCKED
Superior: [receives] → [responds] → UNLOCKED
User: [sends next message] → LOCKED
Superior: [receives] → [responds] → UNLOCKED
```

**Rules:**
- One message at a time per direction
- No back-and-forth chatting
- Each exchange: question → answer → next question
- Lock prevents casual messaging

**Closing Authority:**
- Only the **superior** (the receiver of the original ping, regardless of who initiated) can close the channel — Admin closes Worker↔Admin channels; Super User closes Admin↔Super User channels
- This holds even when the superior was the one who pinged first (e.g., Admin pings Worker for information) — it would be equally inappropriate for the subordinate to unilaterally end a channel while their superior is the one enquiring
- The sender has no unilateral closing authority

**Purpose:** Keeps communication **structured and straight-to-the-point**; prevents channels from becoming noisy or unfocused, while the Ping mechanism separately ensures unaddressed requests remain visible rather than silently timing out.

**Logging:**
- All pings and messages logged with timestamps
- Part of audit trail
- Tracks communication patterns and response times

#### Listeners (Message Channel Extension)

**Purpose:** Allow a Message Channel to be silently observed by a third-party Admin — for example, routing a workplace issue to Human Resources without disrupting the conversation itself.

**How It Works:**
- Either party in the channel (sender or receiver) can add a Listener
- A Listener must be an **Admin**
- If both parties independently add the same person as a Listener, it's deduplicated to one — no duplicate listening
- Listeners see the channel's messages **in real time**, as they happen
- A single Listener can observe multiple channels simultaneously

**Awareness — Asymmetric, Not Fully Covert:**
- Whoever adds a Listener can see the list of Listeners **they themselves added**, and can add more at any time
- The **other party** in the channel has no visibility into Listeners the first party added — they are not informed
- This is available from an options/menu control at the top of the channel, made available once the channel is started

**Accountability:**
- Even though visibility between the two channel parties is asymmetric, the full flow is captured in the **audit trail**: who started the conversation, who added whom as a Listener, and when
- This is what keeps the mechanism accountable despite the participants not having full mutual visibility — consistent with how the rest of the system favors audit trail over restriction as its accountability mechanism

---

## Resource + Assistance Working Together

**Workflow Example:**

1. **Worker needs a file:**
   - Uses Assistance file search
   - Finds `contract-template.docx` in their department's worker resources
   - Downloads and uses it
   - No need to ask admin

2. **Worker has question about file:**
   - Pings admin via Help Ping — attention-getting notification
   - Admin responds → Message Channel opens
   - Sends: "How do I fill out the contract-template?"
   - Message locked; waits for response
   - Admin responds: "Section 3 is auto-filled; edit Section 4 manually"
   - User unlocked; sends next question if needed
   - Admin (the superior) closes the channel once resolved

3. **Admin wants to share new resource:**
   - Places `new-policy.pdf` in Resource `/workers/` folder
   - Index updated automatically
   - Next sync pushes file to all department workers
   - Workers discover it via Assistance search

---

## Integration with Other Combos

**With Task:**
- Task's File verification targets are selected from the Global File Index, scoped to the assignee's Resource access — a Worker can only be assigned a file target they're actually permitted to see
- Workers find files via Assistance search
- A Create-intent File target (a not-yet-existing deliverable) is checked for name collisions against the same Global File Index Resource itself is built on

**With Flow:**
- Flow syncs resource files to appropriate PCs
- Resource rules enforced (admin files don't go to workers)
- Flow respects resource access tiers

**With Hierarchy:**
- Resource access determined by user role in hierarchy
- Help Ping and Message Channel follow the hierarchy chain (Worker↔Admin, Admin↔Super User), with closing authority always resting with the superior in that pair
- Super User sees all resources; Admin sees admin + worker + common; Worker sees worker + common
- Listener reports generated on Message Channels are one Report category that can be routed to a department (e.g., HR) via Hierarchy's Report Routing, while Super User always retains full visibility regardless of routing
- Resource compliance violations (restricted/admin file breaches) are likewise a Report category under the same Report Routing model — routable to a relevant department, always visible to Super User

---

## Key Principles

1. **Index as Policy** — Resource folder structure + centralized index = distributed access control
2. **Search Over Asking** — Users find files independently via Assistance search
3. **Ping vs. Message Channel** — Ping is a repeatable, lock-free attention signal with a persistent status replacing the need for a timeout; the Message Channel (one-message-per-turn) only opens once the superior responds
4. **Superior Closes** — Regardless of who initiated, only the superior in the pair (Admin, or Super User) can close a Message Channel
5. **Listeners for Oversight** — either channel party can silently add an Admin as a real-time observer (e.g., for HR-style oversight); awareness is asymmetric (each side only knows what they added), but the full flow is captured in the audit trail
6. **Native-First Compliance Detection** — restricted/admin file violations detected via OS file events filtered against the Global File Index, with polling as fallback; same pattern as Flow and Task
7. **Security Isolation** — Restricted files tracked and contained; violations reported not deleted
8. **Role-Based Visibility** — Each user sees only resources their role permits
9. **Audit Trail** — All resource access, pings, messages, and compliance checks logged
10. **Flat Worker Structure** — Worker PCs don't need subfolders; index determines content

---

## Implementation Notes

- **Global File Index:** Built via event-driven indexing (OS file events) plus opportunistic full-system sweeps during machine idle time, self-throttling the moment user input resumes; Resource's folder contents are indexed the same way, tagged with their access tier
- **Hash Tracking:** Implement content-based file tracking for restricted files (MD5, SHA-256)
- **Compliance Detection:** Native OS file events (create/move/copy) filtered against the Global File Index for near-real-time detection; polling fallback where native detection isn't practical; no special handling needed for offline PCs beyond catching up on reconnect
- **Ping Status:** Persistent, high-visibility (bright/bold/pulsing) indicator for unaddressed pings on the receiver's interface; clears only when all pending pings/messages are addressed
- **Message Lock Mechanism:** Implement message lock in the Message Channel UI (disable send button until superior responds); Ping itself has no lock
- **Channel Closing:** Restrict close action to the superior in the pair, regardless of who initiated
- **Flow Integration:** Ensure Flow respects resource access rules when syncing files
- **Logging:** Log all resource access, searches, pings, messages, and compliance violations
