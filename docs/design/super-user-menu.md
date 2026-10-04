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
- **Flows**
- **Restricted**

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

## Final menu at a glance

```
Core          Overview · Tasks · Flows · Restricted
Organisation  Departments (with the Admin roster) · Accountability · Reports · Access · Registry
Govern        Rules · Rollout · Audit log
```
