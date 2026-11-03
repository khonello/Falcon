-- 052_retention_issues.sql -- old machine days are not deleted by themselves: on the 90-day clock an issue (type 'retention') asks the
-- Admins to keep or delete them (the user, 3 Nov 2026). Mirrored in database-schema.md 14.
ALTER TABLE issues DROP CONSTRAINT issues_type_check;
ALTER TABLE issues ADD CONSTRAINT issues_type_check CHECK (type IN ('file', 'update', 'deviation', 'flow', 'offline', 'component', 'retention'));
