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

## Open

1. **The Worker Client relays no OS signals.** `control.signal` accepts `usb.inserted/removed`,
   `user.login/logout`, `program.launched/exited`, `network.connected/disconnected`, but `worker_client`
   never sends them. Automations on those triggers save and can never fire. Native detection first, a
   polling fallback second (psutil: removable partitions, `users()`, process-table diff, `net_if_stats`).
   *Found:* Automation (AU08), 27 Sep 2026.
2. **A file being opened cannot be seen.** `file.accessed` exists as an event type but nothing produces it
   (the watcher sees create/modify/move/copy/delete only). The UI no longer offers "is opened"; either
   detect reads (Windows auditing / a minifilter is heavy) or drop the type. *Found:* Automation (AU08).
4. **Built-in actions ignore settings the design asks for** (Actions, AU06). The page offers only what works:
   - `lock_session` locks at once and ignores `duration_s`; no message is shown. The design wants "lock it for
     15 min" with a message (a Worker overlay that holds the lock, then releases it).
   - `notify` only prints `NOTIFY: ...` to the run's output; the design wants a message on their screen that
     stays up "until closed" or for N seconds (the Worker Dialog helper).
   - `reboot` / `shutdown` always warn 30 s; the design lets the Admin pick 1 or 5 min.
5. **Nothing to pick programs from** (Actions, AU06). "Close a program" should be picked from what runs (and
   say "open on 5 machines"), "Start a program" from what is installed on that machine. Today they are typed
   names. Needs a process/installed-programs inventory from the Worker (a `process_list`-style snapshot kept per
   machine).
6. **Rename a file's new name is free text** and `rename_file` runs on every machine the action targets with one
   path; a per-machine path (from `file_index`, by hash or name) would be truer. *Found:* AU06.
9. **Resources: "where it should be" and "a file's journey"** (RS03) have no data. The first needs files marked
   as required on every worker machine and presence per machine (by content hash); the second a per-file history
   (tagged, copied, flagged, owner told) drawn from the audit trail and `file_index` by hash. Both cells are left
   out of the page until then.
14. **The Worker's windows are built; three wait for their triggers** (WR01). `worker_client.windows` has all
    five (blocked, message, locked, ask, task), and the service already opens *blocked* (from the lockout) and
    *task* (on `task.assigned`, with Start). *Message* and *locked* need `notify` / `lock_session` to open them
    instead of printing (item 4), and *ask* needs a way for the person to open it (a tray icon or shortcut) that
    sends `assistance.ping` with the message. Frozen Overlay/Dialog exes are Phase 9 packaging. *Found:* WR01.
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
16. **Department tasks from the Super User have no checks, and can go to several Admins** (the user, 2 Oct 2026).
    Today `task.create` from a Super User needs one Admin account (`engine/task/tasks.py:45`) and carries
    a verification stack like any task. The decision is that a Super User's task is given to a **department**,
    with a **deadline** and **no checks and no expectations**, because such work is rarely a file or a program.
    - **Who is told:** every Admin in the department by default, or only the ones the Super User picks.
    - **What each of them does:** marks it *seen*, *ongoing* or *done*. The task stands at the furthest any of
      them has got.
    - **Who closes it:** only the Super User who gave it calls it complete, or sends it back as ongoing with a
      note that every Admin on it sees.

    Needs:
    - a `department_tasks` row (department, title, deadline, assigner, created, completed) and a
      `department_task_admins` row per Admin told (state, state time). The state time is the record of when it
      was seen.
    - handlers `task.dept_create`, `task.dept_mark {seen|ongoing|done}` (Admin, own row only),
      `task.dept_complete` / `task.dept_reopen` (the assigner only), and `task.dept_list`
    - a push to each Admin told, which the console turns into the strip across every page until they mark it
      seen
    - the soft/final deadline events reused with the one deadline

    Admin → Worker tasks keep their checks. *Raised:* by the user, from the concept's Work page.
## Done inline (for the record)

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
