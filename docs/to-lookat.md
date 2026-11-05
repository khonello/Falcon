# To look at

Open items to go over with the user. Bring this up first in a new session, then tidy it as items close.
Last updated 5 Nov 2026.

## What is really open (checked against the code, 5 Nov 2026)

Every call the console, the TUI and the Worker make has a handler. These are what remains; the rest of this file is the record.

**For the user to decide:** nothing is waiting (5 Nov 2026).

**Waiting on the user to say go**
- Replace the Groq key given in the session, before anything ships.

**Needs real machines, not code** (`docs/VM-TEST-PLAN.md`): Office conversion, a second Windows user refused a Private file, a machine updating itself, the installers on a clean machine, a real printer going offline, real failed sign-ins, a flow between two PCs, the session window end to end, the console as a non-administrator, the tray, overlays and program on a real desktop.

**Unexplained:** a full test run froze on 4 Nov 2026 at 18:32:31 (no CPU, 74 threads waiting, the 180 s limit never fired). Not the Wi-Fi drop: that was 19:07:28. The likeliest cause is the `winnotify` memory fault, fixed at 23:52 after that run. Not seen since in 2 full runs and 4 repeats of the Worker tests, which is not proof.

**Flaky, timing only:** `test_the_screen_streamer...` (the streamer hears stop only on its next send, and an unchanged screen sends nothing) and `test_chain_resource_violation...` (waits 15 s for a process). Each failed once under load and passes alone (6 of 6, 5 of 5).

**Hands-on:** all four scenarios in `docs/HANDS-ON-SCENARIOS.md` were run end to end on 5 Nov 2026 by Claude, with real Notepad and File Explorer by keystroke, and passed, through the TUI. A real USB stick and USB hard disk were tried too (`worker_client/drivewatch.py`): both had been invisible until then. Not covered: the same journeys through the console's pages.

**Settled 5 Nov 2026:** an Admin's PC that dies frees the person after two minutes (built). "Work on a spreadsheet" with no file named keeps asking. Detective flagging a restricted file opened by an unusual program: dropped, as Windows reports tens of thousands of file opens in seconds, mostly backup, antivirus and indexing, so it would be false alarms. Detective's blind spots are not a question for the user: `detective-assumptions.md` was answered on 17 Oct with the anchors, and what is left there is known limits.

**Later, by decision:** the licence store; packaging (Phase 9).

## Answered 4 Nov 2026

- **Any Admin verifies a task:** yes, and built.
- **Only a rule's maker changes it:** no. The user told the Engine session (4 Nov) that every IT Admin covers everything and the log shows who; the concept's "only A. Quaye changes it" goes.
- **The concept's contradictions:** corrected towards what is true. Automation's Next is the real next run, Actions counts all eight rules, Flows has the Engine's steps, and a case's
  account says who wrote it as it happened (its wording is on the UI's list: only Groq smooths now, not the local model).
- **Add a machine is gone** (the user asked, 4 Nov): a machine joins with its licence code at setup. Machines shows Waiting to join only for one installed without a code,
  let in with the code on its screen. New key moved to the TUI (`machine newkey`, the user, 5 Nov 2026). The Registry page (not on the menu) still has the old Register a PC.
- **The flow's Keep / Remove the copies:** back, in the concept and in Make a flow. **Task split is gone** (the user, 4 Nov): a description is one task, in the concept and the console.

## Answered 3 Nov 2026

- **#15 A case told in words:** *(built)* way (a), then a smoothing pass: the Engine writes the account with every fact from the case; the model
  may rewrite the words between the facts, and its paragraph is kept only if every fact is still there, in order, with nothing added.
- **#13:** *(built)* Try a rule first (`control.rule_try`, TUI `event try`). The other two ideas are dropped.
- **`pc_days`:** *(built)* on the 90-day clock an issue asks the Admins to Delete or Keep; kept, it asks again in 30 days.
- **#10 Seen on the network:** dropped. What the Engine has (joining with a licence code, knocked PCs) is enough; the drawer change is the UI's.
- **The licence store:** the user's design, for later: admin and worker codes are downloaded (one file or two); the admin console's setup takes an
  admin code, the Worker's a worker code; the codes live in a remote store that the Engine asks at setup to validate a code (a little outside
  access at setup is fine), and a small website sells them. Today's `licence import` stands in until then.

