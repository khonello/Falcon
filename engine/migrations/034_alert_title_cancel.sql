-- Announcements: an optional title, and a scheduled one can be withdrawn before it is delivered (a status, never a delete).
-- Mirrored in database-schema.md (system_alerts).

ALTER TABLE system_alerts ADD COLUMN title TEXT;
ALTER TABLE system_alerts ADD COLUMN cancelled_at TIMESTAMPTZ;
