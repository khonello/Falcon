# To look at

Open items to go over with the user. Bring this up first in a new session, then tidy it as items close.
Last updated 13 Oct 2026.

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
