-- 016_pc_programs.sql -- the programs installed on a machine, as its Worker last reported them.
--
-- "Start a program" is picked from what is installed on that machine (ENGINE-GAPS #5). Installed programs change
-- rarely, so the latest list per machine is kept in the database; what is *running* changes by the second and is
-- kept in memory only (engine/control/inventory.py), like the machine's levels.
-- Mirrored in database-schema.md 9.

CREATE TABLE pc_programs (
    pc_id        INTEGER PRIMARY KEY REFERENCES pcs(id),
    programs     JSONB NOT NULL,
    reported_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);
