-- What a flow does when a file is deleted at its source: 'keep' leaves the destinations' copies alone (the default), 'mirror' removes them
-- (moved aside into a `.falcon-removed` folder in the destination, never destroyed, and only when the flow wrote the file and nobody has edited it since).
-- Mirrored in database-schema.md 6.

ALTER TABLE flows ADD COLUMN on_source_delete TEXT NOT NULL DEFAULT 'keep' CHECK (on_source_delete IN ('keep', 'mirror'));
