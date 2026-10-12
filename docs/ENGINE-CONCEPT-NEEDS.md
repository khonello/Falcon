# What the console concept needs from the Engine

Written 11 Oct 2026, after the user asked that the Engine cover **everything the console needs**, not only what
`ENGINE-GAPS.md` lists. This is the page-by-page check of the concept (`docs/design/concepts-snapshot.html`,
`docs/design/super-user-menu.md`) against the handlers the Engine has. Each row says what the page shows, whether
the Engine could already feed it, and the work package that closes the gap. Work packages (WP) are built in the order
below; each is committed and pushed on its own and moved to **Done** here when it lands.

Legend: **has** = a handler already gives it; **part** = some of it; **none** = no handler, no table.

## Page by page

| Page (level) | What it needs | Engine today | WP |
|---|---|---|---|
| Overview (Super User) | decisions (stuck updates, empty departments, an Admin's pattern, the version gate, reports only the Super User sees, a department task to complete), fleet strip, *Worth a look* (deviations this week), deviations chart by severity | none (no decisions, no deviations) | 5 |
| Overview (Admin) | Waiting on you, machines online, open issues, sessions held now; fleet map by status/CPU/version/check-in; open issues; event volume by kind + live stream; per-department table (admins, online, issues, on the current version, median time to address) | part (tree, levels, audit.recent) | 1, 2, 5 |
| Departments | each department's Admins, vacancies, machines, worst open issues, assign / remove an Admin, promote a worker | part (tree, offboard) | 6 |
| Accountability | deviations: rule, expected/happened, who, when, context timeline, evidence, outcome (open / explained / accepted / escalated / dismissed) with a written explanation; grouping by rule, department, person/machine; per-day counts | none (`audit.deviations` is the old expectation log) | 4 |
| Rules | built-in locked rules and the Super User's organisation-wide patterns (never / follow / limit), the pattern library, switch on/off, deviation count per rule, "would have cleared N of M" preview | none | 4 |
| Reports | list (has), routing (has), seen (has), *Handling* (how fast each department addresses), strip (waiting, with the department, addressed, typical time) | part | 5 |
| Access / Sessions | sessions today, occupancy, assisted access history and grants | part (sessions_today, assisted_access.*) | 1 |
| Registry | machines (version, key generation, last seen), accounts (Admins, key number), refused connections (who tried, why, tries, last try), register a PC, provision an Admin, make a new key, block an address | part (pc_register, pc_rekey, account_create, auth.failed audit) | 6 |
| Rollout | the version, who runs it, machines holding the next one back (attempts, last error, next try, escalation), approve with leave-outs and a reason, retry now / when idle / when back, adoption per day, failed installs | part (approve, report_status, rollout_health) | 7 |
| Audit log | events with a kind, a plain sentence, the machine and the person; counts per kind; events over time; live stream; export | part (audit.recent has raw action types) | 1 |
| Restricted | marks of files and folders on the person's own workstation, kept to the machine or to one place; every version's hash; copies elsewhere with who was signed in; unmark; change where it is allowed; per-copy: ask the person, delete the copy, allow it here | part (old tier tags and violations; no marks) | 3 |
| Issues (Admin) | tickets: type, severity, subject, machine, owner (or unassigned), state, target time, "what to do" options, timeline; Waiting / Past target / Done today | none | 2 |
| Machines (Admin) | fleet list with health, user, version, CPU, last seen; the machine page: metrics (CPU, memory, disk, network over time), processes (pid, CPU, memory, user; end one), sessions, files, events, OS, agent uptime, IP | part (pc_state, levels, programs) | 1 |
| Messages | (built) | has | |
| Tasks (both) | department tasks (built); Admin→Worker tasks with checks (built) | has | |
| Flows | (built) flow.*; answers to "send you files" (flow.consent) | has | 2 (flow issues) |
| Automation | rules, last firings with results, runs per day, problems this week, *Test on one machine* | part (event_*, event_history) | 8 |
| Actions | library, used by, recent runs (by hand too), run once with results, custom scripts | part (action_*, execution) | 8 |
| Session window | the machine's screen in a window, see-only or see-and-control, time left, extend, leave | none (sessions yes; no screen, no input) | 9 |
| Search (Ctrl K) | find a machine, person, task, flow, issue | none | 10 |

## Work packages

1. **Machines and events** -- fleet read model with health; machine page; processes; disk and network metrics; the
   audit feed in kinds; live event push; export.
2. **Issues** -- the ticket entity and its plays (ask, delete a copy, allow an exception, accept/put back a
   certificate, retry an update, assign an Admin, leave out of the gate, remind, change or withdraw a flow).
3. **Restricted marks** -- marks, version hashes, "kept to", copy detection into Issues, copy decisions.
4. **Rules and Accountability** -- rule store, the evaluators, deviations with context, outcomes.
5. **Overviews and Reports statistics** -- the decision queue, Worth a look, fleet strip, per-department figures,
   report handling times.
6. **Registry and Departments** -- registry lists, refused connections and blocking, promote a worker to Admin,
   stop being an Admin, vacancies.
7. **Rollout gate** -- gate state, leave-outs, retries, adoption and failures.
8. **Automation and Actions statistics** -- runs per day, problems, test run, an action's runs.
9. **Session window** -- the machine's screen to the console and the console's mouse and keyboard back.
10. **Search.**
11. **Open gaps from `ENGINE-GAPS.md`** -- a file being opened, program starts caught at once, retention of
    `file_events`, a folder renamed above a file.

## Done

- **WP1 Machines and events** (11 Oct 2026). `machines.list {department_id?}` is the fleet: each machine with its health
  (healthy / warning / high / critical / offline -- the most serious thing open on it, read from Issues once WP2 lands),
  its person (named for the caller), who is inside it and how (an Admin's session, assisted access), version and whether
  it is behind the approved one, address, OS, last seen, and its latest levels; `summary` counts them.
  `machines.get {pc_id, range: 1h|6h|24h|7d}` is the machine's page: the same facts, four series (processor, memory, disk,
  network), the process list (pid, processor, memory, user -- as the machine last reported it), its sessions over the last
  week, what the file index holds on it by tier, and its last events. The Worker now says its version, OS and start time when it
  connects (`auth.respond` carries them; the Engine adds the address it saw), reports disk fullness and network throughput with its
  metrics, and sends a pid-level process list every minute. `kill_process` takes a `pid` (one process, picked from that list) or a
  program `name`, never both. *The audit trail as events:* every audit row now carries the machine and department it concerns;
  `audit.events {since?, until?, kinds?, pc_id?, department_id?, actor_account_id?, before_id?, limit?}` returns events with a
  kind, one plain sentence, the machine and the person (named the way the caller names people; an Admin sees only their own
  department's); `audit.summary` gives counts per kind and over time buckets; `audit.export` gives the CSV (and is itself
  recorded); and every event is **pushed live** (`audit.event`) to the Super User and to the Admins of the department it concerns,
  named for each viewer. Kinds: session, action, flow, assistance, rollout, deviation, violation (the concept's seven) and task,
  report, admin, system. A logged deviation is now also an audit event. TUI: `machines`, `machine <pc> [range]`, `feed`,
  `feed summary`, `feed export`. *Test:* `tests/test_console_machines.py`, `test_worker_client.py`, `test_operator_client.py`.

- **WP2 Issues** (11 Oct 2026). The ticket entity (migration 022) and `engine/console/issues.py` + `plays.py`. *Raised* from what is
  already recorded: a restricted copy (resource violation; critical when it left the original's department, high on another machine
  of the same department, medium on the same machine), an update that failed (low "One version behind", high "past the escalation
  limit" at the threshold; clears when it lands), a machine that presented another name (the deviation log; clears when it presents its
  registered name again), a flow waiting for consent (owner: the destination's owner; clears on agree, decline or removal), and a
  machine that went quiet (a sweep every minute: only machines that have connected before; medium after a day; clears when it
  connects). Owner: the one person named when raised, else the department's only Admin, else unassigned; a department with no Admin
  escalates to the Super User. `issues.list` (strip figures: open, waiting, past target, done today, mine), `issues.get` (lead, facts,
  *what can be done* with the reasons something cannot, timeline = the issue's own log merged with what the audit trail shows on
  the machine), `issues.act`, `issues.assign` (take, give, hand back), `issues.escalate`, `issues.note`; pushes `issue.raised`,
  `issue.resolved`, `issue.escalated`. *Plays:* **file** -- ask the person (a message on their screen; the issue closes when the copy is
  gone), delete this copy (a real run of the new `delete_file` built-in on that machine; clears the issue when it succeeds), allow it
  here too (reason required, remembered); **update** -- retry when idle / when back online, retry now (the Worker retries at once),
  leave it out of the next version's gate (reason required); **deviation** -- accept the presented name (renames the machine) or put it
  back; **flow** -- remind, send somewhere the Admin manages (edits the flow), withdraw. A machine's health is now read from its open
  issues. TUI: `issues`, `issue <id>`, `issue act|take|give|free|escalate|note`. *Not yet:* assigning an Admin from an issue
  (WP6), the Super User's decisions built on issues (WP5), the rule that every issue also points at (WP4). *Test:*
  `tests/test_console_issues.py`, `test_worker_client.py`, `test_operator_client.py`.


- **WP3 Restricted marks** (11 Oct 2026). A file or folder is marked where it already is, on the marker's own workstation
  (`marks.create {paths, keep: machine|path}`; `marks.tree` lists what the index holds on your workstation to pick from): kept to the
  machine (anywhere on that PC, nowhere else) or to its place (a copy anywhere else is caught, even elsewhere on the same PC). A folder
  covers every file in it and any added later; the mark remembers **every version's hash**, so an edited original never lets an older copy
  slip through. Every file event is checked: a copy where its mark does not allow it is flagged -- a violation and report as before and a
  file issue the marker owns (critical when it left the original's department, high on another machine of the same department, medium
  elsewhere on the same machine) -- and copies already elsewhere are found at marking time. `marks.list {scope: mine|department|all}`,
  `marks.get` (the mark, its copies with who is signed in, this week's resolved ones, and what changing where it is allowed would do),
  `marks.keep_effect`, `marks.change_keep` (copies now allowed close, newly caught ones are raised), `marks.unmark` (open copy issues close;
  history kept). The per-copy decisions are the issue plays: ask the person, delete this copy, allow it here too. TUI: `marks`, `mark`,
  `mark show|keep|remove`. *Test:* `tests/test_console_marks.py`, `test_operator_client.py`.

- **WP4 Rules and Accountability** (11 Oct 2026). *Rules* (`rules.list/get/library/create/update/switch/try`; migration 024): the four
  built-in rules are listed locked (B-1 restricted files stay where they are, B-2 one session per machine, B-3 machines run the approved
  version within two days, B-4 a machine's name matches); the Super User writes organisation-wide rules of three shapes -- *never*, *follow*,
  *limit* -- from the pattern library (restricted file leaves its folder, unanswered help request, machine past the update limit, Admin
  outside their department, out-of-hours session). **The stored shape of a rule is decided here, as the user asked the Engine to
  settle it** (CLAUDE.md had it deferred): `spec` JSON in `rules.spec`, documented in database-schema.md 15 and kept in
  `engine/console/rules.py`; change it there if you disagree. An Admin reads the list ("set by the Super User"); only the Super User changes
  it; a built-in cannot be changed or switched off; switching off stops new deviations and never deletes old ones. `rules.try` says what a
  changed line would have done to the last month's deviations before it is saved. *Deviations* (`deviations.list/get/outcome`, Super User only):
  every one points at its rule and keeps the rule **as it was**; carries what was expected and what happened, who or what it concerns
  (named for the reader), the timeline around it (the audit trail on that machine) and **evidence -- facts only** (who was signed in, which
  Admin entered and how long before it, whether an issue was open on the machine); an outcome (open / explained / accepted / escalated /
  dismissed) where *explained* and *accepted* need the person's own note -- the system never states a cause. List: strip counts by kind,
  per rule, per day (open vs dealt with, by severity), grouping by rule / department / person-or-machine. *Recording*
  (`engine/console/accountability.py`): the combos tell it what happened -- a restricted copy (B-1), a machine presenting another name
  (B-4), a session refused because the machine is held (B-2); a ping to an Admin, a report routed to a department, a version approved, a
  department task given, a department left without an Admin open **watches** on *follow* rules that the sweep (every minute) closes as kept
  or records as a deviation when late; *limit* rules count the audit trail (Admin entries outside working hours, assisted-access entries,
  entries into one machine, failed sign-ins on one machine) over the rolling period, once per period. What a rule says to do is all the
  system does: report it to the Super User (about an Admin: the Super User only), tell the department's Admin (never about an Admin), run
  an Action on the machine. TUI: `rules`, `rule`, `rule add|on|off|try|library`, `deviations`, `deviation <id>`, `deviation outcome`
  (the old raw log is now `expectations`). *Test:* `tests/test_console_rules.py`, `test_operator_client.py`.

- **WP5 Overviews and Reports statistics** (12 Oct 2026). A report now records where it came from (machine, department, the Admin it is about) and
  `reports.board {days?, department_id?}` says whose each one is (`dept`, or the Super User's because it is `fixed` -- about an Admin --, `noadmin` or
  `unrouted`), who addressed it and in how many minutes, with the strip (waiting, with the department, addressed, typical time) and per-department
  *Handling* (all / done / waiting / to you / median). `overview.queue` is the Super User's decisions, worst first, each with its options and their
  effects: reports nobody below can take (mark addressed, route the category, open the seat decision, leave a machine out of the next version's gate,
  ask / limit / note an Admin), a department with no Admin (promote one of its Workers, provision a new Admin; an Admin from another department is
  drawn disabled with the reason -- an Admin belongs to one department), a department's work called done (complete / send back). `overview.decide`
  carries one out through the same handler the console would otherwise call. `overview.su` (four figures, deviations by day and severity, Worth a
  look), `overview.admin` (Waiting on you, machines online, open issues, sessions held) and `overview.departments` (Admins, vacancies, machines,
  issues, on the current version, median time to address, reports) feed both Overviews. New: `hierarchy.admin_promote`, `hierarchy.admin_limit`
  (traversal refuses a limited Admin outside working hours). The version gate decision plugs in through `overview.CARD_SOURCES` / `DECIDERS` and
  arrives with WP7. TUI: `overview`, `departments-board`, `board`, `decisions`, `decide`, `promote`, `admin limit`. *Test:*
  `tests/test_console_overview.py`, `test_operator_client.py`.

- **WP6 Registry and Departments** (12 Oct 2026). `registry.accounts {department_id?, roles?}` (the Super User and every Admin; key number, workstation,
  signed in), `registry.refused {days?}` (one row per who-tried / from-where: the name it claimed, address, why -- not registered, the key that was
  replaced, a wrong key for a machine from an address it never uses --, tries, first / last try, whether blocked, and the advice: register, rekey, block,
  unblock), `registry.block` / `unblock` / `blocked` (an address is refused before the challenge; the try is still counted; never your own address).
  `auth.failed` now records the address, the claimed name, the machine the client id belongs to and which key number was used. `departments.get`
  is a department's page (Admins, `vacant`, machines with health, worst issues, reports handling, open work, Workers who could be promoted).
  `hierarchy.admin_demote` is *Stop being an Admin* (the account stays as a Worker on the same machine, which gets a new key; the issues they owned
  go back to the department; an empty seat is watched). The update issue in a department with no Admin has the play `admin` (promote a Worker there
  and assign the issue to them). *Not done, on purpose:* giving a department an Admin from another department -- an Admin belongs to one department,
  so the seat decision draws it disabled with the reason. TUI: `accounts`, `refused`, `block`, `unblock`, `blocked`, `department`, `admin demote`.
  *Test:* `tests/test_console_registry.py`, `test_operator_client.py`.

- **WP7 Rollout gate** (12 Oct 2026). `rollout.gate {department_id?}` is the whole Rollout page: the current version, when and by whom it was approved; the version
  waiting (`updates.stage`); the strip (running it, holding, left out, failed installs this week and which machines); the machines holding the next approval back
  with their state (retrying / offline / escalated / left out), attempts, last error (the Worker now says what went wrong), next try and who the escalation went to;
  adoption day by day with who joined; `can_approve`. `updates.approve {version, leave_out?, reason?}` no longer waits for machines left out (earlier with
  `updates.leave_out`, or named at approval with a reason) and records them against the version; `updates.take_back` puts one back; `updates.retry {pc_id,
  when: now|idle}` (an Admin in their department; offline machines can only be told for when they are back). The waiting version is also a Super User
  decision (wait / approve now, leaving the holders out with a reason / approve) in `overview.queue`. TUI: `gate`, `update stage|retry|leave-out|take-back|approve ... leave_out=`.
  *Test:* `tests/test_console_rollout.py`, `test_operator_client.py`.

- **WP8 Automation and Actions statistics** (12 Oct 2026). `automation.board {days?}` lists the rules in scope -- the name (a new `name` on a rule, or the rule worded from what it
  watches for), kind (Event / Schedule / Level), what it watches for and does, who set it (an organisation-wide rule is read-only in an Admin's console), on or off,
  how often it fired and when last, how its last firing's runs ended ("All 3 succeeded", "1 failed, 1 success"), its problems -- with the strip and runs per day by
  outcome (Success / Failed / Timed out / Stopped by you). `actions.board` is the library with the rules that use each action, runs, runs by hand, problems, the last run,
  the time limit and each action's own days; `actions.runs {action_id?, event_id?, hand?}` the runs themselves (how long, what it said, what set it off).
  `control.event_test {event_id, pc_id}` is *Test on one machine*: it runs the rule's actions once on a machine it applies to and is online, as a run by hand
  (not a firing). `control.event_history` now says how each run ended. An Admin sees their department's machines only. TUI: `automation`, `action board`, `runs`, `event test`,
  `event add ... name=`. *Test:* `tests/test_console_automation.py`, `test_operator_client.py`.

- **WP9 Session window** (12 Oct 2026). `hierarchy.traverse` takes `mode`: `control` (default, as before: the person is locked out and told who is working on their machine) or `see`
  (they keep working and the Worker shows a bar, "X is viewing your screen", that never takes a click). `session.screen {session_id, action: start|stop, width?, fps?}` turns the picture of
  the machine on or off for whoever entered it (a traversal only -- never an invited helper's session, never a person's own), returning the time left; the machine's Worker captures the
  primary screen (stdlib GDI + PNG, only when it changed, at most `fps` a second, never queued) and sends `session.frame`, which the Engine passes to the viewer alone. `session.control
  {session_id, mode}` switches see / control while the session lasts (the person is told at once; `control` also blocks their own keyboard and mouse with `BlockInput`, which Windows
  ends if the process dies and Ctrl+Alt+Del always overrides); `session.input {session_id, events}` carries the console's mouse and keyboard as fractions of the screen (move, down, up,
  wheel, key, text; at most 200 a call; control mode only) and the Worker applies it with `SendInput`. It all ends with the session -- left, ended by a superior, expired -- or when either
  connection drops. Start, stop, mode changes and how long it lasted are audited; input itself is not. TUI: `traverse ... mode=`, `screen start|stop|shot|mode|click|type`.
  *Test:* `tests/test_console_screens.py`, `test_worker_client.py` (input plan, streamer, lockout), `test_operator_client.py`.
