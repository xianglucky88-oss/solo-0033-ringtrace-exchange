from itertools import groupby


def enrich(report, bands, sources):
    root, valid, proofs = bands.locate(report['band'], report['observed_at'])
    return {**report, 'root': root, 'valid_band': valid, 'proofs': proofs,
            'priority': sources[report['source']]['priority']}


def claim(row):
    return tuple(row[key] for key in ('root', 'observed_at', 'site', 'kind'))


def decide(event, rows, bands, sources):
    candidates = [enrich(row, bands, sources) for row in rows]
    priority = max(row['priority'] for row in candidates)
    top = [row for row in candidates if row['priority'] == priority]
    if any(not row['valid_band'] for row in top):
        reason = 'inactive_band'
    elif len({claim(row) for row in top}) > 1:
        reason = 'peer_conflict'
    else:
        winner = top[0]
        discrepant = any(not row['valid_band'] or claim(row) != claim(winner) for row in candidates)
        return {'event': event, 'state': 'confirmed', 'reason': 'lower_disagreement' if discrepant else None,
                **dict(zip(('root', 'observed_at', 'site', 'kind'), claim(winner))), 'candidates': candidates}
    return {'event': event, 'state': 'held', 'reason': reason, 'candidates': candidates}


def adjudicate(rows, bands, sources):
    ordered = sorted(rows, key=lambda row: (row['event'], row['source'], row['report']))
    return [decide(event, group, bands, sources) for event, group in groupby(ordered, key=lambda row: row['event'])]
