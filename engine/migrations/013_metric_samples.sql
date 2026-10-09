-- 013_metric_samples.sql -- a machine's levels over time, for the "typical day" band.
--
-- control.metrics arrives every few seconds and used to live in memory only, so the threshold slider
-- could only show where the machines sit *now*. The Engine now keeps one sample per machine every
-- few minutes (engine/control/events.py METRIC_SAMPLE_SECONDS) and control.levels draws the rolling
-- 7-day p10-p90 per metric from them. Never deleted (no hard deletes outside audit retention); at
-- one row per machine per 10 minutes the table grows slowly and is read by time range only.
-- Mirrored in database-schema.md 9.

CREATE TABLE metric_samples (
    pc_id       INTEGER NOT NULL REFERENCES pcs(id),
    sampled_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    cpu         REAL NOT NULL,
    memory      REAL NOT NULL,
    idle_s      REAL NOT NULL,
    PRIMARY KEY (pc_id, sampled_at)
);
CREATE INDEX metric_samples_at ON metric_samples (sampled_at);
