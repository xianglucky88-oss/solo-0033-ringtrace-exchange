def domain_events(snapshot):
    return {item['event']: item for item in snapshot['encounters']}


def all_segments(snapshot):
    return {(track['root'], segment['from_event'], segment['to_event']): {'root': track['root'], **segment}
            for track in snapshot['routes'] for segment in track['segments']}


def changes(before, after):
    return [{'key': key, 'before': before.get(key), 'after': after.get(key)}
            for key in sorted(before.keys() | after.keys()) if before.get(key) != after.get(key)]


def compare(before, after):
    return {'from_revision': before['revision'], 'to_revision': after['revision'],
            'encounters': changes(domain_events(before), domain_events(after)),
            'segments': changes(all_segments(before), all_segments(after))}
