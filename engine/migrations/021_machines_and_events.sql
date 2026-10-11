-- 021_machines_and_events.sql -- what the console's fleet, machine page and audit log show (ENGINE-CONCEPT-NEEDS WP1).
--
--   * pcs: where a machine last connected from (`last_ip`), what it runs on (`os`), which build of the Worker it runs
--     (`agent_version`) and since when the agent has been up (`agent_started_at`). The Worker says all of these when it
--     authenticates; the address is the one the Engine saw.
--   * metric_samples: disk fullness and network throughput, beside processor and memory, so the machine page can draw
--     four charts of the same machine over a day or a week.
--   * audit_log: the machine (`pc_id`) and the department an event concerns, so a console can list events by machine and
--     an Admin sees only their own department's. Older rows have neither and show only to the Super User.
-- Mirrored in database-schema.md 1, 9, 10.

ALTER TABLE pcs ADD COLUMN last_ip TEXT;
ALTER TABLE pcs ADD COLUMN os TEXT;
ALTER TABLE pcs ADD COLUMN agent_version TEXT;
ALTER TABLE pcs ADD COLUMN agent_started_at TIMESTAMPTZ;

ALTER TABLE metric_samples ADD COLUMN disk REAL;
ALTER TABLE metric_samples ADD COLUMN net_kbps REAL;

ALTER TABLE audit_log ADD COLUMN pc_id INTEGER REFERENCES pcs(id);
ALTER TABLE audit_log ADD COLUMN department_id INTEGER REFERENCES departments(id);
CREATE INDEX audit_log_pc_idx ON audit_log (pc_id, occurred_at DESC) WHERE pc_id IS NOT NULL;
CREATE INDEX audit_log_department_idx ON audit_log (department_id, occurred_at DESC) WHERE department_id IS NOT NULL;
