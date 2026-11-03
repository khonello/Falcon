# Parked: the Super User

Version 1 is IT Admins only (the user, 1 Nov 2026; `docs/design/v1-it-admin.md`). Nothing that ships names the Super User, so its code
lives here. No package includes this folder (`pyproject.toml` finds `engine*`, `operator_client*`, `worker_client*`, `common*` and
`protocol*` only), ruff skips it, and pytest never collects it. It is kept, not deleted: reconnecting the Super User starts here.

## What is here, and where it goes back

| Here | Back to | What it is |
|---|---|---|
| `engine/task/dept_tasks.py` | `engine/task/` (and `engine/task/__init__.py`, `Engine.start`'s `reschedule_all`) | Department tasks: `task.dept_*` |
| `engine/hierarchy/handover.py` | `engine/hierarchy/` (and `__init__.py`, `Engine.__init__`'s `reset_state`, `enroll.request`'s `super_user` level) | Moving the Super User to another machine: `handover.*` |
| `engine/console/overview_decisions.py` | the end of the helpers in `engine/console/overview.py` | `overview.queue`, `overview.decide`, `overview.su` |
| `engine/cut_handlers.py` | each block names its file (`engine/hierarchy/reports.py`, `engine/hierarchy/accounts.py`) | `reports.routing_get`, `reports.routing_set`, `reports.addressed_view`, `hierarchy.admin_limit` (parked 1 Nov 2026, with their tests) |
| `engine/bootstrap.py` | `engine/__main__.py`, called by `first_account` when the scope is `department` | The first Super User at setup |
| `operator_client/tui/commands/dept_tasks.py` | `operator_client/tui/commands/` (and its `__init__.py`) | `dtask`, `dtasks` |
| `operator_client/tui/commands/cut_commands.py` | each block names its file | `handover *`, `decisions`, `decide`, `admin limit`, `routing *`, `addressed`, the Super User's `overview`, `--handover-join` |
| `operator_client/core/handover_join.py` | `operator_client/core/` | The new machine's half of a handover |
| `operator_client/core/narrate.py` | `operator_client/core/` (and `FalconBridge.narrate`) | Sentences for the Super User's charts |
| `operator_client/gui/qml/*.qml` | `operator_client/gui/qml/` (`Desk` back into `qmldir`) | The Super User's pages, the department cards, entering an Admin's console, the task strip |
| `tests/` | `tests/` | Their tests |
| `design/concepts-super-user.html` | the "Falcon Concepts" artifact (claude.ai/artifact/R2NT8v3996VDFYiS3XM4JL) | The Super User's concept, as last published (23 Oct 2026); the Admin and Worker concepts in `docs/design/` were cleaned of it on 3 Nov 2026 |
| `design/*.md` | `docs/design/` | The Super User's design notes: `su-navigation`, `su-pages`, `super-user-menu`, `super-user-reference` (migrations 022 and 024 still cite `super-user-menu.md` by its old path) |

## What stayed in the shipped code

- The `super_user` role literal in the schema (migrations are never edited), and the Engine's branches for it. They run only under
  `FALCON_ADMIN_SCOPE=department`; in version 1 (`organisation`, the default) an account of that role is refused at sign-in
  (`engine.permissions.signs_in`) and setup never makes one.
- `engine.permissions.require_head`: whoever heads the organisation. Any Admin in version 1, the Super User under `department`.
- The Engine's comments and docstrings name the role "the head of the organisation" (what `require_head` means), not by its name. Its
  branches in code (`role == "super_user"`) stay: they run only under `department`.
- The installers have no Super User role; the first IT Admin's console takes the id and key setup printed (`--role admin --client-id`).

## Reconnecting

Set `FALCON_ADMIN_SCOPE=department`, move each file back as the table says, and put the cut blocks back in their files. The full-design tests
already run under `department` (the default for tests); the ones here go back into `tests/`.
