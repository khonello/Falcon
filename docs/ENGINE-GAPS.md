# Engine work found while building the UI

The GUI rebuild (step 3 onwards) keeps UI and Engine work apart: whatever a page needs from the Engine or
the Worker Client that is not there is written here and fixed in one pass later. Mundane, simple fixes are
done inline and are not listed. Each entry: what is missing, why it matters, where it was found.

**How the Worker reaches the OS** (decided 9 Oct 2026). Nobody using a machine needs to be a Windows administrator;
Falcon's Admin is its own role. The Worker Client runs as a Windows service under the system account, installed once
with admin rights (Phase 9 packaging, as any management agent), and does the OS-level work from there: kernel event
tracing (ETW) for file opens and process starts, process and USB and network state, no Windows audit policy to switch
on by hand. Windows keeps services out of the signed-in person's desktop (session 0), so whatever must draw on their
screen or capture it -- the lock overlay, messages, screenshots -- runs as the Worker's helper windows, started by the
service inside that person's session.

**Packaging and installation are on hold** (the user, 10 Oct 2026): nothing here starts them until the project is given
a clear green flag (PHASES.md, Phase 9). Where an item below mentions the service, the session or an installer, that
part is recorded for later, not built.

## Open

1. **OS signals from the Worker: native for drives, sign-ins and the network; programs still compared** (9-10 Oct
   2026). Built and tested: the Engine tells a machine which signals its automations wait for
   (`control.signal_interest`, and `control.interest_changed` when one is created, changed or disabled);
   `worker_client/ossignals.py` watches only those and relays them through `control.signal`:
   `usb.inserted/removed`, `network.connected/disconnected`, `program.launched/exited` (a program match is applied on
   the Worker) and `user.login/logout`. Each signal is the difference between two looks; the first is a baseline.
   **Native:** `worker_client/winnotify.py` (ctypes) is a hidden message window that Windows tells when a drive or
   volume arrives or leaves and when anyone signs in, out or locks, plus `NotifyIpInterfaceChange` for the network;
   each only nudges the watcher to look at once, so a missed notification costs one safety-net look (30 s) and never a
   wrong signal. **Instant programs (done 12 Oct 2026):** `worker_client/etw.py` starts a real-time ETW session on
   Microsoft-Windows-Kernel-Process only while an automation waits for `program.launched` / `program.exited`, so every
   start and stop is seen the moment Windows creates or ends the process, including one that lives under 3 s; the
   3-second comparison stays as the fallback and is skipped while the trace is live (nothing is said twice). Windows lets
   only an elevated process, or a member of "Performance Log Users", start a trace: the Worker service (system account)
   can; run as an ordinary user it says so once and keeps the fallback. `python scripts/etw_check.py` shows it working
   from an elevated prompt. *Found:* Automation (AU08), 27 Sep 2026.
2. **A file being opened (done 12 Oct 2026)** (the Engine half was done earlier: `file.accessed` is relayable and part of
   the interest list). The Worker now produces it, as decided (the user, 9 Oct 2026): from Windows' own kernel file events
   (`Microsoft-Windows-Kernel-File`, create events), no audit policy switched on by hand, in the Worker service (system
   account). `worker_client/etw.py` filters inside the trace callback by the paths and suffixes automations named, so
   the flood of every open on the machine never leaves the Worker; folders, Falcon's own opens and the several creates
   of one open are dropped; a rule that names only a resource tier cannot be decided on the Worker and is not watched
   live (it says so in the log). The kernel's `\Device\HarddiskVolumeN` paths are turned into drive letters.
   Without the privilege to trace it stays unavailable (the log says why). *Found:* Automation (AU08).
## Done inline (for the record)

