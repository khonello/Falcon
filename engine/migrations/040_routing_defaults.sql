-- Report routing: every department receives every kind of report but the ones about an Admin.
-- (The routing screen is gone; the default is the routing.) Existing departments are brought up to it;
-- anything already routed is left as it was. Attributed to the department's creator, else the first Super User.
INSERT INTO report_routing_config (category, routed_department_id, configured_by_account_id)
SELECT c.category, d.id, COALESCE(d.created_by_account_id, (SELECT min(id) FROM accounts WHERE role = 'super_user'))
FROM departments d
CROSS JOIN (VALUES ('resource_violation'), ('flow_failure'), ('update_status'), ('deviation')) AS c(category)
WHERE COALESCE(d.created_by_account_id, (SELECT min(id) FROM accounts WHERE role = 'super_user')) IS NOT NULL
ON CONFLICT DO NOTHING;
