-- 057_admin_claims.sql -- an Admin's PC comes in with a claim the store signed (docs/SEATS-AND-SETUP.md section 5, STORE-CONTRACT.md).
--
-- admin_claims: every claim this Engine accepted, kept as the store signed it. A claim works once: its claim_id is unique, so the same
--               claim knocking again (copied, replayed) is refused. Never edited or deleted.
-- Mirrored in database-schema.md.

CREATE TABLE admin_claims (
    claim_id        TEXT PRIMARY KEY,
    member_email    TEXT NOT NULL,                          -- who signed in to the store and claimed the seat
    knock_id        INTEGER NOT NULL REFERENCES knocks(id),
    pc_id           INTEGER REFERENCES pcs(id),             -- set once the PC is in
    envelope        JSONB NOT NULL,                         -- {doc, kid, sig} exactly as the store signed it
    used_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
