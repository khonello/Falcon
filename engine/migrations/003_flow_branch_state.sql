-- 003_flow_branch_state.sql -- branch-scoped failure state and soft removal for destinations.
--
-- Flow -> Failure Handling: "only the specific flow or branch the failure occurred on is
-- paused". flows.status/pause_reason is flow-level; the per-destination equivalent lives here.
-- Editing a flow must not hard-delete destinations that flow_sync_log rows reference.
-- Mirrored in database-schema.md 13.

ALTER TABLE flow_destinations ADD COLUMN paused_reason TEXT;
ALTER TABLE flow_destinations ADD COLUMN removed_at TIMESTAMPTZ;
