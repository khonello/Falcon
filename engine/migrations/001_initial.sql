-- 001_initial.sql -- Falcon Engine schema v1, transcribed from database-schema.md.
--
-- PostgreSQL adaptations of the doc's generic types:
--   INTEGER PK      -> INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY
--   TIMESTAMP       -> TIMESTAMPTZ (always UTC-aware)
--   serialized JSON -> JSONB
--
-- Rules the doc places in the *application layer* (not expressible as constraints) are marked
-- "APP:" so they are easy to grep when implementing the data-access layer.
--
-- Section 13 at the bottom holds additions the schema doc does not model but the design docs
-- require (client credentials, system alerts, assistance availability). They are mirrored in
-- database-schema.md 13.

BEGIN;

-- ============================================================================================
-- 1. Identity & Hierarchy
-- ============================================================================================

CREATE TABLE departments (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    name                    TEXT NOT NULL UNIQUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    created_by_account_id   INTEGER  -- FK added below (circular with accounts). APP: super_user only
);

CREATE TABLE pcs (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    hostname        TEXT NOT NULL,
    department_id   INTEGER REFERENCES departments(id),
    pc_type         TEXT NOT NULL CHECK (pc_type IN ('super_user_workstation', 'admin_workstation', 'client_pc')),
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE accounts (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    role                TEXT NOT NULL CHECK (role IN ('super_user', 'admin', 'worker')),
    department_id       INTEGER REFERENCES departments(id),   -- NULL only for super_user
    bound_pc_id         INTEGER UNIQUE REFERENCES pcs(id),    -- one account <-> one PC
    self_display_name   TEXT,
    status              TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'offboarded')),
    offboarded_at       TIMESTAMPTZ,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT accounts_department_required CHECK (role = 'super_user' OR department_id IS NOT NULL)
);

ALTER TABLE departments
    ADD CONSTRAINT departments_created_by_fk FOREIGN KEY (created_by_account_id) REFERENCES accounts(id);

-- Display Names: non-propagation is a QUERY rule -- always filter by namer_account_id = viewer.
CREATE TABLE display_name_grants (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    namer_account_id    INTEGER NOT NULL REFERENCES accounts(id),
    named_account_id    INTEGER NOT NULL REFERENCES accounts(id),
    label               TEXT NOT NULL,
    created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (namer_account_id, named_account_id)
);

-- ============================================================================================
-- 2. Traversal & Sessions
-- ============================================================================================

CREATE TABLE sessions (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pc_id                   INTEGER NOT NULL REFERENCES pcs(id),
    occupant_account_id     INTEGER NOT NULL REFERENCES accounts(id),
    occupied_via            TEXT NOT NULL CHECK (occupied_via IN ('native', 'traversal', 'assisted_access')),
    entered_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    deadline_at             TIMESTAMPTZ,            -- NULL only for native
    extended_count          INTEGER NOT NULL DEFAULT 0,
    un_evictable            BOOLEAN NOT NULL DEFAULT FALSE,   -- APP: TRUE iff occupant is super_user
    ended_at                TIMESTAMPTZ,
    ended_reason            TEXT CHECK (ended_reason IN ('voluntary', 'superior_ended', 'deadline_expired', 'network_drop_deadline_expired')),
    CONSTRAINT sessions_deadline_required CHECK (occupied_via = 'native' OR deadline_at IS NOT NULL),
    CONSTRAINT sessions_ended_reason_pairing CHECK ((ended_at IS NULL) = (ended_reason IS NULL))
);

-- THE mechanism behind "traversal only begins when the destination is idle".
CREATE UNIQUE INDEX one_active_session_per_pc ON sessions (pc_id) WHERE ended_at IS NULL;

