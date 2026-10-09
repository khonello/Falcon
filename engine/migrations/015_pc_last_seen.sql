-- 015_pc_last_seen.sql -- when a machine was last connected.
--
-- Whether a machine is reachable *now* is the Engine's live connection list (in memory; a machine is
-- online while its client holds an authenticated connection). `last_seen_at` is what survives: set
-- when the client connects and when it drops, so a switched-off machine can say since when.
-- hierarchy.traverse refuses a machine that is not connected (FALCON_REFUSE_UNREACHABLE).
-- Mirrored in database-schema.md 1.

ALTER TABLE pcs ADD COLUMN last_seen_at TIMESTAMPTZ;
