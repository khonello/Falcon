# Super User menu: structure, Accountability and Rules

Decided in conversation on 4 Oct 2026. This is the reference for the concept work; the concept artifact has not been changed yet.
Companion to `super-user-reference.md` (what the role can see and do).

## Why the old menu was replaced

The old Super User menu had three catch-all pages (Monitor, Work, Govern). Each held several unrelated things behind one label, so a
label did not say what was behind it. The Admin menu was not the model either: the Admin operates one department, while the Super
User supervises, decides and shapes the whole organisation.

The Super User's verbs, which the menu is built from:

- **Decide**: complete department tasks, take escalations, open the gate to the next version.
- **Hold Admins accountable**: they see every report, and no Admin judges their own Admin.
- **Shape the organisation**: create departments, appoint Admins, register or re-key PCs.
- **Reach across**: cross-department flows, assisted access, un-evictable occupancy of any machine.
- **Be the record**: the audit log and the reports only they see.

## The menu

**Core**

- **Overview**: decisions first (escalations, tasks ready to complete, reports addressed to no one, the update gate), a fleet health
  strip, and one line "N things worth a look" that opens Accountability. Replaces Monitor and Work.
- **Tasks**
- **Restricted**
- **Flows** (last in Core)

**Organisation**

- **Departments**: the organisation tree with each department's Admin roster, vacancies, and appointing or removing Admins. A
  department page opens from here and carries that department's machines and open issues. There is no separate Admins page: who the
  Admins are is structure, and structure lives here.
- **Accountability**: deviations from the rules, each with an owner and an outcome (defined below).
- **Reports**: everything the system wrote down, including what only the Super User sees. Tabs: the list, **Routing** (who receives
  what), **Handling** (how fast each department deals with them).
- **Access**: who is inside which machine now, assisted access grants, ending or blocking sessions. Live state and action, not history.
- **Registry**: machines and accounts. Register a PC, re-key it, provision an Admin. Rare but Super User only, so it needs a home.
  Open question: stay in the menu, or move behind a Settings entry.

**Govern**

- **Rules**: the standard the organisation is measured against (defined below).
- **Rollout**: versions and the gate to the next one.
- **Audit log**: everything that happened, and who did it.

Dropped as menus:

| Dropped | Where it went |
|---|---|
| Monitor | Overview's health strip, and Departments for the detail |
| Work | Overview |
| Issues | Under each department; escalated ones surface in Overview. An issue is a ticket an Admin works; the Super User does not triage |
| Machines | Reachable from a department and from Registry. A flat list of every PC is not how the Super User thinks |

## Accountability

**Definition:** a deviation that someone can be asked about. A *deviation* is the event: the rule expected X and Y happened.
*Accountability* is that event with an owner attached: who, when, in what context, and what came of it.

"Things that went bad" is wider and is not the page. A disk failing or the network dropping goes bad with nobody to ask; those stay
as issues under the department.

**Inclusion test:** a rule was broken **and** there is someone or something to attribute it to (a worker, an Admin, a PC, a
department). No rule broken: it is not here. Nobody to attribute to: it is a department issue.

**Excluded:**

- Faults with no one to attribute them to (they stay in department issues).
- Routine events that kept to the rules (they stay in the Audit log).
- An Admin's own Automation rules firing. Those are that Admin's business and would put one department's tuning on the Super
  User's page. The Super User can see an Admin's rules inside the department, but a firing is not a deviation.

**What it covers:**

- **PCs**: version past the update limit, certificate hostname mismatch, offline past the limit, unusual hour of use, unanswered help
  requests.
- **Workers**: copies of restricted files, usage outside the permitted pattern, missed deadlines on tasks they were part of.
- **Admins**: entering machines outside their department or out of hours, repeatedly entering the same machine, taking over a session
  with no issue open there, touching restricted files, reports and escalations left unanswered, assisted access used often or never
  closed, failed sign-ins, re-issued keys.
- **Departments**: no Admin, or repeatedly slow.

**One record carries all of it:**

| Part | Example |
|---|---|
| Rule | Restricted files stay where they are |
| Expected / happened | Stay in the Finance share / copied to a USB path |
| Who | Yaw, on OPS-03, in Operations |
| When | Thu 09:30, during a session the owner was in |
| Context | The timeline around it: who else was on the machine, what ran, which reports fired |
| Possible reason | Evidence only (see below) |
| Outcome | Open, explained, accepted, escalated, dismissed |

