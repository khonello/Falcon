# Admin navigation audit (7 Oct 2026)

Every place in an Admin's console (the concept, `R2NT8v3996VDFYiS3XM4JL`, version 155) that takes the viewer
from the page they are on to another page, classified by where it lands. The companion to
[su-navigation.md](su-navigation.md).

**The rules the console is held to:**

- An Admin's console is **one department**. Nothing in it opens another department's machines, flows or people
  (Hierarchy: an Admin's scope is their own department; horizontal peers are refused).
- **Up** to the Super User's level only by leaving the console (*Leave console*), and only a Super User who
  traversed in has that.
- **Down** into a worker's PC only by entering its session, with the standard check: who is in it now, and block or
  end them (Session Blocking).
- An Admin does not change what the Super User owns (an organisation-wide rule they set).

**How it was checked:** the console's own routes (`overview`, `tasks`, `flows`, `restricted`, `machines`,
`sessions`, `issues`, `automation`, `actions`, `rollout`, `audit`, `reports`) were followed through every component
they draw, 57 in all, and every `go(...)`, link, `href`, `location`, `history` and navigating callback in those 57 was
listed, plus the console frame drawn by `App` (sidebar, path, banners, Search). The cross-department findings were
then opened inside R. Mensah's console (Operations) to confirm them. Selecting a row, opening a drawer to create
something, and confirmations are not navigation and are left out.

## Summary

| Class | Count | Verdict |
|---|---|---|
| A. Same level: Admin page → Admin page (own department) | 32 rows below (some group several links) | fine, except 4 marked ⚠ |
| B. Up: to the Super User's level | 2 places | fine: explicit |
| C. Down: into a worker's PC | 2 kinds | one fine, one ⚠ |
| D. Breaks a rule or goes wrong | 9 | **fixed**, see *Fixed* below |
| E. Out of the app (concept only) | 2 | not product |

## A. Same level (Admin page → Admin page)

