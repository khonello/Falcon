-- 048_licence_codes.sql -- a machine joins with a code from the licence that was bought, and nobody has to confirm it (the user, 2 Nov 2026).
--
-- A licence (bought, from the licence store) carries codes: admin codes and worker codes. During setup the person installing gives one; the
-- Engine checks it and the machine joins as what the code is for, at once, with no Admin typing a code shown on its screen. A code covers a
-- number of machines (seats); each machine that joins with it uses one. A code can expire or be withdrawn. Codes are kept only as a hash, like
-- a password: what is shown is the last four characters.
-- enrollments.licence_code_id: the code a machine joined with (NULL: it was confirmed by a person with its on-screen code, as before).
-- Mirrored in database-schema.md.

CREATE TABLE licences (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                    TEXT NOT NULL,
    reference               TEXT,                                   -- the store's own id for the licence, as it was bought
    imported_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    imported_by_account_id  INTEGER REFERENCES accounts(id)
);

CREATE TABLE licence_codes (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    licence_id      INTEGER NOT NULL REFERENCES licences(id),
    code_hash       TEXT NOT NULL UNIQUE,
    last4           TEXT NOT NULL,
    role            TEXT NOT NULL CHECK (role IN ('admin', 'worker')),
    seats           INTEGER NOT NULL CHECK (seats > 0),
    used            INTEGER NOT NULL DEFAULT 0 CHECK (used >= 0 AND used <= seats),
    department      TEXT,                                   -- the department a machine joining with it goes into, when the code says
    expires_at      TIMESTAMPTZ,
    revoked_at      TIMESTAMPTZ,
    revoked_by_account_id INTEGER REFERENCES accounts(id)
);

ALTER TABLE enrollments ADD COLUMN licence_code_id INTEGER REFERENCES licence_codes(id);
