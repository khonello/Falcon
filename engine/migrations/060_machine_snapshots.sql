-- 060_machine_snapshots.sql -- the last loose picture of each machine, for Detective alone (engine/detective/snapshot.py; proposals item 3).
--
-- One row per machine, replaced by the next picture (an UPDATE, never a delete): what matters is how the machine changed between two pictures,
-- and each change worth reading becomes a Detective signal, kept in its cases like any other evidence. No page shows this table.
-- Numbered 060 so it cannot take a number the main line is still using (the seats work, 057-059). Mirrored in database-schema.md.

CREATE TABLE machine_snapshots (
    pc_id           INTEGER PRIMARY KEY REFERENCES pcs(id),
    taken_at        TIMESTAMPTZ NOT NULL,          -- when the machine took it
    received_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    data            JSONB NOT NULL                 -- the sections the machine could read (worker_client/machine_snapshot.py); a missing one was not read
);
