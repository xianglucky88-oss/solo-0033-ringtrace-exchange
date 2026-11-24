from .errors import DomainError
from .workbench import current


PAGE_SIZE = 25


def _row_matches(row, query):
    if query.get('band_mode') == 'root':
        roots = {view['root'] for view in row.get('views', ())} or {row['root']}
        if query.get('band') not in roots:
            return False
    elif 'band' in query and row['band'] != query['band']:
        return False
    if 'reference' in query and row['event'] != query['reference']:
        return False
    if 'source' in query and row['source'] != query['source']:
        return False
    time = row['observed_at']
    return ('from' not in query or query['from'] <= time) and ('until' not in query or time < query['until'])


def search(connection, query):
    snapshot = current(connection)
    revision = snapshot['revision']
    if query.get('at', revision) != revision:
        raise DomainError('stale_revision', '检索修订已变化，请从首页重新查询。', 409)
    hits = []
    for event in snapshot['encounters']:
        for row in event['candidates']:
            if _row_matches(row, query):
                hits.append({**row, 'decision': event['state'], 'reason': event['reason']})
    hits.sort(key=lambda row: (row['observed_at'], row['source'], row['report']))
    offset = query['offset']
    end = offset + PAGE_SIZE
    return {'revision': revision, 'total': len(hits), 'offset': offset, 'items': hits[offset:end],
            'next_offset': end if end < len(hits) else None}
