-- 049_chat_files.sql -- a file sent in a conversation (ENGINE-GAPS #7; the user, 22-23 Oct and 2 Nov 2026).
--
-- Anyone in a conversation sends one file from their own machine, once, up to 100 MB; it arrives as a message with the file, and each person
-- in the conversation saves it to Downloads\From Falcon on their machine. Programs and scripts are refused (a script runs as a Custom Action,
-- where it is checked first). Sending something restricted is the consent of the person who restricted it for that one copy; anyone else's
-- file waits until that person agrees. The Engine holds the bytes (on its disk, not in the database) until they are saved, 7 days at most,
-- then drops them; this record stays.
--
--   chat_files.state   asked (waiting for the restriction's owner) | reading (the sender's machine is sending it) | held (ready to save) |
--                      refused (the owner said no, or the sender's machine could not read it) | expired (the bytes were dropped after 7 days)
--   chat_file_saves    each copy saved: on which machine, where, and its hash -- what Restricted and Detective read as a handed-over copy
-- Mirrored in database-schema.md.

CREATE TABLE chat_files (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id         INTEGER NOT NULL REFERENCES conversations(id),
    message_id              INTEGER REFERENCES conversation_messages(id),
    from_account_id         INTEGER NOT NULL REFERENCES accounts(id),
    from_pc_id              INTEGER NOT NULL REFERENCES pcs(id),
    source_path             TEXT NOT NULL,
    name                    TEXT NOT NULL,
    size_bytes              BIGINT,
    content_hash            TEXT,
    state                   TEXT NOT NULL CHECK (state IN ('asked', 'reading', 'held', 'refused', 'expired')),
    reason                  TEXT,
    restricted              JSONB,                                  -- what made it restricted and whose consent let it go, when it was
    consent_account_id      INTEGER REFERENCES accounts(id),        -- whose yes it waits for (state asked)
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    held_at                 TIMESTAMPTZ,
    expires_at              TIMESTAMPTZ,
    dropped_at              TIMESTAMPTZ
);

CREATE INDEX chat_files_conversation_idx ON chat_files (conversation_id, id);
CREATE INDEX chat_files_held_idx ON chat_files (expires_at) WHERE state = 'held';

CREATE TABLE chat_file_saves (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    chat_file_id            INTEGER NOT NULL REFERENCES chat_files(id),
    account_id              INTEGER NOT NULL REFERENCES accounts(id),
    pc_id                   INTEGER NOT NULL REFERENCES pcs(id),
    path                    TEXT,
    content_hash            TEXT,
    asked_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    saved_at                TIMESTAMPTZ
);

CREATE INDEX chat_file_saves_place_idx ON chat_file_saves (pc_id, lower(path));

ALTER TABLE conversation_messages ADD COLUMN chat_file_id INTEGER REFERENCES chat_files(id);
