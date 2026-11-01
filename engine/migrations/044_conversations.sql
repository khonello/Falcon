-- 044_conversations.sql -- an Admin's conversations without the Super User (the user, 29 Oct 2026; ENGINE-GAPS #17).
--
-- Version 1: an Admin talks to the other Admins and to whoever is signed in on a machine, and there is one group of every Admin once there are
-- two or more. No request to talk first (help requests are out of version 1): a conversation is only what was written in it. Separate from the
-- help-ping channels (message_channels), which stay for the Super User's level.
--
--   kind 'pair'    two people; `pair_key` ("<low id>:<high id>") makes writing to the same person reuse it
--   kind 'admins'  every active Admin: its members are read from the accounts at the time, so an Admin who joins is in it and one who leaves is not
--
-- Read times are kept per person (conversation_reads), for the unread counts and "seen". Nothing is deleted. Mirrored in database-schema.md.

CREATE TABLE conversations (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kind            TEXT NOT NULL CHECK (kind IN ('pair', 'admins')),
    pair_key        TEXT,
    created_by_account_id INTEGER REFERENCES accounts(id),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_message_at TIMESTAMPTZ
);

CREATE UNIQUE INDEX conversations_pair_idx ON conversations (pair_key) WHERE kind = 'pair';
CREATE UNIQUE INDEX conversations_admins_idx ON conversations (kind) WHERE kind = 'admins';

CREATE TABLE conversation_members (
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    account_id      INTEGER NOT NULL REFERENCES accounts(id),
    PRIMARY KEY (conversation_id, account_id)
);

CREATE TABLE conversation_messages (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    from_account_id INTEGER NOT NULL REFERENCES accounts(id),
    body            TEXT NOT NULL,
    sent_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX conversation_messages_idx ON conversation_messages (conversation_id, id DESC);

CREATE TABLE conversation_reads (
    conversation_id INTEGER NOT NULL REFERENCES conversations(id),
    account_id      INTEGER NOT NULL REFERENCES accounts(id),
    read_at         TIMESTAMPTZ NOT NULL,
    PRIMARY KEY (conversation_id, account_id)
);