| From | Where you click | Goes to |
|---|---|---|
| **Frame** (every page) | each sidebar item (12) | that page |
| | the path: *Machines /*, *Actions /*, *Flows /*, *Automation /* and the rule's name, *Restricted /*, *Tasks /* | the parent page |
| | Search (Ctrl K): a page, a machine, an issue, *+N more* | that page, machine, issue, or the list |
| | *New task from the Super User* bar, *Open* | Tasks, scrolled to that task |
| **Overview** | *Tasks open*, *Flows*, *Restricted* figures | Tasks, Flows, Restricted |
| | Fleet, a machine tile; *+N* | that machine; Machines |
| | *Open issues*: *View all*, a row, *+N more* | Issues; that issue; Issues |
| | *Event volume*, *Show in audit log* | Audit log, with the kinds and time picked carried over |
| **Tasks** | *New task* (button and empty state) | New task |
| | a task | that task's page |
| | task page, the machine name | that machine |
| | New task: Cancel, Create | Tasks |
| **Flows** | *New flow* (twice) | flow editor |
| | *Edit* (enabled only on your own flows) | flow editor |
| | flow editor: Cancel (asks first), Save | Flows |
| **Restricted** | *Mark files* (button and empty state) | Mark files |
| | Mark files: Cancel, Mark restricted, *Back to Restricted* | Restricted |
| **Machines** | a machine | that machine's page |
| | machine page, *Restricted files →* | Restricted ⚠ (see D8) |
| **Issues** | an issue | that issue |
| | the machine name | that machine |
| | *Done today*, *+N more* | Audit log |
| **Automation** | *New rule* | rule editor |
| | a rule; in *Runs today*, the rule's name | that rule's page |
| | rule page, *Edit* | rule editor ⚠ (see D4) |
| | rule page, a machine; *+N more machines* | that machine ⚠ (see D2); Machines |
| | rule editor: an action's *In the library*; *action library*; *Write a custom action* | that action; Actions; New custom action |
| | rule editor: Cancel (asks first), Save | Automation, or the rule |
| **Actions** | *New custom action* | New custom action |
| | an action | that action's page |
| | action page: *Used by these rules*, a rule; *Recent runs*, a rule | that rule's page |
| | action page, *Edit script* | New custom action ⚠ (see D6) |
| | New custom action: Cancel, Save | Actions |
| **Sessions, Rollout, Audit log, Reports** | none to another page | |

## B. Up, to the Super User's level (allowed)

| Where you click | Goes to |
|---|---|
| sidebar, *Leave console* | the Super User's page for that department; the Admin's session is given back |
| the red *Super User in charge* bar, *Leave* | the same |

Only a Super User who entered by traversal sees these. An Admin in their own console has no way up.

## C. Down, into a worker's PC

| Where you click | Check | Verdict |
|---|---|---|
| machine page, *Enter session* | asks first; if someone is in it, says who and offers to end their session | fine |
| issue page, *Enter OPS-01 and look yourself* / *Look into it first* | none: it acts at once and never checks whether someone else holds the machine | ⚠ D5 |

## D. Breaks a rule or goes wrong

| # | Where | What happens | Rule |
|---|---|---|---|
| **D1** | Restricted, *Copies found elsewhere*, *+N more copies* | asks for `accountability`, a Super User page; the console cannot open it and falls back to **Overview** without a word (shows with more than five copies) | broken link |
| **D2** | rule page, *On*: the machine list | an organisation-wide rule lists **every department's** machines inside one Admin's console (Operations sees LOG-02 and three Finance machines), and each opens that machine's full page, *Enter session* and *Run action* included. Confirmed. | one department |
| **D3** | any address: `#machines/FIN-01`, `#flows/edit-payroll-pdf` | the console opens another department's machine page, and another person's flow in the editor with Save enabled. Nothing on screen links there (flow Edit is disabled on others' flows), but an address, a bookmark or a link from elsewhere does. Confirmed. | one department |
| **D4** | rule page, *Edit*, on a rule the Super User owns | enabled, and opens the editor with Save: an Admin can change an organisation-wide rule (Daily maintenance, Restricted file copied). Flows already disable Edit on others' flows; rules do not. | not the Super User's |
| **D5** | issue page, *Enter … and look yourself* | enters a worker's PC with no check of who is in it and no block-or-end step, unlike *Enter session* on the machine page | Session Blocking |
| **D6** | action page, *Edit script* | opens a **blank** New custom action, not the script you were editing | wrong page |
| **D7** | Search, *Run action on a machine…* | opens Automation (the rules), not anywhere an action is run; running one is *Run once* on Actions | wrong page |
| **D8** | machine page, *Restricted files →* | opens Restricted, which lists only the files *you* marked on *your* PC, nothing about the machine you came from | loses its context |
| **D9** | Search, *Leave session on OPS-07* | offered in every console whoever holds OPS-07 (in the sample it is the Super User's own session) | sample left in |

## E. Out of the app (concept only, both levels)

| Where | What |
|---|---|
| sidebar, *Console Kit ↗* | opens another artifact in a new tab |
| sidebar, *sample: empty · small · large · absurd* | reloads the page with another sample |

Neither belongs to the product; both exist so the concept can be reviewed.

## Not counted

Drawn nowhere inside the console, so not reachable there: every Super User page (Departments, Accountability,
Access, Registry, Reports, Rules, Rollout, Audit log and the Super User's Overview, Tasks, Flows), and the unused
components listed in su-navigation.md.

## Fixed (7 Oct 2026, concept version 156)

| # | Now |
|---|---|
| D1 | Inside a console, *+N more copies* opens Issues with *Restricted file* already picked in its type filter. At the Super User's level it still opens Accountability. |
| D2 | A rule's *On* lists only this department's machines, and says so: "7 of its 11 machines are in this department; the rest belong to others." *Test on one machine* uses one of them. |
| D3 | The console refuses another department's machine, issue or task by address, and another person's flow or the Super User's rule in the editor. It opens the list (or the rule's page) with a bar: *That is not this console's.* and why, e.g. "FIN-01 belongs to Finance, so it does not open in this console." |
| D4 | On a rule the Super User set, *Edit* and *Enabled* are disabled (on the rule page and in the Automation list), with the reason on hover; *Owner* reads "Super User", not "You". A custom action the Super User wrote has *Edit script* disabled the same way. |
| D5 | *Enter … and look yourself* and *Look into it first* ask the same question as the machine page's *Enter session* (one shared `enterSessionConfirm`), before anything happens. |
| D6 | *Edit script* opens the editor filled in with that action (name, description, language, script, limit), titled *Edit …*, with *Save changes*; Cancel and Save return to the action. Address `#actions/edit-<id>`. |
| D7 | Search's action is *Run an action once…*, opening Actions. |
| D8 | The machine page says *The copy of restricted files on OPS-03 →* (or *The 2 copies …*), opening Issues narrowed to restricted files on that machine, with an *on OPS-03 ×* tag to widen it; with none, it says so and links nowhere. |
| D9 | Search offers *Leave your session on …* only for sessions held by the person at this console. |

Checked in R. Mensah's console (Operations): `#automation/daily` (machine list, disabled Edit, Owner Super
User), `#automation/edit-daily`, `#machines/FIN-01`, `#flows/edit-payroll-pdf`, `#issues/UPD-0318` (refused, with
the bar), `#actions/edit-mapdrive` (his own, editor filled in), `#actions/temp` (the Super User's, *Edit script*
disabled), `#automation` (the Super User's rules' *Enabled* greyed). The Super User's Overview and Restricted still
draw as before. Not exercised headless, read in the code only: D1 (needs more than five copies), D5's confirmation,
D8 (on the machine page's Files tab), D7 and D9 (in Search).

Still to decide, not navigation: an organisation-wide rule's *Firings*, *Each action* and *Runs today* still count
and name runs on other departments' machines as plain text (e.g. "Check disk health · FIN-01 · Failed").

## Proposed fixes (as written before they were applied)

1. **D1:** inside a console, *+N more copies* opens Issues showing restricted-file issues only (a type filter carried
   in, like Overview's *Show in audit log*).
2. **D2, D3: the console only opens its own department.** A rule's machine list is the department's machines
   (*12 of 290 machines are in Operations*), and the router refuses another department's machine, flow, task or
   issue by address: it opens the list with a line saying it belongs to another department.
3. **D4:** *Edit* is disabled on a rule the Super User owns, with the reason on hover, as Flows already do; the
   Admin can still see the rule and its runs. (*Enabled* stays the Super User's too.)
4. **D5:** *Enter … and look yourself* goes through the same *Enter session* step as the machine page.
5. **D6:** *Edit script* opens the editor with that action's script, name and limit filled in.
6. **D7:** *Run action on a machine…* opens Actions; or *Run once* straight away with the machine to pick.
7. **D8:** the machine page's link says what it shows: *Copies of restricted files on this machine*, opening Issues
   filtered to restricted files on that machine; or the line is dropped when there are none.
8. **D9:** Search offers *Leave session on …* only for a session the person at this console holds.
