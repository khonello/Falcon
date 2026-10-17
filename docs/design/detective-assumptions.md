# Detective: assumptions, blind spots, and scenarios to attack (17 Oct 2026)

The owner's challenge: Detective is too centred on numbers, and it is meant to be built on human behaviour and psychology. This is the honest account of where
it leans on counts, every assumption in it, and a set of scenarios for the owner to break. Nothing here is a change yet; it is what to react to.

## 1. Is it number-centred? Yes.

Where a count decides whether anything is said at all:

| Graph | Needs |
|---|---|
| gathering (collection) | 8 restricted files in 10 minutes |
| archived (collection) | 3 or more files into one archive |
| mass removal (erasure) | 15 deletions in 2 minutes (25 by hand, and only after staging) |
| bulk destroyed / rewritten (sabotage) | 40 documents in 2 minutes |
| scrambled names (sabotage) | 10 documents renamed to one odd ending |
| outside role (reach) | 15 files across 3 folders in 20 minutes |
| uploaded | 25 MB in a minute |
| case level | combined weights: 0.35 noted, 0.60 case, 0.85 urgent |

What is already about the single act (no count): hidden, disguised, buried, to a drive, removed after taking, log cleared, screenshot tool / picture on the
clipboard, a machine going quiet with a case open.

What that means: **one deletion of the one document that mattered is invisible**, one peek at the one file someone should not look at is invisible, one file
quietly taken is invisible, a corrupted master file is invisible. The numbers measure *noise*; they do not measure *meaning*. A person who knows what they want
needs one file. The more purposeful the person, the fewer events they make.

### What it should be built on instead (proposal, nothing changed)
Three questions per event, quantity only as an amplifier:
1. **What is the thing worth?** The significance of a file, not its count: restricted mark; the only copy anywhere on the index; a task's or flow's source; belongs
   to someone else; sits in a compliance/audit/finance folder; recently edited by others; large age and long untouched then suddenly touched.
