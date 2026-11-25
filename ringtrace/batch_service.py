from . import batch_repository as records
from .batch_io import parse_package, references, reference_refusal, report_numbers, split
from .codec import canonical, decode
from .database import advance, current_revision
from .errors import DomainError


VALIDATION_REASONS = {'invalid_row', 'duplicate_report', 'cross_group_report', 'invalid_reference'}
RECEIPT_KEYS = ('batch', 'source', 'sha256', 'count', 'line_count', 'revision', 'lines', 'groups')


def build(batch, source, sha, rows, conclusions, lines, acceptable, revision, package_error=None):
    originals = {position: canonical(row).decode('utf-8') for position, row in enumerate(rows, 1)}
    view = [dict(line, line=originals[line['position']])
            for line in sorted(lines, key=lambda row: row['position'])]
    return {'batch': batch, 'source': source, 'sha256': sha,
            'count': sum(1 for line in view if line['disposition'] == 'accepted'),
            'line_count': len(rows), 'revision': revision, 'replayed': False,
            'acceptable': acceptable, 'groups': conclusions, 'lines': view,
            'package_error': package_error}


def metadata(receipt):
    """Return the receipt in live-workspace shape, for a proposed snapshot."""
    return {key: receipt[key] for key in RECEIPT_KEYS if key != 'lines'} | {
        'lines': [public_line(line) for line in receipt['lines']]}


def replay(connection, previous):
    """Return the original receipt for a replayed package, byte-identical detail."""
    return {**previous, 'replayed': True, 'acceptable': True, 'count': previous['count'],
            'line_count': previous['line_count'], 'revision': previous['revision'],
            'lines': records.lines_for_batch(connection, previous['batch']),
            'groups': records.groups_for_batch(connection, previous['batch'])}


def assess(connection, payload, expected=None):
    """Validate a package and split it into encounter groups.

    Returns the proposed receipt, the accepted records and whether at least
    one group can be received. The package envelope and the encounter
    references decide whether the whole submission is refused; every other
    line problem only rejects the group sharing that encounter reference.
    """
    batch, source, rows, sha = parse_package(payload)
    previous = records.find_batch(connection, batch)
    if previous:
        if previous['sha256'] != sha:
            raise DomainError('batch_conflict', '该包编号已被不同内容占用。', 409)
        return replay(connection, previous), [], True
    current = current_revision(connection)
    if expected is not None and current != expected:
        raise DomainError('stale_revision', '试算所用修订已变化，请刷新后重新试算。', 409)
    found, errors = references(rows)
    if any(error is not None for error in errors):
        first = next(error for error in errors if error is not None)
        lines = reference_refusal(found, rows, errors)
        receipt = build(batch, source, sha, rows, [], lines, False, current + 1,
                        {'code': first.code, 'message': str(first), 'status': first.status})
        return receipt, [], False
    claimed = set(records.claimed_report_numbers(connection, source, report_numbers(rows)))
    groups, lines, accepted = split(found, rows, claimed)
    acceptable = any(group['state'] == 'accepted' for group in groups)
    receipt = build(batch, source, sha, rows, groups, lines, acceptable, current + 1)
    return receipt, accepted, acceptable


def refusal(receipt):
    """Build the refusal error describing why no group could be received."""
    details = {'groups': receipt['groups'], 'lines': [public_line(line) for line in receipt['lines']]}
    package = receipt.get('package_error')
    if package:
        return DomainError(package['code'], package['message'], package['status'], details)
    reasons = {group['reason'] for group in receipt['groups']}
    status = 400 if reasons <= VALIDATION_REASONS else 409
    code = next(iter(reasons)) if len(reasons) == 1 else 'no_acceptable_group'
    return DomainError(code, '没有可接收的遭遇组，整包未接收。', status, details)


def public_line(line):
    return {key: value for key, value in line.items() if key != 'line'}


def public(receipt):
    """Strip internal-only detail so only disposition and refusal data is exposed."""
    hidden = {'lines', 'package_error', 'acceptable'}
    return {key: value for key, value in receipt.items() if key not in hidden} | {
        'lines': [public_line(line) for line in receipt['lines']]}


def prepare(connection, payload, expected=None):
    receipt, accepted, acceptable = assess(connection, payload, expected)
    if not receipt['replayed'] and not acceptable:
        raise refusal(receipt)
    return receipt, accepted


def ingest(connection, payload, expected=None):
    """Receive every acceptable group of a package as one revision advance.

    A package with at least one acceptable group writes its receipt, line
    dispositions and accepted reports together and advances the revision once.
    A package with no acceptable group writes nothing and advances nothing.
    """
    receipt, accepted = prepare(connection, payload, expected)
    if not receipt['replayed']:
        advance(connection)
        records.insert_batch(connection, receipt, accepted)
    return public(receipt)


def stored(connection, batch):
    """Return the full receipt including the stored original line text."""
    previous = records.find_batch(connection, batch)
    if not previous:
        raise DomainError('unknown_batch', '未找到采集包。', 404)
    return {**previous, 'lines': records.lines_for_batch(connection, batch, source=True),
            'groups': records.groups_for_batch(connection, batch)}


def receipt(connection, batch):
    record = stored(connection, batch)
    lines = [{**public_line(line), 'original': decode(line['line'].encode('utf-8'))}
             for line in record['lines']]
    return {**public(record), 'lines': lines,
            'reports': records.reports_for_batch(connection, batch)}
