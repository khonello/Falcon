# Flow Natural Combo

## Overview

Flow is a one-directional synchronization pipeline that defines how resources (files, data) travel from a source to one or multiple destinations. Like a river that can branch, flows can split into multiple paths, pass through stages/stops, and reach various endpoints. The system ensures destinations stay in sync with source changes while preventing conflicts through one-directional data movement.

---

## Flow Definition

A flow specifies:
- **Source:** Where changes originate (directory on Admin PC or Client PC)
- **Destination(s):** Where resources end up (Admin PC, Client PC, or remote storage)
- **Stages/Stops:** Optional intermediate processing points (manual checkpoints)
- **Synchronization:** Automatic propagation of source changes to all destinations

**One-Directional Principle:** Source → Destination(s) only. This prevents conflicts from bidirectional changes.

---

## Core Components

### Source

**Definition:** The origin point of the flow.

**Properties:**
- Located on Admin PC or Client PC
- Directory containing files/resources to be synced
- Any changes in this directory trigger propagation to destination(s)
- Read authority over downstream (destinations read source as ground truth)

### Destination(s)

**Definition:** Target endpoints where resources are synced.

**Properties:**
- Can be Admin PC, Client PC, or remote storage
- Receives changes from source
- Read-only relationship with source (downstream)
- Multiple destinations possible (branching)
- Can become source for another flow (chaining)

**Cycle Prevention:** Since a destination can become another flow's source, chaining creates a real risk of a cyclic flow (A → B → A). To prevent this, any flow change — a new flow, a new branch, or a change to an existing one — is validated for consistency **before it's saved**. This check runs automatically and reports an explicit status: pass, or a reported issue if a cycle would be created. The change is not accepted while a cycle issue is unresolved.

**Destination Consent:** Whether a flow can be created without approval depends on the relationship between the flow's creator and the **destination's owner** — not simply the direction of the hierarchy:

- **Creator already has authority over the destination** (e.g., an Admin creating a flow whose destination is a Worker's PC in their own department; Super User creating a flow into an Admin's PC): **no consent needed.** The creator's existing authority over that space covers it — the flow is created and logged, same as any other action within that authority.
- **Destination is outside the creator's authority** — this covers two cases:
  - **Upward:** the destination is a superior's space (e.g., a flow whose destination is an Admin's PC, created by someone without authority over that Admin — or an Admin creating a flow into Super User's space)
  - **Lateral:** the destination is at the same hierarchy level as the creator, but not under the creator's own authority (e.g., Worker → Worker in the same department, or Admin → Admin across departments)
  
  In both cases, **the destination's owner must explicitly consent/approve before the flow can be created.** Lateral flows remain genuinely useful (e.g., workers collaborating within a department) and are not disallowed — they simply require the receiving party's approval, since nobody has inherent authority over a peer's space.

**The general rule:** the destination owner's consent is required unless the flow's creator already outranks (has existing authority over) that destination. Downward flows within one's own authority are the only case where consent is implicit.

**Pre-Flight Collision Check:** Before a flow is accepted, its destination path is checked against the Global File Index for existing, unrelated content already at that location — this is distinct from runtime Conflict Handling (see below), which deals with a destination file being modified *after* the flow is already running. This is a check at *creation* time, alongside Cycle Prevention and Destination Consent:

