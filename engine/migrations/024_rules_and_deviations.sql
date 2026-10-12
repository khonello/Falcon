-- 024_rules_and_deviations.sql -- the standard the organisation is measured against, and what was measured (ENGINE-CONCEPT-NEEDS WP4;
-- docs/design/super-user-menu.md, Accountability and Rules).
--
-- A **rule** is a pattern: what should happen. Three shapes: *never* (the first time it happens it is a deviation), *follow* (after one
-- thing happens another must follow within a time) and *limit* (a count that must not go over a line in a period). The Super User writes
-- them for the whole organisation; the ones Falcon always enforces are built in and locked (B-1 .. B-4), listed so every deviation has a
-- rule to point to. A **deviation** is a departure from a rule that someone can be asked about: it carries the rule *as it was* when it
-- happened (`rule_snapshot`), who or what it concerns, what was expected and what happened, and an outcome a person gives it. The system
-- never states a cause: it shows evidence; an explanation is only ever a person's note.
--
-- A *follow* rule is watched: when its trigger happens a `rule_watch` is opened, due `within` minutes later; if what must follow has not
-- happened by then, a deviation is recorded. Nothing is deleted: switching a rule off stops new deviations, and old ones stay.
-- The stored shape of a rule is the `spec` JSON below (the shape the concept's rule builder fills in); see engine/console/rules.py.
-- Mirrored in database-schema.md 15.

CREATE TABLE rules (
    id                    INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code                  TEXT NOT NULL UNIQUE,
    builtin               BOOLEAN NOT NULL DEFAULT false,
    name                  TEXT NOT NULL,
    shape                 TEXT NOT NULL CHECK (shape IN ('never', 'follow', 'limit')),
    spec                  JSONB NOT NULL,
    enabled               BOOLEAN NOT NULL DEFAULT true,
    created_by_account_id INTEGER REFERENCES accounts(id),
    created_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    updated_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE deviations (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code                    TEXT UNIQUE,
    rule_id                 INTEGER NOT NULL REFERENCES rules(id),
    rule_snapshot           JSONB NOT NULL,
    severity                TEXT NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    kind                    TEXT NOT NULL CHECK (kind IN ('pc', 'worker', 'admin', 'dept')),
    subject_account_id      INTEGER REFERENCES accounts(id),
    subject_pc_id           INTEGER REFERENCES pcs(id),
    subject_department_id   INTEGER REFERENCES departments(id),
    department_id           INTEGER REFERENCES departments(id),
    pc_id                   INTEGER REFERENCES pcs(id),
    at                      TIMESTAMPTZ NOT NULL DEFAULT now(),
    short                   TEXT NOT NULL,
    expected                TEXT NOT NULL,
    happened                TEXT NOT NULL,
    value                   DOUBLE PRECISION,
    detail                  JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_key              TEXT,
    outcome                 TEXT NOT NULL DEFAULT 'open' CHECK (outcome IN ('open', 'explained', 'accepted', 'escalated', 'dismissed')),
    note                    TEXT,
    outcome_by_account_id   INTEGER REFERENCES accounts(id),
    outcome_at              TIMESTAMPTZ
);

-- the same departure is never recorded twice
CREATE UNIQUE INDEX deviations_one_per_source ON deviations (rule_id, source_key) WHERE source_key IS NOT NULL;
CREATE INDEX deviations_at_idx ON deviations (at DESC);
CREATE INDEX deviations_rule_idx ON deviations (rule_id, at DESC);

CREATE TABLE rule_watches (
    id               INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    rule_id          INTEGER NOT NULL REFERENCES rules(id),
    opened_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
    due_at           TIMESTAMPTZ NOT NULL,
    expect           TEXT NOT NULL,
    target_table     TEXT NOT NULL,
    target_id        INTEGER NOT NULL,
    subject          JSONB NOT NULL,
    state            TEXT NOT NULL DEFAULT 'open' CHECK (state IN ('open', 'kept', 'broken')),
    closed_at        TIMESTAMPTZ,
    deviation_id     INTEGER REFERENCES deviations(id),
    UNIQUE (rule_id, target_table, target_id, expect)
);

CREATE INDEX rule_watches_open_idx ON rule_watches (due_at) WHERE state = 'open';

-- What Falcon always enforces, listed locked so no deviation points at nothing.
INSERT INTO rules (code, builtin, name, shape, spec) VALUES
 ('B-1', true, 'Restricted files stay where they are', 'never',
  '{"trigger": "file", "who": "everyone", "depts": "all", "severity": "high", "resp": {"report": true, "admin": true}}'),
 ('B-2', true, 'One session on a machine at a time', 'never',
  '{"trigger": "second", "who": "everyone", "depts": "all", "severity": "medium", "resp": {"report": false, "admin": false}}'),
 ('B-3', true, 'Machines run the approved version', 'follow',
  '{"trigger": "version", "expect": "updated", "within": 2880, "who": "machines", "depts": "all", "severity": "high", "resp": {"report": true, "admin": true}}'),
 ('B-4', true, 'A machine''s name matches what it was registered with', 'never',
  '{"trigger": "cert", "who": "machines", "depts": "all", "severity": "medium", "resp": {"report": true, "admin": true}}');