**Possible reason follows "propose, never silently resolve".** The system never states a cause. It shows what is in the timeline, such
as an Admin entering the machine two minutes earlier. A reason becomes a recorded explanation only when a person writes one ("approved
by finance lead"); that sets the outcome to explained and stays on the record.

**Layout:** headline counts by kind, then one list of deviations, most serious first. A grouping switch gives the accountability view:
**by rule**, **by department**, **by person or machine** (the Admin view lives here, as one grouping, not a page). It is deliberately
one page: a separate Deviations page would hold the same rows.

## Rules

**Definition:** the standard the organisation is measured against, set by the Super User for the whole organisation.

**Rule versus pattern:**

- An **Automation rule** is reactive: when X happens, do Y. Admins write these for their own department (Automate group, Admin level).
- A **pattern** is what *should* happen, an expected flow. A deviation is a departure from it. The Super User writes these.

**Three shapes a pattern takes:**

1. **Must never happen**: a restricted file copied outside its folder, two sessions on one PC.
2. **Must follow**: after A, B must happen within a time. A help request answered within an hour, an escalation addressed within a day,
   an update landed within a week.
3. **Must stay within a limit**: a count or rate, such as entries into other departments' machines per week, or failed sign-ins per hour.

**The graph builder** reads left to right: the trigger is the first node, the expected steps follow with their time limits, and every
expected step has a second branch "if this does not happen" leading to a **deviation node**. At the deviation node the Super User
chooses what the system does: record it, report it to the Super User, notify the department's Admin, or run an Action (such as lock the
screen).

**Pre-created patterns** form a library to start from, so nobody starts from a blank graph: Restricted file leaves its folder,
Unanswered help request, Machine past the update limit, Admin outside their department, Out-of-hours session. Pick one, adjust the
limits, choose the scope, switch it on.

**Built-in rules appear here too, locked.** The ones the system always enforces (restricted files, one session per PC, the update
limit, the certificate match) show as locked: the Super User can see them but not edit or disable them. Without this, a restricted-file
deviation would link to a rule that is listed nowhere.

**Page layout:** a library strip of templates; the active patterns as a list, each with its deviation count this week linking into
Accountability filtered to that rule; the graph builder opens from either.

**Constraints:**

- An Admin cannot turn off an organisation-wide pattern. It shows in their console as "set by the Super User".
- A deviation is a record; the system does not punish. Any Action it runs is one the Super User chose in the graph, and nothing runs
  silently.
- The stored shape of a pattern is **not decided**. `condition_spec` and Flow-stage `config` JSON shapes are explicitly deferred
  (CLAUDE.md, spec §10, schema §12). The concept shows the graph and the templates; do not settle the stored form unilaterally.

