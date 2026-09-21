# Task Natural Combo

## Overview

The Task natural combo is a foundational workflow pattern: **Task → Verification → Expectation**, with **Deadline** as a supporting Task-level property.

Verification is the anchor: it defines what the end outcome of the task must be. Expectations are derived from verification, not defined independently — they exist to show that work toward that outcome is happening, without ever confirming it's finished. A local LLM assists by turning a plain-language task description into a populated task structure — Verification targets, Deadline, and task scope — so the assigner rarely has to configure this by hand.

**Governing principle — the LLM surfaces ambiguity, it never silently resolves it:** whenever the LLM encounters something uncertain while populating the task structure — an unclear Verification target, an ambiguous Deadline, or a description that seems to cover more than one task — it surfaces this back to the assigner as a question or a proposal. It never picks silently on the assigner's behalf and presents the guess as settled fact. This single principle governs all LLM-assisted parts of Task creation, not just Verification.

---

## Task

**Definition:** Something to be done; a unit of work assigned to someone.

**Creation Authority:**
- **Super User:** Can create tasks and assign to a Department
- **Admin:** Can create tasks and assign to a Client PC

**Assignment Scope:**
- Tasks are always tied to a user account (the person responsible for completing it)
- Super User creates → Department-level task (Admin or multiple Admins in that department accountable)
- Admin creates → Client PC-level task (specific user account on that PC accountable)

**Task Properties:**
- Assigned to: User account
- Created by: Super User or Admin
- Scope: Department or Client PC level
- Status: Active, In Progress, Completed
- Deadline: Soft and final deadline (see Deadline section)

**No Task Directory:** Tasks are not confined to an auto-created workspace directory. Tracking is by **target identity** (a specific file or program, wherever it actually lives) via the Global File Index and OS file events, not by location — this reflects that workers don't naturally keep task-related work in one dedicated folder, and forcing that was an unnecessary constraint. See Verification for how targets (including not-yet-created files) are specified without needing a task-specific directory.

### Deadline

**Definition:** A Task-level property (one per task, not per verification item) marking when the task should be complete.

**Two Deadlines:**
- **Soft Deadline:** fires first, as a "bring attention back" nudge before the real deadline
- **Final Deadline:** the actual deadline for the task

**Population:** Follows the same natural-language-first pattern as Verification — if the assigner mentions a deadline in their plain-language task description, the LLM extracts it into the structured Deadline field(s). The assigner can directly adjust the structured field afterward; whichever value is left when the assigner confirms is what applies. There is no separate "input deadline" competing with a "structure deadline" — natural language is simply the input method that populates the one structured field, and manual editing is the correction method for that same field.

**Ambiguity Handling:** If the description contains an ambiguous deadline (e.g., "finish this by Monday or Wednesday"), the LLM does not silently pick one — it flags the ambiguity and asks the assigner to confirm which applies, per the governing principle (see Overview).

**Mechanism:** Both Soft and Final Deadline are implemented as scheduled Events (see Control, Events, Monitoring & Actions) — "soft deadline reached" and "final deadline reached" are time-based Event conditions, and whatever Actions are attached to them execute when each fires (e.g., notifying the Admin).

**Status Indicator:** Deadline events surface using the same generalized status indicator pattern as Help Ping's unaddressed-message indicator (see Resource & Assistance) — a persistent, high-visibility (bold/pulsing) indicator, with color distinguishing the kind of state (e.g., a distinct color for deadline reached vs. task completed vs. unaddressed ping). This is one shared visual mechanism used across multiple features, not a Task-specific indicator.

### Multi-Task Detection

**Definition:** Handling for when a task description, given in natural language, appears to actually describe more than one distinct piece of work.

**How It Works:**
- The LLM does not silently split the description into multiple tasks, and does not silently force it into one task either
- Instead, it **proposes a concrete split** — drafting the separate tasks it detected, each pre-filled with whatever is common between them (assigner, assignee, etc.), differing only in what actually needs to differ (Verification targets, Deadline, etc.)
- The assigner is presented with a direct choice: **"Split into two tasks as shown, or edit as one task?"** — not an open-ended question, but a concrete proposal to accept or decline
- This follows the same governing principle as Verification and Deadline ambiguity: the LLM proposes, the assigner decides — nothing is silently restructured on their behalf

---

## Verification

**Definition:** Specifies what must be true for the task to be considered done. Verification is the anchor of the whole combo — it defines the end outcome first, and Expectations are derived from it, not the other way around.

### Primary Path: Natural Language → LLM-Populated Structure

The normal way a task gets its verification is not manual configuration — it's the assigner describing the task in plain language.

