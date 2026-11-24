"""Merge per-explanation adjudications into one workbench projection.

A ruling is final only when every feasible explanation agrees on the state,
ring root, UTC moment, site and kind. Otherwise the encounter is held pending.
A movement segment is certified only under the same identity and endpoints in
every explanation; partial movements are reported as pending with one
supporting and one failing explanation plus the cause of failure.
"""
from collections import defaultdict

from ..coverage import by_site

CLAIM_KEYS = ('root', 'observed_at', 'site', 'kind')


def _signature(event):
    if event['state'] != 'confirmed':
        return ('held', event['reason'])
    return ('confirmed', *(event[key] for key in CLAIM_KEYS))


def _merged_candidate(views):
    base = {key: value for key, value in views[0].items() if key != 'explanation'}
    base['views'] = [
        {'explanation': view['explanation'], 'root': view['root'],
         'valid_band': view['valid_band'], 'proofs': view['proofs']}
        for view in views]
    roots = sorted({view['root'] for view in views})
    base['root'] = roots[0] if len(roots) == 1 else None
    base['valid_band'] = all(view['valid_band'] for view in views)
    base['proofs'] = sorted({proof for view in views for proof in view['proofs']})
    return base


def _view(code, event):
    view = {'explanation': code, 'state': event['state'], 'reason': event.get('reason')}
    if event['state'] == 'confirmed':
        view.update({key: event[key] for key in CLAIM_KEYS})
    return view


def merge_encounters(evaluations):
    if not evaluations:
        return []
    by_event = defaultdict(list)
    for evaluation in evaluations:
        for event in evaluation['events']:
            by_event[event['event']].append((evaluation['explanation'].code, event))

    merged = []
    for event_ref in sorted(by_event):
        outlooks = by_event[event_ref]
        signatures = {_signature(event) for _, event in outlooks}
        candidate_views = defaultdict(list)
        for code, event in outlooks:
            for candidate in event['candidates']:
                candidate_views[(candidate['source'], candidate['report'])].append(
                    {**candidate, 'explanation': code})
        candidates = [_merged_candidate(candidate_views[key]) for key in sorted(candidate_views)]
        views = [_view(code, event) for code, event in outlooks]
        if len(signatures) == 1 and outlooks[0][1]['state'] == 'confirmed':
            winner = outlooks[0][1]
            merged.append({'event': event_ref, 'state': 'confirmed', 'reason': winner['reason'],
                           'root': winner['root'], 'observed_at': winner['observed_at'],
                           'site': winner['site'], 'kind': winner['kind'],
                           'candidates': candidates, 'views': views})
        else:
            uniform_hold = len(signatures) == 1
            reason = outlooks[0][1]['reason'] if uniform_hold else 'explanation_divergence'
            merged.append({'event': event_ref, 'state': 'held', 'reason': reason,
                           'root': None, 'observed_at': None, 'site': None, 'kind': None,
                           'candidates': candidates, 'views': views})
    return merged


def _segment_map(evaluations):
    mapped = defaultdict(dict)
    for evaluation in evaluations:
        code = evaluation['explanation'].code
        for track in evaluation['routes']:
            for segment in track['segments']:
                mapped[(segment['from_event'], segment['to_event'])][code] = {
                    'root': track['root'], **segment}
    return mapped


def _gap_index(evaluations):
    gaps = defaultdict(dict)
    for evaluation in evaluations:
        code = evaluation['explanation'].code
        for track in evaluation['routes']:
            for gap in track['gaps']:
                for event_ref in gap['events']:
                    gaps[event_ref].setdefault(code, {'root': track['root'], **gap})
    return gaps


def _blocking_report(events_by_code, event_ref, code):
    event = events_by_code[code].get(event_ref)
    if not event or event['state'] != 'held':
        return None
    top_priority = max(row['priority'] for row in event['candidates'])
    top = [row for row in event['candidates'] if row['priority'] == top_priority]
    chosen = sorted(top, key=lambda row: (row['observed_at'], row['source'], row['report']))[0]
    return {'event': event_ref, 'source': chosen['source'], 'report': chosen['report']}


