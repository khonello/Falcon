-- 023_resource_marks.sql -- restricted marks: a file or folder marked where it already is (ENGINE-CONCEPT-NEEDS WP3).
--
-- A person marks their own files or folders, on their own workstation; nothing is moved or copied. The mark says where the content may
-- be: `keep = 'machine'` (anywhere on that PC, nowhere else) or `'path'` (only in its place; a copy elsewhere is caught, even elsewhere
-- on the same PC). A folder's mark covers every file inside it and any added later. Content is matched by hash, and the mark remembers
-- every version's hash, so editing the original does not let an older copy slip through. A copy anywhere not allowed becomes an issue.
-- Unmarking sets `unmarked_at`; nothing is deleted.
-- Mirrored in database-schema.md 6.

CREATE TABLE resource_marks (
    id               INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kind             TEXT NOT NULL CHECK (kind IN ('file', 'folder')),
    name             TEXT NOT NULL,
    pc_id            INTEGER NOT NULL REFERENCES pcs(id),
    path             TEXT NOT NULL,
    keep             TEXT NOT NULL CHECK (keep IN ('machine', 'path')),
    by_account_id    INTEGER NOT NULL REFERENCES accounts(id),
    department_id    INTEGER REFERENCES departments(id),
    created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
    unmarked_at      TIMESTAMPTZ,
    unmarked_by_account_id INTEGER REFERENCES accounts(id)
);

CREATE INDEX resource_marks_pc_idx ON resource_marks (pc_id) WHERE unmarked_at IS NULL;

-- Every version of every marked file, by content: what a copy is recognised by.
CREATE TABLE resource_mark_hashes (
    mark_id        INTEGER NOT NULL REFERENCES resource_marks(id),
    content_hash   TEXT NOT NULL,
    source_path    TEXT NOT NULL,
    first_seen_at  TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (mark_id, content_hash)
);

CREATE INDEX resource_mark_hashes_hash_idx ON resource_mark_hashes (content_hash);
