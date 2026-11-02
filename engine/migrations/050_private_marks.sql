-- 050_private_marks.sql -- protection gets three tags: watch, private, restricted (ENGINE-GAPS #3; the user, 21 Oct and 2 Nov 2026).
--
-- A mark carries exactly one:
--   watch       free to go and to open; what happens to it is noted (its file events), nothing is stopped or caught
--   private     only the people the owner names may open the file or folder, or run the program; anyone else is refused BY WINDOWS ITSELF
--               (the Worker sets the item's permissions, keeping the original to put back), and each refusal is noted (Windows' own
--               audit of failed opens, read by the Worker). Whether the machine's system account (backup, antivirus) may read it is the
--               owner's choice per item. Nobody can ask to be added; only the owner changes who is named.
--   restricted  it never leaves its place; a copy elsewhere is caught (every mark before this migration is one).
-- resource_marks.applied: what the machine last said it did for a private mark ({ok, at, granted, missing, error}).
-- pcs.windows_user: who was last signed in on the machine, as Windows names them -- how a named person is found on another machine.
-- Mirrored in database-schema.md.

ALTER TABLE resource_marks ADD COLUMN protection TEXT NOT NULL DEFAULT 'restricted' CHECK (protection IN ('watch', 'private', 'restricted'));
ALTER TABLE resource_marks ADD COLUMN allow_system BOOLEAN NOT NULL DEFAULT TRUE;
ALTER TABLE resource_marks ADD COLUMN applied JSONB;

CREATE TABLE resource_mark_readers (
    mark_id     INTEGER NOT NULL REFERENCES resource_marks(id),
    account_id  INTEGER NOT NULL REFERENCES accounts(id),
    added_at    TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (mark_id, account_id)
);

CREATE TABLE private_refusals (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    mark_id     INTEGER REFERENCES resource_marks(id),
    pc_id       INTEGER NOT NULL REFERENCES pcs(id),
    who         TEXT,                                   -- the Windows account that was refused, as Windows named it
    account_id  INTEGER REFERENCES accounts(id),        -- that person's Falcon account, when known
    process     TEXT,
    path        TEXT NOT NULL,
    at          TIMESTAMPTZ NOT NULL,
    reported_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX private_refusals_mark_idx ON private_refusals (mark_id, at DESC);

ALTER TABLE pcs ADD COLUMN windows_user TEXT;
