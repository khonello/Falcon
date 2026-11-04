# Still not done (temporary, updated 3 Nov 2026)

Written after commit `560eb6f`; updated the same day when version 1 was settled (`docs/design/v1-it-admin.md`).

## The version 1 move (decided 1 Nov 2026; ENGINE-GAPS #18)
Version 1 is IT Admins only. The Super User does not exist in anything that ships. **Steps 1-5 are done (1 Nov 2026). Packaging is on hold (the user, 1 Nov 2026) until the version 1 concept pages are all in the QML.** In order:
1. *(done)* **Admins reach every department** (`admin_scope` fixed to organisation). Admins create departments (labels only) and other Admins. Every issue
   and report reaches every Admin and becomes one's by an explicit **Take**. Two Admins on one machine: refused, told who is in.
2. *(done)* **Setup makes the first IT Admin**, not a Super User (`engine setup`, `bootstrap`, `make_org.py`, `.env.example`, `GETTING-STARTED.md`).
3. *(done)* **Flows:** only an Admin-to-Admin flow needs consent (the destination Admin's, who picks the folder); onto a Worker's machine, the maker picks
   the folder and no consent is needed; the marker's consent for restricted material stays. **Single-file flows**: the source is one file
   followed by identity (rename or move at the source keeps it syncing), and the destination copy is followed the same way.
4. *(done)* **Park the Super User** in `parked/` (handlers, QML pages, TUI commands, preview data, installer role, handover, their tests) and strip every
   reference from what ships.
5. *(done)* **Console:** no Super User words, pages or data; one level, every department.
   **Left from 4-5:** the lists have no department filter yet (the Departments page makes, renames and fills departments, 1 Nov 2026);
   letting another Admin pick the folder of a flow is in the TUI, not the console; making another IT Admin is still to be designed.
6. Then packaging.

**Settled:** An Admin leaving is known by another Admin offboarding the account (the machine stays and says nothing); what the account still owns (restrictions, flows, rules, actions, tasks to verify, issues) is handed to another Admin with a tool, not a page: TUI `account owns <id>` and `account handover <from> <to>` (`hierarchy.ownership`, `hierarchy.hand_over`; decided 1 Nov 2026).

## Engine work: your answers of 2 Nov 2026
- **#3 Private tag:** *(built 2 Nov 2026)* Windows' own permissions and its audit of failed opens; see ENGINE-GAPS #3. To try for real: a
  second Windows user on a machine being refused (the VM plan).
- **#7 Sending a file in a conversation:** *(built 2 Nov 2026)* yes, an admin-tier file may go to a Worker. See ENGINE-GAPS #7.
- **#10 Finding PCs:** *(settled 3 Nov 2026)* no network scan; "Seen on the network" is dropped. A PC with Falcon installed joins with its
  licence code, and one that knocked without a key is listed (`registry.knocked`). The drawer change is in UI-WORK-FROM-ENGINE.md.
- **#13:** *(built 3 Nov 2026)* Try a rule first (`control.rule_try`); the other two dropped.
- **#15:** *(built 3 Nov 2026)* the account written from the case, smoothed by the model only where every fact survives the check.
- **A file deleted at a flow's source:** *(built 2 Nov 2026)* copies are kept by default, and an issue offers Remove the copies / Keep them.
- **`pc_days`:** *(built 3 Nov 2026)* an issue on the 90-day clock: Delete them, or Keep them and be asked again in 30 days.
- **Flow steps:** *(built 4 Nov 2026)* the tree of steps; Placing dropped. Office conversion is not yet run for real. Add a date keeps only the newest
  copy (decided 4 Nov 2026).
- **Joining with a licence code:** *(built 2 Nov 2026)* admin and worker codes from a bought licence; given at setup, the machine joins at once.
  The store, later (the user, 3 Nov 2026): codes downloaded as admin and worker codes, kept in a remote store the Engine asks at setup to
  validate a code, and a small website to buy them.
- **Making another IT Admin:** *(built 2 Nov 2026)* install the admin console on the PC; it asks as an Admin's workstation and an IT Admin
  lets it in with the code on its screen. What it is follows what is installed.

## Super User items
- **#4** group conversations and **#6** directives and notices: parked with the Super User; not part of version 1.

## Built in the Engine but not in the console
- Nothing from 1 Nov is drawn in the QML yet: to-dos, Messages, the machine page, Coming up, the action output kinds and test run, flow runs, the Restricted page, At a glance, and knocked PCs.
- The Worker's side of conversations is built (2 Nov 2026): the service puts them in the program's view with a corner note when an Admin
  writes, the program's API reads and replies (`conversation`, `reply`), and the machine's command line has `messages`, `reply` and `log`.
  The program's QML does not show them yet (the Worker concept's Messages tab and message window).

## Smaller Engine gaps already on record
- **Flows:** *(built 2 Nov 2026)* every step, a flow's name, hourly or run-only flows with Run, several sources, carrying on from
  another flow, files copied, old steps retired. Convert to PDF does text and JPEG only (Office formats need Office or LibreOffice).
- **Rules:** *(built 2 Nov 2026)* disk and network thresholds, and a threshold replayed against the last week.
- **Tasks:** department tasks go with the Super User (parked); an Admin's own to-dos replace them.
- **Overview:** the version 1 concept's Overview draws no trends under its figures, so none are kept; the Engine keeps a week of each machine's readings.
- **Detective:**
  - Clipboard pictures (PrintScreen, Win+Shift+S) and what each program sends out are watched (built 17 Oct 2026; `docs/design/detective.md`); they need a signed-in desktop to be tried for real.
  - *(built 2 Nov 2026)* a bounded, hottest-first queue for what a machine missed, and reports on the spine's tell stage.

## Tests
- *(fixed 2 Nov 2026)* The Worker test that failed when its whole file ran waited for the rule's type, which Detective already listens for; it
  now waits for its own rule. `test_signpipe`'s silent client now retries "every instance is busy", as a real client does.
- *(fixed 2 Nov 2026)* `devops_at_night` took 96 s because Detective compared every pair of events on every event (`common/detective.py`
  `_coverage`): a machine deleting a few hundred files held the Engine for half a minute. It is O(k log k) now, with the same results (one
  run: 36 s -> 0.9 s).

## Not run for real yet
- The session window end to end, a flow between two real PCs, and the tray, overlays and program on a real desktop (the VM plan).
- Running the console as a non-administrator.

## On hold
- Final packaging (Phase 9): bundled interpreter, installer, signing, helpers built as executables, and delivering the certificate and key with the install. Comes after the version 1 move.
