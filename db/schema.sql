-- Run once against bonch-dev-db. Private notes are never bundled into public assets.
CREATE TABLE IF NOT EXISTS trip_notes (
  trip_key TEXT PRIMARY KEY NOT NULL,
  note TEXT NOT NULL DEFAULT '',
  updated_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
);
CREATE INDEX IF NOT EXISTS idx_trip_notes_updated_at ON trip_notes(updated_at);
