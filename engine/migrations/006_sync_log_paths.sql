-- 006_sync_log_paths.sql -- write attribution needs to know WHICH file a destination write was.
--
-- Stages move files at the destination (Categorization puts report.txt under txt/), so an
-- external edit at the destination cannot be mapped back to its source file by path
-- arithmetic. Each flow_sync row now records the source-relative path it synced and the
-- destination path it actually wrote. Mirrored in database-schema.md 13.

ALTER TABLE flow_sync_log ADD COLUMN source_relative_path TEXT;
ALTER TABLE flow_sync_log ADD COLUMN written_path TEXT;
