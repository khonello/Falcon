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
