from . import correction_engine


def find_batch(connection, batch):
    result = connection.execute('SELECT * FROM input_batch WHERE batch = ?', (batch,)).fetchone()
    return dict(result) if result else None


def batches(connection):
    return [dict(row) for row in connection.execute(
        'SELECT batch, source, sha256, count, revision FROM input_batch ORDER BY revision')]


def reports_for_batch(connection, batch):
    effective, original = correction_engine.resolution_map(connection)
    result = []
    for row in connection.execute('SELECT * FROM observation WHERE batch = ? ORDER BY position', (batch,)):
        item = dict(row)
        key = (item['source'], item['report'])
        item['original_event'] = original[key]
        item['event'] = effective[key]
        result.append(item)
    return result


def reports(connection):
    return [dict(row) for row in connection.execute('SELECT * FROM observation ORDER BY event, source, report')]


def insert_batch(connection, receipt, records, routing):
    connection.execute('''INSERT INTO input_batch (batch, source, sha256, count, revision, assignment_key)
                          VALUES (:batch, :source, :sha256, :count, :revision, :assignment_key)''', receipt)
    routed = {row['position']: row for row in routing}
    observation_rows = []
    routing_rows = []
    for position, record in enumerate(records, 1):
        target = routed[position]
        observation_rows.append({**record, 'source': receipt['source'], 'batch': receipt['batch'],
                                 'position': position, 'event': target['event']})
        if target['original_event'] != target['event']:
            routing_rows.append({'batch': receipt['batch'], 'position': position,
                                 'source': receipt['source'], 'report': record['report'],
                                 'original_event': target['original_event'], 'event': target['event']})
    connection.executemany('''INSERT INTO observation
      (source, report, batch, position, event, band, site, kind, observed_at, recorded_at)
      VALUES (:source, :report, :batch, :position, :event, :band, :site, :kind, :observed_at, :recorded_at)''',
      observation_rows)
    connection.executemany('''INSERT INTO intake_routing
      (batch, position, source, report, original_event, event)
      VALUES (:batch, :position, :source, :report, :original_event, :event)''', routing_rows)


def claimed_report_numbers(connection, source, numbers):
    placeholders = ','.join('?' for number in numbers)
    rows = connection.execute(
        f'SELECT report FROM observation WHERE source = ? AND report IN ({placeholders}) ORDER BY report',
        (source, *numbers),
    )
    return [row['report'] for row in rows]
