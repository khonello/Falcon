-- 042_machine_days.sql -- what the Machines page shows about one machine (the user, 24 Oct 2026; ENGINE-GAPS #9).
--
-- About the machine: its memory, its system drive's size and when it last booted, as its Worker says when it connects (the OS, the
-- version and the address were already kept; the registered date is pcs.created_at).
--
-- A day per machine: when its Worker first reached the Engine that day (a check-in: the PC is on and connected, whether or not anyone
-- is signed in), and the quarter hours (0 = 00:00-00:15 ... 95, the Engine host's local time) in which someone used the keyboard or
-- mouse. One small row per machine per day; the page reads today and the last week. Mirrored in database-schema.md.

ALTER TABLE pcs
    ADD COLUMN memory_total_mb INTEGER,
    ADD COLUMN disk_total_gb   REAL,
    ADD COLUMN boot_at         TIMESTAMPTZ;

CREATE TABLE pc_days (
    pc_id           INTEGER NOT NULL REFERENCES pcs(id),
    day             DATE NOT NULL,
    checked_in_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    used_quarters   SMALLINT[] NOT NULL DEFAULT '{}',
    PRIMARY KEY (pc_id, day)
);
