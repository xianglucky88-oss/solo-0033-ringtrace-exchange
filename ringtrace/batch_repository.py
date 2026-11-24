def find_batch(connection, batch):
    result = connection.execute('SELECT * FROM input_batch WHERE batch = ?', (batch,)).fetchone()
    return dict(result) if result else None


def batches(connection):
    return [dict(row) for row in connection.execute('SELECT * FROM input_batch ORDER BY revision')]


def reports_for_batch(connection, batch):
    return [dict(row) for row in connection.execute('SELECT * FROM observation WHERE batch = ? ORDER BY position', (batch,))]


def reports(connection):
    return [dict(row) for row in connection.execute('SELECT * FROM observation ORDER BY event, source, report')]


def insert_batch(connection, receipt, records):
    connection.execute('''INSERT INTO input_batch (batch, source, sha256, count, revision)
                          VALUES (:batch, :source, :sha256, :count, :revision)''', receipt)
    connection.executemany('''INSERT INTO observation
      (source, report, batch, position, event, band, site, kind, observed_at, recorded_at)
      VALUES (:source, :report, :batch, :position, :event, :band, :site, :kind, :observed_at, :recorded_at)''',
      ({**record, 'source': receipt['source'], 'batch': receipt['batch'], 'position': position}
       for position, record in enumerate(records, 1)))


def claimed_report_numbers(connection, source, numbers):
    placeholders = ','.join('?' for number in numbers)
    rows = connection.execute(
        f'SELECT report FROM observation WHERE source = ? AND report IN ({placeholders}) ORDER BY report',
        (source, *numbers),
    )
    return [row['report'] for row in rows]
