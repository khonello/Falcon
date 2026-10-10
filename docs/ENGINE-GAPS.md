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
   wrong signal. **Open:** programs are still found by comparing the process table every 3 s, so a program that
   starts and ends inside 3 s is missed; catching every one needs the kernel's process events (same family as #2, and
   the same blocker). *Found:* Automation (AU08), 27 Sep 2026.
2. **A file being opened cannot be seen** (the Engine half is done: `file.accessed` is relayable and part of the
   interest list). What is missing is the Worker producing it. The decision (the user, 9 Oct 2026): from Windows' own
   kernel file events, with no audit policy switched on by hand, in the Worker service (system account). That code is
   not written: both attempts to write it in this session were stopped by a safety classifier, so it needs to be
   written another way (by hand, or in a session where the writing is not blocked). Until then an automation on
   "is opened" saves and never fires. *Found:* Automation (AU08).
9. **Resources: "where it should be" and "a file's journey"** (RS03) have no data. The first needs files marked
   as required on every worker machine and presence per machine (by content hash); the second a per-file history
   (tagged, copied, flagged, owner told) drawn from the audit trail and `file_index` by hash. Both cells are left
   out of the page until then.
15. **Register machines from the local network instead of typing them** (the user's idea, 27 Sep 2026). Today a
    machine is registered by typing its name (`hierarchy.account_create`), and its client id + key are copied onto it
    by hand. The idea: a small installer on each machine stores who it is meant to be (its name, department, level --
    worker / Admin workstation, and anything else registration needs); the Engine finds those machines on the local
    network and registers them. It works, with two changes so a stranger on the network cannot let itself in:

    - **The machine asks; the Engine does not hunt.** Scanning subnets is unreliable across VLANs and needs the Engine to
      reach into every machine. Instead the installed agent (already the Worker Client) finds the Engine -- the address
      from the install package, or a UDP broadcast / mDNS answer on the LAN -- and opens an unauthenticated
      `enroll.request` over TLS (the Engine's certificate is pinned in the package): `{hostname, requested department,
      requested level, os, mac}`. Only `auth.*`, `system.*` and this one request are allowed before the handshake.
    - **What it says about itself is a request, never a grant** (propose, never silently resolve). Requests land in a
      "Waiting to be registered" list -- on the department page for its Admin, and on Must see for the Super User. A
      person confirms each one (department, level, and who uses it), or refuses it. An Admin can only confirm workers
      in their own department; an Admin workstation needs the Super User. Nothing registers itself.
    - **Pairing, so the right machine gets the key.** The agent shows a short code on its own screen (a Worker window,
      "Registering this machine · code 4 7 2 9"); the person confirming types that code. On a match the Engine
      creates the account + PC and sends the client id + key back over the agent's open enrollment connection -- no
      one copies a key by hand, and a machine that is not really in front of someone cannot finish.
    - Engine: `enroll.request` (pre-auth, rate-limited, audited), `enroll.list` / `enroll.confirm {code, department_id,
      role}` / `enroll.refuse`, an `enrollments` table (pending / confirmed / refused / expired after e.g. 24 h), and
      the pre-auth gate in `connection.py`. Worker: an `--enroll` first-run mode that requests, shows the code, waits,
      then writes the key to its config and connects normally. UI: the waiting list replaces "Register a machine"'s
      typed name (the dialog keeps working as the fallback). *Raised:* by the user, after the dialogs (DG01).
## Done inline (for the record)

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
