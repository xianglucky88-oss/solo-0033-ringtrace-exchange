from collections import defaultdict

from .codec import canonical, digest
from .errors import DomainError


def reconstruct(batch, reports):
    fields = ('report', 'event', 'band', 'site', 'kind')
    rows = []
    for row in sorted(reports, key=lambda row: row['position']):
        original = {field: row[field] for field in fields}
        original['event'] = row.get('original_event', row['event'])
        original['observed_at'] = row['recorded_at']
        rows.append(original)
    return {'batch': batch['batch'], 'source': batch['source'], 'reports': rows}


def verified_payload(receipt, reports):
    positions = sorted(row['position'] for row in reports)
    if positions != list(range(1, receipt['count'] + 1)):
        raise DomainError('damaged_batch', '归档报文数或行号不匹配。', 409)
    if any(row['source'] != receipt['source'] or row['batch'] != receipt['batch'] for row in reports):
        raise DomainError('damaged_batch', '归档报文来源或包号不匹配。', 409)
    payload = canonical(reconstruct(receipt, reports))
    if digest(payload) != receipt['sha256']:
        raise DomainError('damaged_batch', '归档报文摘要不匹配。', 409)
    return payload


def verify_input_batches(receipts, reports):
    by_batch = defaultdict(list)
    for row in reports:
        by_batch[row['batch']].append(row)
    expected = {item['batch'] for item in receipts}
    if len(expected) != len(receipts) or by_batch.keys() != expected:
        raise DomainError('damaged_batch', '封存中的采集包与报文归属不匹配。', 409)
    for receipt in receipts:
        verified_payload(receipt, by_batch[receipt['batch']])
    return len(receipts)
