# Still not done (temporary, updated 1 Nov 2026)

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
   **Left from 4-5:** the Engine's comments and docstrings still describe the full design (they name the Super User where it applies under
   `department`); the lists have no department filter yet (the Departments page makes, renames and fills departments, 1 Nov 2026);
   letting another Admin pick the folder of a flow is in the TUI, not the console; making another IT Admin is still to be designed.
6. Then packaging.

**Settled:** An Admin leaving is known by another Admin offboarding the account (the machine stays and says nothing); what the account still owns (restrictions, flows, rules, actions, tasks to verify, issues) is handed to another Admin with a tool, not a page: TUI `account owns <id>` and `account handover <from> <to>` (`hierarchy.ownership`, `hierarchy.hand_over`; decided 1 Nov 2026).

## Engine work waiting on your decision
- **#3 Private tag:** none of it is built. The open question is how a refusal is shown to the person at the machine.
- **#7 Sending a file in a conversation:** not built. The open question is whether an admin-tier file may go to a Worker.
- **#10 Seen on the network:** whether a network scan is allowed, from which machine, and how often.
- **#15 A case told in words:** it breaks the rule that the model only answers narrow questions, so you need to pick one of the two ways written in the doc.
- **#13, the other three ideas:** try a rule before switching it on, too quiet or too loud, and seeing what a run produced. They aren't in the concept, so I left them alone.
- **A file deleted at a flow's source:** each flow can already choose to keep or remove the copies. A default for new flows across the console is still open.
- **`pc_days` retention:** one row per machine per day, kept forever. Clearing them would be a third deletion beside the 90-day jobs.

## Super User items
- **#4** group conversations and **#6** directives and notices: parked with the Super User; not part of version 1.

## Built in the Engine but not in the console
- Nothing from 1 Nov is drawn in the QML yet: to-dos, Messages, the machine page, Coming up, the action output kinds and test run, flow runs, the Restricted page, At a glance, and knocked PCs.
- The Worker's own program doesn't show the new conversations; it still shows the old help channel.

## Smaller Engine gaps already on record
- **Flows:**
  - Only "Sort by file type" actually changes files. Rename by date, Convert to PDF, Compress to ZIP and Sort by month do nothing yet.
  - An edit leaves the old stages on record.
  - Missing: a flow's own name, several sources merging into one flow, schedules, and a count of files copied per flow.
- **Rules:** no threshold on disk or network.
- **Tasks:** department tasks go with the Super User (parked); an Admin's own to-dos replace them.
- **Overview:** the figures have no trend history.
- **Detective:**
  - Not watched: clipboard and PrintScreen, and what each program sends over the network.
  - No bounded queue on the event spine, and no Reports/Notices step on it yet.

## Tests
- One test fails whenever the whole Worker test file runs, on the committed code too: `test_the_worker_relays_only_the_signals_an_automation_waits_for`. It passes alone, so an earlier test is probably leaving something behind.
- The Detective actor test `devops_at_night` takes about 140 s against the 180 s limit.

## Not run for real yet
- The session window end to end, a flow between two real PCs, and the tray, overlays and program on a real desktop (the VM plan).
- Running the console as a non-administrator.

## On hold
- Final packaging (Phase 9): bundled interpreter, installer, signing, helpers built as executables, and delivering the certificate and key with the install. Comes after the version 1 move.
