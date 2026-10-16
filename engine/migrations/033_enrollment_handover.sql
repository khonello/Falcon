-- A machine can ask to become the Super User's machine (engine/hierarchy/handover.py): the same account moves, the old machine stops being the Super User's.
-- Mirrored in database-schema.md (enrollments).

ALTER TABLE enrollments DROP CONSTRAINT enrollments_requested_level_check;
ALTER TABLE enrollments ADD CONSTRAINT enrollments_requested_level_check CHECK (requested_level IN ('worker', 'admin', 'super_user'));
