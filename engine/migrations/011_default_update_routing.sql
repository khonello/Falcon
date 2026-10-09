-- 011_default_update_routing.sql -- update escalations reach the department by default.
--
-- spec 9.5: a machine stuck past the escalation threshold is reported to its Admins as well as the
-- Super User. Routing used to start empty, so it reached the Super User only until someone routed it.
-- New departments now start routed (AccountsRepo.create_department); this gives existing departments
-- the same default, without touching any routing the Super User already set for update_status.

INSERT INTO report_routing_config (category, routed_department_id, configured_by_account_id)
SELECT 'update_status', d.id, d.created_by_account_id
FROM departments d
WHERE NOT EXISTS (SELECT 1 FROM report_routing_config c WHERE c.category = 'update_status');
