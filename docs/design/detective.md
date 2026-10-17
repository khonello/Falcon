# Detective

What a person seems to be trying to do, read from several small things happening together on a machine. Not "this event, so do that": a model of
human intent. Built 16 Oct 2026 from the owner's brief; `common/detective.py` is the matcher, `engine/detective/` keeps and routes what it concludes,
`scripts/detective_scenarios.py` plays scripted people against it.

## Decisions (the owner, 16 Oct 2026)
- **Who sees what:** coverage of Admin machines goes to the Super User; coverage of department machines goes to that department's Admin (and the Super User).
  An Admin never sees their own machine's cases.
- **Automatic, not triggered**, and the person at the machine is **not told**. (Live screen viewing is a separate feature and still tells the person.)
- **Windows-first** (the signals come from Windows; the Engine is the part that runs on Linux).
- No legal constraint was stated on window titles and file names appearing in evidence.
- Eight behaviours from the start, Reach included.

## The model
- **Behaviours** (human words): concealment, collection, exfiltration (taking out), capture, erasure, evasion, sabotage, reach.
- **Mini-graphs**: each behaviour owns a few small patterns. A pattern has one **spark** (the event that starts it) and, only when it appears, looks back and
  forward over a window for supporting steps -- so it is cheap. Built so far: hidden, disguised name, buried (concealment); archived, gathering (collection);
  to a drive, drive after staging (exfiltration); removed after taking, mass removal, history cleared (erasure); outside role (reach). Capture, evasion and
  sabotage have vocabulary but no graphs yet (they need signals the Worker does not send yet).