CREATE TABLE assisted_access_requests (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    requester_account_id    INTEGER NOT NULL REFERENCES accounts(id),   -- APP: role = admin
    target_department_id    INTEGER REFERENCES departments(id),
    helper_account_id       INTEGER REFERENCES accounts(id),
    entry_path              TEXT NOT NULL CHECK (entry_path IN ('requester_initiated', 'helper_broadcast')),
    matched_at              TIMESTAMPTZ,            -- NULL = went unmatched, never retried
    resulting_session_id    INTEGER REFERENCES sessions(id),
    access_ceiling          JSONB NOT NULL,
    access_narrowing        JSONB,                  -- APP: may only narrow the ceiling
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================================
-- 3. Global File Index
-- ============================================================================================

CREATE TABLE file_index (
    id                                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pc_id                               INTEGER NOT NULL REFERENCES pcs(id),
    path                                TEXT NOT NULL,
    filename                            TEXT NOT NULL,   -- denormalized: name-first collision checks
    content_hash                        TEXT,
    resource_tag                        TEXT CHECK (resource_tag IN ('admin', 'restricted', 'worker_dept', 'common')),
    resource_tag_scope_department_id    INTEGER REFERENCES departments(id),
    indexed_via                         TEXT NOT NULL CHECK (indexed_via IN ('event', 'idle_sweep')),
    last_seen_at                        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (pc_id, path),
    CONSTRAINT file_index_worker_dept_scope CHECK (resource_tag IS DISTINCT FROM 'worker_dept' OR resource_tag_scope_department_id IS NOT NULL)
);

CREATE INDEX file_index_filename_idx ON file_index (filename);
CREATE INDEX file_index_content_hash_idx ON file_index (content_hash) WHERE content_hash IS NOT NULL;
CREATE INDEX file_index_resource_tag_idx ON file_index (resource_tag) WHERE resource_tag IS NOT NULL;

-- ============================================================================================
-- 4. Task
-- ============================================================================================

CREATE TABLE tasks (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    assigner_account_id     INTEGER NOT NULL REFERENCES accounts(id),
    assignee_account_id     INTEGER NOT NULL REFERENCES accounts(id),
    description_raw         TEXT NOT NULL,
    status                  TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'in_progress', 'completed')),
    verification_mode       TEXT NOT NULL CHECK (verification_mode IN ('stack', 'none')),  -- APP: 'none' only by explicit confirmation
    soft_deadline_at        TIMESTAMPTZ,
    final_deadline_at       TIMESTAMPTZ,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at              TIMESTAMPTZ,
    completed_at            TIMESTAMPTZ             -- set only by manual_verifications
);

CREATE INDEX tasks_assignee_idx ON tasks (assignee_account_id) WHERE status <> 'completed';

CREATE TABLE verification_items (
    id                                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_id                             INTEGER NOT NULL REFERENCES tasks(id),
    sequence                            INTEGER NOT NULL,
    target_type                         TEXT NOT NULL CHECK (target_type IN ('file', 'program')),
    intent                              TEXT NOT NULL,
    file_index_id                       INTEGER REFERENCES file_index(id),
    proposed_filename                   TEXT,
    proposed_path                       TEXT,
    linked_file_verification_item_id    INTEGER REFERENCES verification_items(id),
    program_name                        TEXT,
    status                              TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'passed', 'failed')),
    populated_by                        TEXT NOT NULL CHECK (populated_by IN ('llm', 'manual')),
    CONSTRAINT verification_items_intent_by_target CHECK (
        (target_type = 'file' AND intent IN ('create', 'update', 'exists'))
        OR (target_type = 'program' AND intent IN ('used', 'used_with_file', 'installed_available', 'closed_not_running'))
    ),
    CONSTRAINT verification_items_used_with_file_link CHECK (intent <> 'used_with_file' OR linked_file_verification_item_id IS NOT NULL),
    UNIQUE (task_id, sequence)
);

CREATE TABLE expectations (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    verification_item_id    INTEGER NOT NULL REFERENCES verification_items(id),
    signal_type             TEXT NOT NULL,
    observed_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    value                   JSONB
);

CREATE INDEX expectations_item_idx ON expectations (verification_item_id, observed_at DESC);

