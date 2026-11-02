-- 047_flow_names_runs_sources.sql -- what the concept's Flows pages show that a flow could not be (ENGINE-GAPS, "Flows: what the concept's
-- Flows pages show"; built 2 Nov 2026).
--
-- name: the flow's own name, given when it is made ("month-end"); NULL for older flows, which read as "<source folder>-<id>".
-- run_mode: when it copies. 'realtime' (the moment a file changes, as before), 'hourly' (what changed is copied together, every hour) or
--   'manual' (nothing moves until someone presses Run). last_run_at: when it last copied on the hour or by Run.
-- merged_into: several sources merged into one flow. The first source is the flow; each further source is a flow of its own with the same
--   name, steps and destinations, pointing at the first. Pausing, editing, running and retiring act on all of them; lists show the first,
--   with every source.
-- source_flow_id: the flow this one carries on from; its source is that flow's destination folder.
-- flow_stages.retired_at: an edit replaces the steps; the old ones are kept (no hard deletes) and marked retired, so nothing reads them.
-- Mirrored in database-schema.md.

ALTER TABLE flows ADD COLUMN name TEXT CHECK (name IS NULL OR length(name) BETWEEN 1 AND 80);
ALTER TABLE flows ADD COLUMN run_mode TEXT NOT NULL DEFAULT 'realtime' CHECK (run_mode IN ('realtime', 'hourly', 'manual'));
ALTER TABLE flows ADD COLUMN last_run_at TIMESTAMPTZ;
ALTER TABLE flows ADD COLUMN merged_into INTEGER REFERENCES flows(id);
ALTER TABLE flows ADD COLUMN source_flow_id INTEGER REFERENCES flows(id);
ALTER TABLE flow_stages ADD COLUMN retired_at TIMESTAMPTZ;

CREATE INDEX flows_merged_into_idx ON flows (merged_into) WHERE merged_into IS NOT NULL;

-- what an edit left behind before this migration: steps no live destination points at
UPDATE flow_stages s SET retired_at = now()
 WHERE NOT EXISTS (SELECT 1 FROM flow_destinations d WHERE d.parent_stage_id = s.id AND d.removed_at IS NULL)
   AND NOT EXISTS (SELECT 1 FROM flow_stages c WHERE c.parent_stage_id = s.id)
   AND EXISTS (SELECT 1 FROM flow_destinations d WHERE d.flow_id = s.flow_id AND d.removed_at IS NOT NULL);
