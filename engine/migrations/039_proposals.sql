-- 039_proposals.sql -- what the features suggest to each other, for a person to accept or dismiss (the owner, 18 Oct 2026: "propose, never silently resolve").
--
-- One feature may weigh another's facts, but it may not change what another feature holds. When Detective sees that a folder keeps turning up in a case and is not restricted, or that a
-- flow's source machine is under an urgent case, or that a case was escalated, it writes a PROPOSAL here. Nothing happens until a person accepts it; accepting is audited, dismissing is
-- kept. Mirrored in database-schema.md.

CREATE TABLE proposals (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    kind                    TEXT NOT NULL CHECK (kind IN ('mark_folder', 'pause_flow', 'follow_up_task')),
    key                     TEXT NOT NULL,
    title                   TEXT NOT NULL,
    detail                  JSONB NOT NULL DEFAULT '{}',
    pc_id                   INTEGER REFERENCES pcs(id),
    department_id           INTEGER REFERENCES departments(id),
    case_id                 INTEGER REFERENCES detective_cases(id),
    flow_id                 INTEGER REFERENCES flows(id),
    state                   TEXT NOT NULL DEFAULT 'open' CHECK (state IN ('open', 'accepted', 'dismissed')),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_by_account_id   INTEGER REFERENCES accounts(id),
    decided_at              TIMESTAMPTZ,
    note                    TEXT
);

CREATE UNIQUE INDEX proposals_open_key_idx ON proposals (kind, key) WHERE state = 'open';
CREATE INDEX proposals_dept_idx ON proposals (department_id, state);
