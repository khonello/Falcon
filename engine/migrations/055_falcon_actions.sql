-- 055_falcon_actions.sql -- actions that come with Falcon (the user, 13 Nov 2026: "it must begin with a good enough number of actions internal
-- to the system").
--
-- A fresh install has an Actions library before any Admin writes one: Falcon's own (engine/control/starter.py), each with a stable
-- `falcon_key`. They are made by nobody, so `created_by_account_id` is NULL for them and only for them; pages say "Falcon". The Engine adds
-- any that are missing each time it starts (by key, archived ones included, so one an Admin archived does not come back). Any Admin may run,
-- change or archive one, as with any action.
-- Mirrored in database-schema.md 16.
ALTER TABLE actions ALTER COLUMN created_by_account_id DROP NOT NULL;
ALTER TABLE actions ADD COLUMN falcon_key TEXT;
ALTER TABLE actions ADD CONSTRAINT actions_made_by CHECK (created_by_account_id IS NOT NULL OR falcon_key IS NOT NULL);
CREATE UNIQUE INDEX actions_falcon_key ON actions (falcon_key) WHERE falcon_key IS NOT NULL;
