-- 012_report_summary_seen.sql -- a report keeps its sentence, and each reader's "seen".
--
-- The summary passed to reports.emit() used to be logged and pushed only, so a console reading the
-- list later had to rebuild the sentence from the source row (and could not for most categories).
-- It is now written with the report. `report_seen` records when each reader first opened a report,
-- so the board can tell new from seen from addressed. Seen is per reader, never shared: one Admin
-- opening a report does not make it seen for another. Not a Report and not the Super User's View.
-- Mirrored in database-schema.md 8 and engine/hierarchy/reports.py.

ALTER TABLE reports ADD COLUMN summary TEXT NOT NULL DEFAULT '';

CREATE TABLE report_seen (
    report_id   INTEGER NOT NULL REFERENCES reports(id),
    account_id  INTEGER NOT NULL REFERENCES accounts(id),
    seen_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (report_id, account_id)
);
