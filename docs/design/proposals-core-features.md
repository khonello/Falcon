# Proposals: the four core features (the user, 15 Nov 2026)

Seven ideas for Tasks, Flows, Protected and Detective, each checked against what is built and the rules in `CLAUDE.md`.
Nothing here is built. Branch `proposals/core-features`. The questions for the user are at the end.

| # | Feature | Idea | What exists today | Size |
|---|---|---|---|---|
| 1 | Task | Chained tasks | One task per description; no order between tasks | Medium |
| 2 | Flow | Steps saved as a template | Steps are typed into each flow | Small |
| 3 | Protected | A file identity that survives rename and edit | Index row = one place; copies followed by hash; moves by history | Large, and shared |
| 4 | Detective | Windows' own places (Desktop, Downloads...) | `_same_profile` reads `Users\<name>` out of the path | Small |
| 5 | Detective | Usual and unusual, learned and taught | Fixed rules; a reviewer's "this is fine" (program / folder / drive) | Large |
| 6 | Detective | Habits: where they go, when they stop | `pc_days` quarter hours; night is 22:00-06:00 for everyone | Part of 5 |
| 7 | Detective | A loose snapshot of the machine and its changes | System-drive percent in Automation; process snapshots | Medium |

---

## 1. Task: chained tasks

**The idea.** Several tasks in an order, for one person. Only the first is given. When it is done, the next is given, and so on.
The chain is complete when the last one is.

**Today.** `engine/task/tasks.py`: active -> in_progress (the Worker starts it) -> completed (an Admin verifies it). Only an
Admin's verification closes a task (any Admin in version 1). The Worker views, starts and watches; it never verifies. Splitting one
description into several tasks was removed (the user, 4 Nov 2026).

**Proposed shape.**
- A chain is made of tasks the Admin writes **one by one**: each description goes through the proposal and confirmation it goes
  through today. The model does not split a description into a chain, so the 4 Nov decision stands.
- `task_chains` (name, made by, status) and `tasks.chain_id` + `tasks.chain_position`. A task later in the chain is `waiting`: it
  exists, the Admin sees it, the Worker does not.
- **What moves the chain on** (question 1). Recommended: a step's checks are met and the Worker presses Done, and the next step is
  given at once. The step itself still waits for an Admin's verification, as every task does. The chain is complete only when every
  step is verified. So the person is never kept waiting on an Admin, and only a person still closes anything.
- **If an Admin sends a step back** (not verified), the next step stays with the person (it was already given), and the chain says so:
  "step 2 was sent back while step 3 was under way". Nothing is taken back from the person's screen without an Admin choosing it.
- **Deadlines**: each step's deadline can be a date or a span from when it is given ("2 days after it is given"), worked out on
  release by `common/when.py`. The chain may have its own final deadline.
- **Stopping**: an Admin can stop a chain; the remaining steps are cancelled (a status, never deleted) and the audit says who.
- Worker side: the program's Tasks tab shows "Step 2 of 4"; the next step arrives like any task (its window, then the quiet
  reminders).
- Built in this order: Engine handlers (`task.chain_create`, `task.chain_get`, `task.chain_stop`, release when a step is done)
  -> TUI `task chain ...` -> the concept -> QML.

**Worst case, clamped.** At most 20 steps a chain. The Engine refuses a chain step given to anyone but the chain's person (or see
question 2).

---

## 2. Flow: steps saved as a template

**The idea.** A set of steps saved under a name, so another flow can take it in one go.

**Today.** `engine/flow/steps.py`: Category > Kind > Operation > settings (Choosing, Conversion, Renaming, Bundling), per
destination branch, checked by `check_path`. Each flow is made from scratch.

**Proposed shape.**
- `flow_step_templates` (name, the ordered steps as `stage_type` + `config`, made by, made at, retired at). A template is the steps of
  **one branch**; sources and destinations are never in it.
- Saved from Make a flow ("Save these steps") or from an existing flow's branch; used from the step picker ("From a template").
- **A copy, not a link** (question 3). Using a template copies its steps into the flow, and the flow remembers "made from <template>".
  Changing the template later changes no running flow on its own; the template's page says which flows came from it and offers to
  bring them up to date, flow by flow. This follows "propose, never silently resolve".
- Any Admin changes any template; the page says "Made by". A template whose step is retired (as Placing and Unbundling were) says so
  and cannot be used until fixed.
- Restricted is not affected: the guard looks the status up fresh at every step (`engine/flow/guard.py`), whatever the steps came from.

---

## 3. Protected: a file identity that survives rename and edit

**The idea.** A file keeps who it is when renamed, moved or edited. A hash changes when the content changes, so the identity is built
from several things together: hash, name and more.

**Today.**
- An index row is a **place** (machine + path) with a content hash. A move marks the old place gone and makes a new row
  (`engine/file_index.py:149`); `file_events` keeps `old_path`.
