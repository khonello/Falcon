-- 020_file_events.sql -- what happened to files and folders, kept (ENGINE-GAPS #9 follow-up, 10 Oct 2026).
--
-- A Worker already told the Engine about moves (with `old_path`), but the Engine used only the new path: a move looked like
-- a brand-new file, the old place stayed in the index as if the file were still there, and no one could say it had been moved,
-- renamed or deleted. Now:
--   * `file_events` is an append-only history of what the OS reported: create, move (which includes a rename), copy, delete,
--     a change of attributes (read-only, hidden), a change of permissions/owner, and the same for folders. A file being
--     edited is recorded at most once per ten minutes per file (it would otherwise be every save).
--   * `file_index.gone_at` marks a place a file has left (moved away, or deleted): the row is kept (no hard deletes), and
--     it stops being a place the file is; the file turning up there again clears it.
-- Mirrored in database-schema.md 3.

CREATE TABLE file_events (
    id             BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pc_id          INTEGER NOT NULL REFERENCES pcs(id),
    op             TEXT NOT NULL CHECK (op IN ('create', 'modify', 'move', 'copy', 'delete', 'attrib', 'security')),
    is_dir         BOOLEAN NOT NULL DEFAULT false,
    path           TEXT NOT NULL,
    old_path       TEXT,
    content_hash   TEXT,
    file_index_id  INTEGER REFERENCES file_index(id),
    occurred_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX file_events_path_idx ON file_events (pc_id, path);
CREATE INDEX file_events_old_path_idx ON file_events (pc_id, old_path) WHERE old_path IS NOT NULL;
CREATE INDEX file_events_occurred_idx ON file_events (occurred_at);

ALTER TABLE file_index ADD COLUMN gone_at TIMESTAMPTZ;
