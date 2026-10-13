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

- **Final packaging:** bundled interpreter, installer, signing, helper windows built as executables, delivery of the
  Engine's certificate and key with the install. The small packaging (`python -m worker_client service install|start|stop|uninstall|status`)
  is done and tested.

## Housekeeping

- **GUI session message** (handler names, session window caveat, empty `pc_id`, hostname wording) was queued while
  that session was offline. No confirmation it was read.
- **`CLAUDE.md` was committed whole in 3000d67**, so it may include the GUI session's console-line edits. Check the diff.
- **Decided, for the record:** Admin from another department stays disabled; retention is 90 days on the audit clock
  (`audit_log`, `file_events`, run outputs), logged per part.
