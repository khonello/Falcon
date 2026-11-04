-- 054_console_calls.sql -- what the console's pages call (ENGINE-GAPS #23, 4 Nov 2026).
--
-- * talk_requests: a person at a machine asks to talk; one Admin accepts or closes it (engine/resource/talk.py). One open request per person.
-- * conversations: a small group of named people (kind 'group', with a title).
-- * event_skips: one scheduled run of a rule skipped by hand. Taking a skip back or using it is a mark on the row, nothing is deleted.
-- * action_executions.started_by_account_id: who ran it by hand (none: a rule).
-- * flows.paused_at: when a source stopped, for "one source of several gone".
-- * event_actions.timeout_seconds, flow_destinations.note: what the rule and flow drawers send.
-- Mirrored in database-schema.md 16.
CREATE TABLE talk_requests (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    from_account_id         INTEGER NOT NULL REFERENCES accounts(id),
    pc_id                   INTEGER REFERENCES pcs(id),
    line                    TEXT NOT NULL,
    sent_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    state                   TEXT NOT NULL DEFAULT 'open' CHECK (state IN ('open', 'accepted', 'closed')),
    decided_by_account_id   INTEGER REFERENCES accounts(id),
    decided_at              TIMESTAMPTZ,
    why                     TEXT,
    conversation_id         INTEGER REFERENCES conversations(id)
);
CREATE UNIQUE INDEX talk_requests_one_open ON talk_requests (from_account_id) WHERE state = 'open';

ALTER TABLE conversations DROP CONSTRAINT conversations_kind_check;
ALTER TABLE conversations ADD CONSTRAINT conversations_kind_check CHECK (kind IN ('pair', 'admins', 'group'));
ALTER TABLE conversations ADD COLUMN title TEXT;

CREATE TABLE event_skips (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_id                INTEGER NOT NULL REFERENCES event_definitions(id),
    at                      TIMESTAMPTZ NOT NULL,
    by_account_id           INTEGER NOT NULL REFERENCES accounts(id),
    made_at                 TIMESTAMPTZ NOT NULL DEFAULT now(),
    used_at                 TIMESTAMPTZ,
    undone_at               TIMESTAMPTZ
);
CREATE UNIQUE INDEX event_skips_one ON event_skips (event_id, at) WHERE undone_at IS NULL;

ALTER TABLE action_executions ADD COLUMN started_by_account_id INTEGER REFERENCES accounts(id);
ALTER TABLE flows ADD COLUMN paused_at TIMESTAMPTZ;
ALTER TABLE event_actions ADD COLUMN timeout_seconds INTEGER;      -- this rule's limit for this action ("Gets up to"); NULL: the action's own
ALTER TABLE flow_destinations ADD COLUMN note TEXT;                 -- a line for whoever is asked to pick the folder
