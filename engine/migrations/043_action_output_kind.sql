-- 043_action_output_kind.sql -- what a custom action reports back, and a test run before it is saved (the user, 28 Oct 2026; ENGINE-GAPS #14).
--
-- output_kind: its author picks one of three and it is kept with the action.
--   text    what it prints is shown as it is; the first line is the summary
--   list    each line printed is a row, a tab splits the columns; the summary counts the rows
--   status  only whether it worked: the output is not shown, and exit 0 counts as worked
--
-- trial: a script run once on one machine before it is saved (control.action_try). The run is real and recorded with its author's
-- name, so it needs an action row; that row is archived the moment it is made, never in the library and never usable by a rule.
-- Mirrored in database-schema.md.

ALTER TABLE actions
    ADD COLUMN output_kind TEXT NOT NULL DEFAULT 'text' CHECK (output_kind IN ('text', 'list', 'status')),
    ADD COLUMN trial       BOOLEAN NOT NULL DEFAULT false;
