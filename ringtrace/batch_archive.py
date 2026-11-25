from .batch_io import split
from .codec import canonical, decode, digest
from .errors import DomainError

FIELDS = ('report', 'event', 'band', 'site', 'kind')


def archived_rows(receipt):
    """Return every submitted line in its original order, received or not."""
    return [decode(line['line'].encode('utf-8'))
            for line in sorted(receipt['lines'], key=lambda row: row['position'])]


def reconstruct(receipt):
    """Rebuild the canonical source package from the recorded lines.

    Rejected lines are kept as well, so the rebuilt package is byte for byte
    the one that was submitted, including its original array order and time
    spellings.
    """
    return {'batch': receipt['batch'], 'source': receipt['source'], 'reports': archived_rows(receipt)}


def verified_payload(receipt):
    positions = sorted(line['position'] for line in receipt['lines'])
    if positions != list(range(1, receipt['line_count'] + 1)):
        raise DomainError('damaged_batch', '归档报文数或行号不匹配。', 409)
    payload = canonical(reconstruct(receipt))
    if digest(payload) != receipt['sha256']:
        raise DomainError('damaged_batch', '归档报文摘要不匹配。', 409)
    return payload


def legacy_payload(receipt, rows):
    """Rebuild a package archived before line dispositions were recorded."""
    ordered = sorted(rows, key=lambda row: row['position'])
    if [row['position'] for row in ordered] != list(range(1, receipt['count'] + 1)):
        raise DomainError('damaged_batch', '归档报文数或行号不匹配。', 409)
    reports = []
    for row in ordered:
        original = {field: row[field] for field in FIELDS}
        original['observed_at'] = row['recorded_at']
        reports.append(original)
    payload = canonical({'batch': receipt['batch'], 'source': receipt['source'], 'reports': reports})
    if digest(payload) != receipt['sha256']:
        raise DomainError('damaged_batch', '归档报文摘要不匹配。', 409)
    return payload


def verify_input_batches(receipts, reports):
    """Re-check every archived package and its line split.

    Packages recorded with line dispositions are re-split using only the
    material available when each one was received: earlier packages are
    replayed first and later supplemental receipts do not change an earlier
    conclusion. A line recorded as received that the split now refuses, or one
    refused that it now accepts, is reported as a mismatch; so is a received
    report that the recomputed split does not allow, or an allowed report that
    is missing from the sealed findings. Legacy packages archived before line
    dispositions existed are verified from their original content and treated
    as fully received.
    """
    ordered = sorted(receipts, key=lambda row: row['revision'])
    if len({receipt['batch'] for receipt in ordered}) != len(ordered):
        raise DomainError('damaged_batch', '封存中的采集包编号重复。', 409)
    by_batch = {}
    for row in reports:
        by_batch.setdefault(row['batch'], []).append(row)
    claimed = {}
    mismatches = []
    for receipt in ordered:
        source = receipt['source']
        already = claimed.setdefault(source, set())
        lines = receipt.get('lines')
        if not lines:
            rows = by_batch.get(receipt['batch'], [])
            legacy_payload(receipt, rows)
            already.update(row['report'] for row in rows)
            continue
        verified_payload(receipt)
        rows = archived_rows(receipt)
        found = [line['event'] for line in sorted(lines, key=lambda row: row['position'])]
        _, recomputed, accepted = split(found, rows, set(already))
        recorded = {line['position']: line for line in lines}
        flagged = set()
        for line in recomputed:
            previous = recorded.get(line['position'], {})
            if previous.get('disposition') != line['disposition']:
                flagged.add(line['position'])
                mismatches.append({'batch': receipt['batch'], 'position': line['position'],
                                   'recorded': previous.get('disposition'),
                                   'recomputed': line['disposition'], 'reason': line['reason']})
        expected_positions = {entry['position'] for entry in accepted}
        present_positions = {row['position'] for row in by_batch.get(receipt['batch'], [])}
        for position in sorted(present_positions - expected_positions - flagged):
            mismatches.append({'batch': receipt['batch'], 'position': position,
                               'recorded': 'accepted', 'recomputed': 'rejected',
                               'reason': 'misreceived'})
        for position in sorted(expected_positions - present_positions - flagged):
            mismatches.append({'batch': receipt['batch'], 'position': position,
                               'recorded': 'rejected', 'recomputed': 'accepted',
                               'reason': 'missed'})
        already.update(record['record']['report'] for record in accepted)
    if mismatches:
        raise DomainError('damaged_batch', '封存中的接收分流与复算不一致，存在误收或漏收。', 409,
                          {'mismatches': mismatches})
    return len(ordered)
