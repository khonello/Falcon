# Database Schema — v1

**Engine-owned, PostgreSQL (per Implementation Specification §3.3).** No other package holds a database. This document is derived directly from the seven design/spec documents — every table, column, and constraint below traces back to a specific stated rule, not an invented convenience. Where a design doc left something genuinely open (Section 9 items), the schema notes it rather than silently deciding.

Naming convention: `snake_case` tables and columns, singular table names avoided in favor of plural (`accounts`, not `account`), foreign keys named `{referenced_table_singular}_id`.

---

## 1. Identity & Hierarchy

### `departments`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `name` | TEXT UNIQUE NOT NULL | |
| `created_at` | TIMESTAMP NOT NULL | |
| `created_by_account_id` | INTEGER FK → accounts.id | Always a Super User account (Department Creation & Assignment: Super User only) |

*Zero-Admin departments are allowed by design — no `admin_count` constraint enforced at the schema level; surfaced via a query in Super User's aggregate view instead (see `deviation_log` below for the general pattern).*

### `accounts`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `role` | TEXT NOT NULL CHECK (`role` IN ('super_user','admin','worker')) | |
| `department_id` | INTEGER FK → departments.id, NULLABLE | NULL only for Super User; required for Admin and Worker |
| `bound_pc_id` | INTEGER FK → pcs.id, UNIQUE, NULLABLE | **Identity Model: one account ↔ exactly one PC.** UNIQUE enforces one PC can't be bound to two active accounts simultaneously. NULLABLE only because Super User's own workstation binding is not specified as required by any doc — flagged as an open modeling choice, not a stated gap. |
| `self_display_name` | TEXT NULLABLE | The name this account sets for itself, shown to those *below* it (Display Names: self-facing name) |
| `status` | TEXT NOT NULL DEFAULT 'active' CHECK (`status` IN ('active','offboarded')) | Offboarding & Deprovisioning: deactivated, never deleted |
| `offboarded_at` | TIMESTAMP NULLABLE | |
| `created_at` | TIMESTAMP NOT NULL | |

*Note on "account bound to a PC" enforcement: the UNIQUE constraint on `bound_pc_id` prevents two **active** accounts sharing a PC at the database level, but does not by itself catch "account used from an unbound PC" — that is a connection-time check in the Engine (a Worker Client's connection announces its PC identity; the Engine compares it against the authenticating account's `bound_pc_id` and logs a deviation on mismatch — see `deviation_log`), not something a table constraint alone can express.*

### `display_name_grants`
Implements Display Names' **non-propagation rule**: a name set at one relationship layer is never visible or joinable at another.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `namer_account_id` | INTEGER FK → accounts.id | The one assigning the label (e.g., a Super User) |
| `named_account_id` | INTEGER FK → accounts.id | The one being labeled (e.g., an Admin) |
| `label` | TEXT NOT NULL | |
| `created_at` | TIMESTAMP NOT NULL | |
| UNIQUE(`namer_account_id`, `named_account_id`) | | One label per namer-named pair |

**Enforcement of non-propagation is a query-layer rule, not a schema-layer one:** any query resolving "what does account X see when Y is referenced" must filter `display_name_grants` by `namer_account_id = X`, never join across other namers' grants. This is explicitly called out because it is the single easiest rule in this entire schema to violate accidentally with a careless join — flagged for extra test coverage.

**Composed fallback** (when no `self_display_name` and no applicable `display_name_grants` row exists): computed at query time from `accounts.id` + `pcs.hostname` + `departments.name` as available — not stored, always derived, so it never goes stale.

### `pcs`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `hostname` | TEXT NOT NULL | |
| `department_id` | INTEGER FK → departments.id, NULLABLE | NULL for an Admin's or Super User's own workstation if modeled outside department scope |
| `pc_type` | TEXT NOT NULL CHECK (`pc_type` IN ('super_user_workstation','admin_workstation','client_pc')) | |
| `created_at` | TIMESTAMP NOT NULL | |

---

## 2. Traversal & Sessions

