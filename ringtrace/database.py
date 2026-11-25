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
            self._migrate_observation_ranges(connection)

    def _migrate_observation_ranges(self, connection):
        columns = {row['name'] for row in connection.execute('PRAGMA table_info(observation)')}
        if 'observed_end' not in columns:
            connection.execute('BEGIN IMMEDIATE')
            connection.execute('ALTER TABLE observation ADD COLUMN observed_end TEXT')
            connection.execute('ALTER TABLE observation ADD COLUMN recorded_end TEXT')
            connection.commit()

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


def current_revision(connection):
    return connection.execute('SELECT revision FROM ledger_meta WHERE singleton = 1').fetchone()[0]


def advance(connection):
    connection.execute('UPDATE ledger_meta SET revision = revision + 1 WHERE singleton = 1')
    return current_revision(connection)
