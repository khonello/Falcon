-- 041_todos.sql -- an Admin's own to-dos (the user, 29 Oct 2026; ENGINE-GAPS #17).
--
-- Not a kind of Task: a Task goes from one person to another and is closed by verification. A to-do is a line of text its owner
-- wrote for themselves, with when it is due and when it was done. Nothing else: no checks, no assignee, no seen or ongoing. Only its
-- owner sees it, adds it, ticks it and takes the tick back. Nothing is deleted (a tick taken back clears done_at). Mirrored in
-- database-schema.md.

CREATE TABLE todos (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    owner_account_id    INTEGER NOT NULL REFERENCES accounts(id),
    text                TEXT NOT NULL,
    due_at              TIMESTAMPTZ,
    done_at             TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX todos_owner_idx ON todos (owner_account_id, done_at);
