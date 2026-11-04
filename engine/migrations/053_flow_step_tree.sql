-- 053_flow_step_tree.sql -- a flow's steps as a tree (the user, 3 Nov 2026; engine/flow/steps.py): category > kind > operation > settings.
--
-- * flow_stages.stage_type names the kind: choosing, conversion, renaming, bundling (and branch). The older transformation
--   rows are read in their new names (steps.normal); placing (categorization) was dropped, and its rows become branches, which do
--   nothing to a file.
-- * flow_sync_log.outcome also takes 'left_out': a file a step could not convert and was set to leave out (kept on the record with the
--   source version, so it is not sent again for nothing).
-- * pcs.converter: what this machine converts Office files with, as its Worker says at connect ('word', 'libreoffice' or NULL).
-- Mirrored in database-schema.md 16.
ALTER TABLE flow_stages DROP CONSTRAINT flow_stages_stage_type_check;
UPDATE flow_stages SET stage_type = 'branch' WHERE stage_type = 'categorization';
ALTER TABLE flow_stages ADD CONSTRAINT flow_stages_stage_type_check
    CHECK (stage_type IN ('branch', 'transformation', 'choosing', 'conversion', 'renaming', 'bundling'));
ALTER TABLE flow_sync_log DROP CONSTRAINT flow_sync_log_outcome_check;
ALTER TABLE flow_sync_log ADD CONSTRAINT flow_sync_log_outcome_check CHECK (outcome IN ('new', 'changed', 'kept_beside', 'removed', 'left_out'));
ALTER TABLE pcs ADD COLUMN converter TEXT;