- **Case**: findings about the same machine and files, collected under one **intent** ("Taking data out", "Covering up", "Gathering", "Looking where they should
  not", "Hiding something", "Wrecking things"), with the **stage** reached out of five (Reaching, Gathering, Hiding, Taking out, Covering up), the step that has
  not happened yet ("It has not left the machine yet") and what usually comes next. The verdict is the case's, never one graph's.
- **Thread**: findings join a case when they share a file (identity/content survives rename and copy, an archive carries its sources), or fall in the same sitting
  (2 h), or continue the same arc on the same machine within 7 days (the patient actor).
- **Weight**: independent hints combine (1 - the chance every one is nothing) with a small bonus per further kind of behaviour. Levels: noted (0.35, kept quietly),
  case (0.60, raised: Super User and Admin told), urgent (0.85).
- **Context** lowers or raises a finding: Falcon's own work is ignored entirely; a task for that file, a flow that wrote it, a recorded allowance, a drive this
  machine uses all the time, and programs that move files for a living all lower it; a drive never seen before raises it; time of day only nudges, never starts anything.
- **Provenance** (`Sig.by`: hand / started / alone / falcon / unknown) is a weight, never a verdict. Today the Engine marks Falcon's own writes and leaves the rest
  "unknown"; the Worker's witness layer (process for each change, whether input just happened, foreground program) fills it in.
- **Voice**: a pattern and its evidence, never an accusation or a cause; every finding says what would make it innocent. Review uses the deviation outcomes
  (explained / accepted / dismissed / escalated) and is audited.

## Where it runs
The matcher runs in the Engine over the file events and drive signals it already receives (control.signal interest now always includes usb.inserted/removed).
It is stdlib-only so it can move to the Worker later (raw activity then never leaves the machine; only findings do) without changing what the Engine keeps.

## The witness layer (built 17 Oct 2026)
Every file change the Worker reports carries a stamp (`worker_client/witness.py`): **by** hand (input in the last 2 s) / started (a person is about, or a script they
ran) / alone (nobody for 30 s) / unknown, the **program in front** (for hand), and the **program that made the change** -- Windows' own file trace
(`worker_client/etw.py`) remembers which program last opened each file under the watched folders, so a person's `powershell` or `robocopy` is "started", not "by hand".
A service in session 0 sees no desktop, so it asks the helper on the person's desktop and otherwise says "unknown" rather than guess. Also: which attribute changed
(hidden/system/read-only, before and after), a USB drive's own serial and label (the same drive in another letter is still familiar), the machine's own event logs
for a clearing (Security 1102, System 104), screenshot-tool starts, and the Engine hearing a machine stop reporting.

## Behaviours and their graphs (all eight)
Concealment: hidden, disguised name (document become system file, picture, song, archive, or given a second extension), buried. Collection: gathering, archived.
Taking out: to a drive, drive after staging. Capture: a screenshot tool started while restricted files are being worked on (more weight when started again and again).
Erasure: removed after taking, mass removal, history/log cleared. Evasion: a machine goes quiet while a case is open on it (a closed laptop alone is nothing).
Sabotage: documents deleted, rewritten or renamed to one odd ending in bulk. A program doing it is the loud case; a person's own hands doing it is **not**
innocent by default: it starts low (sixty old drafts in one folder stay under "noted") and is raised by what went (a quarter or more restricted, half or more outside
their work, many folders, a very large number). The same sixty deletions are very different in a folder of drafts and across the restricted share. Reach: files opened across folders outside one's work.
A case already raised that turns graver (hiding becomes taking data out) is told again.

**One signal, several readings.** What means little in one reading can mean a lot in another, so a signal is never owned by one behaviour: every graph that can use it
looks at it. A burst of deletions is read as sabotage (damage: by whom, of what, how widely) and, separately, as erasure when it follows gathering, hiding or taking out
on that machine (covering what was done). Thirty deletions by hand after a leak are erasure; the same thirty with nothing before them are nothing. A hidden flag is
concealment alone, but the same file then going to a drive is exfiltration of a hidden thing. Findings combine into the one case, so each reading adds to the others.

## The local model: measured (scripts/detective_model_bench.py, Qwen3-1.7B)
- **Second opinion on a case: used.** In the background, beside the rules' own conclusion, labelled as the model's, never changing a weight or a level. It reads 5 of 7
  scripted cases as a careful person does (misses: the ransom case read as taking data out, snooping as nothing odd).
- **Labelling a rename as a disguise: measured and left out.** With the classes of file in the rule (document / picture / song / archive / system) the rule is right on
  every rename (9/9 tuned, 8/8 held out); the model alone was 9/9 tuned but 6/8 held out and the two together 7/8 (a false alarm). It earned nothing, so it is not used;
  `looks_disguised` stays so the measurement can be repeated with a bigger model. (An earlier prompt that offered two descriptions to choose between made the model
  answer the same thing every time -- the collapse the probe exists to catch.)

## Showing it
`python scripts/detective_scenarios.py` plays scripted people against the matcher. `python scripts/detective_demo.py ...` plays one live against a running Engine as a Worker
you name (only messages are sent; nothing on any machine is touched), so the case appears on the page as it happens.

## Decided against, for now
- **Matching on the Worker.** The Engine already receives every file event for the index, and events missed while offline are caught up on reconnect (the reconcile), so
  moving the matcher to the machine would add a second pipeline for little: raw activity is already sent for the index. The matcher is stdlib-only, so it can move later.

## A dismissal written down as a rule (built 17 Oct 2026)
Reviewing a case as dismissed or explained, the reviewer may ask to remember it for the program, the folder or the drive the case involves. That writes a rule
(`detective_rules`, migration 037): this kind of finding, on this machine, with that program / in that folder / on that drive, is fine. A rule only **lowers** a matching
finding (by the same amount as a recorded allowance); the finding is still kept and says "you ruled folder E: fine for this on 17 Oct". Rules are listed (`detective rules`,
`detective.rules`), can be taken back (`detective unrule`, `detective.rule_revoke`), are audited when made and when revoked, and are scoped like cases (an Admin: own
department's client machines). Nothing is written down unless it was asked for.

## Anchors: the areas an intent covers (built 17 Oct 2026, the owner's model)
The owner's idea: each intent has a few **anchors**, and every event that bears on it falls in one of them *whatever the route*. A pen drive, a browser, a share all fall
in the same area of taking data out. **An anchor is a definition of coverage, not a step**: no order, none required, and filling more of them is not "getting further", only
more evidence. (`common/anchors.py`.)

| Intent | Areas |
|---|---|
| Taking out | Gather, Transform, Compress, Transfer |
| Collecting | Access, Assemble, Consolidate |
| Hiding | Disguise, Relocate, Protect |
| Covering up | Remove, Alter, Clear the trail, (Switch off the record: no signal yet) |
| Capturing | Open the source, Capture, Keep, Pass on |
| Slipping the watch | (Test: no signal yet), Switch off, (Dodge: no signal yet) |
| Wrecking | Reach, Disable safety nets, Destroy |
| Looking where they should not | Find, Beyond role, Widen, Return |

- **Intents contain intents.** Taking out is partly collecting, hiding and capturing; wrecking is partly covering up. What falls in a child's areas counts toward the
  parent at 60%, and an event already counted in the parent's own areas is not counted again as the child's.
- **Weighing.** Each event gets a weight of its own: what was done (a copy to a drive is heavier than a copy to another folder) plus how much the *thing* matters (restricted;
  the only copy the index knows of, counted fully only beside something else that says it matters; a name or place such as contract, payroll, director). An area is
  its heaviest event, or - for many light ones - what they add up to, but **numbers alone stop at 0.30, under "noted"**. Covering more areas adds a little. No area
  has to be filled and one heavy event is enough: one deletion of the only copy of a restricted contract is a case; sixty old drafts are not.
- **A piece of work** is the events that share a file (identity or archive contents, including what was gathered into the archive's folder weeks before) or happen within half
  an hour of each other. The board keeps 30 days, so a person who gathers a file a week and packs it on day 22 is one piece of work.
- **It is a floor, not another vote.** Coverage describes the same events the other graphs describe, so it does not stack with them: a case is at least its strongest
  coverage and otherwise the combined graphs, as before. Coverage too light to be "noted" is kept on the board but names no intent. Context (a task, a flow, an
  allowance, a trusted drive, a backup program) lowers coverage in proportion, since it is a sum of many readings.
- **The page** shows "What it covers": for each intent in the case, its areas, filled when something falls in them, and "no signal yet" where we have none. Nothing is
  drawn as a sequence.
- **Misfire over oversight** is carried by the weights, not by hope: a lone Transfer to a share is "noted", the first look outside one's work in a place that matters is
  "noted", any single heavy act is a finding. The price (more false alarms) is paid by making them cheap to dismiss: a dismissal can be written down as a rule.

**Things I found while building it, to be aware of**
- The Engine never produces `opened` events or the `outside_role` tag, so Collecting's *Access* (from opens) and all of Looking-where-they-should-not exist in the matcher
  and the scenarios but are **dormant in production** until a source for them is built (file opens are only reported for automations' file-accessed interest).
- Files found when a machine reconnects (the Worker's catch-up) used to look like they had just happened and by nobody. They now carry the file's own time and are marked
  "found afterwards"; the Worker did not queue events while offline, so what happens offline is seen at reconnect only as files that are new or changed (deletions are seen
  too). The journal of offline events with real timestamps and witness is still to be built.
- The same sixty deletions score 0.28 (a folder of old drafts) or 0.64 (restricted, outside the person's work): the thing and the person's pattern matter more than the count.

## Pictures on the clipboard, window titles and what a program sends out (built 17 Oct 2026)
- **Clipboard.** PrintScreen puts the whole screen on the clipboard and Win+Shift+S a region, so a screenshot needs no tool. `worker_client/clipboard.py` (run where the
  person's desktop is: the helper when the Worker is a service) watches Windows' clipboard change number and, when it moves and the clipboard now holds a picture, reads
  the picture's width and height from its header. It never reads pixels or text. A picture as large as the screen is "screen", smaller is "region"; it is sent as
  `screen.captured` (always wanted when Detective is on), and Detective reads it with the screenshot-tool graph (capture), which does not count twice when a tool that
  was just started took the picture.
- **Window titles.** The title of the window in front is added to the witness stamp for a person's own hands, trimmed to 160 characters, and kept only in the evidence
  of a finding (it reads "opened payroll.xlsx (in "Payroll Q3 - Google Sheets")"). It is not written into the file event history.
- **What a program sends out.** The Kernel-Network trace (same machinery as the file and process traces) counts, per program, what it sends to addresses outside this
  network; volumes only. When one program has sent 8 MB in a minute it is said once (`network.upload`, again after ten minutes). Detective reads it as taking out,
  low alone (a video call, an update), raised after restricted files were worked on or an archive was made, and lowered for sync and backup clients. Verified against a
  real loopback transfer on this machine.

## Not built yet
Nothing in the original list. Remaining is verification, not building: the tray, the corner notes, the emergency overlay, the program at sign-in and the Detective page
on a real signed-in desktop and a second machine (`docs/VM-TEST-PLAN.md`); the clipboard and the upload trace need a signed-in desktop and an elevated service to be
seen working outside a test. What an upload carried is not known (volumes only), so a sync client that sends company files to a personal account looks like any other.
