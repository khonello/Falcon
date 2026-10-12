-- 028_automation_names.sql -- an automation can have a name (ENGINE-CONCEPT-NEEDS WP8).
--
-- The Automation page lists rules by a name a person gave them ("Snapshot a USB drive when it is inserted"). Without one the console words the rule from what it
-- watches for. Nothing else about how a rule is stored changes.
-- Mirrored in database-schema.md 18.

ALTER TABLE event_definitions ADD COLUMN name TEXT;
