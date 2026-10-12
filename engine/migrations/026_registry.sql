-- 026_registry.sql -- the Registry's blocked addresses (ENGINE-CONCEPT-NEEDS WP6).
--
-- An address the Super User has blocked is refused at the door: the connection is closed before the challenge, and the try is recorded
-- like any refused connection (`auth.failed`, reason "address blocked"), so the Registry still shows that someone keeps trying.
-- Nothing is deleted: lifting a block sets `lifted_at`; blocking it again opens a new row.
-- Mirrored in database-schema.md 16.

CREATE TABLE blocked_addresses (
    id                INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    address           TEXT NOT NULL,
    reason            TEXT NOT NULL DEFAULT '',
    by_account_id     INTEGER NOT NULL REFERENCES accounts(id),
    at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    lifted_at         TIMESTAMPTZ,
    lifted_by_account_id INTEGER REFERENCES accounts(id)
);
CREATE UNIQUE INDEX blocked_addresses_open_idx ON blocked_addresses (address) WHERE lifted_at IS NULL;