## Coverage (the user, 4 Nov 2026)

- Every IT Admin covers everything, restricted included; the audit trail shows who. Pages say "Set by", never "owner". An Admin-to-Admin flow still waits for the destination Admin to agree and pick the folder: kept on purpose.

## Flow steps as a tree (the user, 3 Nov 2026; built 4 Nov)

- **Built:** Category > Kind > Operation > settings (`engine/flow/steps.py`, `flow.steps`, TUI `flow steps`): Choosing, Conversion, Renaming, Bundling. Placing and Unbundling dropped.
- **Not run for real:** Word, Excel and PowerPoint conversion and PDF to DOCX (no Office or LibreOffice on the dev machine; tested with a stand-in).
- **Add a date:** *(decided 4 Nov 2026)* only the newest stays: an edited file's older copy is put aside in `.falcon-removed`.
- **LLM (4 Nov 2026):** Detective's smoothing is off (the 1.7B copied or spoiled most paragraphs, even with a worked example); `tests/test_llm_real.py` runs the real model.
- **Task descriptions:** the user has no more for now (5 Nov 2026), so do not remind them. `data/real-task-descriptions.txt` and `scripts/llm_real_wording.py` are there if more come.
- **Smoothing (4 Nov 2026):** Groq smooths the events paragraph when a key is set; 8 of 8 real paragraphs rewritten and checked. No key: the Engine's own account.
- **Flow steps:** Into one PDF dropped too, with `pypdf`.
- **Qwen3-4B test (5 Nov 2026):** held-out, same 31 cases: 1.7B 31/31 at 3.7 s a call; 4B 30/31 at 6.9 s; Groq 30/31 at about 1 s. Not better and twice as slow, so the 1.7B stays and the file was deleted (the user).
- **Groq fallback (built and tried for real, 4 Nov 2026):** `openai/gpt-oss-120b`, paced under the plan's limit: held-out 30/31, about 1 s a call, the 8 Detective paragraphs all rewritten and passing the check. A burst over the plan's 8,000 tokens a minute is refused: those questions come back unclear, and a test run in a burst scored 25/31 for that reason alone. Before a customer ships: their own key, on a paid plan; the key given in the session should be replaced.

## Engine pass, 2 Nov 2026 (built; the Engine session does no UI work: `docs/UI-WORK-FROM-ENGINE.md` is the UI's list)

