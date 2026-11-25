from itertools import groupby


def interval(row):
    return row['observed_at'], row['observed_end'] or row['observed_at']


def enrich(row, bands, sources):
    lower, upper = interval(row)
    root, valid_lower, valid_upper = bands.valid_window(row['band'], lower, upper)
    _, instant_valid, proofs = bands.locate(row['band'], row['observed_at'])
    return {**row, 'root': root, 'valid_band': instant_valid,
            'valid_from': valid_lower, 'valid_until': valid_upper,
            'proofs': proofs, 'priority': sources[row['source']]['priority']}


def is_range_mode(candidates):
    return any(row['observed_end'] is not None for row in candidates)


def identity(row):
    return tuple(row[key] for key in ('root', 'site', 'kind'))


def instant_claim(row):
    return tuple(row[key] for key in ('root', 'observed_at', 'site', 'kind'))


def decide(event, rows, bands, sources):
    candidates = [enrich(row, bands, sources) for row in rows]
    range_mode = is_range_mode(candidates)
    priority = max(row['priority'] for row in candidates)
    top = [row for row in candidates if row['priority'] == priority]
    if any(row['valid_from'] > row['valid_until'] for row in top):
        reason = 'inactive_band'
    elif range_mode:
        if len({identity(row) for row in top}) > 1:
            reason = 'peer_conflict'
        else:
            shared_lower = max(row['valid_from'] for row in top)
            shared_upper = min(row['valid_until'] for row in top)
            if shared_lower > shared_upper:
                reason = 'no_common_second'
            else:
                winner = top[0]
                discrepant = any(
                    row['valid_from'] > row['valid_until'] or identity(row) != identity(winner)
                    for row in candidates)
                return {'event': event, 'state': 'confirmed',
                        'reason': 'lower_disagreement' if discrepant else None,
                        'root': winner['root'], 'site': winner['site'], 'kind': winner['kind'],
                        'feasible_from': shared_lower, 'feasible_until': shared_upper,
                        'candidates': candidates}
    elif len({instant_claim(row) for row in top}) > 1:
        reason = 'peer_conflict'
    else:
        winner = top[0]
        discrepant = any(not row['valid_band'] or instant_claim(row) != instant_claim(winner)
                         for row in candidates)
        return {'event': event, 'state': 'confirmed',
                'reason': 'lower_disagreement' if discrepant else None,
                'root': winner['root'], 'observed_at': winner['observed_at'],
                'site': winner['site'], 'kind': winner['kind'], 'candidates': candidates}
    held = {'event': event, 'state': 'held', 'reason': reason, 'candidates': candidates}
    if range_mode:
        held['blocked_from'] = min(row['observed_at'] for row in top)
        held['blocked_until'] = max(row['observed_end'] or row['observed_at'] for row in top)
    return held


def adjudicate(rows, bands, sources):
    ordered = sorted(rows, key=lambda row: (row['event'], row['source'], row['report']))
    return [decide(event, group, bands, sources) for event, group in groupby(ordered, key=lambda row: row['event'])]
