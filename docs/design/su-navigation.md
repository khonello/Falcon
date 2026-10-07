# Super User navigation audit (7 Oct 2026)

Every place in the Super User's console (the concept, `R2NT8v3996VDFYiS3XM4JL`, version 154) that takes the
viewer from the page they are on to another page, classified by where it lands.

**The rule:** moving from the Super User's level to an Admin's level happens only through explicit traversal:
the *Enter X's console* step, which asks to block or end that Admin's session first (Hierarchy: traversal and
Session Blocking). Anything else that lands on an Admin-level page is a leak.

**Scope:** navigation only. Clicking a row to select it, opening a drawer to create something, and confirmations
are not navigation and are left out. Found by reading every `go(...)`, `enter(...)` and link in the source, then
checking which components a Super User can actually reach.

## Summary

| Class | Count | Verdict |
|---|---|---|
| A. Same level: Super User page → Super User page | 27 places | fine |
| B. Across levels, by explicit traversal | 3 places | fine: this is the only allowed way |
| C. Across levels, without traversal | 16 places | **broke the rule**: fixed, see *Fixed* below |
| D. Broken: goes nowhere | 1 place | **bug**: fixed |

Two Admin-level pages leak into the Super User's level without traversal:

- **The machine page** (`machines`, drawn by the Admin's `MachineList` / `MachineDetail`): Run action, Enter session,
  processes, everything an Admin works with.
- **The issue workbench** (`issues`, drawn by the Admin's `Issues`): owner picker, resolutions, notify the worker.

They are reachable because the router lets a Super User open `machines`, `issues`, `sessions` and `dept` directly
(`SU_PARENT`). `dept` and `sessions` draw Super User pages (`DeptPage`, `AccessPage`); `machines` and `issues` draw
the Admin's.

## A. Same level (Super User → Super User)

| From page | Where you click | Goes to |
|---|---|---|
| **Sidebar** (every page) | each menu item | that page |
| **Top bar** (every page) | the path, e.g. *Departments /* | the parent page |
| | Search (Ctrl K), a page name | that page |
| **Overview** | *Open deviations* figure | Accountability |
| | *On current version* figure | Rollout |
| | Fleet, *+N more* | Departments |
| | Fleet, no machines yet: *Open Registry* | Registry |
| | *Worth a look*, a row or *+N more* | Accountability (the row's record opens) |
| **Tasks** | none to another page (a click selects; *New task* opens the drawer) | |
| **Restricted** | *Mark files* | Restricted / Mark files (editor) |
| | Mark files: Cancel, Save | Restricted |
| | *Copies found elsewhere*, *+N more* | Accountability |
| **Flows** | *New flow* (twice: list, empty state) | Flows / New flow (editor) |
| | Board, *Edit* | Flows / Edit (editor) |
| | Flow editor: Cancel, Save | Flows |
| **Departments** | Board, *Department page* | Department page |
| | Board, no Admin: *Appoint an Admin* | Overview (the decision) |
| | *Machines in use today*, a pin | Audit log |
| **Department page** | *Today* chart, a pin | Audit log |
| | *Leave console* (after traversal) | back to the Department page |
| **Accountability** | Empty state, *See the rules* | Rules |
| | Board, the rule's name | Rules (that rule) |
| **Reports** | *Handling*, a department | Departments (that department) |
| **Rollout** | *By department*, a department | Departments (that department) |
| **Rules** | *New rule* | Rules / New rule (editor) |
| | *Start from a pattern*, an unused one | Rules / New rule from it |
| | Board, *Edit* | Rules / Edit (editor) |
| | Board, *See its deviations* | Accountability (filtered to the rule) |
| | Rule editor: Cancel, Save, *Back to the rules* | Rules |
| **Audit log** | none to another page | |

## B. Across levels, by explicit traversal (allowed)

Each opens *Enter X's console?*, which asks to **block** or **end** that Admin's session. Only then does the
console switch to the Admin's, under the *Super User in charge* bar. *Leave console* comes back to the department.

| From page | Where you click |
|---|---|
| **Departments** | *Admins* list on the right, an Admin |
| | Board, *Enter X's console* (one button per Admin, up to two) |
| **Department page** | *Admins*, *Enter* beside each |

## C. Across levels without traversal (breaks the rule)

### C1. To the Admin's machine page (`machines`): 10 places

| From page | Where you click |
|---|---|
| **Overview** | Fleet map, a machine tile |
| **Overview, a decision** | *A machine's update is stuck* picture, a machine |
| | *1.4.3 waits for approval* picture, a machine holding the gate |
| **Departments** | Board, *Machines* tiles, a machine |
| **Department page** | *Today* chart, a machine's name |
| **Access** | Board, *Open the machine* |
| **Registry** | Board, *Open its page* |
| **Audit log** | Board, *Open the machine* |
| **Search** (Ctrl K) | a machine |
| | *+N more machines* (opens the Admin's machine list) |

### C2. To the Admin's issue workbench (`issues`): 6 places

| From page | Where you click |
|---|---|
| **Restricted** | *Copies found elsewhere*, a copy |
| | *Where it is* chart, a copy card |
| | *Where it is* chart, *+N more copies … see them all on Issues* |
| **Departments** | Board, *Worst open issues*, an issue |
| **Department page** | *Open issues*, an issue |
| **Search** (Ctrl K) | an issue, and *+N more issues* |

Once there, the Admin's pages link on: the issue workbench opens the machine page (C1) and the Audit log; the
machine page opens Restricted.

## D. Broken

| From page | Where you click | What happens |
|---|---|---|
| **Search** (Ctrl K) | *Run action on a machine…* | asks for `automation`, which a Super User cannot open; the router falls back to **Overview** without a word |

## Not counted

These components contain navigation but are drawn nowhere, so nobody can click them: `LookCloser`, `AdminWeek`,
`DeptAdmins`, `IssueFlow`, `DeptTable`, and the *Structure* part of `Govern` (only its *Routing* part is shown, on
Reports). They should be deleted or brought back on purpose.

## Fixed (7 Oct 2026, concept version 155)

All of C and D are closed. At the Super User's level the router no longer opens `machines` or `issues`
(`suRoute`, used by every `go(...)` and by an address typed in), so a link added later cannot leak either:

| Asked for | Opens instead |
|---|---|
| a machine | **Registry**, with that machine picked. Its board offers *Work on it in X's console* (traversal, landing on that machine in the console); a department with no Admin says there is no console to work in. |
| a copy of a file the Super User marked | **Restricted**, with that file picked and that copy picked on the *Where it is* chart. The board under the chart deals with it: *Ask … to delete it*, *Delete this copy* (asks first), *Allow it on …* (with a reason). Clicking a copy card or a row in *Copies found elsewhere* picks it there too. |
| any other issue | **that department's page**, with the issue picked in a board under *Open issues*: *Handle it in X's console* (traversal, landing on that issue in the console), or *Decide it on Overview* when the department has no Admin |
| the machine list, the issue list | Registry; Departments |

Also changed:

- `SU_PARENT` keeps only `dept` and `sessions`, which draw Super User pages.
- The links that pointed at the machine page now say where they go: *See it in Registry* on Access and Audit log;
  the machine tiles, the fleet map, the *Today* chart and the decision pictures open Registry.
- **Search** at the Super User's level offers pages, machines (to Registry), issues (routed as above) and
  departments; *Run action on a machine…* is gone (an Admin's console has it).
- **Traversal can now land somewhere:** `enter(admin, { page, sub })` opens *Enter X's console?* as before, and after
  block or end opens that page and item inside the console instead of its Overview.

Checked by opening the old leak addresses: `#machines/OPS-03` lands on Registry with OPS-03 picked;
`#issues/INC-1054` on Restricted, Payroll archive, OPS-03 copy picked; `#issues/INC-1041` on Operations with the issue
picked and *Handle it in R. Mensah's / A. Quaye's console*; `#issues/UPD-0318` on Logistics with *Decide it on
Overview*. Inside R. Mensah's console, `#issues/INC-1041` still opens his issue workbench. The traversal buttons were
not click-tested headless.

## Proposed fixes (as written before they were applied)

1. **A machine, at the Super User's level, opens in Registry** with that machine picked: its board already shows
   department, user, address, version, key and last seen. Working on the machine (run an action, enter its
   session) is offered there as *Do this in X's console*, which goes through traversal (B).
2. **An issue, at the Super User's level:**
   - a copy of one of the Super User's own marked files is theirs to deal with, so it is handled on Restricted
     (the *Where it is* board gets the copy's actions: ask, delete, allow);
   - any other issue belongs to a department, so it opens on that department's page, with *Handle it in X's
     console* going through traversal (B). A department with no Admin keeps the issue on Overview as a decision,
     as today.
3. **Remove `machines` and `issues` from the Super User's routes** (`SU_PARENT`), so nothing can leak there again
   by accident; keep `dept` and `sessions`, which draw Super User pages.
4. **Search** offers only Super User pages, machines (to Registry) and departments; *Run action on a machine…*
   becomes *Run an action… in an Admin's console*, through traversal, or is dropped.
