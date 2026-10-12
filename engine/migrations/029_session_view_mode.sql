-- 029_session_view_mode.sql -- a session can be only seen, or seen and controlled (ENGINE-CONCEPT-NEEDS WP9).
--
-- Entering a machine now says how: `see` (the person at it keeps working and sees a bar saying who is looking) or `control` (the person is locked out and sees
-- who is working on their machine -- what entering always did before, and still the default). The mode can change while the session lasts. It decides what the
-- machine's Worker shows and whether remote mouse and keyboard are applied; it never changes who may enter (Session Blocking is the same either way).
-- Mirrored in database-schema.md 19.

ALTER TABLE sessions ADD COLUMN view_mode TEXT NOT NULL DEFAULT 'control' CHECK (view_mode IN ('see', 'control'));
