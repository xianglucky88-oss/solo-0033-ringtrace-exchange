"""Upgrade material recorded before per-group intake existed.

Earlier packages were all-or-nothing, so every stored observation stood for an
accepted line. Replaying those rows as accepted lines keeps older receipts
downloadable and older releases verifiable from the content they were built on.
"""
from .codec import canonical

FIELDS = ('report', 'event', 'band', 'site', 'kind')


def backfill(connection):
    batches = [dict(row) for row in connection.execute('SELECT * FROM input_batch WHERE line_count = 0')]
    for batch in batches:
        rows = [dict(row) for row in connection.execute(
            'SELECT * FROM observation WHERE batch = ? ORDER BY position', (batch['batch'],))]
        for row in rows:
            original = {field: row[field] for field in FIELDS}
            original['observed_at'] = row['recorded_at']
            connection.execute('''INSERT INTO batch_line
              (batch, position, event, report, line, disposition, reason, message)
              VALUES (?, ?, ?, ?, ?, 'accepted', NULL, NULL)''',
              (batch['batch'], row['position'], row['event'], row['report'],
               canonical(original).decode('utf-8')))
        groups = {}
        for row in rows:
            groups.setdefault(row['event'], []).append(row['position'])
        for event, positions in groups.items():
            connection.execute('''INSERT OR IGNORE INTO batch_group (batch, event, state, reason)
                                  VALUES (?, ?, 'accepted', NULL)''', (batch['batch'], event))
        connection.execute('UPDATE input_batch SET line_count = ? WHERE batch = ?',
                           (len(rows), batch['batch']))
