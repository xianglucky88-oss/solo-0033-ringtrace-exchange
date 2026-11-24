CREATE TABLE IF NOT EXISTS ledger_meta (
  singleton INTEGER PRIMARY KEY CHECK (singleton = 1),
  revision INTEGER NOT NULL
);
INSERT OR IGNORE INTO ledger_meta VALUES (1, 0);
CREATE TABLE IF NOT EXISTS input_batch (
  batch TEXT PRIMARY KEY,
  source TEXT NOT NULL,
  sha256 TEXT NOT NULL,
  count INTEGER NOT NULL,
  revision INTEGER NOT NULL UNIQUE,
  assignment_key TEXT NOT NULL DEFAULT '',
  UNIQUE (batch, source)
);
CREATE TABLE IF NOT EXISTS observation (
  source TEXT NOT NULL,
  report TEXT NOT NULL,
  batch TEXT NOT NULL,
  position INTEGER NOT NULL,
  event TEXT NOT NULL,
  band TEXT NOT NULL,
  site TEXT NOT NULL,
  kind TEXT NOT NULL,
  observed_at TEXT NOT NULL,
  recorded_at TEXT NOT NULL,
  PRIMARY KEY (source, report),
  UNIQUE (batch, position),
  FOREIGN KEY (batch, source) REFERENCES input_batch (batch, source)
);
CREATE TABLE IF NOT EXISTS band_link (
  proof TEXT PRIMARY KEY,
  old_band TEXT NOT NULL UNIQUE,
  new_band TEXT NOT NULL UNIQUE,
  effective_at TEXT NOT NULL,
  revision INTEGER NOT NULL UNIQUE,
  CHECK (old_band <> new_band)
);
CREATE TABLE IF NOT EXISTS event_correction (
  revision INTEGER PRIMARY KEY,
  source_event TEXT NOT NULL,
  first_event TEXT NOT NULL,
  second_event TEXT NOT NULL,
  CHECK (source_event <> first_event),
  CHECK (source_event <> second_event),
  CHECK (first_event <> second_event)
);
CREATE TABLE IF NOT EXISTS event_assignment (
  source TEXT NOT NULL,
  report TEXT NOT NULL,
  correction_revision INTEGER NOT NULL,
  original_event TEXT NOT NULL,
  event TEXT NOT NULL,
  PRIMARY KEY (source, report, correction_revision),
  FOREIGN KEY (source, report) REFERENCES observation (source, report),
  FOREIGN KEY (correction_revision) REFERENCES event_correction (revision)
);
CREATE INDEX IF NOT EXISTS idx_event_assignment_report ON event_assignment (source, report, correction_revision);
CREATE TABLE IF NOT EXISTS intake_routing (
  batch TEXT NOT NULL,
  position INTEGER NOT NULL,
  source TEXT NOT NULL,
  report TEXT NOT NULL,
  original_event TEXT NOT NULL,
  event TEXT NOT NULL,
  PRIMARY KEY (batch, position),
  UNIQUE (source, report),
  FOREIGN KEY (batch, source) REFERENCES input_batch (batch, source),
  FOREIGN KEY (source, report) REFERENCES observation (source, report)
);
CREATE TABLE IF NOT EXISTS release (
  revision INTEGER PRIMARY KEY,
  sha256 TEXT NOT NULL,
  payload BLOB NOT NULL,
  created_at TEXT NOT NULL
);
