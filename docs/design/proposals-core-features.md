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
| 3 | Detective | A loose snapshot of the machine and its changes | Nothing compares a machine with itself over time | Medium |
| 4 | Detective | Usual and unusual: habits, learned and taught | Fixed weights; a reviewer's "this is fine" (program / folder / drive) | Large; start narrow |

**Order:** Windows' places (2) -> the snapshot (3) -> the exact file identity (1, links 1-4) -> narrow habits (4) -> mostly the same
content (1, link 5). 2 is small and the rest of Detective uses it. 3 needs no learning, so it is worth more for its cost than 4.
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
  5. *Made from restricted content*: a new file that holds a restricted file's text (copied out and pasted, edited, then carried
     out). **Found by events first, confirmed by content** (the user, 15 Nov 2026), below, and built last.

### Made from restricted content: events find it, content confirms it

**1. Events find it.** What the Worker already sees, in order, is most of the story:
- a restricted file is **opened**, and by which program (Windows' own file trace, `worker_client/etw.py`; file opens need the elevated
  service, and were confirmed delivered on 4 Nov 2026);
- the same program **creates or saves a new file** in the same sitting (the witness stamp on every file change says which program made
  it, and whether by hand);
- **a copy to the clipboard** in that program, between the two. This one is not seen today (Detective's "clipboard" is still open).
  The helper on the person's desktop can hear the clipboard change and which program owns it (Windows' clipboard listener; a service
  in session 0 cannot). It may also fingerprint the copied text there, the same way as below, and compare it with the restricted
  fingerprints the Worker holds: **the copied text never leaves the desktop, only "it matched `budget-2026.xlsx`"**. Watching the
  clipboard this way is agreed (the user, 15 Nov 2026), and so is a passage being enough when the events point at the file (below).

These do not decide anything on their own: Word or Excel has many files open at once, so "the same program saved a new file" is broad.
What they do is **name the candidate**: this new file, possibly made from that restricted file. Only candidates are compared, which
keeps the comparison small.

**2. Content confirms it**, the same way whatever program wrote the file:
- **Text, not bytes.** The comparison never looks at a file's bytes, so no program's way of writing a file can upset it (Word
  rewrites its XML on every save; others re-encode, re-zip, re-wrap, and nobody knows them all). From each file only its **text** is
  taken, and normalised: lower case, every run of spaces and line breaks made one space, punctuation and formatting dropped. Readers:
  plain text, CSV and code as they are; Word, Excel and PowerPoint (and the OpenDocument kin) by opening the zip (`zipfile`) and
  taking the text out of the parts that hold what was written (the document, each sheet, each slide, shared strings), never the
  pictures, styles, themes or properties; RTF by its text. PDFs, pictures and other formats have no reader at first, so they are
  followed by their hash only.
- **Fingerprints of the words** (winnowing, as plagiarism checkers do): every run of 8 words is hashed, and from each window of
  them the smallest hash is kept. A sentence gives the same fingerprints wherever it lands: in a Word file, pasted into a spreadsheet
  cell, in a text file. Reformatting, moving paragraphs, inserting and deleting text change only the fingerprints around the change.
  All stdlib (`hashlib`, `re`, `zipfile`, `xml.etree`), done by the Worker when the machine is idle, hot first.
- **Text every document shares does not count.** A contract made from the same template as a restricted master contract shares its
  standard clauses with it and is not a copy. So a fingerprint that also appears in documents that are not restricted is left out;
  only text that is the restricted file's own counts. The Engine counts fingerprints across ordinary documents too: hashes only, never
  text.

**3. The rule, decided, not suggested** (the user, 15 Nov 2026: if the system cannot be sure, an Admin looking at "87% the same" is
no better placed). Two cases, both applied at once and recorded with the reason:
- **With the events** (the new file is a candidate of a restricted file): it is restricted if it holds a **passage** of that file's
  own text, at least 40 fingerprints (about a paragraph). Otherwise copying 69% of a file would be a way round a 70% rule. One figure
  or a sentence quoted in a report does not make the report restricted.
