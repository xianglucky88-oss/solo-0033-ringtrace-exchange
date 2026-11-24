from . import correction_engine, correction_repository
from .errors import DomainError
from .workbench import current


PAGE_SIZE = 25


def reference_matches(row, wanted, aliases):
    if row['event'] == wanted:
        return True
    return wanted in aliases and row['event'] in aliases[wanted]


def matches(row, query, aliases):
    band_key = 'root' if query.get('band_mode') == 'root' else 'band'
    exact = [('source', 'source'), ('band', band_key)]
    if any(name in query and row[key] != query[name] for name, key in exact):
        return False
    if 'reference' in query and not reference_matches(row, query['reference'], aliases):
        return False
    moment = row['observed_at']
    return ('from' not in query or query['from'] <= moment) and ('until' not in query or moment < query['until'])


def search(connection, query):
    snapshot = current(connection)
    revision = snapshot['revision']
    if query.get('at', revision) != revision:
        raise DomainError('stale_revision', '检索修订已变化，请从首页重新查询。', 409)
    aliases = correction_engine.event_aliases(
        correction_repository.corrections(connection),
        correction_engine.effective_reports(connection))
    hits = []
    for event in snapshot['encounters']:
        for row in event['candidates']:
            if matches(row, query, aliases):
                hits.append({**row, 'decision': event['state'], 'reason': event['reason']})
    hits.sort(key=lambda row: (row['observed_at'], row['source'], row['report']))
    offset = query['offset']
    end = offset + PAGE_SIZE
    return {'revision': revision, 'total': len(hits), 'offset': offset, 'items': hits[offset:end],
            'next_offset': end if end < len(hits) else None}
