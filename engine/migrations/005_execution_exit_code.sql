-- 005_execution_exit_code.sql -- the worker reports the process exit code; the Dashboard shows
-- it next to the status. Mirrored in database-schema.md 13.

ALTER TABLE action_executions ADD COLUMN exit_code INTEGER;