2. **Is this normal for this person?** A baseline per person and machine: the folders, programs, hours, volumes they usually have. Today the thresholds are one
   set for everybody ("usual" is the organisation's idea, not theirs). The deviation from *their own* pattern is the psychology; the absolute number is not.
3. **Why now?** The moment: what changed around them (a task overdue or taken away, a handover, a move of department, a session ended by a superior, a long absence
   then a return, an announcement). People act on a feeling that has a date. Time of day is a nudge already; the life-event around it is not used at all.

And the shape over time, not the burst: probing (a harmless file first, to see if it is noticed), rehearsal, escalation, a pause after being seen, displacement
(smaller and slower once watched).

## 2. Assumptions I made (every one that I know of)

**About what is seen**
1. Only watched folders are seen. Work moved outside the watch roots is invisible.
2. Restricted marks stand for "what matters". An important file nobody marked is just a file.
3. Metadata only: no content, so a file renamed and edited, or a secret pasted into a harmless file, is not seen. A password-protected archive is only an archive.
4. The person at the keyboard is the account's owner. Someone on a colleague's logged-in machine, or sharing a login, is read as the owner.
5. "By hand / started / alone" comes from input idle time (2 s, 30 s). A person who nudges the mouse to look present while a script runs is read as "by hand".
6. A machine that is switched on, online, and runs the Worker. Offline work, a second boot (live USB, a VM), or killing the Worker is only noticed as "went quiet", and only if a case was already open.
7. **Time:** events that arrive late (a machine back online replays missed ones) are placed at the moment they *arrive*, not when they happened. A burst caught up after reconnect looks like it all happened just now. (Likely a real defect, not just an assumption.)
8. Memory is six hours and a graph looks 15 minutes either side. A patient actor over days is only caught by the one scenario I wrote for it, not in general.
9. Falcon's own work (flows, actions) is never behaviour. An Admin who builds a flow that carries files somewhere is invisible to Detective by construction.
10. Nobody watches the Super User. Admin machines go to the Super User; the Super User's machine goes to no one.

**About what a signal means**
11. Doing it by a program on its own is slightly worse than by hand. A person who deliberately automates is read as less deliberate than one who does it by hand.
12. A task for a file, a flow, or an "allowed" mark lowers a finding by 0.45. A person can create a task or an allowance (or be given one) to cover themself.
13. A drive used three times is familiar and lowered. An insider can use the trusted drive, or build trust with it first.
14. Sync and backup programs "move data for a living" and are lowered: OneDrive, Dropbox, Teams, Zoom ... A personal sync account looks the same as the company's.
15. Disguise rule: a document renamed to an image/system/archive/media file. Other disguises (a document named like a document) are not seen.
16. Hidden = the hidden attribute. A file made unremarkable by any other means is not hidden.
17. A screenshot is only telling when restricted files were open in the last ten minutes.
18. A big upload is only telling after restricted files or an archive within 30 minutes; split into pieces under 25 MB a minute, or across programs, it adds up to nothing.
19. Public addresses are "out"; an internal share, another PC, a NAS are "in". Copying to a colleague's PC is not exfiltration.
20. The levels (0.35 / 0.60 / 0.85) and the 0.06 bonus per extra behaviour are my choices, not measured against anything but my own scenarios.

**About people**
21. Intent is inferred from a pattern of acts; there is no model of motive, mood, or the event that triggered it.
22. Everyone has the same normal. A new starter, a person on a project, and a night-shift person are all judged by the same thresholds.
23. A good employee with a history is not treated differently from a bad one; neither is a person who has been through something.
24. The person does not know Detective exists, and does not change behaviour because of it.

## 3. Scenarios to break

Each: the person, what they do and why it is human, what Detective does today, and the question. Marked:
**Sees** (a finding, a case likely), **Partly** (a finding that might not rise), **Blind** (nothing).

### Concealment (making something hard to find)
- **C1 The labeller.** Renames `payroll-q3.xlsx` to `Holiday photos 2019.jpg` in Pictures. — *Sees.*
- **C2 The zip.** Puts the one file in a password-protected zip called `invoice.zip` in Downloads. One file, so no gathering; a zip alone is nothing. — *Blind.*
- **C3 The slow burier.** Moves one restricted file a week into `Old\Archive\2019\misc`. Not a system folder; one a week. — *Blind.*
- **C4 The hiding copy.** Copies the file next to a similar-named file and leaves both visible. — *Blind.*
- **C5 The note.** Pastes the figures into a notes app or an email draft. — *Blind.*
- **Q.** How would you hide a thing from the one person who would look?

### Collection (gathering what they will take)
- **K1 The one-file collector.** Needs only the customer master list. Opens it, copies it. — *Blind until it goes to a drive.*
- **K2 The patient collector.** Two restricted files a day for a month. — *Blind (six hours of memory).*
- **K3 The curious auditor.** Opens ten restricted files because it is their job. — *Partly (noted, lowered by a task if one exists).* Risk of a false alarm.
- **K4 The searcher.** Uses search to see names without opening anything. — *Blind.*
- **K5 The new starter.** Reads everything in the first fortnight. — *Partly.* Needs a baseline to be fair.
- **Q.** What would you collect first, and what would you leave alone to look ordinary?

### Taking out (exfiltration)
- **E1 The phone.** Photographs the screen. — *Blind by design.*
- **E2 The webmail.** Uploads the file to a personal mail in the browser, 4 MB. — *Blind (under 25 MB).*
- **E3 The drip.** 10 MB at a time every two minutes through the browser. — *Blind.*
- **E4 The trusted drive.** Uses the department's usual drive, after using it for harmless things for weeks. — *Partly (lowered, 0.35).*
- **E5 The cloud folder.** Drops files into the company's sync folder that is also tied to a personal account. — *Blind (sync clients are lowered).*
- **E6 The test run.** Copies a harmless file to a new drive first, to see if anyone reacts. — *Partly (a new drive adds 0.10).*
- **E7 The flow.** An Admin builds a flow that mirrors a folder to a share they control. — *Blind (Falcon's own work).*
- **E8 The print.** Prints it. — *Blind.*
- **E9 The colleague's PC.** Copies to a coworker's machine across the network. — *Blind (internal).*
- **Q.** Which of these would you actually use, and what would make you choose a different one?

### Capture (taking the information without the file)
- **P1 PrintScreen.** — *Sees when restricted files are open.*
- **P2 The phone camera.** — *Blind by design.*
- **P3 The recorder.** Starts Game Bar / a meeting share / a screen recorder not on my list. — *Blind (list only).*
- **P4 The remote session.** Copies through a remote desktop's clipboard. — *Blind.*
- **P5 The capture after closing.** Takes the picture a minute after the file is closed. — *Blind (the file is no longer "open").*
- **Q.** What would you use that is not on the list?

### Covering up (erasure)
- **R1 The one document.** Deletes the single contract amendment that shows what was agreed. One file. — *Blind unless it follows a copy to a drive.*
- **R2 The alteration.** Opens the restricted record and changes one figure, then saves. Nothing deleted. — *Blind: alteration is not a behaviour at all.*
- **R3 The wipe of the trail.** Clears Recycle Bin, browser history, recent files. — *Blind (only event logs are seen).*
- **R4 The tidy-up after.** Deletes thirty old files after a leak. — *Sees now.*
- **R5 The timestamp.** Resets a file's date to look untouched. — *Blind.*
- **Q.** What would you most want to be able to say "I never touched that" about?

### Evading (not being watched)
- **V1 Offline first.** Unplugs the network, works, plugs back in. The events come late and are placed at arrival time. — *Partly, and the time is wrong.*
- **V2 Outside the roots.** Does the work in a folder the Worker does not watch. — *Blind.*
- **V3 Another boot.** Starts a live USB or a VM. — *Blind.*
- **V4 Kill the Worker.** Stops the process. — *Partly (quiet only if a case was open).*
- **V5 A second account.** Works as a different local user. — *Depends on what the Worker watches.*
- **Q.** How would you slip it, knowing it only reacts to a case already being open?

### Wrecking (sabotage)
- **B1 The one file.** Corrupts the master database or the one config everyone depends on. — *Blind.*
- **B2 The slow poison.** Changes a few numbers in a reference sheet each day. — *Blind.*
- **B3 The lock-out.** Changes permissions so others cannot open a shared folder. The `permissions` act exists but nothing reads it. — *Blind.*
- **B4 The backup.** Deletes the shadow copies or stops the backup job, then wrecks. — *Blind to the first half.*
- **B5 The ransom pattern.** — *Sees.*
- **B6 The sixty drafts.** — *Quiet, as it should be; raised if they were restricted.*
- **Q.** If you wanted to hurt the team and look innocent, what is the smallest thing that would do it?

### Reaching (going where they have no reason to)
- **Q1 The one look.** Opens the director's folder once. One file, targeted at one person. — *Blind. Arguably the most telling kind.*
- **Q2 The walker.** Browses folder lists without opening anything. — *Blind.*
- **Q3 The borrowed seat.** Uses a colleague's logged-in machine. — *Wrong person, silently.*
- **Q4 After the news.** Looks around right after a colleague is let go or a handover. — *Blind to the "why now".*
- **Q5 The wide sweep.** Fifteen files across four folders in twenty minutes. — *Sees.*
- **Q.** What would you look at, and what would make you stop?

## 4. Questions I would like the owner's help on
1. Which of C2/K1/R1/R2/B1/Q1 (single, meaningful acts) should be a finding on their own, and what makes the *file* meaningful to you?
2. Is "alteration" (changing a restricted record, not deleting it) a ninth behaviour, or part of erasure/sabotage?
3. How should the person's own baseline be built, and how long before it can be trusted? (A new starter has none.)
4. What life events around a person may Detective know about, and which is it not allowed to use? (Falcon already holds tasks, handovers, session blocks, absences.)
5. Should Admins and the Super User be watched for Falcon's own tools (flows, actions, tasks) being used as the channel?
