def links(connection):
    return [dict(row) for row in connection.execute('SELECT * FROM band_link ORDER BY effective_at, proof')]


def groups(connection):
    rows = connection.execute('SELECT * FROM link_group ORDER BY group_id')
    result = []
    for row in rows:
        group = dict(row)
        group['members'] = [dict(member) for member in connection.execute(
            'SELECT * FROM band_link WHERE group_id = ? ORDER BY effective_at, proof', (group['group_id'],))]
        result.append(group)
    return result


def find_group(connection, group_id):
    row = connection.execute('SELECT * FROM link_group WHERE group_id = ?', (group_id,)).fetchone()
    return dict(row) if row else None


def find_group_for_band(connection, new_band):
    row = connection.execute('SELECT * FROM link_group WHERE new_band = ?', (new_band,)).fetchone()
    return dict(row) if row else None


def insert_link(connection, row):
    connection.execute('''INSERT INTO band_link
        (proof, old_band, new_band, effective_at, revision, group_id, state, excluded_note)
        VALUES (:proof, :old_band, :new_band, :effective_at, :revision,
                :group_id, COALESCE(:state, 'active'), :excluded_note)''',
        {**row, 'group_id': row.get('group_id'), 'state': row.get('state', 'active'),
         'excluded_note': row.get('excluded_note')})


def insert_group(connection, group):
    connection.execute('''INSERT INTO link_group (group_id, new_band, state, chosen_proof, revision, excluded_note)
                          VALUES (:group_id, :new_band, :state, :chosen_proof, :revision, :excluded_note)''',
        {**group, 'chosen_proof': group.get('chosen_proof'), 'excluded_note': group.get('excluded_note')})


def decide_group(connection, group_id, chosen_proof, revision):
    connection.execute('''UPDATE link_group SET state = 'decided', chosen_proof = ?, revision = ?
                          WHERE group_id = ?''', (chosen_proof, revision, group_id))


def mark_link(connection, proof, state, note):
    connection.execute('UPDATE band_link SET state = ?, excluded_note = ? WHERE proof = ?', (state, note, proof))
