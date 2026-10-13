-- A Worker's indexer or event tracker that keeps dying is an issue on that machine (type 'component'), raised by the
-- Worker's own report (`control.component_status`) and closed by the next report that says it is healthy.
-- Mirrored in database-schema.md 14.

ALTER TABLE issues DROP CONSTRAINT issues_type_check;
ALTER TABLE issues ADD CONSTRAINT issues_type_check CHECK (type IN ('file', 'update', 'deviation', 'flow', 'offline', 'component'));
