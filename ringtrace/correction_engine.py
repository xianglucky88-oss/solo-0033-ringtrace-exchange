"""Resolve the current encounter reference of every received report.

The original event number written on a report is immutable. Encounter
corrections split a live encounter into two unused numbers and every
re-routed intake line confirms where an old paper number now belongs.
"""
from collections import defaultdict


def resolution_map(connection):
    """Return (effective_event, original_event) lookup keyed by (source, report)."""
    effective = {}
    original = {}
    for row in connection.execute('SELECT source, report, event FROM observation'):
        key = (row['source'], row['report'])
        effective[key] = row['event']
        original[key] = row['event']
    latest = {}
    for row in connection.execute(
            'SELECT source, report, correction_revision, event FROM event_assignment '
            'ORDER BY correction_revision'):
        latest[(row['source'], row['report'])] = row['event']
    for key, event in latest.items():
        effective[key] = event
    for row in connection.execute('SELECT source, report, original_event, event FROM intake_routing'):
        key = (row['source'], row['report'])
        original[key] = row['original_event']
        effective[key] = row['event']
    return effective, original


def effective_reports(connection):
    """All observations with their current effective event and preserved original number."""
    effective, original = resolution_map(connection)
    rows = []
    for row in connection.execute('SELECT * FROM observation ORDER BY event, source, report'):
        item = dict(row)
        key = (item['source'], item['report'])
        item['original_event'] = original[key]
        item['event'] = effective[key]
        rows.append(item)
    return rows


def live_events(reports):
    return {row['event'] for row in reports}


def reports_of_event(reports, reference):
    return [row for row in reports if row['event'] == reference]


def event_aliases(corrections, reports):
    """Map every original number that no longer resolves live to its live descendants."""
    aliases = defaultdict(set)
    live = live_events(reports)
    for row in reports:
        if row['original_event'] != row['event']:
            aliases[row['original_event']].add(row['event'])
    for correction in corrections:
        if correction['source_event'] not in live:
            aliases[correction['source_event']].update(
                (correction['first_event'], correction['second_event']))
    return {key: sorted(values) for key, values in aliases.items()}
