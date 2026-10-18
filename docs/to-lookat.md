# To look at

Open items to go over with the user. Bring this up first in a new session, then tidy it as items close.
Last updated 18 Oct 2026.

## Waiting on a decision

- Nothing. (Hostname mismatch decided 13 Oct 2026: the console says "recorded, not blocked", as the Engine behaves.)

## Not exercised yet

- **Session window with a real console watching a real desktop.** The pieces are tested apart (frames, input, helper,
  service), never end to end.
- **Tier-only file-open rules.** Not watched live by design: the Worker cannot decide them, and the log says so.
- **Department-level issues with an empty `pc_id`.** The Engine never raises one. The GUI session was told. Nothing to
  change unless the user names one they expect.

## On hold until everything is locked

- **Final packaging** (plan in `docs/PACKAGING-PLAN.md`; the installers' code is written and tested in `installers/`): bundled interpreter, installer, signing, helper windows built as executables, delivery of the
  Engine's certificate and key with the install. The small packaging (`python -m worker_client service install|start|stop|uninstall|status`)
  is done and tested.

## Housekeeping

- **GUI session message** (handler names, session window caveat, empty `pc_id`, hostname wording) was queued while
  that session was offline. No confirmation it was read.
- **`CLAUDE.md` was committed whole in 3000d67**, so it may include the GUI session's console-line edits. Check the diff.
- **Decided, for the record:** Admin from another department stays disabled; retention is 90 days on the audit clock
  (`audit_log`, `file_events`, run outputs), logged per part.

## Found while trying the session window live (13 Oct 2026)

- **The blocked person's bar is the Worker's overlay, not the console's** (decided 13 Oct 2026): nothing to build in the console; the Admin installer puts the overlay on the Admin's PC.
- **Block vs end an Admin's session.** The Engine treats both the same; the dialog offers both.
- **Session window:** picture, mouse and (by script) keyboard injection work; overlays shown on the Worker PC for see and control. Left: typing through the console on a second machine.
- **Fixed in GUI files by this session:** auto-connect on start (`app.py`), `EnterConsole.qml` (`enter` clashed with the
  popup's own; the mode sent was "block"/"end"), the three pages that enter a machine now send the take-over.

## Installers (13 Oct 2026)

- **Written and tested; the Engine's installer was also run for real on Linux (WSL), twice, and removed.** Not yet on a clean machine. The Hyper-V pass should do, in order: the Engine's installer (Linux VM, with the `.deb`), then the Super User's,
  an Admin's and a person's PC (Windows VMs), confirm each registration, and try the console as a non-administrator user on the Admin workstation (the pipe's access rules).
- **Decide:** is the Super User's PC also a managed machine (the Worker service on it)? Today the Super User's installer is the console only.
- **Not mine, and removed from the list:** the Admin console needs no blocked bar; the overlay on the Admin's PC does it (the Admin installer puts the Worker pieces there).

## Flow, Restricted, Task tried live (14 Oct 2026)

- Fixed along the way (see `ENGINE-GAPS.md`): big files, a destination that was away, files already in a source folder, a file mid-write, a marked file being moved, an allowance by path, `index.search`, ghosts in the index.
- **Decide:** should a file deleted at a flow's source also be deleted at its destinations? Today it is not (the design says "destination updated to match source"; deleting is the risky half).
- **Done since:** the console's own forms are scripted live (`live_drill.py forms`, 18 checks) and the default Qwen3-1.7B model is downloaded and probed 8/8. **Still only on separate machines:** a flow between two real PCs (`docs/VM-TEST-PLAN.md`).

## Proactive and reactive (16 Oct 2026)

- Built: the index reconciles on start, reconnect and a timer; the Engine heals flows, marks and tasks on timers; a flow never overwrites what it did not write. See `ENGINE-GAPS.md`.
- The two-PC Flow test, the away-and-back tests and the non-administrator console test are in `docs/VM-TEST-PLAN.md` (needs a machine with ~14 GB free for the guests).
- Still open: should a deleted source file be deleted at destinations? (Today: no; the destination keeps its copy. The user said that is what they first thought.)

## Task creation, hardened (16 Oct 2026)

- **`@` dialog** (New task): `@` lists Person / File / Folder / Program / Deadline; Up/Down move, Enter or Tab take the highlighted one, Esc closes. `@file:`, `@program:`, `@folder:`, `@deadline:` can also be typed straight. A file or program asks a second question (what should happen to it). What is marked goes to the Engine as `hints` and is taken as given; the patterns and the model only read the rest. Tested with real key events (`tests/test_task_mentions.py`).
- **One deadline reader** (`common/when.py`, 124 cases): used by the Engine, the console and the dialog. It never guesses: `3/4`, "Monday or Wednesday", "next week" are refused with the reason. `task.when` and `falcon.readWhen` expose it.
- **The model**: cached, time-limited per call and per proposal (75 s), declared away only after 3 failures in a row, refuses prompts too long to ask, text can't close its own quotes. `task.propose` returns `model` stats and `notes`.
- **Benchmark on this machine (Windows wheel):** the 1.7B scored 26/27 tuned and 26/32 held-out before the verb fixes (export, back up, rename, "must be on", "Monday's review" were cue-list gaps, not model errors). After them: tuned 32/32, fresh held-out 31/31. The 29/32 in CLAUDE.md was measured elsewhere.
- **Command palette**: Ctrl K and Ctrl P open it, Ctrl Shift P opens it in `>` command mode (commands, pages, "New task/flow/rule"); it now also finds tasks and flows (and rules at the Super User's level), and the list follows the arrow keys.
- For the GUI session: I edited `SmartText.qml`, `NewTaskPage.qml`, `NewFlowPage.qml`, `TaskChart.qml`, `Palette.qml`, `main.qml` (two shortcuts) and `bridge.py` (`readWhen`).

## A deleted source file: now a choice per flow (16 Oct 2026)

- Decided with the user: each flow chooses, in its setup beside the source: **Keep the copies** (the default) or **Remove the copies**. `flows.on_source_delete`, migration 032, `flow.create` / `flow.edit` take `on_source_delete`.
- Remove means *put aside*: the destination's machine moves its copy into `.falcon-removed` under the destination folder, only if the flow wrote it and it is unchanged since (otherwise it is kept and the creator is told). A destination that was away is dealt with on catch-up. A mirror never removes anything because a listing came back empty (`flow.mirror_held` in the audit).
- Not built: a console-wide default for new flows (each new flow starts on Keep).

## A local memory of lookups (16 Oct 2026)

- `operator_client/core/lookup_cache.py`: a small JSON file next to the console's settings (`<settings>.cache.json`), per signed-in account and Engine (another account starts empty), every section dated, bounded (2000 items, 30 days), written atomically, an unreadable file is just empty. Read-only convenience: the Engine stays the only source of truth.
- Kept now: the people/machines tree (what the `@` person list and the palette's machines need) and files you picked (offered again as "seen before" when the index says nothing or there is no Engine). Offline, the `@` list says "Offline: showing what was known".
- Not cached on purpose: the whole file index, sessions, health, issues.
- Next if wanted: recent tasks/flows/rules for the palette, and a "last updated" line on the pickers.

## The Worker's task reminders, and a small list of "my tasks" (16 Oct 2026)

- A task window used to open once; closed without Start, it was never seen again. Now `worker_client/reminders.py` keeps the tasks waiting to be started and shows each one's window again (15, then 30, then hourly), marked "Still waiting to be started", one at a time, never while a superior is using the machine, never once started/finished. Rebuilt from the Engine at every connect, so a restart forgets nothing.
- New window kind `tasks` ("Your tasks"): everything assigned to the person, soonest due first, Start on what is not started. Opened from the tray (click the icon, or "My tasks"); the tray menu also still has "Ask my Admin for help".
- Pickers say how old their names are: "Not connected. Names as of ..." (palette; the pages themselves are replaced by the Connect screen while disconnected), or "Names as of ..., from the last time you were connected. Updating." just after start.
- Still to look at on a real desktop (VM plan): the tray icon, the reminder window popping over other applications, the list window from the tray.

## Moving the Super User to a dedicated machine (16 Oct 2026)

- Built (Engine + TUI + installer option): `handover open | status | confirm <id> <code> | cancel`, migration 033, `python -m operator_client --handover-join`, and `installers.windows.install --role superuser --handover`. See `docs/GETTING-STARTED.md`. Tested end to end (`tests/test_handover.py`): same account, one Super User at all times, old key stops at once, wrong codes and expired windows change nothing.
- Not built: a page for it in the console (Access / Registry) — today it is TUI commands. Nothing for the old machine afterwards except registering it like any other.
- Still your decision: should the old machine be kept as an ordinary managed machine? (Default: it is just unbound; register it as a Worker if you want it.)

## The Falcon program on a Worker's machine, announcements, quiet reminders (16 Oct 2026)

- **The program** (`python -m worker_client.program`): tray icon + one small window with four tabs — Today, Tasks, Announcements, My machine. Its own calm look, not the console's. It holds no key: it asks the Worker service on the same machine over a loopback socket (`worker_client/localapp.py`, `app.json` with a port and token beside the settings), and when the service is away it shows what it last knew and says so. Starts at sign-in (a Run entry, installed by the Windows installer for Worker and Admin PCs), opens from the tray icon or the Start-menu "Falcon" shortcut, one copy per person. It replaces the tray icon and the "your tasks" window.
- **Announcements**: an Announcements page in the core menu at both levels (compose; sent / scheduled / withdrawn list); Workers read them in the program. "Delivered is enough": no read tracking. An **emergency** also covers the screen (new overlay kind) until the person says they have read it; one not yet read is shown again after a restart or a reconnect, for a day.
- **Quiet reminders**: a task passed over gets a small corner note from the program after an hour, then four, then every eight — never a window over their work. The task's own window still opens once when it is given.
- Old machine after a handover: unbound, no longer part of Falcon (the message says so).
- Needs a real desktop to judge (VM plan): the tray icon and its number, the corner note, the program starting at sign-in, the emergency covering a real screen, the Start-menu shortcut.

## Messages now holds announcements; Detective is a blank page (16 Oct 2026)

- Announcements are a second side of **Messages** (a "Conversations | Announcements" switch at the top of both), no longer a menu item. The compose form offers two kinds, Announcement and Emergency (the Engine still supports Warning). The palette has "New announcement".
- **Detective** is in the Core menu at both levels as an empty page, only so the menu can be decided. Menu decided: **Home** (Overview, Messages), **Core** (Tasks, Flows, Restricted, Detective), then the rest.

## Detective, first slice (16 Oct 2026)
- Built: the behaviour model (`common/detective.py`), scripted scenarios (`python scripts/detective_scenarios.py`), the Engine keeping/raising/reviewing cases
  (`engine/detective`, `detective.*`), the Worker telling "made hidden" from other attribute changes, and `detective` commands in the shell. Design and the
  decisions: `docs/design/detective.md`. The Detective page is built (cases, the picture, the story, review).
- The leak scenario raises while the files are still on the machine ("It has not left the machine yet"); the backup twin with the same moves stays quiet.

## Detective, the rest of it (17 Oct 2026)
- Built: the witness layer (by hand / started / alone, the program that made a change from Windows' file trace, USB serial and label, log clearing, screenshot tools, a
  machine going quiet), graphs for all eight behaviours, the local model as a labelled second opinion, a live demo (`scripts/detective_demo.py`). See `docs/design/detective.md`.
- The model was measured: the second opinion is used; renaming labels were left out because the rule alone beat it (the benchmark is there to repeat with a bigger model).
- Still open: clipboard / PrintScreen, per-program network, writing a dismissal as a rule that applies again, and a real-desktop look at the page (VM plan).

## Hot/cold, limits, the spine, restricted flows, the actors (18 Oct 2026)
- Built: hot/cold ordering of the Worker's sweep and catch-up, program lists and the Engine's healing (`common/heat.py`); limits and an assessment before marking a folder restricted (`marks.assess`, 20,000 files a mark,
  100,000 a machine, generated folders covered but not tracked); worst cases in `docs/design/worst-cases.md`; the event spine (`engine/bus.py`, `docs/design/the-spine.md`); flows pause and ask the owner before
  carrying anything restricted (`flow.restricted*`); 39 actors against Detective (`docs/design/detective-actors.md`).
- **Done since:** the marking assessment is measured (the Engine's own time per file, slowed when it is busy) and shown on the Mark page before anything is done; flows waiting for a restricted owner are answered on
  the Flows page; the Super User's move to another machine is on the Registry page; every list read has a hard cap; Task, Flow, mark and case events are on the spine with the facts `task_expects`, `flow_route`,
  `flow_bypass`; Detective proposes (pause a flow, mark a folder, a follow-up task) and a person decides (`proposals`).
- **Console, 18 Oct 2026:** the proposals are on the Detective page and in the Super User's queue; flows waiting for a restricted owner and a machine asking to become the Super User's are in the queue too; the Admin's Overview counts suggestions and flows to allow (`overview.admin`); the Restricted page shows what is tracked by content, what is generated, and which flows carry a mark. The spine's health stays a debugging tool, not a page.
- **Still not done:** a bounded priority queue on the bus; Reports/Notices as the spine's "tell" stage; the dormant sources (the Engine produces `opened`
  events and the outside-role tag only from the new file-open batches, which need the Worker's file trace, i.e. an elevated service on a real machine).
- **Waiting on the owner:** how they would get around the Detective scenarios (`docs/design/detective-assumptions.md`); whether the Super User's old machine is re-enrolled as a managed machine (default: unbound);
  the VM runs (two-PC Flow, keyboard control, away-and-back, the tray / overlay / program at sign-in / Detective page on a real desktop).
