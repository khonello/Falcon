# Proposals: the core features (the user, 15 Nov 2026)

Ideas for Protected and Detective, each checked against what is built and the rules in `CLAUDE.md`. **All of it goes into version 1
(the user, 15 Nov 2026).** Nothing here is built yet. Branch `proposals/core-features`. The questions for the user are at the end.

Dropped on 15 Nov 2026, so they do not come back by another name:
- **Flow: steps saved as a template.** Copying steps from another flow would do most of it, and a customer with ten flows rarely
  reuses steps.
- **Task: chained tasks**, and the smaller "give after" too. The work (a waiting status, release, relative deadlines, send-back,
  stopping, a new Worker action or a split rule, and the most involved page in the console) was far more than the convenience, with
  no sign yet that work comes in sequences.

Task and Flow still gain: both follow a renamed file through the file identity (item 1).

| # | Feature | Idea | What exists today | Size |
|---|---|---|---|---|
| 1 | Protected (the index) | A file identity that survives rename, move and edit | Index row = one place; copies followed by hash; moves by history | Large, shared |
| 2 | Detective | Windows' own places (Desktop, Downloads...) | `_same_profile` reads `Users\<name>` out of the path | Small |
| 3 | Detective | A loose snapshot of the machine and its changes | System-drive percent in Automation; process snapshots | Medium |
| 4 | Detective | Usual and unusual: habits, learned and taught | Fixed weights; a reviewer's "this is fine" (program / folder / drive) | Large; start narrow |

**Order:** Windows' places (2) -> the snapshot (3) -> the exact file identity (1, links 1-4) -> narrow habits (4) -> "probably the
same file" (1, link 5). 2 is small and the rest of Detective uses it. 3 needs no learning, so it is worth more for its cost than 4.
The exact part of 1 is cheap and solid; its scoring part is the hard part and comes last.

---

## 1. A file identity that survives rename, move and edit

**The idea.** A file keeps who it is when renamed, moved or edited. A hash changes when the content changes, so the identity is built
from several things together: hash, name and more.

**Today.**
- An index row is a **place** (machine + path) with a content hash. A move marks the old place gone and makes a new row
  (`engine/file_index.py:149`); `file_events` keeps `old_path`.
- `resource/journey.py` follows a file by its **hash** and stitches moves (and folder moves) from the history.
- So: renamed only -> followed (history). Copied only -> followed (hash). **Edited and then copied or carried away -> lost**: the new
  hash matches nothing, and the copy has no move in the history. That is the gap, and it is the case Protected exists for.
- The Worker already reads Windows' own file id (`st_ino`, `worker_client/fsmeta.py`) to spot renames while polling, but never sends it.

**One identity in the Global File Index, not a Protected-only one.** The rule is "one index, never per-feature bookkeeping", and the
identity helps Task, Flow and Detective as much as Protected (see "Beyond Protected").
- `file_lineage` (id, first seen, first name, first place). Each index row gets `lineage_id`. A lineage has **versions** (each
  hash it has had, in order) and **places** (each path it has had, on each machine).
- **Links, strongest first**, each one recorded with how it was made. 1-4 are exact and applied; they are built first.
  1. *Same file id* (volume serial + Windows' file id; 128-bit on ReFS): survives rename, a move on the same drive, and editing in
     place. A move to another drive is a copy and a delete to Windows, and gets a new id.
  2. *Move event* with `old_path`: rename, move.
  3. *Save-by-replace*: Word, Excel and many editors write a temp file and swap it in, which gives a new file id. Same path, same
     name, replaced within a few seconds -> the same lineage. Windows keeps the created time across this swap, which confirms it.
     The window is clamped.
  4. *Same hash* elsewhere -> a **copy**: a new lineage with `copy_of` the first.
  5. *Probably the same*: a new file on another drive or machine whose content is mostly that of a known lineage's latest version
     (edited, then carried out). This one is **scored**, never taken as a fact, and built last.
- **How "mostly the same content" is measured.** Hashing a file in fixed blocks does not work for the files that matter most: a `.docx`
  or `.xlsx` is a zip, so one changed cell changes the compressed bytes all through the file, and a fixed block boundary shifts with
  every insertion. So, by kind (all stdlib, done by the Worker when the machine is idle, hot first):
  - *Office files* (`.docx`, `.xlsx`, `.pptx` and their kin): open the zip (`zipfile`) and hash each part inside it. An edit usually
    changes one part (`word/document.xml`, one sheet); the pictures, styles and other sheets stay the same. The score is the share of
    parts, by size, that match.
  - *Text, CSV, code*: cut the file where a rolling hash of its content says (content-defined chunks, about 8 KB each), so an insertion
    moves only the chunks around it. The score is the share of chunks that match.
  - *PDF, pictures, archives*: whole hash only at first; a PDF compresses its content, so it is no better off than a zip without
    opening its streams.
- **Propose, never silently resolve** (question 1). A link of kind 5 is a **suggestion**: "This looks like `budget-2026.xlsx`
  (restricted), edited: 87% of its content is the same." A restricted status is never put on a file by a suggestion alone; an Admin
  says yes. Detective may *weigh* a suggestion (it already weighs, never decides).
- Weaker attributes, which only add to a score: the document's own properties (Office's author, title, created, read from
  `docProps/core.xml`), the folder it came from, its name.