- **Without the events** (it turned up on a drive or another machine, or its events were missed): it is restricted if it holds
  **70% or more** of a restricted file's own text, the "copy, then edited" case.
- Either way it is treated like any copy of restricted content today: shown on the Protected page as a copy caught, with its reason
  ("holds a passage of `budget-2026.xlsx`, pasted at 10:05"), in the file's journey, and an Admin can let it stay with the allowance
  that exists today.
- Too small to judge: a restricted file with under about 40 fingerprints of its own is followed by its hash only.
- Restricted content only: fingerprints are kept only for restricted files (and the counts for ordinary ones), through one table from
  fingerprint to lineage.

**Where it is recorded: two readings of the same events, on the one spine.**
- **Protected** decides the *status*: the file holds restricted content. That is recorded as Protected records a copy caught today
  (the `resource.*` audit, the Protected page, the journey), and it is a fact about the file, not about a person.
- **Detective** reads the *behaviour*: "restricted text gathered into a new file" is a finding under collection, weighed low on its own,
  since quoting a budget in a report is ordinary work. It joins a case only when it adds up: the new file then hidden, renamed to look
  like something else, or taken to a drive.
- So the person is not reported twice: a copy caught is a status, never an accusation; a Detective case is raised only by what follows.

**Testing:** Word, Excel and PowerPoint are being installed on the dev machine (the user, 15 Nov 2026), so the readers and the rule are
tested against files really edited and saved by the real programs. The same install lets the flow's Office conversion steps be run for
real at last (`docs/to-lookat.md`: "Not run for real").

**Beyond Protected.**
- **Task**: "report.docx must be in Shared\Finance" is still met when the person renames it there, or the Admin is told it was
  renamed, not "missing".
- **Flow**: a source file renamed is renamed at the destination, not copied anew with the old copy kept beside it.
- **Detective**: threads already join on "a file survives rename and copy"; this gives them edited files too ("the restricted budget,
  edited, then on a USB drive").
- **The journey**: one unbroken line from first seen to today, through edits.

**Worst case, clamped.** A lineage keeps its last 50 versions and every place; text is read only from files under 200 MB;
fingerprints are kept only for restricted files, so the comparison grows with what is restricted, not with the index; only candidates
named by the events are compared at once, the rest when the machine is idle.

**Built: the exact links (15 Nov 2026).** Migration 061 (`file_lineage`; `file_index.lineage_id`, `file_id`, `linked_by`), the linking in
`engine/file_index.py` (`_link`), the Worker sending each file's Windows id with its events, catch-up and sweep (`worker_client/fsmeta.py`
`file_id`), `index.lineage` and TUI `lineage <file_index_id>`, and the journey following the whole family of lineages, so a file carried to
a drive and edited there is one journey. As built:
- **Versions are not a table**: a lineage's versions are the hashes in the history of its places (`file_events`), and its places are the rows
  that carry it. Nothing is kept twice, so "the last 50 versions" needs no clamp of its own; the history's 90-day clock applies.
- **An editor's save** is read two ways: the place was left and written again within 60 seconds (Word's move-aside, swap-in), or written over
  while still there (a temp file moved straight onto the document). Both keep the place's file.
- **A Windows file id** is trusted only on the same machine and only at a place left in the last ten minutes, since Windows may give the id
  to another file later.
- **Every place already in the index** began as a file of its own when the migration ran; links are made from then on.
- Not yet: Task following a renamed file and Flow renaming at the destination (both can now ask the lineage), and link 5, made from
  restricted content (step 5 of the order).

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

**Built (15 Nov 2026).** `common/places.py` (the kinds, a machine's map, the usual layout as a guess), `worker_client/places.py` (read from each
profile's hive; told at every connect and when it changes), `engine/places.py` (`index.places`, `index.places_get`; held in memory, told again at every
connect), TUI `machine places <pc_id>`. Every file event Detective reads carries its place and, for a move, where it was (`info["place"]`,
`info["was"]`). Detective uses them for "somewhere nobody looks" (buried, hidden, disguised, and what does not count as gathering) and for filing
between one person's own places; its words name the place ("moved into Temp"). Where a machine has not said, the usual layout gives exactly what
Detective did before. Measured: no cost per event against `main`. Changed from the plan above:
- **A file put in Startup** is read by the snapshot (item 3), which covers every way a program starts at sign-in (the Startup folders and the Run
  keys), not only the folder; no Detective area fits it today.
