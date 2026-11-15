-- 061_file_lineage.sql -- one identity for a file that survives rename, move and edit (proposals item 1, the exact links; engine/file_index.py).
--
-- A `file_index` row is a PLACE (a machine and a path). A lineage is the FILE: every place it has been, whatever its name and content were. A
-- place joins a lineage by one of the exact links, recorded in `file_index.linked_by`:
--   new        first seen here, with nothing to tie it to anything known
--   file_id    the same Windows file id (volume serial + file index) seen at another path of the machine: renamed or moved
--   move       a move event from a place of that lineage
--   replaced   written over a place of that lineage that had been left seconds before (an editor's save: temp file swapped in)
--   copy       a copy event from a place of another lineage: a new lineage, `copy_of` that one
--   hash       the same content as a place of another lineage: a new lineage, `copy_of` that one
-- Its versions are the hashes its places have had (the history in `file_events`); nothing about restricted status changes here.
-- Every place already known starts as a file of its own. Numbered 061 (see 060). Mirrored in database-schema.md.

CREATE TABLE file_lineage (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    first_pc_id     INTEGER NOT NULL REFERENCES pcs(id),
    first_path      TEXT NOT NULL,
    first_name      TEXT NOT NULL,
    first_seen_at   TIMESTAMPTZ NOT NULL DEFAULT now(),
    copy_of         INTEGER REFERENCES file_lineage(id),
    began_by        TEXT NOT NULL CHECK (began_by IN ('new', 'copy', 'hash'))
);

CREATE INDEX file_lineage_copy_of_idx ON file_lineage (copy_of) WHERE copy_of IS NOT NULL;

ALTER TABLE file_index ADD COLUMN lineage_id INTEGER REFERENCES file_lineage(id);
ALTER TABLE file_index ADD COLUMN file_id TEXT;
ALTER TABLE file_index ADD COLUMN linked_by TEXT CHECK (linked_by IN ('new', 'file_id', 'move', 'replaced', 'copy', 'hash'));

CREATE INDEX file_index_lineage_idx ON file_index (lineage_id) WHERE lineage_id IS NOT NULL;
CREATE INDEX file_index_file_id_idx ON file_index (pc_id, file_id) WHERE file_id IS NOT NULL;

WITH born AS (
    INSERT INTO file_lineage (first_pc_id, first_path, first_name, first_seen_at, began_by)
    SELECT pc_id, path, filename, COALESCE(first_seen_at, last_seen_at), 'new' FROM file_index ORDER BY id
    RETURNING id, first_pc_id, first_path
)
UPDATE file_index f SET lineage_id = born.id, linked_by = 'new' FROM born WHERE f.pc_id = born.first_pc_id AND f.path = born.first_path;
