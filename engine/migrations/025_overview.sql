-- 025_overview.sql -- what the Overviews and the Reports page need (ENGINE-CONCEPT-NEEDS WP5).
--
-- A report now says where it came from: the machine, the department it counts against, and, for a report about an Admin, who.
-- The department is what decides who can take it (its Admins when the category is routed there, the Super User otherwise), so
-- the Engine records it when the report is written instead of working it out from the source each time it is read.
--
-- `su_decisions` is the Super User's answer to a decision that is theirs alone (keep waiting, note that it was expected): kept so
-- the same card does not come back at once. A decision that is acted on needs no row; its effect is its record.
--
-- `accounts.hours_limited` is the Super User limiting an Admin to working hours: traversal into a machine is refused outside them.
-- Mirrored in database-schema.md 15.

ALTER TABLE reports ADD COLUMN pc_id INTEGER REFERENCES pcs(id);
ALTER TABLE reports ADD COLUMN department_id INTEGER REFERENCES departments(id);
ALTER TABLE reports ADD COLUMN about_account_id INTEGER REFERENCES accounts(id);
CREATE INDEX reports_department_idx ON reports (department_id, generated_at DESC);

ALTER TABLE accounts ADD COLUMN hours_limited BOOLEAN NOT NULL DEFAULT FALSE;

CREATE TABLE su_decisions (
    id                INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    decision_key      TEXT NOT NULL,
    option_key        TEXT NOT NULL,
    note              TEXT,
    by_account_id     INTEGER NOT NULL REFERENCES accounts(id),
    at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    until_at          TIMESTAMPTZ
);
CREATE INDEX su_decisions_key_idx ON su_decisions (decision_key, at DESC);
