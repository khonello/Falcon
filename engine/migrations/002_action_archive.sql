-- 002_action_archive.sql -- "no hard deletes" needs a soft-delete marker on actions.
--
-- event_definitions has `enabled`, flows have status 'inactive', accounts have 'offboarded';
-- actions had nothing, so deleting a Custom Action would have been the schema's only hard
-- delete outside audit retention. Mirrored in database-schema.md 13.

ALTER TABLE actions ADD COLUMN archived_at TIMESTAMPTZ;