**How it works:**
1. Assigner types what the assignee is supposed to do, in natural language, as they normally would describe a task
2. A **local LLM** reads this description and populates a predefined task structure from it — inferring:
   - The verification target(s) (which file(s) or program(s) matter)
   - The verification item type for each (exists, updated, created, etc.)
   - The expectations to derive and track for each target (see Expectation section)
3. The populated structure is shown to the assigner for review
4. **If the structure is insufficient** — the LLM can't confidently infer a target, or the description doesn't give it enough to work with — the assigner is **informed**, not silently left with a guessed structure passed off as certain

**Verification is not forced.** Not every task needs it. But "no verification" must be an **explicit choice made by the user** — it is never the LLM's silent default when it can't infer a target. The LLM may propose "no verification seems to apply here" as a suggestion, but the user confirms it. A task with unclear verification and no explicit "None" from the user is a task the LLM should flag as insufficient, not quietly wave through.

### Fallback Path: Manual Verification Item Editor

When the LLM's structure is insufficient, or the assigner wants to correct or add to what it inferred, verification items can be added manually:

- **`[ + item ]`** — adds a new verification item
- Choosing an item means picking its **target type**: **File** or **Program**
- Multiple items can be added, building the same stack the LLM would have populated

This is the correction mechanism, not a competing primary path — most tasks should never need it if the natural-language description was clear enough.

**Target selection constraints:**

| Target Type | Selection Source | Constraint |
|---|---|---|
| **File** | Searchable list from the Global File Index | Must exist in the Global File Index, and must be a file the **assignee** (not the assigner) is permitted to access |
| **Program** | Dropdown of programs | Populated from what's actually installed/available on the **assignee's specific PC** — it's their machine doing the work |

Once a target is selected, the applicable expectation categories (see Expectation section) are attached automatically based on whether it's a File or Program target.

### Intent

Once a target type (File or Program) is selected, the item also specifies an **Intent** — what is actually supposed to happen with that target. Intent is chosen from a finite, predefined list, grouped by target type, and it's what the LLM infers from the description alongside the target itself (e.g., "put together the report" implies Create; "keep the data file current" implies Update).

**File Intents:**
- **Create** — the file doesn't exist yet at task start; the deliverable is a new file
- **Update** — the file already exists and must change
- **Exists** — the file must be present, unchanged (a presence check)

**Program Intents:**
- **Used** — the program must show genuine activity for a meaningful duration, not just be launched and left idle. This is the general-purpose intent, verified via the Expectation signals already defined for Program targets (active/idle state, memory footprint, activity over time).
- **Used With File** — the program must be actively used *and* have an open file descriptor tied to a specific file (from a File target elsewhere in the verification stack, or independently specified). This is the intent that directly answers the original problem with program-based verification: it's not just "was the program used," it's "was the program used on this specific file" — tying usage evidence back to a concrete deliverable rather than accepting mere presence in the process list.
- **Installed/Available** — a presence check only, no usage required: the program must simply be available on the assignee's PC. Relevant when a task's real deliverable is a File, but a specific program is a prerequisite worth confirming exists, without verifying its usage.
- **Closed/Not Running** — the inverse of Used: the program must be closed or not running by task completion. Relevant for tasks like ensuring a sensitive file isn't left open, or other cleanup/security-adjacent checks.

**Create Intent — Name, Path, and Collision Handling:**

Since there's no Task Directory to place a new file in, a Create-intent File target is specified primarily by **name** — this is what matters most, since tracking is by file identity via OS events, not by location:

- **Name** is the primary field, always required
- **Path** is optional — shown in the structure only if the assigner's input specified one; if not given, no path is required or assumed, since the system will detect the file being created wherever it actually lands
- **Collision check:** before the task is accepted, the proposed name is checked against the Global File Index, scoped to the assignee. If a file with that name already exists somewhere the assignee has:
  - The collision is **surfaced to the assigner**, per the governing principle — never silently accepted or silently guessed around
  - This can also reveal a misclassified Intent (e.g., a name collision on a "Create" might actually mean the assigner meant "Update")
  - **Resolution:** the assigner must provide either a specific directory path (to disambiguate location) or a new file name before the task can be accepted

### Verification Item Types (Exists / Updated / Created — see Intent above)

Each verification item's check is defined by its target's Intent:

- **File exists** (Intent: Exists) — target file is present
- **File updated** (Intent: Update) — target file has changed since a defined baseline (task creation time, or last check)
- **File created** (Intent: Create) — a new file appears, identified by name (and optional path); see Create Intent above for collision handling
- **Program-based** (Program Intent — Used, Used With File, Installed/Available, or Closed/Not Running) — see Intent above for what each checks, and Expectation for how usage is measured

### Verification Stack

A task can have multiple verification items, whether populated by the LLM or added manually:

**Verification Stack Features:**
- **Multiple checks per task:** as many verification items as needed, mixing File and Program targets
- **Ordering:** items can have a sequence (Item 1 → Item 2 → Item 3), but no nesting
- **Status display:** assigner sees status of each check (✓ passed, ✗ failed, pending)
- **Location:** each File target is tracked by identity (name, and content hash once it exists) via the Global File Index and OS events — not by a shared task-specific location

**Example Verification Stack:**
```
Task: "Complete Q4 Analysis"
Verification Item 1: File exists — report.xlsx
Verification Item 2: File updated — raw-data.csv (modified since task start)
Verification Item 3: File exists — summary.pdf
```

### Manual Verification (Completion)

- **Performed by:** The person who assigned the task
- **Function:** Reviews the actual work and all verification items, makes final decision
- **Authority:** Only manual verification can mark a task as complete
- **Process:** Assigner sees verification stack status (all items and their pass/fail states), reviews the actual work at each target's location, then marks entire task as complete or incomplete
- **Key point:** Task is verified as a whole unit—not individual verification items

**Key Principle:**
- Verification stack provides transparency into what checks passed/failed
- Manual verification by assigner is the only authority that completes the task

---

## Expectation

**Definition:** Conditions or signals that indicate work is being actively done, derived automatically from a verification item's target. Gives assurance that the task is in process, though never a guarantee that work is actually completed.

**Derivation depends on target type** — a File target and a Program target produce fundamentally different expectations, because they're tracked through different mechanisms:

### From a File Target

The OS already emits events for file activity (created, modified, moved, deleted). Expectations for a file target are built directly on these native signals:

