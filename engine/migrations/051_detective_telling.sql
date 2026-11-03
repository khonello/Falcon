-- 051_detective_telling.sql -- a case told in words (ENGINE-GAPS #15; the user, 3 Nov 2026): the model's smoothing of the Engine's own account,
-- kept with markers in place of the facts (engine/detective/telling.py), and the fingerprint of the account it was made from. NULL: not
-- smoothed (the Engine's own account is shown). A fingerprint that no longer matches the case is not used: the case grew since.
ALTER TABLE detective_cases ADD COLUMN telling JSONB;
