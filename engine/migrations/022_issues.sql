-- 022_issues.sql -- issues: the tickets an Admin works (ENGINE-CONCEPT-NEEDS WP2; docs/design/super-user-menu.md).
--
-- An issue is a thing that needs someone: a copy of a restricted file where it is not allowed, a machine whose update is stuck,
-- a machine that presented another name, a flow waiting for someone to agree, a machine that stopped checking in. The system
-- raises them from what it already records (resource violations, update attempts, the deviation log, flow consent, connections)
-- and resolves them when the cause goes away; a person can also resolve one by acting on it. A help request is not an issue: it
-- lives in Messages.
--
-- `owner_account_id` NULL means unassigned: any Admin of the department may take it, and the Super User when the department has
-- no Admin (`escalated_at` says it came up to them). `source_table/source_id` link an issue to what raised it, so the same cause
-- never raises two open issues. Nothing is deleted: a resolved issue stays, with who resolved it and how.
-- Mirrored in database-schema.md 14.

CREATE TABLE issues (
    id                     INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    code                   TEXT UNIQUE,
    type                   TEXT NOT NULL CHECK (type IN ('file', 'update', 'deviation', 'flow', 'offline')),
    severity               TEXT NOT NULL CHECK (severity IN ('critical', 'high', 'medium', 'low')),
    title                  TEXT NOT NULL,
    subject                TEXT NOT NULL DEFAULT '',
    pc_id                  INTEGER REFERENCES pcs(id),
    department_id          INTEGER REFERENCES departments(id),
    opened_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    owner_account_id       INTEGER REFERENCES accounts(id),
    target_hours           INTEGER NOT NULL DEFAULT 24,
    state                  TEXT NOT NULL DEFAULT 'open' CHECK (state IN ('open', 'waiting', 'resolved')),
    label                  TEXT,
    detail                 JSONB NOT NULL DEFAULT '{}'::jsonb,
    source_table           TEXT,
    source_id              INTEGER,
    escalated_at           TIMESTAMPTZ,
    resolved_at            TIMESTAMPTZ,
    resolved_by_account_id INTEGER REFERENCES accounts(id),
    resolution             TEXT,
    CONSTRAINT issues_resolved_pairing CHECK ((state = 'resolved') = (resolved_at IS NOT NULL))
);

-- one open issue per cause
CREATE UNIQUE INDEX issues_one_open_per_source ON issues (source_table, source_id)
    WHERE source_table IS NOT NULL AND state <> 'resolved';
CREATE INDEX issues_pc_idx ON issues (pc_id) WHERE state <> 'resolved';
CREATE INDEX issues_department_idx ON issues (department_id, state);

CREATE TABLE issue_log (
    id                INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    issue_id          INTEGER NOT NULL REFERENCES issues(id),
    at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    actor_account_id  INTEGER REFERENCES accounts(id),      -- NULL: the system
    kind              TEXT NOT NULL,
    text              TEXT NOT NULL
);

CREATE INDEX issue_log_issue_idx ON issue_log (issue_id, at);

-- A place a restricted file's content may be, with the reason a person gave: "Allow it here too" on a copy. The same content at
-- the same place is not reported again. (`mark_id` is filled once marks exist, WP3.)
CREATE TABLE restricted_allowances (
    id                INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pc_id             INTEGER NOT NULL REFERENCES pcs(id),
    path              TEXT NOT NULL,
    content_hash      TEXT,
    mark_id           INTEGER,
    reason            TEXT NOT NULL,
    by_account_id     INTEGER NOT NULL REFERENCES accounts(id),
    at                TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX restricted_allowances_pc_idx ON restricted_allowances (pc_id, content_hash);

-- A machine left out of the gate to the next version ("it can then be approved without it"), with the reason. WP7 reads this.
CREATE TABLE gate_exclusions (
    id                INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pc_id             INTEGER NOT NULL REFERENCES pcs(id),
    for_version       TEXT NOT NULL,
    reason            TEXT NOT NULL,
    by_account_id     INTEGER NOT NULL REFERENCES accounts(id),
    at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (pc_id, for_version)
);
