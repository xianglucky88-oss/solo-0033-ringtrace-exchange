def corrections(connection):
    return [dict(row) for row in connection.execute(
        'SELECT * FROM event_correction ORDER BY revision')]


def list_with_assignments(connection):
    rows = []
    for correction in corrections(connection):
        assignments = [dict(row) for row in connection.execute(
            'SELECT source, report, original_event, event FROM event_assignment '
            'WHERE correction_revision = ? ORDER BY source, report', (correction['revision'],))]
        rows.append({**correction, 'assignments': assignments})
    return rows


def insert_correction(connection, row):
    connection.execute('''INSERT INTO event_correction
        (revision, source_event, first_event, second_event)
        VALUES (:revision, :source_event, :first_event, :second_event)''', row)
    connection.executemany('''INSERT INTO event_assignment
        (source, report, correction_revision, original_event, event)
        VALUES (:source, :report, :correction_revision, :original_event, :event)''', row['assignments'])


def assignments(connection):
    return [dict(row) for row in connection.execute(
        'SELECT * FROM event_assignment ORDER BY correction_revision, source, report')]


def routed_reports(connection):
    return [dict(row) for row in connection.execute(
        'SELECT source, report, original_event, event FROM intake_routing ORDER BY batch, position')]


def insert_routing(connection, rows):
    connection.executemany('''INSERT INTO intake_routing
        (batch, position, source, report, original_event, event)
        VALUES (:batch, :position, :source, :report, :original_event, :event)''', rows)


def assignment_key_exists(connection, key):
    if not key:
        return False
    return connection.execute(
        'SELECT 1 FROM input_batch WHERE assignment_key = ? LIMIT 1', (key,)).fetchone() is not None


def find_assignment_key(connection, batch):
    row = connection.execute(
        'SELECT assignment_key FROM input_batch WHERE batch = ?', (batch,)).fetchone()
    return row['assignment_key'] if row else None
