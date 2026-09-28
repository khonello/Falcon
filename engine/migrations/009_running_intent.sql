-- 009_running_intent.sql -- the Program Intent list gains 'running'.
--
-- "Check whether Slack is still running" had no Intent to land on: the closest was
-- 'closed_not_running', which verifies the exact opposite. A held-out benchmark case
-- produced that inversion, so the option is added rather than approximated.
-- 'running' reads the same process_state signal as 'closed_not_running', inverted.
-- Mirrored in database-schema.md 6 and engine/task/verification.py.

ALTER TABLE verification_items DROP CONSTRAINT verification_items_intent_by_target;
ALTER TABLE verification_items ADD CONSTRAINT verification_items_intent_by_target CHECK (
    (target_type = 'file' AND intent IN ('create', 'update', 'exists'))
    OR (target_type = 'program' AND intent IN ('used', 'used_with_file', 'installed_available',
                                               'closed_not_running', 'running'))
);