- `resource/journey.py` follows a file by its **hash** and stitches moves (and folder moves) from the history.
- So: renamed only -> followed (history). Copied only -> followed (hash). **Edited and then copied or carried away -> lost**: the new
  hash matches nothing, and the copy has no move in the history. That is the gap.
- The Worker already reads Windows' own file id (`st_ino`, `worker_client/fsmeta.py`) to spot renames while polling, but never sends it.

**Proposed shape: one identity in the Global File Index, not a Protected-only one.** The rule is "one index, never per-feature
bookkeeping", and the idea helps more than Protected (see "Beyond Protected" below). So:
- `file_lineage` (id, first seen, first name, first place). Each index row gets `lineage_id`. A lineage has **versions** (each
  hash it has had, in order) and **places** (each path it has had, on each machine).
- **Links, strongest first**, each one recorded with how it was made:
  1. *Same file id* (volume serial + Windows' 64-bit file id): survives rename, move on the same drive, and editing in place. Exact.
  2. *Move event* with `old_path`: rename, move. Exact.
  3. *Save-by-replace*: Word, Excel and many editors write a temp file and swap it in, which gives a new file id. Same path, same
     name, replaced within a few seconds -> the same lineage. Exact enough; the window is clamped.
  4. *Same hash* elsewhere -> a **copy**: a new lineage with `copy_of` the first. Exact.
  5. *Probably the same*: a new file on another drive or machine whose name, size and content blocks are close to a known
     lineage's latest version (edited, then carried out). This is the one that needs care, so it is **scored**, never taken as a fact.
- **Content blocks**: the Worker hashes a document in fixed blocks (stdlib `hashlib`) as well as whole. Two files sharing most blocks are
  mostly the same content. Only documents and archives, only below a size (say 200 MB), done when the machine is idle, hot first.
- **Propose, never silently resolve** (question 4). Links 1-4 are exact and applied. A link of kind 5 is a **suggestion**: "This
  looks like `budget-2026.xlsx` (restricted), edited: 87% of its content is the same." A restricted status is never put on a file by a
  suggestion alone; an Admin says yes. Detective may *weigh* a suggestion (it already weighs, never decides).
- More attributes worth carrying, weakest weight: created time (Windows keeps it across a save-by-replace), the document's own
  properties (Office's author and title, read with `zipfile`), the folder it came from.

**Beyond Protected.**
- **Task**: "report.docx must be in Shared\Finance" is still met when the person renames it there, or the Admin is told it was
  renamed, not "missing".
- **Flow**: a source file renamed is renamed at the destination, not copied anew with the old copy kept beside it.
- **Detective**: threads already join on "a file survives rename and copy"; this gives them edited files too ("the restricted budget,
  edited, then on a USB drive").
- **The journey**: one unbroken line from first seen to today, through edits.

**Worst case, clamped.** A lineage keeps its last 50 versions and every place; block hashes only for files under the size limit;
a suggestion is looked for only for files that are restricted or have a Detective case.

---

## 4. Detective: Windows' own places

**The idea.** Know Desktop, Documents, Downloads and the other places Windows names.

**Today.** `common/detective.py` `_same_profile` cuts `Users\<name>` out of a path. A Desktop moved into OneDrive, or a profile on
another drive, is not seen.

**Proposed shape.**
- The Worker asks Windows for each signed-in person's known folders (`SHGetKnownFolderPath` through `ctypes`, stdlib + Windows only):
  Desktop, Documents, Downloads, Pictures, Videos, Music, OneDrive, AppData (Roaming, Local), Temp, Startup, the Recycle Bin, and the
  machine's Program Files, Windows, ProgramData. It sends the map at connect and when it changes (a folder redirected).
- Every file event is given its **place kind** (`downloads`, `documents`, `temp`, `startup`, ...) before Detective reads it.
- What it gives the graphs: Downloads -> Documents is filing (lower); Documents -> Temp, AppData or the Recycle Bin is burying (higher);
  a file written to Startup is something that will run at sign-in (new, worth a reading); emptying the Recycle Bin after gathering is
  erasure.
- Also useful outside Detective: Task (`@folder:Downloads` for any person), Flow (a source "their Desktop" that follows redirection).

---

## 5 and 6. Detective: usual and unusual, learned and taught

**The idea.** The system learns what is usual for each person and machine. People can also say what is usual, so their word corrects
what the system assumed. Usual covers what they do, where they go, when they start and stop.

**Today.** Weights are fixed in the code. Night is 22:00-06:00 for everyone and only nudges. A reviewer's "this is fine" is a rule
(`detective_rules`: a program, folder or drive on one machine) that only lowers a finding, never hides it. `pc_days` keeps the quarter
hours someone was at the keyboard.

**Proposed shape.**
- **A habit profile per person on a machine**, built by the Engine from what it already receives, over a rolling 28 days:
  - *when*: the hours they are usually at the keyboard (from `pc_days`), when they usually start and stop, the days they work;
  - *where*: the folders and shares they usually work in (by place kind and by folder), the drives they use;
  - *what*: the programs they use, and the usual amount of change in a day (files made, moved, deleted, sent to drives).
- **A finding is weighed against the person's own normal**, not one fixed line: 300 deletions is ordinary for a developer's build
  folder and very unusual for a receptionist. Work at 23:00 is ordinary for someone who always works late. Detective's voice stays the
  same: "unusual for this person: they have not deleted more than 20 files in a day in four weeks".
- **Taught by people, three ways:**
  1. *From a review*: "this is fine" (today) widens to a time ("they work nights"), a place, an amount; "this was right" teaches
     the other way.
  2. *Said by an Admin, without a case*: "Ama works Saturdays", "the Finance machines run a backup at 02:00".
  3. *From the work itself*: a task or a flow that covers a folder makes work there usual for that time.
- **Guards** (these keep it from being fooled):
  - **The system may learn that something is usual; only a person may make the sensitive usual.** Anything restricted, anything
    going to a new drive, and anything Detective already raised a case about is never learned as normal by itself.
  - **A slow climb is a pattern too.** A profile that grows week after week in one direction (more files to drives every week) is
    noted, so a patient person cannot teach the system their leak.
  - **New people and machines** have no normal for the first 14 days; findings say so ("not enough known yet") and use today's fixed
    weights.
  - What a person taught is shown on the Detective page beside the machine, with who taught it and when, and can be taken back. It
    lowers or raises a weight; the finding is always recorded.
  - Time of day still never **starts** a case alone; it weighs more when it is unusual for that person.

---

## 7. Detective: a loose snapshot of the machine

**The idea.** A rough picture of the whole machine, taken now and then, compared with the last one. A sudden change shows what
events alone miss. Storage dropping sharply may be a clean-up or sabotage, and the same holds in other areas.

**Today.** Automation has a threshold on the system drive's percentage; the Worker sends process lists. Nothing compares the machine
with itself over time.

**Proposed shape.**
- **What the snapshot holds** (cheap, all Windows-native, read when the machine is idle; stops the instant someone types):
  - storage: free and used space of each drive; the size and file count of each known folder (from item 4);
  - programs installed, services and how they start, startup entries, scheduled tasks;
  - local accounts and who is in Administrators; shared folders;
  - Defender and the firewall on or off; BitLocker on each drive;
  - printers and USB devices known; the size of the event logs.
- **Every 6 hours and at connect**, plus when a big event batch arrives. The Engine keeps the latest snapshot and a diff per day for 90
  days (the retention clock).
- **A sudden change becomes a signal**, and like every signal it is read several ways:
  - storage down 40 GB: in the Recycle Bin, Temp or Windows Update's folder -> a clean-up (quiet); in Documents or a share, by hand,
    after gathering -> sabotage or erasure (raised);
  - a new member of Administrators, Defender turned off, a new startup entry, the event log shrinking: worth a reading every time;
  - a program installed that copies or hides files (an archiver, a cloud sync tool, a wiper).
- **It also heals.** A snapshot that differs from what the events said (Documents is 2 GB smaller but no deletes came in) means events
  were missed. The index sweep is started for that folder. This is "proactive first, reactive second".
- **Automation can listen too**: "a new local Administrator", "Defender off", "a drive below 10% free" as events for rules, on the same
  spine.

**Worst case, clamped.** A snapshot is at most a few hundred KB; the known-folder sizes come from the index where it has them, a walk
only where it does not; a machine that is always busy gets its snapshot at connect only, and the page says how old it is.

---

## What fits where

- **Shared ground**: 3 (identity) and 4 (places) sit under the others. 4 is small and helps 5, 6 and 7, so it goes first; 3 is the
  largest and is worth doing before more of Detective leans on file threads.
- **Suggested order**: 4 -> 2 -> 1 -> 3 -> 7 -> 5/6.
- **Placement**: the phase order is fixed (Phase 9 packaging is now the blocker for a sale). These come after, unless the user says
  one goes into version 1 (question 5).
- Each lands as Engine handler + TUI command first, then the concept, then the QML (the TUI is the scripted test surface).

## Questions for the user

1. **What moves a chain on?** (a) the step's checks are met and the person presses Done; the Admin verifies later (recommended), or
   (b) only an Admin's verification gives the next step.
2. **One person per chain, or can a step go to someone else** (a hand-off: Kofi prepares, Ama checks)?
3. **Templates: a copy (recommended) or a live link** that changes every flow using it when the template changes?
4. **"Probably the same file"** (edited, then carried away): a suggestion an Admin confirms before it is treated as restricted
   (recommended), or applied at once above a score?
5. **When**: after packaging (Phase 9) as planned, or does any of these go into version 1?
