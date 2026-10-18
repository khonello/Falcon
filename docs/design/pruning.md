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
| Registry | **Becomes a tab of Departments** ("Machines and accounts"), not a page of its own | The owner's call; machines and accounts belong to departments. |
| Actions | **Becomes a tab of Automation** | The library exists to serve rules. |
| Issues (Admin) | **Stays**, as the Admin's one inbox; the Super User's one inbox is the "Waiting on you" queue | Each level has exactly one place where things that need a person are decided. Replacing Issues with the queue is a large change for little gain. |

## Menus after
- **Admin:** Core (Overview, Messages, Tasks, Flows, Restricted, Detective) · Monitor (Machines, Issues) · Automate (Automation, with an Actions tab) · Govern (Audit log).
- **Super User:** Core (the same six) · Organisation (Departments, with a Machines and accounts tab) · Govern (Audit log).

From 14 pages to 10 (Admin) and to 8 (Super User).

## Still to decide at the split
Custom Actions (unsandboxed scripts), the version-approval gate, the rule builder under Automation, and whether the removed pages' Engine handlers are deleted or only gated.