- **Registering machines by asking** (was #15, done 10 Oct 2026). A new Worker runs `python -m worker_client --engine
  host:port --ca engine.crt --enroll [--department ID] [--level worker|admin]`: it asks (`enroll.request`, one of only
  two requests accepted before the handshake, the other being `enroll.wait`), shows a four-digit code on its own screen
  (console and a Worker window), and waits. Nothing registers itself: the request waits in `enrollments` (migration
  019) and the Super User sees all of them, an Admin the ones for their department (`enroll.list`, with no code in it).
  Whoever confirms types the code (`enroll.confirm {enrollment_id, code, department_id?, level?}`); an Admin confirms
  only Workers in their own department, an Admin workstation needs the Super User; five wrong codes refuse it; it can
  be refused (`enroll.refuse`) and expires after 24 h. The account and PC are made by the same `provision()` as
  `hierarchy.account_create`. The machine is nudged (`enroll.decided`) and collects its client id and key with its
  token, once, ever (`collected` afterwards -- an Admin rekeys); they are written into its config and it carries on as a
  Worker. The confirmer never receives the key. Asks are rate-limited to five waiting per address and 100 in all, and
  audited (`enroll.requested/confirmed/refused/collected`). TUI: `enroll`, `enroll confirm <id> <code>`, `enroll
  refuse <id>`. The typed-name registration still works as the fallback. Not built (the console, not the Engine):
  the "Waiting to be registered" list on the department page and Must see. The Worker finds the Engine from the install
  package's address (`--engine`); a LAN broadcast to find it without one is not built. *Test:* `tests/test_enrollment.py`,
  `test_worker_client.py::test_a_new_worker_registers_itself_by_asking_and_then_runs`,
  `test_operator_client.py::test_scripted_enrollment`.

- **Everything the OS reports about files, recorded and used** (follow-up to #9, done 10 Oct 2026; the user: the OS emits
  move, rename and more, so cover what it emits rather than being narrow). *The gap that was there:* the Worker already
  sent a move with `old_path`, but the Engine used only the new path -- a move looked like a new file, the old place
  stayed in the index as if the file were still there, and a delete left no mark. *Now:* the Engine uses `old_path`,
  marks a place a file has left as `gone_at` (row kept) and keeps an append-only `file_events` history (migration 020) of
  create, move/rename, copy, delete, edit (once per ten minutes per file), **attribute changes** (read-only, hidden) and
  **permission/owner changes**, for files and for **folders** (created, moved/renamed, deleted; never index rows). The
  Worker's watcher (`worker_client/watcher.py`, `fsmeta.py`) tells a content edit from an attribute flip or a
  permission change by comparing two looks of the file (size and last write; attribute flags; a hash of owner, group
  and access list read with `GetFileSecurityW`), reports folder events, and in the polling fallback tells a move from a
  delete plus a create by the file's own identity (verified on this machine: read-only flag -> `attrib`, edit ->
  `modify`, an ACL change -> `security`, real renames/moves/folder events through the native watcher). The journey now
  shows renamed, moved, edited, attributes changed, permissions changed and deleted. Automations can wait on the new
  signals: `file.attributes_changed`, `file.permissions_changed`, `folder.created`, `folder.moved`, `folder.deleted`
  (a move's signal carries `old_path`). Flow, Resource and Task still hear only content changes. A place a file has
  left no longer counts as a collision, a copy elsewhere, a search hit or a folder entry. *Still open:* a file being
  *opened* (#2: the kernel trace, blocked); a folder renamed above a file is now followed into that file's journey (12 Oct 2026: the journey says "Its folder was renamed/moved" and does not count the same file under the new folder as a copy); the
  polling fallback sees no folders or permissions; `file_events` has no retention job yet. *Test:*
  `test_worker_client.py` (real filesystem: native and polling), `test_resource_assistance.py` (journey, automations).
- **A file's journey** (was #9, done 10 Oct 2026; the user decided: the journey only, not "required on every machine").
  `resource.journey {file_index_id}` follows a file by its CONTENT (the hash), because a copy has another path and
  sits on another machine, and returns its places and a timeline, oldest first: `first_seen` and `copied` (each place
  the same content was indexed, by when it first appeared there -- the index now keeps `first_seen_at`, migration
  018), `tagged` (audit, with who), `flagged` and `owner_told` (a Restricted File Tracking violation, and the person
  told), `resolved` (audit, with who) and `synced` / `conflict` (the flow sync log: a flow carried it to a machine, or an
  outside edit was in the way). Each event has a plain sentence. The Super User sees everything; an Admin only what
  happened on their own department's machines (a file with no place in it is "not found" to them); names are the
  caller's. Workers may not ask. TUI: `journey <file_index_id>`. Not covered: a rename or move is not a recorded event
  (a moved file is a new place with the same content). *Test:* `test_resource_assistance.py::test_a_files_journey_follows_its_content_and_stays_in_scope`,
  `test_operator_client.py::test_scripted_file_journey`.

- **Department tasks** (was #16, done 10 Oct 2026). A different thing from an Admin's task to a Worker (which keeps its
  checks; the old `task.propose`/`task.create` now refuse a Super User and point here). `task.dept_create
  {department_id, title, deadline_at, admin_ids?}` tells every Admin in the department, or only the ones picked
  (a department with no Admin is refused); `task.dept_mark {task_id, state: seen|ongoing|done}` is an Admin's own row
  only; the task *stands at* the furthest any Admin has got; `task.dept_complete` and `task.dept_reopen {note}` are the
  Super User who gave it only (reopen sends everyone who had finished back to ongoing, and every Admin on it gets the
  note); `task.dept_list` (the Super User: all; an Admin: the ones they were told, their own row only, and `unseen`
  for the strip across every page until they mark it seen) and `task.dept_get`. Pushes: `task.dept_assigned`,
  `task.dept_updated` (to the Super User), `task.dept_completed`, `task.dept_reopened`, `task.dept_deadline`. The one
  deadline is armed on create and on Engine start, and fires the `task.deadline_final` event (data `dept_task_id`).
  Tables `department_tasks`, `department_task_admins`, `department_task_notes` (migration 017). TUI: `dtask give|mark|
  complete|reopen`, `dtasks`, `dtask <id>`. *Test:* `test_task.py::test_a_department_task_is_not_an_admins_task`,
  `test_operator_client.py::test_scripted_department_task`.

- **A file action finds its file on each machine** (was #6, done 10 Oct 2026). `rename_file`, `restore_file` and
  `snapshot_file` name their file one of three ways: `path` (the same path on every machine, as before),
  `find_name` (a file name) or `find_hash` (a content hash); exactly one. For the last two the Engine looks the file up
  in the file index for each machine the action runs on and sends that machine its own path
  (`executions.locate_file`). A machine with no copy, or with several, is not guessed at: the run is recorded as failed
  with "the file is not on this machine" or "2 copies on this machine; name the path", audited as `action.not_run`, and
  nothing is sent. `control.file_locations {find_name|find_hash, pc_ids?}` previews it before anything runs: per
  machine found / missing / several, with the paths. TUI: `where <name> | hash=..`, and
  `action add control rename_file find_name=.. new_name=..`. (A department run includes the Admin's own workstation, as
  every department run does.) *Test:* `test_control_updates.py::test_a_file_action_uses_each_machines_own_path`.

- **Programs are picked, not typed** (was #5, done 10 Oct 2026). The Worker reports what runs (the process table
  grouped by program: name, how many, memory; every minute) and what is installed (Windows' own lists, read from the
  registry -- the Uninstall keys and App Paths -- with the program to start where it is known; on connect and every
  six hours): `control.inventory`. `control.programs {pc_ids?}` gives a console both, one row per program with how
  many machines it is on ("open on 5 machines"), most widespread first, scoped to the caller's department (the Super
  User: every machine); with one machine named it is exactly what is installed there. Installed programs are kept
  in `pc_programs` (migration 016); what runs is in memory and refilled within a minute after a restart. TUI:
  `programs [pcs=..]`. On this machine: 141 running programs, 96 installed (57 with a path to start).
  *Test:* `test_control_updates.py`, `test_worker_client.py`.

- **Actions that act on the person's screen, and a way to ask for help** (was #4 and #14, done 10 Oct 2026).
  `notify` takes `message` and `stay_s` (0 or absent: stays until the person closes it); `lock_session` takes
  `duration_s` and an optional `message` (the "Locked by your Admin" window for that long, then the screen is
  released); `reboot`/`shutdown` take `delay_s` (0-3600; the console offers 60 or 300) and a `message` beside the
  warning. The Engine checks the settings (`control.action_create/update`) and raises the run's timeout to the
  action's own length plus 30 s, so a lock is never cut short. The Worker runs them through the same detached
  path (`worker_client/builtins.py`), opening the message and locked windows, and says in the run's summary what
  happened ("closed by the person", "taken down after 20 s", "locked for 15 min"). Without PySide6 or with
  windows off, notify says "not shown" and a lock falls back to locking the workstation once. *Ask for help:* a
  tray icon (`worker_client/windows/tray.py`, started by the service) prints `ask` when clicked; the service
  asks `assistance.my_admins` (new: a Worker's department Admins, an Admin's Super User), opens the ask window
  (one button per Admin -- a ping carries no message, so there is no text box any more) and sends
  `assistance.ping`. TUI: `action add control notify message=.. stay_s=..`, `lock_session duration_s=..`,
  `reboot delay_s=..`; `actions` lists the optional settings. **A lock also blocks the keyboard and mouse at the OS level** (`BlockInput`) while its
  window holds; Windows ends the block if the process dies and Ctrl+Alt+Del always overrides it. Still for Phase 9: under the Windows service these
  windows and the tray must be started inside the person's session (a service has no desktop).
  *Test:* `test_control_updates.py`, `test_worker_client.py`, `test_resource_assistance.py`.

- **A machine's live state** (was #12, done 9 Oct 2026). Online means the machine's client holds an authenticated
  connection now (`Engine.online_pc_ids()`); `pcs.last_seen_at` (migration 015) records when it connected or dropped,
  and consoles get `pc.presence {pc_id, online}`. `hierarchy.traverse` refuses a machine that is not connected
  (`unavailable`, "FIN-02 is not reachable (last seen ...)"; `FALCON_REFUSE_UNREACHABLE=0` turns it off).
  `hierarchy.tree` rows carry `online` and `last_seen_at`; `hierarchy.pc_state {pc_id}` gives reachable, last seen,
  the latest levels and **what is in front**: the Worker now adds `foreground {program, title}` to `control.metrics`
  (`worker_client/foreground.py`, ctypes; under the Windows service this moves into the person's-session helper).
  TUI: `tree` shows online/offline, `pc state <pc_id>`.
  *Test:* `test_hierarchy.py::test_a_machine_that_is_not_connected_cannot_be_entered_and_says_since_when`.
- **What an action returned, kept with the run** (was #20, done 9 Oct 2026). A script (built-in or Custom) marks
  what it returns with lines the Worker strips from the text: `FALCON:summary <line>`, `FALCON:result <json>`,
  `FALCON:image <path>`. `control.execution_result` now stores the text (first and last 64 KB), the summary (on
  `action_executions.summary`, so every list has it) and the rows (`execution_outputs`, migration 014); the built-in
  monitoring actions return rows and a summary ("321 running · EXCEL.EXE uses the most memory"). Screenshots: the old
  PowerShell capture was blocked by Windows Defender as malicious, so `worker_client/screenshot.py` captures with GDI
  through ctypes, scales to 1600 px wide and fits 2 MB as PNG (stdlib only); the Worker sends it as
  `control.execution_image` before the result. `control.execution` returns output, result, `has_image`, `expired`;
  `control.execution_image_get` returns the picture (the run's department's Admins and the Super User, every view
  audited). After 90 days the audit retention job clears text, rows and picture (rows stay). TUI: `exec <id>`,
  `exec picture <id> <file>`. Still to do with packaging: under the Windows service the capture must run in the
  person's session as a helper. *Test:* `test_control_updates.py`, `test_worker_client.py` (executor).
- **A typical day for each level** (was #3, done 9 Oct 2026). `control.metrics` now also stores one sample per machine
  every 10 minutes in `metric_samples` (migration 013, never deleted); `control.levels` adds `typical`: the rolling
  7-day p10-p90 of processor, memory and idle across the same machines, with the sample count and since when (null
  until a sample exists). The min-max of now stays. TUI: `levels`.
  *Test:* `test_control_updates.py` (levels: a second report inside the interval is not stored).
- **A report keeps its words and each reader's "seen"** (was #7, done 9 Oct 2026). `reports.summary` holds the
  sentence `emit()` was given (migration 012); `reports.list` returns it with `seen_at` (this reader's first open,
  theirs alone) and `addressed_at`. `reports.seen {report_ids}` marks reports the reader can see; the first open is
  kept. Reports written before 012 have an empty summary. TUI: `report seen <ids>`.
  *Test:* `test_hierarchy.py::test_a_report_keeps_its_words_and_each_reader_sees_it_alone`.
- **Listeners from any department** (was #8, done 9 Oct 2026). `assistance.listener_candidates {channel_id}` lists
  every active Admin in every department, less the channel's two parties and those the caller already added, named
  as the caller names them; only a party may ask. TUI: `listen who <channel_id>`.
  *Test:* `test_resource_assistance.py` (HR's Admin offered to a Finance worker).
- **A task's checks in `task.list`** (was #11, done 9 Oct 2026). Every task row carries `checks_total` and
  `checks_passed`, so a list can say "2 of 3 checks passed" without a `task.get` per task; the TUI's `tasks` shows
  them as a `checks` column. *Test:* `test_task.py` (the list carries 0 of 2 after create).
- **An Admin belongs to one department** (was #13, closed 9 Oct 2026, the user's decision). Kept: assigning an Admin
  to a department without one means a new Admin account, or promoting one of its workers. The concept's "an Admin
  from another department, as well" option is removed.
- **The Super User watching every channel** (was #10, closed 9 Oct 2026, the user's decision). Not built: a channel
  is between two people, and a third party reads it only as a Listener added by a party (an Admin). The Super User's
  Messages page shows their own conversations with Admins.
- **A report category about an Admin, never routed; update escalations routed by default** (was #17, done 9 Oct
  2026). `about_admin` is a fixed category: `reports.routing_set` refuses it (FORBIDDEN) and `reports.routing_get`
  lists it under `fixed`. An Admin entering a machine outside working hours (`FALCON_WORKING_HOURS`, default
  06:00-18:00, the Engine host's local time; a span may cross midnight) raises one, to the Super User only. New
  departments start with `update_status` routed to them, and migration 011 gives existing departments the same
  default. *Test:* `test_about_admin_reports_reach_the_super_user_only_and_updates_route_by_default`.
- **Routing a kind of report, with or without what came before** (was #18, done 9 Oct 2026). A routed department used
  to see every report of the category, however old: visibility is read-time. `report_routing_config` gains
  `includes_earlier` (migration 010); `reports.routing_set` takes `include_earlier` (default true, the old
  behaviour) for the departments it adds, keeps the rows of departments already routed (so when each was routed and
  what it sees survive later edits), and answers `added`, `removed` and `earlier_unaddressed`. An empty list sends
  the category back to the Super User only; a removed department stops seeing it, and what it addressed stays in the
  Super User's View. Audited with all of it. TUI: `routing set <category> [ids] [earlier=no]`.
  *Test:* `test_routing_a_department_with_or_without_earlier_reports`.
- **A Super User automation seen from a department** (was #19, done 9 Oct 2026). An Admin could not see the Super
  User's organisation-wide automations at all. Now `control.event_list` and `control.dashboard` include those that
  reach the department (no machines named, or one of its machines named), marked `org_wide` / `read_only`;
  `control.event_update` and `control.event_delete` refuse them (FORBIDDEN); `control.event_history` counts runs on the
  department's machines only and says how many machines each firing reached (`machines`). Two more found on the way:
  the dashboard sent an Admin every running action in the organisation (now the department's only), and a Super
  User's timed automation with no machines named ran on none (it now runs on every department's machines).
  *Test:* `test_a_super_user_automation_is_seen_from_a_department_by_its_own_machines`.

- `control.event_history`, `control.levels`, `match.tier`, and time events firing on machine 0 (Automation).
- `flow.list` shapes and hostnames, `index.folders` (Flows).
- `resource.shelves`: files per tier across the department (Resources).
- `auth.respond` says a hostname mismatch back to the client; `hierarchy.session_state` says how long an Extend adds.

- **The session window under the Windows service** (12 Oct 2026, WP9). `worker_client/screenstream.py` captures the screen and applies input from the Worker process itself, which is right while the
  Worker runs in the person's session. As a Windows service (packaging, on hold) it runs in session 0, whose desktop is empty, so capture and input move into the person's-session helper like the
  `screenshot` built-in and the foreground reading: the Engine side (`session.screen`, `session.frame`, `session.input`) does not change.

- **Waiting on the user** (12 Oct 2026). (1) `file_events` has no retention job: the invariant is that the 90-day `audit_log` purge is the only hard delete, so purging this second history needs a decision. (2) A file being
  *opened* (kernel trace) and program starts caught at once were refused by the safety classifier and not retried; the 3-second look (and the native hooks that exist) stays.

- **The Worker as a service reaches the person's desktop by itself** (12 Oct 2026). `worker_client/winsession.py` starts a program on the signed-in person's desktop from the service
  (`WTSGetActiveConsoleSessionId`, `WTSQueryUserToken`, `CreateProcessAsUserW`, desktop `winsta0\default`, stdin/stdout pipes): the Worker's windows and tray, the desktop built-ins
  (`screenshot`, `notify`, `lock_session`, `start_process`, through `worker_client.runlogged`, which writes their output to the log the service reads) and a small helper
  (`worker_client/helper.py`, `userhelper.py`) that captures the screen and applies the console's input for the session window. Run as an ordinary user, none of it is used and a refusal
  never crashes anything. Nothing about the desktop needs setting up by hand. *Not exercised here:* the service-account path itself (this machine has no service installed; packaging is on hold).

- **File-event retention and the firewall** (13 Oct 2026). `file_events` now ages out on the audit trail's clock (`FALCON_AUDIT_RETENTION_DAYS`, 90): a file's journey reaches back as far as the trail does, and the one
  setting governs both; the "only hard delete" invariant in CLAUDE.md names both purges. `python -m engine setup` opens the Engine's port in a running `ufw` or `firewalld` on Linux (as root, else it prints the
  command); other firewalls are left alone and it says so; on a non-Linux machine it only says the Engine is meant for Linux. *Test:* `test_console_rollout.py`, `test_setup_firewall.py`.

- **The Worker as a Windows service: the necessary part of packaging, built and tested** (13 Oct 2026; the final packaging stays on hold). `python -m worker_client service install` (once, from an elevated prompt) registers the
  Worker as a service that starts with Windows, runs as the system account and restarts itself if it stops; `uninstall`, `start`, `stop`, `status` do the rest. `worker_client/winservice.py` speaks the service-control
  protocol through ctypes, so nothing extra is bundled; settings are the Worker's usual file (`%PROGRAMDATA%\Falcon\worker.json`), the log `%PROGRAMDATA%\Falcon\worker.log`. *Tested for real on this machine*
  (`test_worker_client.py`, elevated prompt only, each removing what it installed): a probe service reported that it runs as the system account in session 0, may trace programs and file opens, and started a program on the
  signed-in person's desktop; and the real Worker, installed as a service against a throwaway Engine, connected as FIN-01, appeared online with its version, OS and address, and went offline when stopped.
  *Not yet done (final packaging):* a bundled interpreter and installer, signing, the helper windows frozen as executables, and a pinned Engine certificate and key delivered with the install.

- **Flows: what the concept's Flows pages show that the Engine and Worker cannot do yet** (13 Oct 2026, found putting the concept's flow
  graph side by side with the QML). The console now keeps each step's name in its stage `config` as `op` (plus `by: "extension"` for
  Sort by file type, which the Worker already reads) and reads a flow's steps from the `parent_stage_id` tree: this is the smallest
  shape that lets a step come back as it was picked. The full `config` shape is still a deferred decision (spec §10), so it is for
  the user to confirm. Open: (1) **the Worker carries out only Sort by file type.** Rename by date, Convert to PDF, Compress to ZIP and
  Sort by month are kept and drawn, but they leave the files as they are (`worker_client/flowsync.py` converts only txt/md/csv).
  (2) **An edit leaves the old stages on record.** `FlowsRepo.replace_structure` adds new `flow_stages` rows and keeps the old ones,
  and `flow.list` returns them all. The console counts only stages a live destination reaches, but the Engine should mark the old
  ones retired or leave them out of `shapes`. (3) **Not in the Engine, drawn disabled with the reason:** a flow's own name (flows are named
  `<source folder>-<id>`), several sources merging into one flow, carrying on from another flow, asking the Super User or another
  Admin to pick a folder on their own workstation, copying on a schedule or only when run, and the files-copied count per flow (the
  concept's "Files copied" column and figure; the console shows branches and the last copy instead). (4) A destination in remote
  storage (no machine) cannot be picked in the builder, so editing such a flow shows it as unset.

- **The console against the concept, page by page: what the Engine cannot back yet** (13 Oct 2026, found auditing every page at both
  levels against the published concept). Each is drawn disabled with the reason, or left out where the concept only decorates; nothing is faked.
  (1) **Rules:** a threshold on *disk* or *network* (only `threshold.cpu` / `threshold.memory` exist; the reading picker lists them disabled).
  (2) **Actions:** *Test on one machine* for a script not saved yet: `control.action_run` takes a saved action id, so an unsaved draft cannot
  be tried; the button is disabled on New action. (3) **Tasks:** changing a department task after it is sent (Edit is disabled on the
  Super User's given tasks). (4) **Reports:** *Prompt the department* (the Super User nudging a department's Admins about a report they
  have not handled). (5) **History behind the headline figures:** the concept's small trends under the overview figures need a few days of
  each figure (KPI histories); the overviews show today's figure without a trend. Likewise a week of sessions and assisted access per
  department for the Departments page's day view beyond today. (6) **Flows** — see the entry above (names, files copied per flow,
  several sources, carrying on from another flow, asking someone to pick a folder, schedules).

- **The indexer and the event tracker run as their own supervised programs** (13 Oct 2026; decided in `docs/PACKAGING-PLAN.md`). `worker_client/indexer.py` (the
  file watcher and idle sweep, below-normal priority) and `worker_client/tracker.py` (the kernel trace and Windows notifications) are started by the service
  (`childproc.Supervised`), restarted when they die (1, 2, 5, 10, 30 seconds, back to the start after a minute of steadiness) and called unhealthy after five
  deaths in five minutes. They hold no Engine connection: what they report goes to the service over stdin/stdout and out through its one connection. Always so as
  a Windows service; `--separate` (or `separate_programs` in the settings) elsewhere; off for tests that drive the pieces directly. An unhealthy part is told to the
  Engine (`control.component_status`, migration 030) and is an issue on that machine ("Part of the Worker"), closed when it is steady again. *Tested:*
  `tests/test_children.py` (real child processes: killed and restarted, still reporting; a program that cannot start becomes unhealthy; the issue raised and
  closed), and for real as an installed service (elevated prompt): both parts run under it, a killed tracker comes back, a file the indexer saw reaches the
  Engine, and both go when the service stops. *Not done:* the UI helper is still started by the service on demand as before (already its own program).

- **The Worker's overlays and the keyboard, tried for real** (13 Oct 2026). With the windows installed (`PySide6-Essentials` is all the Worker's windows need; the `worker-ui` extra
  now asks for that, ~170 MB lighter than all of PySide6), entering a machine in *see* mode puts "<name> is viewing your screen" at the top of the person's desktop, and
  in *control* mode a card "<name> is using this machine · you can use it again when they leave, about 30 minutes" over it; both go when the session ends (picture taken from the
  desktop itself). The keyboard path was checked with `scripts/keyboard_check.py`: the Worker's input code typed text (including é and 中), Shift+A, ordinary keys and
  Backspace into a real window. Mouse control had been tried through the console. *Still only by a second machine:* the console's own key presses arriving through the session
  window (on one PC the viewer is its own target).

- **The installers' code, written and tested** (13 Oct 2026; compiling it into executables stays on hold). `installers/`: `roles.py` (what each installer carries), `payload.py`
  (a role's packages, the libraries read from `pyproject.toml`, a manifest of hashes; refuses any secret, test or cache), `bundle.py` (the Engine's address and certificate,
  no key, with its fingerprint), `engine/install.py` (Linux: user, folders, runtime, a PostgreSQL role with a made password, settings, `engine setup`, ownership, the bundle,
  a hardened systemd unit; plus `debian/` and `build_deb.sh`), `windows/install.py` (worker, admin, superuser: code, runtime, the public and the private folders with real ACLs,
  the service, the console shortcut, the Super User's own settings, a receipt, uninstall that keeps the key) and `windows/falcon.iss` (the wrapper for the later `setup.exe`).
  See `installers/README.md`. Machines register by probation, as decided: a service installed with no key asks, shows the code in the person's session (again if nobody was
  there), and keeps the key it is handed in the closed folder. An Admin's console holds no key: the service answers the Engine's challenge for it over a named pipe
  (`common/signpipe.py`). *Tested:* `tests/test_installers.py` (including, from an elevated prompt, an Admin workstation installed as a service that registers itself and
  whose keyless console signs in), `test_signpipe.py`, `test_enrollment.py`. *Run for real:* the Engine's installer on Linux (WSL), twice, with a Windows client connecting over the bundle's pinned certificate; the second run changed nothing. *Not run for real:* the Windows runtime venv with real wheels
  and the `.deb` build (the VMs); a non-administrator Windows user opening the pipe (the VM). *Still open:* a bundled interpreter, frozen helper windows, signing, the update pipeline, and whether
  the Super User's PC is also a managed machine.

- **Flow, Restricted and Task tried live, and what that found** (14 Oct 2026). `python scripts/live_drill.py flow|restricted|task|gui` runs real Worker processes on this PC against a running
  Engine and says PASS or FAIL per behaviour (28, 26, 26 and 36 checks; all pass now). It found and fixed: **Flow** -- a file over ~3 MB never arrived (one message longer than a
  connection reads; now chunks both ways, `CHUNK_BYTES`), a destination that was away lost what it missed with no status (now paused as `destination:unreachable`, resumed when it
  returns, and caught up: `flow.list` / `flow.listing`, `flow_sync_log.source_hash`, migration 031), a flow made over files already in the source folder or resumed after a pause sent
  nothing of what was missed (same catch-up), a file being written was read at every event (now once, `FALCON_FLOW_SETTLE_SECONDS`), unfinished transfers lived forever (failed after ten
  minutes); **Restricted** -- renaming or moving the marked original raised a copy issue against itself (the mark now follows a move: a move event, or a delete and a create of the same
  content within ten seconds; a folder move takes its marks along), an allowance matched by path alone so other restricted content saved there went unreported (now that content on that
  machine); **Task** -- `index.search` (the Task page's find-an-existing-file) failed on timestamps; **the index** -- files deleted while a Worker was away stayed "present" and
  caused false collisions, so a complete idle sweep now marks what it did not see as gone (`index.sweep_done`). *Open, decided by the user:* a file deleted at the source is not deleted
  at the destinations (the design says "updated to match source"); the index of a machine learns of offline deletions only at its next complete idle sweep; the console's forms
  (New flow, New task, Mark files) are tested against faked answers, and every page loads clean against the live Engine, but filling a form through the real console is not scripted;
  Task proposals were tried with the 0.6B model (the default 1.7B is not on this machine).

- **Proactive first, reactive second: the core heals itself** (16 Oct 2026, the user's rule). Events are the fast path; they are never the only path.
  *The index:* each Worker keeps what the Engine was last told (`worker_client/snapshot.py`, sqlite beside its settings) and `Watcher.reconcile()` compares its
  folders with it on connect, on a timer (`reconcile_seconds`) and after a failed report, sending exactly what appeared, changed or went as `index.catchup` events the
  Engine ingests as if they had happened live -- so Flow, Restricted and Task react to what happened while the machine was off or the Engine unreachable. The first look is a
  full baseline. A file is recorded only after the Engine took the report. *The Engine looks again by itself:* `flow.heal` (every running flow is caught up, 20 min),
  `marks.heal` (every marked content against everything the index holds, 30 min), `tasks.heal` (a file a task asked for that is already there is bound, 10 min), on top of
  the catch-up on create, resume, return and consent. *Collisions:* a flow never overwrites a file it did not write: the Engine tells the destination what the flow last
  wrote there (`previous`) and the Worker keeps anything else beside the new file as `<name>-modified` and says so (`flow.conflict`); a source file deleted and brought back
  finds its destination copy still there (deletes are not propagated) and no collision. *Also found and fixed on the way:* a stop that never finished (Python 3.10's
  `wait_for` can swallow a cancellation, so `task.cancel()` + `gather` hung the service; `worker_client/stopping.stop_tasks` cancels until it really stops), a modified
  file reported as deleted by the first reconcile, deadlines set in the console failing ("must be ISO 8601": JavaScript's `...Z` is refused by Python 3.10; `engine/isotime.py`),
  and the New flow form turning a collision into an error instead of the question it should be. *Tried live through the real console:* `python scripts/live_drill.py forms`
  (New flow with and without files at the destination, New task read by the 1.7B model, Mark files). The default 1.7B model is on this machine now.
