-- 046_flow_single_file.sql -- a flow can carry one file, followed wherever it goes (the user, 1 Nov 2026; docs/design/v1-it-admin.md).
--
-- source_kind 'file': source_path is the file itself. When it is renamed or moved on its machine the flow's source_path follows it (from the
-- index's move events), so its changes keep syncing. followed_path: where the flow's own copy is at a destination when someone has moved or
-- renamed it there; the next change is written to that place instead of the destination folder. Null while it is where the flow put it.
-- Mirrored in database-schema.md.

ALTER TABLE flows ADD COLUMN source_kind TEXT NOT NULL DEFAULT 'folder' CHECK (source_kind IN ('folder', 'file'));
ALTER TABLE flow_destinations ADD COLUMN followed_path TEXT;