- If the proposed destination path collides with existing content already indexed there, the collision is **surfaced to the flow's creator** — never silently overwritten or silently accepted
- **Resolution:** the creator must provide either a different destination path, or confirm the collision is intentional (e.g., the flow is meant to replace what's there) before the flow is accepted
- This follows the same governing approach used in Task for Create-intent name collisions — detected against the same Global File Index, surfaced rather than guessed around

### Stages/Stops

**Definition:** Manual checkpoints between source and destination(s) where processing occurs.

**Three Stage Types:**

#### 1. Branch Stage
- Splits the flow to create multiple destinations/paths
- One source (or one path) can split into many downstream paths
- Allows resource distribution to multiple endpoints
- Example: Source syncs to Client PC A, Client PC B, and Remote Storage simultaneously

**Placement determines scope:** A Transformation or Categorization stage placed **before** a Branch applies to everything downstream of it (shared across all resulting destinations). The same stage type placed **after** a Branch, on one specific path, applies only to that one destination. This lets a flow share common processing across all destinations while still allowing individual destinations to have their own additional treatment.

```
Source
  → Transformation Stage (convert to PDF)     ← applies to everything downstream
      → Branch
          ├─→ Destination A: Categorization (by type)   ← only affects A
          ├─→ Destination B (no further processing)
          └─→ Branch (splits again)
                ├─→ Destination C
                └─→ Destination D: Categorization (different rule)  ← only affects D
```

#### 2. Transformation Stage
- Modifies file format during transit
- Only makes sense between source and destination (mid-flow)
- Common transformations: convert to PDF, convert to Word, compress, decompress
- Transformed version flows to destination; original preserved at source
- Example: Word documents → converted to PDF → synced to PDF archive

#### 3. Categorization Stage
- Organizes files at destination by type
- Creates subdirectories based on file extension/category
- Executed when files reach destination
- Example: PDFs go to `/pdf/`, ZIPs go to `/zip/`, images to `/images/`

**Manual Checkpoint:** Each stage is manually configured and managed, not automatic.

---

## Synchronization Mechanism

**Trigger Mechanism:**

The system monitors all PCs that have been established as flow sources. Since the OS already emits events for file changes, the general approach is:

1. OS emits a file-change event (broadly, for any file activity on the PC)
2. The system filters this against the registry of files/directories recognized as flow sources on that PC
3. Only matches trigger a sync check — non-matching activity is ignored

**Fallback:** If native event filtering proves too complex or unreliable for a given case, the system falls back to polling all files recognized as flow sources for changes on an interval.

**How Sync Proceeds Once Triggered:**
1. Matched change is detected (via native event or poll)
2. Changes propagate through stages
3. Destination(s) updated to match source

**Change Detection & Attribution:**
- **Content Hash:** Verifies file content integrity
- **Timestamps:** Tracks modification times to detect changes
- **Write Attribution:** Every write carries the hash produced by that write, plus who made the change and at what hierarchy level
- Combined, this lets the flow distinguish its own sync-driven writes from external ones — the flow checks whether the write's attribution matches its own sync process, rather than only comparing hash/timestamp in isolation (see Conflict Handling)

**Propagation Path:**
```
Source changes
    ↓
Stage 1 (optional processing)
    ↓
Stage N (optional processing)
    ↓
Destination(s) synced
```

---

## Conflict Handling

**One-Directional Conflict Prevention:**

When a destination file is modified by an external entity (not from source sync):

1. **Detect:** System checks the write's attribution (hash, who made it, at what hierarchy level) against its own sync process. If the attribution doesn't match the flow's own sync-driven write, it's an external modification — this avoids the flow ever mistaking its own write for a conflict.
2. **Preserve:** Modified file is renamed with `-modified` suffix
   - Example: `report.xlsx` → `report-modified.xlsx`
3. **Sync New:** New copy created from source alongside renamed file
   - Example: Fresh `report.xlsx` synced from source
4. **Result:** Both versions exist (modified external version + synced source version)

**Purpose:** Preserves external work while maintaining source-of-truth from source.

---

## Failure Handling

**Scope of Failure:** Flow failures come from a finite set of possibilities tied to the flow's structure and stage types — a Transformation stage failing to convert a file, a Categorization stage failing to place a file, a broken destination connection, and similar. Because this set is finite, the system can predefine how to respond to each one.

**On Failure:**
1. **Pause, scoped precisely:** Only the specific flow or branch the failure occurred on is paused — not the entire flow tree. Unaffected branches continue operating normally.
2. **Persistent status at the source/creator side:** The flow creator sees a failure status that does not clear on its own — it remains until the underlying issue is actually resolved.
3. **Status at the destination side:** The affected destination also shows a status indicating new changes won't reflect until the issue is resolved, rather than silently going stale with no indication anything is wrong.
4. **Reactive fix suggestion, not upfront configuration:** Clicking the failure status surfaces a quick, safe suggested solution appropriate to that failure type (e.g., "remove transformation stage"). These suggestions are predefined per stage type/failure type as built-in system knowledge — the flow creator is never asked to anticipate or configure failure handling when first setting up the flow. Suggestions only appear reactively, once a failure has actually occurred.
5. **Resume:** Once the issue is resolved (by applying the suggestion or otherwise), the paused flow or branch resumes automatically.

**Why this approach:** Asking a flow creator to configure failure handling for every possible failure mode upfront is excessive before they've even seen the flow in action. Predefining solutions per (finite) failure type and surfacing them only when relevant keeps setup simple while still giving a clear, actionable path to resolution when something breaks.

---

## Flow Examples

### Example 1: Simple One-to-One Flow

```
Source: Admin PC - /documents/
    ↓
Destination: Remote Storage - /backup/documents/

Any changes to files in /documents/ sync to /backup/documents/
```

### Example 2: One-to-Many Flow (Branching)

```
Source: Client PC-1 - /classwork/
    ├─→ Destination 1: Admin PC - /submissions/
    └─→ Destination 2: Remote Storage - /archive/

Classwork syncs to both admin review and archive simultaneously
```

### Example 3: Flow with Transformation

```
Source: Admin PC - /reports/ (Word documents)
    ↓
Transformation Stage: Convert to PDF
    ↓
Destination: Remote Storage - /pdf-archive/

Word documents automatically converted to PDF during sync
```

### Example 4: Flow with Categorization

```
Source: Client PC - /downloads/ (mixed file types)
    ↓
Categorization Stage: Organize by file type
    ↓
Destination: Admin PC - /organized-downloads/
    ├─ /pdf/
    ├─ /images/
    ├─ /documents/
    └─ /archives/

Files arrive at destination organized into type-specific folders
```

### Example 5: Complex Multi-Stage Flow (Branching + Transformation + Categorization)

```
Source: Admin PC - /raw-submissions/
    ├─→ Branch A: Transformation Stage (convert to PDF)
    │       ↓
    │   Categorization Stage (organize by type)
    │       ↓
    │   Destination 1: Remote Storage - /submissions-archive/
    │
    └─→ Branch B: No transformation
            ↓
        Destination 2: Backup Storage - /raw-backup/
```

---

## Flow Creation & Management

**Creation Authority:**
- Super User: Can create flows at department or system level
- Admin: Can create flows within their department (source and destination on admin/client PCs)
- All flow creation is subject to **Destination Consent** (see Core Components → Destination) — implicit where the creator already has authority over the destination, explicit approval required otherwise (lateral flows, or flows into a superior's space)

**Flow Properties:**
- Source: Directory path on Admin PC or Client PC
- Destination(s): Directory path on Admin PC, Client PC, or remote storage
- Stages: Ordered list of processing stages (Branch, Transformation, Categorization)
- Status: Active, Paused, Inactive
- Sync Frequency: Real-time, scheduled, or manual trigger
- Conflict Resolution: Automatic (rename + sync), based on write attribution
- Failure Status: Persistent until resolved, scoped to the affected flow/branch only
- Cycle Check: Validated before any flow/branch change is saved

**Flow Operations:**
- Create flow
- Edit stages/destinations
- Pause/resume flow
- Monitor sync status
- View sync history and conflicts
- Delete flow

---

## Key Principles

1. **One-Directional** — Source → Destination(s) only; prevents bidirectional conflicts
2. **Branching** — One source can sync to multiple destinations simultaneously
3. **Chaining, with Cycle Prevention** — Destination can become source for another flow, but any flow/branch change is validated for cycles before it's saved
4. **Destination Consent** — a flow is created without approval only when the creator already has authority over the destination; lateral flows and flows into a superior's space require the destination owner's explicit consent
5. **Pre-Flight Collision Check** — a flow's destination path is checked against the Global File Index before creation; existing unrelated content there is surfaced to the creator, never silently overwritten
6. **Staged Processing** — Transformation and categorization happen mid-flow, not at source; placement before/after a Branch determines shared vs. per-destination scope
7. **Manual Checkpoints** — Stages are manually configured, not automatic
8. **Conflict Preservation via Attribution** — Every write carries hash + who + hierarchy level, letting the flow distinguish its own sync writes from genuinely external ones; external modifications preserved (renamed) while source syncs alongside
9. **Native-First Change Detection** — OS-emitted file events, filtered against registered flow sources, drive sync checks; polling is the fallback where native detection isn't practical
10. **Failure is Scoped and Reactive** — a failure pauses only the affected flow/branch, persists as a status until resolved, and surfaces a predefined fix suggestion only when it happens — never configured upfront
11. **Transparent History** — All syncs, conflicts, and failures logged for audit and troubleshooting

---

## Integration with Other Combos

**With Task:**
- **Distinction:** Task is work verified by an assigner; Flow is automated, one-directional resource distribution with no human verification. They serve different purposes but can compose.
- A task's verification targets are tracked by identity (via the Global File Index and OS events), not confined to a task-specific folder — a Flow can pick up a task's target file once it exists and distribute it onward, using that same identity-based tracking rather than a shared location convention.
- Example: an Admin assigns a task whose deliverable is a report file; once that file exists and passes verification, a Flow sources from wherever it actually lives and distributes it to other destinations.

**With Resource:**
- Resource folders cannot be a direct Flow source or destination (security boundary) — Flow moves resource files under the hood instead, respecting Resource's access tiers.
- Both Flow's sync trigger and Resource's compliance detection use the same native-OS-event-plus-polling-fallback pattern against the same Global File Index, rather than separate mechanisms.
- Flow's Pre-Flight Collision Check and Task's Create-intent name collision check both validate against the same Global File Index, using the same "surface to the creator, never silently resolve" approach.

**With Hierarchy:**
- Flow's Destination Consent rule is built directly on hierarchy authority: a flow is created without approval only when the creator already outranks the destination owner; lateral flows and flows into a superior's space require explicit consent.
- Flow write attribution (hash + who + hierarchy level) reuses the same audit-trail-driven accountability principle used throughout Hierarchy — traceability instead of restriction.
- All flow creation, sync activity, conflicts, and failures are logged as part of the same system-wide audit trail (see Hierarchy's Audit & Logging). A paused flow's failure status is a Report under Hierarchy's Report Routing model, always visible to Super User and routable to a specific department (e.g., IT) the same as any other report category.
