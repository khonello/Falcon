# A click stays on its page: sweep (7 Oct 2026)

The rule ([super-user-menu.md](super-user-menu.md), *A click stays on its page*): a click changes the page only when
it is the sidebar, the path, Search, a link whose words name where it goes (ending "→"), or a create/edit button
that opens an editor. Everything else acts in place.

This sweep lists every click in the concept (version 156) that changes the page, at both levels, built on
[su-navigation.md](su-navigation.md) and [admin-navigation.md](admin-navigation.md): the same reachability pass
(components drawn from each level's routes) and every `go(...)` and `enter(...)` in them. Each is marked:

- **ok**: frame, a link that names its page, or an editor's create/edit/cancel/save;
- **arrow**: names its page but lacks the "→";
- **implicit**: a row, tile, figure, chart mark, rail item or name that changes the page without saying so.

## Super User

| Page | Click | Goes to | Verdict | Change |
|---|---|---|---|---|
| Overview | *Open deviations* figure | Accountability | implicit | figure is plain; the *Deviations, 7 days* panel carries *Accountability →* |
| | *On current version* figure | Rollout | implicit | figure is plain (Rollout is in the sidebar) |
| | Fleet, a machine tile | Registry | implicit | click pins the tile's card in place, with *See it in Registry →* in it |
| | Fleet, *+N* | Departments | implicit | *+N more on Departments →* |
| | Fleet, no machines: *Open Registry* | Registry | arrow | *Open Registry →* |
| | *Deviations, 7 days*: *Accountability* | Accountability | arrow | *Accountability →* |
| | *Worth a look*, a row | Accountability | implicit | row opens in place under itself (expected, what happened, who), with *Open in Accountability →* |
| | *Worth a look*, *+N more* | Accountability | implicit | *+N more in Accountability →* |
| Overview, a decision | *Update stuck* and *1.4.3 gate* pictures, a machine | Registry | implicit | machines are marks with their name on hover, not links |
| Departments | Admins rail, an Admin | asks *Enter X's console?* | ok (asks first) | |
| | board: *Enter X's console* | console, after asking | arrow | *Enter X's console →* |
| | board: *Department page* | Department page | arrow | *Department page →* |
| | board: *Appoint an Admin* | Overview | implicit (does not say Overview) | *Appoint one on its page →* (the department page has the picker) |
| | board: *Machines* tiles | Registry | implicit | marks, name on hover |
| | board: *Worst open issues*, a row | Department page | implicit | plain rows; *Department page →* is beside them |
| | *Machines in use today*, a pin | Audit log | implicit | pin shows its event on hover, as now; no jump |
| Department page | Admins, *Enter* | asks first | arrow | *Enter →* |
| | issue board: *Deal with it on Restricted*, *Decide it on Overview*, *Handle it in X's console* | those | arrow | each gets "→" |
| | *Today*, a machine's name | Registry | implicit | name only |
| | *Today*, a pin | Audit log | implicit | hover only |
| Accountability | empty: *See the rules* | Rules | arrow | *See the rules →* |
| | record: the rule's name | Rules | implicit (a name as a link) | name plain, then *See the rule →* |
| Reports | *Handling*, a department | Departments | implicit | filters the reports list to that department (click again to clear) |
| Rollout | *By department*, a department | Departments | implicit | filters *Holding the gate* to that department |
| Restricted | *Copies found elsewhere*, *+N more copies* | Accountability | implicit | the rail grows in place to list them all, scrolling |
| Rules | *Start from a pattern*, an unused one | rule editor | implicit (a rail row opens an editor) | selects it: its pattern shows in the board, with *Build a rule from it* (an editor button) |
| | board: *See its deviations* | Accountability | arrow | *See its deviations in Accountability →* |
| Access, Audit log | board: *See it in Registry* | Registry | arrow | *See it in Registry →* |
| Registry | board: *Work on it in X's console* | console, after asking | arrow | "→" |
| Tasks, Flows, Restricted, Rules | *New task*, *New flow*, *Edit*, *Mark files*, *New rule*, editors' Cancel and Save | editors and back | ok | |
| Everywhere | sidebar, path, Search, *Leave console* | | ok | |

## Admin's console

The console's pages still use the older list-then-page pattern: a row opens the item's own page. Under the rule a row
selects and a board under the list shows the item, as on the Super User's pages; only a machine keeps its own page,
reached by *Open OPS-03's page →*.

| Page | Click | Goes to | Verdict | Change |
|---|---|---|---|---|
| Overview | *Tasks open*, *Flows*, *Restricted* figures | those pages | implicit | figures plain |
| | Fleet, a machine tile; *+N* | machine page; Machines | implicit | pin in place with *Open OPS-03's page →*; *+N more on Machines →* |
| | *Open issues*, a row | Issues | implicit | row opens in place under itself, with *Open in Issues →* |
| | *Open issues*: *View all*, *+N more* | Issues | arrow / implicit | *All issues →*; *+N more in Issues →* |
| | *Event volume*, *Show in audit log* | Audit log | ok | |
| Tasks | a task | the task's page | implicit | **board under the list**: targets and signs of progress, the verdict (Complete / Incomplete) |
| | task: the machine's name | machine page | implicit | name only; *Open OPS-01's page →* in the board |
| Machines | a machine | machine page | implicit | **board under the list**: health, version, session, user, with *Open OPS-03's page →*, *Enter session*, *Run action* |
| Issues | the machine's name | machine page | implicit | *Open OPS-03's page →* |
| | *Done today*, *+N more* | Audit log | implicit | *+N more in Audit log →* |
| Automation | a rule; in *Runs today*, a rule's name | rule page | implicit | **board under the list**: the rule's *How it works*, its actions, Edit, Enabled, *Test on one machine* |
| | rule: a machine; *+N more machines* | machine page; Machines | implicit | names only |
| | rule editor: *In the library*, *action library*, *Write a custom action* | Actions | arrow, and **leaves an unsaved editor** | open the action in a side drawer, read-only, without leaving the editor |
| Actions | an action | action page | implicit | **board under the list**: what it does, used by, outcomes, the script, *Run once*, *Edit script* |
| | action page: *Used by* a rule; *Recent runs* a rule | rule page | implicit | names only (Automation is in the sidebar) |
| Machine page | *The copy of restricted files on OPS-03* | Issues | arrow | "→" |
| | *Enter session* | asks first | ok | |
| Flows, Restricted, Sessions, Rollout, Audit log, Reports | | | ok: already in place, or no links | |

## Count

Rows in the tables above (a row can hold several clicks of one kind):

| | Super User | Admin |
|---|---|---|
| implicit | 17 | 12 |
| arrow only | 10 | 2 |
| Admin pages to rebuild with a board | | Tasks, Machines, Automation, Actions |
