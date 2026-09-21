-- 004_action_metadata_alert_delivery.sql
--
-- Control -> Custom Actions lists "Name, description, execution timing" as Action properties
-- and built-in actions take parameters (a notification message, a path); the v1 schema had
-- no columns for them. Alerts need a delivery marker so the Scheduler can deliver scheduled
-- ones exactly once. Mirrored in database-schema.md 13.

ALTER TABLE actions ADD COLUMN name TEXT;
ALTER TABLE actions ADD COLUMN description TEXT;
ALTER TABLE actions ADD COLUMN params JSONB;          -- builtin parameters, e.g. {"message": "..."}
ALTER TABLE actions ADD COLUMN timing JSONB;          -- {"mode": "immediate"} | {"mode": "delayed", "delay_s": N}

ALTER TABLE system_alerts ADD COLUMN delivered_at TIMESTAMPTZ;
