-- 035_detective.sql -- Detective: what a person seems to be trying to do, read from several things happening together (common/detective.py).
--
--   * `detective_cases`: one row per case (a hypothesis about intent on one machine, with the stage it has reached). A case is a record of a PATTERN
--     and its evidence, never a statement of cause; a person reviews it (explained / accepted / escalated / dismissed) and the review is kept.
--   * `detective_findings`: what each mini-graph concluded, with the evidence (the signals, in order) and what would make it innocent.
--   * `detective_devices`: how often a drive has been seen on a machine (a drive this machine uses all the time lowers a finding).
--   * `file_events.detail`: for an attribute change, which attributes it was (hidden, system, read-only), so "made hidden" can be told from the rest.
-- Cases are kept; nothing is deleted except by the 90-day retention job like the other history.
-- Mirrored in database-schema.md.

ALTER TABLE file_events ADD COLUMN detail JSONB;

CREATE TABLE detective_cases (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pc_id           INTEGER NOT NULL REFERENCES pcs(id),
    department_id   INTEGER REFERENCES departments(id),
    intent          TEXT NOT NULL,
    level           TEXT NOT NULL CHECK (level IN ('quiet', 'noted', 'case', 'urgent')),
    weight          REAL NOT NULL,
    stage_count     INTEGER NOT NULL DEFAULT 0,
    stage_name      TEXT,
    next_stage      TEXT,
    not_yet         TEXT,
    behaviours      TEXT[] NOT NULL DEFAULT '{}',
    headline        TEXT NOT NULL,
    story           JSONB NOT NULL DEFAULT '[]',
    status          TEXT NOT NULL DEFAULT 'open' CHECK (status IN ('open', 'explained', 'accepted', 'escalated', 'dismissed')),
    first_at        TIMESTAMPTZ NOT NULL,
    last_at         TIMESTAMPTZ NOT NULL,
    raised_at       TIMESTAMPTZ,
    reviewed_by_account_id INTEGER REFERENCES accounts(id),
    reviewed_at     TIMESTAMPTZ,
    note            TEXT
);

CREATE INDEX detective_cases_pc_idx ON detective_cases (pc_id, last_at DESC);
CREATE INDEX detective_cases_open_idx ON detective_cases (level, last_at DESC) WHERE status = 'open';

CREATE TABLE detective_findings (
    id          INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    case_id     INTEGER NOT NULL REFERENCES detective_cases(id),
    behaviour   TEXT NOT NULL,
    graph       TEXT NOT NULL,
    weight      REAL NOT NULL,
    at          TIMESTAMPTZ NOT NULL,
    summary     TEXT NOT NULL,
    innocent    TEXT,
    why         JSONB NOT NULL DEFAULT '[]',
    things      JSONB NOT NULL DEFAULT '[]',
    evidence    JSONB NOT NULL DEFAULT '[]'
);

CREATE INDEX detective_findings_case_idx ON detective_findings (case_id, at);

CREATE TABLE detective_devices (
    pc_id       INTEGER NOT NULL REFERENCES pcs(id),
    device      TEXT NOT NULL,
    uses        INTEGER NOT NULL DEFAULT 1,
    first_seen  TIMESTAMPTZ NOT NULL DEFAULT now(),
    last_seen   TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (pc_id, device)
);
