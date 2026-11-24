from . import batch_repository as records
from .batch_io import parse_batch
from .database import advance, current_revision
from .errors import DomainError


def prepare(connection, payload, expected=None):
    batch, source, reports, sha = parse_batch(payload)
    previous = records.find_batch(connection, batch)
    if previous:
        if previous['sha256'] != sha:
            raise DomainError('batch_conflict', '该包编号已被不同内容占用。', 409)
        return {**previous, 'replayed': True}, reports
    current = current_revision(connection)
    if expected is not None and current != expected:
        raise DomainError('stale_revision', '试算所用修订已变化，请刷新后重新试算。', 409)
    duplicates = records.claimed_report_numbers(connection, source, [row['report'] for row in reports])
    if duplicates:
        raise DomainError('report_conflict', f'该来源已接收报文 {duplicates[0]}，整包未接收。', 409)
    return dict(batch=batch, source=source, sha256=sha, count=len(reports), revision=current + 1, replayed=False), reports


def ingest(connection, payload, expected=None):
    receipt, reports = prepare(connection, payload, expected)
    if not receipt['replayed']:
        advance(connection)
        records.insert_batch(connection, receipt, reports)
    return receipt


def receipt(connection, batch):
    previous = records.find_batch(connection, batch)
    if not previous:
        raise DomainError('unknown_batch', '未找到采集包。', 404)
    return {**previous, 'reports': records.reports_for_batch(connection, batch)}
