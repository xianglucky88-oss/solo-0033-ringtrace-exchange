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
  line_count INTEGER NOT NULL,
  revision INTEGER NOT NULL UNIQUE,
  UNIQUE (batch, source)
);
CREATE TABLE IF NOT EXISTS batch_line (
  batch TEXT NOT NULL,
  position INTEGER NOT NULL,
  event TEXT NOT NULL,
  report TEXT,
  line TEXT NOT NULL,
  disposition TEXT NOT NULL CHECK (disposition IN ('accepted', 'rejected')),
  reason TEXT,
  message TEXT,
  PRIMARY KEY (batch, position),
  FOREIGN KEY (batch) REFERENCES input_batch (batch)
);
CREATE TABLE IF NOT EXISTS batch_group (
  batch TEXT NOT NULL,
  event TEXT NOT NULL,
  state TEXT NOT NULL CHECK (state IN ('accepted', 'rejected')),
  reason TEXT,
  PRIMARY KEY (batch, event),
  FOREIGN KEY (batch) REFERENCES input_batch (batch)
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
CREATE TABLE IF NOT EXISTS release (
  revision INTEGER PRIMARY KEY,
  sha256 TEXT NOT NULL,
  payload BLOB NOT NULL,
  created_at TEXT NOT NULL
);
