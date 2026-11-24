from . import batch_repository as records
from . import correction_engine, correction_repository
from .batch_io import parse_batch
from .codec import canonical, digest
from .database import advance, current_revision
from .errors import DomainError


def _routing_key(routing):
    return digest(canonical(routing)) if routing else ''


def _resolve_routing(connection, reports, routing):
    """Confirm every old paper number line-by-line against a live descendant event."""
    effective = correction_engine.effective_reports(connection)
    aliases = correction_engine.event_aliases(correction_repository.corrections(connection), effective)
    by_position = {row['position']: row for row in routing}
    resolved = []
    for index, row in enumerate(reports, 1):
        original = row['event']
        if index in by_position:
            target = by_position[index]['event']
            allowed = aliases.get(original, [])
            if target not in allowed:
                raise DomainError('routing_conflict',
                                  f'第 {index} 条报文原号 {original} 只能归入 {allowed or "仍在使用的原号"}。')
            resolved.append({'position': index, 'original_event': original, 'event': target})
        elif original in aliases:
            raise DomainError('routing_required',
                              f'第 {index} 条报文仍写旧号 {original}，须逐行确认归入哪个新号，整包不入账。')
        else:
            resolved.append({'position': index, 'original_event': original, 'event': original})
    return resolved


def prepare(connection, payload, expected=None):
    batch, source, reports, sha, routing = parse_batch(payload)
    assignment_key = _routing_key(routing)
    previous = records.find_batch(connection, batch)
    if previous:
        if previous['sha256'] != sha:
            raise DomainError('batch_conflict', '该包编号已被不同内容占用。', 409)
        if previous['assignment_key'] != assignment_key:
            raise DomainError('routing_conflict',
                              '同号包的逐行归属与原回执不一致，有改动即冲突。', 409)
        return {**previous, 'replayed': True}, reports, _stored_routing(connection, batch)
    current = current_revision(connection)
    if expected is not None and current != expected:
        raise DomainError('stale_revision', '试算所用修订已变化，请刷新后重新试算。', 409)
    duplicates = records.claimed_report_numbers(connection, source, [row['report'] for row in reports])
    if duplicates:
        raise DomainError('report_conflict', f'该来源已接收报文 {duplicates[0]}，整包未接收。', 409)
    resolved = _resolve_routing(connection, reports, routing)
    if correction_repository.assignment_key_exists(connection, assignment_key):
        raise DomainError('routing_conflict', '相同逐行归属已随其他采集包受理。', 409)
    receipt = dict(batch=batch, source=source, sha256=sha, count=len(reports),
                   revision=current + 1, replayed=False, assignment_key=assignment_key)
    return receipt, reports, resolved


def _stored_routing(connection, batch):
    rows = connection.execute(
        'SELECT position, original_event, event FROM intake_routing WHERE batch = ? ORDER BY position',
        (batch,)).fetchall()
    return [dict(row) for row in rows]


def ingest(connection, payload, expected=None):
    receipt, reports, routing = prepare(connection, payload, expected)
    if not receipt['replayed']:
        advance(connection)
        records.insert_batch(connection, receipt, reports, routing)
    return {key: value for key, value in receipt.items() if key != 'assignment_key'}


def receipt(connection, batch):
    previous = records.find_batch(connection, batch)
    if not previous:
        raise DomainError('unknown_batch', '未找到采集包。', 404)
    return {key: value for key, value in previous.items() if key != 'assignment_key'} | {
        'reports': records.reports_for_batch(connection, batch)}