**Beyond Protected.**
- **Task**: "report.docx must be in Shared\Finance" is still met when the person renames it there, or the Admin is told it was
  renamed, not "missing".
- **Flow**: a source file renamed is renamed at the destination, not copied anew with the old copy kept beside it.
- **Detective**: threads already join on "a file survives rename and copy"; this gives them edited files too ("the restricted budget,
  edited, then on a USB drive").
- **The journey**: one unbroken line from first seen to today, through edits.

**Worst case, clamped.** A lineage keeps its last 50 versions and every place; part and chunk hashes only for files under 200 MB; a
suggestion is looked for only for files that are restricted or have a Detective case.

---

## 2. Detective: Windows' own places

**The idea.** Know Desktop, Documents, Downloads and the other places Windows names.

**Today.** `common/detective.py` `_same_profile` cuts `Users\<name>` out of a path. A Desktop moved into OneDrive, or a profile on
another drive, is not seen.

**Proposed shape.**
- **Read from the registry, not asked of the shell.** The Worker is a service with nobody signed in to it, so `SHGetKnownFolderPath`
  would give the service's own folders. Instead it reads each profile's folders from
  `HKEY_USERS\<SID>\Software\Microsoft\Windows\CurrentVersion\Explorer\User Shell Folders` (stdlib `winreg`; expanding
  `%USERPROFILE%` with the profile's own path from `ProfileList`). That works from the service and catches a Desktop or Documents
  moved into OneDrive. Profiles not loaded (nobody signed in) are read from their `NTUSER.DAT` only if needed; otherwise the default
  places under the profile path stand in, marked as such.
- The places: Desktop, Documents, Downloads, Pictures, Videos, Music, OneDrive, AppData (Roaming, Local), Temp, Startup, the Recycle
  Bin, and the machine's Program Files, Windows, ProgramData. Sent at connect and when they change (a folder redirected).
- Every file event is given its **place kind** (`downloads`, `documents`, `temp`, `startup`, ...) before Detective reads it.
- What it gives the graphs: Downloads -> Documents is filing (lower); Documents -> Temp, AppData or the Recycle Bin is burying (higher);
  a file written to Startup is something that will run at sign-in (new, worth a reading); emptying the Recycle Bin after gathering is
  erasure.
- Also useful outside Detective: Task (`@folder:Downloads` for any person), Flow (a source "their Desktop" that follows redirection).

---

## 3. Detective: a loose snapshot of the machine

**The idea.** A rough picture of the whole machine, taken now and then, compared with the last one. A sudden change shows what
events alone miss. Storage dropping sharply may be a clean-up or sabotage, and the same holds in other areas. Some changes matter
whoever made them, so this needs no learning at all: yesterday against today.

**Today.** Automation has a threshold on the system drive's percentage; the Worker sends process lists. Nothing compares the machine
with itself over time.

**Proposed shape.**
- **What the snapshot holds** (cheap, all Windows-native, read when the machine is idle; stops the instant someone types). The Worker
  service has the rights to read all of it:
  - storage: free and used space of each drive; the size and file count of each known place (from item 2);
  - programs installed, services and how they start, startup entries, scheduled tasks;
  - local accounts and who is in Administrators; shared folders;
  - Defender and the firewall on or off; BitLocker on each drive;
  - printers and USB devices known; the size of the event logs.
- **Every 6 hours and at connect**, plus when a big event batch arrives. The Engine keeps the latest snapshot and a diff per day for 90
  days (the retention clock).
- **One machine state for Detective and Automation.** Automation's disk threshold reads the same record, and gains new events for rules
  on the same spine: "a new local Administrator", "Defender off", "a drive below 10% free".
- **A sudden change becomes a signal**, and like every signal it is read several ways:
  - storage down 40 GB: in the Recycle Bin, Temp or Windows Update's folder -> a clean-up (quiet); in Documents or a share, by hand,
    after gathering -> sabotage or erasure (raised);
  - a new member of Administrators, Defender turned off, a new startup entry, the event log shrinking: worth a reading every time;
  - a program installed that copies or hides files (an archiver, a cloud sync tool, a wiper).
- **It also heals.** A snapshot that differs from what the events said (Documents is 2 GB smaller but no deletes came in) means events
  were missed. The index sweep is started for that folder. This is "proactive first, reactive second".

**Worst case, clamped.** A snapshot is at most a few hundred KB; the place sizes come from the index where it has them, a walk only
where it does not; a machine that is always busy gets its snapshot at connect only, and the page says how old it is.

---

## 4. Detective: usual and unusual, learned and taught

**The idea.** The system learns what is usual for each person and machine. People can also say what is usual, so their word corrects
what the system assumed. Usual covers what they do, where they go, when they start and stop.

**Today.** Weights are fixed in the code. Night is 22:00-06:00 for everyone and only nudges. A reviewer's "this is fine" is a rule
(`detective_rules`, migration 037: a program, folder or drive on one machine) that only lowers a finding, never hides it. `pc_days`
keeps the quarter hours someone was at the keyboard.

**Why narrow first.** Systems that learn each person's normal are known for noise. With a few dozen people and 28 days, the normal is
thin, and unusual days are common (a holiday, a month-end, a new project). So the first version learns little and only weighs.

**First version.**
- **Three habits per person on a machine**, over a rolling 28 days, from what the Engine already receives:
  - *hours*: when they are usually at the keyboard (from `pc_days`), and the days they work;
  - *drives*: the drives they usually use (already counted per machine; made per person);
  - *amounts*: the usual daily number of files deleted and of files sent to drives.
- They **only weigh findings Detective already makes**; a habit never raises a finding on its own. 300 deletions weigh less for someone
  who deletes hundreds every day than for someone who deletes ten; work at 23:00 weighs less for someone who always works late. The
  voice stays the same: "unusual for this person: they have not deleted more than 20 files in a day in four weeks".
- **Taught by people** (the strongest part): the 037 rules widen from program / folder / drive to a time ("they work nights") and an
  amount, made from a review or by an Admin without a case ("the Finance machines run a backup at 02:00"). "This was right" teaches the
  other way. A task or a flow that covers a folder makes work there usual for that time.

**Guards** (these keep it from being fooled):
- **The system may learn that something is usual; only a person may make the sensitive usual.** Anything restricted, anything going to
  a new drive, and anything Detective already raised a case about is never learned as normal by itself. Not negotiable: without it,
  Detective learns the very thing it should flag.
- **A slow climb is a pattern too.** A habit that grows week after week in one direction (more files to drives every week) is noted, so
  a patient person cannot teach the system their leak.
- **New people and machines** have no habits for the first 14 days; findings say so ("not enough known yet") and use today's fixed
  weights.
- What a person taught is shown on the Detective page beside the machine, with who taught it and when, and can be taken back. It
  lowers or raises a weight; the finding is always recorded.
- Time of day still never **starts** a case alone.

**Later, if the first version earns it:** where they usually work (folders and shares, by place kind), the programs they use, when they
usually stop.

**For the customer to know.** A profile of each person's habits, kept without telling them, goes further than today's Detective. Where
the customer is, the law on watching employees may ask them to tell their staff. Not a reason to drop it; it may need a line in the
customer's setup or terms.

---

## Placement

**Version 1, all of it (the user, 15 Nov 2026).** Each lands as Engine handler + TUI command first, then the concept, then the QML
(the TUI is the scripted test surface). Engine work and UI work stay in separate sessions. When this branch is merged, `PHASES.md` and
`START-HERE.md` get these items (question 2 says where).

## Questions for the user

1. **"Probably the same file"** (edited, then carried away): a suggestion an Admin confirms before it is treated as restricted
   (recommended), or applied at once above a score?
2. **Before or after packaging?** Phase 9 is the blocker for a sale. These can be built (a) before it, so the installers carry them
   from the first build, or (b) beside it, the Engine session on these while the packaging work goes on.
