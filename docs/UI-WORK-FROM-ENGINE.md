# UI work the Engine is waiting on

Written by the Engine session for the UI session (the user, 2 Nov 2026: separation of powers -- the Engine session never touches QML, pages
or the concept; it writes here what the UI needs). Each item: what the Engine now offers, the handler, and what a page or window should do
with it. The concept still decides how it looks. Strike an item when it is drawn.

## Console (operator_client/gui/qml)

### Flows (built 2 Nov 2026)
- **A flow's name.** `flow.create` / `flow.edit` take `name` (1-80 characters); `flow.list` / `flow.status` return it. A flow without one is
  still read as `<source folder>-<id>`.
- **When it copies.** `run_mode`: `realtime` (as before), `hourly`, `manual` ("only when I run it"); in `flow.create` / `flow.edit`, returned
  in the lists with `last_run_at`. The concept's "Real time / On a schedule / Only when I run it" select maps to these (on a schedule = hourly).
- **Run.** `flow.run {flow_id}` -> `{sources_started}`; conflict when the flow is paused, waiting for consent, or its source is offline.
- **Several sources merged into one flow.** `flow.create` takes `sources: [{source_pc_id, source_path, source_kind?}]` (1-10, not overlapping);
  `flow.list` / `flow.status` return `sources` (every source, the first is the flow's own). The list shows one flow; pause, resume, edit,
  run and retire act on all its sources.
- **Carrying on from another flow.** `flow.create` takes `from_flow: {flow_id, destination_id}`: the new flow's source is that destination;
  `source_flow_id` comes back. The concept's "a folder, or an existing flow" source.
- **Files copied.** `flow.list` / `flow.status`: `files_copied: {total, today, last_at}` (the concept's Files copied column and figure).
- **Steps.** Every step now does what it says (Rename by date, Convert to PDF, Compress to ZIP, Sort by file type, Sort by month). Convert to
  PDF does text and JPEG only; a Word or Excel file still fails with the existing suggestion. An edit retires the old steps (`flow.list`
  returns only the live ones), so the page's own "only stages a live destination reaches" filter is no longer needed.
- **Another Admin picks the folder** (`let_them_choose` on a destination; the other Admin names it in `flow.consent {destination_path}`):
  the console's New flow still says "not in the console yet". The Engine side is there since 1 Nov.

### Rules (built 2 Nov 2026)
- **Disk and network readings.** Event types `threshold.disk` (`match.percent`, of the system drive) and `threshold.network` (`match.kbps`
  received, optional `duration_s`), beside cpu and memory. The rule builder's reading picker can enable Disk and Network.
- **Would it have fired.** `control.threshold_backtest {type, value, minutes?, pc_ids?}` -> `{per_day[7] oldest first, total, by_machine
  {host: n}, now: [hosts], samples, unread}` from the stored readings: the concept's backtest under the threshold slider.

### Files in conversations (built 2 Nov 2026; ENGINE-GAPS #7, the concept's v296)
- Send: `chat.send_file {conversation_id, path}` (a file on the sender's own machine) -> `{file_id, state: reading | asked, waits_for?}`.
  Refused with the reason: programs and scripts, over 100 MB. Restricted: the sender's own restriction is their consent; someone else's waits.
- The message: `chat.message` pushes and `chat.get` messages carry `file: {file_id, name, size, state, expires_at}` (the card with Save).
- Save: `chat.file_save {file_id}` -> the caller's machine writes it to Downloads\From Falcon; pushed back as `chat.file_saved {file_id, path}`
  or `chat.file_save_failed`. `chat.files {conversation_id}` lists files with who saved them where.
- Asked to allow: `chat.file_consent_request {file_id, name, from, why}` push to the person who restricted it; they answer
  `chat.file_consent {file_id, grant}`. The sender hears `chat.file_refused {file_id, name, why}`.
- The Worker program: `localapp` ops `send_file {id, path}` and `save_file {file_id}` (client.py `send_file()`, `save_file()`); the
  conversation it gets from `conversation` carries each message's `file`. Pushes reach the program as the view's toasts only, so the
  program reads a file's state again from `conversation`.

### Private and Watch (built 2 Nov 2026; ENGINE-GAPS #3, the concept's three tags)
- `marks.create` takes `protection` (watch | private | restricted, default restricted), and for private `readers` (account ids; the owner is
  always one) and `allow_system` (the machine's system account, for backup and antivirus).
- `marks.list` / `marks.get` return `protection`, `allow_system`, `readers [{account_id, name}]`, `applied {ok, at, granted, missing, error}`
  (what the machine did; `missing`: people whose Windows name is not known yet) and, for private, `refusals [{who, account_id, process, path,
  at, machine}]` (the concept's "refused, in grey").
- `marks.readers {mark_id, readers, allow_system?}`: the owner changes who may open it. Pushes: `private.refused`, `private.apply_failed`.
- The Worker program: a refused person gets a toast of kind `private` in the view ("<name> is private", who to ask).

### Issues (built 2 Nov 2026)
- **A file deleted at a flow's source.** A flow set to keep its copies (the default) now raises an issue of type `flow` ("A file was deleted
  at a flow's source", one per flow, gathering the files) with two options from `issues.get`: `remove_copies` and `keep_copies`. The Issues
  page draws options from the Engine, so it should need nothing new; check that it reads right.

### Registry / Add a machine (built 2 Nov 2026)
- **A machine with the console installed is let in as an Admin.** `enroll.confirm` by an IT Admin now accepts a request that asked to be an
  Admin's workstation (the admin installer asks so); the level always follows what the machine asked (`requested_level`). Where Registry's
  "Asking to join" shows such a request, Let it in works now; it should say it will be an IT Admin's machine.

### Updates (built 2 Nov 2026)
- `updates.packages` -> `{packages: [{version, role, bytes, sha256, approved}], folder}`: what the Engine holds for machines to update from.
  The Rollout gate can say when an approved version has no package for a role (its machines then cannot update). A machine's failed
  update now carries the installer's last log line in `updates.report_status`' error, as before.

### Licences (built 2 Nov 2026)
- A machine joins with a licence code given at setup (admin or worker code), and nobody confirms it. The console needs a place for the
  licence: `licence.import {name, reference?, codes}` (taking in the file the licence store hands over), `licence.list` -> `{codes: [{id,
  licence, last4, role, seats, used, left, department, expires_at, revoked_at, machines: [{hostname, decided_at}]}]}`, `licence.revoke
  {code_id}`. Probably beside Registry (Machines > Registry). A machine that joins this way is pushed as `enroll.joined` and `machines.changed`.

### Flows: steps as a tree (the user, 3 Nov 2026; `engine/flow/steps.py`) -- New flow's step picker changes
- **The tree:** `flow.steps {}` -> `{tree, order}`. `tree` is a list of categories, each `{category, label, says, kinds: [{kind, label,
  says, needs?, ops: [{op, label, needs?, settings: {key: spec}}]}]}`. A setting's spec says how to draw it: `choices` (+ `default`,
  `words` for nicer labels), `many` (pick several), `list: "extension"` (file types typed in), `text: <max length>`, `number: [lo, hi]`,
  `flag`. `required` marks the ones that must be filled. Draw the picker from this, not from a list in the QML: Category > Kind >
  Operation, then its settings.
  - Per file: Choosing (by file type, by name, by size), Conversion (To PDF, To DOCX, To another image type, Zip each file), Renaming
    (Add a date, Add text, Replace text in the name).
  - All files: Bundling (Into one ZIP).
- **Sending a step:** in `flow.create` / `flow.edit`, each stage is `{"step": {kind, op, settings}, "parent_index"?}` (a branch is still
  `{"stage_type": "branch"}`). `flow.list` / `flow.status` return each stage with `stage_type` = its kind and `config: {kind, op, label,
  settings}`. The old five names (`{"config": {"op": "Rename by date"}}`) are still accepted, for the console as it is.
- **Placing is dropped.** "Sort by file type" and "Sort by month" are refused now ("placing steps were dropped"): take them out of
  New flow and the flow drawings. A flow made with one keeps running; its placing step shows as nothing.
- **The order is fixed:** Choosing, Conversion, Renaming, Bundling, on each destination's path (`order`). The Engine refuses
  any other order, so New flow can simply list a path's steps in that order (or sort them as they are added). At most one Bundling per path.
- **Add a date keeps only the newest copy.** An edited file gets a new dated name and the older copy is put aside in `.falcon-removed`; in
  `flow.runs` it shows with outcome `removed`. A copy changed at the destination stays, and a `flow.conflict` push says so.
- **Bundling** only in a flow that runs every hour or only when Run is pressed, from one folder (not a single file, not several
  sources): the Engine refuses it otherwise. Say so beside the step, and grey "Real time" when a bundling step is on (or the step when
  Real time is picked). Each run makes one file from the whole folder as it is (not only what changed), and makes none when nothing changed.
- **A Conversion that cannot be done** never stops the flow any more: the `if_not` setting ("Copy it as it is" / "Leave it out",
  default copy). Files a step left out are kept on the record: `flow.runs` gives them as `left_out`, with no `path`. A bundle's row in
  `flow.runs` has `bundle: true` and its file in `path`.
- **Which destinations convert Office files:** `flow.status` destinations carry `converter` (`word`, `libreoffice` or null). Beside a
  To PDF (Word, Excel, PowerPoint) or To DOCX (from PDF) step, say which destinations have neither, so those files will be copied as they are.
- The old fix suggestions about "add a Categorization stage" are gone; a bundle that could not be made pauses that destination as
  `bundling:bundle_failed`, with its own suggestion.

### New task: what a description cannot say (built 4 Nov 2026; `engine/task/cues.py`)
- `task.propose` `flags` has new kinds, each with `detail`, a sentence to show as it is: `cannot_check` (a message channel, another task, a flow), `unnamed_result`,
  `made_from`, `waits_on_event`, `depends_on_check`, `folder_guess`, `quality_unseen`, `inside_file`, `recurring`; `ambiguous_deadline` may now carry `detail` too. Show every flag's `detail` on the proposal, before Give.

### From the drawers, built 4 Nov 2026
- `control.event_create` / `control.event_update` take `action_limits {action_id: seconds}`; a rule's actions come back with `rule_limit_s`. `user.login` takes `match.outside_hours: true` (before 08:00, from 18:00, or a weekend).
- `flow.create` destinations take `note`, sent in `flow.consent_request`. `hierarchy.pc_register` no longer needs `department_id`: send none instead of the first department.
- **"Written by the local model":** when `telling.smoothed` is true the wording came from Groq, not a local model. Say "worded by a model; every fact is Falcon's".

### Nobody owns anything between Admins (the user, 4 Nov 2026)
- Take "only A. Quaye changes it", "Only you close it", "only whoever marked it" and the like out of the pages and the concept: any Admin changes any Automation rule, verifies any task, edits, pauses or deletes any flow, changes any mark or who may open a Private file, and answers any consent. The audit trail shows who did it. Hide no control because someone else made the thing.
- **The word (the user, 4 Nov 2026): nothing says "owner" or "yours".** Say who did it, as a fact: "Set by A. Quaye" on a rule (`automation.board`'s `set_by`; `owner` goes when the page moves), "Marked by" on a mark, "Made by" on a flow, "Given by" on a task. `flow.restricted_request` now reaches every Admin.

### What ENGINE-GAPS #23 asked for is answered (built 4 Nov 2026; names as the QML calls them)
- Live now: `task.remind`, `chat.requests` / `chat.request_accept` / `chat.request_close`, small groups (`chat.open {account_ids, title?}`), `issues.list`'s `detail`, `issues.act` key `rule`,
  `flow.remind`, `flow.keep`, `flow.start`, `flow.list`'s `sources[k].pause_reason` / `paused_at`, `update.now`, `machines.end_program`, eight `check_ins`, `automation.run_again`, `automation.skip`
  and `coming_up[k].skipped`, "20 succeeded", `marks.allow_revoke`, `marks.get`'s `lately` `who` / `where` and `flows_allowed` `flow` / `what` / `from` / `to` / `today` / `last_at`, `flow.restricted_waiting`'s `what` / `from` / `to`,
  `control.event_history`'s `detail` and `by_hand`, `threshold.signin` and `printer.offline`, `control.action_list`'s `impact` / `risky` / `created_by_name`, `actions.runs`' `who`, `detective.cases`' `restricted`.
- A file issue no longer offers `ask`. `delete`'s `done` says Resolved; the issue closes when the machine reports the file gone.
- The QML's own rewrites of these can go ("20 success" to "succeeded", hiding `ask`).
- The Worker's program: `talk {line}` is the new op for Ask IT (`chat.ask`); the corner note shows when a request is answered, and on `task.reminder`.
- Detective: `telling.smoothed` is true when Groq is set up, so the concept's "in the local model's words" should say what is true: the wording is the model's, the facts are not.

### Detective: a case told in words (built 3 Nov 2026; ENGINE-GAPS #15, the concept's "What Detective noticed")
- `detective.case` now returns `telling: {paragraphs, text, smoothed, note}`. `paragraphs` is a list of paragraphs, each a list of parts:
  `{text}` (plain words) or `{text, kind, value}` (a fact to mark). Kinds: `person` (value: account id, text already in the viewer's own
  name), `machine`, `time` (value ISO), `duration`, `file`, `folder`, `drive`, `program`, `count`, `amount`, `intent`, `reason` (a rule's
  own reason or what would make it innocent, word for word), `tag` ("a restricted file"). Mark people, files, machines, programs and times
  the way the task box does; the rest can stay plain.
- `smoothed` is true when Groq smoothed the paragraph that tells what happened and it passed the check; that needs a Groq key. Otherwise the account is the Engine's own, word for word. Either way show `note`
  ("Detective's reading of the evidence, not proof."). The page's own writing-out of the findings can go: draw this instead.
- When the smoothing arrives later, `detective.updated {case_id, telling: true}` is pushed: read the case again.

### Automation: try a rule first (built 3 Nov 2026; ENGINE-GAPS #13, the user chose this one of the three)
- `control.rule_try {type, match?, action_ids, pc_id, event_id?}`: the rule as it stands in the editor, tried once on one machine the
  person picks (online, in scope); nothing is saved. Returns `{hostname, when, condition, runs: [{execution_id, action_id, name}]}`.
  `condition.kind`: `level` (`reading`, `limit`, `over_now`, `minutes`), `clock` (`next`: three ISO times), `files` (`week`: how many times
  it would have started there in the last week, `latest`: up to five {path, at}), `signal` (`says`: seen only when it happens).
- The runs are real and come back as any run does (`action.status` pushes, `control.execution`); they run now, ignoring the action's delay.
  New rule and an opened rule's editor: a "Try it on one machine" button with a machine picker, showing the condition and the runs filling in.
- The other two ideas (what a run produced, too quiet or too loud) are dropped: nothing to draw.

### Issues: old machine records (built 3 Nov 2026; the user's answer on `pc_days`)
- A new issue type `retention` ("Old records"; code prefix RET), not tied to a machine (`pc_id` and `department_id` are null): "Old machine
  records are due to be deleted", raised daily when machine days pass the 90-day window. Two options from `issues.get`: `delete_old`
  (Delete them) and `keep_old` (Keep them; asked again in 30 days). The Issues page draws options from the Engine; it needs the type's
  label and an icon or tone in its kinds filter, and to read right with no machine.

### Registry / Add a machine: "Seen on the network" is dropped (the user, 3 Nov 2026)
- The Add a machine drawer offers only the knocked PCs (`registry.knocked`). Take out "Seen on the network" and anything that says it is
  coming: a machine with Falcon installed joins by itself with its licence code, and the Engine will not scan the network.

### Departments (built 1 Nov 2026, drawn)
- `hierarchy.department_rename`, `hierarchy.pc_move`: on the Departments page. Still to draw: the "Every department" filter on Machines and the
  department label on each machine (the concept's Machines).

### From the 1 Nov Engine pass, not drawn yet (docs/still-not-done.md)
- To-dos (`todo.list/add/done`), Messages (`chat.list/people/open/get/send/read`), the machine page's facts (`machines.get`: running_now, about,
  keyboard, check_ins), Coming up (`automation.board`: next_at, coming_up), action output kinds and Try (`control.action_try`), flow runs as a
  diff (`flow.runs`), the Restricted page's came_by / allowed / lately / flows_allowed (`marks.get`), At a glance (`detective.glance`), knocked
  PCs (`registry.knocked`).

### Tests failing on the rebuilt pages (found by the Engine session, 4 Nov 2026, on its own test database)
All in `test_operator_gui.py`, all in the QML: fix the page, or the test if the concept changed it.
- `test_nothing_clickable_uses_a_taphandler`: a `TapHandler` is back somewhere (CLAUDE.md says why not).
- `test_colours_are_named_only_in_the_theme`: a colour named outside `Theme.qml`.
- `test_restricting_finds_it_by_search_and_what_is_restricted_cannot_be_picked_again`: the Restricted page.

## The Worker's own program and windows (worker_client/program/qml, worker_client/windows/qml)

### Conversations (built 2 Nov 2026; the Worker concept's Messages tab and "An Admin writes to you" window)
- The program's view (`localapp` op `view`) now has `messages: [{id, with, unread, last, from, at}]` and `unread`.
- `localapp` op `conversation {id}` -> the conversation (messages oldest first, `from`, `at`, `mine`), marked read; op `reply {id, body}`.
  `worker_client/program/client.py` has `conversation()` and `reply()`.
- A new message puts a corner note in the view's `toasts`: `{id: "m<conversation id>", kind: "message", conversation_id, title, text}`; it
  goes when the conversation is opened.
- The person replies, never starts one: no compose anywhere on their side. "Ask for help" is cut (the `ask` op still exists; the program
  should not offer it).

### My machine (built 2 Nov 2026)
- The view's `machine`: `{name, address, windows, falcon, connected, engine, account, signed_in_at, restarted_at, storage: {total_gb, free_gb,
  used_percent}}` -- what "Copy these details" copies.
