-- 027_rollout.sql -- the rollout gate (ENGINE-CONCEPT-NEEDS WP7).
--
-- `staged_versions`: a version that is ready and waits for the Super User to approve it. The packaging pipeline (deferred) and the Super User stage a
-- build the same way, through `updates.stage`; approving it ends its waiting. Nothing about a staged version reaches a machine.
--
-- `pc_version_log`: which version each machine ran, and since when -- written when a machine says it runs a version it did not run before. It is what
-- "machines on the current version, day by day" is added up from.
--
-- `pc_version_status.last_error`: what the last failed attempt said went wrong (a file in use, an update share that could not be reached).
--
-- A machine left out of the gate keeps its `gate_exclusions` row (022) with `for_version = 'next'` until that version is approved; approving converts the
-- row to the version, so it stays on record who was left out of which approval, and why.
-- Mirrored in database-schema.md 17.

CREATE TABLE staged_versions (
    version_string        TEXT PRIMARY KEY,
    note                  TEXT NOT NULL DEFAULT '',
    staged_by_account_id  INTEGER NOT NULL REFERENCES accounts(id),
    staged_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    approved_at           TIMESTAMPTZ
);

CREATE TABLE pc_version_log (
    id         INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pc_id      INTEGER NOT NULL REFERENCES pcs(id),
    version    TEXT NOT NULL,
    at         TIMESTAMPTZ NOT NULL DEFAULT now()
);
CREATE INDEX pc_version_log_idx ON pc_version_log (pc_id, at DESC, id DESC);

ALTER TABLE pc_version_status ADD COLUMN last_error TEXT;

INSERT INTO pc_version_log (pc_id, version, at)
SELECT id, agent_version, COALESCE(agent_started_at, now()) FROM pcs WHERE agent_version IS NOT NULL;