### `sessions`
The single table implementing **Session Blocking During Traversal** — session, not traversal, is the unit that gets blocked (Hierarchy §Traversal Boundaries).

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `pc_id` | INTEGER FK → pcs.id NOT NULL | The occupied/blocked target |
| `occupant_account_id` | INTEGER FK → accounts.id NOT NULL | Who currently holds it — the native user, or whoever traversed in |
| `occupied_via` | TEXT NOT NULL CHECK (`occupied_via` IN ('native','traversal','assisted_access')) | `assisted_access` is deliberately its own value — Cross-Department Assisted Access is explicitly a separate mechanism from Traversal, not a variant of it |
| `entered_at` | TIMESTAMP NOT NULL | |
| `deadline_at` | TIMESTAMP NULLABLE | **Traversal Time Limit** — NULL only for `occupied_via = 'native'`, since native use has no imposed limit; required for `traversal` and `assisted_access` |
| `extended_count` | INTEGER NOT NULL DEFAULT 0 | Number of extension requests granted |
| `un_evictable` | BOOLEAN NOT NULL DEFAULT FALSE | TRUE when `occupant_account_id`'s role is `super_user` — enforced by application logic at session-creation time; standard CHECK constraints can't subquery another table, regardless of database engine |
| `ended_at` | TIMESTAMP NULLABLE | NULL while session is active; this is what "session blocked" means at the data level — a `sessions` row for a given `pc_id` with `ended_at IS NULL` |
| `ended_reason` | TEXT NULLABLE CHECK (`ended_reason` IN ('voluntary','superior_ended','deadline_expired','network_drop_deadline_expired')) | |

**Enforcement of "one active session per PC":** a partial unique index — `CREATE UNIQUE INDEX one_active_session_per_pc ON sessions(pc_id) WHERE ended_at IS NULL`. This is the actual mechanism behind "traversal can only begin when the destination is idle": inserting a new active session row for an already-occupied `pc_id` fails at the database level, which the Engine translates into the correct response — block-or-end-first for vertical relationships, hard refusal for horizontal.

**Network drop resolution (Implementation Spec §7.1):** deliberately *no* separate "connection_lost_at" column or disconnect-handling state. A dropped connection has no special row or status — the existing `deadline_at` continues to govern the row exactly as it would with a live connection; `ended_reason = 'network_drop_deadline_expired'` exists only so the audit trail can distinguish *why* a deadline expiry occurred, not to add new behavior.

### `assisted_access_requests`
Cross-Department Assisted Access — deliberately its own table, not folded into `sessions`, since entry here is consent-based, not block-or-end-first.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `requester_account_id` | INTEGER FK → accounts.id NOT NULL | Must be role = 'admin' |
| `target_department_id` | INTEGER FK → departments.id, NULLABLE | NULL if requester didn't target a specific department |
| `helper_account_id` | INTEGER FK → accounts.id, NULLABLE | NULL until matched |
| `entry_path` | TEXT NOT NULL CHECK (`entry_path` IN ('requester_initiated','helper_broadcast')) | |
| `matched_at` | TIMESTAMP NULLABLE | NULL if never matched — **no lingering**, an unmatched request is not retried or queued; the row simply records that a request was made and went unmatched |
| `resulting_session_id` | INTEGER FK → sessions.id, NULLABLE | Set once matched and a `sessions` row (with `occupied_via = 'assisted_access'`) is created |
| `access_ceiling` | TEXT NOT NULL | System-defined baseline, serialized (JSON) — what the helper can touch, before requester narrowing |
| `access_narrowing` | TEXT NULLABLE | Requester-configured restriction, serialized (JSON) — may only narrow, never loosen, the ceiling; enforced in application logic, not by the schema |
| `created_at` | TIMESTAMP NOT NULL | |

---

## 3. Global File Index