**Why Rules is separate from Accountability.** They do different jobs on different schedules. Accountability is for reviewing: opened
often, light, read-first. Rules is for authoring: opened rarely, and the graph builder is the heaviest screen in the menu. Nobody
looking at deviations should land in a graph editor. The Admin level already follows this split (Automation is its own page). Rules
sits in Govern (the Super User setting the organisation's standards); Accountability sits in Organisation because it reports on the
people and machines there.

## How Accountability and Rules are tied

The rule is what makes something an accountability record.

- **Every record points to a rule.** No rule, no record.
- **Rules shows the other side.** Each rule lists its deviation count this week; clicking it opens Accountability filtered to that rule.
  Accountability keeps "by rule" as a grouping.
- **A record keeps the rule as it was when the deviation happened.** Raising a limit from 1 hour to 2 does not rewrite last week's
  "broke the 1-hour rule".
- **Switching a rule off stops new records and never deletes old ones** (no hard deletes).
- **Which rules count:** the built-in rules and the Super User's organisation-wide rules only (see Excluded above).
- **Editing can show its effect before saving** (idea): "raising this limit would have cleared 14 of the 19 deviations this month",
  from data already on the Accountability page.

## Open questions

- Does **Registry** stay in the menu or move behind a Settings entry? (Rarely used, so it could sit low.)
- Does the first concept include the full graph builder, or only the template library and the active list, with the builder as a later
  step? The Admin's Automation page already has a similar builder that can be reused.
- Does **Overview** keep the line "N things worth a look" counting open deviations only? (Outcomes make "open" meaningful.)

## Opening, creating and editing (decided 6 Oct 2026, revised 7 Oct 2026)

One standard across every Super User page, chosen by size:

- **A click on a row selects it; it never opens a drawer.** The selected item shows in a **board directly under the
  list**, whole: its facts, any sections (a chart, a timeline), and its actions in the board's header. With nothing
  picked the board shows the first row, or the most urgent one, and says so ("the first in the list · click another to
  see it here"). One click, one result: a drawer opened by the same click covered the board it had just updated.
  In the concept the board is one component, `ItemBoard`, except where the page draws its own (Tasks, Restricted,
  Rules, Flows, Accountability).
- **Editing happens in the board:** a task's Edit turns its title and deadline into fields above its chart; a rule's
  Switch on/off and a mark's Unmark sit in the board header.
- **Small things are created in the side drawer**, with stacked labels and Cancel / Create at the bottom: New task,
  Register a PC, Provision an Admin. A new key is shown once in that same drawer, which then cannot be dismissed by
  clicking outside it.
- **Big things get one full-page shell**: form on the left, live preview on the right, Cancel and Save in a bar fixed at the
  bottom. Used for New flow, Edit flow, Mark files and the rule editor. No step-by-step wizards.
- **Modals only for "are you sure"** (Unmark, make a new key, end a session, discard a half-built flow, change where a
  marked file is allowed). Never for creating or editing.

### The selected item is remembered

The page and the item selected on it are navigation state, not a moment:

- In the Qt console: kept in the client's navigation state and restored on reload, reconnect or reopening the app.
  Selecting an item pushes it onto a history, so Back returns to the previous selection or page. Links from elsewhere (a
  notification, the Overview, Accountability) open the page with that item selected.
- Saved edits live on the Engine and survive anything. Only unsaved typing in an open Edit form can be lost; the form warns
  before it is closed with changes in it.
- The concept shows the same thing with the address: `#tasks/D-14`, `#restricted/M-9`, `#flows/weekly`.

### A click stays on its page (decided 7 Oct 2026)

Applies to every page at every level. A sudden change of page makes you work out where you are and how you got
there, so a click may change the page only when:

1. it is the **sidebar**, the **path** at the top (*Departments / Operations*), or **Search** (Ctrl K): moving is their
   whole job;
2. **its words name where it goes**: *Department page →*, *See it in Registry →*, *Show in audit log →*, *Enter
   R. Mensah's console*. Such a link ends in "→" everywhere, so it reads the same on every page;
3. it is a **create or edit button that opens a full editor** (*New flow*, *Edit*, *Mark files*); the editor keeps the
   path back (*Flows / New flow*) and Cancel returns where you were.

Everything else acts in place: rows, tiles, figures, chart marks, rail items and names select, filter, highlight, or
show the item in the board under the list. A name is not a link to another page unless it says so with "→".

One page is kept because a board cannot hold it: a machine's own page (charts, processes, sessions, files), reached
only by *Open OPS-03's page →* in that machine's board.

### Leaving the Super User's level

Going from a Super User page into an Admin's console happens only through traversal: *Enter X's console*, which asks
to block or end that Admin's session first. Every link on the Super User's pages, and which ones break this, is listed
in [su-navigation.md](su-navigation.md).

## The standard list container (decided 6 Oct 2026)

Use it wherever a page's main job is a list of things you open (Core uses it for Given to departments, Marked files and All
flows in the organisation; apply it in Organisation and Govern where it fits). In the concept it is one component,
`ListPanel`, so the pages cannot drift apart.

- **Frame:** one panel. Title and a short subtitle on the left of the header ("most urgent first · click one to see it below");
  on the right a search box ("Filter by …") and the one primary action (New task, Mark files, New flow) in blue.
- **Size:** one fixed height (452px in the concept) whether it holds one row or a full page; six rows a page. A footer
  is always there: "1–6 of 96" on the left, the pager on the right. The rail beside it, if any, is the same height.
- **Columns, in this order:**
  1. **The item:** a grey icon, the name in medium weight, and one small grey mono line under it (a path, a route,
     an ID and department).
  2. **Up to three plain columns** in quiet grey text (who made it, who was told, where it is allowed). A measure is a
     grey bar with its figure beside it (files covered, files copied, time used).
  3. **Now:** a dot and a few words. Green when it is fine, red when someone has to act, grey when it is waiting.
- **Colour** is spent only in the Now dot. No coloured text, rings or badges in the other columns.
- **Rows:** a row selects the item; the board under the list shows it. No per-row buttons; Edit lives in the board.
- **Empty:** the panel keeps its size and says what will appear there, with the primary action as a button.

The **rail** beside a list (Ready to complete, Copies found elsewhere) is a short list of rows: a coloured mark, the title,
one grey line under it and a time on the right; up to six, then "+N more"; same starting height as the list.

## Organisation and Govern, as built in the concept (6 Oct 2026)

Every page, top to bottom: a strip of four plain figures, the standard list container with a rail beside it, the board
of the selected item (remembered in the address), then at most one visual. Strip figures that are also filters are
marked "filter".

The visual sits below the board, full width, and shows the page's own thing: either a change over time the rows cannot
show (or that filters the list), or a diagram of the selected item (Flows: the flow; Rules: the rule's pattern). A page
with neither gets none; pages are not given a chart for symmetry.

| Page | Strip | List (a row selects; the board under it shows the item) | Rail | Visual (below the board) |
|---|---|---|---|---|
| Departments | departments, without an Admin, machines online, open issues | Departments: Admins, online, open issues; Now = No Admin / N critical / All well | Admins (click enters their console) | Machines in use today |
| Accountability | PCs, Workers, Admins, Departments (filters) | Deviations: who, severity, when; Open / Everything | Rules broken this week (click filters) | Deviations per day, still open vs dealt with (click a day filters) |
| Reports | waiting on you, waiting in departments, addressed (filters), typical time | Reports: what, goes to, written; Now = Waiting on you / With the department / Addressed | Handling by department | — (Where reports go sits below) |
| Access | inside now, non-owner sessions, at night, assisted | Sessions today: owner locked out, started, length | Assisted access | Machine occupancy today |
| Registry | machines, checking in, accounts, refused this week | Machines: version, key, last seen; Register a PC | Accounts (Provision an Admin) | Refused connections: who tried without a valid key, why, tries, last try (a section, not a chart) |
| Rules | rules, switched on, broken this week, kept | Rules: set by, applies to, this week; New rule | Start from a pattern | The pattern of the rule you opened, else the one set most recently (Edit sits on it) |
| Rollout | current version, running it, holding 1.4.3 back, failed installs | Holding the gate: running, last error, next try | By department | Machines on 1.4.2 (Approve sits on it) |
| Audit log | events, actors, violations, kept for | Everything that happened: when, kind; Export | Kinds (click filters) | Events over time (drag to narrow) |

The rule editor uses the full-page shell with the pattern diagram as a band above it; built-in rules open read-only.

Core follows the same order (list, then the board of the item you clicked or the most relevant one): Tasks shows how far
each Admin told has got (Given, Seen, Under way, Done, Completed by you; the most urgent task by default), with the
facts and the decision (Not done yet / Complete, or Remind them) under the chart; Restricted shows where a marked file
belongs and where copies turned up (the one with most copies by default); Flows shows the flow diagram (the most recent
by default), with its sync log under it.

### Where reports go (Reports, decided 7 Oct 2026)

One row per kind of report, read as a sentence with a blank: the kind and one plain line on what writes it; "Goes to
**you** and [departments ▾]" (a searchable multi-pick that holds fifty departments, with an *every department*
shortcut); and on the right this week's count and how many are waiting on you, which previews the change as you edit
("5 → 0 waiting on you"). A picked department with no Admin says so under the row. *About an Admin* is a locked row:
you only. Changed rows are tinted; Save asks first and is recorded. It replaced a kinds × departments grid of dots
that needed a legend to read and never said why you would route anything.

### Where it is (Restricted, decided 7 Oct 2026)

A chart of fixed size, whatever the number of copies:

- **Allowed**, on the left: a plain grey box for the machine, with the rule in words under its name ("allowed anywhere
  on this PC" or "allowed only in D:\Acquisitions\") and a *change* link that asks first and says what it means for
  copies. Inside, one box for the marked item, the same for a file or a folder; only its icon and grey line differ
  ("file · the original", "folder · 23 files, and any added later").
- **Elsewhere**, at the right edge: a card per copy (machine, who was signed in, for a folder the file that was copied,
  where, how long ago); a quiet outline, a softer dashed arrow from the original, the time in red, no fill, no blue.
  Three slots, the most serious first, centred when fewer; the rest counted on one reserved line ("+4 more copies, less
  serious · see them all on Issues ›"). No copies: the same frame, dashed, "No copy anywhere else".
- The header carries only Unmark. No switch between the two rules on the board.

## Final menu at a glance

```
Core          Overview · Tasks · Restricted · Flows
Organisation  Departments (with the Admin roster) · Accountability · Access · Registry · Reports
Govern        Rules · Rollout · Audit log
```