- File creation detected
- File modification detected (content or timestamp change)
- File activity frequency (how often it's being touched)
- Directory-level activity around the file (new related files appearing)

**Baseline for "updated":** measured against a defined point — task creation time, or the last check — so "has this changed" always has a concrete reference, not an ambiguous "changed at some point."

### From a Program Target

Programs don't have a single "done" signal the way a file does, so expectations here are about **usage evidence** rather than state change:

- Whether the program is currently active or idle
- Memory footprint while running (a proxy for real use vs. sitting open unused)
- Open file descriptors associated with the program — this is what connects program activity back to the actual files it's touching, without the assigner needing to separately specify those files
- General process activity over time (is it being interacted with, or just open in the background)

**Why this matters:** a program being open proves nothing on its own (as raised earlier — "Excel is open" doesn't confirm any specific task is happening). Tying expectations to memory footprint, activity, and file descriptor access ties the signal back to real use of that specific program for that specific task, not just its presence in the process list.

**Key Characteristic:**
Regardless of target type, expectations are always soft signals — they indicate progress but never confirm completion. Only Verification, checked manually by the assigner, can do that.

---

## Task Lifecycle

```
1. TASK CREATED (by assigner, described in natural language)
   ↓
2. LLM POPULATES STRUCTURE (verification target(s) + intent, item types, derived expectations, deadline)
   ↓
3. ASSIGNER REVIEWS STRUCTURE
   ├─ Sufficient → confirm and proceed
   ├─ Insufficient → assigner informed, corrects/adds via manual [+ item] editor
   ├─ Name collision on a Create-intent target → assigner provides path or new name
   └─ No verification applies → assigner explicitly confirms "None" (never a silent default)
   ↓
4. TASK ASSIGNED (to user account, with confirmed verification stack or explicit None)
   ↓
5. TASK START ACKNOWLEDGED (by assigned user)
   ↓
6. EXPECTATION SIGNALS (derived from verification targets, monitored continuously — skipped if verification is None)
   ↓
7. MANUAL VERIFICATION (assigner reviews verification stack status & actual work)
   ↓
8. TASK MARKED COMPLETE (only after manual verification by assigner)
   ↓
9. TASK CLOSED
```

**Note:** The assigned user cannot close the task — only the assigner can mark it complete after manual verification. Verification stack status is continuously updated and displayed to the assigner.

---

## Natural Combo Flow

### Assigner's Perspective (Setup)
```
Task (described in natural language) → LLM populates Verification targets/items → Expectations derived automatically → Assigner reviews and confirms
```

The assigner describes the task in plain language; the LLM infers verification targets (file or program) and item types, and expectations are derived automatically from those targets. The assigner reviews the result — correcting via the manual `[+ item]` editor if needed, or confirming "None" explicitly if no verification applies.

### Assigned's Perspective (Execution)
```
Task → Acknowledge task start → Work on the target file(s)/program(s) → See expectations tracked
```

The assigned user receives the task, clicks to start it, works on whatever files or programs the task's verification targets, and sees expectations being tracked in real-time as progress signals — tracked by identity via the Global File Index and OS events, not confined to a task-specific folder. They don't close the task — only the assigner can.

### Assigner's Perspective (Verification)
```
Review verification stack status → Review actual work at each target's location → Mark complete or incomplete
```

The assigner sees the verification stack showing which checks passed/failed, reviews the actual work at each target's location, and makes the final decision to mark the task complete or incomplete.

### How the Combo Works Together

1. **Task** is created with clear scope and assignment, described in natural language
2. **LLM populates Verification** — targets (file or program), Intent, item types, and stack — from the natural language description; a name collision on a Create-intent target is surfaced for resolution
3. **Assigner reviews**, corrects via manual editor if insufficient, or explicitly confirms "None"
4. **Expectations** are derived automatically from each verification target's type (File or Program)
5. **Assigned user** starts the task and works on the target file(s)/program(s), wherever they actually are
6. **Expectations** continuously monitor the relevant targets for progress signals, tracked by identity via the Global File Index and OS events
7. **Verification Stack** status updates in real-time (checks pass/fail)
8. **Manual Verification** by assigner reviews entire task (stack status + actual work)
9. Task is marked complete or incomplete as a whole unit

**Example Scenario:**

Admin describes task in natural language: *"Have jsmith put together the Q4 sales analysis — I need the analysis report, the raw data file kept current, and a final summary PDF."*

LLM populates structure:
- Task: "Complete Q4 Sales Analysis"
- Assigned to: User account `jsmith` on Client PC-047
- Verification Stack inferred:
  - Item 1: File target `analysis-report.xlsx`, Intent: Create (name only, no path specified) — Global File Index checked, no collision found
  - Item 2: File target `raw-data.csv`, Intent: Update (baseline: task creation time) — resolved against an existing file already in the index
  - Item 3: File target `summary.pdf`, Intent: Create — Global File Index checked, no collision found
- Expectations derived (File targets): file creation/modification signals for each of the three files, tracked by identity regardless of where jsmith saves them

Admin reviews the populated structure — confirms it's sufficient, no manual correction needed.

Assigned User:
- Starts task at 09:15
- Works on the three files, saved wherever is natural for their workflow
- Sees expectations (file activity signals) being tracked in real-time

Admin's Manual Verification (2024-01-16 14:00):
- Reviews verification stack status: Item 1 ✓, Item 2 ✓, Item 3 ✗
- Locates and reviews the actual files via the Global File Index
- Checks analysis quality and completeness
- Marks: "Task complete ✓" (or "Incomplete — missing summary.pdf")

Task closed (or returned for revision).

---

## Key Principles

1. **Task** = work unit with clear scope and assignee, described in natural language
2. **No Task Directory** = tasks are not confined to an auto-created workspace; targets are tracked by identity (via the Global File Index and OS events) wherever they actually live, not by location
3. **Verification is the anchor** = defines the end outcome first; Expectations are derived from it, never defined independently
4. **LLM-assisted setup** = a local LLM populates verification targets, Intent, and items from plain-language task descriptions; manual `[+ item]` editing is the fallback/correction path, not the primary one
5. **Verification targets** = File (from the Global File Index, scoped to assignee's access) or Program (from the assignee's own installed programs)
6. **Intent governs the check** = each target has an Intent chosen from a finite, predefined list — File: Create/Update/Exists; Program: Used/Used With File/Installed-Available/Closed-Not Running — Intent, not just the target, determines what the verification item actually checks
7. **Create Intent is name-first** = a not-yet-existing file is specified primarily by name; path is optional and only shown if given; a name collision against the Global File Index is surfaced to the assigner, who resolves it with a path or a new name
8. **"None" must be explicit** = a task can skip verification, but only via explicit user confirmation — never a silent LLM default
9. **Expectations are target-type-specific** = File targets derive from OS-native file events (created, modified); Program targets derive from usage evidence (activity, memory footprint, open file descriptors) — presence alone (e.g., "program is open") is never sufficient
10. **Manual Verification** = only authority to complete task; assigner reviews verification stack status + actual work
11. **Task completion** = verified as a whole unit, not individual items
12. **Transparency** = assigner sees real-time verification stack status without manual per-item verification
13. **LLM proposes, never silently resolves** = the single governing rule behind all LLM-assisted parts of Task creation — ambiguous verification targets, ambiguous deadlines, name collisions, and descriptions covering multiple tasks are all surfaced to the assigner as a question or proposal, never silently decided
14. **Deadline is one Task-level property, not per-item** = Soft and Final deadline apply to the whole task; both are implemented as scheduled Events, and their alerts use the same shared status-indicator pattern as Help Ping
15. **Multi-Task Detection proposes a concrete split** = when a description seems to cover multiple tasks, the LLM drafts the proposed split (sharing common fields, differing only where needed) and asks the assigner to accept the split or keep it as one task — it never restructures silently
