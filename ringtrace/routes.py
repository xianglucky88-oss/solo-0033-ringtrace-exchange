from collections import defaultdict
from datetime import datetime
from itertools import groupby, pairwise


def span(event):
    if 'feasible_from' in event:
        return event['feasible_from'], event['feasible_until']
    return event['observed_at'], event['observed_at']


def seconds_between(start, end):
    return int((datetime.fromisoformat(end) - datetime.fromisoformat(start)).total_seconds())


def overlaps(lower, upper, start, end):
    return not (upper < start or lower > end)


def by_root(encounters):
    points, holds = defaultdict(list), defaultdict(list)
    range_mode = any('feasible_from' in event for event in encounters)
    for event in encounters:
        if event['state'] == 'confirmed':
            points[event['root']].append(event)
            continue
        candidates = event['candidates']
        priority = max(row['priority'] for row in candidates)
        top = [row for row in candidates if row['priority'] == priority]
        start = min(row['observed_at'] for row in top)
        end = max(row['observed_end'] or row['observed_at'] for row in top)
        for root in {row['root'] for row in top}:
            holds[root].append((start, end, event['event']))
    return points, holds, range_mode


def legacy_timeline(root, points, holds):
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
        seconds = seconds_between(start, end)
        segments.append({'from_event': a['event'], 'to_event': b['event'], 'from_site': a['site'],
                         'to_site': b['site'], 'start': start, 'end': end, 'elapsed_seconds': seconds,
                         'kind': 'stay' if a['site'] == b['site'] else 'move'})
    return {'root': root, 'event_count': len(points), 'segments': segments,
            'gaps': sorted(gaps, key=lambda gap: (gap['start'], gap['end'], gap['reason']))}


def range_timeline(root, points, holds):
    ordered = sorted(points, key=lambda row: (span(row)[0], span(row)[1], row['event']))
    segments, gaps = [], []
    ordered_holds = sorted(holds)
    for index, left_event in enumerate(ordered[:-1]):
        right_event = ordered[index + 1]
        left_lower, left_upper = span(left_event)
        right_lower, right_upper = span(right_event)
        if not (left_upper < right_lower):
            gaps.append({'start': max(left_lower, right_lower), 'end': min(left_upper, right_upper),
                         'reason': 'same_time',
                         'events': sorted([left_event['event'], right_event['event']])})
            continue
        touching = sorted(hold[2] for hold in ordered_holds
                          if overlaps(hold[0], hold[1], left_upper, right_lower))
        if touching:
            gaps.append({'start': left_upper, 'end': right_lower, 'reason': 'held_between',
                         'reasons': ['held_between'], 'events': touching})
            continue
        segments.append({
            'from_event': left_event['event'], 'to_event': right_event['event'],
            'from_site': left_event['site'], 'to_site': right_event['site'],
            'start': left_lower, 'start_until': left_upper, 'end': right_lower, 'end_until': right_upper,
            'min_elapsed_seconds': seconds_between(left_upper, right_lower),
            'max_elapsed_seconds': seconds_between(left_lower, right_upper),
            'kind': 'stay' if left_event['site'] == right_event['site'] else 'move',
        })
    # A third confirmed encounter of the same root may share a feasible second with either
    # endpoint or be strictly sandwiched between two ordered encounters: when its observation
    # is itself uncertain (a closed range), the span cannot be read as one provable movement.
    # Definite-instant encounters already have fixed positions and are covered by adjacency.
    for middle_index, middle in enumerate(ordered[1:-1], start=1):
        if span(middle)[0] == span(middle)[1]:
            continue
        middle_lower, middle_upper = span(middle)
        left_event = next((candidate for candidate in reversed(ordered[:middle_index])
                           if span(candidate)[1] < middle_upper), None)
        right_event = next((candidate for candidate in ordered[middle_index + 1:]
                            if span(candidate)[0] > middle_lower), None)
        if left_event is None or right_event is None:
            continue
        left_upper = span(left_event)[1]
        right_lower = span(right_event)[0]
        if left_upper < right_lower and overlaps(middle_lower, middle_upper, left_upper, right_lower):
            gaps.append({'start': left_upper, 'end': right_lower, 'reason': 'intervening_event',
                         'reasons': ['intervening_event'], 'events': [middle['event']]})
    return {'root': root, 'event_count': len(points), 'segments': segments,
            'gaps': sorted(gaps, key=lambda gap: (gap['start'], gap['end'], gap['reason'], gap['events']))}


def build_routes(encounters):
    points, holds, range_mode = by_root(encounters)
    timeline = range_timeline if range_mode else legacy_timeline
    return [timeline(root, points[root], holds[root]) for root in sorted(points.keys() | holds.keys())]
