def find_batch(connection, batch):
    result = connection.execute('SELECT * FROM input_batch WHERE batch = ?', (batch,)).fetchone()
    return dict(result) if result else None


def lines_for_batch(connection, batch, *, source=False):
    columns = 'position, event, report, disposition, reason, message'
    if source:
        columns += ', line'
    return [dict(row) for row in connection.execute(
        f'SELECT {columns} FROM batch_line WHERE batch = ? ORDER BY position', (batch,))]


def groups_for_batch(connection, batch):
    return [dict(row) for row in connection.execute(
        'SELECT event, state, reason FROM batch_group WHERE batch = ? ORDER BY rowid', (batch,))]


def batches(connection, *, sealed=False):
    """Return every received package with its line dispositions and groups.

    With ``sealed`` the original text of each submitted line travels with the
    record, so a release can be recomputed and re-split from the material that
    was on hand at the time of receipt. The live workspace omits that text.
    """
    result = []
    for row in connection.execute('SELECT * FROM input_batch ORDER BY revision'):
        item = dict(row)
        item['lines'] = lines_for_batch(connection, item['batch'], source=sealed)
        item['groups'] = groups_for_batch(connection, item['batch'])
        result.append(item)
    return result


def reports_for_batch(connection, batch):
    return [dict(row) for row in connection.execute('SELECT * FROM observation WHERE batch = ? ORDER BY position', (batch,))]


def reports(connection):
    return [dict(row) for row in connection.execute('SELECT * FROM observation ORDER BY event, source, report')]


def insert_batch(connection, receipt, records):
    connection.execute('''INSERT INTO input_batch (batch, source, sha256, count, line_count, revision)
                          VALUES (:batch, :source, :sha256, :count, :line_count, :revision)''', receipt)
    connection.executemany('''INSERT INTO batch_line
      (batch, position, event, report, line, disposition, reason, message)
      VALUES (:batch, :position, :event, :report, :line, :disposition, :reason, :message)''',
      ({**line, 'batch': receipt['batch']} for line in receipt['lines']))
    connection.executemany('''INSERT INTO batch_group (batch, event, state, reason)
                              VALUES (?, ?, ?, ?)''',
      ((receipt['batch'], group['event'], group['state'], group['reason']) for group in receipt['groups']))
    connection.executemany('''INSERT INTO observation
      (source, report, batch, position, event, band, site, kind, observed_at, recorded_at)
      VALUES (:source, :report, :batch, :position, :event, :band, :site, :kind, :observed_at, :recorded_at)''',
      ({**entry['record'], 'source': receipt['source'], 'batch': receipt['batch'], 'position': entry['position']}
       for entry in records))


def claimed_report_numbers(connection, source, numbers):
    numbers = list(numbers)
    if not numbers:
        return []
    placeholders = ','.join('?' for _ in numbers)
    rows = connection.execute(
        f'SELECT report FROM observation WHERE source = ? AND report IN ({placeholders}) ORDER BY report',
        (source, *numbers),
    )
    return [row['report'] for row in rows]
