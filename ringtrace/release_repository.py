from datetime import datetime, timezone


def headers(connection):
    return [dict(row) for row in connection.execute('SELECT revision, sha256, created_at FROM release ORDER BY revision DESC')]


def find(connection, revision):
    row = connection.execute('SELECT * FROM release WHERE revision = ?', (revision,)).fetchone()
    return dict(row) if row else None


def add(connection, revision, sha, payload):
    row = {'revision': revision, 'sha256': sha, 'payload': payload,
           'created_at': datetime.now(timezone.utc).isoformat(timespec='seconds').replace('+00:00', 'Z')}
    connection.execute('INSERT INTO release VALUES (:revision, :sha256, :payload, :created_at)', row)
    return row