def _failure_reason(segment_key, code, evaluation, gaps, events_by_code):
    start_ref, end_ref = segment_key
    event_map = {event['event']: event for event in evaluation['events']}
    for ref in segment_key:
        gap = gaps.get(ref, {}).get(code)
        if gap:
            return {'reason': gap['reason'], 'blocking_event': ref,
                    'blocking_report': _blocking_report(events_by_code, ref, code)}
    start, end = event_map.get(start_ref), event_map.get(end_ref)
    if start is None or end is None or start['state'] != 'confirmed' or end['state'] != 'confirmed':
        missing = next(ref for ref in segment_key
                       if event_map.get(ref, {}).get('state') != 'confirmed')
        return {'reason': 'held_endpoint', 'blocking_event': missing,
                'blocking_report': _blocking_report(events_by_code, missing, code)}
    if start['root'] != end['root']:
        return {'reason': 'root_divergence', 'blocking_event': None, 'blocking_report': None}
    return {'reason': 'not_adjacent', 'blocking_event': None, 'blocking_report': None}


def merge_routes(evaluations):
    segment_views = _segment_map(evaluations)
    gaps = _gap_index(evaluations)
    events_by_code = {evaluation['explanation'].code:
                      {event['event']: event for event in evaluation['events']}
                      for evaluation in evaluations}
    all_codes = [evaluation['explanation'].code for evaluation in evaluations]

    certified, pending = [], []
    for key, per_code in sorted(segment_views.items()):
        identity = {(row['root'], row['from_site'], row['to_site'], row['start'], row['end'], row['kind'])
                    for row in per_code.values()}
        if len(per_code) == len(all_codes) and len(identity) == 1:
            sample = next(iter(per_code.values()))
            certified.append({'key': key, **sample, 'explanations': sorted(per_code)})
            continue
        supporting = next(code for code in all_codes if code in per_code)
        failing = next((code for code in all_codes if code not in per_code), None)
        if failing is None:
            baseline = per_code[supporting]
            failing = next(code for code, row in per_code.items()
                           if (row['root'], row['from_site'], row['to_site'], row['start'], row['end'])
                           != (baseline['root'], baseline['from_site'], baseline['to_site'],
                               baseline['start'], baseline['end']))
        evaluation = next(item for item in evaluations if item['explanation'].code == failing)
        pending.append({
            'from_event': key[0], 'to_event': key[1],
            'supporting': {'explanation': supporting, **per_code[supporting]},
            'failing': {'explanation': failing,
                        **_failure_reason(key, failing, evaluation, gaps, events_by_code)},
        })

    confirmed_events = defaultdict(set)
    gap_cards = defaultdict(lambda: defaultdict(list))
    roots = set()
    for evaluation in evaluations:
        code = evaluation['explanation'].code
        confirmed_by_root = defaultdict(set)
        for event in evaluation['events']:
            if event['state'] == 'confirmed':
                confirmed_by_root[event['root']].add(event['event'])
        for track in evaluation['routes']:
            roots.add(track['root'])
            confirmed_events[track['root']].update(confirmed_by_root[track['root']])
            for gap in track['gaps']:
                gap_cards[track['root']][(gap['start'], gap['end'], gap['reason'])].append(
                    (code, gap['events']))
    route_cards = []
    for root in sorted(roots | {segment['root'] for segment in certified}):
        segments = sorted((row for row in certified if row['root'] == root),
                          key=lambda row: (row['start'], row['end']))
        merged_gaps = []
        for (start, end, reason), appearances in sorted(gap_cards[root].items()):
            events = sorted({ref for _, refs in appearances for ref in refs})
            merged_gaps.append({'start': start, 'end': end, 'reason': reason, 'events': events,
                                'explanations': sorted({code for code, _ in appearances})})
        route_cards.append({'root': root, 'event_count': len(confirmed_events[root]),
                            'segments': segments, 'gaps': merged_gaps})
    return route_cards, sorted(pending, key=lambda row: (row['from_event'], row['to_event']))


def assemble_projection(revision, catalog, batches, reports, links, groups, evaluations):
    encounters = merge_encounters(evaluations)
    routes, pending_moves = merge_routes(evaluations)
    explanation_cards = [{
        'code': evaluation['explanation'].code,
        'choices': [{'group': group_id, 'proof': proof}
                    for group_id, proof in evaluation['explanation'].choices],
        'proofs': sorted(link['proof'] for link in evaluation['explanation'].links),
    } for evaluation in evaluations]
    return {
        'format': 2, 'revision': revision, 'catalog': catalog, 'batches': batches, 'links': links,
        'groups': groups, 'explanations': explanation_cards,
        'encounters': encounters, 'routes': routes, 'pending_moves': pending_moves,
        'coverage': by_site(catalog['sites'], encounters, routes),
    }
