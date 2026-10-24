# Who runs the console: one IT team, or each department

**A proposal from the user, 24 Oct 2026. Written down only; not to be implemented yet.** It touches the backbone
(`hierarchy-system-design.md`): who an Admin answers for, where reports go, and what the Super User oversees. So it is
decided once, before the Engine changes, and every combo doc is read against it.

## The question

Is the console run from one central point by IT, or by each department for itself? An organisation picks one of two
modes.

| | **A. Per department** (what is built today) | **B. Central IT** (proposed) |
|---|---|---|
| Who the Admins are | People inside each department, each running their own | An IT team serving the whole organisation |
| An Admin's reach | Their one department (`require_department_scope`) | Every department |
| Departments are | Access boundaries | Groups of people and machines, for reading and routing; not a wall |
| Two Admins | Peers in one department, or strangers across two | Colleagues with the same reach everywhere |
| Number of Admins | Changes nothing about reach | Changes nothing about reach: one IT Admin or ten, each sees and acts on everything |

In B, "the role an Admin plays on one department is expanded to all departments". It is the same Admin console, with
the same pages and actions, over the whole organisation.

## What B changes, area by area

- **Authority.** `require_department_scope` lets an Admin through for any department. Every handler that scopes by the
  Admin's department reads the mode, so there is one switch, not a fork of the code. The Super User keeps everything
  they have now.
- **Hierarchy.** Super User → Department → Admin → PC becomes Super User → IT (the Admins) → Departments → PCs.
  Traversal is unchanged: an Admin enters any PC the way they enter one in their own department today.
- **Session Blocking.** There is still one session per PC. Today, Admins of different departments never meet on a
  machine; in B, any two IT Admins can. The horizontal-peer rule (hard refusal) applies between them unchanged, unless
  decided otherwise. Super User occupancy stays un-evictable.
- **Reports and issues.** Today a report is routed additively to that department's Admins. In B every report reaches
  every IT Admin. The risk is that everyone sees it and no one acts. B therefore needs a light way to say "mine": taking
  an issue, shown to the others. The report itself is still written once.
- **Tasks.** An IT Admin gives tasks to anyone in any department. A Super User directive to a department lands with
  the IT team. Who takes it is the same "mine" question as reports.
- **Help requests and messages.** A worker's help request goes to the IT team as a whole, not to their department's
  Admins. The first Admin to answer has the conversation; the others see that it is taken.
- **Restricted, Flows, consent.** Unchanged in rule. The owner of a restriction is whoever marked it, or the Super
  User. In B an IT Admin can mark things in any department, so consent requests can come from anywhere.
- **Display Names.** Unchanged. Names stay per namer and never cross namers. An IT Admin's names are theirs alone.
- **Audit.** Unchanged. Every row already names who did what. In B, "which department" becomes a column to filter
  on, not the edge of what an Admin can see.
- **The Admin's console.** The same pages. Lists group or filter by department, because the fleet is the whole
  organisation (the worst case on record is about 12 departments × 60 machines, so paging and grouping are mandatory).
  The situation line and Overview speak for the organisation, or for the department filtered to.
- **The Super User's console.** Departments are still measured as departments. The Admins page measures IT people by
  what they take and close, not by which department they run. Directives go to departments as now; IT receives them.
- **Schema.** A deployment setting, `admin_scope = department | organisation`. In B an IT Admin's
  `department_id` is null, or ignored. Departments, PCs and people keep their departments.

## How the mode is chosen

The proposal is one setting for the whole Engine, chosen at `python -m engine setup` and changed only by the Super
User, with a clear confirmation. Behaviour is the same no matter how many Admins there are.

## Open, for the user to decide

1. Can the mode change after setup, or is it fixed at install? If it can change, what happens to reports and tasks
   routed under the old mode?
2. A third shape, a mix where some Admins are IT-wide and some are per department: rule it out, or keep it in view?
3. In B, does the horizontal-peer refusal stay between IT Admins, or may one IT Admin take over a colleague's session
   with a warning?
4. In B, what is "mine" for an issue or help request: an explicit Take button, or whoever acts first?
5. In B, are there still department-level Admins for things only a department should decide (its Restricted folders,
   its routing), or does IT decide everything?
