-- 038_flow_restricted_consent.sql -- a flow may carry something restricted only with the consent of whoever owns the restriction (the owner, 18 Oct 2026).
--
-- By default a flow never touches a restricted file or folder. When one is met (when the flow is made, or later in its ordinary running) the flow is PAUSED and the owner
-- of the restriction is asked: the person who marked it (or the Super User), or for a tier with no mark the Super User / the department's Admin. A consent is for one flow and
-- one thing (a mark, or a tier), can expire, and can be taken back; each use is on the audit trail. Consenting also makes the flow's destination folders a place that content
-- may be (so Restricted does not raise the copies there as violations), until the consent is taken back.
-- Mirrored in database-schema.md.

CREATE TABLE flow_restricted_consents (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    flow_id                 INTEGER NOT NULL REFERENCES flows(id),
    mark_id                 INTEGER REFERENCES resource_marks(id),
    tag                     TEXT CHECK (tag IN ('restricted', 'admin')),
    scope_department_id     INTEGER REFERENCES departments(id),
    name                    TEXT NOT NULL,
    sample_path             TEXT,
    state                   TEXT NOT NULL DEFAULT 'asked' CHECK (state IN ('asked', 'granted', 'declined', 'revoked')),
    asked_at                TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_by_account_id   INTEGER REFERENCES accounts(id),
    decided_at              TIMESTAMPTZ,
    expires_at              TIMESTAMPTZ,
    note                    TEXT,
    issue_id                INTEGER,
    CHECK ((mark_id IS NULL) <> (tag IS NULL))
);

CREATE UNIQUE INDEX flow_restricted_live_mark_idx ON flow_restricted_consents (flow_id, mark_id) WHERE mark_id IS NOT NULL AND state IN ('asked', 'granted');
CREATE UNIQUE INDEX flow_restricted_live_tag_idx ON flow_restricted_consents (flow_id, tag, COALESCE(scope_department_id, 0)) WHERE tag IS NOT NULL AND state IN ('asked', 'granted');

-- A place that restricted content is allowed: now also a whole folder (what a consented flow writes into), tied to the consent, and taken away when it is revoked.
ALTER TABLE restricted_allowances ADD COLUMN folder BOOLEAN NOT NULL DEFAULT FALSE;
ALTER TABLE restricted_allowances ADD COLUMN consent_id INTEGER REFERENCES flow_restricted_consents(id);
ALTER TABLE restricted_allowances ADD COLUMN revoked_at TIMESTAMPTZ;
