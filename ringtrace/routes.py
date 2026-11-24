from collections import defaultdict
from datetime import datetime
from itertools import groupby, pairwise


def by_root(encounters):
    points, holds = defaultdict(list), defaultdict(list)
    for event in encounters:
        if event['state'] == 'confirmed':
            points[event['root']].append(event)
            continue
        candidates = event['candidates']
        priority = max(row['priority'] for row in candidates)
        top = [row for row in candidates if row['priority'] == priority]
        start = min(row['observed_at'] for row in top)
        end = max(row['observed_at'] for row in top)
        for root in {row['root'] for row in top}:
            holds[root].append((start, end, event['event']))
    return points, holds


def timeline(root, points, holds):
    groups = [(at, list(group)) for at, group in groupby(
        sorted(points, key=lambda row: (row['observed_at'], row['event'])), key=lambda row: row['observed_at'])]
    segments, gaps = [], []
    for at, group in groups:
        if len(group) > 1:
            gaps.append({'start': at, 'end': at, 'reason': 'same_time', 'events': [row['event'] for row in group]})
    ordered_holds = sorted(holds)
    active = []
    next_hold = 0
    for (start, left), (end, right) in pairwise(groups):
        active = [hold for hold in active if hold[1] >= start]
        while next_hold < len(ordered_holds) and ordered_holds[next_hold][0] <= end:
            hold = ordered_holds[next_hold]
            if hold[1] >= start:
                active.append(hold)
            next_hold += 1
        if len(left) != 1 or len(right) != 1:
            continue
        if active:
            gaps.append({'start': start, 'end': end, 'reason': 'held_between',
                         'events': sorted(hold[2] for hold in active)})
            continue
        a, b = left[0], right[0]
        seconds = int((datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds())
        segments.append({'from_event': a['event'], 'to_event': b['event'], 'from_site': a['site'],
                         'to_site': b['site'], 'start': start, 'end': end, 'elapsed_seconds': seconds,
                         'kind': 'stay' if a['site'] == b['site'] else 'move'})
    return {'root': root, 'event_count': len(points), 'segments': segments,
            'gaps': sorted(gaps, key=lambda gap: (gap['start'], gap['end'], gap['reason']))}


def build_routes(encounters):
    points, holds = by_root(encounters)
    return [timeline(root, points[root], holds[root]) for root in sorted(points.keys() | holds.keys())]
