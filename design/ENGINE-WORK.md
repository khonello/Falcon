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

## Done inline (for the record)

- `control.event_history`, `control.levels`, `match.tier`, and time events firing on machine 0 (Automation).
- `flow.list` shapes and hostnames, `index.folders` (Flows).
- `resource.shelves`: files per tier across the department (Resources).
