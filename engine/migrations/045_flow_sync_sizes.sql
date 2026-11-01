-- 045_flow_sync_sizes.sql -- a flow's last sync, as a diff (the user, 24 Oct 2026; ENGINE-GAPS #11).
--
-- For each file a flow wrote: what happened to it at the destination (new, changed, or a file the flow did not write kept beside the new one) and
-- its size there before and after, as the destination's Worker reports when it writes. Runs are read from the log by time (flow.runs), not stored.
-- Rows from before this migration have no outcome or sizes. Kept on the 90-day clock with the rest of a flow's history. Mirrored in
-- database-schema.md.

ALTER TABLE flow_sync_log
    ADD COLUMN outcome      TEXT CHECK (outcome IN ('new', 'changed', 'kept_beside', 'removed')),
    ADD COLUMN bytes_before BIGINT,
    ADD COLUMN bytes_after  BIGINT;