- **The Recycle Bin**: the installer watches `C:\Users`, so a file deleted through Explorer reaches the Engine as a delete, never as a move into
  `$Recycle.Bin`; the place is known, but nothing arrives there to read. Emptying it is the snapshot's to see (storage).

---

## 3. Detective: a loose snapshot of the machine

**The idea.** A rough picture of the whole machine, taken now and then, compared with the last one. A sudden change shows what
events alone miss. Storage dropping sharply may be a clean-up or sabotage, and the same holds in other areas. Some changes matter
whoever made them, so this needs no learning at all: yesterday against today.

**Today.** Nothing compares the machine with itself over time.

**Detective's alone (the user, 15 Nov 2026).** The snapshot is part of Detective, inside it. No page shows it, Automation does not read
it, and an Admin never sees it as such: only a finding it led to, as evidence in a case ("Documents is 38 GB smaller than this
morning").

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
- **A sudden change becomes a signal**, and like every signal it is read several ways:
  - storage down 40 GB: in the Recycle Bin, Temp or Windows Update's folder -> a clean-up (quiet); in Documents or a share, by hand,
    after gathering -> sabotage or erasure (raised);
  - a new member of Administrators, Defender turned off, a new startup entry, the event log shrinking: worth a reading every time;
  - a program installed that copies or hides files (an archiver, a cloud sync tool, a wiper).
- **It also heals.** A snapshot that differs from what the events said (Documents is 2 GB smaller but no deletes came in) means events
  were missed. The index sweep is started for that folder. This is "proactive first, reactive second".

**Worst case, clamped.** A snapshot is at most a few hundred KB; the place sizes come from the index where it has them, a walk only
where it does not; a machine that is always busy gets its snapshot at connect only, and a finding says how old the snapshot it
compared with was.

**Built (15 Nov 2026).** `worker_client/machine_snapshot.py` takes the picture (two minutes after connecting, then every six hours);
`engine/detective/snapshot.py` (`detective.snapshot`) compares it with the last one, kept in `machine_snapshots` (migration 060, one row per
machine), and feeds each change to Detective as a signal weighed by `common.detective.SYSTEM_CHANGES`; Reach gained the area **Raise**, and
Evasion's **Dodge** and Erasure's **Switch off the record** are now seen. Tried on the dev machine: 17 KB, every section read. As built:
- **A person's own places are summed from the watcher's own record** (`index-state.db`), not walked: a real Documents of 151,000 files ran
  out a 30-second walk. Only Temp, the Recycle Bin, Windows Update's downloads and a place outside the watched folders are walked.
- **Only what both pictures have is compared**, and a place measured partly says nothing; the first picture is the baseline.
- **Falcon's own actions** in the same stretch halve what a change weighs, since it may be theirs; Falcon's own service, program and tasks are
  left out of the picture.
- **Weights are light**: only a new administrator, Defender turned off or an emptied event log come near "noted" alone; the rest add to a case.
- **Not in it yet**: BitLocker (no reliable way without WMI or a localised command's output), printers, and the USB devices (the drive
  watch already reports each drive as it is plugged in). **Healing** (a place that shrank with no deletes heard starts a sweep of it) is not
  built: the watcher already reconciles on its own timer, so missed events are found anyway, only later.
- **Six-hour resolution**: a change is placed at the picture that showed it, so it joins a case by the machine and the stretch of days, not by
  the half hour.

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

**Version 1, all of it (the user, 15 Nov 2026).** The packaging work will be redone (the user, 15 Nov 2026), so this work neither
waits on it nor fits around it. Each lands as Engine handler + TUI command first, then the concept, then the QML (the TUI is the
scripted test surface); the snapshot has no page of its own. Engine work and UI work stay in separate sessions. When this branch is
merged, `PHASES.md` and `START-HERE.md` get these items.

## Questions for the user

None waiting (15 Nov 2026).
