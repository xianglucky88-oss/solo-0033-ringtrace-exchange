def links(connection):
    return [dict(row) for row in connection.execute('SELECT * FROM band_link ORDER BY effective_at, proof')]


def insert_link(connection, row):
    connection.execute('''INSERT INTO band_link (proof, old_band, new_band, effective_at, revision)
                          VALUES (:proof, :old_band, :new_band, :effective_at, :revision)''', row)
