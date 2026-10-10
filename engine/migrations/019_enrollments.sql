-- 019_enrollments.sql -- machines asking to be registered (ENGINE-GAPS #15).
--
-- A newly installed Worker finds the Engine and asks, before it has any key (`enroll.request`, one of the only
-- two requests accepted before the handshake). What it says about itself is a REQUEST, never a grant: it lands here as
-- `pending`, and a person confirms it (department, level) or refuses it. Nothing registers itself.
--
-- Pairing: the machine shows a short `code` on its own screen; whoever confirms types it, so a machine that is not
-- really in front of someone cannot finish. On a match the Engine creates the account + PC and the machine collects its
-- client id and key once, with the `token` only it holds (stored here as a hash).
-- Pending requests expire after 24 hours. Mirrored in database-schema.md 1.

CREATE TABLE enrollments (
    id                       INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code                     TEXT NOT NULL,
    token_hash               TEXT NOT NULL UNIQUE,
    hostname                 TEXT NOT NULL,
    os                       TEXT,
    mac                      TEXT,
    requested_department_id  INTEGER REFERENCES departments(id),
    requested_level          TEXT NOT NULL DEFAULT 'worker' CHECK (requested_level IN ('worker', 'admin')),
    peer                     TEXT,
    status                   TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'confirmed', 'refused', 'expired')),
    attempts                 INTEGER NOT NULL DEFAULT 0,
    created_at               TIMESTAMPTZ NOT NULL DEFAULT now(),
    expires_at               TIMESTAMPTZ NOT NULL,
    decided_by_account_id    INTEGER REFERENCES accounts(id),
    decided_at               TIMESTAMPTZ,
    refused_reason           TEXT,
    account_id               INTEGER REFERENCES accounts(id),
    pc_id                    INTEGER REFERENCES pcs(id),
    delivered_at             TIMESTAMPTZ
);

CREATE INDEX enrollments_pending_idx ON enrollments (created_at) WHERE status = 'pending';
