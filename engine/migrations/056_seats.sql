-- 056_seats.sql -- machines knock and Admins give seats (docs/SEATS-AND-SETUP.md, decided with the user 14 Nov 2026).
--
-- seat_grants: what the store sold, kept as the store signed it (`envelope`), and checked again each time it is read: a row edited by
--              hand counts for nothing. A renewal is a new grant. Never edited or deleted.
-- knocks:      one row per installed PC (its install token, held only as a hash), with what it says about itself, kept up to date by each
--              knock. `waiting` until an Admin gives it a seat; `seated` once given (the key is handed over once, `delivered_at`); back to
--              `waiting` when the seat is taken back. No code, nothing typed.
-- seats:       who gave which machine a seat, when, and who took it back. A machine has at most one seat in use at a time.
-- Machines provisioned before seats existed are given a seat row here, so the count of seats in use is true from the start.
-- Mirrored in database-schema.md.

CREATE TABLE seat_grants (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    grant_id        TEXT NOT NULL UNIQUE,
    role            TEXT NOT NULL CHECK (role IN ('admin', 'worker')),
    seats           INTEGER NOT NULL CHECK (seats > 0),
    valid_from      TIMESTAMPTZ NOT NULL,
    valid_until     TIMESTAMPTZ NOT NULL,
    envelope        JSONB NOT NULL,                         -- {doc, kid, sig} exactly as the store signed it
    received_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE knocks (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    token_hash      TEXT NOT NULL UNIQUE,
    hostname        TEXT NOT NULL,
    os              TEXT,
    mac             TEXT,
    hardware_id     TEXT,
    signed_in_user  TEXT,
    peer            TEXT,
    status          TEXT NOT NULL DEFAULT 'waiting' CHECK (status IN ('waiting', 'seated')),
    pc_id           INTEGER REFERENCES pcs(id),
    delivered_at    TIMESTAMPTZ,                            -- the key went to the machine (once per seating)
    first_seen      TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen       TIMESTAMPTZ NOT NULL DEFAULT now(),
    knocks          INTEGER NOT NULL DEFAULT 1
);
CREATE INDEX knocks_waiting_idx ON knocks (last_seen) WHERE status = 'waiting';

CREATE TABLE seats (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pc_id               INTEGER NOT NULL REFERENCES pcs(id),
    role                TEXT NOT NULL CHECK (role IN ('admin', 'worker')),
    given_by_account_id INTEGER REFERENCES accounts(id),   -- NULL: given before seats existed, or by an Admin claim from the store
    given_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    taken_by_account_id INTEGER REFERENCES accounts(id),   -- NULL with taken_at set: taken back by the Engine (the end of a seat period)
    taken_at            TIMESTAMPTZ,
    taken_reason        TEXT
);
CREATE UNIQUE INDEX seats_one_per_pc ON seats (pc_id) WHERE taken_at IS NULL;

INSERT INTO seats (pc_id, role)
SELECT p.id, a.role FROM pcs p JOIN accounts a ON a.bound_pc_id = p.id
WHERE a.status = 'active' AND a.role IN ('admin', 'worker');

ALTER TABLE issues DROP CONSTRAINT issues_type_check;
ALTER TABLE issues ADD CONSTRAINT issues_type_check CHECK (type IN ('file', 'update', 'deviation', 'flow', 'offline', 'component', 'retention', 'seats'));
