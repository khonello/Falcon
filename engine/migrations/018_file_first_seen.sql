-- 018_file_first_seen.sql -- when the file index first saw a file where it is.
--
-- A file's journey (ENGINE-GAPS #9) shows where the same content has been and when it first appeared there; the index
-- only kept `last_seen_at`. `first_seen_at` is set once, when the row is created, and never changed by later events
-- (the upsert leaves it alone). Rows that already exist are given their last_seen_at as the best we know.
-- Mirrored in database-schema.md 3.

ALTER TABLE file_index ADD COLUMN first_seen_at TIMESTAMPTZ;
UPDATE file_index SET first_seen_at = last_seen_at;
ALTER TABLE file_index ALTER COLUMN first_seen_at SET NOT NULL;
ALTER TABLE file_index ALTER COLUMN first_seen_at SET DEFAULT now();