### `file_index`
The single shared index consumed by Task (Verification, collision checks), Flow (Pre-Flight Collision Check, sync trigger), and Resource (compliance detection, search) — per Implementation Spec §6.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `pc_id` | INTEGER FK → pcs.id NOT NULL | |
| `path` | TEXT NOT NULL | |
| `filename` | TEXT NOT NULL | Denormalized from `path` deliberately — Task's Create-intent collision checking is name-first (per Task §Create Intent), so filename needs to be independently indexable, not derived from `path` at query time |
| `content_hash` | TEXT NULLABLE | NULL until the file exists (relevant for a Create-intent target registered before its file appears) |
| `resource_tag` | TEXT NULLABLE CHECK (`resource_tag` IN ('admin','restricted','worker_dept','common')) | NULL for a file with no Resource classification |
| `resource_tag_scope_department_id` | INTEGER FK → departments.id, NULLABLE | Only meaningful when `resource_tag = 'worker_dept'` |
| `indexed_via` | TEXT NOT NULL CHECK (`indexed_via` IN ('event','idle_sweep')) | Which of the two population mechanisms recorded this entry (Implementation Spec §6.2) |
| `last_seen_at` | TIMESTAMP NOT NULL | |
| UNIQUE(`pc_id`, `path`) | | |

---

## 4. Task

### `tasks`
No `task_directory` column anywhere in this schema — deliberately, per Task's "No Task Directory" resolution. Target tracking is entirely through `verification_items` → `file_index` / process identity, never a location.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `assigner_account_id` | INTEGER FK → accounts.id NOT NULL | Super User or Admin |
| `assignee_account_id` | INTEGER FK → accounts.id NOT NULL | |
| `description_raw` | TEXT NOT NULL | The original natural-language input — kept verbatim, since it's what the LLM decision graph (Implementation Spec §7.2.1) was run against, useful for later re-derivation or dispute review |
| `status` | TEXT NOT NULL DEFAULT 'active' CHECK (`status` IN ('active','in_progress','completed')) | |
| `verification_mode` | TEXT NOT NULL CHECK (`verification_mode` IN ('stack','none')) | `'none'` only ever set by **explicit** assigner confirmation — never a default; application logic must reject a task creation that leaves this ambiguous, per Task's governing principle |
| `soft_deadline_at` | TIMESTAMP NULLABLE | |
| `final_deadline_at` | TIMESTAMP NULLABLE | |
| `created_at` | TIMESTAMP NOT NULL | |
| `started_at` | TIMESTAMP NULLABLE | Client's Task Interaction exception — set when the assignee acknowledges/starts |
| `completed_at` | TIMESTAMP NULLABLE | Set only by `manual_verification`, never automatically |