- Flow steps all real, flow names, hourly / run-only flows and Run, several sources merged, carrying on from a flow, files copied,
  old steps retired; disk and network rules and a week's backtest; the Worker writes back; the spine's bounded catch-up queue;
  Detective's O(k log k) coverage; licence codes (a machine joins with one at setup, nobody confirms); files in conversations (#7);
  Private (#3) with Windows' own permissions; the update pipeline; a deleted source file's copies kept with an issue to remove them.
- **Not run for real yet:** a second Windows user refused a Private file, a machine updating itself, the two installers (the VM plan).

## Older decisions (all settled since)

- Version 1 is IT Admins; what stood in for the Super User is `require_head` and any Admin. `who-runs-the-console.md` questions 3 to 5 are settled by `docs/design/v1-it-admin.md`: two Admins on one machine are refused, nobody owns an issue, departments are labels. Network discovery is dropped.

## Version 1 settled, 1 Nov 2026 (`docs/design/v1-it-admin.md`)

- Super User parked out of everything that ships; IT Admins only; departments are labels Admins create; Admin to Admin refused on a machine;
  issues by Take; only Admin-to-Admin flows need consent; single-file flows followed at both ends. The plan is ENGINE-GAPS #18.
- **Steps 1-3 built (1 Nov 2026):** Admins over every department (`FALCON_ADMIN_SCOPE`), the first IT Admin at setup, Admin-to-Admin
  consent with the destination naming the folder, single-file flows. Next: park the Super User, then the console.
- **Settled:** An Admin leaving is known by another Admin offboarding the account (the machine stays and says nothing); what the account still owns (restrictions, flows, rules, actions, tasks to verify, issues) is handed to another Admin with a tool, not a page: TUI `account owns <id>` and `account handover <from> <to>` (`hierarchy.ownership`, `hierarchy.hand_over`; decided 1 Nov 2026).

## Engine pass, 1 Nov 2026 (ENGINE-GAPS 8, 9, 10, 11, 12, 13, 14, 16, 17)

- **Built:** one task per description; the machine page facts (busiest programs, about, keyboard quarters, check-ins; the Worker's protected list);
  PCs that knocked; a flow's last sync as a diff; the Restricted page (how a copy got there, allowed, lately, flows allowed); Coming up; custom action
  output kinds, per-machine results, stopping a run, a test run before saving; Detective weighing what was carried, and At a glance; an Admin's
  to-dos; an Admin's conversations. Migrations 041-045. Each has a TUI command; none of it is drawn in the QML yet.
- **What was waiting on the user here is all answered** (see Answered, above).
- **Noticed:** fixed since: `devops_at_night` (`_coverage`) and the Worker's conversations.

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
- **Not mine, and removed from the list:** the Admin console needs no blocked bar; the overlay on the Admin's PC does it (the Admin installer puts the Worker pieces there).

## Flow, Restricted, Task tried live (14 Oct 2026)

- Fixed along the way (see `ENGINE-GAPS.md`): big files, a destination that was away, files already in a source folder, a file mid-write, a marked file being moved, an allowance by path, `index.search`, ghosts in the index.
- **Done since:** the console's own forms are scripted live (`live_drill.py forms`, 18 checks) and the default Qwen3-1.7B model is downloaded and probed 8/8. **Still only on separate machines:** a flow between two real PCs (`docs/VM-TEST-PLAN.md`).

## Proactive and reactive (16 Oct 2026)

- Built: the index reconciles on start, reconnect and a timer; the Engine heals flows, marks and tasks on timers; a flow never overwrites what it did not write. See `ENGINE-GAPS.md`.
- The two-PC Flow test, the away-and-back tests and the non-administrator console test are in `docs/VM-TEST-PLAN.md` (needs a machine with ~14 GB free for the guests).
- A deleted source file is now a choice per flow (see below).

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
- **Console, later the same day:** Detective page rebuilt on the standard list-and-item layout (equal heights, evidence in paired panels, suggestions and written rules always shown side by side); the Super User's Overview is now the four core features as a 2 x 2 with what waits on them above and a slim organisation line below; Home and Core are one Core group of six; `scripts/preview.py` has real Detective cases (played through the matcher), suggestions, rules and a flow waiting for consent; the concept (claude.ai/artifact/R2NT8v3996VDFYiS3XM4JL, version 186) has the Detective page, the new Overview and the restricted-flow consent. Not yet in the concept: the machine-asks-to-take-over card, the mark assessment card.
- **Pruned (docs/design/pruning.md):** the console lost the Accountability, Rules, Reports, Access, Sessions and Rollout pages, listeners and the cross-department hand-off; Registry is a tab of Departments and Actions a tab of Automation (Admin 10 pages, Super User 8). Their Engine handlers and tests are untouched until the core / full split decides them (rules, deviations, reports routing, updates gate). **Assisted access, listeners and the report kinds Listener report / Help across departments / Folder conflict are gone from the Engine too (19 Oct); every report kind but "About an Admin" now routes to each department by default (migration 040).**
- The bounded queue and the tell stage are built (2 Nov 2026); file opens need the elevated service, and were confirmed delivered here on 4 Nov 2026.
