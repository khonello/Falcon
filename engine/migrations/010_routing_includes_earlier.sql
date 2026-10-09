-- 010_routing_includes_earlier.sql -- a routed department can see earlier reports, or only new ones.
--
-- Visibility is decided at read time, so routing a category to a department used to show it every
-- report of that category, however old. The Super User now chooses when adding a department: the
-- reports already written come with it (the default, and the old behaviour), or only reports
-- written from now on. `configured_at` is when that department was routed; a row is kept as long
-- as the department stays routed, so the time survives later edits of the same category.
-- Mirrored in database-schema.md 8 and engine/hierarchy/reports.py.

ALTER TABLE report_routing_config ADD COLUMN includes_earlier BOOLEAN NOT NULL DEFAULT true;