### `verification_items`
The stack. Ordering is a display concern (per Task's "no output piping" principle, echoed here for consistency across Task and Control/Events/Monitoring), so ordering is a plain integer, not a linked-list structure.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `task_id` | INTEGER FK → tasks.id NOT NULL | |
| `sequence` | INTEGER NOT NULL | Display order within the stack — "no nesting," so a flat integer is sufficient, no parent/child self-reference needed |
| `target_type` | TEXT NOT NULL CHECK (`target_type` IN ('file','program')) | |
| `intent` | TEXT NOT NULL CHECK ( (`target_type` = 'file' AND `intent` IN ('create','update','exists')) OR (`target_type` = 'program' AND `intent` IN ('used','used_with_file','installed_available','closed_not_running')) ) | Compound CHECK ties Intent's legal values to target_type, matching the design's explicit File-vs-Program Intent lists |
| `file_index_id` | INTEGER FK → file_index.id, NULLABLE | Set for `target_type = 'file'`; NULL for a Create-intent target until the file actually appears and gets indexed |
| `proposed_filename` | TEXT NULLABLE | Create-intent, name-first: populated immediately even before `file_index_id` exists |
| `proposed_path` | TEXT NULLABLE | Optional per design — "shown only if the assigner's input specified one" |
| `linked_file_verification_item_id` | INTEGER FK → verification_items.id, NULLABLE | Self-reference used only for `intent = 'used_with_file'`, linking a Program item to the File item it's tied to |
| `program_name` | TEXT NULLABLE | Set for `target_type = 'program'` |
| `status` | TEXT NOT NULL DEFAULT 'pending' CHECK (`status` IN ('pending','passed','failed')) | |
| `populated_by` | TEXT NOT NULL CHECK (`populated_by` IN ('llm','manual')) | Whether this item came from the decision graph or the `[+ item]` fallback editor — kept for audit/debugging of LLM accuracy over time |

### `expectations`
Soft signals, per target — deliberately a separate table from `verification_items`, since Expectation is explicitly derived from Verification and can have a many-per-item cardinality (multiple signal readings over time), not a 1:1 property.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `verification_item_id` | INTEGER FK → verification_items.id NOT NULL | |
| `signal_type` | TEXT NOT NULL | e.g. `'file_modified'`, `'process_active'`, `'memory_footprint'`, `'open_file_descriptor'` — an open list by design (Expectation's signal set is descriptive, not a fixed enum in the source docs), so TEXT rather than CHECK-constrained |
| `observed_at` | TIMESTAMP NOT NULL | |
| `value` | TEXT NULLABLE | Serialized detail, shape depends on `signal_type` |

### `manual_verifications`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `task_id` | INTEGER FK → tasks.id NOT NULL UNIQUE | One per task — task is verified "as a whole unit," never per-item |
| `verified_by_account_id` | INTEGER FK → accounts.id NOT NULL | Must equal `tasks.assigner_account_id` — enforced in application logic; Postgres can alternatively enforce this via a trigger if stricter database-level guarantee is wanted later, but a plain CHECK cannot cross-reference another table's row |
| `outcome` | TEXT NOT NULL CHECK (`outcome` IN ('complete','incomplete')) | |
| `verified_at` | TIMESTAMP NOT NULL | |

---

## 5. Flow

### `flows`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `created_by_account_id` | INTEGER FK → accounts.id NOT NULL | |
| `source_pc_id` | INTEGER FK → pcs.id NOT NULL | |
| `source_path` | TEXT NOT NULL | |
| `status` | TEXT NOT NULL DEFAULT 'active' CHECK (`status` IN ('active','paused','inactive')) | |
| `pause_reason` | TEXT NULLABLE | Populated only when `status = 'paused'`; free text since Failure Handling's predefined-suggestion set (Flow §Failure Handling) is a UI/logic concern layered on top of this, not a fixed schema enum |
| `consent_status` | TEXT NOT NULL CHECK (`consent_status` IN ('not_required','pending','granted')) | `'not_required'` when creator already outranks every destination owner; `'pending'`/`'granted'` for lateral or upward flows |
| `created_at` | TIMESTAMP NOT NULL | |

### `flow_destinations`
Branching — one flow, many destinations.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `flow_id` | INTEGER FK → flows.id NOT NULL | |
| `parent_stage_id` | INTEGER FK → flow_stages.id, NULLABLE | NULL if this destination branches directly off the source with no intervening stage |
| `destination_pc_id` | INTEGER FK → pcs.id, NULLABLE | NULL if destination is remote storage rather than a PC |
| `destination_path` | TEXT NOT NULL | |
| `owner_account_id` | INTEGER FK → accounts.id NOT NULL | Whose authority/consent this destination falls under (Destination Consent) |
| `pre_flight_check_status` | TEXT NOT NULL CHECK (`pre_flight_check_status` IN ('passed','collision_pending','cycle_pending')) | Both checks recorded on the same row since both gate flow acceptance the same way (Flow §Pre-Flight Collision Check, §Cycle Prevention) |

### `flow_stages`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `flow_id` | INTEGER FK → flows.id NOT NULL | |
| `parent_stage_id` | INTEGER FK → flow_stages.id, NULLABLE | Self-reference — a stage can sit before or after a Branch, so this models the actual path structure, not a flat list |
| `stage_type` | TEXT NOT NULL CHECK (`stage_type` IN ('branch','transformation','categorization')) | |
| `config` | TEXT NULLABLE | Serialized (JSON) — e.g., target format for Transformation, rule set for Categorization |

### `flow_sync_log`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `flow_destination_id` | INTEGER FK → flow_destinations.id NOT NULL | |
| `content_hash` | TEXT NOT NULL | The write's own hash — this plus `written_by` is the **write attribution** that lets a flow distinguish its own writes from external ones (Flow §Synchronization Mechanism) |
| `written_by` | TEXT NOT NULL CHECK (`written_by` IN ('flow_sync','external')) | |
| `written_by_account_id` | INTEGER FK → accounts.id, NULLABLE | Populated when `written_by = 'external'` and attributable |
| `conflict_resolved` | BOOLEAN NOT NULL DEFAULT FALSE | TRUE once a detected external write has been renamed `-modified` and a fresh sync copy created |
| `occurred_at` | TIMESTAMP NOT NULL | |

---

## 6. Resource

Resource's tier folders (`admin`, `restricted`, `workers`, `common`) are represented via `file_index.resource_tag` (Section 3) rather than a separate table — there is no additional Resource-specific file record, since the design explicitly states Resource is one *consumer* of the Global File Index, not the owner of a parallel one.

### `resource_violations`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `file_index_id` | INTEGER FK → file_index.id NOT NULL | The specific file that violated its tier — **only this file is ignored going forward, never the surrounding structure** (Directory Structure Conflicts principle) |
| `expected_tag` | TEXT NOT NULL | What the tag should have permitted for this PC |
| `found_on_pc_id` | INTEGER FK → pcs.id NOT NULL | |
| `detected_via` | TEXT NOT NULL CHECK (`detected_via` IN ('event','polling_fallback')) | |
| `surfaced_to_account_id` | INTEGER FK → accounts.id NOT NULL | The affected user this was surfaced to |
| `resolved_at` | TIMESTAMP NULLABLE | |
| `report_id` | INTEGER FK → reports.id, NULLABLE | Every violation is also a routable Report (Section 8) |
| `detected_at` | TIMESTAMP NOT NULL | |

---

## 7. Assistance (Ping, Message Channel, Listeners)

### `pings`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `sender_account_id` | INTEGER FK → accounts.id NOT NULL | |
| `receiver_account_id` | INTEGER FK → accounts.id NOT NULL | Must be `sender`'s direct superior — enforced in application logic |
| `sent_at` | TIMESTAMP NOT NULL | |
| `addressed_at` | TIMESTAMP NULLABLE | NULL = contributes to the receiver's persistent pulsing status; **repeatable, no lock** — no UNIQUE constraint preventing multiple unaddressed pings from the same sender |

### `message_channels`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `opened_via_ping_id` | INTEGER FK → pings.id NOT NULL | A channel always opens because a superior responded to a Ping |
| `initiator_account_id` | INTEGER FK → accounts.id NOT NULL | Whoever sent the original Ping (may be subordinate or superior — Admin can Ping Worker for information, too) |
| `superior_account_id` | INTEGER FK → accounts.id NOT NULL | Whoever holds closing authority, **always the superior regardless of who initiated** |
| `turn` | TEXT NOT NULL CHECK (`turn` IN ('sender','superior')) | Whose turn it currently is — this single column *is* the one-message-per-turn lock |
| `closed_at` | TIMESTAMP NULLABLE | Set only by `superior_account_id` — enforced in application logic |
| `opened_at` | TIMESTAMP NOT NULL | |

### `messages`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `message_channel_id` | INTEGER FK → message_channels.id NOT NULL | |
| `sender_account_id` | INTEGER FK → accounts.id NOT NULL | |
| `body` | TEXT NOT NULL | |
| `sent_at` | TIMESTAMP NOT NULL | |

### `listeners`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `message_channel_id` | INTEGER FK → message_channels.id NOT NULL | |
| `listener_account_id` | INTEGER FK → accounts.id NOT NULL | Must be role = 'admin' |
| `added_by_account_id` | INTEGER FK → accounts.id NOT NULL | Either channel party — this column is what makes visibility asymmetric: a query for "Listeners I can see" filters `added_by_account_id = requesting_account_id`, never both parties' additions jointly |
| `added_at` | TIMESTAMP NOT NULL | |
| UNIQUE(`message_channel_id`, `listener_account_id`) | | Dedup: if both parties add the same person, it collapses to one row (first insert wins; second is a no-op, not an error) |

---

## 8. Reports & Routing

### `reports`
The single table every "surfaced to Super User" event throughout the whole system writes to — Resource violations, Flow failures, Listener-channel closures, Assisted Access sessions, update rollout failures, all land here, distinguished only by `category`.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `category` | TEXT NOT NULL | e.g. `'resource_violation'`, `'flow_failure'`, `'listener_report'`, `'assisted_access'`, `'update_rollout_failure'` — open list, not CHECK-constrained, since new categories are expected to be added as the system grows |
| `source_table` | TEXT NOT NULL | Which table the underlying event lives in (`'resource_violations'`, `'flow_sync_log'`, etc.) |
| `source_id` | INTEGER NOT NULL | The row id in that table — a polymorphic reference, deliberately not a strict FK, since no relational database can cleanly FK a column across a variable target table. Postgres's table inheritance or a `CHECK`-per-partition approach could reduce this tradeoff later, but is not necessary for v1 — enforced in the Engine's data-access layer instead |
| `generated_at` | TIMESTAMP NOT NULL | |

**Super User always sees every row here, unconditionally — no query ever filters `reports` by routing for a Super User's own view.**

### `report_routing_config`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `category` | TEXT NOT NULL | |
| `routed_department_id` | INTEGER FK → departments.id NOT NULL | |
| `configured_by_account_id` | INTEGER FK → accounts.id NOT NULL | Must be role = 'super_user' |
| `configured_at` | TIMESTAMP NOT NULL | |
| UNIQUE(`category`, `routed_department_id`) | | |

*A department with multiple Admins: this table routes to the **department**, not one Admin — resolving which Admins see a routed report is a query joining `reports` → `report_routing_config` → `accounts WHERE department_id = ... AND role = 'admin'`, deliberately not a `routed_admin_id` column, per Report Routing's explicit "every Admin in the department" resolution.*

### `report_addressed_views`
The Super-User-only View — **structurally incapable of being a Report**, by design, not by convention. This table has no `category` column and is never read by the same query path that resolves a routed department's report pane, preventing the infinite-regress problem the design explicitly calls out.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `report_id` | INTEGER FK → reports.id NOT NULL | |
| `addressed_by_account_id` | INTEGER FK → accounts.id NOT NULL | |
| `addressed_at` | TIMESTAMP NOT NULL | |

---

## 9. Control, Events, Monitoring & Actions

### `event_definitions`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `created_by_account_id` | INTEGER FK → accounts.id NOT NULL | Must be role = 'admin' — this whole combo is Admin-interface-only (Implementation Spec §7.5); Super User traverses in rather than creating these directly |
| `condition_type` | TEXT NOT NULL CHECK (`condition_type` IN ('native_pushed','polled')) | Which of the two evaluation mechanisms this event uses |
| `condition_spec` | TEXT NOT NULL | Serialized (JSON) — the actual condition (file path pattern, threshold value, cron-like schedule, etc.) |
| `enabled` | BOOLEAN NOT NULL DEFAULT TRUE | |
| `created_at` | TIMESTAMP NOT NULL | |

### `actions`
Covers Control, Monitoring, and Custom Actions in one table — they share the same lifecycle (timeout, termination, status), differing mainly in `action_kind` and, for Custom, script content.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `created_by_account_id` | INTEGER FK → accounts.id NOT NULL | Must be role = 'admin'; Custom Actions additionally require this to be the *authoring* Admin for audit attribution |
| `action_kind` | TEXT NOT NULL CHECK (`action_kind` IN ('control','monitoring','custom')) | |
| `builtin_type` | TEXT NULLABLE | e.g. `'shutdown'`, `'screenshot'` — NULL for `action_kind = 'custom'` |
| `custom_script` | TEXT NULLABLE | Populated only for `action_kind = 'custom'`; PowerShell or Python source, validated against the standard-library-plus-Windows-native-only constraint before storage |
| `custom_script_language` | TEXT NULLABLE CHECK (`custom_script_language` IN ('python','powershell')) | |
| `timeout_seconds` | INTEGER NOT NULL | Every Action has a timeout — no NULL/unbounded case permitted |
| `created_at` | TIMESTAMP NOT NULL | |

### `event_actions`
Join table — an Event triggers one or more Actions, each executing independently.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `event_definition_id` | INTEGER FK → event_definitions.id NOT NULL | |
| `action_id` | INTEGER FK → actions.id NOT NULL | |
| `display_sequence` | INTEGER NOT NULL | **Display/UI ordering only — never a data dependency.** No column here represents "wait for the previous action's output," because the design explicitly states actions attached to the same event execute independently, with no output piping between them (v1) |

### `action_executions`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `action_id` | INTEGER FK → actions.id NOT NULL | |
| `triggered_by_event_definition_id` | INTEGER FK → event_definitions.id, NULLABLE | NULL if manually/immediately triggered rather than event-fired |
| `target_pc_id` | INTEGER FK → pcs.id NOT NULL | |
| `status` | TEXT NOT NULL DEFAULT 'pending' CHECK (`status` IN ('pending','success','failed','terminated')) | |
| `terminated_reason` | TEXT NULLABLE CHECK (`terminated_reason` IN ('timeout','manual')) | Populated only when `status = 'terminated'` |
| `output_log_path` | TEXT NULLABLE | Where stdout/output was captured, per the reference project's tail-by-file-growth pattern (Implementation Spec §7.3) |
| `started_at` | TIMESTAMP NOT NULL | |
| `ended_at` | TIMESTAMP NULLABLE | |

---

## 10. Audit Trail

### `audit_log`
One table, every combo writes to it — this is deliberate, matching "one log, one hierarchy, one system" from the Synthesis document, rather than per-combo audit tables that would need to be unioned for any cross-cutting view (Super User's audit review, retention purge).

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `actor_account_id` | INTEGER FK → accounts.id, NULLABLE | NULL for a system-initiated entry (e.g., an idle-triggered index sweep with no human actor) |
| `action_type` | TEXT NOT NULL | e.g. `'traversal_started'`, `'session_ended'`, `'task_verified'`, `'flow_created'`, `'resource_violation_detected'` — open list, not CHECK-constrained |
| `target_type` | TEXT NULLABLE | Polymorphic, paired with `target_id` the same way `reports.source_table`/`source_id` works |
| `target_id` | INTEGER NULLABLE | |
| `detail` | TEXT NULLABLE | Serialized (JSON) — free-form context specific to `action_type` |
| `occurred_at` | TIMESTAMP NOT NULL | |

**Retention:** a scheduled job deletes rows where `occurred_at < now() - 90 days`, flat across every `action_type` — no per-category tiering in v1 (Hierarchy §Audit & Logging → Retention). This job is the one piece of "automatic deletion" anywhere in this schema, and it is explicitly time-based and universal, never triggered by content or category.

### `deviation_log`
Implements **System Expectations & Deviation Handling** as its own first-class table, not folded into `audit_log`, because a deviation is a distinct kind of event — it has an *expectation* and an *observed reality* to record, which `audit_log`'s generic shape doesn't naturally carry.

| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `expectation` | TEXT NOT NULL | Which named expectation was violated (matches the left column of Hierarchy's System Expectations table — e.g. `'account_bound_to_one_pc'`, `'flow_one_directional'`, `'directory_structure_matches_hierarchy_level'`) |
| `observed_account_id` | INTEGER FK → accounts.id, NULLABLE | Who/what triggered the deviation, where attributable |
| `observed_pc_id` | INTEGER FK → pcs.id, NULLABLE | |
| `detail` | TEXT NULLABLE | Serialized (JSON) — what was expected vs. what was found |
| `surfaced_to_account_id` | INTEGER FK → accounts.id, NOT NULL | The affected party this was made visible to — every deviation must have one, per the "never silently tolerated" principle |
| `resolved_at` | TIMESTAMP NULLABLE | |
| `detected_at` | TIMESTAMP NOT NULL | |

---

## 11. Update & Deployment

### `versions`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `version_string` | TEXT UNIQUE NOT NULL | |
| `approved_by_account_id` | INTEGER FK → accounts.id NOT NULL | Must be role = 'super_user' |
| `approved_at` | TIMESTAMP NOT NULL | Approval **cannot occur** while any `pc_version_status` row is behind the currently-current version — enforced in application logic before insert, not expressible as a table constraint |

### `pc_version_status`
| Column | Type | Notes |
|---|---|---|
| `id` | INTEGER PK | |
| `pc_id` | INTEGER FK → pcs.id NOT NULL UNIQUE | |
| `current_version_id` | INTEGER FK → versions.id NOT NULL | |
| `target_version_id` | INTEGER FK → versions.id, NULLABLE | Set during an in-progress rollout; NULL when the PC is already current |
| `last_attempt_at` | TIMESTAMP NULLABLE | |
| `attempt_failure_count` | INTEGER NOT NULL DEFAULT 0 | Reset to 0 on a successful update; compared against the (tunable, per Implementation Spec §10 open item) escalation threshold |
| `escalated_at` | TIMESTAMP NULLABLE | Set once `attempt_failure_count` crosses the threshold — this is what generates a `reports` row (`category = 'update_rollout_failure'`) visible to the department's Admin and, aggregated, to Super User |

---

## 12. Cross-Cutting Notes for Implementation

- **No table in this schema performs a hard DELETE except the `audit_log` retention job.** Every other "removal" in the design (offboarding, resource violations, deviation) is a status/flag change, consistent with the system-wide preference for preserving history over erasing it.
- **Every polymorphic reference** (`reports.source_table`/`source_id`, `audit_log.target_type`/`target_id`) is a deliberate tradeoff — it avoids one join table per source type, at the cost of the database not being able to enforce referential integrity on these columns itself. This must be enforced in the Engine's data-access layer instead. Flagged explicitly so it isn't mistaken for an oversight during code review.
- **This schema does not yet model:** the exact serialized shape of `condition_spec` (Events), `config` (Flow stages), `access_ceiling`/`access_narrowing` (Assisted Access) — these are JSON blobs whose internal shape is an implementation-phase decision, not a v1 schema-design decision, since the *external* behavior they drive is already fully specified in the design documents.

---

## 13. Additions Made During Implementation

Columns/tables the design documents require but v1 of this schema did not model. Each is in `engine/migrations/001_initial.sql` under the same section number.

| Addition | Why |
|---|---|
| `pcs.client_id` TEXT UNIQUE | Implementation Spec §8.2 issues each client a derived key for its `client_id`; the Identity Model binds one account to one PC, so the credential identity belongs on `pcs`. Needed for `auth.respond` to resolve a connection to an account. |
| `accounts.assistance_available` BOOLEAN | Hierarchy → Cross-Department Assisted Access → Two Entry Paths: "opted in as reachable for assistance" needs a persisted flag for the availability query. |
| `system_alerts` table | Hierarchy → System Alerts & Announcements: type, audience (admin_only / department / all_users / specific_users), body, action link, `deliver_at`, optional `recurrence` (JSON). Delivery events go to `audit_log`. |

Postgres adaptations applied uniformly: identity columns for PKs, `TIMESTAMPTZ` for every timestamp, `JSONB` for every serialized-JSON column, and a `schema_migrations` bookkeeping table.
| `actions.archived_at` TIMESTAMPTZ (migration 002) | "No hard deletes": `event_definitions` has `enabled`, `flows` has `'inactive'`, `accounts` has `'offboarded'` — `actions` had no soft-delete marker, so deleting a Custom Action would have been the only hard delete outside audit retention. |
| `flow_destinations.paused_reason` TEXT, `flow_destinations.removed_at` TIMESTAMPTZ (migration 003) | Failure Handling pauses "only the specific flow or branch" — a per-destination pause needs a column; editing a flow's destinations must not hard-delete rows that `flow_sync_log` references. |
| `actions.name`, `actions.description`, `actions.params` JSONB, `actions.timing` JSONB (migration 004) | Control → Custom Actions lists name/description/execution timing as Action properties, and built-ins take parameters; none had a column. |
| `system_alerts.delivered_at` TIMESTAMPTZ (migration 004) | Scheduled alerts must be delivered exactly once by the Scheduler. |
| `action_executions.exit_code` INTEGER (migration 005) | The Worker Client reports the script's exit code; the Dashboard shows it alongside success/failed/terminated. |
| `flow_sync_log.source_relative_path`, `flow_sync_log.written_path` TEXT (migration 006) | Write attribution per file: stages relocate files at the destination, so an external edit there must be mapped back to its source file via the sync row that wrote it, not by path arithmetic. |
| `pc_version_status.current_version_id` made nullable (migration 007) | A freshly provisioned PC runs a build that predates any approval; NULL = never confirmed on an approved version (counts as behind), so its first failed attempt can still be recorded and escalated. |
