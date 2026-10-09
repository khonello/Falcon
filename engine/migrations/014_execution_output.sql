-- 014_execution_output.sql -- what an action returned, kept with the run.
--
-- Output used to be streamed into an in-memory tail on the Engine (lost on restart) and kept in full
-- only in a log file on the worker machine. Now each run keeps:
--   * `action_executions.summary` -- one line the action can set ("C: 92% full"), light enough for
--     every list;
--   * `execution_outputs` -- the text (bounded: first and last 64 KB) and, for monitoring actions that
--     return rows, the structured `result` as JSON so a console can draw a table;
--   * `execution_images` -- a screenshot's picture (downscaled JPEG/PNG), returned only on request,
--     never pushed; every view is audited.
-- Kept 90 days: the audit retention job then clears the text, result and picture (UPDATE to NULL --
-- the run rows themselves stay, no hard deletes). Mirrored in database-schema.md 9.

ALTER TABLE action_executions ADD COLUMN summary TEXT;

CREATE TABLE execution_outputs (
    execution_id  INTEGER PRIMARY KEY REFERENCES action_executions(id),
    output        TEXT,
    result        JSONB,
    recorded_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    cleared_at    TIMESTAMPTZ
);

CREATE TABLE execution_images (
    execution_id  INTEGER PRIMARY KEY REFERENCES action_executions(id),
    mime          TEXT NOT NULL CHECK (mime IN ('image/jpeg', 'image/png')),
    data          BYTEA,
    bytes         INTEGER NOT NULL,
    captured_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    cleared_at    TIMESTAMPTZ
);
