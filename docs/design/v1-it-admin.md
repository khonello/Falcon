# Version 1: IT Admins only, the Super User packed away

Decided by the user, 1 Nov 2026. This builds on `who-runs-the-console.md` (25 Oct: mode B, central IT) and settles what it left open. Where
this and an older doc disagree for version 1, this wins. The combo docs keep their full design; they carry a short version 1 note pointing here.

## What version 1 is

- **One console, for IT Admins only.** There may be several IT Admins, all with the same reach over every department and every machine.
  Workers are the people at the machines; they never use the console.
- **No Super User in version 1.** It does not exist in anything that ships: no page, word, menu item, sample data, link, handler reachable from
  the console, installer role or setup step names it. It is not deleted: its code is **parked** outside what the packages carry, to be
  reconnected in a later version (decided 1 Nov 2026).
- **Departments are labels.** Admins create them and use them to group people and machines for reading and filtering. They are not walls: an
  Admin's reach does not stop at one.
- **Everything is created from the console:** departments, Admins, machines, flows, restrictions, rules, actions, tasks, to-dos.

## Decisions (1 Nov 2026)

| Question | Decision |
|---|---|
| Super User code | Parked in a `parked/` folder the packages never include; every reference stripped from what ships. Reconnecting starts there. |
| Consent for flows | Only a flow **from one Admin's machine to another Admin's machine** needs consent: the destination Admin's. A flow onto a Worker's machine needs none. |
| Who picks the destination folder | **The destination chooses.** For an Admin's machine, that Admin picks the folder when consenting. For a Worker's machine, the Admin making the flow picks it (assumed: Workers never use the console). |
| Restricted material in a flow | **Kept as it is**: a flow pauses and asks the Admin who marked the restricted file or folder, unless that Admin made the flow. So there are two consents, never more: the destination Admin's (Admin to Admin) and the marker's (restricted). |
| Two Admins on one machine | **Refused**, as peers are today: the second Admin is told who is in and since when, and can message them. Nobody pushes a colleague out. |
| "Mine" for an issue or report | **An explicit Take.** Every issue and report reaches every Admin and stays unassigned until one takes it; the others see who has it. `issue take / give / free` already exist. |
| First account at setup | (assumed) `python -m engine setup` makes the first IT Admin, not a Super User. Any Admin can then add Admins and departments. |

## Flows can carry one file, followed wherever it goes

A flow's source is a **folder or a single file**. A single file is followed by its identity in the Global File Index, not by its path: if it is
renamed or moved on its machine, the flow keeps syncing its changes from the new place. The destination copy is followed the same way: if
someone moves or renames it at the destination, the next change is written to where it now is, not to the old path. "A flow never overwrites a
file it did not write" still holds: the followed copy is the one the flow wrote. A file deleted at either end follows each flow's existing keep /
remove choice.

## What stands in for the Super User

| Where the design named the Super User | Version 1 |
|---|---|
| Owner of a restriction | The Admin who marked it. **Open:** who owns it when that Admin leaves (proposal: it passes to whoever takes the issue, or stays with nobody and any Admin may decide). |
| Rules "set above you", organisation-wide automations | Gone: every rule is an Admin's, and any Admin sees every rule. A rule stays its maker's to change. |
| Department tasks and directives | Gone. An Admin's own to-dos (ENGINE-GAPS #17) take their place. |
| Notices and announcements from above | Gone. Admins write announcements to Workers as now. |
| Reports only the Super User sees ("about an Admin") | Gone. Every report goes to every Admin. |
| The un-evictable Super User session | Gone. Admin to Admin is refused (above). |
| Report routing to departments | Gone: there is nothing to route, every Admin receives everything. |
| The first account | The first IT Admin (above). |
| Handover of the Super User's machine | Parked. |

## The move, in order

**Steps 1-3 done 1 Nov 2026.** One switch, `FALCON_ADMIN_SCOPE` (`engine/permissions.py`: `org_wide`, `kept`, `own_department`,
`in_scope`), defaults to `organisation`; `department` keeps the full design for later and is what the older tests run under (a test marked
`organisation` runs as version 1: `tests/test_v1_scope.py`). Admins make departments and other Admins, take one away (never themself),
promote and demote; a department needs no Admin of its own; every issue starts unassigned for any Admin to take; reports reach every
Admin. `engine setup` / `bootstrap` make the first IT Admin in a department named IT. Flows: only onto another Admin's machine needs consent,
and that Admin names the folder as they agree (`let_them_choose` at creation, `destination_path` in `flow.consent`); a Worker's folder is
named by the maker. A flow's source may be one file (`source_kind: file`, migration 046): a move at the source takes the flow along, and its
copy moved at a destination is where the next change is written (`followed_path`). TUI: `flow create ... file`, `dest=<pc>:` to let them
choose, `flow consent <id> yes folder=..`. Steps 4-6 are next.


1. **Engine: Admins reach every department.** One setting (`admin_scope`, fixed to organisation for version 1) in `engine/permissions.py`;
   every handler that filters by `ident.department_id` reads it. Department and Admin creation become Admin handlers. Reports and issues reach
   every Admin, with Take.
2. **Engine: setup and accounts.** `engine setup` bootstraps the first Admin; `bootstrap`, `make_org.py`, `.env` and `GETTING-STARTED.md` follow.
3. **Flows.** Consent only Admin to Admin, with the destination Admin choosing the folder; Worker destinations chosen by the maker; restricted
   consent from the marker kept. A single-file source and a followed destination copy (index identity, move events, the sync log's
   `written_path`).
4. **Park the Super User.** Move its handlers, QML pages, TUI commands, preview data, installer role, handover and their tests into `parked/`;
   strip every reference from `engine/`, `operator_client/`, `worker_client/`, `installers/`, `scripts/` and the docs that ship. The `super_user`
   role literal stays in the schema (migrations are never edited) but no account of it is made.
5. **Console.** The Admin console with no Super User words, pages or data; departments as filters and groups.
6. **Then packaging** (Phase 9), on the result.

## Still open

- Who owns a restriction when the Admin who marked it leaves.
- `who-runs-the-console.md` question 5 (department-level Admins) is answered by this: there are none; IT decides everything.
