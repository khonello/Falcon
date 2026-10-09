# Engine work found while building the UI

The GUI rebuild (step 3 onwards) keeps UI and Engine work apart: whatever a page needs from the Engine or
the Worker Client that is not there is written here and fixed in one pass later. Mundane, simple fixes are
done inline and are not listed. Each entry: what is missing, why it matters, where it was found.

## Open

1. **The Worker Client relays no OS signals.** `control.signal` accepts `usb.inserted/removed`,
   `user.login/logout`, `program.launched/exited`, `network.connected/disconnected`, but `worker_client`
   never sends them. Automations on those triggers save and can never fire. Native detection first, a
   polling fallback second (psutil: removable partitions, `users()`, process-table diff, `net_if_stats`).
   *Found:* Automation (AU08), 27 Sep 2026.
2. **A file being opened cannot be seen.** `file.accessed` exists as an event type but nothing produces it
   (the watcher sees create/modify/move/copy/delete only). The UI no longer offers "is opened"; either
   detect reads (Windows auditing / a minifilter is heavy) or drop the type. *Found:* Automation (AU08).
3. **No "normal" level history.** `control.levels` gives the range the machines sit in *now*; the slider's
   band would be truer as a typical day (e.g. a rolling 7-day p10-p90 per metric). *Found:* AU09.
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
7. **A report keeps no words and no "seen".** `reports` stores category + source pointer + time; the summary
   passed to `emit()` is only logged and pushed. The Reports page rebuilds the sentence by reading the source
   (violations, flows) and falls back to a generic line for the rest (listener, cross-department, update,
   deviation). Store the summary (or resolve every source in `reports.list`), and add a per-reader "seen" so the
   board's new / seen / addressed can be told apart. *Found:* Reports (RP03).
8. **A Listener can only be chosen from the Admin's own department.** `hierarchy.tree` for an Admin holds their
   department, so "Add a listener" offers only their fellow Admins; the design's "HR is listening" needs a list
   of active Admins across departments (names by the requester's grants). *Found:* Assistance (AS03).
9. **Resources: "where it should be" and "a file's journey"** (RS03) have no data. The first needs files marked
   as required on every worker machine and presence per machine (by content hash); the second a per-file history
   (tagged, copied, flagged, owner told) drawn from the audit trail and `file_index` by hash. Both cells are left
   out of the page until then.
10. **A Super User cannot watch every channel.** `assistance.channels` returns only channels the caller is a
    party to or listens on; Work's "Help, watched" (WK03) wants every open channel across departments (read-only,
    never taking part), with whose turn it is. The page shows the channels the Super User listens on plus help
    across departments under way (from sessions). *Found:* Work (WK03).
11. **A task's verification state is not in `task.list`.** Work's "Yours" wants "both checks passed · verify"
    on the card; today that needs `task.get` per task. A per-task `checks_passed / checks_total` in the list
    would do. *Found:* WK03.
12. **A client PC's live state is thin** (level 4, CP03). `control.levels` gives processor, memory and idle from the
    Worker's last metrics report (in memory, lost on restart); the design also wants **what is in front** (the
    foreground program and its document) and a machine that is **not reachable** refused at `hierarchy.traverse`
    (the Engine keeps no online state, so a held session on a switched-off machine looks like any other).
    *Found:* level 4.
13. **An Admin belongs to one department.** DG01's "Assign an Admin to Logistics" picks an existing Admin
    ("A. Quaye · Operations · already governs 14 machines"); the schema gives an account one `department_id`, so
    assigning would move them. The page offers "Give it an Admin" (a new Admin account and workstation) until an
    Admin can govern more than one department -- a decision, not only a query. *Found:* dialogs (DG01).
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
17. **A report category about an Admin, which can never be routed** (the user, 2 Oct 2026). An Admin's own
    behaviour, such as entering a machine at 2 a.m., is reported only to the Super User. Routing it to the
    department would have the Admin judge themselves.
    - **Engine:** a fixed category, `about_admin`, whose `reports.routing_set` is refused (`FORBIDDEN`). The
      reports are emitted by the session code when an Admin enters outside working hours.
    - **Default routing for update escalations:** *Update stuck* is routed to every department by default,
      so a failure past the threshold reaches that PC's Admin (§9.5). Today routing starts empty.

    *Raised:* by the user, from the concept's Work page.
## Done inline (for the record)

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
