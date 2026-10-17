-- 037_detective_rules.sql -- a reviewer's "this is fine" written down so it applies again (common/detective.py `Rule`).
--
-- A rule says: findings of this kind (`graph`) on this machine, involving this program / folder / drive (`kind`, `value`), are fine. It only LOWERS a
-- matching finding -- the finding is still recorded, with the rule named in its reasons -- so nothing is hidden. It is made only when the reviewer asks
-- for it while reviewing a case, shown on the Detective page, and can be taken back (`revoked_at`); a revoked rule is kept, like everything else.
-- Mirrored in database-schema.md.

CREATE TABLE detective_rules (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pc_id           INTEGER NOT NULL REFERENCES pcs(id),
    graph           TEXT NOT NULL,
    kind            TEXT NOT NULL CHECK (kind IN ('program', 'folder', 'drive')),
    value           TEXT NOT NULL,
    case_id         INTEGER REFERENCES detective_cases(id),
    made_by_account_id INTEGER REFERENCES accounts(id),
    made_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    revoked_by_account_id INTEGER REFERENCES accounts(id),
    revoked_at      TIMESTAMPTZ
);

CREATE UNIQUE INDEX detective_rules_live_idx ON detective_rules (pc_id, graph, kind, lower(value)) WHERE revoked_at IS NULL;
