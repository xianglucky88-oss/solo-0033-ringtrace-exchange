from contextlib import contextmanager
from pathlib import Path
import sqlite3


class Database:
    def __init__(self, path):
        self.path = Path(path)

    @contextmanager
    def connect(self):
        connection = sqlite3.connect(self.path, isolation_level=None, timeout=8)
        connection.row_factory = sqlite3.Row
        try:
            connection.execute('PRAGMA foreign_keys = ON')
            yield connection
        finally:
            connection.close()

    def initialize(self):
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.connect() as connection:
            connection.execute('PRAGMA journal_mode = WAL')
            schema = Path(__file__).with_name('schema.sql').read_text(encoding='utf-8')
            connection.executescript(f'BEGIN IMMEDIATE;\n{schema}\nCOMMIT;')
            migrate(connection)
            connection.execute('CREATE INDEX IF NOT EXISTS idx_band_link_group ON band_link (group_id)')

    @contextmanager
    def transaction(self, *, write=False):
        with self.connect() as connection:
            connection.execute('BEGIN IMMEDIATE' if write else 'BEGIN')
            try:
                yield connection
                connection.commit()
            except BaseException:
                connection.rollback()
                raise


def migrate(connection):
    """Rebuild the legacy single-chain band_link table so groups can be stored."""
    columns = {row['name'] for row in connection.execute('PRAGMA table_info(band_link)')}
    if 'group_id' in columns:
        return
    connection.executescript('''
BEGIN IMMEDIATE;
ALTER TABLE band_link RENAME TO band_link_legacy;
CREATE TABLE band_link (
  proof TEXT PRIMARY KEY,
  old_band TEXT NOT NULL,
  new_band TEXT NOT NULL,
  effective_at TEXT NOT NULL,
  revision INTEGER NOT NULL,
  group_id TEXT,
  state TEXT NOT NULL DEFAULT 'active' CHECK (state IN ('active', 'excluded')),
  excluded_note TEXT,
  CHECK (old_band <> new_band),
  FOREIGN KEY (group_id) REFERENCES link_group (group_id)
);
CREATE INDEX idx_band_link_group ON band_link (group_id);
INSERT INTO band_link (proof, old_band, new_band, effective_at, revision, group_id, state)
SELECT proof, old_band, new_band, effective_at, revision, NULL, 'active' FROM band_link_legacy;
DROP TABLE band_link_legacy;
COMMIT;
''')


def current_revision(connection):
    return connection.execute('SELECT revision FROM ledger_meta WHERE singleton = 1').fetchone()[0]


def advance(connection):
    connection.execute('UPDATE ledger_meta SET revision = revision + 1 WHERE singleton = 1')
    return current_revision(connection)
