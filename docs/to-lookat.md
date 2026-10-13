# To look at

Open items to go over with the user. Bring this up first in a new session, then tidy it as items close.
Last updated 13 Oct 2026.

## Waiting on a decision

- Nothing. (Hostname mismatch decided 13 Oct 2026: the console says "recorded, not blocked", as the Engine behaves.)

## Not exercised yet

- **Session window with a real console watching a real desktop.** The pieces are tested apart (frames, input, helper,
  service), never end to end.
- **Tier-only file-open rules.** Not watched live by design: the Worker cannot decide them, and the log says so.
- **Department-level issues with an empty `pc_id`.** The Engine never raises one. The GUI session was told. Nothing to
  change unless the user names one they expect.

## On hold until everything is locked

- **Final packaging** (plan agreed in `docs/PACKAGING-PLAN.md`): bundled interpreter, installer, signing, helper windows built as executables, delivery of the
  Engine's certificate and key with the install. The small packaging (`python -m worker_client service install|start|stop|uninstall|status`)
  is done and tested.

## Housekeeping

- **GUI session message** (handler names, session window caveat, empty `pc_id`, hostname wording) was queued while
  that session was offline. No confirmation it was read.
- **`CLAUDE.md` was committed whole in 3000d67**, so it may include the GUI session's console-line edits. Check the diff.
- **Decided, for the record:** Admin from another department stays disabled; retention is 90 days on the audit clock
  (`audit_log`, `file_events`, run outputs), logged per part.

## Found while trying the session window live (13 Oct 2026)

- **The blocked person sees nothing.** The Engine pushes `session.blocked` / `session.viewing`, `ClientState` keeps
  it (`falcon.blocked`, `blockedSession`, `blockedBy`), but no QML draws it: the Admin whose console the Super User
  entered shows no bar. For the GUI session (the one session lid, "blocked" wording).
- **Block vs end an Admin's session.** The Engine treats both the same; the dialog offers both.
- **Session window:** picture, mouse and (by script) keyboard injection work; overlays shown on the Worker PC for see and control. Left: typing through the console on a second machine.
- **Fixed in GUI files by this session:** auto-connect on start (`app.py`), `EnterConsole.qml` (`enter` clashed with the
  popup's own; the mode sent was "block"/"end"), the three pages that enter a machine now send the take-over.