CREATE TABLE manual_verifications (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    task_id                 INTEGER NOT NULL UNIQUE REFERENCES tasks(id),
    verified_by_account_id  INTEGER NOT NULL REFERENCES accounts(id),   -- APP: must equal tasks.assigner_account_id
    outcome                 TEXT NOT NULL CHECK (outcome IN ('complete', 'incomplete')),
    verified_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================================
-- 5. Flow
-- ============================================================================================

CREATE TABLE flows (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_by_account_id   INTEGER NOT NULL REFERENCES accounts(id),
    source_pc_id            INTEGER NOT NULL REFERENCES pcs(id),
    source_path             TEXT NOT NULL,
    status                  TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active', 'paused', 'inactive')),
    pause_reason            TEXT,
    consent_status          TEXT NOT NULL CHECK (consent_status IN ('not_required', 'pending', 'granted')),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX flows_source_pc_idx ON flows (source_pc_id) WHERE status = 'active';

CREATE TABLE flow_stages (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    flow_id         INTEGER NOT NULL REFERENCES flows(id),
    parent_stage_id INTEGER REFERENCES flow_stages(id),
    stage_type      TEXT NOT NULL CHECK (stage_type IN ('branch', 'transformation', 'categorization')),
    config          JSONB
);

CREATE TABLE flow_destinations (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    flow_id                 INTEGER NOT NULL REFERENCES flows(id),
    parent_stage_id         INTEGER REFERENCES flow_stages(id),
    destination_pc_id       INTEGER REFERENCES pcs(id),     -- NULL = remote storage
    destination_path        TEXT NOT NULL,
    owner_account_id        INTEGER NOT NULL REFERENCES accounts(id),
    pre_flight_check_status TEXT NOT NULL CHECK (pre_flight_check_status IN ('passed', 'collision_pending', 'cycle_pending'))
);

CREATE TABLE flow_sync_log (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    flow_destination_id     INTEGER NOT NULL REFERENCES flow_destinations(id),
    content_hash            TEXT NOT NULL,
    written_by              TEXT NOT NULL CHECK (written_by IN ('flow_sync', 'external')),
    written_by_account_id   INTEGER REFERENCES accounts(id),
    conflict_resolved       BOOLEAN NOT NULL DEFAULT FALSE,
    occurred_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX flow_sync_log_destination_idx ON flow_sync_log (flow_destination_id, occurred_at DESC);

-- ============================================================================================
-- 8. Reports & Routing  (before 6 -- resource_violations references reports)
-- ============================================================================================

CREATE TABLE reports (
    id              INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category        TEXT NOT NULL,
    source_table    TEXT NOT NULL,          -- polymorphic: APP validates
    source_id       INTEGER NOT NULL,
    generated_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX reports_category_idx ON reports (category, generated_at DESC);

CREATE TABLE report_routing_config (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    category                TEXT NOT NULL,
    routed_department_id    INTEGER NOT NULL REFERENCES departments(id),
    configured_by_account_id INTEGER NOT NULL REFERENCES accounts(id),  -- APP: super_user only
    configured_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (category, routed_department_id)
);

-- Super-User-only View. No category column: structurally incapable of being a Report.
CREATE TABLE report_addressed_views (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    report_id               INTEGER NOT NULL REFERENCES reports(id),
    addressed_by_account_id INTEGER NOT NULL REFERENCES accounts(id),
    addressed_at            TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================================
-- 6. Resource
-- ============================================================================================

CREATE TABLE resource_violations (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    file_index_id           INTEGER NOT NULL REFERENCES file_index(id),   -- only THIS file is ignored
    expected_tag            TEXT NOT NULL,
    found_on_pc_id          INTEGER NOT NULL REFERENCES pcs(id),
    detected_via            TEXT NOT NULL CHECK (detected_via IN ('event', 'polling_fallback')),
    surfaced_to_account_id  INTEGER NOT NULL REFERENCES accounts(id),
    resolved_at             TIMESTAMPTZ,
    report_id               INTEGER REFERENCES reports(id),
    detected_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================================
-- 7. Assistance (Ping, Message Channel, Listeners)
-- ============================================================================================

CREATE TABLE pings (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    sender_account_id   INTEGER NOT NULL REFERENCES accounts(id),
    receiver_account_id INTEGER NOT NULL REFERENCES accounts(id),   -- APP: sender's direct superior
    sent_at             TIMESTAMPTZ NOT NULL DEFAULT now(),
    addressed_at        TIMESTAMPTZ                                  -- NULL = pulsing; repeatable, no lock
);

CREATE INDEX pings_unaddressed_idx ON pings (receiver_account_id) WHERE addressed_at IS NULL;

CREATE TABLE message_channels (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    opened_via_ping_id      INTEGER NOT NULL REFERENCES pings(id),
    initiator_account_id    INTEGER NOT NULL REFERENCES accounts(id),
    superior_account_id     INTEGER NOT NULL REFERENCES accounts(id),   -- closing authority, always
    turn                    TEXT NOT NULL CHECK (turn IN ('sender', 'superior')),   -- the lock
    closed_at               TIMESTAMPTZ,                                -- APP: set only by superior
    opened_at               TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE messages (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    message_channel_id  INTEGER NOT NULL REFERENCES message_channels(id),
    sender_account_id   INTEGER NOT NULL REFERENCES accounts(id),
    body                TEXT NOT NULL,
    sent_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX messages_channel_idx ON messages (message_channel_id, sent_at);

-- Visibility is a QUERY rule: "listeners I can see" filters added_by_account_id = requester.
CREATE TABLE listeners (
    id                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    message_channel_id  INTEGER NOT NULL REFERENCES message_channels(id),
    listener_account_id INTEGER NOT NULL REFERENCES accounts(id),   -- APP: role = admin
    added_by_account_id INTEGER NOT NULL REFERENCES accounts(id),
    added_at            TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (message_channel_id, listener_account_id)                -- dedup; second add is a no-op
);

-- ============================================================================================
-- 9. Control, Events, Monitoring & Actions
-- ============================================================================================

CREATE TABLE event_definitions (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_by_account_id   INTEGER NOT NULL REFERENCES accounts(id),   -- APP: role = admin
    condition_type          TEXT NOT NULL CHECK (condition_type IN ('native_pushed', 'polled')),
    condition_spec          JSONB NOT NULL,
    enabled                 BOOLEAN NOT NULL DEFAULT TRUE,
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE actions (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_by_account_id   INTEGER NOT NULL REFERENCES accounts(id),   -- APP: role = admin
    action_kind             TEXT NOT NULL CHECK (action_kind IN ('control', 'monitoring', 'custom')),
    builtin_type            TEXT,
    custom_script           TEXT,
    custom_script_language  TEXT CHECK (custom_script_language IN ('python', 'powershell')),
    timeout_seconds         INTEGER NOT NULL CHECK (timeout_seconds > 0),
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT actions_custom_shape CHECK (
        (action_kind = 'custom' AND custom_script IS NOT NULL AND custom_script_language IS NOT NULL AND builtin_type IS NULL)
        OR (action_kind <> 'custom' AND builtin_type IS NOT NULL AND custom_script IS NULL AND custom_script_language IS NULL)
    )
);

CREATE TABLE event_actions (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    event_definition_id     INTEGER NOT NULL REFERENCES event_definitions(id),
    action_id               INTEGER NOT NULL REFERENCES actions(id),
    display_sequence        INTEGER NOT NULL,       -- display only, never a data dependency
    UNIQUE (event_definition_id, action_id)
);

CREATE TABLE action_executions (
    id                                  INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    action_id                           INTEGER NOT NULL REFERENCES actions(id),
    triggered_by_event_definition_id    INTEGER REFERENCES event_definitions(id),
    target_pc_id                        INTEGER NOT NULL REFERENCES pcs(id),
    status                              TEXT NOT NULL DEFAULT 'pending' CHECK (status IN ('pending', 'success', 'failed', 'terminated')),
    terminated_reason                   TEXT CHECK (terminated_reason IN ('timeout', 'manual')),
    output_log_path                     TEXT,
    started_at                          TIMESTAMPTZ NOT NULL DEFAULT now(),
    ended_at                            TIMESTAMPTZ,
    CONSTRAINT action_executions_terminated_reason CHECK ((status = 'terminated') = (terminated_reason IS NOT NULL))
);

CREATE INDEX action_executions_live_idx ON action_executions (started_at DESC) WHERE status = 'pending';

-- ============================================================================================
-- 10. Audit Trail
-- ============================================================================================

CREATE TABLE audit_log (
    id                  BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    actor_account_id    INTEGER REFERENCES accounts(id),    -- NULL = system-initiated
    action_type         TEXT NOT NULL,
    target_type         TEXT,
    target_id           TEXT,                               -- polymorphic; TEXT so client_ids fit too
    detail              JSONB,
    occurred_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- The retention purge (the ONE hard delete in the system) scans this.
CREATE INDEX audit_log_occurred_idx ON audit_log (occurred_at);

CREATE TABLE deviation_log (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    expectation             TEXT NOT NULL,
    observed_account_id     INTEGER REFERENCES accounts(id),
    observed_pc_id          INTEGER REFERENCES pcs(id),
    detail                  JSONB,
    surfaced_to_account_id  INTEGER NOT NULL REFERENCES accounts(id),   -- never silently tolerated
    resolved_at             TIMESTAMPTZ,
    detected_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- ============================================================================================
-- 11. Update & Deployment
-- ============================================================================================

CREATE TABLE versions (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    version_string          TEXT NOT NULL UNIQUE,
    approved_by_account_id  INTEGER NOT NULL REFERENCES accounts(id),   -- APP: super_user; hard gate on approval
    approved_at             TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE pc_version_status (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    pc_id                   INTEGER NOT NULL UNIQUE REFERENCES pcs(id),
    current_version_id      INTEGER NOT NULL REFERENCES versions(id),
    target_version_id       INTEGER REFERENCES versions(id),
    last_attempt_at         TIMESTAMPTZ,
    attempt_failure_count   INTEGER NOT NULL DEFAULT 0,
    escalated_at            TIMESTAMPTZ
);

-- ============================================================================================
-- 13. Additions required by the design docs but not modelled in database-schema.md v1
--     (mirrored in database-schema.md 13)
-- ============================================================================================

-- Auth provisioning (spec 8.2): each client is issued a derived key for its client_id. The
-- client_id identifies the PC (Identity Model: one account <-> one PC), so it lives on pcs.
ALTER TABLE pcs ADD COLUMN client_id TEXT UNIQUE;

-- Assisted Access "opted in as reachable for assistance" (Hierarchy -> Two Entry Paths).
ALTER TABLE accounts ADD COLUMN assistance_available BOOLEAN NOT NULL DEFAULT FALSE;

-- System Alerts & Announcements (Hierarchy). Delivery/logging is via audit_log; this is the
-- alert itself plus its audience and schedule.
CREATE TABLE system_alerts (
    id                      INTEGER GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
    created_by_account_id   INTEGER NOT NULL REFERENCES accounts(id),
    alert_type              TEXT NOT NULL CHECK (alert_type IN ('emergency', 'warning', 'announcement', 'routine')),
    audience                TEXT NOT NULL CHECK (audience IN ('admin_only', 'department', 'all_users', 'specific_users')),
    department_id           INTEGER REFERENCES departments(id),          -- audience = department
    recipient_account_ids   INTEGER[],                                   -- audience = specific_users
    body                    TEXT NOT NULL,
    action_link             TEXT,
    deliver_at              TIMESTAMPTZ NOT NULL DEFAULT now(),          -- immediate or scheduled
    recurrence              JSONB,                                       -- NULL = one-shot
    created_at              TIMESTAMPTZ NOT NULL DEFAULT now(),
    CONSTRAINT system_alerts_audience_shape CHECK (
        (audience = 'department' AND department_id IS NOT NULL)
        OR (audience = 'specific_users' AND recipient_account_ids IS NOT NULL)
        OR audience IN ('admin_only', 'all_users')
    )
);

COMMIT;
