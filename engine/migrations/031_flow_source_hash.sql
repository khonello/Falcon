-- A flow remembers which version of the SOURCE file each destination was last given, so a destination that was away (offline, paused, failed)
-- can be caught up with exactly what it is missing, and nothing it already has is sent twice. `content_hash` stays what was WRITTEN (a stage may
-- change it); `source_hash` is what it was made from.
-- Mirrored in database-schema.md 6.

ALTER TABLE flow_sync_log ADD COLUMN source_hash TEXT;
