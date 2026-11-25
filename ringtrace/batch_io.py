from .catalog import SOURCES
from .codec import canonical, digest
from .errors import DomainError
from .fields import exact_fields, token
from .observations import parse_report


def parse_package(raw):
    """Validate the package envelope and return the raw report rows.

    Only the header, the registered source and the array shape decide the
    fate of the whole submission. Row level problems are resolved later,
    encounter reference by encounter reference.
    """
    exact_fields(raw, 'batch source reports')
    batch = token(raw['batch'], '采集包编号')
    source = token(raw['source'], '来源编号')
    if source not in SOURCES:
        raise DomainError('unknown_source', '报文来源未登记。')
    if not isinstance(raw['reports'], list) or not 1 <= len(raw['reports']) <= 500:
        raise DomainError('invalid_batch_size', '每包须含 1 至 500 条报文。')
    return batch, source, raw['reports'], digest(canonical(raw))


def references(rows):
    """Resolve one encounter reference per row.

    Returns the references and a parallel list of errors. A missing or
    malformed reference makes the package undividable, so the caller refuses
    the whole submission instead of accepting any group.
    """
    found, errors = [], []
    for position, row in enumerate(rows, 1):
        if not isinstance(row, dict) or 'event' not in row:
            found.append(None)
            errors.append(DomainError(
                'invalid_fields', f'第 {position} 条报文：字段应为 report event band site kind observed_at。'))
            continue
        try:
            found.append(token(row['event'], '遭遇引用'))
            errors.append(None)
        except DomainError as error:
            found.append(None)
            errors.append(DomainError(error.code, f'第 {position} 条报文：{error}'))
    return found, errors


def parsed(rows):
    """Parse each row, returning the record or the validation failure."""
    result = []
    for row in rows:
        try:
            result.append((parse_report(row), None))
        except DomainError as error:
            result.append((None, error))
    return result


def tentative_number(row):
    """Return a report identifier that looks valid, even on an otherwise bad row."""
    raw = row.get('report') if isinstance(row, dict) else None
    try:
        return token(raw, '报文编号')
    except DomainError:
        return None


def report_numbers(rows):
    """Collect every report identifier that looks valid, for a cheap lookup."""
    return {number for number in map(tentative_number, rows) if number is not None}


GROUP_MESSAGES = {
    'invalid_row': '同组有报文未通过校验。',
    'duplicate_report': '同组报文编号重复。',
    'cross_group_report': '报文编号在包内跨组重用。',
    'report_conflict': '同组报文编号已被该来源接收。',
    'invalid_reference': '包内遭遇引用缺失或无效。',
    'package_rejected': '包内遭遇引用缺失或无效，整包拒收。',
}


def _line(position, event, number, disposition, reason, message):
    return {'position': position, 'event': event, 'report': number,
            'disposition': disposition, 'reason': reason, 'message': message}


def reference_refusal(found, rows, errors):
    """Describe a package refused because an encounter reference is unusable.

    Every line is reported as rejected; the line that carried the bad
    reference names its own reason, the others name the package refusal.
    """
    lines = []
    for position, row in enumerate(rows, 1):
        reference, number = errors[position - 1], tentative_number(row)
        lines.append(_line(position, found[position - 1], number, 'rejected',
                           reference.code if reference else 'package_rejected',
                           str(reference) if reference else GROUP_MESSAGES['package_rejected']))
    return lines


def split(found, rows, claimed):
    """Decide every submitted line and encounter group.

    ``found`` holds a valid encounter reference for every row, ``claimed`` the
    report numbers already accepted for the source. A group is accepted only
    when each of its lines is valid, its report numbers are unique inside the
    package and none of them was already accepted for the source. A report
    number shared across groups rejects every group that carries it, even when
    one of those rows fails validation for another reason.
    """
    pairs = parsed(rows)
    groups = {}
    for position, (event, (record, error)) in enumerate(zip(found, pairs), 1):
        groups.setdefault(event, []).append({'position': position, 'record': record, 'error': error,
                                             'tentative': tentative_number(rows[position - 1])})

    holders = {}
    for event, entries in groups.items():
        for entry in entries:
            if entry['tentative'] is not None:
                holders.setdefault(entry['tentative'], set()).add(event)
    shared = {number for number, events in holders.items() if len(events) > 1}

    conclusions, lines, accepted = [], [], []
    for event, entries in groups.items():
        seen = {}
        for entry in entries:
            if entry['tentative'] is not None:
                seen.setdefault(entry['tentative'], []).append(entry['position'])
        repeated = {number for number, positions in seen.items() if len(positions) > 1}
        reused = {number for number in seen if number in claimed}
        crossed = {number for number in seen if number in shared}
        if any(entry['error'] is not None for entry in entries):
            reason = 'invalid_row'
        elif repeated:
            reason = 'duplicate_report'
        elif crossed:
            reason = 'cross_group_report'
        elif reused:
            reason = 'report_conflict'
        else:
            reason = None

        rejected = []
        for entry in entries:
            record = entry['record']
            number = entry['tentative']
            if reason is None:
                accepted.append({'position': entry['position'], 'record': record})
                lines.append(_line(entry['position'], event, number, 'accepted', None, None))
                continue
            if entry['error'] is not None:
                line_reason, message = entry['error'].code, str(entry['error'])
            elif number in repeated:
                line_reason, message = 'duplicate_report', '报文编号在包内重复。'
            elif number in crossed:
                line_reason, message = 'cross_group_report', '报文编号在包内跨组重用。'
            elif number in reused:
                line_reason, message = 'report_conflict', '该来源已接收此报文编号。'
            else:
                line_reason, message = 'group_rejected', GROUP_MESSAGES[reason]
            rejected.append(entry['position'])
            lines.append(_line(entry['position'], event, number, 'rejected', line_reason, message))
        conclusions.append({'event': event, 'state': 'accepted' if reason is None else 'rejected',
                            'reason': reason, 'lines': [entry['position'] for entry in entries],
                            'rejected_lines': rejected})
    return conclusions, lines, accepted
