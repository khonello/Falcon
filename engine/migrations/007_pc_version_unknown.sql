-- 007_pc_version_unknown.sql -- a PC may have never been confirmed on an approved version.
--
-- A freshly provisioned PC runs whatever build it was installed with, which predates any
-- Super User approval; its first failed update attempt still needs a status row. NULL here
-- means "not confirmed on any approved version" and counts as behind. Mirrored in
-- database-schema.md 13.

ALTER TABLE pc_version_status ALTER COLUMN current_version_id DROP NOT NULL;
