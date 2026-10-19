# Pruning (18 Oct 2026)

Decided with the owner, before the core / full split: remove duplication first, then decide what "core" is. Four things are the product (Tasks, Flows, Restricted, Detective); everything
else earns its place by serving them or is cut. Nothing here deletes data or database tables (no hard deletes); Engine handlers of a removed page stay until the split decides their fate.

## Decided
| Call | Decision | Why |
|---|---|---|
| Assisted access (an Admin from another department asking to be let into a worker's machine) | **Cut** | A second, different rule for entering a machine on top of traversal; touches nothing core. |
| Listeners on a message channel | **Cut** (and the "Listener report" kind with it) | Silent reading of a conversation is a trust and legal liability in a sale, and costs code in four places. Ping, channel and announcements stay. |
| Deviations, Accountability, the Rules page and its builder | **Cut** | A second governance product that overlaps Detective, Issues and the queue. Detective replaces "a rule was broken". |
| Reports page and report routing | **Cut the page; routing becomes fixed** | The queue (Super User) and Issues (Admin) already show what reports produce; each kind goes to the department's Admins and the Super User, an Admin's own conduct to the Super User only. |
| Rollout page (both levels) and the version-approval gate | **Cut the page** | Version and "behind" already show on Machines / Departments; a stuck update arrives as an issue. The gate is decided at the split. |
| Access (Super User) and Sessions (Admin) pages | **Cut the pages** | Who is inside a machine is already on the machine's row ("Someone inside" filter) and its page. |
| Registry | **Moves to the Admin level**, as a tab of Machines (the department's machines and people, register and re-key a PC, let a new machine in). The Super User keeps only what the Engine reserves for them: refused connections and moving to another machine, as a tab of Departments | The owner's call (18 Oct): registering and re-keying is operations, not oversight. The Engine already lets an Admin do all of it inside their department. |
| Actions | **Stays its own Admin page** (the merge into Automation was reverted at the owner's request) | The owner's call. |
| Issues (Admin) | **Stays**, as the Admin's one inbox; the Super User's one inbox is the "Waiting on you" queue | Each level has exactly one place where things that need a person are decided. Replacing Issues with the queue is a large change for little gain. |

## Menus after
- **Admin:** Core (Overview, Messages, Tasks, Flows, Restricted, Detective) · Monitor (Machines with a Registry tab, Issues) · Automate (Automation, Actions) · Govern (Audit log).
- **Super User:** Core (the same six) · Organisation (Departments, with a Refused connections tab) · Govern (Audit log).

From 14 pages to 11 (Admin) and to 8 (Super User).

## The Super User sees and does less (owner, 18 Oct)
A CEO-level view: pages grouped by department, read first, at most one decision each; anything operational is an "Open in [Admin]'s console" link. The Super User keeps: giving and completing department tasks, assigning an Admin, escalations and cases on Admin machines, a flow asking to carry something they marked, marking their own files, pinging Admins. Done (19 Oct): Tasks, Flows and Departments are a card a department (`DeptCard`), with a narrow drawer for one item; the Super User gives and completes tasks, answers a flow's request to carry something they marked, assigns an Admin, and enters an Admin's console for everything else. Detective is the same (cases by department; the Super User decides only a case sent up and a case on an Admin's own workstation; Detective's suggestions to pause a flow or mark a folder go to the Admin). Departments keeps the standard four-part card, list and side panel. Restricted for the Super User is already only their own marks and the copies of them (the owner of a restriction decides), so it is unchanged. The Admin Overview is left as it is.

## Still to decide at the split
Custom Actions (unsandboxed scripts), the version-approval gate, the rule builder under Automation, and whether the removed pages' Engine handlers are deleted or only gated.
